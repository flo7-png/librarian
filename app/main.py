"""
Librarian API — Main application entry point
"""
import os
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import httpx
from pydantic import BaseModel

# Initialize database
from app.paths import DATA_DIR
DATABASE_URL = f"sqlite:///{DATA_DIR}/librarian.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
from app.models import Base
Base.metadata.create_all(bind=engine)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Librarian", version="0.1.0")

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration from environment
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = os.getenv("QDRANT_PORT", "6333")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def check_qdrant() -> bool:
    """Check if Qdrant is healthy"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"http://{QDRANT_HOST}:{QDRANT_PORT}/health")
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")
        return False


async def check_ollama() -> bool:
    """Check if Ollama is healthy"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Ollama health check failed: {e}")
        return False


@app.get("/api/health")
async def health():
    """Health check endpoint"""
    qdrant_ok = await check_qdrant()
    ollama_ok = await check_ollama()

    status = "ok" if qdrant_ok and ollama_ok else "degraded"
    
    return {
        "status": status,
        "qdrant": "ok" if qdrant_ok else "unreachable",
        "ollama": "ok" if ollama_ok else "unreachable",
    }


# ============= SCHEMAS =============

class JobEnqueueRequest(BaseModel):
    priority: int = 0


class JobResponse(BaseModel):
    job_id: str
    status: str


# ============= COLLECTIONS API =============

from app.models import Collection, Document, DocumentStatus, JobType, Job, JobStatus
from app.services import (
    register_collection, get_collection, list_collections,
    update_collection, delete_collection, get_collection_stats,
    enqueue_extract, enqueue_ocr, enqueue_json_normalize,
    enqueue_dedupe_scan, enqueue_classify_scan, enqueue_summarize,
    get_job, list_jobs,
    CollectionCreate, CollectionUpdate, CollectionResponse
)
from app.jobs import JobQueue, ScanJobProcessor


@app.post("/api/collections", response_model=CollectionResponse)
def create_collection(data: CollectionCreate, db: Session = Depends(get_db)):
    """Register a new collection"""
    try:
        collection = register_collection(db, data)
        return collection
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/collections", response_model=list)
def list_all_collections(active_only: bool = False, db: Session = Depends(get_db)):
    """List all collections"""
    collections = list_collections(db, active_only=active_only)
    return [CollectionResponse.model_validate(c).model_dump() for c in collections]


