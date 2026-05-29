from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .audit import append_audit_record, build_evidence_record


def apply_controlled_patch(
    workspace_root: str | Path,
    patch_plan: list[dict[str, Any]],
    audit_log_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(workspace_root).resolve()
    if not patch_plan:
        evidence = build_evidence_record(
            command=f"apply_controlled_patch {root}",
            exit_code=2,
            stdout="[]",
            stderr="empty_patch_plan",
        )
        if audit_log_path is not None:
            evidence = append_audit_record(audit_log_path, evidence)
        return {
            "ok": False,
            "changed_files": [],
            "error": "empty_patch_plan",
            "evidence": evidence,
        }
    changed_files: list[str] = []
    for change in patch_plan:
        relative = str(change.get("path", ""))
        if not relative:
            raise ValueError("patch path must be non-empty")
        target = (root / relative).resolve()
        if target != root and root not in target.parents:
            raise ValueError("patch path must stay inside workspace_root")
        content = str(change.get("content", ""))
        expected_sha256 = change.get("expected_sha256")
        if target.exists():
            if not isinstance(expected_sha256, str) or not expected_sha256:
                raise ValueError("existing patch target requires expected_sha256")
            current_sha256 = _sha256_text(target.read_text(encoding="utf-8"))
            if current_sha256 != expected_sha256:
                raise ValueError("existing patch target sha256 mismatch")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        changed_files.append(target.relative_to(root).as_posix())

    stdout = json.dumps(changed_files, ensure_ascii=False, sort_keys=True)
    evidence = build_evidence_record(
        command=f"apply_controlled_patch {root}",
        exit_code=0,
        stdout=stdout,
        stderr="",
    )
    if audit_log_path is not None:
        evidence = append_audit_record(audit_log_path, evidence)
    return {
        "ok": True,
        "changed_files": changed_files,
        "evidence": evidence,
    }


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
