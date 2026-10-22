"""
CLI commands for testing and management
Run with: python -m app.cli <command> [args]
"""
import sys
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
from app.paths import DATA_DIR
DATABASE_URL = f"sqlite:///{DATA_DIR}/librarian.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from app.models import Base
from app.services import get_collection, get_collection_stats
Base.metadata.create_all(bind=engine)


def cmd_collection_create(name: str, root_path: str, host_display_path: str):
    """Create a new collection"""
    from app.services import register_collection, CollectionCreate
    
    db = SessionLocal()
    try:
        data = CollectionCreate(
            name=name,
            container_root=root_path,
            host_display_path=host_display_path,
        )
        collection = register_collection(db, data)
        print(f"✓ Created collection: {collection.id}")
        print(f"  Name: {collection.name}")
        print(f"  Root: {collection.container_root}")
    finally:
        db.close()


def cmd_collection_list():
    """List all collections"""
    from app.services import list_collections
    
    db = SessionLocal()
    try:
        collections = list_collections(db)
        if not collections:
            print("No collections found.")
            return
        
        print(f"\n{'ID':<36} {'Name':<20} {'Root':<40}")
        print("-" * 96)
        for c in collections:
            print(f"{c.id:<36} {c.name:<20} {c.container_root:<40}")
    finally:
        db.close()


def cmd_collection_stats(collection_id: str):
    """Show stats for a collection"""
    from app.services import get_collection, get_collection_stats
    
    db = SessionLocal()
    try:
        collection = get_collection(db, collection_id)
        if not collection:
            print(f"✗ Collection not found: {collection_id}")
            return
        
        stats = get_collection_stats(db, collection_id)
        print(f"\nCollection: {collection.name}")
        print(f"Root: {collection.container_root}")
        print(f"\nDocument Status:")
        print(f"  Discovered: {stats['discovered']}")
        print(f"  Queued: {stats['queued']}")
        print(f"  Processing: {stats['processing']}")
        print(f"  Indexed: {stats['indexed']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Skipped: {stats['skipped']}")
        print(f"  Inactive: {stats['inactive']}")
        print(f"  Needs Review: {stats.get('needs_review', 0)}")
        print(f"  ---")
        print(f"  Total: {stats['total']}")
    finally:
        db.close()


def cmd_scan(collection_id: str):
    """Scan a collection"""
    from app.jobs import JobQueue, ScanJobProcessor
    from app.services import get_collection
    
    db = SessionLocal()
    try:
        collection = get_collection(db, collection_id)
        if not collection:
            print(f"✗ Collection not found: {collection_id}")
            return
        
        print(f"Scanning {collection.name}...")
        
        job_queue = JobQueue(db)
        from app.models import JobType
        job = job_queue.create_job(collection_id, JobType.SCAN)
        
        processor = ScanJobProcessor(db, job_queue)
        processor.process(job.id)
        
        print(f"✓ Scan completed!")
        print(f"  Job ID: {job.id}")
        print(f"  Status: {job.status.value}")
        
        # Show stats
        stats = get_collection_stats(db, collection_id)
        print(f"\nResults:")
        print(f"  Discovered: {stats['discovered']}")
        print(f"  Total: {stats['total']}")
    
    except Exception as e:
        logger.exception("Scan failed")
        print(f"✗ Scan failed: {e}")
    finally:
        db.close()


def cmd_list_documents(collection_id: str):
    """List documents in a collection"""
    from app.models import Document
    
    db = SessionLocal()
    try:
        docs = db.query(Document).filter(
            Document.collection_id == collection_id
        ).order_by(Document.created_at.desc()).all()
        
        if not docs:
            print(f"No documents found in collection {collection_id}")
            return
        
        print(f"\n{'File Name':<50} {'Status':<12} {'Size':<10}")
        print("-" * 72)
        for doc in docs:
            size_str = f"{doc.size_bytes / 1024 / 1024:.1f}MB" if doc.size_bytes else "?"
            print(f"{doc.file_name:<50} {doc.status.value:<12} {size_str:<10}")
        
        print(f"\nTotal: {len(docs)} documents")
    finally:
        db.close()


# ============= NEW COMMANDS =============

