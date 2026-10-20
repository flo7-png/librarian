from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "data" / "manifests" / "files_manifest.json"
OUT_PATH = ROOT / "data" / "manifests" / "classified_documents.json"


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


def main():
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Missing manifest: {MANIFEST_PATH}")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    classified = [{**item, "classification": classify(item["path"])} for item in manifest]

    OUT_PATH.write_text(json.dumps(classified, indent=2), encoding="utf-8")
    print(f"Classified manifest written to {OUT_PATH}")


if __name__ == "__main__":
    main()
