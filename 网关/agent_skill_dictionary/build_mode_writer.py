from __future__ import annotations

import hashlib
from pathlib import Path

from .build_mode_types import ViolationEvidence, WriteEvidence


def safe_write(workspace_root: str | Path, relative_path: str, content: str) -> WriteEvidence | ViolationEvidence:
    root = Path(workspace_root).resolve()
    if not str(relative_path).strip():
        return ViolationEvidence(
            blocked_action="write:",
            reason="empty_path",
            source="scoped_writer",
        )
    target = (root / relative_path).resolve()
    if target != root and root not in target.parents:
        return ViolationEvidence(
            blocked_action=f"write:{relative_path}",
            reason="path_escape",
            source="scoped_writer",
        )
    if _is_sensitive_path(target):
        return ViolationEvidence(
            blocked_action=f"write:{relative_path}",
            reason="sensitive_path",
            source="scoped_writer",
        )
    if target == root or target.is_dir():
        return ViolationEvidence(
            blocked_action=f"write:{relative_path}",
            reason="directory_path",
            source="scoped_writer",
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    rel = target.relative_to(root).as_posix()
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return WriteEvidence(
        ok=True,
        changed_files=(rel,),
        path_scope=str(root),
        patch_digest=digest,
    )


def _is_sensitive_path(path: Path) -> bool:
    text = path.as_posix()
    return any(part in text for part in ("/.ssh/", "/.codex/", "/.claude/"))
