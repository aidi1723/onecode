from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_skill_dictionary.golden_task_harness import run_golden_case_file
from agent_skill_dictionary.kernel_contract import KernelContractError, validate_summary_contract


DEFAULT_CASES_PATH = Path("tests/golden_cases/eight_word_core.json")
DEFAULT_OUTPUT_JSON = Path("reports/golden-matrix.json")
DEFAULT_OUTPUT_MD = Path("reports/golden-matrix.md")


def run_matrix(
    cases_path: str | Path = DEFAULT_CASES_PATH,
    models: list[str] | None = None,
    modes: list[str] | None = None,
    base_url: str = "http://127.0.0.1:8080",
    token: str | None = None,
    output_json: str | Path = DEFAULT_OUTPUT_JSON,
    output_md: str | Path = DEFAULT_OUTPUT_MD,
    workspace_parent: str | Path | None = None,
    chat_stream: bool = False,
    concurrency: int = 1,
) -> dict[str, Any]:
    selected_models = models or ["gpt-5-mini"]
    selected_modes = modes or ["local"]
    cases_file = Path(cases_path)
    cases = _load_cases(cases_file)
    workspace_root = Path(workspace_parent or ".oneword/golden_matrix_workspaces")
    workspace_root.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for model in selected_models:
        for mode in selected_modes:
            if mode == "local":
                results.extend(_run_local_mode(cases_file, cases, model, mode, workspace_root))
            elif mode == "run":
                results.extend(
                    _run_gateway_run_mode(
                        cases,
                        model,
                        mode,
                        base_url,
                        token,
                        workspace_root,
                        concurrency=concurrency,
                    )
                )
            elif mode == "chat":
                results.extend(
                    _run_gateway_chat_mode(
                        cases,
                        model,
                        mode,
                        base_url,
                        token,
                        workspace_root,
                        chat_stream=chat_stream,
                        concurrency=concurrency,
                    )
                )
            elif mode == "anthropic":
                results.extend(
                    _run_gateway_anthropic_mode(
                        cases,
                        model,
                        mode,
                        base_url,
                        token,
                        workspace_root,
                        chat_stream=chat_stream,
                        concurrency=concurrency,
                    )
                )
            else:
                raise ValueError(f"unsupported golden matrix mode: {mode}")

    report = {
        "ok": all(row.get("ok") for row in results),
        "case_count": len(results),
        "models": selected_models,
        "modes": selected_modes,
        "results": results,
    }
    _write_json(Path(output_json), report)
    _write_markdown(Path(output_md), report)
    return report


def _run_local_mode(
    cases_file: Path,
    cases: list[dict[str, Any]],
    model: str,
    mode: str,
    workspace_root: Path,
) -> list[dict[str, Any]]:
    model_root = workspace_root / _slug(model) / mode
    report = run_golden_case_file(cases_file, workspace_parent=model_root)
    rows: list[dict[str, Any]] = []
    case_by_id = {case["task_id"]: case for case in cases}
    for row in report["results"]:
        task_id = str(row["task_id"])
        session_id = _session_id(model, mode, task_id)
        rows.append(
            _normalize_row(
                {
                    **row,
                    "model": model,
                    "gateway_mode": mode,
                    "session_id": session_id,
                    "workspace": str(model_root / task_id),
                    "description": case_by_id.get(task_id, {}).get("description"),
                    "blocked": row.get("actual_status") == "halted",
                    "http_status": None,
                    "error_type": None,
                }
            )
        )
    return rows


def _run_gateway_run_mode(
    cases: list[dict[str, Any]],
    model: str,
    mode: str,
    base_url: str,
    token: str | None,
    workspace_root: Path,
    concurrency: int = 1,
) -> list[dict[str, Any]]:
    return _map_cases(
        cases,
        concurrency,
        lambda case: _run_gateway_run_case(case, model, mode, base_url, token, workspace_root),
    )


def _run_gateway_run_case(
    case: dict[str, Any],
    model: str,
    mode: str,
    base_url: str,
    token: str | None,
    workspace_root: Path,
) -> dict[str, Any]:
        task_id = str(case["task_id"])
        session_id = _session_id(model, mode, task_id)
        workspace = workspace_root / _slug(model) / mode / session_id
        if _is_local_only_case(case):
            return _skipped_row(case, model, mode, session_id, workspace, "local_only_mock_case")
        _prepare_workspace(workspace, case.get("workspace_files", {}))
        body = _run_request_body(case, model, session_id, workspace)
        started = time.monotonic()
        payload, status_code = _json_request(
            "POST",
            f"{base_url.rstrip('/')}/v1/yizijue/run",
            json_body=body,
            token=token,
        )
        latency = time.monotonic() - started
        return _gateway_run_row(case, model, mode, session_id, workspace, payload, status_code, latency)


