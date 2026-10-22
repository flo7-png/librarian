# AGENTS.md — Librarian Repository Conventions

This document defines the coding conventions, architecture patterns, and operational rules for agents working on the Librarian codebase.

## Repository Sync (mandatory before any work)

Before doing any work in this repo, always sync to the latest `main`
branch and confirm the working tree is clean:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\sync-main.ps1
```

Manual equivalent (what the script runs):

```powershell
git fetch origin main
git checkout main
git pull --ff-only origin main
git status   # must print nothing
```

Exit codes: `0` synced + clean (safe to start) · `1` dirty tree or no commits
yet (resolve first — never work on top of uncommitted changes) · `2` no
`origin` remote (`git remote add origin <url>`) · `3/4/5` fetch/checkout/pull
failed · `6` dirty after sync. Do not start any task while the script exits
non-zero.

## Core Principles

1. **Local-First, No Cloud** — Zero external network calls. Only localhost Ollama (port 11434) is permitted.
2. **Windows-First Paths** — Use `pathlib.Path` everywhere. No hardcoded `/app-data` — use `DATA_DIR` env var.
3. **Job-Driven Architecture** — All long-running work goes through the job queue. Workers dispatch via job type.
4. **CLI-First** — Every feature must have a `python -m app.cli` command. API mirrors CLI.
5. **Test with pytest** — Unit tests in `tests/`, fixtures in temp dirs, no external dependencies.
6. **Outputs Under `data/` and `logs/`** — Never write outside these directories.

## Code Style

### Python Conventions
- **Type hints** on all public functions
- **Dataclasses** for structured results (`@dataclass`)
- **SQLAlchemy 2.0 style** — `Base = declarative_base()`, `Column`, `relationship`
- **Pydantic v2** — `BaseModel` with `model_validate`/`model_dump`
- **Logging** — `logging.getLogger(__name__)` at module top
- **Error handling** — Catch specific exceptions, log with `logger.exception()`, return structured errors

### Module Organization
```
app/
├── __init__.py
├── main.py           # FastAPI app + endpoints
├── models.py         # SQLAlchemy ORM (single source of truth)
├── db.py             # Raw SQLite init (for Docker)
├── scanner.py        # FileScanner, ChangeDetector
├── jobs.py           # JobQueue, ScanJobProcessor
├── services.py       # Business logic (register, enqueue, stats)
├── worker.py         # Worker with dispatch table
├── cli.py            # Typer-style CLI commands
├── classify.py       # File classification
├── dedupe.py         # Duplicate detection
├── extract.py        # Text extraction per type
├── jsonnorm.py       # Chat export normalization
├── quality.py        # Quality gate scoring
└── ollama_client.py  # Local Ollama wrapper
```

### Database Patterns
- **Models in `models.py` only** — Single source of truth
- **Migrations** — Use `alembic` for schema changes (not done yet; additive columns OK)
- **Raw SQLite in `db.py`** — Only for Docker init; matches models
- **Sessions** — `SessionLocal` from `main.py`/`cli.py`; pass `db: Session` to services

### Job Types (extend in `models.py:JobType`)
```
SCAN, INGEST, REINDEX, PURGE, RETRY,
EXTRACT_TEXT, OCR_PDF, NORMALIZE_JSON,
DEDUPE_SCAN, CLASSIFY_SCAN, SUMMARIZE
```

### Document Statuses (extend in `models.py:DocumentStatus`)
```
DISCOVERED, QUEUED, PROCESSING, INDEXED,
FAILED, SKIPPED, INACTIVE, NEEDS_REVIEW
```

### Adding a New Job Type
1. Add to `JobType` enum in `models.py`
2. Add handler in `Worker.handlers` dict in `worker.py`
3. Add to appropriate queue (`fast` or `slow`) in `Worker.handled_types`
4. Add `enqueue_*` function in `services.py`
5. Add CLI command in `cli.py`
6. Add API endpoint in `main.py`
7. Add test in `tests/test_extraction.py`

## Configuration

All config via environment variables (`.env` file or shell):
- `DATA_DIR` — Root for database + extracted text (default: `/app-data` in Docker, `D:\AI\librarian\data` locally)
- `TESSERACT_CMD` — Full path to tesseract.exe (default: `C:\Program Files\Tesseract-OCR\tesseract.exe`)
- `OCR_MAX_PAGES` — Max pages per PDF to OCR (default: 200)
- `OCR_LANG` — Tesseract language (default: `eng`)
- `QUALITY_THRESHOLD` — Quality gate threshold 0-1 (default: 0.35)
- `OLLAMA_HOST` — Ollama API (default: `http://127.0.0.1:11434`)
- `OLLAMA_SUMMARIZE_MODEL` — Model for summarization (default: `phi4-mini:3.8b`)

## Testing Rules

- **Unit tests** in `tests/test_extraction.py` (new) and `tests/test_milestone2.py` (existing)
- **Fixtures** created in `tempfile.TemporaryDirectory()` — no committed test data
- **Skip conditions** — Use `@pytest.mark.skipif` for missing binaries (tesseract)
- **Run command** — `python -m pytest tests/ -q` from repo root
- **No external services** in tests — mock or skip

