"""Project configuration helpers."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
INPUT_DIR = DATA_DIR / "input"
MANIFEST_DIR = DATA_DIR / "manifests"
EXTRACTED_DIR = DATA_DIR / "extracted"
CHUNKS_DIR = DATA_DIR / "chunks"
REVIEWS_DIR = DATA_DIR / "reviews"
