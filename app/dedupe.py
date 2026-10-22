"""
Duplicate detection: SHA-256 exact dupes + filename+size near-dupes
"""
import logging
import uuid
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Document, DuplicateGroup

logger = logging.getLogger(__name__)


def find_exact_duplicates(db: Session, collection_id: str) -> List[DuplicateGroup]:
    """
    Find documents with identical SHA-256 hashes within a collection.
    
    Returns list of DuplicateGroup objects (not yet committed).
    """
    # Query for hashes that appear more than once
    dup_hashes = db.query(Document.content_hash).filter(
        Document.collection_id == collection_id,
        Document.content_hash.isnot(None),
        Document.status != 'inactive'
    ).group_by(Document.content_hash).having(func.count(Document.id) > 1).all()
    
    groups = []
    for (hash_val,) in dup_hashes:
        # Get all documents with this hash
        docs = db.query(Document).filter(
            Document.collection_id == collection_id,
            Document.content_hash == hash_val,
            Document.status != 'inactive'
        ).all()
        
        group = DuplicateGroup(
            id=str(uuid.uuid4()),
            collection_id=collection_id,
            group_type="exact_hash",
            representative_hash=hash_val,
            member_count=len(docs),
            member_hashes=[d.content_hash for d in docs],
        )
        groups.append(group)
    
    return groups


def find_filename_size_duplicates(db: Session, collection_id: str) -> List[DuplicateGroup]:
    """
    Find documents with same filename and size (near-duplicates).
    
    Returns list of DuplicateGroup objects (not yet committed).
    """
    # Query for filename+size combinations that appear more than once
    dup_combos = db.query(
        Document.file_name,
        Document.size_bytes
    ).filter(
        Document.collection_id == collection_id,
        Document.size_bytes.isnot(None),
        Document.status != 'inactive'
    ).group_by(Document.file_name, Document.size_bytes).having(func.count(Document.id) > 1).all()
    
    groups = []
    for file_name, size_bytes in dup_combos:
        docs = db.query(Document).filter(
            Document.collection_id == collection_id,
            Document.file_name == file_name,
            Document.size_bytes == size_bytes,
            Document.status != 'inactive'
        ).all()
        
        # Skip if all have same hash (already caught by exact duplicate detection)
        hashes = {d.content_hash for d in docs if d.content_hash}
        if len(hashes) == 1:
            continue
        
        group = DuplicateGroup(
            id=str(uuid.uuid4()),
            collection_id=collection_id,
            group_type="filename_size",
            representative_name=file_name,
            representative_size=size_bytes,
            member_count=len(docs),
            member_hashes=[d.content_hash for d in docs if d.content_hash],
        )
        groups.append(group)
    
    return groups


def run_dedupe_scan(db: Session, collection_id: str) -> Dict:
    """
    Run full deduplication scan for a collection.
    
    Returns summary dict with counts.
    """
    logger.info(f"Starting dedupe scan for collection {collection_id}")
    
    # Clear existing duplicate groups for this collection
    db.query(DuplicateGroup).filter(
        DuplicateGroup.collection_id == collection_id
    ).delete()
    
    # Find exact duplicates
    exact_groups = find_exact_duplicates(db, collection_id)
    for g in exact_groups:
        db.add(g)
    
    # Find filename+size duplicates
    name_groups = find_filename_size_duplicates(db, collection_id)
    for g in name_groups:
        db.add(g)
    
    db.commit()
    
    # Mark documents that are in duplicate groups
    all_group_ids = [g.id for g in exact_groups + name_groups]
    
    # Get all member hashes from exact groups
    exact_hashes = set()
    for g in exact_groups:
        exact_hashes.update(g.member_hashes)
    
    # Mark documents in exact duplicate groups (keep first as primary)
    for hash_val in exact_hashes:
        docs = db.query(Document).filter(
            Document.collection_id == collection_id,
            Document.content_hash == hash_val,
            Document.status != 'inactive'
        ).order_by(Document.created_at).all()
        
        # First doc is primary, rest are duplicates
        for i, doc in enumerate(docs):
            if i == 0:
                doc.error_message = None  # Clear any previous error
            else:
                doc.error_message = f"Duplicate of {docs[0].relative_path} (same SHA-256)"
    
    db.commit()
    
    summary = {
        "exact_duplicate_groups": len(exact_groups),
        "exact_duplicate_files": sum(g.member_count for g in exact_groups),
        "filename_size_groups": len(name_groups),
        "filename_size_files": sum(g.member_count for g in name_groups),
    }
    
    logger.info(f"Dedupe scan complete: {summary}")
    return summary


def get_duplicate_groups(db: Session, collection_id: str) -> List[DuplicateGroup]:
    """Get all duplicate groups for a collection"""
    return db.query(DuplicateGroup).filter(
        DuplicateGroup.collection_id == collection_id
    ).order_by(DuplicateGroup.member_count.desc()).all()


def get_duplicate_report(db: Session, collection_id: str) -> Dict:
    """Generate a human-readable duplicate report"""
    groups = get_duplicate_groups(db, collection_id)
    
    report = {
        "total_groups": len(groups),
        "exact_hash_groups": 0,
        "filename_size_groups": 0,
        "groups": [],
    }
    
    for group in groups:
        if group.group_type == "exact_hash":
            report["exact_hash_groups"] += 1
        else:
            report["filename_size_groups"] += 1
        
        # Get document details for this group
        docs = []
        if group.group_type == "exact_hash":
            docs = db.query(Document).filter(
                Document.collection_id == collection_id,
                Document.content_hash == group.representative_hash,
                Document.status != 'inactive'
            ).all()
        else:
            docs = db.query(Document).filter(
                Document.collection_id == collection_id,
                Document.file_name == group.representative_name,
                Document.size_bytes == group.representative_size,
                Document.status != 'inactive'
            ).all()
        
        group_info = {
            "id": group.id,
            "type": group.group_type,
            "member_count": group.member_count,
            "documents": [
                {
                    "id": d.id,
                    "relative_path": d.relative_path,
                    "size_bytes": d.size_bytes,
                    "content_hash": d.content_hash[:16] + "..." if d.content_hash else None,
                    "is_primary": i == 0,
                }
                for i, d in enumerate(docs)
            ],
        }
        report["groups"].append(group_info)
    
    return report


if __name__ == "__main__":
    import sys
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import os
    
    logging.basicConfig(level=logging.INFO)
    
    from app.models import Base
    from app.paths import DATA_DIR
    DATABASE_URL = f"sqlite:///{DATA_DIR}/librarian.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    if len(sys.argv) < 2:
        print("Usage: python -m app.dedupe <collection_id>")
        sys.exit(1)
    
    collection_id = sys.argv[1]
    
    db = SessionLocal()
    try:
        summary = run_dedupe_scan(db, collection_id)
        print(f"Dedupe scan complete:")
        print(f"  Exact hash groups: {summary['exact_duplicate_groups']} ({summary['exact_duplicate_files']} files)")
        print(f"  Filename+size groups: {summary['filename_size_groups']} ({summary['filename_size_files']} files)")
        
        report = get_duplicate_report(db, collection_id)
        for group in report["groups"]:
            print(f"\nGroup {group['id'][:8]} ({group['type']}, {group['member_count']} files):")
            for doc in group["documents"]:
                marker = "→ PRIMARY" if doc["is_primary"] else "  duplicate"
                print(f"  {marker}: {doc['relative_path']} ({doc['size_bytes']} bytes)")
    finally:
        db.close()