import json
from pathlib import Path
from typing import Any

from onecode.kernel.checkpoint import (
    atomic_write_json,
    manifest_size_metrics,
    run_evidence_write_lock,
    utc_now_iso,
    validate_manifest_metrics,
    validate_skill_selection,
    wal_entry_hash,
    write_ledger,
)
from onecode.kernel.context import create_context
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
from onecode.kernel.run_id import validate_run_id
from onecode.kernel.trace import TraceEvent, trace_evidence_metrics, write_trace_event
from onecode.kernel.wal import global_wal_evidence_metrics, global_wal_paths


def delivery_summary(ledger: dict) -> dict[str, int | str]:
    return IchingKernel.delivery_decision(
        status=ledger.get("status"),
        requested_count=ledger.get("requested_count"),
        completed_count=ledger.get("completed_count"),
        skipped_count=ledger.get("skipped_count"),
        failed_count=ledger.get("failed_count"),
    )


def ledger_history_present(ledger_path: str | None) -> bool:
    if not isinstance(ledger_path, str):
        return False
    return Path(ledger_path).with_suffix(".jsonl").exists()


def task_completion_evidence(result: dict, verifier_results: list[dict]) -> dict:
    manifest_path = result.get("manifest_path")
    ledger_path = result.get("ledger_path")
    assets_complete = (
        result.get("status") == "completed"
        and result.get("failed_count") == 0
        and result.get("requested_count")
        == result.get("completed_count", 0) + result.get("skipped_count", 0)
    )
    verifiers_passed = all(verifier.get("status") == "passed" for verifier in verifier_results)
    return {
        "assets_complete": assets_complete,
        "verifiers_passed": verifiers_passed,
        "ledger_present": isinstance(ledger_path, str) and Path(ledger_path).exists(),
        "ledger_history_present": ledger_history_present(ledger_path),
        "manifest_present": isinstance(manifest_path, str) and Path(manifest_path).exists(),
        "checkpoint_count": len(result.get("assets", [])) if isinstance(result.get("assets"), list) else 0,
    }


def apply_verifier_evidence(result: dict, workspace: Path, verifier_results: list) -> dict:
    verifier_dicts = [verifier.to_dict() for verifier in verifier_results]
    return apply_verifier_evidence_from_dicts(result, workspace, verifier_dicts)


def apply_verifier_evidence_from_dicts(result: dict, workspace: Path, verifier_dicts: list[dict]) -> dict:
    first_failure = next((verifier for verifier in verifier_dicts if verifier["status"] != "passed"), None)
    evidence = task_completion_evidence(result, verifier_dicts)
    task_status = task_status_from_verifier_dicts(result, verifier_dicts)
    enhanced = {
        **result,
        "verifier_results": verifier_dicts,
        "task_completion_evidence": evidence,
        "delivery_status": "deliverable" if first_failure is None and evidence["assets_complete"] else "blocked",
        **task_status,
    }
    if first_failure is not None:
        enhanced = {
            **enhanced,
            "status": "halted",
            "reason": first_failure["reason"],
            "partial": True,
        }
    return write_result_ledger(workspace, enhanced)


def sync_manifest_final_status(context: Any, result: dict) -> None:
    manifest, _, _ = read_json(context.manifest_path)
    if manifest is None:
        return
    manifest = {
        **manifest,
        "updated_at": utc_now_iso(),
        "status": result.get("status"),
        "partial": result.get("partial"),
        "reason": result.get("reason"),
    }
    if isinstance(result.get("state"), str):
        manifest["current_state"] = result["state"]
    metrics = manifest_size_metrics(manifest)
    validate_manifest_metrics(metrics)
    manifest["manifest_metrics"] = metrics
    with run_evidence_write_lock(context.evidence_root):
        atomic_write_json(context.manifest_path, manifest)


def append_final_trace_status(context: Any, result: dict, verifier_dicts: list[dict]) -> None:
    trace_path_value = result.get("trace_path")
    if not isinstance(trace_path_value, str):
        return
    trace_path = Path(trace_path_value)
    if not trace_path.exists():
        return
    write_trace_event(
        trace_path,
        TraceEvent(
            trace_id=str(result.get("trace_id") or context.run_id),
            run_id=context.run_id,
            span_id="run-verifier-final",
            parent_span_id="run",
            event_type="run_completed",
            status=str(result.get("status")),
            payload={
                "reason": result.get("reason"),
                "delivery_status": result.get("delivery_status"),
                "verifier_count": len(verifier_dicts),
            },
        ),
    )


