"""
Text extraction per file type
"""
import os
import logging
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import pytesseract
    from PIL import Image
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    from pptx import Presentation
    HAS_PPTX = True
except ImportError:
    HAS_PPTX = False

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

from app.classify import FileType, PDFType, is_scanned_pdf
from app.paths import DATA_DIR

logger = logging.getLogger(__name__)

# Configuration
TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
OCR_MAX_PAGES = int(os.getenv("OCR_MAX_PAGES", "200"))
OCR_LANG = os.getenv("OCR_LANG", "eng")
XLSX_MAX_ROWS = int(os.getenv("XLSX_MAX_ROWS", "5000"))
PDF_PAGE_TIMEOUT = int(os.getenv("PDF_PAGE_TIMEOUT", "30"))

# Configure pytesseract
if HAS_TESSERACT:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


@dataclass
class ExtractionResult:
    """Result of text extraction"""
    text: str
    pages: int
    method: str  # "text", "ocr", "native"
    chars_per_page: List[int]
    metadata: Dict
    confidence: float  # 0-1 quality score
    extracted_at: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


def _extract_page_text(page, timeout: int = None) -> Tuple[Optional[str], bool]:
    """Run page.extract_text() with a hard timeout.

    pdfplumber can hang indefinitely on pathological pages (observed on a
    26MB IEEE scan). The extraction runs in a daemon thread so a hung page
    never blocks the worker: we return (None, True) on timeout and abandon
    the thread.

    Returns:
        (text, timed_out)
    """
    import threading

    timeout = PDF_PAGE_TIMEOUT if timeout is None else timeout
    box = {}
    done = threading.Event()

    def _run():
        try:
            box["text"] = page.extract_text()
        except Exception as e:  # noqa: BLE001 - re-raised on the caller thread
            box["error"] = e
        finally:
            done.set()

    t = threading.Thread(target=_run, daemon=True, name="pdfpage")
    t.start()
    if done.wait(timeout):
        if "error" in box:
            raise box["error"]
        return box.get("text"), False
    return None, True


def extract_text_pdf(filepath: Path) -> ExtractionResult:
    """Extract text from a text-based PDF using pdfplumber"""
    if not HAS_PDFPLUMBER:
        raise RuntimeError("pdfplumber not available")
    
    all_text = []
    chars_per_page = []
    metadata = {"page_count": 0, "pages_skipped": 0}
    
    with pdfplumber.open(filepath) as pdf:
        metadata["page_count"] = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            try:
                text, timed_out = _extract_page_text(page)
            except Exception as e:  # noqa: BLE001 - one bad page must not sink the file
                logger.warning(f"Page {i+1} failed for {filepath}: {e}")
                metadata["pages_errored"] = metadata.get("pages_errored", 0) + 1
                metadata.setdefault("page_errors", []).append(f"page {i+1}: {e}")
                text, timed_out = "", False
            if timed_out:
                logger.warning(f"Page {i+1} timed out after {PDF_PAGE_TIMEOUT}s: {filepath}")
                metadata["pages_skipped"] += 1
                text = ""
            all_text.append(f"[Page {i+1}]\n{text or ''}")
            chars_per_page.append(len(text or ""))
    
    full_text = "\n\n".join(all_text)
    total_chars = sum(chars_per_page)
    avg_chars = total_chars / len(chars_per_page) if chars_per_page else 0
    
    # Confidence based on average chars per page
    confidence = min(1.0, avg_chars / 500) if avg_chars > 0 else 0.0
    
    return ExtractionResult(
        text=full_text,
        pages=len(chars_per_page),
        method="text",
        chars_per_page=chars_per_page,
        metadata=metadata,
        confidence=confidence,
        extracted_at=datetime.utcnow().isoformat(),
    )


