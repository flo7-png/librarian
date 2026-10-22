"""
Collection management API endpoints
"""
import logging
import uuid
from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


# Pydantic schemas for request/response
class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    host_display_path: str
    container_root: str
    recursive: bool = True
    include_extensions: Optional[List[str]] = None
    exclude_directories: Optional[List[str]] = None


class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    active: Optional[bool] = None
    include_extensions: Optional[List[str]] = None
    exclude_directories: Optional[List[str]] = None


class CollectionResponse(BaseModel):
    id: str
    name: str
    host_display_path: str
    container_root: str
    recursive: bool
    active: bool
    include_extensions: List[str]
    exclude_directories: List[str]
    created_at: str
    
    class Config:
        from_attributes = True


class CollectionStatsResponse(CollectionResponse):
    discovered: int = 0
    indexed: int = 0
    failed: int = 0
    queued: int = 0
    total: int = 0


class JobResponse(BaseModel):
    job_id: str
    status: str
    
    class Config:
        from_attributes = True


def register_collection(db: Session, data: CollectionCreate) -> 'Collection':
    """Create and register a new collection"""
    from app.models import Collection
    
    # Validate uniqueness
    existing = db.query(Collection).filter(Collection.name == data.name).first()
    if existing:
        raise ValueError(f"Collection name already exists: {data.name}")
    
    collection = Collection(
        id=str(uuid.uuid4()),
        name=data.name,
        host_display_path=data.host_display_path,
        container_root=data.container_root,
        recursive=data.recursive,
        include_extensions=data.include_extensions or [],
        exclude_directories=data.exclude_directories or [],
    )
    
    db.add(collection)
    try:
        db.commit()
        logger.info(f"Registered collection: {data.name}")
        return collection
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Failed to register collection: {e}")


def get_collection(db: Session, collection_id: str) -> Optional['Collection']:
    """Fetch collection by ID"""
    from app.models import Collection
    return db.query(Collection).filter(Collection.id == collection_id).first()


def get_collection_by_name(db: Session, name: str) -> Optional['Collection']:
    """Fetch collection by name"""
    from app.models import Collection
    return db.query(Collection).filter(Collection.name == name).first()


def list_collections(db: Session, active_only: bool = False) -> List['Collection']:
    """List all collections"""
    from app.models import Collection
    query = db.query(Collection)
    if active_only:
        query = query.filter(Collection.active == True)
    return query.order_by(Collection.created_at).all()


def update_collection(db: Session, collection_id: str, data: CollectionUpdate) -> Optional['Collection']:
    """Update a collection"""
    from app.models import Collection
    
    collection = get_collection(db, collection_id)
    if not collection:
        return None
    
    if data.name is not None:
        # Check for name conflicts
        existing = db.query(Collection).filter(
            Collection.name == data.name,
            Collection.id != collection_id
        ).first()
        if existing:
            raise ValueError(f"Collection name already exists: {data.name}")
        collection.name = data.name
    
    if data.active is not None:
        collection.active = data.active
    
    if data.include_extensions is not None:
        collection.include_extensions = data.include_extensions
    
    if data.exclude_directories is not None:
        collection.exclude_directories = data.exclude_directories
    
    db.commit()
    logger.info(f"Updated collection: {collection_id}")
    return collection


def delete_collection(db: Session, collection_id: str) -> bool:
    """Delete a collection and all its documents"""
    from app.models import Collection
    
    collection = get_collection(db, collection_id)
    if not collection:
        return False
    
    db.delete(collection)
    db.commit()
    logger.info(f"Deleted collection: {collection_id}")
    return True


def get_collection_stats(db: Session, collection_id: str) -> dict:
    """Get statistics for a collection"""
    from app.models import Collection, Document, DocumentStatus
    
    collection = get_collection(db, collection_id)
    if not collection:
        return {}
    
    # Count documents by status
    statuses = {
        DocumentStatus.DISCOVERED: 0,
        DocumentStatus.QUEUED: 0,
        DocumentStatus.PROCESSING: 0,
        DocumentStatus.INDEXED: 0,
        DocumentStatus.FAILED: 0,
        DocumentStatus.SKIPPED: 0,
        DocumentStatus.INACTIVE: 0,
        DocumentStatus.NEEDS_REVIEW: 0,
    }
    
    for status in statuses:
        count = db.query(Document).filter(
            Document.collection_id == collection_id,
            Document.status == status
        ).count()
        statuses[status] = count
    
    total = sum(statuses.values())
    
    return {
        "discovered": statuses[DocumentStatus.DISCOVERED],
        "queued": statuses[DocumentStatus.QUEUED],
        "processing": statuses[DocumentStatus.PROCESSING],
        "indexed": statuses[DocumentStatus.INDEXED],
        "failed": statuses[DocumentStatus.FAILED],
        "skipped": statuses[DocumentStatus.SKIPPED],
        "inactive": statuses[DocumentStatus.INACTIVE],
        "needs_review": statuses[DocumentStatus.NEEDS_REVIEW],
        "total": total,
    }


