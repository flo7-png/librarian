$ErrorActionPreference = "Stop"

& ".\.venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
python -m pip install pypdf pdfplumber pymupdf pytesseract python-docx python-pptx openpyxl pandas docling marker-pdf