def cmd_classify(collection_id: str):
    """Classify all documents in a collection"""
    from app.services import enqueue_classify_scan, get_collection
    
    db = SessionLocal()
    try:
        collection = get_collection(db, collection_id)
        if not collection:
            print(f"✗ Collection not found: {collection_id}")
            return
        
        print(f"Classifying {collection.name}...")
        
        job = enqueue_classify_scan(db, collection_id)
        
        # Process immediately
        from app.worker import Worker
        worker = Worker(db, queue_type="fast")
        worker.process_job(job)
        
        print(f"✓ Classification completed!")
        print(f"  Job ID: {job.id}")
        print(f"  Status: {job.status.value}")
    
    except Exception as e:
        logger.exception("Classification failed")
        print(f"✗ Classification failed: {e}")
    finally:
        db.close()


def cmd_dedupe(collection_id: str):
    """Run deduplication scan on a collection"""
    from app.services import enqueue_dedupe_scan, get_collection
    from app.dedupe import get_duplicate_report
    
    db = SessionLocal()
    try:
        collection = get_collection(db, collection_id)
        if not collection:
            print(f"✗ Collection not found: {collection_id}")
            return
        
        print(f"Running deduplication on {collection.name}...")
        
        job = enqueue_dedupe_scan(db, collection_id)
        
        # Process immediately
        from app.worker import Worker
        worker = Worker(db, queue_type="fast")
        worker.process_job(job)
        
        # Show report
        report = get_duplicate_report(db, collection_id)
        print(f"\n✓ Deduplication completed!")
        print(f"  Job ID: {job.id}")
        print(f"  Status: {job.status.value}")
        print(f"\nDuplicate Report:")
        print(f"  Total groups: {report['total_groups']}")
        print(f"  Exact hash groups: {report['exact_hash_groups']}")
        print(f"  Filename+size groups: {report['filename_size_groups']}")
        
        for group in report['groups'][:10]:  # Show first 10
            print(f"\n  Group {group['id'][:8]} ({group['type']}, {group['member_count']} files):")
            for doc in group['documents']:
                marker = "→ PRIMARY" if doc['is_primary'] else "  duplicate"
                print(f"  {marker}: {doc['relative_path']} ({doc['size_bytes']} bytes)")
        
        if len(report['groups']) > 10:
            print(f"\n  ... and {len(report['groups']) - 10} more groups")
    
    except Exception as e:
        logger.exception("Deduplication failed")
        print(f"✗ Deduplication failed: {e}")
    finally:
        db.close()


def cmd_extract(collection_id: str, doc_id: str = None):
    """Extract text from documents in a collection (or single document by ID)"""
    from app.services import enqueue_extract, get_collection, get_job
    from app.models import Document, DocumentStatus
    
    db = SessionLocal()
    try:
        collection = get_collection(db, collection_id)
        if not collection:
            print(f"✗ Collection not found: {collection_id}")
            return
        
        if doc_id:
            # Single document extraction
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if not doc:
                print(f"✗ Document not found: {doc_id}")
                return
            print(f"Extracting {doc.file_name}...")
        else:
            print(f"Extracting all documents in {collection.name}...")
        
        job = enqueue_extract(db, collection_id)
        
        # Process immediately
        from app.worker import Worker
        worker = Worker(db, queue_type="fast")
        worker.process_job(job)
        
        print(f"✓ Extraction completed!")
        print(f"  Job ID: {job.id}")
        print(f"  Status: {job.status.value}")
        
        # Show stats
        stats = get_collection_stats(db, collection_id)
        print(f"\nResults:")
        print(f"  Indexed: {stats['indexed']}")
        print(f"  Needs Review: {stats.get('needs_review', 0)}")
        print(f"  Failed: {stats['failed']}")
    
    except Exception as e:
        logger.exception("Extraction failed")
        print(f"✗ Extraction failed: {e}")
    finally:
        db.close()


def cmd_ocr(collection_id: str, doc_id: str = None):
    """Run OCR on scanned PDFs in a collection (or single document by ID)"""
    from app.services import enqueue_ocr, get_collection
    from app.models import Document
    
    db = SessionLocal()
    try:
        collection = get_collection(db, collection_id)
        if not collection:
            print(f"✗ Collection not found: {collection_id}")
            return
        
        if doc_id:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if not doc:
                print(f"✗ Document not found: {doc_id}")
                return
            print(f"Running OCR on {doc.file_name}...")
        else:
            print(f"Running OCR on scanned PDFs in {collection.name}...")
        
        job = enqueue_ocr(db, collection_id)
        
        # Process immediately (slow queue)
        from app.worker import Worker
        worker = Worker(db, queue_type="slow")
        worker.process_job(job)
        
        print(f"✓ OCR completed!")
        print(f"  Job ID: {job.id}")
        print(f"  Status: {job.status.value}")
    
    except Exception as e:
        logger.exception("OCR failed")
        print(f"✗ OCR failed: {e}")
    finally:
        db.close()


