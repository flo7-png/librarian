from pathlib import Path
import hashlib
import json
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
INPUT_ROOT = ROOT / "data" / "input"
OUT_PATH = ROOT / "data" / "manifests" / "files_manifest.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_files(base_dir: Path):
    for path in sorted(base_dir.rglob("*")):
        if path.is_file():
            yield path


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    manifest = []

    if not INPUT_ROOT.exists():
        print(f"Input directory does not exist: {INPUT_ROOT}")
        return

    for file_path in iter_files(INPUT_ROOT):
        manifest.append({
            "path": str(file_path.relative_to(ROOT)),
            "size_bytes": file_path.stat().st_size,
            "sha256": sha256_file(file_path),
            "extension": file_path.suffix.lower(),
            "created_at": datetime.utcnow().isoformat() + "Z",
        })

    with OUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    print(f"Manifest written to {OUT_PATH}")


if __name__ == "__main__":
    main()
