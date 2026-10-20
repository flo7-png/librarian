from pathlib import Path
import json
from pytesseract import image_to_string
from pdf2image import convert_from_path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "data" / "manifests" / "classified_documents.json"
OUT_ROOT = ROOT / "data" / "extracted"


def is_likely_scanned(pdf_path: Path):
    # Conservative default: run OCR for all PDFs classified as pdf and let a human review filters decide.
    return True


def main():
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Missing manifest: {MANIFEST_PATH}")

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    for item in manifest:
        if item["classification"] != "pdf":
            continue

        pdf_path = ROOT / item["path"]
        if not is_likely_scanned(pdf_path):
            continue

        output = {"source": item["path"], "pages": []}

        try:
            pages = convert_from_path(str(pdf_path), dpi=300)
            for idx, page in enumerate(pages, start=1):
                output["pages"].append({
                    "page": idx,
                    "text": image_to_string(page, config="--psm 6")
                })
        except Exception as exc:
            output["error"] = str(exc)

        out_path = OUT_ROOT / f"{Path(item['path']).stem}_ocr.json"
        out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"OCR processed: {pdf_path}")


if __name__ == "__main__":
    main()
