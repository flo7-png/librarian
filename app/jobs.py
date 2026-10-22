"""
Job queue and worker orchestration
"""
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models import Job, JobStatus, JobType, JobEvent, JobEventLevel, Collection, Document, DocumentStatus

logger = logging.getLogger(__name__)


class JobQueue:
    """In-memory job queue for background tasks"""
    
    def __init__(self, db: Session):
        self.db = db
        self.fast_queue = []  # For quick extraction tasks
        self.slow_queue = []  # For OCR/heavy tasks
    
    def create_job(
        self,
        collection_id: str,
        job_type: JobType,
        priority: int = 0,
    ) -> Job:
        """Create and queue a new job"""
        job = Job(
            id=str(uuid.uuid4()),
            collection_id=collection_id,
            job_type=job_type,
            status=JobStatus.QUEUED,
            priority=priority,
        )
        self.db.add(job)
        self.db.commit()
        
        logger.info(f"Created job {job.id} for collection {collection_id} (type: {job_type})")
        return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Fetch a job by ID"""
        return self.db.query(Job).filter(Job.id == job_id).first()
    
    def list_jobs(self, collection_id: Optional[str] = None, status: Optional[JobStatus] = None) -> List[Job]:
        """List jobs with optional filtering"""
        query = self.db.query(Job)
        if collection_id:
            query = query.filter(Job.collection_id == collection_id)
        if status:
            query = query.filter(Job.status == status)
        return query.order_by(Job.created_at.desc()).all()
    
    def start_job(self, job_id: str) -> Job:
        """Mark job as running"""
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Started job {job_id}")
        return job
    
    def complete_job(self, job_id: str, message: Optional[str] = None) -> Job:
        """Mark job as completed"""
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        
        job.status = JobStatus.COMPLETED
        job.finished_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Completed job {job_id}")
        if message:
            self.log_event(job_id, "completion", message, JobEventLevel.INFO)
        
        return job
    
    def fail_job(self, job_id: str, error: str) -> Job:
        """Mark job as failed"""
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        
        job.status = JobStatus.FAILED
        job.finished_at = datetime.utcnow()
        job.error_message = error
        self.db.commit()
        
        logger.error(f"Failed job {job_id}: {error}")
        self.log_event(job_id, "failure", error, JobEventLevel.ERROR)
        
        return job
    
    def pause_job(self, job_id: str) -> Job:
        """Pause a running job"""
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        
        job.status = JobStatus.PAUSED
        self.db.commit()
        
        logger.info(f"Paused job {job_id}")
        return job
    
    def resume_job(self, job_id: str) -> Job:
        """Resume a paused job"""
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        
        job.status = JobStatus.RUNNING
        self.db.commit()
        
        logger.info(f"Resumed job {job_id}")
        return job
    
    def cancel_job(self, job_id: str) -> Job:
        """Cancel a job"""
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        
        job.status = JobStatus.CANCELLED
        job.finished_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Cancelled job {job_id}")
        return job
    
    def update_progress(self, job_id: str, done: int, total: int) -> Job:
        """Update job progress"""
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        
        job.progress_done = done
        job.progress_total = total
        self.db.commit()
        
        return job
    
    def log_event(
        self,
        job_id: str,
        event_type: str,
        message: str,
        level: JobEventLevel = JobEventLevel.INFO,
        document_id: Optional[str] = None,
    ) -> JobEvent:
        """Log a job event"""
        event = JobEvent(
            id=str(uuid.uuid4()),
            job_id=job_id,
            document_id=document_id,
            level=level,
            event_type=event_type,
            message=message,
        )
        self.db.add(event)
        self.db.commit()
        
        return event


class ScanJobProcessor:
    """Process a SCAN job: recursively discover files in a collection"""
    
    def __init__(self, db: Session, job_queue: JobQueue):
        self.db = db
        self.job_queue = job_queue
    
    def process(self, job_id: str) -> None:
        """Execute the scan job"""
        from app.scanner import FileScanner, ChangeDetector
        
        job = self.job_queue.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        
        try:
            self.job_queue.start_job(job_id)
            
            collection = self.db.query(Collection).filter(Collection.id == job.collection_id).first()
            if not collection:
                raise ValueError(f"Collection not found: {job.collection_id}")
            
            logger.info(f"Scanning collection {collection.name} from {collection.container_root}")
            
            # Scan the collection root
            scanner = FileScanner(
                root_path=collection.container_root,
                include_extensions=collection.include_extensions,
                exclude_directories=collection.exclude_directories,
            )
            current_files = scanner.scan()
            
            # Get previous hashes from DB
            previous_docs = self.db.query(Document).filter(
                Document.collection_id == collection.id
            ).all()
            previous_hashes = {doc.relative_path: doc.content_hash for doc in previous_docs}
            
            # Detect changes
            new_or_changed, unchanged, deleted = ChangeDetector.detect_changes(
                current_files,
                previous_hashes,
            )
            
            logger.info(
                f"Scan results: {len(new_or_changed)} new/changed, "
                f"{len(unchanged)} unchanged, {len(deleted)} deleted"
            )
            
            # Update database
            # 1. Insert/update new files as DISCOVERED
            for file_data in new_or_changed:
                existing = self.db.query(Document).filter(
                    Document.collection_id == collection.id,
                    Document.relative_path == file_data["relative_path"],
                ).first()
                
                if existing:
                    # Update existing
                    existing.content_hash = file_data["content_hash"]
                    existing.size_bytes = file_data["size_bytes"]
                    existing.modified_time = file_data["modified_time"]
                    existing.status = DocumentStatus.DISCOVERED
                    existing.last_seen_at = datetime.utcnow()
                else:
                    # Create new
                    doc = Document(
                        id=str(uuid.uuid4()),
                        collection_id=collection.id,
                        relative_path=file_data["relative_path"],
                        source_path=file_data["source_path"],
                        file_name=file_data["file_name"],
                        extension=file_data["extension"],
                        size_bytes=file_data["size_bytes"],
                        modified_time=file_data["modified_time"],
                        content_hash=file_data["content_hash"],
                        status=DocumentStatus.DISCOVERED,
                    )
                    self.db.add(doc)
            
            # 2. Mark deleted files as INACTIVE
            for relative_path in deleted:
                doc = self.db.query(Document).filter(
                    Document.collection_id == collection.id,
                    Document.relative_path == relative_path,
                ).first()
                if doc:
                    doc.status = DocumentStatus.INACTIVE
                    logger.info(f"Marked {relative_path} as inactive (deleted)")
            
            # 3. Update unchanged files' last_seen_at
            for file_data in unchanged:
                doc = self.db.query(Document).filter(
                    Document.collection_id == collection.id,
                    Document.relative_path == file_data["relative_path"],
                ).first()
                if doc:
                    doc.last_seen_at = datetime.utcnow()
            
            self.db.commit()
            
            # Set progress and complete
            total = len(current_files)
            self.job_queue.update_progress(job_id, total, total)
            self.job_queue.complete_job(
                job_id,
                f"Scanned {total} files: {len(new_or_changed)} new/changed, "
                f"{len(deleted)} deleted"
            )
            
            logger.info(f"Scan job {job_id} completed successfully")
        
        except Exception as e:
            logger.exception(f"Scan job {job_id} failed")
            self.job_queue.fail_job(job_id, str(e))
            raise
