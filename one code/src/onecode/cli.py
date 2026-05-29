import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.inspection import (
    LEDGER_COUNT_FIELDS,
    read_json,
    validate_checkpoint_evidence,
    validate_ledger_counts,
    validate_status_document,
)
from onecode.kernel.execution_engine import execute_plan
from onecode.kernel.execution_plan_loader import execution_trace_to_dict, load_execution_plan
from onecode.kernel.checkpoint import write_ledger
from onecode.kernel.runner import run_task
from onecode.kernel.task_plan import load_task_plan
from onecode.kernel.task_resume import PlannedAsset, classify_task_resume
from onecode.kernel.model_loop import (
    build_provider,
    execute_model_plan,
    is_patch_only_repair_plan,
    run_model_task,
)
from onecode.kernel.model_provider import api_key_from_env, build_provider_config
from onecode.kernel.self_audit import audit_self
from onecode.kernel.context import create_context
from onecode.kernel.verifier import (
    DEFAULT_VERIFIER_POLICY_PATH,
    load_verifier_policy,
    run_verifier,
    task_status_from_results,
    validate_selected_verifiers,
    write_verifier_policy,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="onecode")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("task")
    run_parser.add_argument("--workspace", default=".")
    run_parser.add_argument("--http-timeout-seconds", type=float, default=60)
    run_parser.add_argument("--run-id", default=None)
    run_parser.add_argument("--simulate-action-seconds", type=float, default=0)
    run_parser.add_argument("--write-path", default=None)
    run_parser.add_argument("--write-content", default=None)
    run_parser.add_argument("--write-text", action="append", default=None)
    run_parser.add_argument("--intent-type", default="noop")
    run_parser.add_argument("--command", dest="intent_command", default=None)
    run_parser.add_argument("--resume-from", default=None)
    run_parser.add_argument("--patch-path", default=None)
    run_parser.add_argument("--search-block", default=None)
    run_parser.add_argument("--replace-block", default=None)

    run_plan_parser = subparsers.add_parser("run-plan")
    run_plan_parser.add_argument("--workspace", default=".")
    run_plan_parser.add_argument("--plan", required=True)
    run_plan_parser.add_argument("--http-timeout-seconds", type=float, default=60)
    run_plan_parser.add_argument("--run-id", default=None)
    run_plan_parser.add_argument("--resume-from", default=None)
    run_plan_parser.add_argument("--verifier-policy", default=None)
    run_plan_parser.add_argument("--verifier", action="append", default=None)
    run_plan_parser.add_argument("--repair-model", default=None)
    run_plan_parser.add_argument("--repair-provider", default="responses")
    run_plan_parser.add_argument("--repair-endpoint", default=None)
    run_plan_parser.add_argument("--repair-api-key", default=None)
    run_plan_parser.add_argument("--max-repair-attempts", type=int, default=0)

    run_execution_plan_parser = subparsers.add_parser("run-execution-plan")
    run_execution_plan_parser.add_argument("--workspace", default=".")
    run_execution_plan_parser.add_argument("--plan", required=True)
    run_execution_plan_parser.add_argument("--run-id", default=None)
    run_execution_plan_parser.add_argument("--resume-from", default=None)

    run_model_parser = subparsers.add_parser("run-model")
    run_model_parser.add_argument("task")
    run_model_parser.add_argument("--workspace", default=".")
    run_model_parser.add_argument("--http-timeout-seconds", type=float, default=60)
    run_model_parser.add_argument("--run-id", default=None)
    run_model_parser.add_argument("--resume-from", default=None)
    run_model_parser.add_argument("--model", default=None)
    run_model_parser.add_argument("--api-key", default=None)
    run_model_parser.add_argument(
        "--provider",
        choices=[
            "responses",
            "chat",
            "openai-compatible",
            "compatible",
            "qwen",
            "dashscope",
            "deepseek",
            "kimi",
            "moonshot",
            "zhipu",
            "glm",
        ],
        default="responses",
    )
    run_model_parser.add_argument("--endpoint", default=None)

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--workspace", default=".")
    inspect_parser.add_argument("--run-id", required=True)

    list_runs_parser = subparsers.add_parser("list-runs")
    list_runs_parser.add_argument("--workspace", default=".")

    init_verifier_policy_parser = subparsers.add_parser("init-verifier-policy")
    init_verifier_policy_parser.add_argument("--workspace", default=".")
    init_verifier_policy_parser.add_argument("--output", default=DEFAULT_VERIFIER_POLICY_PATH)
    init_verifier_policy_parser.add_argument("--preset", action="append", default=None)
    init_verifier_policy_parser.add_argument("--force", action="store_true")

    subparsers.add_parser("doctor")
    subparsers.add_parser("audit-self")

    tui_parser = subparsers.add_parser("tui")
    tui_parser.add_argument("--workspace", default=None)
    tui_parser.add_argument("--model", default=None)
    tui_parser.add_argument(
        "--provider",
        choices=[
            "chat",
            "openai-compatible",
            "compatible",
            "qwen",
            "dashscope",
            "deepseek",
            "kimi",
            "moonshot",
            "zhipu",
            "glm",
        ],
        default=None,
    )
    return parser


