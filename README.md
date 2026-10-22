# Librarian — Local-First Document Extraction Pipeline

A Windows-first, fully local document indexing and extraction system. No cloud services, no paid APIs, no SaaS — everything runs on your machine using open-source tools.

## Features

- **Collection Registry** — Manage multiple source roots (D:\References, D:\Books, etc.)
- **Recursive Scanner** — Discovers files with extension filtering and exclusion rules
- **SHA-256 Change Detection** — Incremental indexing (only process new/changed files)
- **File Classification** — By extension + magic bytes; detects scanned vs text PDFs
- **Duplicate Detection** — Exact SHA-256 matches + filename+size near-dupes
- **Text Extraction** — PDF (pdfplumber), DOCX, PPTX, XLSX, JSON (chat exports), text/MD
- **Scanned PDF OCR** — Local Tesseract (eng) via pytesseract, capped pages
- **Quality Gate** — Scores extracted text 0-1; below threshold → `needs_review`
- **Local Summarization** — Ollama (phi4-mini) for high-value documents only
- **Job Queue + Worker** — Async processing with progress tracking
- **REST API + CLI** — Full programmatic and command-line control
- **Triage & Repair** — Local health triage and recovery for broken/junk files (see below)

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Collections │────▶│   Scanner   │────▶│  Documents  │
│  (roots)    │     │  (SHA-256)  │     │  (registry) │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌─────────────┐     ┌──────▼──────┐
                    │  Worker     │◀────│  Job Queue  │
                    │ (dispatch)  │     │  (SQLite)   │
                    └──────┬──────┘     └─────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
    ┌─────────┐      ┌──────────┐      ┌───────────┐
    │ Extract │      │   OCR    │      │  Dedupes  │
    │ (fast)  │      │ (slow)   │      │  (fast)   │
    └────┬────┘      └────┬─────┘      └─────┬─────┘
         │                │                  │
         ▼                ▼                  ▼
   ┌──────────┐     ┌──────────┐       ┌──────────┐
   │ Quality  │     │ Quality  │       │  Report  │
   │  Gate    │     │  Gate    │       │          │
   └────┬─────┘     └────┬─────┘       └──────────┘
        │                │
        ▼                ▼
   ┌────────────────────────────┐
   │   data/extracted/<hash>    │
   │   .txt + manifests/*.json  │
   └────────────────────────────┘
```

## Installation

### Prerequisites

1. **Python 3.11+** — `python -m pip install --upgrade pip`
2. **Tesseract OCR** — Download installer from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
   - Default install: `C:\Program Files\Tesseract-OCR\tesseract.exe`
   - Add to PATH or set `TESSERACT_CMD` env var
3. **Ollama** — [ollama.com](https://ollama.com) for local LLM summarization
   - `ollama pull phi4-mini:3.8b` (default summarization model)

### Quick Install

```powershell
cd D:\AI\librarian
pip install -r requirements.txt
```

The `requirements.txt` includes:
- `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`
- `pdfplumber`, `pypdf`, `pymupdf`, `python-docx`, `python-pptx`, `openpyxl`
- `pytesseract`, `pandas`, `docling`, `marker-pdf`, `requests`, `httpx`

### Environment Variables (`.env`)

```ini
DATA_DIR=D:\AI\librarian\data          # Database + extracted text
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
OCR_MAX_PAGES=200                       # Max pages to OCR per PDF
QUALITY_THRESHOLD=0.35                  # Quality gate threshold
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_SUMMARIZE_MODEL=phi4-mini:3.8b
```

## Quickstart

### 1. Register a Collection

```powershell
# CLI
python -m app.cli collection-create references D:\References D:\References

# Or via API
curl -X POST http://localhost:8080/api/collections ^
  -H "Content-Type: application/json" ^
  -d '{"name":"references","container_root":"D:\References","host_display_path":"D:\References"}'
```

### 2. Scan the Collection

```powershell
python -m app.cli scan <collection-id>

# Or API
curl -X POST http://localhost:8080/api/collections/<id>/scan
```

### 3. Classify Documents

```powershell
python -m app.cli classify <collection-id>

# API
curl -X POST http://localhost:8080/api/collections/<id>/jobs/classify
```

### 4. Extract All Text

```powershell
# Process immediately
python -m app.cli extract <collection-id>

# Or queue for worker
python -m app.cli extract-all --queue
```

### 5. Run OCR on Scanned PDFs

```powershell
python -m app.cli ocr <collection-id>
```

### 6. Find Duplicates

```powershell
python -m app.cli dedupe <collection-id>
```

### 7. Review Quality

```powershell
python -m app.cli quality <document-id>
```

### 8. Summarize High-Value Docs

```powershell
# Mark as high-value + summarize
python -m app.cli summarize <document-id> --high-value
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `collection-create <name> <root> <display>` | Register new collection |
| `collection-list` | List all collections |
| `collection-stats <id>` | Show document counts by status |
| `scan <id>` | Scan collection for files |
| `classify <id>` | Classify all documents |
| `dedupe <id>` | Find exact + near duplicates |
| `extract <id> [doc-id]` | Extract text (all or single) |
| `ocr <id> [doc-id]` | OCR scanned PDFs |
| `extract-all [id] [--queue]` | Queue extraction for all/all-one |
| `quality <doc-id>` | Show quality assessment |
| `summarize <doc-id> [--high-value]` | Ollama summarization |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/collections` | Create collection |
| `GET` | `/api/collections` | List collections |
| `GET` | `/api/collections/{id}` | Get collection |
| `GET` | `/api/collections/{id}/stats` | Collection statistics |
| `POST` | `/api/collections/{id}/scan` | Scan collection |
| `POST` | `/api/collections/{id}/jobs/extract` | Queue extraction |
| `POST` | `/api/collections/{id}/jobs/ocr` | Queue OCR |
| `POST` | `/api/collections/{id}/jobs/normalize-json` | Queue JSON normalization |
| `POST` | `/api/collections/{id}/jobs/dedupe` | Queue dedupe scan |
| `POST` | `/api/collections/{id}/jobs/classify` | Queue classification |
| `POST` | `/api/collections/{id}/jobs/summarize` | Queue summarization |
| `GET` | `/api/jobs/{id}` | Job status |
| `GET` | `/api/documents` | List documents |
| `POST` | `/api/documents/{id}/high-value` | Toggle high-value flag |

## Output Structure

```
data/
├── librarian.db              # SQLite database
└── extracted/
    ├── <sha256>.txt          # Extracted text per document
    └── manifests/
        └── <sha256>.json     # Extraction metadata
logs/
└── extractor.log             # Extraction logs
```

## Local-Only Guarantee

- **No network calls** except `localhost:11434` (Ollama)
- **No model downloads** — uses already-pulled Ollama models
- **No cloud OCR** — Tesseract runs locally
- **No telemetry** — zero external requests
- **All data stays in** `D:\AI\librarian\data\` and `logs\`

## Development

### Run Tests

```powershell
python -m pytest tests/ -v
```

### Run API Server

```powershell
python -m app.main
# Visit http://localhost:8080/docs
```

### Run Workers

```powershell
# Fast queue (extraction, classification, dedupe, JSON, summarization)
python -m app.worker --queue fast

# Slow queue (OCR)
python -m app.worker --queue slow
```

## Core workflow

1. inventory files and compute hashes
2. classify document types
3. deduplicate by content hash
4. detect low-quality or broken files
5. extract text or OCR as required
6. normalize outputs to a consistent schema
7. run review and quality gates
8. only then send high-value docs to a local LLM

## Error triage and repair workflow

The repo includes a built-in local triage and repair layer for common extraction failures seen in messy source collections.

### Quick commands

```powershell
python .\scripts\triage_document_health.py
python .\scripts\repair_bad_files.py --dry-run
```

This creates a review report under `data/reviews/needs_review.json` and a suggested repair plan for files needing local action.

### What the triage stage checks

- `~$` lock/temp Office files
- zero-byte files
- duplicate files by SHA-256
- invalid ZIP-based Office files (`.docx`, `.pptx`, `.xlsx`)
- PDFs that fail to parse or are truncated
- files that extract zero characters
- files that fail the quality gate

### Repair guidance

Use local, open-source tools before any cloud processing:

- qpdf for PDF validation/repair
- Ghostscript for PDF rewrite and rendering
- Tesseract for OCR fallback
- LibreOffice headless for rescuing damaged Office files
- 7-Zip for ZIP validation and file inspection
- jdupes for duplicate detection

See `docs/REPAIR_WORKFLOW.md` for the full operational plan and links to project pages.

## Repository Layout (full)

```text
librarian/
├── AGENTS.md
├── README.md
├── requirements.txt
├── pyproject.toml
├── .opencode/
│   └── instructions.md
├── config/
│   ├── extraction_targets.yaml
│   ├── review_rules.yaml
│   └── tool_manifest.yaml
├── docs/
│   ├── PROJECT_DECISIONS.md
│   ├── REPAIR_WORKFLOW.md
│   ├── TOOLCHAIN.md
│   └── WINDOWS_INSTALL.md
├── app/                    # FastAPI service + worker layer
├── scripts/
│   ├── build_manifest.py
│   ├── classify_documents.py
│   ├── extract_pdf_text.py
│   ├── extract_scanned_pdf.py
│   ├── extract_office.py
│   ├── normalize_json_exports.py
│   ├── quality_gate.py
│   ├── repair_bad_files.py
│   ├── scan_inventory.py
│   ├── triage_document_health.py
│   ├── needs_review_report.py
│   ├── convert-legacy.ps1
│   └── sync-main.ps1
├── src/
│   ├── __init__.py
│   ├── chunking.py
│   ├── classify.py
│   ├── config.py
│   ├── dedupe.py
│   ├── extractors/
│   ├── inventory.py
│   ├── llm_local.py
│   ├── normalize.py
│   └── review.py
├── tests/
├── reports/
├── data/
│   ├── input/
│   ├── manifests/
│   ├── extracted/
│   ├── chunks/
│   └── reviews/
├── logs/
└── .gitignore
```

## OpenCode integration guidance

OpenCode should follow the repo in this order:

1. inventory files and hash them
2. classify file types
3. triage health and identify repairable issues
4. quarantine or exclude lock/temp junk files
5. repair or OCR recoverable files locally
6. apply extraction and normalization passes
7. quality gate review output
8. only then send high-value docs to a local LLM

The repo remains intentionally local, deterministic, and transparent.

## License

MIT — Use freely for personal or commercial purposes.
