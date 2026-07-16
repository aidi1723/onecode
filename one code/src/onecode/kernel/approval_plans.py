from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import secrets
from tempfile import NamedTemporaryFile
import time
from typing import Any

from onecode.kernel.model_provider import ModelPlan, validate_model_plan
from onecode.kernel.execution_tools import default_tool_registry


PLAN_ID_PATTERN = re.compile(r"[a-f0-9]{32}\Z")
PLAN_STORE_VERSION = 1
MAX_PLAN_BYTES = 500_000
DEFAULT_MAX_PLAN_AGE_SECONDS = 3_600
ALLOWED_MODEL_METADATA = frozenset({"model", "model_provider", "safe_agent"})
GUARDED_TOOL_NAMES = frozenset({"write_text", "patch_text", "run_command"})


@dataclass(frozen=True)
class StoredApprovalPlan:
    plan_id: str
    workspace: str
    plan: ModelPlan
    model_metadata: dict[str, Any]
    plan_sha256: str
    created_at: float
    path: Path


def persist_approval_plan(
    workspace: Path,
    plan: ModelPlan,
    *,
    model_metadata: dict[str, Any],
) -> StoredApprovalPlan:
    root = Path(workspace).resolve()
    _validate_plan_tool_parameters(plan)
    metadata = _validated_model_metadata(model_metadata)
    plan_id = secrets.token_hex(16)
    created_at = time.time()
    plan_payload = model_plan_to_dict(plan)
    core = {
        "version": PLAN_STORE_VERSION,
        "plan_id": plan_id,
        "workspace": str(root),
        "created_at": created_at,
        "plan": plan_payload,
        "model_metadata": metadata,
    }
    plan_sha256 = _payload_sha256(core)
    document = {**core, "plan_sha256": plan_sha256}
    encoded = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    if len(encoded) > MAX_PLAN_BYTES:
        raise ValueError("approval_plan_too_large")
    directory = root / ".onecode" / "pending-plans"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{plan_id}.json"
    _atomic_write(path, encoded)
    return StoredApprovalPlan(plan_id, str(root), plan, metadata, plan_sha256, created_at, path)


def load_approval_plan(
    workspace: Path,
    plan_id: str,
    *,
    max_age_seconds: int = DEFAULT_MAX_PLAN_AGE_SECONDS,
) -> StoredApprovalPlan:
    _validate_load_request(plan_id, max_age_seconds)
    root = Path(workspace).resolve()
    path = root / ".onecode" / "pending-plans" / f"{plan_id}.json"
    return _load_approval_plan_path(root, plan_id, path, max_age_seconds=max_age_seconds)


