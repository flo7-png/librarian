"""Review workflow helpers."""

from pathlib import Path
import json


def write_review_note(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
