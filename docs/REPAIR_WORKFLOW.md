# Repair and review workflow

This document explains the local triage and recovery pipeline for broken or low-quality files in the `librarian` project.

## Goal

The repo is intentionally local-only and reviewable. When a document fails extraction, the system should not just mark it as a failure; it should classify the failure, attempt local repair if appropriate, and record the result in a structured review ledger.

## Why this matters

The error reports in mixed document collections usually contain a predictable set of issues:

- temp lock files created by Microsoft Office (`~$...`)
- duplicate files with the same content hash
- zero-byte files
- broken ZIP packages in DOCX/PPTX/XLSX files
- truncated or corrupt PDFs
- files with 0 extracted characters after extraction or OCR

These are not AI problems; they are file-health and triage problems.

## Open-source local tools

These are the preferred tools for a no-subscription workflow.

### PDF repair and validation

- qpdf: https://github.com/qpdf/qpdf
- Ghostscript: https://github.com/ArtifexSoftware/ghostpdl
- Tesseract: https://github.com/tesseract-ocr/tesseract
- Mutool (MuPDF): https://github.com/pymupdf/PyMuPDF
- OCRmyPDF: https://github.com/ocrmypdf/OCRmyPDF

### Office file rescue

- LibreOffice: https://www.libreoffice.org/
- 7-Zip: https://www.7-zip.org/

### Duplicate detection

- jdupes: https://github.com/jbruchon/jdupes
- rmlint: https://github.com/SeeSpotRun/rmlint

### Python ecosystem used by this repo

- Python: https://github.com/python/cpython
- pypdf: https://github.com/py-pdf/pypdf
- pdfplumber: https://github.com/jsvine/pdfplumber
- python-docx: https://github.com/python-openxml/python-docx
- python-pptx: https://github.com/scanny/python-pptx
- openpyxl: https://github.com/openpyxl/openpyxl
- pandas: https://github.com/pandas-dev/pandas

## Recommended triage flow

1. Build inventory and hash all files
2. Classify files by extension and type
3. Detect temp / junk files (`~$...`)
4. Detect zero-byte files
5. Detect duplicate SHA-256 values
6. Validate Office ZIPs
7. Attempt PDF parsing and repair
8. Record errors in `data/reviews/needs_review.json`
9. Use repair scripts and local tools to recover what can be salvaged
10. Preserve a review trail for every action

## Repository integration points

The project already has the right structure to absorb this cleanly:

- `scripts/` for operational steps
- `config/` for rules and tool manifests
- `data/reviews/` for review outputs
- `src/` for reusable logic

This should be added as a normal pipeline stage, not a separate ad hoc workflow.

## Suggested repo additions

The repo should include:

- `scripts/triage_document_health.py` — identifies broken / junk / duplicate files
- `scripts/repair_bad_files.py` — attempts local recovery and records the result
- `config/review_rules.yaml` — local policy and tool mapping
- `data/reviews/needs_review.json` — generated output from triage
- `data/reviews/repair_log.json` — generated output from repair attempts

## OpenCode-friendly operating pattern

OpenCode should follow this sequence:

```text
inventory -> classify -> triage -> dedupe -> repair -> extract -> normalize -> quality gate -> review
```

This sequence preserves reviewability, local-first processing, and clear failure categorization.

## Typical failure categories

- lock file: file name starts with `~$` and should be ignored
- empty file: zero-byte file, no extraction is possible
- duplicate: same content hash as another file, retain one canonical copy
- office corruption: broken ZIP / bad CRC-32 / invalid container
- PDF damage: `Unexpected EOF`, `File is not a PDF file`, truncated data
- zero extraction: file parses but no readable text was found

## Practical local actions

For each failure type:

- lock file: auto-skip
- empty file: move to review or quarantine
- duplicate: keep canonical copy and mark duplicates for exclusion
- corrupted Office doc: try LibreOffice rescue save
- damaged PDF: run qpdf, then Ghostscript, then OCR fallback
- zero extraction: check if file is image-only, blank, or placeholder content

## Web references and project pages

- Python: https://github.com/python/cpython
- Tesseract: https://github.com/tesseract-ocr/tesseract
- qpdf: https://github.com/qpdf/qpdf
- Ghostscript: https://github.com/ArtifexSoftware/ghostpdl
- LibreOffice: https://www.libreoffice.org/
- 7-Zip: https://www.7-zip.org/
- jdupes: https://github.com/jbruchon/jdupes
- pypdf: https://github.com/py-pdf/pypdf
- python-docx: https://github.com/python-openxml/python-docx
- python-pptx: https://github.com/scanny/python-pptx
- openpyxl: https://github.com/openpyxl/openpyxl
- pandas: https://github.com/pandas-dev/pandas

## Final recommendation

This should become a standard local review and repair stage in the repo, not a stretch goal. It matches the project philosophy and gives OpenCode a deterministic sequence that is easy to follow, log, and reuse.