# ============= JOB ENQUEUE FUNCTIONS =============

def enqueue_extract(db: Session, collection_id: str, priority: int = 0) -> 'Job':
    """Enqueue an EXTRACT_TEXT job for a collection"""
    from app.models import Job, JobType, JobStatus
    from app.jobs import JobQueue
    
    job_queue = JobQueue(db)
    job = job_queue.create_job(collection_id, JobType.EXTRACT_TEXT, priority)
    logger.info(f"Enqueued EXTRACT_TEXT job {job.id} for collection {collection_id}")
    return job


def enqueue_ocr(db: Session, collection_id: str, priority: int = 0) -> 'Job':
    """Enqueue an OCR_PDF job for a collection"""
    from app.models import Job, JobType, JobStatus
    from app.jobs import JobQueue
    
    job_queue = JobQueue(db)
    job = job_queue.create_job(collection_id, JobType.OCR_PDF, priority)
    logger.info(f"Enqueued OCR_PDF job {job.id} for collection {collection_id}")
    return job


def enqueue_json_normalize(db: Session, collection_id: str, priority: int = 0) -> 'Job':
    """Enqueue a NORMALIZE_JSON job for a collection"""
    from app.models import Job, JobType, JobStatus
    from app.jobs import JobQueue
    
    job_queue = JobQueue(db)
    job = job_queue.create_job(collection_id, JobType.NORMALIZE_JSON, priority)
    logger.info(f"Enqueued NORMALIZE_JSON job {job.id} for collection {collection_id}")
    return job


def enqueue_dedupe_scan(db: Session, collection_id: str, priority: int = 0) -> 'Job':
    """Enqueue a DEDUPE_SCAN job for a collection"""
    from app.models import Job, JobType, JobStatus
    from app.jobs import JobQueue
    
    job_queue = JobQueue(db)
    job = job_queue.create_job(collection_id, JobType.DEDUPE_SCAN, priority)
    logger.info(f"Enqueued DEDUPE_SCAN job {job.id} for collection {collection_id}")
    return job


def enqueue_classify_scan(db: Session, collection_id: str, priority: int = 0) -> 'Job':
    """Enqueue a CLASSIFY_SCAN job for a collection"""
    from app.models import Job, JobType, JobStatus
    from app.jobs import JobQueue
    
    job_queue = JobQueue(db)
    job = job_queue.create_job(collection_id, JobType.CLASSIFY_SCAN, priority)
    logger.info(f"Enqueued CLASSIFY_SCAN job {job.id} for collection {collection_id}")
    return job


def enqueue_summarize(db: Session, collection_id: str, priority: int = 0) -> 'Job':
    """Enqueue a SUMMARIZE job for a collection (high-value docs only)"""
    from app.models import Job, JobType, JobStatus
    from app.jobs import JobQueue
    
    job_queue = JobQueue(db)
    job = job_queue.create_job(collection_id, JobType.SUMMARIZE, priority)
    logger.info(f"Enqueued SUMMARIZE job {job.id} for collection {collection_id}")
    return job


def get_job(db: Session, job_id: str) -> Optional['Job']:
    """Get job by ID"""
    from app.models import Job
    return db.query(Job).filter(Job.id == job_id).first()


def list_jobs(db: Session, collection_id: Optional[str] = None, status: Optional[str] = None) -> List['Job']:
    """List jobs with optional filtering"""
    from app.models import Job, JobStatus
    query = db.query(Job)
    if collection_id:
        query = query.filter(Job.collection_id == collection_id)
    if status:
        try:
            status_enum = JobStatus[status.upper()]
            query = query.filter(Job.status == status_enum)
        except KeyError:
            pass
    return query.order_by(Job.created_at.desc()).all()
