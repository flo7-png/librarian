"""
SQLite ledger schema for Librarian
"""
import os
import sqlite3
import logging

logger = logging.getLogger(__name__)

from app.paths import DATA_DIR
DB_PATH = os.path.join(DATA_DIR, "librarian.db")


def init_db():
    """Initialize SQLite database with baseline schema"""
    os.makedirs(DATA_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Collections table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS collections (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            host_display_path TEXT,
            container_root TEXT NOT NULL,
            recursive BOOLEAN DEFAULT 1,
            active BOOLEAN DEFAULT 1,
            include_extensions TEXT,
            exclude_directories TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Documents table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            collection_id TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            source_path TEXT,
            file_name TEXT,
            extension TEXT,
            size_bytes INTEGER,
            modified_time TIMESTAMP,
            content_hash TEXT,
            status TEXT DEFAULT 'discovered',
            parser TEXT,
            ocr_status TEXT DEFAULT 'not_needed',
            error_message TEXT,
            extraction_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            indexed_at TIMESTAMP,
            last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(collection_id, relative_path),
            FOREIGN KEY(collection_id) REFERENCES collections(id)
        )
    """)
    
    # Chunks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            qdrant_point_id TEXT UNIQUE,
            chunk_index INTEGER,
            text_hash TEXT,
            text_preview TEXT,
            location_json TEXT,
            active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(document_id) REFERENCES documents(id)
        )
    """)
    
    # Jobs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            collection_id TEXT,
            job_type TEXT DEFAULT 'scan',
            status TEXT DEFAULT 'queued',
            priority INTEGER DEFAULT 0,
            progress_total INTEGER DEFAULT 0,
            progress_done INTEGER DEFAULT 0,
            started_at TIMESTAMP,
            finished_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            error_message TEXT,
            FOREIGN KEY(collection_id) REFERENCES collections(id)
        )
    """)
    
    # Job events table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_events (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            document_id TEXT,
            level TEXT DEFAULT 'info',
            event_type TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(job_id) REFERENCES jobs(id),
            FOREIGN KEY(document_id) REFERENCES documents(id)
        )
    """)
    
    # Duplicate groups table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS duplicate_groups (
            id TEXT PRIMARY KEY,
            collection_id TEXT NOT NULL,
            group_type TEXT NOT NULL,
            representative_hash TEXT,
            representative_name TEXT,
            representative_size INTEGER,
            member_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            member_hashes TEXT,
            FOREIGN KEY(collection_id) REFERENCES collections(id)
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {DB_PATH}")


if __name__ == "__main__":
    init_db()
