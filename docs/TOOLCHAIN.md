# Toolchain guide

This project is intentionally local-only and open-source.

## Approved tools

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

## Tool role map

- OCR: Tesseract
- native PDF extraction: pypdf + pdfplumber
- layout-heavy PDFs: Docling or Marker
- DOCX: python-docx
- PPTX: python-pptx
- XLSX: openpyxl
- data wrangling: pandas
- local model runtime: Ollama

## Policy

- no cloud OCR
- no paid document AI services
- no external extraction APIs
- local-first by design