def doctor_check(name: str, passed: bool, detail: dict | None = None) -> dict:
    return {"name": name, "passed": passed, "detail": detail or {}}


def doctor_result_detail(result: dict) -> dict:
    return {
        "run_id": result["run_id"],
        "status": result["status"],
        "reason": result["reason"],
        "iching_status_code": result["iching_status_code"],
        "iching_transition_action": result["iching_transition_action"],
        "iching_transition_reason": result["iching_transition_reason"],
        "dispatch_decision": result["iching_profile"]["dispatch_decision"],
    }


def doctor_rule_passed(result: dict) -> bool:
    profile = result["iching_profile"]
    profile_transition = IchingKernel.transition(profile["status_code"])
    return (
        profile["status_code"] == result["iching_status_code"]
        and profile["transition"]["action"] == profile_transition.action
        and profile["transition"]["reason"] == profile_transition.reason
        and profile["dispatch_decision"] == IchingKernel.dispatch_decision(profile_transition)
    )


def run_doctor() -> dict:
    checks = []
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)

        write_result = run_task(
            "doctor write",
            workspace=workspace,
            run_id="doctor-write",
            write_path="src/doctor_asset.py",
            write_content="value = 1\n",
        )
        checks.append(
            doctor_check(
                "write_text",
                write_result["status"] == "completed"
                and (workspace / "src" / "doctor_asset.py").exists()
                and doctor_rule_passed(write_result),
                doctor_result_detail(write_result),
            )
        )

        run_task(
            "doctor source",
            workspace=workspace,
            run_id="doctor-source",
            write_path="src/resume_asset.py",
            write_content="ready = True\n",
        )
        resume_result = run_task(
            "doctor resume",
            workspace=workspace,
            run_id="doctor-resume",
            resume_from_run_id="doctor-source",
            write_path="src/resume_asset.py",
            write_content="ready = False\n",
        )
        checks.append(
            doctor_check(
                "resume_skip",
                resume_result["status"] == "skipped"
                and resume_result["reason"] == "resumed_asset_ready"
                and (workspace / "src" / "resume_asset.py").read_text(encoding="utf-8") == "ready = True\n"
                and doctor_rule_passed(resume_result),
                doctor_result_detail(resume_result),
            )
        )

        outside = workspace.parent / "onecode-doctor-outside.txt"
        if outside.exists():
            outside.unlink()
        breach_result = run_task(
            "doctor breach",
            workspace=workspace,
            run_id="doctor-breach",
            write_path="../onecode-doctor-outside.txt",
            write_content="blocked\n",
        )
        checks.append(
            doctor_check(
                "sovereignty_breach",
                breach_result["status"] == "halted"
                and breach_result["reason"] == "sovereignty_breach"
                and not outside.exists()
                and doctor_rule_passed(breach_result),
                doctor_result_detail(breach_result),
            )
        )

        timeout_result = run_task(
            "doctor timeout",
            workspace=workspace,
            run_id="doctor-timeout",
            http_timeout_seconds=0.01,
            simulated_action_seconds=0.05,
        )
        checks.append(
            doctor_check(
                "http_timeout",
                timeout_result["status"] == "halted"
                and timeout_result["reason"] == "http_timeout"
                and doctor_rule_passed(timeout_result),
                doctor_result_detail(timeout_result),
            )
        )

    return {"status": "ok" if all(check["passed"] for check in checks) else "failed", "checks": checks}


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
    context = create_context(
        workspace_root=workspace,
        http_timeout_seconds=60,
        run_id=enhanced["run_id"],
        resume_from_run_id=enhanced.get("resumed_from"),
    )
    write_ledger(context, enhanced)
    return enhanced


