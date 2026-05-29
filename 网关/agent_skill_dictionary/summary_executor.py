from __future__ import annotations

from pathlib import Path
from typing import Any

from .audit import append_audit_record, build_evidence_record


def summarize_active_context(
    active_context: dict[str, Any],
    audit_log_path: str | Path | None = None,
) -> dict[str, Any]:
    markdown = _format_markdown(active_context)
    evidence = build_evidence_record(
        command="summarize_active_context",
        exit_code=0,
        stdout=markdown,
        stderr="",
    )
    if audit_log_path is not None:
        evidence = append_audit_record(audit_log_path, evidence)
    return {
        "ok": True,
        "markdown": markdown,
        "evidence": evidence,
    }


def _format_markdown(active_context: dict[str, Any]) -> str:
    files = active_context.get("inspect_files", []) or []
    native_card = str(active_context.get("native_inspect_card_text", "") or "")
    snippets = active_context.get("inspect_snippets", {}) or {}
    guard_findings = active_context.get("guard_findings", []) or []
    lines = [
        "# OneWord Handoff Summary",
        "",
        f"- Original request: {active_context.get('original_request', '')}",
        f"- Current state: {active_context.get('current_state', '')}",
        f"- Last state: {active_context.get('last_state', '')}",
        f"- Last ok: {active_context.get('last_ok')}",
        f"- Last exit code: {active_context.get('last_exit_code')}",
        f"- Verification exit code: {active_context.get('verification_exit_code')}",
        f"- Guard Risk: {active_context.get('guard_risk')}",
        f"- Last evidence SHA-256: {active_context.get('last_evidence_sha256')}",
        "",
        "## Inspect Files",
    ]
    if files:
        lines.extend(f"- {path}" for path in files)
    else:
        lines.append("- None")
    if native_card:
        lines.extend(["", "## Native Inspect Card", "```text", native_card.rstrip(), "```"])
    else:
        lines.extend(["", "## Snippets"])
    if snippets and not native_card:
        for path, snippet in snippets.items():
            lines.extend([f"### {path}", "```text", str(snippet).rstrip(), "```"])
    elif not native_card:
        lines.append("None")
    lines.extend(["", "## Guard Findings"])
    if guard_findings:
        for finding in guard_findings:
            file_name = finding.get("file")
            line_number = finding.get("line")
            pattern = finding.get("pattern")
            severity = finding.get("severity")
            lines.append(f"- {file_name}:{line_number} [{severity}] {pattern}")
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"
