"""Repo-local data directory resolution for Librarian.

Single source of truth: DATA_DIR env var wins, otherwise <repo>/data.
Keeps the SQLite ledger and extracted outputs inside the repository
(per brief: outputs under data/ and logs/), regardless of cwd.
"""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = os.getenv("DATA_DIR") or str(REPO_ROOT / "data")
