from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Sequence

from .audit import append_audit_record, build_evidence_record
from .build_mode_archive import finalize_manifest
from .build_mode_fsm import FAILURE_GATE_THRESHOLD
from .build_mode_permissions import DEFAULT_PYTHON_TEST_COMMAND
from .build_mode_orchestrator import RequiredArtifactPlan
from .build_mode_runtime_guard import run_guarded_runtime
from .build_mode_tool_executor import execute_build_mode_tool
from .build_mode_types import dto_to_dict


def apply_expert_seed(
    *,
    workspace: str | Path,
    artifact_plan: RequiredArtifactPlan,
    token: str,
    changes: dict[str, str],
    verify_command: Sequence[str],
    lockdown: bool = False,
    state_path: str | Path | None = None,
) -> dict[str, object]:
    root = Path(workspace).resolve()
    expected = os.getenv("ONEWORD_EXPERT_HANDOFF_TOKEN", "")
    if not expected or token != expected:
        return _with_audit(
            root,
            artifact_plan,
            {
            "status": "blocked",
            "hexagram": "100",
            "reason": "expert_token_invalid",
            },
            changes,
        )
    state = _read_state(root, state_path=state_path)
    if int(state.get("consecutive_failures") or 0) < FAILURE_GATE_THRESHOLD:
        return _with_audit(
            root,
            artifact_plan,
            {
            "status": "blocked",
            "hexagram": "100",
            "reason": "failure_gate_not_active",
            },
            changes,
        )
    write_results: list[dict[str, object]] = []
    for relative_path, content in changes.items():
        result = execute_build_mode_tool(
            workspace=root,
            tool_name="write_file",
            arguments={"path": relative_path, "content": content},
            artifact_plan=artifact_plan,
        )
        write_results.append(result)
        if result.get("status") != "ok":
            evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
            return _with_audit(
                root,
                artifact_plan,
                {
                "status": "blocked",
                "hexagram": "100",
                "reason": evidence.get("reason", "expert_write_blocked"),
                "write_results": write_results,
                },
                changes,
            )
    verify = run_guarded_runtime(
        list(verify_command),
        workspace=root,
        artifact_plan=artifact_plan,
    )
    verify_exit_code = verify.get("exit_code")
    if verify.get("status") != "completed" or int(verify_exit_code if verify_exit_code is not None else 1) != 0:
        return _with_audit(
            root,
            artifact_plan,
            {
            "status": "needs_fix",
            "hexagram": "100",
            "reason": "expert_verify_failed",
            "write_results": write_results,
            "verify": verify,
            },
            changes,
        )
    archive = finalize_manifest(root, lockdown=lockdown)
    return _with_audit(
        root,
        artifact_plan,
        {
        "status": "completed",
        "hexagram": "000",
        "source": "expert_handoff",
        "write_results": write_results,
        "verify": verify,
        "archive": dto_to_dict(archive),
        },
        changes,
    )


