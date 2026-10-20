$ErrorActionPreference = "Stop"

Write-Host "Installing librarian local extraction toolchain..."

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Error "Python is not installed or not on PATH. Install from https://github.com/python/cpython"
    exit 1
}

$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    Write-Error "Git is not installed or not on PATH. Install from https://github.com/git/git"
    exit 1
}

$tesseract = Get-Command tesseract -ErrorAction SilentlyContinue
if (-not $tesseract) {
    Write-Warning "Tesseract is not on PATH. Install from https://github.com/tesseract-ocr/tesseract"
}

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& ".\.venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host "Install complete."
Write-Host "Next: ensure Tesseract is on PATH and run: tesseract --version"
Write-Host "Optional: install Ollama from https://github.com/ollama/ollama"