def _run_gateway_chat_mode(
    cases: list[dict[str, Any]],
    model: str,
    mode: str,
    base_url: str,
    token: str | None,
    workspace_root: Path,
    chat_stream: bool,
    concurrency: int = 1,
) -> list[dict[str, Any]]:
    return _map_cases(
        cases,
        concurrency,
        lambda case: _run_gateway_chat_case(
            case,
            model,
            mode,
            base_url,
            token,
            workspace_root,
            chat_stream=chat_stream,
        ),
    )


def _run_gateway_chat_case(
    case: dict[str, Any],
    model: str,
    mode: str,
    base_url: str,
    token: str | None,
    workspace_root: Path,
    chat_stream: bool,
) -> dict[str, Any]:
        task_id = str(case["task_id"])
        session_id = _session_id(model, mode, task_id)
        workspace = workspace_root / _slug(model) / mode / session_id
        if _is_local_only_case(case):
            return _skipped_row(case, model, mode, session_id, workspace, "local_only_mock_case")
        _prepare_workspace(workspace, case.get("workspace_files", {}))
        body = _chat_request_body(case, model, session_id, workspace, chat_stream=chat_stream)
        started = time.monotonic()
        payload, status_code = _json_request(
            "POST",
            f"{base_url.rstrip('/')}/v1/chat/completions",
            json_body=body,
            token=token,
        )
        latency = time.monotonic() - started
        return _gateway_chat_row(case, model, mode, session_id, workspace, payload, status_code, latency)


def _run_gateway_anthropic_mode(
    cases: list[dict[str, Any]],
    model: str,
    mode: str,
    base_url: str,
    token: str | None,
    workspace_root: Path,
    chat_stream: bool,
    concurrency: int = 1,
) -> list[dict[str, Any]]:
    return _map_cases(
        cases,
        concurrency,
        lambda case: _run_gateway_anthropic_case(
            case,
            model,
            mode,
            base_url,
            token,
            workspace_root,
            chat_stream=chat_stream,
        ),
    )


def _run_gateway_anthropic_case(
    case: dict[str, Any],
    model: str,
    mode: str,
    base_url: str,
    token: str | None,
    workspace_root: Path,
    chat_stream: bool,
) -> dict[str, Any]:
        task_id = str(case["task_id"])
        session_id = _session_id(model, mode, task_id)
        workspace = workspace_root / _slug(model) / mode / session_id
        if _is_local_only_case(case):
            return _skipped_row(case, model, mode, session_id, workspace, "local_only_mock_case")
        _prepare_workspace(workspace, case.get("workspace_files", {}))
        body = _anthropic_request_body(case, model, session_id, workspace, chat_stream=chat_stream)
        started = time.monotonic()
        payload, status_code = _json_request(
            "POST",
            f"{base_url.rstrip('/')}/v1/messages",
            json_body=body,
            token=token,
        )
        latency = time.monotonic() - started
        return _gateway_chat_row(case, model, mode, session_id, workspace, payload, status_code, latency)


def _map_cases(
    cases: list[dict[str, Any]],
    concurrency: int,
    fn: Any,
) -> list[dict[str, Any]]:
    if concurrency <= 1:
        return [fn(case) for case in cases]
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        return list(executor.map(fn, cases))


def _gateway_run_row(
    case: dict[str, Any],
    model: str,
    mode: str,
    session_id: str,
    workspace: Path,
    payload: dict[str, Any],
    status_code: int,
    latency: float,
) -> dict[str, Any]:
    expected_trace = list(case.get("expected_trace", []))
    actual_trace = list(payload.get("trace", []))
    expected_status = case.get("expected_status")
    actual_status = payload.get("status")
    trace_match = actual_trace == expected_trace
    status_match = actual_status == expected_status
    return _normalize_row(
        {
            "task_id": case["task_id"],
            "description": case.get("description"),
            "model": model,
            "gateway_mode": mode,
            "session_id": session_id,
            "workspace": str(workspace),
            "expected_trace": expected_trace,
            "actual_trace": actual_trace,
            "trace_match": trace_match,
            "expected_status": expected_status,
            "actual_status": actual_status,
            "status_match": status_match,
            "preflight_match": None,
            "contract_validated": trace_match and status_match,
            "contract_errors": [],
            "forbidden_tool_attempts": 0,
            "final_status": actual_status,
            "exit_code": _latest_exit_code(payload.get("history", [])),
            "retry_count_to_success": _retry_count_to_success(payload),
            "risk_level": _latest_risk(payload),
            "latency_seconds": round(latency, 6),
            "token_compression_ratio": None,
            "summary_information_density": None,
            "summary_contract_validated": None,
            "conformance_score": 1.0 if status_code < 400 else 0.0,
            "tool_mask_match": True,
            "evidence_hash_validated": bool(payload.get("audit_log_path")),
            "blocked": actual_status == "halted" or status_code >= 400,
            "http_status": status_code,
            "error_type": _error_type(payload),
            "ok": status_code < 500 and trace_match and status_match,
        }
    )


