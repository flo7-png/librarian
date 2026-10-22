from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import zipfile

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "data" / "manifests" / "classified_documents.json"
OUT_PATH = ROOT / "data" / "reviews" / "needs_review.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_item(item: dict) -> str:
    path = item.get("path", "")
    suffix = Path(path).suffix.lower()
    if suffix in {".docx", ".pptx", ".xlsx", ".xls"}:
        return "office"
    if suffix == ".pdf":
        return "pdf"
    if suffix == ".json":
        return "json"
    return "other"


def is_lock_file(path: Path) -> bool:
    return path.name.startswith("~$")


def validate_office_zip(path: Path) -> tuple[bool, str | None]:
    if not path.exists():
        return False, "missing file"
    try:
        with zipfile.ZipFile(path) as zf:
            zf.testzip()
        return True, None
    except zipfile.BadZipFile as exc:
        return False, f"bad zip: {exc}"
    except Exception as exc:  # pragma: no cover
        return False, f"zip validation error: {exc}"


def validate_pdf(path: Path) -> tuple[bool, str | None]:
    if not path.exists():
        return False, "missing file"
    if not path.stat().st_size:
        return False, "empty file"
    if PdfReader is None:
        return True, "pypdf unavailable"
    try:
        with path.open("rb") as handle:
            reader = PdfReader(handle)
            pages = len(reader.pages)
        return True, f"pdf readable ({pages} pages)"
    except Exception as exc:  # pragma: no cover
        return False, f"pdf parse error: {exc}"


def main() -> None:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Missing manifest: {MANIFEST_PATH}")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    by_hash: dict[str, list[str]] = defaultdict(list)
    for item in manifest:
        path_value = item.get("path")
        if not path_value:
            continue
        full_path = ROOT / path_value
        if not full_path.exists():
            continue
        by_hash[sha256_file(full_path)].append(path_value)

    review_items = []
    for item in manifest:
        path_value = item.get("path")
        if not path_value:
            continue

        full_path = ROOT / path_value
        record = {
            "path": path_value,
            "classification": item.get("classification", classify_item(item)),
            "status": "valid",
            "reason": "",
            "severity": "low",
            "repairable": False,
            "details": {},
        }

        if not full_path.exists():
            record["status"] = "missing_file"
            record["reason"] = "file is missing"
            record["severity"] = "medium"
            review_items.append(record)
            continue

        if is_lock_file(full_path):
            record["status"] = "lock_file"
            record["reason"] = "Microsoft Office temp / lock file"
            record["severity"] = "low"
            record["repairable"] = False
            review_items.append(record)
            continue

        if full_path.stat().st_size == 0:
            record["status"] = "empty_file"
            record["reason"] = "file is zero bytes"
            record["severity"] = "medium"
            record["repairable"] = False
            review_items.append(record)
            continue

        identical_hashes = by_hash.get(sha256_file(full_path), [])
        if len(identical_hashes) > 1:
            record["status"] = "duplicate"
            record["reason"] = "duplicate file detected by SHA-256"
            record["severity"] = "medium"
            record["details"]["duplicates"] = identical_hashes
            review_items.append(record)
            continue

        suffix = full_path.suffix.lower()
        if suffix in {".docx", ".pptx", ".xlsx", ".xls"}:
            ok, detail = validate_office_zip(full_path)
            if not ok:
                record["status"] = "office_corruption"
                record["reason"] = detail or "broken Office ZIP container"
                record["severity"] = "high"
                record["repairable"] = True
                record["details"]["zip_check"] = detail
                review_items.append(record)
                continue

        if suffix == ".pdf":
            ok, detail = validate_pdf(full_path)
            if not ok:
                record["status"] = "pdf_damage"
                record["reason"] = detail or "PDF failed validation"
                record["severity"] = "high"
                record["repairable"] = True
                record["details"]["pdf_check"] = detail
                review_items.append(record)
                continue

        if item.get("classification") == "other":
            record["status"] = "needs_review"
            record["reason"] = "unknown or unsupported file type"
            record["severity"] = "medium"
            record["repairable"] = False
            review_items.append(record)
            continue

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_items": len(manifest),
            "needs_review": sum(1 for item in review_items if item["status"] != "valid"),
            "by_status": {status: sum(1 for item in review_items if item["status"] == status) for status in sorted({item["status"] for item in review_items})},
        },
        "items": review_items,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Review report written to {OUT_PATH}")


if __name__ == "__main__":
    main()