def extract_text_scanned_pdf(filepath: Path) -> ExtractionResult:
    """Extract text from a scanned PDF using OCR"""
    if not HAS_PDFPLUMBER:
        raise RuntimeError("pdfplumber not available")
    if not HAS_TESSERACT:
        raise RuntimeError("pytesseract not available")
    
    # Check tesseract binary
    global TESSERACT_CMD
    if not Path(TESSERACT_CMD).exists():
        # Try to find in PATH
        import shutil
        found = shutil.which("tesseract")
        if found:
            TESSERACT_CMD = found
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
        else:
            raise RuntimeError(f"Tesseract not found at {TESSERACT_CMD} or in PATH")
    
    all_text = []
    chars_per_page = []
    metadata = {"page_count": 0, "ocr_pages": 0}
    
    with pdfplumber.open(filepath) as pdf:
        metadata["page_count"] = len(pdf.pages)
        pages_to_ocr = min(len(pdf.pages), OCR_MAX_PAGES)
        
        for i in range(pages_to_ocr):
            page = pdf.pages[i]
            # Render page to image
            try:
                im = page.to_image(resolution=300)
                pil_image = im.original
                
                # OCR the image
                text = pytesseract.image_to_string(pil_image, lang=OCR_LANG)
                all_text.append(f"[Page {i+1}]\n{text}")
                chars_per_page.append(len(text))
                metadata["ocr_pages"] += 1
                
            except Exception as e:
                logger.warning(f"OCR failed for page {i+1} of {filepath}: {e}")
                all_text.append(f"[Page {i+1}]\n[OCR FAILED]")
                chars_per_page.append(0)
    
    full_text = "\n\n".join(all_text)
    total_chars = sum(chars_per_page)
    avg_chars = total_chars / len(chars_per_page) if chars_per_page else 0
    
    # Confidence based on OCR output
    confidence = min(1.0, avg_chars / 300) if avg_chars > 0 else 0.0
    
    return ExtractionResult(
        text=full_text,
        pages=len(chars_per_page),
        method="ocr",
        chars_per_page=chars_per_page,
        metadata=metadata,
        confidence=confidence,
        extracted_at=datetime.utcnow().isoformat(),
    )


def extract_text_docx(filepath: Path) -> ExtractionResult:
    """Extract text from DOCX"""
    if not HAS_DOCX:
        raise RuntimeError("python-docx not available")
    
    doc = docx.Document(filepath)
    all_text = []
    chars_per_page = []  # Treat as single "page"
    
    # Paragraphs
    for para in doc.paragraphs:
        if para.text.strip():
            all_text.append(para.text)
    
    # Tables
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text for cell in row.cells)
            if row_text.strip():
                all_text.append(row_text)
    
    full_text = "\n".join(all_text)
    chars = len(full_text)
    chars_per_page.append(chars)
    
    metadata = {
        "paragraph_count": len(doc.paragraphs),
        "table_count": len(doc.tables),
    }
    
    confidence = 1.0 if chars > 0 else 0.0
    
    return ExtractionResult(
        text=full_text,
        pages=1,
        method="native",
        chars_per_page=chars_per_page,
        metadata=metadata,
        confidence=confidence,
        extracted_at=datetime.utcnow().isoformat(),
    )


def extract_text_pptx(filepath: Path) -> ExtractionResult:
    """Extract text from PPTX"""
    if not HAS_PPTX:
        raise RuntimeError("python-pptx not available")
    
    prs = Presentation(filepath)
    all_text = []
    chars_per_page = []
    slide_count = 0
    
    for i, slide in enumerate(prs.slides):
        slide_text = []
        slide_count += 1
        
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    if para.text.strip():
                        slide_text.append(para.text)
            if shape.has_table:
                for row in shape.table.rows:
                    row_text = " | ".join(cell.text for cell in row.cells)
                    if row_text.strip():
                        slide_text.append(row_text)
        
        # Notes (notes_text_frame is None on some slides)
        if slide.has_notes_slide:
            notes_frame = slide.notes_slide.notes_text_frame
            notes = notes_frame.text if notes_frame is not None else ""
            if notes.strip():
                slide_text.append(f"[Notes]\n{notes}")
        
        if slide_text:
            page_text = f"[Slide {i+1}]\n" + "\n".join(slide_text)
            all_text.append(page_text)
            chars_per_page.append(len(page_text))
        else:
            chars_per_page.append(0)
    
    full_text = "\n\n".join(all_text)
    metadata = {"slide_count": slide_count}
    
    total_chars = sum(chars_per_page)
    avg_chars = total_chars / slide_count if slide_count > 0 else 0
    confidence = min(1.0, avg_chars / 200) if avg_chars > 0 else 0.0
    
    return ExtractionResult(
        text=full_text,
        pages=slide_count,
        method="native",
        chars_per_page=chars_per_page,
        metadata=metadata,
        confidence=confidence,
        extracted_at=datetime.utcnow().isoformat(),
    )