def task_status_from_verifier_dicts(result: dict, verifier_dicts: list[dict]) -> dict:
    status_codes = [
        asset.get("raw_status_code")
        for asset in result.get("assets", [])
        if isinstance(asset, dict) and isinstance(asset.get("raw_status_code"), int)
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


def build_run_plan_repair_prompt(
    task: str,
    result: dict,
    verifier_results: list[dict],
    planned_asset_paths: list[str],
) -> str:
    failed_verifiers = [verifier for verifier in verifier_results if verifier.get("status") != "passed"]
    verifier_lines = []
    for verifier in failed_verifiers:
        verifier_lines.append(
            "\n".join(
                [
                    f"- id: {verifier.get('id')}",
                    f"  status: {verifier.get('status')}",
                    f"  reason: {verifier.get('reason')}",
                    f"  exit_code: {verifier.get('exit_code')}",
                    f"  stdout_tail: {verifier.get('stdout_tail')}",
                    f"  stderr_tail: {verifier.get('stderr_tail')}",
                ]
            )
        )
    return (
        "Repair the OneCode run-plan verifier failure using patches only.\n"
        f"Original task: {task}\n"
        f"Run id: {result.get('run_id')}\n"
        f"Planned asset paths: {', '.join(planned_asset_paths)}\n"
        f"Task status code: {result.get('task_status_code')}\n"
        f"Task transition action: {result.get('task_transition_action')}\n"
        f"Task transition reason: {result.get('task_transition_reason')}\n"
        f"Task resume decisions: {json.dumps(result.get('task_resume_decisions', []), ensure_ascii=False)}\n"
        "Failed verifier evidence:\n"
        f"{chr(10).join(verifier_lines) if verifier_lines else '- unavailable'}\n"
        "Return JSON with patches only. Do not return assets or execution_plan."
    )


def repair_provider_for_args(args: Any) -> tuple[Any, str]:
    config = build_provider_config(args.repair_provider, endpoint=args.repair_endpoint, model=args.repair_model)
    api_key = args.repair_api_key if args.repair_api_key is not None else api_key_from_env(provider_kind=args.repair_provider)
    if api_key is None:
        raise ValueError(f"{config.env_key} is required for run-plan repair")
    return build_provider(api_key, args.repair_provider, args.repair_endpoint), config.model


def apply_run_plan_repair(
    result: dict,
    task: str,
    workspace: Path,
    http_timeout_seconds: float,
    verifier_specs: list,
    planned_asset_paths: list[str],
    args: Any,
) -> dict:
    initial_verifiers = verifier_dicts(result.get("verifier_results", []))
    if verifier_failure(initial_verifiers) is None or args.max_repair_attempts <= 0:
        return result

    provider, model = repair_provider_for_args(args)
    repair_results = []
    repair_verifier_results = []
    prompt_evidence = []
    current_result = result
    current_verifiers = initial_verifiers

    for attempt in range(1, args.max_repair_attempts + 1):
        prompt = build_run_plan_repair_prompt(task, current_result, current_verifiers, planned_asset_paths)
        prompt_evidence.append(
            {
                "attempt": attempt,
                "failed_verifier_ids": [
                    verifier.get("id") for verifier in current_verifiers if verifier.get("status") != "passed"
                ],
                "planned_asset_paths": planned_asset_paths,
            }
        )
        repair_plan = provider.create_plan(prompt, model=model, http_timeout_seconds=http_timeout_seconds)
        if not is_patch_only_repair_plan(repair_plan):
            rejected = {
                **current_result,
                "status": "halted",
                "partial": True,
                "repaired": False,
                "repair_attempt_count": attempt,
                "initial_verifier_results": initial_verifiers,
                "repair_verifier_results": repair_verifier_results,
                "repair_results": repair_results,
                "repair_rejected_reason": "repair_plan_must_use_patches_only",
                "repair_prompt_evidence": prompt_evidence,
            }
            return write_result_ledger(workspace, rejected)

        repair_result = execute_model_plan(
            repair_plan,
            workspace=workspace,
            http_timeout_seconds=http_timeout_seconds,
            run_id=current_result["run_id"],
            resume_from_run_id=current_result.get("resumed_from"),
            run_metadata={"repair_attempt": attempt},
        )
        repair_results.append(repair_result)
        latest_verifiers = verifier_dicts([run_verifier(workspace, spec) for spec in verifier_specs])
        repair_verifier_results.append(latest_verifiers)
        current_result = apply_verifier_evidence_from_dicts(current_result, workspace, latest_verifiers)
        current_verifiers = latest_verifiers
        if verifier_failure(latest_verifiers) is None:
            repaired = {
                **align_counts_with_manifest(workspace, current_result),
                "status": "completed",
                "reason": None,
                "partial": False,
                "delivery_status": "deliverable",
                "repaired": True,
                "repair_attempt_count": attempt,
                "initial_verifier_results": initial_verifiers,
                "repair_verifier_results": repair_verifier_results,
                "repair_results": repair_results,
                "repair_rejected_reason": None,
                "repair_prompt_evidence": prompt_evidence,
            }
            return write_result_ledger(workspace, repaired)

    exhausted = {
        **align_counts_with_manifest(workspace, current_result),
        "status": "halted",
        "partial": True,
        "repaired": False,
        "repair_attempt_count": args.max_repair_attempts,
        "initial_verifier_results": initial_verifiers,
        "repair_verifier_results": repair_verifier_results,
        "repair_results": repair_results,
        "repair_rejected_reason": None,
        "repair_prompt_evidence": prompt_evidence,
    }
    return write_result_ledger(workspace, exhausted)


def write_result_ledger(workspace: Path, result: dict) -> dict:
    context = create_context(
        workspace_root=workspace,
        http_timeout_seconds=60,
        run_id=result["run_id"],
        resume_from_run_id=result.get("resumed_from"),
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
    if not runs_root.exists():
        return {"workspace": str(workspace), "runs": []}
    runs = []
    for run_dir in sorted(path for path in runs_root.iterdir() if path.is_dir()):
        _, summary = inspect_run(resolved_workspace, run_dir.name)
        runs.append(summary)
    return {"workspace": str(workspace), "runs": runs}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.subcommand == "inspect":
        exit_code, result = inspect_run(Path(args.workspace), args.run_id)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return exit_code

    if args.subcommand == "list-runs":
        result = list_runs(Path(args.workspace))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "init-verifier-policy":
        try:
            result = write_verifier_policy(
                workspace=Path(args.workspace),
                output=args.output,
                preset_ids=args.preset,
                force=args.force,
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "tui":
        from onecode.tui.app import run_tui
        run_tui(
            workspace=Path(args.workspace) if args.workspace is not None else None,
            model=args.model,
            provider_kind=args.provider,
        )
        return 0

    if args.subcommand == "doctor":
        result = run_doctor()
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] == "ok" else 1

    if args.subcommand == "audit-self":
        result = audit_self(Path.cwd(), run_doctor)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] == "ok" else 1

    if args.subcommand == "run-plan":
        try:
            task, write_texts, plan_evidence = load_task_plan(Path(args.plan))
            if args.max_repair_attempts < 0:
                parser.error("--max-repair-attempts must be non-negative")
            if args.max_repair_attempts > 0 and not args.verifier:
                parser.error("--max-repair-attempts requires --verifier")
            verifier_specs = []
            if args.verifier:
                if args.verifier_policy is None:
                    parser.error("--verifier requires --verifier-policy")
                policy = load_verifier_policy(Path(args.verifier_policy))
                verifier_specs = validate_selected_verifiers(Path(args.workspace), policy, args.verifier)
            resume_summary = None
            if args.resume_from is not None:
                planned_assets = [
                    PlannedAsset(path=write_text.partition("=")[0], content=write_text.partition("=")[2])
                    for write_text in write_texts
                ]
                resume_summary = classify_task_resume(
                    workspace=Path(args.workspace),
                    source_run_id=args.resume_from,
                    planned_assets=planned_assets,
                    verifier_specs=verifier_specs,
                )
                if any(decision.kind == "halt" for decision in resume_summary.decisions):
                    result = halted_task_resume_result(
                        Path(args.workspace),
                        args.run_id,
                        args.resume_from,
                        resume_summary,
                    )
                    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
                    return IchingKernel.process_exit_code(status=result["status"], reason=result["reason"])
            result = run_task(
                task,
                workspace=Path(args.workspace),
                http_timeout_seconds=args.http_timeout_seconds,
                run_id=args.run_id,
                write_texts=write_texts,
                resume_from_run_id=args.resume_from,
                run_metadata=plan_evidence,
            )
            if verifier_specs and result["status"] == "completed":
                verifier_results = [run_verifier(Path(args.workspace), spec) for spec in verifier_specs]
                result = apply_verifier_evidence(result, Path(args.workspace), verifier_results)
                result = apply_run_plan_repair(
                    result=result,
                    task=task,
                    workspace=Path(args.workspace),
                    http_timeout_seconds=args.http_timeout_seconds,
                    verifier_specs=verifier_specs,
                    planned_asset_paths=[write_text.partition("=")[0] for write_text in write_texts],
                    args=args,
                )
            result = apply_task_resume_evidence(result, Path(args.workspace), resume_summary)
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return IchingKernel.process_exit_code(status=result["status"], reason=result["reason"])

    if args.subcommand == "run-execution-plan":
        try:
            plan = load_execution_plan(Path(args.plan))
            trace = execute_plan(
                plan,
                workspace=Path(args.workspace),
                run_id=args.run_id,
                resume_from_run_id=args.resume_from,
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(execution_trace_to_dict(trace), ensure_ascii=False, sort_keys=True))
        return 0 if trace.success else 1

    if args.subcommand == "run-model":
        try:
            result = run_model_task(
                args.task,
                workspace=Path(args.workspace),
                http_timeout_seconds=args.http_timeout_seconds,
                run_id=args.run_id,
                resume_from_run_id=args.resume_from,
                model=args.model,
                api_key=args.api_key,
                provider_kind=args.provider,
                endpoint=args.endpoint,
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return IchingKernel.process_exit_code(status=result["status"], reason=result["reason"])

    if args.subcommand == "run":
        if args.write_text and (args.write_path is not None or args.write_content is not None):
            parser.error("cannot combine --write-text with --write-path or --write-content")
        if args.write_text and (
            args.patch_path is not None or args.search_block is not None or args.replace_block is not None
        ):
            parser.error("cannot combine --write-text with patch arguments")
        try:
            result = run_task(
                args.task,
                workspace=Path(args.workspace),
                http_timeout_seconds=args.http_timeout_seconds,
                run_id=args.run_id,
                simulated_action_seconds=args.simulate_action_seconds,
                write_path=args.write_path,
                write_content=args.write_content,
                write_texts=args.write_text,
                intent_type=args.intent_type,
                command=args.intent_command,
                resume_from_run_id=args.resume_from,
                patch_path=args.patch_path,
                search_block=args.search_block,
                replace_block=args.replace_block,
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return IchingKernel.process_exit_code(status=result["status"], reason=result["reason"])

    parser.error(f"unknown command: {args.subcommand}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
