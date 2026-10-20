# Windows installation guide

This is the expected path for local setup.

## 1) Install Python

Use the official Python repo:
https://github.com/python/cpython

## 2) Install Git for Windows

Use the official Git repo:
https://github.com/git/git

## 3) Install Tesseract OCR

Use the official Tesseract OCR repo:
https://github.com/tesseract-ocr/tesseract

After install, verify:

```powershell
tesseract --version
```

## 4) Create a venv

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 5) Install Python dependencies

```powershell
pip install -r requirements.txt
```

## 6) Optional local model runtime

Install Ollama from:
https://github.com/ollama/ollama

Then pull a model if desired:

```powershell
ollama pull llama3.1
```
