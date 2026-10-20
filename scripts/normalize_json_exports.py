from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
INPUT_ROOT = ROOT / "data" / "input"
OUT_ROOT = ROOT / "data" / "extracted"


def normalize_message_tree(node):
    if isinstance(node, dict):
        if "messages" in node:
            return {"messages": [normalize_message_tree(m) for m in node["messages"]]}
        return {key: normalize_message_tree(value) for key, value in node.items()}
    if isinstance(node, list):
        return [normalize_message_tree(item) for item in node]
    return node


def main():
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_ROOT.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            normalized = normalize_message_tree(data)
            out_path = OUT_ROOT / f"{path.stem}_normalized.json"
            out_path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Normalized: {path}")
        except Exception as exc:
            print(f"Skipped {path}: {exc}")


if __name__ == "__main__":
    main()
