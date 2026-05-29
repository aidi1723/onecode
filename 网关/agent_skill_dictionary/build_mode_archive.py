from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .build_mode_types import ArchiveEvidence


def finalize_manifest(workspace_root: str | Path, lockdown: bool = False) -> ArchiveEvidence:
    root = Path(workspace_root).resolve()
    manifest_dir = root / ".yizijue"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    sha256_map = _hash_workspace(root)
    manifest_path = manifest_dir / "manifest.json"
    payload = {
        "sha256_map": sha256_map,
        "lockdown": lockdown,
        "readonly_status": "lockdown" if lockdown else "audit_only",
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if lockdown:
        _lockdown(root)
    return ArchiveEvidence(
        manifest_path=manifest_path.relative_to(root).as_posix(),
        sha256_map=sha256_map,
        readonly_status="lockdown" if lockdown else "audit_only",
        lockdown=lockdown,
    )


def _hash_workspace(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith(".yizijue/"):
            continue
        result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _lockdown(root: Path) -> None:
    for path in root.rglob("*"):
        try:
            if path.is_file():
                os.chmod(path, 0o444)
            elif path.is_dir():
                os.chmod(path, 0o555)
        except PermissionError:
            continue