@app.get("/api/collections/{collection_id}", response_model=CollectionResponse)
def get_one_collection(collection_id: str, db: Session = Depends(get_db)):
    """Get a specific collection"""
    collection = get_collection(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@app.get("/api/collections/{collection_id}/stats")
def get_stats(collection_id: str, db: Session = Depends(get_db)):
    """Get collection statistics"""
    collection = get_collection(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    stats = get_collection_stats(db, collection_id)
    return stats


@app.patch("/api/collections/{collection_id}", response_model=CollectionResponse)
def update_one_collection(
    collection_id: str,
    data: CollectionUpdate,
    db: Session = Depends(get_db),
):
    """Update a collection"""
    try:
        collection = update_collection(db, collection_id, data)
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        return collection
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/collections/{collection_id}")
def delete_one_collection(collection_id: str, db: Session = Depends(get_db)):
    """Delete a collection"""
    success = delete_collection(db, collection_id)
    if not success:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"deleted": collection_id}


@app.post("/api/collections/{collection_id}/scan", response_model=JobResponse)
def scan_collection(collection_id: str, db: Session = Depends(get_db)):
    """Start a scan job for a collection"""
    collection = get_collection(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    job_queue = JobQueue(db)
    job = job_queue.create_job(collection_id, JobType.SCAN)
    
    # Process immediately (in production, this would be async)
    try:
        processor = ScanJobProcessor(db, job_queue)
        processor.process(job.id)
    except Exception as e:
        logger.error(f"Scan job failed: {e}")
        job_queue.fail_job(job.id, str(e))
        raise HTTPException(status_code=500, detail="Scan job failed")
    
    return {"job_id": job.id, "status": job.status.value}


# ============= JOB ENQUEUE ENDPOINTS =============

@app.post("/api/collections/{collection_id}/jobs/extract", response_model=JobResponse)
def enqueue_extract_job(collection_id: str, request: JobEnqueueRequest, db: Session = Depends(get_db)):
    """Enqueue text extraction job for a collection"""
    collection = get_collection(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    job = enqueue_extract(db, collection_id, request.priority)
    return {"job_id": job.id, "status": job.status.value}


@app.post("/api/collections/{collection_id}/jobs/ocr", response_model=JobResponse)
def enqueue_ocr_job(collection_id: str, request: JobEnqueueRequest, db: Session = Depends(get_db)):
    """Enqueue OCR job for scanned PDFs in a collection"""
    collection = get_collection(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    job = enqueue_ocr(db, collection_id, request.priority)
    return {"job_id": job.id, "status": job.status.value}


@app.post("/api/collections/{collection_id}/jobs/normalize-json", response_model=JobResponse)
def enqueue_json_normalize_job(collection_id: str, request: JobEnqueueRequest, db: Session = Depends(get_db)):
    """Enqueue JSON normalization job for chat exports"""
    collection = get_collection(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    job = enqueue_json_normalize(db, collection_id, request.priority)
    return {"job_id": job.id, "status": job.status.value}


@app.post("/api/collections/{collection_id}/jobs/dedupe", response_model=JobResponse)
def enqueue_dedupe_job(collection_id: str, request: JobEnqueueRequest, db: Session = Depends(get_db)):
    """Enqueue deduplication scan job"""
    collection = get_collection(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    job = enqueue_dedupe_scan(db, collection_id, request.priority)
    return {"job_id": job.id, "status": job.status.value}


@app.post("/api/collections/{collection_id}/jobs/classify", response_model=JobResponse)
def enqueue_classify_job(collection_id: str, request: JobEnqueueRequest, db: Session = Depends(get_db)):
    """Enqueue classification scan job"""
    collection = get_collection(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    job = enqueue_classify_scan(db, collection_id, request.priority)
    return {"job_id": job.id, "status": job.status.value}


@app.post("/api/collections/{collection_id}/jobs/summarize", response_model=JobResponse)
def enqueue_summarize_job(collection_id: str, request: JobEnqueueRequest, db: Session = Depends(get_db)):
    """Enqueue summarization job for high-value documents"""
    collection = get_collection(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    job = enqueue_summarize(db, collection_id, request.priority)
    return {"job_id": job.id, "status": job.status.value}


@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Get job status and details"""
    job = get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "id": job.id,
        "collection_id": job.collection_id,
        "job_type": job.job_type.value,
        "status": job.status.value,
        "priority": job.priority,
        "progress_total": job.progress_total,
        "progress_done": job.progress_done,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "created_at": job.created_at.isoformat(),
        "error_message": job.error_message,
    }


@app.get("/api/jobs")
def list_all_jobs(
    collection_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List jobs with optional filtering"""
    jobs = list_jobs(db, collection_id, status)
    return [
        {
            "id": job.id,
            "collection_id": job.collection_id,
            "job_type": job.job_type.value,
            "status": job.status.value,
            "priority": job.priority,
            "progress_total": job.progress_total,
            "progress_done": job.progress_done,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "created_at": job.created_at.isoformat(),
            "error_message": job.error_message,
        }
        for job in jobs
    ]


@app.get("/api/documents")
def list_documents(
    collection_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List documents with optional filtering"""
    query = db.query(Document)
    
    if collection_id:
        query = query.filter(Document.collection_id == collection_id)
    
    if status:
        try:
            status_enum = DocumentStatus[status.upper()]
            query = query.filter(Document.status == status_enum)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    documents = query.order_by(Document.created_at.desc()).all()
    return [
        {
            "id": doc.id,
            "relative_path": doc.relative_path,
            "file_name": doc.file_name,
            "status": doc.status.value,
            "size_bytes": doc.size_bytes,
            "quality_score": doc.quality_score,
            "extraction_method": doc.extraction_method,
            "high_value": doc.high_value,
            "page_count": doc.page_count,
            "char_count": doc.char_count,
            "created_at": doc.created_at.isoformat(),
        }
        for doc in documents
    ]


@app.post("/api/documents/{doc_id}/high-value")
def set_high_value(doc_id: str, high_value: bool = True, db: Session = Depends(get_db)):
    """Mark a document as high-value for summarization"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc.high_value = high_value
    db.commit()
    return {"id": doc.id, "high_value": doc.high_value}


@app.get("/")
async def root():
    """Root endpoint — UI will be served here"""
    return {"message": "Librarian API is running. Visit /docs for API documentation."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
