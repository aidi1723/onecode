from __future__ import annotations

import json
from pathlib import Path

from onecode.kernel.checkpoint import wal_entry_hash
from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.inspection import (
    LEDGER_COUNT_FIELDS,
    read_json,
    validate_checkpoint_evidence,
    validate_evidence_chain,
    validate_ledger_counts,
    validate_status_document,
    validate_trace_completion,
)
from onecode.kernel.wal import global_wal_paths


def delivery_summary(ledger: dict) -> dict[str, int | str]:
    return IchingKernel.delivery_decision(
        status=ledger.get("status"),
        requested_count=ledger.get("requested_count"),
        completed_count=ledger.get("completed_count"),
        skipped_count=ledger.get("skipped_count"),
        failed_count=ledger.get("failed_count"),
    )


def checkpoint_asset_path(payload: dict | None, workspace_root: Path) -> str | None:
    if not isinstance(payload, dict) or not isinstance(payload.get("path"), str):
        return None
    path = Path(payload["path"])
    if not path.is_absolute():
        return payload["path"]
    try:
        return str(path.resolve().relative_to(workspace_root))
    except ValueError:
        return None


def checkpoint_assets(checkpoints: list[dict], workspace_root: Path) -> list[dict]:
    assets = []
    for checkpoint in checkpoints:
        checkpoint_payload, _, _ = read_json(Path(checkpoint["path"]))
        payload = checkpoint_payload.get("payload") if isinstance(checkpoint_payload, dict) else None
        assets.append(
            {
                "turn_index": checkpoint.get("turn_index"),
                "status": checkpoint.get("status"),
                "reason": checkpoint.get("reason"),
                "intent_type": checkpoint.get("intent_type"),
                "decision": checkpoint.get("decision"),
                "path": checkpoint_asset_path(payload, workspace_root),
                "iching_status_code": checkpoint.get("iching_status_code"),
            }
        )
    return assets


TASK_INSPECT_FIELDS = [
    "verifier_results",
    "task_status_code",
    "task_transition_action",
    "task_transition_reason",
    "task_dispatch_decision",
    "task_entropy",
    "task_entropy_decision",
    "task_entropy_reason",
    "task_completion_evidence",
    "task_resume_decisions",
    "task_resume_status_code",
    "task_resume_transition_action",
    "task_resume_transition_reason",
    "task_resume_dispatch_decision",
    "repair_attempt_count",
    "repaired",
    "initial_verifier_results",
    "repair_verifier_results",
    "repair_results",
    "repair_rejected_reason",
    "repair_prompt_evidence",
]


def optional_task_inspect_fields(ledger: dict) -> dict:
    return {field: ledger[field] for field in TASK_INSPECT_FIELDS if field in ledger}


def read_global_wal_segment(path: Path) -> tuple[list[dict] | None, str | None]:
    if not path.exists():
        return [], None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None, "global_wal_unreadable"
    entries = []
    previous_hash = None
    for line in lines:
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            return None, "invalid_global_wal_json"
        if not isinstance(value, dict):
            return None, "invalid_global_wal_entry"
        if "hash" in value or "prev" in value:
            if value.get("prev") != previous_hash:
                return None, "global_wal_chain_prev_mismatch"
            expected_hash = wal_entry_hash(value)
            if value.get("hash") != expected_hash:
                return None, "global_wal_chain_hash_mismatch"
            previous_hash = expected_hash
        value = {**value, "_wal_path": str(path)}
        entries.append(value)
    return entries, None


def read_global_wal_entries(workspace: Path) -> tuple[list[dict] | None, str | None, str | None]:
    entries = []
    for wal_path in global_wal_paths(workspace):
        segment_entries, corrupt_reason = read_global_wal_segment(wal_path)
        if corrupt_reason is not None or segment_entries is None:
            return None, str(wal_path), corrupt_reason
        entries.extend(segment_entries)
    return entries, None, None


def read_global_wal_run_entry(workspace: Path, run_id: str) -> tuple[dict | None, str | None, str | None]:
    entries, corrupt_path, corrupt_reason = read_global_wal_entries(workspace)
    if corrupt_path is not None or entries is None:
        return None, corrupt_path, corrupt_reason
    matched = None
    for value in entries:
        if value.get("rid") == run_id:
            matched = value
    return matched, None, None


