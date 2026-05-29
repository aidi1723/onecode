from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

from .audit import verify_audit_chain
from .context_breaker import build_active_context
from .kernel_contract import KernelContractError, assert_runtime_contract
from .loader import load_dictionary
from .runner import run_oneword_task
from .tool_guard import preflight_tool_call


DEFAULT_DICTIONARY_PATH = "agent_skill_dictionary/programming-agent-skill-dictionary.json"


def run_golden_case_file(
    case_file: str | Path,
    workspace_parent: str | Path | None = None,
    dictionary_path: str | Path = DEFAULT_DICTIONARY_PATH,
) -> dict[str, Any]:
    cases = json.loads(Path(case_file).read_text(encoding="utf-8"))
    dictionary = load_dictionary(str(dictionary_path))
    parent_manager: TemporaryDirectory[str] | None = None
    if workspace_parent is None:
        parent_manager = TemporaryDirectory()
        parent = Path(parent_manager.name)
    else:
        parent = Path(workspace_parent)
        parent.mkdir(parents=True, exist_ok=True)

    try:
        results = [_run_case(case, parent, dictionary) for case in cases]
    finally:
        if parent_manager is not None:
            parent_manager.cleanup()

    failed = sum(1 for result in results if not result["ok"])
    return {
        "ok": failed == 0,
        "case_count": len(results),
        "failed": failed,
        "results": results,
    }


def _run_case(case: dict[str, Any], parent: Path, dictionary: dict[str, Any]) -> dict[str, Any]:
    task_id = str(case["task_id"])
    workspace = parent / task_id
    if workspace.exists():
        shutil.rmtree(workspace)
    template = case.get("workspace_template")
    if template:
        shutil.copytree(Path(str(template)), workspace)
    else:
        workspace.mkdir(parents=True)
    _write_workspace_files(workspace, case.get("workspace_files", {}))

    preflight_results = [
        _run_preflight_check(dictionary, check)
        for check in case.get("preflight_checks", [])
    ]

    started = time.monotonic()
    result = _run_oneword_for_case(case, workspace)
    latency_seconds = time.monotonic() - started

    history = list(result.get("history", []))
    active_context = build_active_context(
        str(case.get("input", "")),
        result.get("trace", [""])[-1] if result.get("trace") else "",
        history,
    )
    audit_path = result.get("audit_log_path")
    audit_verification = verify_audit_chain(audit_path) if audit_path else {"valid": False}

    expected_trace = list(case.get("expected_trace", []))
    actual_trace = list(result.get("trace", []))
    expected_status = case.get("expected_status")
    actual_status = result.get("status")
    compression_ratio = _compression_ratio(case, active_context)
    min_compression_ratio = float(case.get("min_compression_ratio", 0))
    forbidden_tool_attempts = sum(1 for item in preflight_results if not item["allowed"])
    preflight_match = all(item["matches"] for item in preflight_results)
    risk_match = _risk_matches(case, active_context)
    exit_code_match = _exit_code_matches(case, history)
    contract_result = _validate_contracts(case, preflight_results, history)

    checks = {
        "trace": actual_trace == expected_trace,
        "status": actual_status == expected_status,
        "preflight": preflight_match,
        "contract": contract_result["valid"],
        "audit": bool(audit_verification.get("valid")),
        "risk": risk_match,
        "exit_code": exit_code_match,
        "compression": compression_ratio >= min_compression_ratio,
    }
    return {
        "task_id": task_id,
        "expected_trace": expected_trace,
        "actual_trace": actual_trace,
        "trace_match": checks["trace"],
        "expected_status": expected_status,
        "actual_status": actual_status,
        "status_match": checks["status"],
        "preflight_match": checks["preflight"],
        "contract_validated": checks["contract"],
        "contract_errors": contract_result["errors"],
        "forbidden_tool_attempts": forbidden_tool_attempts,
        "final_status": actual_status,
        "exit_code": _latest_exit_code(history),
        "risk_level": active_context.get("guard_risk"),
        "latency_seconds": round(latency_seconds, 6),
        "token_compression_ratio": compression_ratio,
        "conformance_score": _conformance_score(preflight_results),
        "evidence_hash_validated": checks["audit"],
        "audit_log_path": audit_path,
        "ok": all(checks.values()),
        "checks": checks,
    }


