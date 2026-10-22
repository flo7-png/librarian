"""Generate reports/needs-review-YYYY-MM-DD.md for NEEDS_REVIEW documents.

Includes, per file: full path, size/chars/quality/parser, the DB-stored
error_message, and the ACTUAL error obtained by re-running the real
extractor (app.extract.extract_text) against the file right now.
Read-only with respect to the database.
"""
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.extract import extract_text  # noqa: E402

logging.getLogger("app.extract").setLevel(logging.CRITICAL)

DB = ROOT / "data" / "librarian.db"
REPORTS = ROOT / "reports"


def diagnose(row, fresh):
    """The actual reason this file needs review, best evidence first."""
    meta_err = (fresh.metadata or {}).get("error")
    if meta_err:
        return f"extraction threw: {meta_err}"
    if row["size_bytes"] == 0:
        return "file is empty (0 bytes on disk) — nothing to extract"
    if row["file_name"].startswith("~$"):
        return "Office lock/owner file (~$), not a real document — ignore or delete"
    if len(fresh.text) == 0:
        return (f"parser '{fresh.method}' opened the file but extracted 0 characters "
                f"(images-only, placeholder, or no readable text)")
    md = fresh.metadata or {}
    cs = md.get("chartsheets")
    if cs:
        if md.get("sheet_count") == len(cs):
            return f"all {len(cs)} sheet(s) are chartsheets (chart-only tabs) - no cell data to extract"
        return f"worksheet data extracted; {len(cs)} chartsheet(s) skipped (chart-only: {', '.join(cs[:3])})"
    return "ok on re-run (state may have changed since worker run)"


def main():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    rows = list(c.execute("""
        SELECT id, relative_path, source_path, file_name, extension, size_bytes,
               status, parser, ocr_status, IFNULL(error_message,'') AS error_message,
               quality_score, char_count, page_count
        FROM documents WHERE status='NEEDS_REVIEW' ORDER BY relative_path"""))

    events = {}
    for r in c.execute("""
        SELECT e.document_id, e.message FROM job_events e
        JOIN documents d ON d.id = e.document_id
        WHERE d.status='NEEDS_REVIEW' ORDER BY e.created_at DESC"""):
        events.setdefault(r["document_id"], r["message"])

    entries, causes = [], {}
    for row in rows:
        path = Path(row["source_path"])
        try:
            if not path.exists():
                fresh, diag = None, f"source file missing on disk: {path}"
            else:
                fresh = extract_text(path)
                diag = diagnose(row, fresh)
        except Exception as e:  # noqa: BLE001 - report must not die on one file
            fresh, diag = None, f"re-run itself failed: {type(e).__name__}: {e}"
        key = ("lock file" if row["file_name"].startswith("~$") else
               "empty file" if row["size_bytes"] == 0 else
               "extraction threw" if diag.startswith("extraction threw") else
               "0 chars extracted")
        causes[key] = causes.get(key, 0) + 1
        entries.append((row, fresh, diag))
        print(f"  [{key}] {row['file_name']} -> {diag[:90]}")

    out = REPORTS / f"needs-review-{datetime.now():%Y-%m-%d}.md"
    lines = [
        "# Librarian — NEEDS_REVIEW documents (with actual errors)",
        "",
        f"Generated: {datetime.now():%Y-%m-%d %H:%M} | count: {len(rows)}",
        "",
        "Sources: `documents.error_message` (what the worker stored), plus a fresh",
        "re-run of the real extractor (`app.extract.extract_text`) per file to",
        "capture the underlying error the worker never persisted.",
        "",
        "## Summary by cause",
        "",
    ]
    lines += [f"- {k}: {v}" for k, v in sorted(causes.items(), key=lambda kv: -kv[1])]
    lines += ["", "## Files", ""]
    for i, (row, fresh, diag) in enumerate(entries, 1):
        lines += [
            f"### {i}. {row['relative_path']}",
            f"- Full path: `{row['source_path']}`",
            f"- Size: {row['size_bytes']} B | chars (worker): {row['char_count']} | "
            f"quality: {row['quality_score']:.2f} | parser: {row['parser']} | ocr: {row['ocr_status']}",
            f"- Stored error (DB): {row['error_message'] or '(none)'}",
            f"- Actual error (re-run): {diag}",
        ]
        if fresh is not None:
            lines.append(f"- Re-run detail: method={fresh.method}, pages={fresh.pages}, "
                         f"chars={len(fresh.text)}, confidence={fresh.confidence:.2f}")
        if row["id"] in events:
            lines.append(f"- Worker event: {events[row['id']]}")
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nreport: {out}")


if __name__ == "__main__":
    main()
