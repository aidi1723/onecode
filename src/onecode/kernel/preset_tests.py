from __future__ import annotations

import hashlib
import posixpath
from pathlib import Path


def is_preset_test_path(path: str) -> bool:
    if not isinstance(path, str) or not path.strip():
        return False
    normalized = posixpath.normpath(path.replace("\\", "/").strip()).lstrip("/")
    folded = normalized.casefold()
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


def authoritative_preset_test_hashes(workspace_root: Path) -> dict[str, str]:
    from onecode.kernel.run_inspection import read_global_wal_entries

    entries, _, corrupt_reason = read_global_wal_entries(workspace_root)
    if not corrupt_reason and entries:
        for entry in reversed(entries):
            th = entry.get("th")
            if isinstance(th, list) and th:
                return {item["p"]: item["s"] for item in th if isinstance(item, dict) and "p" in item and "s" in item}
    return preset_test_hashes(workspace_root)