def _gateway_chat_row(
    case: dict[str, Any],
    model: str,
    mode: str,
    session_id: str,
    workspace: Path,
    payload: dict[str, Any],
    status_code: int,
    latency: float,
) -> dict[str, Any]:
    gateway = payload.get("yizijue_gateway", {}) if isinstance(payload, dict) else {}
    tool_guard = gateway.get("tool_guard", {}) if isinstance(gateway, dict) else {}
    active_code = gateway.get("active_code")
    actual_trace = [active_code] if active_code else []
    expected_trace = list(case.get("expected_trace", []))
    blocked = bool(gateway.get("blocked")) or status_code >= 400
    tool_mask_match = bool(tool_guard.get("allowed", True)) or blocked
    trace_match = bool(actual_trace) and active_code in expected_trace
    summary_contract = _summary_contract_result(case, payload, active_code)
    contract_validated = tool_mask_match and summary_contract["valid"]
    return _normalize_row(
        {
            "task_id": case["task_id"],
            "description": case.get("description"),
            "model": model,
            "gateway_mode": mode,
            "session_id": session_id,
            "workspace": str(workspace),
            "expected_trace": expected_trace,
            "actual_trace": actual_trace,
            "trace_match": trace_match,
            "expected_status": case.get("expected_status"),
            "actual_status": "blocked" if blocked else "forwarded",
            "status_match": None,
            "preflight_match": None,
            "contract_validated": contract_validated,
            "contract_errors": _chat_contract_errors(tool_mask_match, summary_contract),
            "forbidden_tool_attempts": 0 if tool_mask_match else 1,
            "final_status": "blocked" if blocked else "forwarded",
            "exit_code": None,
            "risk_level": None,
            "latency_seconds": round(latency, 6),
            "token_compression_ratio": None,
            "retry_count_to_success": None,
            "summary_information_density": summary_contract["information_density"],
            "summary_contract_validated": summary_contract["valid"],
            "conformance_score": 1.0 if tool_mask_match else 0.0,
            "evidence_hash_validated": False,
            "blocked": blocked,
            "http_status": status_code,
            "error_type": _error_type(payload),
            "tool_mask_match": tool_mask_match,
            "ok": status_code < 500 and tool_mask_match and trace_match and summary_contract["valid"],
        }
    )


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        "model": "",
        "gateway_mode": "",
        "session_id": "",
        "workspace": "",
        "trace_match": False,
        "preflight_match": None,
        "contract_validated": False,
        "forbidden_tool_attempts": 0,
        "final_status": row.get("actual_status"),
        "exit_code": None,
        "risk_level": None,
        "latency_seconds": None,
        "token_compression_ratio": None,
        "retry_count_to_success": None,
        "summary_information_density": None,
        "summary_contract_validated": None,
        "conformance_score": None,
        "tool_mask_match": None,
        "evidence_hash_validated": False,
        "blocked": False,
        "http_status": None,
        "error_type": None,
        "skipped": False,
        "skip_reason": None,
        "ok": False,
    }
    return {**defaults, **row}


def _skipped_row(
    case: dict[str, Any],
    model: str,
    mode: str,
    session_id: str,
    workspace: Path,
    reason: str,
) -> dict[str, Any]:
    return _normalize_row(
        {
            "task_id": case["task_id"],
            "description": case.get("description"),
            "model": model,
            "gateway_mode": mode,
            "session_id": session_id,
            "workspace": str(workspace),
            "expected_trace": list(case.get("expected_trace", [])),
            "actual_trace": [],
            "trace_match": None,
            "expected_status": case.get("expected_status"),
            "actual_status": "skipped",
            "status_match": None,
            "contract_validated": True,
            "final_status": "skipped",
            "tool_mask_match": None,
            "skipped": True,
            "skip_reason": reason,
            "ok": True,
        }
    )


def _is_local_only_case(case: dict[str, Any]) -> bool:
    return bool(case.get("mock_missing_scanners"))


