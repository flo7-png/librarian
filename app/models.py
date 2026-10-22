"""
SQLAlchemy ORM models for Librarian
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum
import uuid

Base = declarative_base()


class Collection(Base):
    """Named source root for indexing"""
    __tablename__ = "collections"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False, index=True)
    host_display_path = Column(String, nullable=False)  # Show to user
    container_root = Column(String, nullable=False)      # /sources/references
    recursive = Column(Boolean, default=True)
    active = Column(Boolean, default=True)
    include_extensions = Column(JSON, default=list)      # ["txt", "pdf", "docx"]
    exclude_directories = Column(JSON, default=list)     # [".git", "__pycache__"]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    documents = relationship("Document", back_populates="collection", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="collection", cascade="all, delete-orphan")


class DocumentStatus(str, enum.Enum):
    DISCOVERED = "discovered"
    QUEUED = "queued"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    SKIPPED = "skipped"
    INACTIVE = "inactive"
    NEEDS_REVIEW = "needs_review"


class OCRStatus(str, enum.Enum):
    NOT_NEEDED = "not_needed"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class Document(Base):
    """File tracked in a collection"""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    collection_id = Column(String, ForeignKey("collections.id"), nullable=False, index=True)
    relative_path = Column(String, nullable=False)  # path/to/file.txt
    source_path = Column(String, nullable=False)     # /sources/references/path/to/file.txt
    file_name = Column(String, nullable=False)
    extension = Column(String)
    size_bytes = Column(Integer)
    modified_time = Column(DateTime)
    content_hash = Column(String, index=True)        # SHA-256 for change detection
    status = Column(Enum(DocumentStatus), default=DocumentStatus.DISCOVERED)
    parser = Column(String)                           # docling, pypdf, etc.
    ocr_status = Column(Enum(OCRStatus), default=OCRStatus.NOT_NEEDED)
    error_message = Column(Text)
    extraction_path = Column(String)                  # /app-data/extracted/<hash>/document.md
    created_at = Column(DateTime, default=datetime.utcnow)
    indexed_at = Column(DateTime)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    
    # Extraction metadata
    quality_score = Column(Integer)                   # 0-100 quality score
    extraction_method = Column(String)                # text, ocr, native
    high_value = Column(Boolean, default=False)       # Flag for Ollama summarization
    page_count = Column(Integer)                      # Number of pages/sheets/slides
    char_count = Column(Integer)                      # Extracted character count
    
    # Foreign key relationship
    collection = relationship("Collection", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    
    __table_args__ = (
        # Unique constraint on collection + relative path
        # (ensures no duplicates per collection)
    )


class Chunk(Base):
    """Extracted text chunk from a document"""
    __tablename__ = "chunks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)
    qdrant_point_id = Column(String, unique=True)      # Reference to Qdrant vector
    chunk_index = Column(Integer)                       # Order within document
    text_hash = Column(String)                          # For deduplication
    text_preview = Column(Text)                         # First 500 chars
    location_json = Column(JSON)                        # {page: 5, section: "Methods"}
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    document = relationship("Document", back_populates="chunks")


class JobType(str, enum.Enum):
    SCAN = "scan"
    INGEST = "ingest"
    REINDEX = "reindex"
    PURGE = "purge"
    RETRY = "retry"
    EXTRACT_TEXT = "extract_text"
    OCR_PDF = "ocr_pdf"
    NORMALIZE_JSON = "normalize_json"
    DEDUPE_SCAN = "dedupe_scan"
    CLASSIFY_SCAN = "classify_scan"
    SUMMARIZE = "summarize"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(Base):
    """Background indexing job"""
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    collection_id = Column(String, ForeignKey("collections.id"), nullable=True, index=True)
    job_type = Column(Enum(JobType), default=JobType.SCAN)
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED)
    priority = Column(Integer, default=0)
    progress_total = Column(Integer, default=0)        # Total files to process
    progress_done = Column(Integer, default=0)         # Files processed
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    error_message = Column(Text)
    
    collection = relationship("Collection", back_populates="jobs")
    events = relationship("JobEvent", back_populates="job", cascade="all, delete-orphan")


class JobEventLevel(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class JobEvent(Base):
    """Audit log for a job"""
    __tablename__ = "job_events"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    level = Column(Enum(JobEventLevel), default=JobEventLevel.INFO)
    event_type = Column(String)                        # "file_skipped", "parse_error", etc.
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("Job", back_populates="events")


class DuplicateGroup(Base):
    """Group of duplicate documents"""
    __tablename__ = "duplicate_groups"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    collection_id = Column(String, ForeignKey("collections.id"), nullable=False, index=True)
    group_type = Column(String, nullable=False)  # "exact_hash" or "filename_size"
    representative_hash = Column(String, nullable=True)  # SHA-256 for exact, None for filename+size
    representative_name = Column(String, nullable=True)  # filename for filename+size
    representative_size = Column(Integer, nullable=True)  # size for filename+size
    member_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    member_hashes = Column(JSON, default=list)  # List of document content_hashes in this group
    
    collection = relationship("Collection")
