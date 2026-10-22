# Project decisions

## What this repo is for

This project is a practical control layer for large, messy knowledge collections. It is not a marketing template and not a generic AI wrapper.

## Core decisions

- ECU must be curated before full digesting.
- Military and electrical folders are the highest-priority OCR cases.
- Old AI exports are valuable but require normalization.
- spreadsheets should be treated as structured data, not prose
- low-value junk should be filtered early

## Approved tools

- Python: https://github.com/python/cpython
- Tesseract: https://github.com/tesseract-ocr/tesseract
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

## Rejected tools

- Adobe Acrobat OCR
- Adobe PDF services
- Azure Document Intelligence
- Google Document AI
- AWS Textract
- cloud document extraction services