def _run_request_body(
    case: dict[str, Any],
    model: str,
    session_id: str,
    workspace: Path,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "input": case.get("input", ""),
        "workspace": str(workspace),
        "model": model,
        "session_id": session_id,
        "enable_all": True,
        "verification_command": case.get("verification_command"),
        "patch_plan": case.get("patch_plan"),
        "enable_external_scanners": bool(case.get("enable_external_scanners", False)),
        "require_guard_scanner": bool(case.get("require_guard_scanner", False)),
        "guard_scanner_types": case.get("guard_scanner_types"),
    }
    return {key: value for key, value in body.items() if value is not None}


def _chat_request_body(
    case: dict[str, Any],
    model: str,
    session_id: str,
    workspace: Path,
    chat_stream: bool,
) -> dict[str, Any]:
    return {
        "model": model,
        "stream": chat_stream,
        "metadata": {
            "oneword_session_id": session_id,
            "oneword_workspace": str(workspace),
        },
        "messages": [
            {
                "role": "user",
                "content": str(case.get("input", "")),
            }
        ],
        "tools": [
            _tool("read_file"),
            _tool("write_file"),
            _tool("edit_scoped_file"),
            _tool("bash"),
            _tool("run_pytest"),
            _tool("run_npm_test"),
            _tool("capture_coverage"),
        ],
    }


def _tool(name: str) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"Golden matrix probe tool: {name}",
            "parameters": {"type": "object", "properties": {}},
        },
    }


def _anthropic_request_body(
    case: dict[str, Any],
    model: str,
    session_id: str,
    workspace: Path,
    chat_stream: bool,
) -> dict[str, Any]:
    return {
        "model": model,
        "max_tokens": 1024,
        "stream": chat_stream,
        "metadata": {
            "oneword_session_id": session_id,
            "oneword_workspace": str(workspace),
        },
        "messages": [
            {
                "role": "user",
                "content": str(case.get("input", "")),
            }
        ],
        "tools": [
            _anthropic_tool("read_file"),
            _anthropic_tool("write_file"),
            _anthropic_tool("edit_scoped_file"),
            _anthropic_tool("bash"),
            _anthropic_tool("run_pytest"),
            _anthropic_tool("run_npm_test"),
            _anthropic_tool("capture_coverage"),
        ],
    }


def _anthropic_tool(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "description": f"Golden matrix probe tool: {name}",
        "input_schema": {"type": "object", "properties": {}},
    }


def _json_request(
    method: str,
    url: str,
    json_body: dict[str, Any] | None = None,
    token: str | None = None,
    timeout: int = 120,
) -> tuple[dict[str, Any], int]:
    headers = {"content-type": "application/json"}
    if token:
        headers["authorization"] = f"Bearer {token}"
    data = json.dumps(json_body or {}).encode("utf-8") if json_body is not None else None
    request = urlrequest.Request(url, data=data, headers=headers, method=method)
    try:
        with urlrequest.urlopen(request, timeout=timeout) as response:
            return _decode_response(response.read()), _response_status(response)
    except urlerror.HTTPError as exc:
        try:
            return _decode_response(exc.read()), exc.code
        finally:
            exc.close()


def _decode_response(raw: bytes) -> dict[str, Any]:
    if not raw:
        return {}
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("expected JSON object response")
    return payload


def _response_status(response: Any) -> int:
    status = getattr(response, "status", 200)
    if isinstance(status, int):
        return status
    if isinstance(status, str) and status.isdigit():
        return int(status)
    return 200