def task_status_from_verifier_dicts(result: dict, verifier_dicts: list[dict]) -> dict:
    status_codes = [
        asset.get("raw_status_code")
        for asset in result.get("assets", [])
        if isinstance(asset, dict)
        and isinstance(asset.get("raw_status_code"), int)
        and not isinstance(asset.get("raw_status_code"), bool)
    ]
    for verifier in verifier_dicts:
        status_codes.append(
            IchingKernel.classify_outcome(
                "completed" if verifier.get("status") == "passed" else "halted",
                verifier.get("reason"),
            )
        )
    entropy = IchingKernel.entropy_regulated_status(status_codes)
    status_code = int(entropy["status_code"])
    transition = IchingKernel.transition(status_code)
    return {
        "task_status_code": status_code,
        "task_transition_action": transition.action,
        "task_transition_reason": transition.reason,
        "task_dispatch_decision": IchingKernel.dispatch_decision(transition),
        "task_entropy": entropy["entropy"],
        "task_entropy_decision": entropy["decision"],
        "task_entropy_reason": entropy.get("reason"),
    }


def verifier_dicts(verifier_results: list) -> list[dict]:
    return [verifier.to_dict() if hasattr(verifier, "to_dict") else dict(verifier) for verifier in verifier_results]


def verifier_failure(verifier_results: list[dict]) -> dict | None:
    return next((verifier for verifier in verifier_results if verifier.get("status") != "passed"), None)


def write_result_ledger(workspace: Path, result: dict) -> dict:
    context = create_context(
        workspace_root=workspace,
        http_timeout_seconds=60,
        run_id=result["run_id"],
        resume_from_run_id=result.get("resumed_from"),
    )
    sync_manifest_final_status(context, result)
    raw_verifier_results = result.get("verifier_results")
    append_final_trace_status(
        context,
        result,
        raw_verifier_results if isinstance(raw_verifier_results, list) else [],
    )
    write_ledger(context, result)
    return result


def align_counts_with_manifest(workspace: Path, result: dict) -> dict:
    manifest_path = result.get("manifest_path")
    if not isinstance(manifest_path, str) or not Path(manifest_path).exists():
        return result
    manifest, _, _ = read_json(Path(manifest_path))
    checkpoints = manifest.get("checkpoints") if isinstance(manifest, dict) else None
    if not isinstance(checkpoints, list):
        return result
    completed_count = sum(1 for checkpoint in checkpoints if checkpoint.get("status") == "completed")
    skipped_count = sum(1 for checkpoint in checkpoints if checkpoint.get("status") == "skipped")
    failed_count = sum(1 for checkpoint in checkpoints if checkpoint.get("status") in {"denied", "halted"})
    return {
        **result,
        "requested_count": len(checkpoints),
        "completed_count": completed_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
    }


def apply_task_resume_evidence(result: dict, workspace: Path, resume_summary: Any | None) -> dict:
    if resume_summary is None:
        return result
    enhanced = {**result, **resume_summary.to_dict()}
    write_result_ledger(workspace, enhanced)
    return enhanced


def halted_task_resume_result(
    workspace: Path,
    run_id: str | None,
    resume_from_run_id: str,
    resume_summary: Any,
) -> dict:
    first_halt = next(
        (decision for decision in resume_summary.decisions if decision.kind == "halt"),
        None,
    )
    context = create_context(
        workspace_root=workspace,
        run_id=run_id,
        resume_from_run_id=resume_from_run_id,
    )
    result = {
        "run_id": context.run_id,
        "status": "halted",
        "state": "000000",
        "manifest_path": str(context.manifest_path),
        "ledger_path": str(context.evidence_root / "ledger.json"),
        "partial": True,
        "reason": first_halt.reason if first_halt is not None else "task_resume_halt",
        "decision": "halted",
        "intent_type": "task_resume",
        "payload": {},
        "resumed_from": resume_from_run_id,
        "resumed": False,
        "assets": [],
        "requested_count": 0,
        "completed_count": 0,
        "skipped_count": 0,
        "failed_count": 1,
        **resume_summary.to_dict(),
    }
    write_ledger(context, result)
    return result


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