## Worker Dispatch

The `Worker` class in `worker.py` uses a dispatch table:
```python
self.handlers = {
    JobType.SCAN: self._handle_scan,
    JobType.EXTRACT_TEXT: self._handle_extract_text,
    JobType.OCR_PDF: self._handle_ocr_pdf,
    # ...
}
```

Two queues:
- **fast** — `EXTRACT_TEXT`, `NORMALIZE_JSON`, `DEDUPE_SCAN`, `CLASSIFY_SCAN`, `SUMMARIZE`, `SCAN`
- **slow** — `OCR_PDF`

Run with: `python -m app.worker --queue fast|slow [--once]`

## Extraction Output Format

Each document gets:
- `data/extracted/<sha256>.txt` — Full extracted text with page markers
- `data/extracted/manifests/<sha256>.json` — Metadata:
```json
{
  "source_path": "...",
  "content_hash": "...",
  "pages": 5,
  "chars": 12345,
  "chars_per_page": [2000, 2100, ...],
  "method": "text|ocr|native",
  "confidence": 0.85,
  "metadata": {...},
  "extracted_at": "2024-01-01T00:00:00"
}
```

## Quality Gate

`compute_quality_score(text, file_size, pages, method, confidence)` returns `QualityScore`:
- **Components**: size_ratio, replacement_char_ratio, alpha_ratio, language_sanity, extraction_confidence
- **Threshold**: `QUALITY_THRESHOLD` (default 0.35)
- **Below threshold** → `Document.status = NEEDS_REVIEW`

## Ollama Usage

- **Only for high-value docs** — `Document.high_value = True`
- **Model**: `phi4-mini:3.8b` (small, fast)
- **Timeout**: 120s, `num_ctx=4096`, `keep_alive=5m`
- **Client**: `OllamaClient` in `ollama_client.py` — `summarize()`, `extract_key_points()`

## Prohibited Patterns

| ❌ Don't | ✅ Do |
|----------|-------|
| `requests.get("https://...")` | `requests.post("http://127.0.0.1:11434/...")` |
| `os.path.join("/hardcoded", ...)` | `Path(os.getenv("DATA_DIR", "...")) / "..."` |
| `print()` in library code | `logger.info()` |
| `async def` without `await` | Sync functions (worker is sync) |
| New tables without `models.py` | Add to `models.py` + `db.py` |
| Cloud API keys in code | Local-only, no secrets |

## First-Run Command Sequence for D:\References

```powershell
cd D:\AI\librarian

# 1. Register collection
python -m app.cli collection-create references D:\References D:\References

# 2. Scan (discovers files, computes SHA-256)
python -m app.cli scan <collection-id>

# 3. Classify (detects file types, scanned PDFs)
python -m app.cli classify <collection-id>

# 4. Extract all text (queues or runs extraction)
python -m app.cli extract-all --queue
# Then run worker:
python -m app.worker --queue fast

# 5. OCR scanned PDFs (slow queue)
python -m app.cli ocr <collection-id>
# Or via worker:
python -m app.worker --queue slow

# 6. Find duplicates
python -m app.cli dedupe <collection-id>

# 7. Review quality
python -m app.cli collection-stats <collection-id>
# Check needs_review count, then:
python -m app.cli quality <doc-id>

# 8. Summarize high-value docs
python -m app.cli summarize <doc-id> --high-value
```

## Git Hygiene

