"""
Integration tests for Milestone 2: Recursive Indexing
Run with: pytest tests/test_milestone2.py -v
"""
import pytest
import tempfile
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, Collection, Document, DocumentStatus, JobType, JobStatus
from app.services import register_collection, CollectionCreate, get_collection_stats
from app.scanner import FileScanner, ChangeDetector
from app.jobs import JobQueue, ScanJobProcessor


@pytest.fixture
def temp_dir():
    """Create a temporary directory with test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test file structure
        Path(tmpdir, "docs").mkdir()
        Path(tmpdir, "docs", "file1.txt").write_text("Content 1")
        Path(tmpdir, "docs", "file2.md").write_text("# Markdown\n\nContent 2")
        Path(tmpdir, "docs", "subdir").mkdir()
        Path(tmpdir, "docs", "subdir", "file3.pdf").write_text("PDF content")
        
        # Create ignored files
        Path(tmpdir, "docs", ".git").mkdir()
        Path(tmpdir, "docs", ".git", "config").write_text("git config")
        Path(tmpdir, "__pycache__").mkdir()
        Path(tmpdir, "__pycache__", "cache.pyc").write_text("cache")
        
        yield tmpdir


@pytest.fixture
def test_db():
    """Create a test database"""
    DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_scanner_discovers_files(temp_dir):
    """Test that FileScanner recursively discovers files"""
    scanner = FileScanner(temp_dir)
    files = scanner.scan()
    
    # Should find 3 files (not the .git or __pycache__ ones)
    assert len(files) == 3
    
    file_names = {f["file_name"] for f in files}
    assert "file1.txt" in file_names
    assert "file2.md" in file_names
    assert "file3.pdf" in file_names
    
    # Check structure
    assert any(f["relative_path"] == "docs/file1.txt" for f in files)
    assert any(f["relative_path"] == "docs/subdir/file3.pdf" for f in files)


def test_scanner_computes_sha256(temp_dir):
    """Test that SHA-256 hashes are computed"""
    scanner = FileScanner(temp_dir)
    files = scanner.scan()
    
    for file_data in files:
        # Hash should be 64 hex characters (SHA-256)
        assert len(file_data["content_hash"]) == 64
        assert all(c in "0123456789abcdef" for c in file_data["content_hash"])


def test_scanner_respects_extension_filter(temp_dir):
    """Test that include_extensions filter works"""
    scanner = FileScanner(temp_dir, include_extensions=["txt", "md"])
    files = scanner.scan()
    
    # Should only find txt and md files
    assert len(files) == 2
    file_names = {f["file_name"] for f in files}
    assert "file1.txt" in file_names
    assert "file2.md" in file_names
    assert "file3.pdf" not in file_names


def test_change_detector_finds_new_files(temp_dir):
    """Test change detection for new files"""
    scanner = FileScanner(temp_dir)
    current = scanner.scan()
    previous = {}  # Empty — all files are "new"
    
    new_or_changed, unchanged, deleted = ChangeDetector.detect_changes(current, previous)
    
    assert len(new_or_changed) == 3
    assert len(unchanged) == 0
    assert len(deleted) == 0


def test_change_detector_finds_unchanged_files(temp_dir):
    """Test change detection for unchanged files"""
    scanner = FileScanner(temp_dir)
    current = scanner.scan()
    
    # Build previous hashes from current scan
    previous = {f["relative_path"]: f["content_hash"] for f in current}
    
    new_or_changed, unchanged, deleted = ChangeDetector.detect_changes(current, previous)
    
    assert len(new_or_changed) == 0
    assert len(unchanged) == 3
    assert len(deleted) == 0


def test_collection_registration(test_db):
    """Test collection registration"""
    data = CollectionCreate(
        name="test-collection",
        host_display_path="/tmp/test",
        container_root="/sources/test",
    )
    
    collection = register_collection(test_db, data)
    
    assert collection.name == "test-collection"
    assert collection.container_root == "/sources/test"
    assert collection.active == True


def test_scan_job_creates_documents(test_db, temp_dir):
    """Test that scan job creates document records"""
    # Register collection
    data = CollectionCreate(
        name="test-scan",
        host_display_path=temp_dir,
        container_root=temp_dir,
    )
    collection = register_collection(test_db, data)
    
    # Create and run scan job
    job_queue = JobQueue(test_db)
    job = job_queue.create_job(collection.id, JobType.SCAN)
    
    processor = ScanJobProcessor(test_db, job_queue)
    processor.process(job.id)
    
    # Verify job completed
    job = job_queue.get_job(job.id)
    assert job.status == JobStatus.COMPLETED
    
    # Verify documents were created
    docs = test_db.query(Document).filter(
        Document.collection_id == collection.id
    ).all()
    assert len(docs) == 3
    
    # Verify statuses
    assert all(doc.status == DocumentStatus.DISCOVERED for doc in docs)


def test_collection_stats(test_db, temp_dir):
    """Test collection statistics"""
    # Register and scan
    data = CollectionCreate(
        name="test-stats",
        host_display_path=temp_dir,
        container_root=temp_dir,
    )
    collection = register_collection(test_db, data)
    
    job_queue = JobQueue(test_db)
    job = job_queue.create_job(collection.id, JobType.SCAN)
    
    processor = ScanJobProcessor(test_db, job_queue)
    processor.process(job.id)
    
    # Get stats
    stats = get_collection_stats(test_db, collection.id)
    
    assert stats["total"] == 3
    assert stats["discovered"] == 3
    assert stats["indexed"] == 0
    assert stats["failed"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