def compact_skill_selection_inspect_fields(
    ledger: dict,
    manifest: dict,
) -> tuple[dict[str, Any], str | None]:
    ledger_selection = ledger.get("skill_selection")
    manifest_selection = manifest.get("skill_selection")
    validated_ledger = None
    validated_manifest = None
    try:
        validated_ledger = validate_skill_selection(ledger_selection)
        validated_manifest = validate_skill_selection(manifest_selection)
    except ValueError:
        return {}, "invalid_skill_selection_evidence"

    if validated_ledger is not None and validated_manifest is not None:
        if validated_ledger.get("selection_sha256") != validated_manifest.get("selection_sha256"):
            return {}, "skill_selection_mismatch"
    selection = validated_ledger or validated_manifest
    if selection is None:
        return {}, None
    return {
        "skill_context_status": selection.get("status"),
        "ssr": selection.get("selection_reason"),
        "ssc": selection.get("selected_count"),
        "ssh": selection.get("selection_sha256"),
    }, None


def trace_repair_decision(evidence_metrics: dict[str, Any]) -> dict[str, Any]:
    trace_metrics = evidence_metrics.get("trace") if isinstance(evidence_metrics, dict) else None
    if not isinstance(trace_metrics, dict):
        return {}
    if int(trace_metrics.get("aggregate_gap_count") or 0) <= 0:
        return {}
    return {
        "delivery_status": "blocked",
        "next_action": "repair",
        "repair_required": True,
        "repair_reason": "trace_aggregate_gap",
    }


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
        "ssh": entry.get("ssh"),
        "ssr": entry.get("ssr"),
        "ssc": entry.get("ssc"),
        "manifest_path": entry.get("mp"),
        "ledger_path": entry.get("lp"),
        "wal_path": entry_wal_path,
        "evidence_metrics": {"global_wal": global_wal_evidence_metrics(workspace)},
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


def corrupt_inspection_payload(
    run_id: str,
    corrupt_path: str | None,
    corrupt_reason: str | None,
    manifest_path: Path,
    ledger_path: Path,
) -> dict:
    return {
        "run_id": run_id,
        "status": "corrupt",
        "corrupt_path": corrupt_path,
        "corrupt_reason": corrupt_reason,
        "manifest_path": str(manifest_path),
        "ledger_path": str(ledger_path),
    }


def validate_run_documents(
    run_id: str,
    manifest: dict,
    ledger: dict,
    manifest_path: Path,
    ledger_path: Path,
) -> tuple[list[dict] | None, dict[str, Any], dict | None]:
    corrupt_path, corrupt_reason = validate_status_document(manifest, manifest_path)
    if corrupt_path is None:
        corrupt_path, corrupt_reason = validate_status_document(ledger, ledger_path)
    if corrupt_path is not None:
        return None, {}, corrupt_inspection_payload(run_id, corrupt_path, corrupt_reason, manifest_path, ledger_path)
    if manifest["status"] != ledger["status"]:
        return None, {}, corrupt_inspection_payload(
            run_id,
            str(ledger_path),
            "status_mismatch",
            manifest_path,
            ledger_path,
        )
    corrupt_path, corrupt_reason = validate_ledger_counts(ledger, ledger_path)
    if corrupt_path is not None:
        return None, {}, corrupt_inspection_payload(run_id, corrupt_path, corrupt_reason, manifest_path, ledger_path)
    if "checkpoints" not in manifest:
        return None, {}, corrupt_inspection_payload(
            run_id,
            str(manifest_path),
            "missing_checkpoints",
            manifest_path,
            ledger_path,
        )
    checkpoints = manifest["checkpoints"]
    if not isinstance(checkpoints, list):
        return None, {}, corrupt_inspection_payload(
            run_id,
            str(manifest_path),
            "invalid_checkpoints",
            manifest_path,
            ledger_path,
        )
    if not all(isinstance(checkpoint, dict) for checkpoint in checkpoints):
        return None, {}, corrupt_inspection_payload(
            run_id,
            str(manifest_path),
            "invalid_checkpoint_entry",
            manifest_path,
            ledger_path,
        )
    corrupt_path, corrupt_reason = validate_checkpoint_evidence(checkpoints, manifest_path)
    if corrupt_path is not None:
        return None, {}, corrupt_inspection_payload(run_id, corrupt_path, corrupt_reason, manifest_path, ledger_path)
    if all(field in ledger for field in LEDGER_COUNT_FIELDS):
        resolved_count = ledger["completed_count"] + ledger["skipped_count"] + ledger["failed_count"]
        if resolved_count != len(checkpoints):
            return None, {}, corrupt_inspection_payload(
                run_id,
                str(manifest_path),
                "checkpoint_count_mismatch",
                manifest_path,
                ledger_path,
            )
    skill_selection_fields, skill_selection_error = compact_skill_selection_inspect_fields(ledger, manifest)
    if skill_selection_error is not None:
        return None, {}, corrupt_inspection_payload(
            run_id,
            str(ledger_path),
            skill_selection_error,
            manifest_path,
            ledger_path,
        )
    return checkpoints, skill_selection_fields, None


