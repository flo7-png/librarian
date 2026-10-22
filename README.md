# librarian
Local-only document extraction pipeline for research and archival workflows.

## Repository purpose

This repository is designed for local-only document extraction, classification, deduplication, OCR, and review for mixed collections of PDFs, Office files, and export artifacts.

## Core workflow

1. inventory files and compute hashes
2. classify document types
3. deduplicate by content hash
4. detect low-quality or broken files
5. extract text or OCR as required
6. normalize outputs to a consistent schema
7. run review and quality gates
8. use a local LLM only for selected high-value documents

## Error triage and repair workflow

The repo now includes a built-in local triage and repair layer for common extraction failures seen in messy source collections.

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

## Repo layout

```text
librarian/
├── AGENTS.md
├── README.md
├── requirements.txt
├── pyproject.toml
├── config/
│   ├── extraction_targets.yaml
│   ├── review_rules.yaml
│   └── tool_manifest.yaml
├── docs/
│   ├── PROJECT_DECISIONS.md
│   ├── REPAIR_WORKFLOW.md
│   ├── TOOLCHAIN.md
│   └── WINDOWS_INSTALL.md
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
│   └── triage_document_health.py
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
├── data/
│   ├── input/
│   ├── manifests/
│   ├── extracted/
│   ├── chunks/
│   └── reviews/
├── logs/
└── .opencode/
    └── instructions.md
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