def inspect_global_wal_run(workspace: Path, run_id: str) -> tuple[int, dict] | None:
    entry, corrupt_path, corrupt_reason = read_global_wal_run_entry(workspace, run_id)
    wal_path = workspace.resolve() / ".onecode" / "global-ledger.jsonl"
    if corrupt_path is not None:
        return 1, {
            "run_id": run_id,
            "status": "corrupt",
            "corrupt_path": corrupt_path,
            "corrupt_reason": corrupt_reason,
            "wal_path": str(wal_path),
        }
    if entry is None or entry.get("em") != "wal":
        return None
    entry_wal_path = entry.get("_wal_path") if isinstance(entry.get("_wal_path"), str) else str(wal_path)
    ledger = {
        "status": entry.get("st"),
        "requested_count": entry.get("rc"),
        "completed_count": entry.get("cc"),
        "skipped_count": entry.get("sc"),
        "failed_count": entry.get("fc"),
    }
    return 0, {
        "run_id": run_id,
        "status": entry.get("st"),
        "partial": entry.get("pc"),
        "reason": entry.get("rs"),
        "evidence_mode": "wal",
        "requested_count": entry.get("rc"),
        "completed_count": entry.get("cc"),
        "skipped_count": entry.get("sc"),
        "failed_count": entry.get("fc"),
        "checkpoint_count": None,
        "iching_status_code": entry.get("isc"),
        "iching_transition_action": entry.get("ita"),
        "profile_sha256": entry.get("ph"),
        "profile_registry_ref": entry.get("pr"),
        "manifest_path": entry.get("mp"),
        "ledger_path": entry.get("lp"),
        "wal_path": entry_wal_path,
    } | delivery_summary(ledger)


def global_wal_run_summaries(workspace: Path) -> tuple[list[dict] | None, dict | None]:
    entries, corrupt_path, corrupt_reason = read_global_wal_entries(workspace)
    wal_path = workspace.resolve() / ".onecode" / "global-ledger.jsonl"
    if corrupt_path is not None or entries is None:
        return None, {
            "run_id": None,
            "status": "corrupt",
            "corrupt_path": corrupt_path,
            "corrupt_reason": corrupt_reason,
            "wal_path": str(wal_path),
        }
    latest_by_run_id = {}
    for entry in entries:
        run_id = entry.get("rid")
        if isinstance(run_id, str) and entry.get("em") == "wal":
            latest_by_run_id[run_id] = entry
    summaries = []
    for run_id in sorted(latest_by_run_id):
        inspected = inspect_global_wal_run(workspace, run_id)
        if inspected is not None:
            _, summary = inspected
            summaries.append(summary)
    return summaries, None


