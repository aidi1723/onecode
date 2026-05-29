from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

from .audit import append_audit_record, build_evidence_record


def archive_markdown(
    markdown: str,
    memory_dir: str | Path,
    title: str = "OneWord Handoff Summary",
    audit_log_path: str | Path | None = None,
) -> dict[str, Any]:
    target_dir = Path(memory_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = _filename(title)
    path = target_dir / filename
    path.write_text(markdown, encoding="utf-8")
    evidence = build_evidence_record(
        command=f"archive_markdown {path}",
        exit_code=0,
        stdout=str(path),
        stderr="",
    )
    if audit_log_path is not None:
        evidence = append_audit_record(audit_log_path, evidence)
    return {
        "ok": True,
        "path": str(path),
        "evidence": evidence,
    }


def _filename(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower()).strip("-")
    if not slug:
        slug = "oneword-summary"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{stamp}-{slug}.md"
