from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "librarian.db"
OUT_PATH = ROOT / "data" / "manifests" / "files_manifest.json"


def _created_at(value: str | None) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value).isoformat() + "Z"
    except ValueError:
        return value


def collect_rows(db_path: Path) -> list[dict]:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute(
            "SELECT source_path, size_bytes, content_hash, extension, created_at, char_count FROM documents"
        )
        rows = []
        for source_path, size_bytes, content_hash, extension, created_at, char_count in cur:
            rows.append({
                "path": source_path,
                "size_bytes": size_bytes or 0,
                "sha256": content_hash or "",
                "extension": (extension or Path(source_path).suffix.lower()).lower(),
                "created_at": _created_at(created_at),
                "chars": char_count,
            })
        return rows
    finally:
        conn.close()


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Missing database: {DB_PATH}")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    manifest = collect_rows(DB_PATH)
    with OUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    print(f"Manifest written to {OUT_PATH} ({len(manifest)} files)")


if __name__ == "__main__":
    main()