- **Commit messages**: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`
- **Never commit** `data/`, `logs/`, `.env`, `Librarian.env`, `__pycache__/`, `.pytest_cache/`
- **Run tests before push**: `pytest tests/ -q`
- **No force push** to main

## Debugging Tips

- **Logs**: `tail -f logs/extractor.log` (if configured) or check `job_events` table
- **Job status**: `GET /api/jobs/{id}` or `python -m app.cli list-jobs <id>`
- **Document status**: `GET /api/documents?collection_id=...&status=failed`
- **Extraction files**: Check `data/extracted/<hash>.txt` and `manifests/<hash>.json`
- **Worker stuck**: Check `Job.status = RUNNING` with old `started_at` → manual retry

---

## Extraction Pipeline (`src/` + `scripts/`) — origin conventions

Local-only document extraction pipeline for research, curation, and archival workflows.

This repository exists to solve the exact class of problems described: large mixed document collections, scanned PDFs, Office files, JSON exports, duplication, and local-only extraction without cloud APIs, SaaS OCR, or subscription fees.

It is intentionally opinionated, strict, and boring: the goal is reliable local extraction, clean metadata, deduplication, and reviewable output that can be handed to a local model or a human curator without wasting compute on junk.

## What this repo does

- inventories a source tree and hashes every file
- identifies likely duplicates before expensive work
- classifies files by type
- extracts text from PDFs, DOCX, PPTX, XLSX, and JSON exports
- runs OCR for scanned PDFs using local Tesseract
- normalizes output into a consistent schema
- surfaces likely junk items for curation decisions
- triages extraction health and repairs recoverable files locally
- gives OpenCode a repo-local workflow to follow without cloud services

## Strict rules

- no cloud OCR or paid document intelligence
- no SaaS AI extraction layer
- no locked-in proprietary formats
- Windows-first local installation
- work with open-source tools only

## Approved toolchain

- Python: https://github.com/python/cpython
- Git: https://github.com/git/git
- Tesseract OCR: https://github.com/tesseract-ocr/tesseract
- pypdf: https://github.com/py-pdf/pypdf
- pdfplumber: https://github.com/jsvine/pdfplumber
- PyMuPDF: https://github.com/pymupdf/PyMuPDF
- Docling: https://github.com/DS4SD/docling
- Marker: https://github.com/VikParuchuri/marker
- python-docx: https://github.com/python-openxml/python-docx
- python-pptx: https://github.com/scanny/python-pptx
- openpyxl: https://github.com/openpyxl/openpyxl
- pandas: https://github.com/pandas-dev/pandas
- Ollama: https://github.com/ollama/ollama

## Repo layout

```text
librarian/
├── AGENTS.md
├── README.md
├── requirements.txt
├── pyproject.toml
├── .opencode/
│   └── instructions.md
├── config/
│   ├── tool_manifest.yaml
│   ├── extraction_targets.yaml
│   └── review_rules.yaml
├── docs/
│   ├── TOOLCHAIN.md
│   ├── WINDOWS_INSTALL.md
│   ├── REPAIR_WORKFLOW.md
│   └── PROJECT_DECISIONS.md
├── scripts/
│   ├── install_windows.ps1
│   ├── install_python_packages.ps1
│   ├── build_manifest.py
│   ├── classify_documents.py
│   ├── extract_pdf_text.py
│   ├── extract_scanned_pdf.py
│   ├── extract_office.py
│   ├── normalize_json_exports.py
│   ├── quality_gate.py
│   ├── scan_inventory.py
│   ├── triage_document_health.py
│   └── repair_bad_files.py
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── inventory.py
│   ├── dedupe.py
│   ├── classify.py
│   ├── normalize.py
│   ├── chunking.py
│   ├── review.py
│   ├── llm_local.py
│   └── extractors/
│       ├── __init__.py
│       ├── pdf_text.py
│       ├── pdf_ocr.py
│       ├── office.py
│       ├── json_exports.py
│       └── archives.py
├── app/                 # FastAPI service + worker layer (see Module Organization above)
├── tests/               # pytest suite
├── reports/             # human-facing triage/repair reports
├── data/
│   ├── input/
│   ├── manifests/
│   ├── extracted/
│   ├── chunks/
│   └── reviews/
├── logs/
│   └── .gitkeep
└── .gitignore
```

## Pipeline Quickstart

1. Install Python from the official repo:
   https://github.com/python/cpython

2. Install Git for Windows:
   https://github.com/git/git

3. Install Tesseract OCR:
   https://github.com/tesseract-ocr/tesseract

4. Open PowerShell in the repo root and create a venv:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

5. Install Python dependencies:

```powershell
pip install -r requirements.txt
```

6. Run the pipeline:

```powershell
python .\scripts\build_manifest.py
python .\scripts\classify_documents.py
python .\scripts\extract_pdf_text.py
python .\scripts\extract_scanned_pdf.py
python .\scripts\extract_office.py
python .\scripts\normalize_json_exports.py
python .\scripts\quality_gate.py
```

7. Triage and repair unhealthy files (see `docs/REPAIR_WORKFLOW.md`):

```powershell
python .\scripts\triage_document_health.py
python .\scripts\repair_bad_files.py --dry-run
```

**DB-backed collections**: when sources are registered in `data/librarian.db`
(the `app/` service) instead of copied into `data/input`, generate the
manifest from the ledger instead of scanning (same schema as
`build_manifest.py`; adds `chars` so triage can apply the
`text_zero_chars` rule):

```powershell
python .\scripts\build_manifest_from_db.py
```

Then run `classify_documents.py` and the triage steps as usual. Triage
re-hashes every file from disk (~10-12 min for 4 GB under Windows Defender
real-time scanning) — run it detached and wait for `data/reviews/needs_review.json`.

## Data model expectations

This repository expects a source-data directory at `data/input`, a manifest directory at `data/manifests`, extracted output under `data/extracted`, and review output under `data/reviews`.

The system is designed to be extended in a clean way:

- inventory + dedupe logic live under `src/inventory.py` and `src/dedupe.py`
- extraction logic lives under `src/extractors/`
- normalized outputs are separate from raw extraction output
- review logic and quality gates live independently

## Why this repo exists

This repository is explicitly not a generic template. It is a practical answer to the exact problem set previously described:

- scanned PDFs with no text layer
- OCR quality issues
- duplicated manuals and revisions
- mixed Office-document dumps
- noisy JSON exports
- the need to avoid a full AI binge on junk files

## Notes for OpenCode

OpenCode should treat this repository as the authoritative local project. It should use the scripts and configuration in this repo, not introduce cloud services or paid extraction APIs.

The repo is designed to be safe, local, and reviewable.
