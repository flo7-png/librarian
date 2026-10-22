from pathlib import Path
import json
from pypdf import PdfReader
from pdfplumber import open as pdfplumber_open

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "data" / "manifests" / "classified_documents.json"
OUT_ROOT = ROOT / "data" / "extracted"


def extract_text_from_pdf(pdf_path: Path):
    chunks = []

    reader = PdfReader(str(pdf_path))
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            chunks.append({"page": len(chunks) + 1, "text": text})

    if not chunks:
        with pdfplumber_open(str(pdf_path)) as pdf:
            for idx, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    chunks.append({"page": idx, "text": text})

    return chunks


def main():
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Missing manifest: {MANIFEST_PATH}")

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    for item in manifest:
        if item["classification"] != "pdf":
            continue

        source_path = ROOT / item["path"]
        raw_data = {
            "source": item["path"],
            "pages": extract_text_from_pdf(source_path),
        }
        out_path = OUT_ROOT / f"{Path(item['path']).stem}.json"
        out_path.write_text(json.dumps(raw_data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Processed {source_path}")


if __name__ == "__main__":
    main()