def _run_oneword_for_case(case: dict[str, Any], workspace: Path) -> dict[str, Any]:
    kwargs = {
        "user_input": str(case.get("input", "")),
        "workspace": workspace,
        "enable_all": True,
        "verification_command": case.get("verification_command"),
        "patch_plan": case.get("patch_plan"),
        "enable_external_scanners": bool(case.get("enable_external_scanners", False)),
        "require_guard_scanner": bool(case.get("require_guard_scanner", False)),
        "guard_scanner_types": case.get("guard_scanner_types"),
    }
    if case.get("mock_missing_scanners"):
        with patch("agent_skill_dictionary.guard_executor.shutil.which", return_value=None):
            return run_oneword_task(**kwargs)
    return run_oneword_task(**kwargs)


def _write_workspace_files(workspace: Path, files: dict[str, str]) -> None:
    for relative, content in files.items():
        target = (workspace / relative).resolve()
        if workspace.resolve() not in target.parents and target != workspace.resolve():
            raise ValueError(f"golden file escapes workspace: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(content), encoding="utf-8")


def _run_preflight_check(dictionary: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]:
    decision = preflight_tool_call(
        dictionary,
        active_code=str(check.get("active_code", "")),
        tool_name=str(check.get("tool_name", "")),
        arguments=check.get("arguments", {}),
    )
    expected_allowed = bool(check.get("expected_allowed", False))
    return {
        "active_code": check.get("active_code"),
        "tool": check.get("tool_name"),
        "arguments": check.get("arguments", {}),
        "allowed": bool(decision.get("allowed")),
        "expected_allowed": expected_allowed,
        "matches": bool(decision.get("allowed")) == expected_allowed,
        "violations": decision.get("violations", []),
    }


def _validate_contracts(
    case: dict[str, Any],
    preflight_results: list[dict[str, Any]],
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    for item in preflight_results:
        if item["expected_allowed"]:
            continue
        try:
            assert_runtime_contract(
                active_opcode=str(item["active_code"]),
                model_request={"tools": [{"type": "function", "function": {"name": item["tool"]}}]},
                sandbox_response={},
            )
        except KernelContractError:
            continue
        errors.append(
            {
                "active_code": item["active_code"],
                "tool": item["tool"],
                "reason": "forbidden_tool_not_rejected_by_contract",
            }
        )

    expected_exit_code = case.get("expected_exit_code")
    if expected_exit_code not in (None, 0):
        try:
            assert_runtime_contract(
                active_opcode="测",
                model_request={"tools": [{"type": "function", "function": {"name": "run_pytest"}}]},
                sandbox_response={
                    "exit_code": expected_exit_code,
                    "next_suggested_state": case.get("invalid_next_state_probe", "总"),
                },
            )
        except KernelContractError:
            pass
        else:
            errors.append({"active_code": "测", "reason": "nonzero_exit_allowed_success_route"})

    return {"valid": not errors, "errors": errors}


def _risk_matches(case: dict[str, Any], active_context: dict[str, Any]) -> bool:
    expected = case.get("expected_risk")
    if expected is None:
        return True
    return active_context.get("guard_risk") == expected


def _exit_code_matches(case: dict[str, Any], history: list[dict[str, Any]]) -> bool:
    expected = case.get("expected_exit_code")
    if expected is None:
        return True
    return _latest_exit_code(history) == expected


def _latest_exit_code(history: list[dict[str, Any]]) -> int | None:
    for item in reversed(history):
        result = item.get("result", {}) if isinstance(item.get("result"), dict) else {}
        if "exit_code" in result:
            return result["exit_code"]
    return None


def _compression_ratio(case: dict[str, Any], active_context: dict[str, Any]) -> float:
    noise_chars = int(case.get("history_noise_chars", 0))
    if noise_chars <= 0:
        return 1.0
    compacted = len(json.dumps(active_context, ensure_ascii=False, sort_keys=True))
    return max(0.0, 1.0 - (compacted / noise_chars))


def _conformance_score(preflight_results: list[dict[str, Any]]) -> float:
    if not preflight_results:
        return 1.0
    return sum(1 for item in preflight_results if item["matches"]) / len(preflight_results)