def trace_metrics_for_ledger(
    run_id: str,
    ledger: dict,
    evidence_metrics: dict[str, Any],
    manifest_path: Path,
    ledger_path: Path,
) -> tuple[dict[str, Any], dict | None]:
    trace_value = ledger.get("trace_path")
    if not isinstance(trace_value, str):
        return evidence_metrics, None
    trace_path = Path(trace_value)
    corrupt_path, corrupt_reason = validate_trace_completion(ledger, trace_path)
    if corrupt_path is not None:
        return evidence_metrics, corrupt_inspection_payload(
            run_id,
            corrupt_path,
            corrupt_reason,
            manifest_path,
            ledger_path,
        )
    return {**evidence_metrics, "trace": trace_evidence_metrics(trace_path)}, None


def workspace_root_from_manifest(manifest: dict, workspace: Path) -> Path:
    if isinstance(manifest.get("workspace_root"), str):
        return Path(manifest["workspace_root"]).resolve()
    return workspace.resolve()


def run_inspection_summary(
    run_id: str,
    workspace: Path,
    manifest: dict,
    ledger: dict,
    checkpoints: list[dict],
    skill_selection_fields: dict[str, Any],
    manifest_path: Path,
    ledger_path: Path,
    evidence_metrics: dict[str, Any],
) -> dict:
    workspace_root = workspace_root_from_manifest(manifest, workspace)
    base_summary = {
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
        "evidence_metrics": evidence_metrics,
    } | skill_selection_fields | delivery_summary(ledger) | optional_task_inspect_fields(ledger)
    return base_summary | trace_repair_decision(evidence_metrics)


def inspect_run(workspace: Path, run_id: str) -> tuple[int, dict]:
    try:
        run_id = validate_run_id(run_id)
    except ValueError:
        return 1, {
            "run_id": run_id,
            "status": "invalid",
            "reason": "invalid_run_id",
        }
    evidence_root = workspace.resolve() / ".onecode" / "runs" / run_id
    manifest_path = evidence_root / "manifest.json"
    ledger_path = evidence_root / "ledger.json"
    manifest, corrupt_manifest_path, corrupt_manifest_reason = read_json(manifest_path)
    ledger, corrupt_ledger_path, corrupt_ledger_reason = read_json(ledger_path)
    corrupt_path = corrupt_manifest_path or corrupt_ledger_path
    corrupt_reason = corrupt_manifest_reason or corrupt_ledger_reason
    if corrupt_path is not None:
        return 1, corrupt_inspection_payload(run_id, corrupt_path, corrupt_reason, manifest_path, ledger_path)
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
    checkpoints, skill_selection_fields, corrupt_payload = validate_run_documents(
        run_id,
        manifest,
        ledger,
        manifest_path,
        ledger_path,
    )
    if corrupt_payload is not None or checkpoints is None:
        return 1, corrupt_payload or corrupt_inspection_payload(
            run_id,
            str(manifest_path),
            "invalid_run_documents",
            manifest_path,
            ledger_path,
        )
    evidence_metrics = ledger.get("evidence_metrics", {})
    if not isinstance(evidence_metrics, dict):
        evidence_metrics = {}
    evidence_metrics, corrupt_payload = trace_metrics_for_ledger(
        run_id,
        ledger,
        evidence_metrics,
        manifest_path,
        ledger_path,
    )
    if corrupt_payload is not None:
        return 1, corrupt_payload
    corrupt_path, corrupt_reason = validate_evidence_chain(evidence_root / "evidence-chain.jsonl")
    if corrupt_path is not None:
        return 1, corrupt_inspection_payload(run_id, corrupt_path, corrupt_reason, manifest_path, ledger_path)
    return 0, run_inspection_summary(
        run_id,
        workspace,
        manifest,
        ledger,
        checkpoints,
        skill_selection_fields,
        manifest_path,
        ledger_path,
        evidence_metrics,
    )


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
