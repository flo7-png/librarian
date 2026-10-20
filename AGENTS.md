# librarian

Local-only document extraction pipeline for research, curation, and archival workflows.

This repository exists to solve the exact class of problems you described: large mixed document collections, scanned PDFs, Office files, JSON exports, duplication, and local-only extraction without cloud APIs, SaaS OCR, or subscription fees.

It is intentionally opinionated, strict, and boring: the goal is reliable local extraction, clean metadata, deduplication, and reviewable output that can be handed to a local model or a human curator without wasting compute on junk.

## What this repo does

- inventories a source tree and hashes every file
- identifies likely duplicates before expensive work
- classifies files by type
- extracts text from PDFs, DOCX, PPTX, XLSX, and JSON exports
- runs OCR for scanned PDFs using local Tesseract
- normalizes output into a consistent schema
- surfaces likely junk items for curation decisions
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
│   └── extraction_targets.yaml
├── docs/
│   ├── TOOLCHAIN.md
│   ├── WINDOWS_INSTALL.md
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
│   └── quality_gate.py
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

## Quickstart

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

## Data model expectations

This repository expects a source-data directory at `data/input`, a manifest directory at `data/manifests`, extracted output under `data/extracted`, and review output under `data/reviews`.

The system is designed to be extended in a clean way:

- inventory + dedupe logic live under `src/inventory.py` and `src/dedupe.py`
- extraction logic lives under `src/extractors/`
- normalized outputs are separate from raw extraction output
- review logic and quality gates live independently

## Why this repo exists

This repository is explicitly not a generic template. It is a practical answer to the exact problem set you previously described:

- scanned PDFs with no text layer
- OCR quality issues
- duplicated manuals and revisions
- mixed Office-document dumps
- noisy JSON exports
- the need to avoid a full AI binge on junk files

## Notes for OpenCode

OpenCode should treat this repository as the authoritative local project. It should use the scripts and configuration in this repo, not introduce cloud services or paid extraction APIs.

The repo is designed to be safe, local, and reviewable.