def list_pending_approval_plans(
    workspace: Path, *, limit: int = 100
) -> tuple[list[StoredApprovalPlan], int]:
    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= 100
    ):
        raise ValueError("limit must be between 1 and 100")
    root = Path(workspace).resolve()
    directory = root / ".onecode" / "pending-plans"
    if not directory.is_dir():
        return [], 0
    paths = sorted(
        directory.glob("*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    plans: list[StoredApprovalPlan] = []
    skipped = 0
    for path in paths:
        if len(plans) >= limit:
            break
        try:
            plans.append(load_approval_plan(root, path.stem))
        except ValueError:
            skipped += 1
    return plans, skipped


def claim_approval_plan(
    workspace: Path,
    plan_id: str,
    *,
    max_age_seconds: int = DEFAULT_MAX_PLAN_AGE_SECONDS,
) -> StoredApprovalPlan:
    _validate_load_request(plan_id, max_age_seconds)
    root = Path(workspace).resolve()
    pending = root / ".onecode" / "pending-plans" / f"{plan_id}.json"
    executing_directory = root / ".onecode" / "executing-plans"
    executing_directory.mkdir(parents=True, exist_ok=True)
    claimed = executing_directory / f"{plan_id}.json"
    try:
        pending.replace(claimed)
    except FileNotFoundError as exc:
        archived = root / ".onecode" / "approval-plans" / f"{plan_id}.json"
        if claimed.exists():
            raise ValueError("approval_plan_in_progress") from exc
        if archived.exists():
            raise ValueError("approval_plan_already_resolved") from exc
        raise ValueError("approval_plan_not_found") from exc
    return _load_approval_plan_path(root, plan_id, claimed, max_age_seconds=max_age_seconds)


def _load_approval_plan_path(
    root: Path,
    plan_id: str,
    path: Path,
    *,
    max_age_seconds: int,
) -> StoredApprovalPlan:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise ValueError("approval_plan_not_found") from exc
    if len(raw) > MAX_PLAN_BYTES:
        raise ValueError("approval_plan_too_large")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("approval_plan_invalid") from exc
    if not isinstance(document, dict):
        raise ValueError("approval_plan_invalid")
    digest = document.pop("plan_sha256", None)
    if not isinstance(digest, str) or digest != _payload_sha256(document):
        raise ValueError("approval_plan_mismatch")
    if document.get("version") != PLAN_STORE_VERSION or document.get("plan_id") != plan_id:
        raise ValueError("approval_plan_mismatch")
    if document.get("workspace") != str(root):
        raise ValueError("approval_plan_workspace_mismatch")
    created_at = document.get("created_at")
    if isinstance(created_at, bool) or not isinstance(created_at, (int, float)):
        raise ValueError("approval_plan_invalid")
    if time.time() - float(created_at) > max_age_seconds:
        raise ValueError("approval_plan_expired")
    plan_payload = document.get("plan")
    if not isinstance(plan_payload, dict):
        raise ValueError("approval_plan_invalid")
    metadata = _validated_model_metadata(document.get("model_metadata"))
    plan = validate_model_plan(plan_payload)
    _validate_plan_tool_parameters(plan)
    return StoredApprovalPlan(
        plan_id=plan_id,
        workspace=str(root),
        plan=plan,
        model_metadata=metadata,
        plan_sha256=digest,
        created_at=float(created_at),
        path=path,
    )


def _validate_load_request(plan_id: str, max_age_seconds: int) -> None:
    if not isinstance(plan_id, str) or PLAN_ID_PATTERN.fullmatch(plan_id) is None:
        raise ValueError("invalid_plan_id")
    if isinstance(max_age_seconds, bool) or not isinstance(max_age_seconds, int) or max_age_seconds <= 0:
        raise ValueError("max_age_seconds must be positive")


def _validate_plan_tool_parameters(plan: ModelPlan) -> None:
    registry = default_tool_registry()
    calls: list[tuple[str, dict[str, Any]]] = []
    calls.extend(("write_text", {"path": asset.path, "content": asset.content}) for asset in plan.assets)
    calls.extend(
        (
            "patch_text",
            {
                "path": patch.path,
                "search_block": patch.search_block,
                "replace_block": patch.replace_block,
            },
        )
        for patch in plan.patches
    )
    calls.extend(
        (tool_call.tool_name, dict(tool_call.params))
        for step in plan.execution_steps
        for tool_call in step.tool_calls
    )
    for tool_name, params in calls:
        tool = registry.get(tool_name)
        if tool is None:
            raise ValueError(f"unsupported approval tool: {tool_name}")
        tool.plan_action(params)


def finalize_approval_plan(stored: StoredApprovalPlan, decision: str, result: dict[str, Any]) -> Path:
    if decision not in {"approved", "rejected"}:
        raise ValueError("invalid_approval_decision")
    archive = stored.path.parent.parent / "approval-plans"
    archive.mkdir(parents=True, exist_ok=True)
    path = archive / f"{stored.plan_id}.json"
    payload = {
        "version": PLAN_STORE_VERSION,
        "plan_id": stored.plan_id,
        "workspace": stored.workspace,
        "plan_sha256": stored.plan_sha256,
        "decision": decision,
        "resolved_at": time.time(),
        "result": _bounded_result_summary(result),
    }
    _atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    stored.path.unlink(missing_ok=True)
    return path


def model_plan_requires_approval(plan: ModelPlan) -> bool:
    if plan.assets or plan.patches:
        return True
    return any(
        tool.tool_name in GUARDED_TOOL_NAMES
        for step in plan.execution_steps
        for tool in step.tool_calls
    )


def model_plan_to_dict(plan: ModelPlan) -> dict[str, Any]:
    payload: dict[str, Any] = {"task": plan.task}
    if plan.assets:
        payload["assets"] = [{"path": item.path, "content": item.content} for item in plan.assets]
    if plan.patches:
        payload["patches"] = [
            {"path": item.path, "search_block": item.search_block, "replace_block": item.replace_block}
            for item in plan.patches
        ]
    if plan.execution_steps:
        payload["execution_plan"] = {
            "steps": [
                {
                    "id": step.id,
                    "description": step.description,
                    "depends_on": list(step.depends_on),
                    "mode": step.mode,
                    "tool_calls": [
                        {
                            "tool_name": tool.tool_name,
                            "description": tool.description,
                            "params": dict(tool.params),
                        }
                        for tool in step.tool_calls
                    ],
                }
                for step in plan.execution_steps
            ]
        }
    if plan.no_action_reason is not None:
        payload["no_action"] = {"reason": plan.no_action_reason}
    return payload


def _validated_model_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) - ALLOWED_MODEL_METADATA:
        raise ValueError("model_metadata contains disallowed fields")
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if len(encoded.encode("utf-8")) > 100_000:
        raise ValueError("model_metadata too large")
    return json.loads(encoded)


def _payload_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _atomic_write(path: Path, content: bytes) -> None:
    with NamedTemporaryFile("wb", dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temp = Path(handle.name)
        handle.write(content)
        handle.flush()
    temp.replace(path)


def _bounded_result_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        key: result.get(key)
        for key in ("run_id", "status", "reason", "requested_count", "completed_count", "failed_count")
    }
