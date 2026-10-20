"""Inventory helpers."""

from pathlib import Path


def iter_files(base_dir: Path):
    for path in sorted(base_dir.rglob("*")):
        if path.is_file():
            yield path
