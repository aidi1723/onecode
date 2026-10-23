from __future__ import annotations

import hashlib
from pathlib import Path


def is_preset_test_path(path: str) -> bool:
    normalized = path.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    folded = normalized.casefold().rstrip("/")
    return folded == "tests" or folded.startswith("tests/")


def preset_test_hashes(workspace_root: Path) -> dict[str, str]:
    tests_dir = workspace_root / "tests"
    if not tests_dir.is_dir():
        return {}
    hashes: dict[str, str] = {}
    for file_path in sorted(tests_dir.rglob("*.py")):
        if "__pycache__" in file_path.parts or not file_path.is_file():
            continue
        rel = file_path.relative_to(workspace_root).as_posix()
        hashes[rel] = hashlib.sha256(file_path.read_bytes()).hexdigest()
    return hashes
