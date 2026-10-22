# AGENTS.md

This repository is the local-only extraction system for large mixed document collections.

Follow this file first. It is the operating contract for any coding agent working here.

## Required constraints

- Use only open source, free, local tools.
- No cloud OCR.
- No paid API-based extraction.
- No proprietary SaaS document intelligence.
- No external document processing services.
- Work only with local files and local runtimes.
- Prefer deterministic scripts and clear metadata over fancy automation.
- When a document is damaged, broken, empty, or clearly junk, route it through a local triage and repair workflow before attempting full extraction.

## Installation order

1. Install Python from the official Python repo:
   https://github.com/python/cpython

2. Install Git for Windows:
   https://github.com/git/git

3. Install Tesseract OCR:
   https://github.com/tesseract-ocr/tesseract

4. Install qpdf for PDF repair and validation:
   https://github.com/qpdf/qpdf

5. Install Ghostscript for PDF rewrite and repair:
   https://github.com/ArtifexSoftware/ghostpdl

6. Install LibreOffice for Office file rescue:
   https://www.libreoffice.org/

7. Create a virtual environment and install dependencies.

8. Optionally install Ollama for local model usage:
   https://github.com/ollama/ollama

## Allowed toolchain

- Tesseract OCR
- qpdf
- Ghostscript
- LibreOffice headless
- 7-Zip
- jdupes
- pypdf
- pdfplumber
- PyMuPDF
- Docling
- Marker
- python-docx
- python-pptx
- openpyxl
- pandas
- Ollama

## Disallowed toolchain

- Adobe Acrobat OCR / Adobe PDF services
- Azure AI Document Intelligence
- Google Document AI
- AWS Textract
- paid OCR pipelines
- cloud-based AI extraction services

## Operating expectations

- Keep source files in `data/input`
- Keep manifests in `data/manifests`
- Keep extracted outputs in `data/extracted`
- Keep review output in `data/reviews`
- Keep chunk output in `data/chunks`
- Keep logs under `logs/`

## Required workflow

1. inventory files and compute hashes
2. classify document types
3. triage file health and quality issues
4. deduplicate by content hash
5. extract text or OCR as required
6. repair recoverable broken files locally
7. normalize output to a consistent schema
8. run quality gate and review decisions
9. use local LLMs only for selected high-value docs

## Priority order

1. scanned PDFs
2. text-native PDFs
3. DOCX/PPTX/XLSX
4. broken file repair and recovery
5. JSON export normalization
6. local LLM summarization of selected value-rich documents

## Repo behavior

OpenCode should follow the actual scripts in this repo rather than improvising a cloud solution.

It should prefer simplicity, repeatability, metadata-rich output, and a transparent review trail over flashy, expensive single-pass summaries.

## Local triage stage

The project includes a recovery-first workflow for damaged collections:

- classify lock/temp files as junk automatically
- quarantine empty files
- flag duplicate files before extraction
- validate Office ZIP containers
- attempt PDF repair before re-running OCR
- create a local review ledger for human decision points

This is an intentional part of the pipeline and should be treated as normal operational behavior, not as a one-off cleanup step.
