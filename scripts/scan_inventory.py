from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "data" / "manifests" / "files_manifest.json"
OUT_PATH = ROOT / "data" / "manifests" / "inventory_summary.json"


def main():
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Missing manifest: {MANIFEST_PATH}")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    summary = {
        "total_files": len(manifest),
        "by_extension": {},
        "total_size_bytes": 0,
    }

    for item in manifest:
        ext = item["extension"] or "<none>"
        summary["by_extension"][ext] = summary["by_extension"].get(ext, 0) + 1
        summary["total_size_bytes"] += item["size_bytes"]

    OUT_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Inventory summary written to {OUT_PATH}")


if __name__ == "__main__":
    main()
