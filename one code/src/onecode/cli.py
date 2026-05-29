import argparse
import json
import tempfile
from pathlib import Path

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
from onecode.kernel.runner import run_task
from onecode.kernel.task_plan import load_task_plan
from onecode.kernel.model_loop import run_model_task
from onecode.kernel.self_audit import audit_self


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
    } | delivery_summary(ledger)


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
            result = run_task(
                task,
                workspace=Path(args.workspace),
                http_timeout_seconds=args.http_timeout_seconds,
                run_id=args.run_id,
                write_texts=write_texts,
                resume_from_run_id=args.resume_from,
                run_metadata=plan_evidence,
            )
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