def inspect_run(workspace: Path, run_id: str) -> tuple[int, dict]:
    evidence_root = workspace.resolve() / ".onecode" / "runs" / run_id
    manifest_path = evidence_root / "manifest.json"
    ledger_path = evidence_root / "ledger.json"
    manifest, corrupt_manifest_path, corrupt_manifest_reason = read_json(manifest_path)
    ledger, corrupt_ledger_path, corrupt_ledger_reason = read_json(ledger_path)
    corrupt_path = corrupt_manifest_path or corrupt_ledger_path
    corrupt_reason = corrupt_manifest_reason or corrupt_ledger_reason
    if corrupt_path is not None:
        return 1, {
            "run_id": run_id,
            "status": "corrupt",
            "corrupt_path": corrupt_path,
            "corrupt_reason": corrupt_reason,
            "manifest_path": str(manifest_path),
            "ledger_path": str(ledger_path),
        }
    if manifest is None or ledger is None:
        wal_result = inspect_global_wal_run(workspace, run_id)
        if wal_result is not None:
            return wal_result
        return 1, {
            "run_id": run_id,
            "status": "missing",
            "manifest_path": str(manifest_path),
            "ledger_path": str(ledger_path),
        }
    corrupt_path, corrupt_reason = validate_status_document(manifest, manifest_path)
    if corrupt_path is None:
        corrupt_path, corrupt_reason = validate_status_document(ledger, ledger_path)
    if corrupt_path is not None:
        return 1, {
            "run_id": run_id,
            "status": "corrupt",
            "corrupt_path": corrupt_path,
            "corrupt_reason": corrupt_reason,
            "manifest_path": str(manifest_path),
            "ledger_path": str(ledger_path),
        }
    if manifest["status"] != ledger["status"]:
        return 1, {
            "run_id": run_id,
            "status": "corrupt",
            "corrupt_path": str(ledger_path),
            "corrupt_reason": "status_mismatch",
            "manifest_path": str(manifest_path),
            "ledger_path": str(ledger_path),
        }
    corrupt_path, corrupt_reason = validate_ledger_counts(ledger, ledger_path)
    if corrupt_path is not None:
        return 1, {
            "run_id": run_id,
            "status": "corrupt",
            "corrupt_path": corrupt_path,
            "corrupt_reason": corrupt_reason,
            "manifest_path": str(manifest_path),
            "ledger_path": str(ledger_path),
        }
    if "checkpoints" not in manifest:
        return 1, {
            "run_id": run_id,
            "status": "corrupt",
            "corrupt_path": str(manifest_path),
            "corrupt_reason": "missing_checkpoints",
            "manifest_path": str(manifest_path),
            "ledger_path": str(ledger_path),
        }
    checkpoints = manifest["checkpoints"]
    if not isinstance(checkpoints, list):
        return 1, {
            "run_id": run_id,
            "status": "corrupt",
            "corrupt_path": str(manifest_path),
            "corrupt_reason": "invalid_checkpoints",
            "manifest_path": str(manifest_path),
            "ledger_path": str(ledger_path),
        }
    if not all(isinstance(checkpoint, dict) for checkpoint in checkpoints):
        return 1, {
            "run_id": run_id,
            "status": "corrupt",
            "corrupt_path": str(manifest_path),
            "corrupt_reason": "invalid_checkpoint_entry",
            "manifest_path": str(manifest_path),
            "ledger_path": str(ledger_path),
        }
    corrupt_path, corrupt_reason = validate_checkpoint_evidence(checkpoints, manifest_path)
    if corrupt_path is not None:
        return 1, {
            "run_id": run_id,
            "status": "corrupt",
            "corrupt_path": corrupt_path,
            "corrupt_reason": corrupt_reason,
            "manifest_path": str(manifest_path),
            "ledger_path": str(ledger_path),
        }
    if all(field in ledger for field in LEDGER_COUNT_FIELDS):
        resolved_count = ledger["completed_count"] + ledger["skipped_count"] + ledger["failed_count"]
        if resolved_count != len(checkpoints):
            return 1, {
                "run_id": run_id,
                "status": "corrupt",
                "corrupt_path": str(manifest_path),
                "corrupt_reason": "checkpoint_count_mismatch",
                "manifest_path": str(manifest_path),
                "ledger_path": str(ledger_path),
            }
    trace_value = ledger.get("trace_path")
    if isinstance(trace_value, str):
        corrupt_path, corrupt_reason = validate_trace_completion(ledger, Path(trace_value))
        if corrupt_path is not None:
            return 1, {
                "run_id": run_id,
                "status": "corrupt",
                "corrupt_path": corrupt_path,
                "corrupt_reason": corrupt_reason,
                "manifest_path": str(manifest_path),
                "ledger_path": str(ledger_path),
            }
    corrupt_path, corrupt_reason = validate_evidence_chain(evidence_root / "evidence-chain.jsonl")
    if corrupt_path is not None:
        return 1, {
            "run_id": run_id,
            "status": "corrupt",
            "corrupt_path": corrupt_path,
            "corrupt_reason": corrupt_reason,
            "manifest_path": str(manifest_path),
            "ledger_path": str(ledger_path),
        }
    workspace_root = (
        Path(manifest["workspace_root"]).resolve()
        if isinstance(manifest.get("workspace_root"), str)
        else workspace.resolve()
    )
    return 0, {
        "run_id": run_id,
        "status": ledger.get("status", manifest.get("status")),
        "partial": ledger.get("partial", manifest.get("partial")),
        "reason": ledger.get("reason", manifest.get("reason")),
        "resumed_from": ledger.get("resumed_from", manifest.get("resumed_from")),
        "plan_path": ledger.get("plan_path"),
        "plan_sha256": ledger.get("plan_sha256"),
        "plan_asset_count": ledger.get("plan_asset_count"),
        "requested_count": ledger.get("requested_count"),
        "completed_count": ledger.get("completed_count"),
        "skipped_count": ledger.get("skipped_count"),
        "failed_count": ledger.get("failed_count"),
        "checkpoint_count": len(checkpoints),
        "iching_status_code": ledger.get("iching_status_code", manifest.get("iching_status_code")),
        "iching_transition_action": ledger.get(
            "iching_transition_action", manifest.get("iching_transition_action")
        ),
        "iching_transition_reason": ledger.get(
            "iching_transition_reason", manifest.get("iching_transition_reason")
        ),
        "assets": checkpoint_assets(checkpoints, workspace_root),
        "manifest_path": str(manifest_path),
        "ledger_path": str(ledger_path),
    } | delivery_summary(ledger) | optional_task_inspect_fields(ledger)


def list_runs(workspace: Path) -> dict:
    resolved_workspace = workspace.resolve()
    runs_root = resolved_workspace / ".onecode" / "runs"
    runs = []
    seen_run_ids = set()
    if runs_root.exists():
        for run_dir in sorted(path for path in runs_root.iterdir() if path.is_dir()):
            _, summary = inspect_run(resolved_workspace, run_dir.name)
            runs.append(summary)
            if isinstance(summary.get("run_id"), str):
                seen_run_ids.add(summary["run_id"])
    wal_summaries, corrupt_summary = global_wal_run_summaries(resolved_workspace)
    if corrupt_summary is not None:
        runs.append(corrupt_summary)
    else:
        for summary in wal_summaries or []:
            run_id = summary.get("run_id")
            if isinstance(run_id, str) and run_id not in seen_run_ids:
                runs.append(summary)
    runs.sort(key=lambda run: str(run.get("run_id") or ""))
    return {"workspace": str(workspace), "runs": runs}
