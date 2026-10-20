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

## Installation order

1. Install Python from the official Python repo:
   https://github.com/python/cpython

2. Install Git for Windows:
   https://github.com/git/git

3. Install Tesseract OCR:
   https://github.com/tesseract-ocr/tesseract

4. Create a virtual environment and install dependencies.

5. Optionally install Ollama for local model usage:
   https://github.com/ollama/ollama

## Allowed toolchain

- Tesseract OCR
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
3. deduplicate by content hash
4. extract text or OCR as required
5. normalize output to a consistent schema
6. run quality gate and review decisions
7. use local LLMs only for selected high-value docs

## Priority order

1. scanned PDFs
2. text-native PDFs
3. DOCX/PPTX/XLSX
4. JSON export normalization
5. local LLM summarization of selected value-rich documents

## Repo behavior

OpenCode should follow the actual scripts in this repo rather than improvising a cloud solution.

It should prefer simplicity, repeatability, and metadata-rich output over flashy, expensive single-pass summaries.
