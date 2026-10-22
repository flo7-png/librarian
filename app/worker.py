"""
Librarian worker — background task processor
"""
import logging
import os
import sys
import time
import signal
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.paths import DATA_DIR
DATABASE_URL = f"sqlite:///{DATA_DIR}/librarian.db"

from app.models import Base, Job, JobStatus, JobType, Document, DocumentStatus, Collection
from app.jobs import JobQueue
from app.scanner import FileScanner, ChangeDetector
from app.services import get_collection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


class Worker:
    """Background job worker with dispatch table"""
    
    def __init__(self, db: Session, queue_type: str = "fast"):
        self.db = db
        self.queue_type = queue_type
        self.job_queue = JobQueue(db)
        
        # Dispatch table: job_type -> handler method
        self.handlers = {
            JobType.SCAN: self._handle_scan,
            JobType.EXTRACT_TEXT: self._handle_extract_text,
            JobType.OCR_PDF: self._handle_ocr_pdf,
            JobType.NORMALIZE_JSON: self._handle_normalize_json,
            JobType.DEDUPE_SCAN: self._handle_dedupe_scan,
            JobType.CLASSIFY_SCAN: self._handle_classify_scan,
            JobType.SUMMARIZE: self._handle_summarize,
        }
        
        # Job types this worker handles
        if queue_type == "fast":
            self.handled_types = [
                JobType.SCAN,
                JobType.EXTRACT_TEXT,
                JobType.NORMALIZE_JSON,
                JobType.DEDUPE_SCAN,
                JobType.CLASSIFY_SCAN,
                JobType.SUMMARIZE,
            ]
        else:  # slow queue for OCR
            self.handled_types = [
                JobType.OCR_PDF,
            ]
    
    def _get_next_job(self) -> Optional[Job]:
        """Get next queued job this worker can handle"""
        for job_type in self.handled_types:
            job = self.db.query(Job).filter(
                Job.job_type == job_type,
                Job.status == JobStatus.QUEUED
            ).order_by(Job.priority.desc(), Job.created_at).first()
            if job:
                return job
        return None
    
    def process_job(self, job: Job) -> bool:
        """Process a single job"""
        job_id = job.id
        job_type = job.job_type
        
        logger.info(f"Processing job {job_id} (type: {job_type})")
        
        try:
            self.job_queue.start_job(job_id)
            
            handler = self.handlers.get(job_type)
            if not handler:
                raise ValueError(f"No handler for job type: {job_type}")
            
            handler(job)
            
            self.job_queue.complete_job(job_id, f"Completed {job_type.value}")
            logger.info(f"Job {job_id} completed successfully")
            return True
            
        except Exception as e:
            logger.exception(f"Job {job_id} failed")
            self.job_queue.fail_job(job_id, str(e))
            return False
    
    def run(self, once: bool = False):
        """Main worker loop"""
        logger.info(f"Worker started (queue: {self.queue_type})")
        
        while not shutdown_requested:
            job = self._get_next_job()
            
            if job:
                self.process_job(job)
                
                if once:
                    break
            else:
                # No jobs, sleep
                time.sleep(5)
        
        logger.info("Worker shutting down")
    
    # ========== Job Handlers ==========
    
    def _handle_scan(self, job: Job):
        """Handle SCAN job"""
        from app.jobs import ScanJobProcessor
        
        processor = ScanJobProcessor(self.db, self.job_queue)
        processor.process(job.id)
    
    def _handle_extract_text(self, job: Job):
        """Handle EXTRACT_TEXT job"""
        from app.extract import extract_text, extract_text_pdf, save_extraction_result
        from app.classify import classify_file, is_scanned_pdf, FileType, PDFType
        from app.quality import compute_quality_score
        
        # Job should have document_id in a custom field or we process all discovered
        # For now, process all DISCOVERED documents in the collection
        collection_id = job.collection_id
        if not collection_id:
            raise ValueError("EXTRACT_TEXT job requires collection_id")
        
        docs = self.db.query(Document).filter(
            Document.collection_id == collection_id,
            Document.status.in_([DocumentStatus.DISCOVERED, DocumentStatus.QUEUED]),
            Document.extension.in_(["pdf", "txt", "md", "docx", "pptx", "xlsx", "json"])
        ).all()
        
        if not docs:
            logger.info(f"No documents to extract in collection {collection_id}")
            self.job_queue.update_progress(job.id, 0, 0)
            return
        
        self.job_queue.update_progress(job.id, 0, len(docs))
        
        for i, doc in enumerate(docs):
            if shutdown_requested:
                break
            
            try:
                filepath = Path(doc.source_path)
                if not filepath.exists():
                    logger.warning(f"File not found: {filepath}")
                    doc.status = DocumentStatus.FAILED
                    doc.error_message = "Source file not found"
                    continue
                
                # Classify
                file_type = classify_file(filepath)
                pdf_type = is_scanned_pdf(filepath) if file_type == FileType.PDF else None

                # Fast queue must never OCR inline: scanned PDFs go to the slow OCR queue
                if pdf_type == PDFType.SCANNED:
                    doc.ocr_status = "pending"
                    self.db.commit()
                    self.job_queue.update_progress(job.id, i + 1, len(docs))
                    continue

                # Extract
                doc.status = DocumentStatus.PROCESSING
                self.db.commit()

                if pdf_type == PDFType.MIXED:
                    # Text layer only; low-yield docs fall to NEEDS_REVIEW and get OCR'd by the slow queue
                    result = extract_text_pdf(filepath)
                else:
                    result = extract_text(filepath, file_type, pdf_type)
                
                # Save extraction
                text_path, manifest_path = save_extraction_result(
                    filepath, result, doc.content_hash
                )
                
                # Quality check
                quality = compute_quality_score(
                    text=result.text,
                    file_size=doc.size_bytes or 0,
                    pages=result.pages,
                    method=result.method,
                    extraction_confidence=result.confidence
                )
                
                # Update document
                doc.extraction_path = str(text_path)
                doc.parser = result.method
                doc.page_count = result.pages
                doc.char_count = len(result.text)
                doc.quality_score = int(quality.score * 100)
                doc.extraction_method = result.method
                
                if quality.needs_review:
                    doc.status = DocumentStatus.NEEDS_REVIEW
                    doc.error_message = f"Quality score: {quality.score:.2f} (threshold: {quality.threshold})"
                else:
                    doc.status = DocumentStatus.INDEXED
                    doc.indexed_at = datetime.utcnow()
                    doc.error_message = None
                
                self.db.commit()
                
                # Log event
                self.job_queue.log_event(
                    job.id, "extraction_complete",
                    f"Extracted {doc.file_name}: {result.method}, {len(result.text)} chars, quality={quality.score:.2f}",
                    document_id=doc.id
                )
                
            except Exception as e:
                logger.exception(f"Extraction failed for {doc.relative_path}")
                doc.status = DocumentStatus.FAILED
                doc.error_message = str(e)
                self.db.commit()
                
                self.job_queue.log_event(
                    job.id, "extraction_failed",
                    f"Failed to extract {doc.file_name}: {e}",
                    level="error",
                    document_id=doc.id
                )
            
            self.job_queue.update_progress(job.id, i + 1, len(docs))
    
    def _handle_ocr_pdf(self, job: Job):
        """Handle OCR_PDF job - for scanned PDFs"""
        from app.extract import extract_text_scanned_pdf, save_extraction_result
        from app.classify import is_scanned_pdf, PDFType
        from app.quality import compute_quality_score
        
        collection_id = job.collection_id
        if not collection_id:
            raise ValueError("OCR_PDF job requires collection_id")
        
        # Find documents marked as needing OCR
        docs = self.db.query(Document).filter(
            Document.collection_id == collection_id,
            Document.extension == "pdf",
            Document.status.in_([DocumentStatus.DISCOVERED, DocumentStatus.QUEUED, DocumentStatus.NEEDS_REVIEW]),
        ).all()
        
        # Filter to only scanned PDFs
        scanned_docs = []
        for doc in docs:
            filepath = Path(doc.source_path)
            if filepath.exists():
                pdf_type = is_scanned_pdf(filepath)
                if pdf_type in (PDFType.SCANNED, PDFType.MIXED):
                    scanned_docs.append(doc)
        
        if not scanned_docs:
            logger.info(f"No scanned PDFs to OCR in collection {collection_id}")
            self.job_queue.update_progress(job.id, 0, 0)
            return
        
        self.job_queue.update_progress(job.id, 0, len(scanned_docs))
        
        for i, doc in enumerate(scanned_docs):
            if shutdown_requested:
                break
            
            try:
                filepath = Path(doc.source_path)
                
                doc.status = DocumentStatus.PROCESSING
                doc.ocr_status = "running"
                self.db.commit()
                
                result = extract_text_scanned_pdf(filepath)
                
                # Save extraction
                text_path, manifest_path = save_extraction_result(
                    filepath, result, doc.content_hash
                )
                
                # Quality check
                quality = compute_quality_score(
                    text=result.text,
                    file_size=doc.size_bytes or 0,
                    pages=result.pages,
                    method=result.method,
                    extraction_confidence=result.confidence
                )
                
                # Update document
                doc.extraction_path = str(text_path)
                doc.parser = "tesseract"
                doc.ocr_status = "complete"
                doc.page_count = result.pages
                doc.char_count = len(result.text)
                doc.quality_score = int(quality.score * 100)
                doc.extraction_method = result.method
                
                if quality.needs_review:
                    doc.status = DocumentStatus.NEEDS_REVIEW
                    doc.error_message = f"OCR quality: {quality.score:.2f}"
                else:
                    doc.status = DocumentStatus.INDEXED
                    doc.indexed_at = datetime.utcnow()
                    doc.error_message = None
                
                self.db.commit()
                
                self.job_queue.log_event(
                    job.id, "ocr_complete",
                    f"OCR'd {doc.file_name}: {len(result.text)} chars, quality={quality.score:.2f}",
                    document_id=doc.id
                )
                
            except Exception as e:
                logger.exception(f"OCR failed for {doc.relative_path}")
                doc.status = DocumentStatus.FAILED
                doc.ocr_status = "failed"
                doc.error_message = str(e)
                self.db.commit()
                
                self.job_queue.log_event(
                    job.id, "ocr_failed",
                    f"OCR failed for {doc.file_name}: {e}",
                    level="error",
                    document_id=doc.id
                )
            
            self.job_queue.update_progress(job.id, i + 1, len(scanned_docs))
    
    def _handle_normalize_json(self, job: Job):
        """Handle NORMALIZE_JSON job"""
        from app.extract import extract_text_json, save_extraction_result
        from app.quality import compute_quality_score
        
        collection_id = job.collection_id
        if not collection_id:
            raise ValueError("NORMALIZE_JSON job requires collection_id")
        
        docs = self.db.query(Document).filter(
            Document.collection_id == collection_id,
            Document.extension == "json",
            Document.status.in_([DocumentStatus.DISCOVERED, DocumentStatus.QUEUED]),
        ).all()
        
        if not docs:
            self.job_queue.update_progress(job.id, 0, 0)
            return
        
        self.job_queue.update_progress(job.id, 0, len(docs))
        
        for i, doc in enumerate(docs):
            if shutdown_requested:
                break
            
            try:
                filepath = Path(doc.source_path)
                if not filepath.exists():
                    continue
                
                doc.status = DocumentStatus.PROCESSING
                self.db.commit()
                
                result = extract_text_json(filepath)
                
                text_path, manifest_path = save_extraction_result(
                    filepath, result, doc.content_hash
                )
                
                quality = compute_quality_score(
                    text=result.text,
                    file_size=doc.size_bytes or 0,
                    pages=result.pages,
                    method=result.method,
                    extraction_confidence=result.confidence
                )
                
                doc.extraction_path = str(text_path)
                doc.parser = "json_normalizer"
                doc.page_count = result.pages
                doc.char_count = len(result.text)
                doc.quality_score = int(quality.score * 100)
                doc.extraction_method = result.method
                
                if quality.needs_review:
                    doc.status = DocumentStatus.NEEDS_REVIEW
                else:
                    doc.status = DocumentStatus.INDEXED
                    doc.indexed_at = datetime.utcnow()
                
                self.db.commit()
                
            except Exception as e:
                logger.exception(f"JSON normalization failed for {doc.relative_path}")
                doc.status = DocumentStatus.FAILED
                doc.error_message = str(e)
                self.db.commit()
            
            self.job_queue.update_progress(job.id, i + 1, len(docs))
    
    def _handle_dedupe_scan(self, job: Job):
        """Handle DEDUPE_SCAN job"""
        from app.dedupe import run_dedupe_scan
        
        collection_id = job.collection_id
        if not collection_id:
            raise ValueError("DEDUPE_SCAN job requires collection_id")
        
        summary = run_dedupe_scan(self.db, collection_id)
        
        self.job_queue.log_event(
            job.id, "dedupe_complete",
            f"Found {summary['exact_duplicate_groups']} exact groups, {summary['filename_size_groups']} name+size groups"
        )
    
    def _handle_classify_scan(self, job: Job):
        """Handle CLASSIFY_SCAN job"""
        from app.classify import get_file_type_info
        
        collection_id = job.collection_id
        if not collection_id:
            raise ValueError("CLASSIFY_SCAN job requires collection_id")
        
        docs = self.db.query(Document).filter(
            Document.collection_id == collection_id,
            Document.status != 'inactive'
        ).all()
        
        if not docs:
            self.job_queue.update_progress(job.id, 0, 0)
            return
        
        self.job_queue.update_progress(job.id, 0, len(docs))
        
        for i, doc in enumerate(docs):
            if shutdown_requested:
                break
            
            try:
                filepath = Path(doc.source_path)
                if filepath.exists():
                    info = get_file_type_info(filepath)
                    doc.parser = info.get("final_type", "unknown")
                    if "pdf_type" in info:
                        doc.ocr_status = "pending" if info.get("needs_ocr") else "not_needed"
                    self.db.commit()
            except Exception as e:
                logger.warning(f"Classification failed for {doc.relative_path}: {e}")
            
            self.job_queue.update_progress(job.id, i + 1, len(docs))
    
    def _handle_summarize(self, job: Job):
        """Handle SUMMARIZE job - uses Ollama for high-value docs"""
        from app.ollama_client import OllamaClient
        from app.extract import save_extraction_result
        
        collection_id = job.collection_id
        if not collection_id:
            raise ValueError("SUMMARIZE job requires collection_id")
        
        # Find high-value indexed documents
        docs = self.db.query(Document).filter(
            Document.collection_id == collection_id,
            Document.high_value == True,
            Document.status == DocumentStatus.INDEXED,
            Document.extraction_path.isnot(None)
        ).all()
        
        if not docs:
            logger.info(f"No high-value docs to summarize in collection {collection_id}")
            self.job_queue.update_progress(job.id, 0, 0)
            return
        
        client = OllamaClient()
        
        if not client.check_health():
            raise RuntimeError("Ollama not available")
        
        self.job_queue.update_progress(job.id, 0, len(docs))
        
        for i, doc in enumerate(docs):
            if shutdown_requested:
                break
            
            try:
                # Read extracted text
                extraction_path = Path(doc.extraction_path)
                if not extraction_path.exists():
                    logger.warning(f"Extraction file not found: {extraction_path}")
                    continue
                
                with open(extraction_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                # Summarize
                result = client.summarize(text, max_length=300)
                
                if result.success:
                    # Save summary alongside extraction
                    summary_path = extraction_path.with_suffix('.summary.txt')
                    with open(summary_path, 'w', encoding='utf-8') as f:
                        f.write(result.text)
                    
                    doc.error_message = f"Summarized: {result.text[:200]}..."
                    self.db.commit()
                    
                    self.job_queue.log_event(
                        job.id, "summarize_complete",
                        f"Summarized {doc.file_name} ({result.eval_count} tokens)",
                        document_id=doc.id
                    )
                else:
                    logger.warning(f"Summarization failed for {doc.file_name}: {result.error}")
                
            except Exception as e:
                logger.exception(f"Summarization failed for {doc.relative_path}")
                self.job_queue.log_event(
                    job.id, "summarize_failed",
                    f"Summarization failed for {doc.file_name}: {e}",
                    level="error",
                    document_id=doc.id
                )
            
            self.job_queue.update_progress(job.id, i + 1, len(docs))


def main():
    """Worker entry point"""
    queue_type = "fast"
    once = False
    
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv[1:]):
            if arg == "--queue" and i + 1 < len(sys.argv):
                queue_type = sys.argv[i + 2]
            elif arg == "--once":
                once = True
    
    # Initialize database
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    
    db = SessionLocal()
    try:
        worker = Worker(db, queue_type)
        worker.run(once=once)
    finally:
        db.close()


if __name__ == "__main__":
    main()