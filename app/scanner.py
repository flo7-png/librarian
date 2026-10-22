"""
Recursive file scanner with SHA-256 change detection
"""
import os
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Default supported extensions
DEFAULT_EXTENSIONS = {
    "text": ["txt", "md", "csv", "json", "yaml", "yml", "html", "htm", "xml", "rtf", "eml"],
    "pdf": ["pdf"],
    "office": ["docx", "doc", "xlsx", "xls", "pptx", "ppt", "odt", "ods", "odp"],
    "image": ["jpg", "jpeg", "png", "gif", "tiff", "tif", "webp"],
}

# Directories to skip
DEFAULT_EXCLUSIONS = {
    ".git", ".hg", ".svn", "CVS",  # VCS
    "__pycache__", ".pytest_cache", ".tox", "node_modules", "venv", ".env",  # Dev
    ".DS_Store", "Thumbs.db", "$RECYCLE.BIN",  # OS
    ".trash", ".cache", "tmp", "temp",  # System
}


class FileScanner:
    """Recursively scan a folder and track files with SHA-256 hashes"""
    
    def __init__(
        self,
        root_path: str,
        include_extensions: Optional[List[str]] = None,
        exclude_directories: Optional[List[str]] = None,
        max_file_size_mb: int = 500,
    ):
        """
        Initialize scanner.
        
        Args:
            root_path: Base folder to scan (e.g., /sources/references)
            include_extensions: List of extensions to include (default: all supported)
            exclude_directories: List of directory names to skip (default: DEFAULT_EXCLUSIONS)
            max_file_size_mb: Skip files larger than this
        """
        self.root_path = Path(root_path)
        self.max_file_size = max_file_size_mb * 1024 * 1024
        
        # Extensions to include (flatten the dict of categories)
        if include_extensions:
            self.include_extensions = set(e.lower().lstrip('.') for e in include_extensions)
        else:
            self.include_extensions = set()
            for exts in DEFAULT_EXTENSIONS.values():
                self.include_extensions.update(exts)
        
        # Directories to exclude
        self.exclude_directories = set(exclude_directories or DEFAULT_EXCLUSIONS)
        
        if not self.root_path.exists():
            raise ValueError(f"Root path does not exist: {root_path}")
        
        if not self.root_path.is_dir():
            raise ValueError(f"Root path is not a directory: {root_path}")
    
    def scan(self) -> List[Dict]:
        """
        Scan the root path recursively and return file metadata.
        
        Returns:
            List of dicts with keys:
            - relative_path: path relative to root_path
            - source_path: absolute path in container
            - file_name: just the filename
            - extension: file extension (without dot)
            - size_bytes: file size
            - modified_time: last modified timestamp
            - content_hash: SHA-256 hash of file content
        """
        files = []
        
        for dirpath, dirnames, filenames in os.walk(self.root_path):
            # Filter out excluded directories (modifies dirnames in-place)
            dirnames[:] = [
                d for d in dirnames
                if d not in self.exclude_directories and not d.startswith('.')
            ]
            
            for filename in filenames:
                # Skip hidden files
                if filename.startswith('.'):
                    continue
                
                filepath = Path(dirpath) / filename
                
                # Get extension
                ext = filepath.suffix.lower().lstrip('.')
                
                # Filter by extension
                if self.include_extensions and ext not in self.include_extensions:
                    continue
                
                # Skip if too large
                try:
                    size = filepath.stat().st_size
                    if size > self.max_file_size:
                        logger.warning(f"Skipping {filepath} (too large: {size} bytes)")
                        continue
                except OSError as e:
                    logger.error(f"Cannot stat {filepath}: {e}")
                    continue
                
                # Compute SHA-256
                try:
                    content_hash = self._compute_sha256(filepath)
                except OSError as e:
                    logger.error(f"Cannot read {filepath}: {e}")
                    continue
                
                # Relative path (for storage in DB)
                relative_path = str(filepath.relative_to(self.root_path)).replace('\\', '/')
                
                # Container path (where it's mounted inside Docker)
                source_path = str(filepath)
                
                # Modified time
                try:
                    modified_time = datetime.fromtimestamp(filepath.stat().st_mtime)
                except OSError:
                    modified_time = None
                
                files.append({
                    "relative_path": relative_path,
                    "source_path": source_path,
                    "file_name": filename,
                    "extension": ext,
                    "size_bytes": size,
                    "modified_time": modified_time,
                    "content_hash": content_hash,
                })
        
        return files
    
    @staticmethod
    def _compute_sha256(filepath: Path, chunk_size: int = 65536) -> str:
        """Compute SHA-256 hash of a file in chunks (memory efficient)"""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                sha256.update(data)
        return sha256.hexdigest()


class ChangeDetector:
    """Detect which files are new or changed based on SHA-256"""
    
    @staticmethod
    def detect_changes(
        current_files: List[Dict],
        previous_hashes: Dict[str, str],
    ) -> Tuple[List[Dict], List[str], List[str]]:
        """
        Compare current scan against previous hashes.
        
        Args:
            current_files: List of dicts from FileScanner.scan()
            previous_hashes: Dict mapping relative_path -> content_hash from DB
        
        Returns:
            Tuple of (new_or_changed, unchanged, deleted)
            - new_or_changed: Files that are new or have changed hash
            - unchanged: Files with same hash as before
            - deleted: Files that were in DB but not in current scan
        """
        current_by_path = {f["relative_path"]: f for f in current_files}
        current_hashes = {f["relative_path"]: f["content_hash"] for f in current_files}
        
        new_or_changed = []
        unchanged = []
        
        for file_data in current_files:
            relative_path = file_data["relative_path"]
            new_hash = file_data["content_hash"]
            old_hash = previous_hashes.get(relative_path)
            
            if old_hash is None or old_hash != new_hash:
                new_or_changed.append(file_data)
            else:
                unchanged.append(file_data)
        
        # Files that were in DB but not in current scan
        deleted = [path for path in previous_hashes if path not in current_by_path]
        
        return new_or_changed, unchanged, deleted
