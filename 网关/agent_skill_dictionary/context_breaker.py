from __future__ import annotations

from typing import Any


def build_active_context(
    original_request: str,
    current_state: str,
    history: list[dict[str, Any]],
    max_files: int = 50,
    max_snippets: int = 10,
    runtime_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    last = history[-1] if history else {}
    last_result = last.get("result", {}) if isinstance(last.get("result", {}), dict) else {}
    last_evidence = last_result.get("evidence", {})
    inspect_result = _latest_result_for_state(history, "查")
    verify_result = _latest_result_for_state(history, "测")
    guard_result = _latest_result_for_state(history, "卫")
    active = {
        "original_request": original_request,
        "current_state": current_state,
        "last_state": last.get("state"),
        "last_ok": last_result.get("ok"),
        "last_evidence_sha256": last_evidence.get("sha256") if isinstance(last_evidence, dict) else None,
        "last_exit_code": last_result.get("exit_code"),
        "inspect_files": list(inspect_result.get("files", []))[:max_files],
        "native_inspect_card_text": str(inspect_result.get("native_card_text", ""))[:1600],
        "inspect_snippets": _trim_snippets(inspect_result.get("snippets", {}), max_snippets),
        "verification_exit_code": verify_result.get("exit_code"),
        "guard_risk": guard_result.get("risk"),
        "guard_findings": _trim_findings(guard_result.get("findings", [])),
    }
    if runtime_metadata:
        active.update(_compact_runtime_metadata(runtime_metadata))
    return active


def _latest_result_for_state(history: list[dict[str, Any]], state: str) -> dict[str, Any]:
    for item in reversed(history):
        if item.get("state") == state and isinstance(item.get("result"), dict):
            return item["result"]
    return {}


def _trim_snippets(value: Any, max_snippets: int) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, str] = {}
    for key in sorted(value)[:max_snippets]:
        result[str(key)] = str(value[key])[:400]
    return result


def _trim_findings(value: Any, max_findings: int = 10) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    findings: list[dict[str, Any]] = []
    for item in value[:max_findings]:
        if not isinstance(item, dict):
            continue
        findings.append(
            {
                "file": item.get("file"),
                "line": item.get("line"),
                "pattern": item.get("pattern"),
                "severity": item.get("severity"),
                "snippet": str(item.get("snippet", ""))[:160],
            }
        )
    return findings


def _compact_runtime_metadata(value: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    if "retry_count" in value:
        compact["retry_count"] = int(value.get("retry_count", 0))
    transitions = value.get("transitions")
    if isinstance(transitions, list):
        compact["transitions"] = [
            _compact_transition(item)
            for item in transitions[-5:]
            if isinstance(item, dict)
        ]
    return compact


def _compact_transition(value: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "from",
        "from_trigram",
        "to",
        "to_trigram",
        "trigger",
        "retry_count",
        "evidence_sha256",
    )
    return {key: value.get(key) for key in keys if key in value}