def _prepare_workspace(workspace: Path, files: dict[str, str]) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    root = workspace.resolve()
    for relative, content in files.items():
        target = (workspace / relative).resolve()
        if root not in target.parents and target != root:
            raise ValueError(f"golden matrix file escapes workspace: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(content), encoding="utf-8")


def _load_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("golden case file must contain a JSON array")
    return payload


def _latest_exit_code(history: Any) -> int | None:
    if not isinstance(history, list):
        return None
    for item in reversed(history):
        if not isinstance(item, dict):
            continue
        result = item.get("result", {})
        if isinstance(result, dict) and "exit_code" in result:
            return result["exit_code"]
    return None


def _retry_count_to_success(payload: dict[str, Any]) -> int | None:
    history = payload.get("history", [])
    if not isinstance(history, list):
        return None
    verify_attempts = 0
    success_seen = False
    for item in history:
        if not isinstance(item, dict):
            continue
        result = item.get("result", {})
        if not isinstance(result, dict) or "exit_code" not in result:
            continue
        verify_attempts += 1
        if result.get("exit_code") == 0:
            success_seen = True
            break
    if success_seen:
        return max(0, verify_attempts - 1)
    if verify_attempts:
        return verify_attempts
    return None


def _summary_contract_result(
    case: dict[str, Any],
    payload: dict[str, Any],
    active_code: str | None,
) -> dict[str, Any]:
    if "总" not in list(case.get("expected_trace", [])) and active_code != "总":
        return {"valid": True, "errors": [], "information_density": None}
    summary_payload = _extract_summary_payload(payload)
    if summary_payload is None:
        return {"valid": bool(payload.get("yizijue_gateway", {}).get("blocked")), "errors": [], "information_density": None}
    try:
        validated = validate_summary_contract(summary_payload)
    except KernelContractError as exc:
        return {
            "valid": False,
            "errors": [{"reason": exc.reason, "details": exc.details}],
            "information_density": _information_density(summary_payload),
        }
    return {
        "valid": True,
        "errors": [],
        "information_density": _information_density(validated),
    }


def _extract_summary_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    for choice in payload.get("choices", []):
        if not isinstance(choice, dict):
            continue
        message = choice.get("message", {})
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _information_density(value: dict[str, Any]) -> float:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if not raw:
        return 0.0
    populated = sum(1 for item in value.values() if item not in (None, "", [], {}))
    return round(populated / len(raw), 6)


def _chat_contract_errors(
    tool_mask_match: bool,
    summary_contract: dict[str, Any],
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    if not tool_mask_match:
        errors.append({"reason": "tool_mask_mismatch"})
    errors.extend(summary_contract.get("errors", []))
    return errors


def _latest_risk(payload: dict[str, Any]) -> str | None:
    if payload.get("status") == "halted":
        snapshot = payload.get("snapshot", {})
        if isinstance(snapshot, dict):
            return snapshot.get("guard_risk")
    return None


def _error_type(payload: dict[str, Any]) -> str | None:
    error = payload.get("error", {}) if isinstance(payload, dict) else {}
    if isinstance(error, dict):
        return error.get("type")
    return None


def _write_json(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "task_id",
        "model",
        "gateway_mode",
        "expected_trace",
        "actual_trace",
        "trace_match",
        "contract_validated",
        "forbidden_tool_attempts",
        "retry_count_to_success",
        "final_status",
        "http_status",
        "latency_seconds",
        "conformance_score",
        "summary_information_density",
    ]
    lines = [
        "# OneWord Golden Matrix",
        "",
        f"- ok: `{report['ok']}`",
        f"- case_count: `{report['case_count']}`",
        f"- models: `{', '.join(report['models'])}`",
        f"- modes: `{', '.join(report['modes'])}`",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in report["results"]:
        lines.append("| " + " | ".join(_md_cell(row.get(header)) for header in headers) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _md_cell(value: Any) -> str:
    if isinstance(value, list):
        value = "[" + ", ".join(str(item) for item in value) + "]"
    if value is None:
        return ""
    return str(value).replace("|", "\\|").replace("\n", " ")


def _session_id(model: str, mode: str, task_id: str) -> str:
    return f"{_slug(model)}-{_slug(mode)}-{_slug(task_id)}"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower())
    return slug.strip("-") or "default"


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> dict[str, Any]:
    parser = argparse.ArgumentParser(description="Build a OneWord golden model comparison matrix.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES_PATH), help="Golden case JSON file.")
    parser.add_argument("--models", default="gpt-5-mini", help="Comma-separated model names.")
    parser.add_argument(
        "--modes",
        default="local",
        help="Comma-separated modes: local,run,chat,anthropic.",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8080", help="Gateway base URL.")
    parser.add_argument("--token", default=None, help="Optional ONEWORD_GATEWAY_TOKEN.")
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON), help="JSON report path.")
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD), help="Markdown report path.")
    parser.add_argument(
        "--workspace-parent",
        default=None,
        help="Parent directory for isolated per-model/per-case workspaces.",
    )
    parser.add_argument(
        "--chat-stream",
        action="store_true",
        help="Send stream=true in chat/anthropic modes to verify stream blocking behavior.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="HTTP case concurrency for run/chat/anthropic modes.",
    )
    args = parser.parse_args()

    report = run_matrix(
        cases_path=Path(args.cases),
        models=_parse_csv(args.models),
        modes=_parse_csv(args.modes),
        base_url=args.base_url,
        token=args.token,
        output_json=Path(args.output_json),
        output_md=Path(args.output_md),
        workspace_parent=Path(args.workspace_parent) if args.workspace_parent else None,
        chat_stream=args.chat_stream,
        concurrency=args.concurrency,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return report


if __name__ == "__main__":
    main()
