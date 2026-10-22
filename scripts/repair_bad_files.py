from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = ROOT / "data" / "reviews" / "needs_review.json"
REPAIR_LOG_PATH = ROOT / "data" / "reviews" / "repair_log.json"


def has_executable(name: str) -> bool:
    return shutil.which(name) is not None


def recommended_action(item: dict) -> str:
    status = item.get("status")
    if status == "lock_file":
        return "skip_and_exclude"
    if status == "empty_file":
        return "quarantine_or_skip"
    if status == "duplicate":
        return "keep_canonical_copy_only"
    if status == "office_corruption":
        return "libreoffice_rescue_then_reextract"
    if status == "pdf_damage":
        return "qpdf_or_ghostscript_then_reextract"
    if status == "missing_file":
        return "verify_source_path"
    return "manual_review"


def build_commands(item: dict):
    path = ROOT / item["path"]
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return [
            "qpdf --check " + str(path),
            "qpdf --linearize --replace-input " + str(path),
            "gswin64c -sDEVICE=pdfwrite -dNOPAUSE -dBATCH -sOutputFile=repair.pdf " + str(path),
        ]
    if suffix in {".docx", ".pptx", ".xlsx", ".xls"}:
        return [
            "7z l " + str(path),
            "soffice --headless --invisible --convert-to docx --outdir <repair_dir> " + str(path),
        ]
    return ["manual_review"]


def main() -> None:
    if not REPORT_PATH.exists():
        raise FileNotFoundError(f"Missing review report: {REPORT_PATH}. Run triage_document_health.py first.")

    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    entries = []
    for item in report.get("items", []):
        if item.get("status") == "valid":
            continue
        entries.append({
            "path": item["path"],
            "status": item["status"],
            "action": recommended_action(item),
            "commands": build_commands(item),
            "tools_available": {
                "qpdf": has_executable("qpdf"),
                "gs": has_executable("gs") or has_executable("gswin64c"),
                "soffice": has_executable("soffice"),
                "7z": has_executable("7z") or has_executable("7za"),
            },
        })

    REPAIR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPAIR_LOG_PATH.write_text(json.dumps({
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "items": entries,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Repair plan written to {REPAIR_LOG_PATH}")


if __name__ == "__main__":
    main()