def cmd_extract_all(collection_id: str = None, queue: bool = False):
    """Queue extraction jobs for all text-classified documents across collections"""
    from app.services import enqueue_extract, list_collections, get_collection
    from app.models import Document, DocumentStatus
    
    db = SessionLocal()
    try:
        if collection_id:
            collections = [get_collection(db, collection_id)]
            if not collections[0]:
                print(f"✗ Collection not found: {collection_id}")
                return
        else:
            collections = list_collections(db, active_only=True)
        
        if not collections:
            print("No active collections found.")
            return
        
        total_queued = 0
        for collection in collections:
            # Count documents ready for extraction
            count = db.query(Document).filter(
                Document.collection_id == collection.id,
                Document.status.in_([DocumentStatus.DISCOVERED, DocumentStatus.QUEUED]),
                Document.extension.in_(["pdf", "txt", "md", "docx", "pptx", "xlsx", "json"])
            ).count()
            
            if count > 0:
                job = enqueue_extract(db, collection.id)
                total_queued += 1
                if queue:
                    print(f"  Queued EXTRACT_TEXT job {job.id} for {collection.name} ({count} docs)")
                else:
                    # Process immediately
                    from app.worker import Worker
                    worker = Worker(db, queue_type="fast")
                    worker.process_job(job)
                    print(f"  Completed extraction for {collection.name} ({count} docs)")
        
        if queue:
            print(f"\n✓ Queued {total_queued} extraction jobs")
        else:
            print(f"\n✓ Completed extraction for {total_queued} collections")
    
    except Exception as e:
        logger.exception("Extract-all failed")
        print(f"✗ Extract-all failed: {e}")
    finally:
        db.close()


