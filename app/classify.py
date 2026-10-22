"""
File classification by extension + magic sniff
"""
import os
import logging
from pathlib import Path
from typing import Optional
from enum import Enum

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

logger = logging.getLogger(__name__)


class FileType(str, Enum):
    """Classification categories"""
    PDF = "pdf"
    TEXT = "text"
    MARKDOWN = "markdown"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    JSON = "json"
    VIDEO = "video"
    ARCHIVE = "archive"
    IMAGE = "image"
    OTHER = "other"


class PDFType(str, Enum):
    """PDF sub-classification"""
    TEXT = "text"       # Extractable text
    SCANNED = "scanned" # Needs OCR
    MIXED = "mixed"     # Both text and images


# Extension to FileType mapping
EXTENSION_MAP = {
    # Text
    "txt": FileType.TEXT,
    "md": FileType.MARKDOWN,
    "markdown": FileType.MARKDOWN,
    "csv": FileType.TEXT,
    "yaml": FileType.TEXT,
    "yml": FileType.TEXT,
    "html": FileType.TEXT,
    "htm": FileType.TEXT,
    "xml": FileType.TEXT,
    "rtf": FileType.TEXT,
    "eml": FileType.TEXT,
    "log": FileType.TEXT,
    "ini": FileType.TEXT,
    "cfg": FileType.TEXT,
    "conf": FileType.TEXT,
    "py": FileType.TEXT,
    "js": FileType.TEXT,
    "ts": FileType.TEXT,
    "java": FileType.TEXT,
    "cpp": FileType.TEXT,
    "c": FileType.TEXT,
    "h": FileType.TEXT,
    "cs": FileType.TEXT,
    "go": FileType.TEXT,
    "rs": FileType.TEXT,
    "rb": FileType.TEXT,
    "php": FileType.TEXT,
    "sh": FileType.TEXT,
    "bat": FileType.TEXT,
    "ps1": FileType.TEXT,
    "sql": FileType.TEXT,
    "json": FileType.JSON,
    # PDF
    "pdf": FileType.PDF,
    # Office
    "docx": FileType.DOCX,
    "doc": FileType.DOCX,
    "pptx": FileType.PPTX,
    "ppt": FileType.PPTX,
    "xlsx": FileType.XLSX,
    "xls": FileType.XLSX,
    "odt": FileType.TEXT,
    "ods": FileType.TEXT,
    "odp": FileType.TEXT,
    # Video
    "mp4": FileType.VIDEO,
    "mkv": FileType.VIDEO,
    "avi": FileType.VIDEO,
    "mov": FileType.VIDEO,
    "webm": FileType.VIDEO,
    "flv": FileType.VIDEO,
    "wmv": FileType.VIDEO,
    # Archive
    "zip": FileType.ARCHIVE,
    "tar": FileType.ARCHIVE,
    "gz": FileType.ARCHIVE,
    "bz2": FileType.ARCHIVE,
    "xz": FileType.ARCHIVE,
    "7z": FileType.ARCHIVE,
    "rar": FileType.ARCHIVE,
    # Image
    "jpg": FileType.IMAGE,
    "jpeg": FileType.IMAGE,
    "png": FileType.IMAGE,
    "gif": FileType.IMAGE,
    "tiff": FileType.IMAGE,
    "tif": FileType.IMAGE,
    "webp": FileType.IMAGE,
    "bmp": FileType.IMAGE,
    "ico": FileType.IMAGE,
}


# Magic MIME type to FileType mapping (fallback when extension unknown)
MAGIC_MAP = {
    "application/pdf": FileType.PDF,
    "text/plain": FileType.TEXT,
    "text/markdown": FileType.MARKDOWN,
    "text/csv": FileType.TEXT,
    "text/html": FileType.TEXT,
    "text/xml": FileType.TEXT,
    "application/json": FileType.JSON,
    "application/xml": FileType.TEXT,
    "application/msword": FileType.DOCX,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileType.DOCX,
    "application/vnd.ms-powerpoint": FileType.PPTX,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": FileType.PPTX,
    "application/vnd.ms-excel": FileType.XLSX,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": FileType.XLSX,
    "video/mp4": FileType.VIDEO,
    "video/x-matroska": FileType.VIDEO,
    "video/quicktime": FileType.VIDEO,
    "video/x-msvideo": FileType.VIDEO,
    "application/zip": FileType.ARCHIVE,
    "application/x-tar": FileType.ARCHIVE,
    "application/gzip": FileType.ARCHIVE,
    "application/x-7z-compressed": FileType.ARCHIVE,
    "application/x-rar-compressed": FileType.ARCHIVE,
    "image/jpeg": FileType.IMAGE,
    "image/png": FileType.IMAGE,
    "image/gif": FileType.IMAGE,
    "image/tiff": FileType.IMAGE,
    "image/webp": FileType.IMAGE,
}