def extract_text_xlsx(filepath: Path) -> ExtractionResult:
    """Extract text from XLSX (tab-separated per sheet)"""
    if not HAS_OPENPYXL:
        raise RuntimeError("openpyxl not available")
    
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    all_text = []
    chars_per_page = []
    sheet_count = 0
    chartsheet_names = []

    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        sheet_count += 1
        sheet_text = [f"[Sheet: {sheet_name}]"]
        row_count = 0

        if not hasattr(sheet, "iter_rows"):
            # Chartsheet: chart-only tab with no cell grid
            chartsheet_names.append(sheet_name)
            sheet_text.append("[Chartsheet - chart only, no cell data]")
            all_text.append("\n".join(sheet_text))
            chars_per_page.append(0)
            continue

        for row in sheet.iter_rows(values_only=True):
            row_count += 1
            if row_count > XLSX_MAX_ROWS:
                sheet_text.append(f"[Truncated at {XLSX_MAX_ROWS} rows]")
                break
            
            # Filter None values and convert to string
            cells = [str(c) if c is not None else "" for c in row]
            if any(c.strip() for c in cells):
                sheet_text.append("\t".join(cells))
        
        page_text = "\n".join(sheet_text)
        all_text.append(page_text)
        chars_per_page.append(len(page_text))
    
    wb.close()
    
    full_text = "\n\n".join(all_text)
    metadata = {"sheet_count": sheet_count, "max_rows_per_sheet": XLSX_MAX_ROWS}
    if chartsheet_names:
        metadata["chartsheets"] = chartsheet_names
    
    total_chars = sum(chars_per_page)
    avg_chars = total_chars / sheet_count if sheet_count > 0 else 0
    confidence = min(1.0, avg_chars / 500) if avg_chars > 0 else 0.0
    
    return ExtractionResult(
        text=full_text,
        pages=sheet_count,
        method="native",
        chars_per_page=chars_per_page,
        metadata=metadata,
        confidence=confidence,
        extracted_at=datetime.utcnow().isoformat(),
    )


def extract_text_json(filepath: Path) -> ExtractionResult:
    """Extract and normalize JSON (chat exports)"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except UnicodeDecodeError:
        with open(filepath, 'r', encoding='latin-1') as f:
            data = json.load(f)
    
    # Normalize using jsonnorm
    from app.jsonnorm import normalize_chat_export
    normalized = normalize_chat_export(data)
    
    full_text = normalized.get("text", "")
    metadata = {
        "turn_count": normalized.get("turn_count", 0),
        "format": normalized.get("format", "unknown"),
    }
    chars_per_page = [len(full_text)]
    
    confidence = 1.0 if full_text else 0.0
    
    return ExtractionResult(
        text=full_text,
        pages=1,
        method="native",
        chars_per_page=chars_per_page,
        metadata=metadata,
        confidence=confidence,
        extracted_at=datetime.utcnow().isoformat(),
    )


def extract_text_plain(filepath: Path) -> ExtractionResult:
    """Extract text from plain text/markdown files"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
    except UnicodeDecodeError:
        with open(filepath, 'r', encoding='latin-1') as f:
            text = f.read()
    
    chars_per_page = [len(text)]
    metadata = {"line_count": text.count('\n') + 1}
    confidence = 1.0 if text else 0.0
    
    return ExtractionResult(
        text=text,
        pages=1,
        method="native",
        chars_per_page=chars_per_page,
        metadata=metadata,
        confidence=confidence,
        extracted_at=datetime.utcnow().isoformat(),
    )