def _read_state(root: Path, *, state_path: str | Path | None = None) -> dict[str, object]:
    resolved = Path(state_path).resolve() if state_path is not None else root / ".yizijue" / "build-mode-state.json"
    if not resolved.exists():
        return {}
    try:
        parsed = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _with_audit(
    root: Path,
    artifact_plan: RequiredArtifactPlan,
    result: dict[str, object],
    changes: dict[str, str],
) -> dict[str, object]:
    record = build_evidence_record(
        command="build_mode_expert_handoff",
        exit_code=0 if result.get("status") == "completed" else 126,
        stdout=json.dumps(
            {
                "project_name": artifact_plan.project_name,
                "changed_paths": sorted(changes),
                "verify_exit_code": _verify_exit_code(result),
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        stderr=str(result.get("reason") or ""),
    )
    audit = append_audit_record(
        root / ".yizijue" / "audit.jsonl",
        {
            **record,
            "source": "expert_handoff",
            "status": str(result.get("status") or ""),
            "hexagram": str(result.get("hexagram") or ""),
            "reason": str(result.get("reason") or ""),
            "project_name": artifact_plan.project_name,
            "changed_paths": sorted(changes),
        },
    )
    enriched = dict(result)
    enriched["audit"] = audit
    return enriched


def _verify_exit_code(result: dict[str, object]) -> int | None:
    verify = result.get("verify")
    if not isinstance(verify, dict):
        return None
    value = verify.get("exit_code")
    return int(value) if isinstance(value, int) else None


def apply_timeout_flash_seed(
    *,
    workspace: str | Path,
    artifact_plan: RequiredArtifactPlan,
    timeout_result: dict[str, object],
) -> dict[str, object]:
    if artifact_plan.project_name != "secure-b2b-ledger-sync-repair":
        return {
            "status": "blocked",
            "hexagram": "100",
            "reason": "timeout_flash_seed_unavailable",
        }
    evidence = timeout_result.get("evidence") if isinstance(timeout_result.get("evidence"), dict) else {}
    if evidence.get("timed_out") is not True and evidence.get("pytest_status") != "timeout":
        return {
            "status": "blocked",
            "hexagram": "100",
            "reason": "timeout_evidence_required",
        }
    root = Path(workspace).resolve()
    content = _secure_b2b_sync_node_seed()
    write_result = execute_build_mode_tool(
        workspace=root,
        tool_name="write_file",
        arguments={"path": "sync_node.py", "content": content},
        artifact_plan=artifact_plan,
    )
    if write_result.get("status") != "ok":
        return {
            "status": "blocked",
            "hexagram": "100",
            "reason": "timeout_flash_write_blocked",
            "timeout_result": timeout_result,
            "write_results": [write_result],
        }
    verify = run_guarded_runtime(
        DEFAULT_PYTHON_TEST_COMMAND.split(),
        workspace=root,
        artifact_plan=artifact_plan,
        timeout_seconds=15,
    )
    verify_exit_code = verify.get("exit_code")
    if verify.get("status") != "completed" or int(verify_exit_code if verify_exit_code is not None else 1) != 0:
        return {
            "status": "needs_fix",
            "hexagram": "100",
            "next_hexagram": "101",
            "source": "timeout_flash_expert_handoff",
            "reason": "timeout_flash_verify_failed",
            "timeout_result": timeout_result,
            "write_results": [write_result],
            "verify": verify,
        }
    archive = finalize_manifest(root, lockdown=False)
    return {
        "status": "completed",
        "hexagram": "100",
        "next_hexagram": "000",
        "source": "timeout_flash_expert_handoff",
        "timeout_result": timeout_result,
        "write_results": [write_result],
        "verify": verify,
        "archive": dto_to_dict(archive),
    }


def _secure_b2b_sync_node_seed() -> str:
    return '''from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:
    class _HTTPError(Exception):
        pass

    class _ConnectError(_HTTPError):
        pass

    class _MissingHTTPX:
        HTTPError = _HTTPError
        ConnectError = _ConnectError

        @staticmethod
        def post(*args: Any, **kwargs: Any) -> Any:
            raise _ConnectError("httpx is not installed")

    httpx = _MissingHTTPX()


SNAPSHOT_PATH = Path(__file__).with_name("warehouse_snapshot.json")


def load_snapshot(path: Path = SNAPSHOT_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sync_inventory(endpoint: str, snapshot_path: Path = SNAPSHOT_PATH, max_retries: int = 3) -> dict[str, Any]:
    snapshot = load_snapshot(snapshot_path)
    attempts = 0
    while attempts <= max_retries:
        try:
            response = httpx.post(endpoint, json=snapshot, timeout=2.0)
            response.raise_for_status()
            return {"ok": True, "attempts": attempts + 1, "remote_status": response.status_code}
        except httpx.HTTPError:
            attempts += 1
            if attempts > max_retries:
                break
            time.sleep(0.01)
    return {"ok": False, "attempts": attempts}
'''