# Scanned PDF detection threshold (chars per page)
SCANNED_PDF_CHAR_THRESHOLD = int(os.getenv("SCANNED_PDF_CHAR_THRESHOLD", "100"))
SCANNED_PDF_MAX_PAGES = int(os.getenv("SCANNED_PDF_MAX_PAGES", "3"))


def classify_by_extension(filepath: Path) -> FileType:
    """Classify file by extension"""
    ext = filepath.suffix.lower().lstrip('.')
    return EXTENSION_MAP.get(ext, FileType.OTHER)


def classify_by_magic(filepath: Path) -> Optional[FileType]:
    """Classify file by magic bytes (MIME type)"""
    if not HAS_MAGIC:
        return None
    
    try:
        mime = magic.from_file(str(filepath), mime=True)
        return MAGIC_MAP.get(mime)
    except Exception as e:
        logger.debug(f"Magic detection failed for {filepath}: {e}")
        return None


def classify_file(filepath: Path) -> FileType:
    """
    Classify a file by extension first, then magic bytes as fallback.
    """
    # Try extension first
    ftype = classify_by_extension(filepath)
    if ftype != FileType.OTHER:
        return ftype
    
    # Fallback to magic
    ftype = classify_by_magic(filepath)
    if ftype:
        return ftype
    
    return FileType.OTHER


def is_scanned_pdf(filepath: Path, max_pages: int = None, char_threshold: int = None) -> PDFType:
    """
    Detect if a PDF is scanned (image-based) vs text-extractable.
    
    Args:
        filepath: Path to PDF file
        max_pages: Max pages to check (default from env SCANNED_PDF_MAX_PAGES)
        char_threshold: Min chars per page to consider text (default from env SCANNED_PDF_CHAR_THRESHOLD)
    
    Returns:
        PDFType.TEXT, PDFType.SCANNED, or PDFType.MIXED
    """
    if not HAS_PDFPLUMBER:
        logger.warning("pdfplumber not available, assuming text PDF")
        return PDFType.TEXT
    
    max_pages = max_pages or SCANNED_PDF_MAX_PAGES
    char_threshold = char_threshold or SCANNED_PDF_CHAR_THRESHOLD
    
    try:
        with pdfplumber.open(filepath) as pdf:
            pages_to_check = min(len(pdf.pages), max_pages)
            if pages_to_check == 0:
                return PDFType.TEXT
            
            text_pages = 0
            scanned_pages = 0
            
            for i in range(pages_to_check):
                page = pdf.pages[i]
                text = page.extract_text() or ""
                char_count = len(text.strip())
                
                if char_count >= char_threshold:
                    text_pages += 1
                else:
                    scanned_pages += 1
            
            if text_pages == 0:
                return PDFType.SCANNED
            elif scanned_pages == 0:
                return PDFType.TEXT
            else:
                return PDFType.MIXED
                
    except Exception as e:
        logger.error(f"Failed to analyze PDF {filepath}: {e}")
        # Default to text on error
        return PDFType.TEXT


def get_file_type_info(filepath: Path) -> dict:
    """
    Get comprehensive file type information.
    """
    ext_type = classify_by_extension(filepath)
    magic_type = classify_by_magic(filepath)
    
    result = {
        "extension_type": ext_type.value,
        "magic_type": magic_type.value if magic_type else None,
        "final_type": ext_type.value if ext_type != FileType.OTHER else (magic_type.value if magic_type else FileType.OTHER.value),
    }
    
    # For PDFs, add scanned detection
    if result["final_type"] == FileType.PDF.value:
        pdf_type = is_scanned_pdf(filepath)
        result["pdf_type"] = pdf_type.value
        result["needs_ocr"] = pdf_type in (PDFType.SCANNED, PDFType.MIXED)
    
    return result


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python -m app.classify <filepath>")
        sys.exit(1)
    
    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)
    
    info = get_file_type_info(filepath)
    print(f"File: {filepath}")
    for k, v in info.items():
        print(f"  {k}: {v}")