def cmd_quality(doc_id: str):
    """Show quality assessment for a document"""
    from app.models import Document
    from app.extract import save_extraction_result
    from app.quality import compute_quality_score
    
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            print(f"✗ Document not found: {doc_id}")
            return
        
        print(f"Quality assessment for: {doc.file_name}")
        print(f"  Status: {doc.status.value}")
        print(f"  Quality Score: {doc.quality_score or 'N/A'}")
        print(f"  Extraction Method: {doc.extraction_method or 'N/A'}")
        print(f"  Pages: {doc.page_count or 'N/A'}")
        print(f"  Characters: {doc.char_count or 'N/A'}")
        print(f"  High Value: {doc.high_value}")
        
        if doc.extraction_path and Path(doc.extraction_path).exists():
            with open(doc.extraction_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            quality = compute_quality_score(
                text=text,
                file_size=doc.size_bytes or 0,
                pages=doc.page_count or 1,
                method=doc.extraction_method or "unknown",
                extraction_confidence=1.0
            )
            
            print(f"\nDetailed Quality:")
            print(f"  Final Score: {quality.score:.3f}")
            print(f"  Passed: {quality.passed}")
            print(f"  Needs Review: {quality.needs_review}")
            print(f"  Threshold: {quality.threshold}")
            print(f"  Extracted Chars: {quality.extracted_chars}")
            print(f"  Component Scores:")
            for k, v in quality.details.get('component_scores', {}).items():
                print(f"    {k}: {v:.3f}")
    
    except Exception as e:
        logger.exception("Quality check failed")
        print(f"✗ Quality check failed: {e}")
    finally:
        db.close()


def cmd_summarize(doc_id: str, high_value: bool = False):
    """Summarize a document using Ollama (marks as high-value if --high-value)"""
    from app.models import Document, DocumentStatus
    from app.ollama_client import OllamaClient
    
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            print(f"✗ Document not found: {doc_id}")
            return
        
        if high_value:
            doc.high_value = True
            db.commit()
            print(f"Marked {doc.file_name} as high-value")
        
        if doc.status != DocumentStatus.INDEXED:
            print(f"✗ Document not indexed (status: {doc.status.value})")
            return
        
        if not doc.extraction_path or not Path(doc.extraction_path).exists():
            print(f"✗ No extracted text available")
            return
        
        print(f"Summarizing {doc.file_name}...")
        
        with open(doc.extraction_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        client = OllamaClient()
        if not client.check_health():
            print("✗ Ollama not available")
            return
        
        result = client.summarize(text, max_length=300)
        
        if result.success:
            print(f"\n✓ Summary ({result.eval_count} tokens):")
            print(result.text)
            
            # Save summary
            summary_path = Path(doc.extraction_path).with_suffix('.summary.txt')
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(result.text)
            print(f"\nSaved to: {summary_path}")
        else:
            print(f"✗ Summarization failed: {result.error}")
    
    except Exception as e:
        logger.exception("Summarization failed")
        print(f"✗ Summarization failed: {e}")
    finally:
        db.close()


def usage():
    """Show usage"""
    print("""
Librarian CLI — Collection and indexing management

Usage: python -m app.cli <command> [args]

Commands:
  collection-create <name> <root_path> <host_display_path>
                          Create a new collection
                          Example: collection-create references /sources/references D:\\References
   
  collection-list        List all collections
   
  collection-stats <collection_id>
                          Show statistics for a collection
   
  scan <collection_id>    Scan and index a collection
   
  list-documents <collection_id>
                          List documents in a collection
   
  classify <collection_id>
                          Classify all documents in a collection
   
  dedupe <collection_id>
                          Find and report duplicates in a collection
   
  extract <collection_id> [doc_id]
                          Extract text from all documents (or single doc by ID)
   
  ocr <collection_id> [doc_id]
                          Run OCR on scanned PDFs (or single doc by ID)
   
  extract-all [collection_id] [--queue]
                          Queue extraction for all collections (or one)
                          Use --queue to only queue jobs, not process
   
  quality <doc_id>
                          Show quality assessment for a document
   
  summarize <doc_id> [--high-value]
                          Summarize a document using Ollama
                          Use --high-value to mark as high-value

Examples:
  python -m app.cli collection-create references /sources/references D:\\References
  python -m app.cli collection-list
  python -m app.cli scan <id>
  python -m app.cli classify <id>
  python -m app.cli dedupe <id>
  python -m app.cli extract <id>
  python -m app.cli extract-all --queue
  python -m app.cli quality <doc_id>
  python -m app.cli summarize <doc_id> --high-value
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    try:
        if command == "collection-create":
            if len(args) < 3:
                print("Error: collection-create requires 3 arguments")
                sys.exit(1)
            cmd_collection_create(args[0], args[1], args[2])
        
        elif command == "collection-list":
            cmd_collection_list()
        
        elif command == "collection-stats":
            if len(args) < 1:
                print("Error: collection-stats requires 1 argument (collection_id)")
                sys.exit(1)
            cmd_collection_stats(args[0])
        
        elif command == "scan":
            if len(args) < 1:
                print("Error: scan requires 1 argument (collection_id)")
                sys.exit(1)
            cmd_scan(args[0])
        
        elif command == "list-documents":
            if len(args) < 1:
                print("Error: list-documents requires 1 argument (collection_id)")
                sys.exit(1)
            cmd_list_documents(args[0])
        
        elif command == "classify":
            if len(args) < 1:
                print("Error: classify requires 1 argument (collection_id)")
                sys.exit(1)
            cmd_classify(args[0])
        
        elif command == "dedupe":
            if len(args) < 1:
                print("Error: dedupe requires 1 argument (collection_id)")
                sys.exit(1)
            cmd_dedupe(args[0])
        
        elif command == "extract":
            if len(args) < 1:
                print("Error: extract requires at least 1 argument (collection_id)")
                sys.exit(1)
            doc_id = args[1] if len(args) > 1 else None
            cmd_extract(args[0], doc_id)
        
        elif command == "ocr":
            if len(args) < 1:
                print("Error: ocr requires at least 1 argument (collection_id)")
                sys.exit(1)
            doc_id = args[1] if len(args) > 1 else None
            cmd_ocr(args[0], doc_id)
        
        elif command == "extract-all":
            collection_id = args[0] if len(args) > 0 and not args[0].startswith('--') else None
            queue = '--queue' in args
            cmd_extract_all(collection_id, queue)
        
        elif command == "quality":
            if len(args) < 1:
                print("Error: quality requires 1 argument (doc_id)")
                sys.exit(1)
            cmd_quality(args[0])
        
        elif command == "summarize":
            if len(args) < 1:
                print("Error: summarize requires 1 argument (doc_id)")
                sys.exit(1)
            high_value = '--high-value' in args
            cmd_summarize(args[0], high_value)
        
        else:
            print(f"Unknown command: {command}")
            usage()
            sys.exit(1)
    
    except Exception as e:
        logger.exception("Command failed")
        print(f"Error: {e}")
        sys.exit(1)
