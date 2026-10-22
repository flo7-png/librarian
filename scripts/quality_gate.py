from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_ROOT = ROOT / "data" / "extracted"
REVIEW_ROOT = ROOT / "data" / "reviews"


def main():
    REVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    report = []

    for path in sorted(EXTRACTED_ROOT.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            text_size = len(json.dumps(data, ensure_ascii=False)) if isinstance(data, (dict, list)) else 0
            report.append({
                "file": str(path.relative_to(ROOT)),
                "proxy_size": text_size,
                "status": "manual_review_required" if text_size > 0 else "empty",
            })
        except Exception as exc:
            report.append({
                "file": str(path.relative_to(ROOT)),
                "status": "error",
                "error": str(exc),
            })

    out_path = REVIEW_ROOT / "quality_gate_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Quality gate report written to {out_path}")


if __name__ == "__main__":
    main()