def extract_text(filepath: Path, file_type: FileType = None, pdf_type: PDFType = None) -> ExtractionResult:
    """
    Main extraction dispatcher.
    
    Args:
        filepath: Path to file
        file_type: Pre-classified FileType (optional, will classify if not provided)
        pdf_type: Pre-detected PDFType for PDFs (optional)
    
    Returns:
        ExtractionResult
    """
    if file_type is None:
        from app.classify import classify_file
        file_type = classify_file(filepath)
    
    logger.info(f"Extracting {filepath} as {file_type.value}")
    
    try:
        if file_type == FileType.PDF:
            if pdf_type is None:
                pdf_type = is_scanned_pdf(filepath)
            
            if pdf_type == PDFType.SCANNED:
                return extract_text_scanned_pdf(filepath)
            elif pdf_type == PDFType.MIXED:
                # Try text first, then OCR for low-yield pages
                text_result = extract_text_pdf(filepath)
                if text_result.confidence < 0.3:
                    logger.info(f"Low text yield, falling back to OCR for {filepath}")
                    return extract_text_scanned_pdf(filepath)
                return text_result
            else:
                return extract_text_pdf(filepath)
        
        elif file_type == FileType.DOCX:
            return extract_text_docx(filepath)
        
        elif file_type == FileType.PPTX:
            return extract_text_pptx(filepath)
        
        elif file_type == FileType.XLSX:
            return extract_text_xlsx(filepath)
        
        elif file_type == FileType.JSON:
            return extract_text_json(filepath)
        
        elif file_type in (FileType.TEXT, FileType.MARKDOWN):
            return extract_text_plain(filepath)
        
        else:
            # Unsupported type
            return ExtractionResult(
                text="",
                pages=0,
                method="unsupported",
                chars_per_page=[0],
                metadata={"error": f"Unsupported file type: {file_type.value}"},
                confidence=0.0,
                extracted_at=datetime.utcnow().isoformat(),
            )
    
    except Exception as e:
        logger.exception(f"Extraction failed for {filepath}")
        return ExtractionResult(
            text="",
            pages=0,
            method="error",
            chars_per_page=[0],
            metadata={"error": str(e)},
            confidence=0.0,
            extracted_at=datetime.utcnow().isoformat(),
        )


def save_extraction_result(
    filepath: Path,
    result: ExtractionResult,
    content_hash: str,
    extracted_root: Path = None
) -> Tuple[Path, Path]:
    """
    Save extraction result to data/extracted/<hash>.txt and manifest.
    
    Returns:
        (text_file_path, manifest_path)
    """
    if extracted_root is None:
        extracted_root = Path(DATA_DIR) / "extracted"
    
    extracted_root.mkdir(parents=True, exist_ok=True)
    manifests_dir = extracted_root / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    
    # Text file
    text_path = extracted_root / f"{content_hash}.txt"
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write(result.text)
    
    # Manifest
    manifest = {
        "source_path": str(filepath),
        "content_hash": content_hash,
        "pages": result.pages,
        "chars": len(result.text),
        "chars_per_page": result.chars_per_page,
        "method": result.method,
        "confidence": result.confidence,
        "metadata": result.metadata,
        "extracted_at": result.extracted_at,
    }
    manifest_path = manifests_dir / f"{content_hash}.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    
    return text_path, manifest_path


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python -m app.extract <filepath>")
        sys.exit(1)
    
    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)
    
    from app.classify import classify_file, is_scanned_pdf, FileType
    
    ftype = classify_file(filepath)
    pdf_type = None
    if ftype == FileType.PDF:
        pdf_type = is_scanned_pdf(filepath)
    
    result = extract_text(filepath, ftype, pdf_type)
    print(f"Method: {result.method}")
    print(f"Pages: {result.pages}")
    print(f"Chars: {len(result.text)}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Metadata: {result.metadata}")
    print(f"\nFirst 500 chars:\n{result.text[:500]}")