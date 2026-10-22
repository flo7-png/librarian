"""Classification helpers."""

from pathlib import Path


def classify(path: str):
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext == ".docx":
        return "docx"
    if ext == ".pptx":
        return "pptx"
    if ext in {".xlsx", ".xls"}:
        return "xlsx"
    if ext == ".json":
        return "json"
    if ext == ".zip":
        return "zip"
    if ext == ".md":
        return "markdown"
    return "other"
