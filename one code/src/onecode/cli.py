import argparse
import json
import tempfile
import string
import hashlib
from pathlib import Path

from onecode.kernel.checkpoint import sha256_file
from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.runner import run_task


VALID_RUN_STATUSES = {"completed", "skipped", "denied", "halted"}
LEDGER_COUNT_FIELDS = ("requested_count", "completed_count", "skipped_count", "failed_count")
SHA256_HEX_LENGTH = 64
HEX_DIGITS = set(string.hexdigits)
PLAN_ASSET_FIELDS = {"path", "content"}


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

    run_plan_parser = subparsers.add_parser("run-plan")
    run_plan_parser.add_argument("--workspace", default=".")
    run_plan_parser.add_argument("--plan", required=True)
    run_plan_parser.add_argument("--http-timeout-seconds", type=float, default=60)
    run_plan_parser.add_argument("--run-id", default=None)
    run_plan_parser.add_argument("--resume-from", default=None)

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--workspace", default=".")
    inspect_parser.add_argument("--run-id", required=True)

    list_runs_parser = subparsers.add_parser("list-runs")
    list_runs_parser.add_argument("--workspace", default=".")

    subparsers.add_parser("doctor")
    return parser


def doctor_check(name: str, passed: bool, detail: dict | None = None) -> dict:
    return {"name": name, "passed": passed, "detail": detail or {}}


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
                write_result["status"] == "completed" and (workspace / "src" / "doctor_asset.py").exists(),
                {"run_id": write_result["run_id"], "status": write_result["status"], "reason": write_result["reason"]},
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
                and (workspace / "src" / "resume_asset.py").read_text(encoding="utf-8") == "ready = True\n",
                {"run_id": resume_result["run_id"], "status": resume_result["status"], "reason": resume_result["reason"]},
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
                and not outside.exists(),
                {"run_id": breach_result["run_id"], "status": breach_result["status"], "reason": breach_result["reason"]},
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
                timeout_result["status"] == "halted" and timeout_result["reason"] == "http_timeout",
                {"run_id": timeout_result["run_id"], "status": timeout_result["status"], "reason": timeout_result["reason"]},
            )
        )

    return {"status": "ok" if all(check["passed"] for check in checks) else "failed", "checks": checks}


def read_json(path: Path) -> tuple[dict | None, str | None, str | None]:
    if not path.exists():
        return None, None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, str(path), "invalid_json"
    if not isinstance(data, dict):
        return None, str(path), "non_object_json"
    return data, None, None


def sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_task_plan(path: Path) -> tuple[str, list[str], dict]:
    resolved_path = path.resolve()
    data, corrupt_path, corrupt_reason = read_json(path)
    if corrupt_path is not None:
        raise ValueError(f"invalid plan: {corrupt_reason}")
    if data is None:
        raise ValueError("invalid plan: missing_file")
    task = data.get("task", "plan")
    if not isinstance(task, str) or not task:
        raise ValueError("invalid plan: task must be a non-empty string")
    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("invalid plan: assets must be a non-empty list")

    write_texts = []
    seen_paths = set()
    for index, asset in enumerate(assets, start=1):
        if not isinstance(asset, dict):
            raise ValueError(f"invalid plan asset {index}: asset must be an object")
        unknown_fields = sorted(set(asset) - PLAN_ASSET_FIELDS)
        if unknown_fields:
            raise ValueError(f"invalid plan asset {index}: unknown fields {', '.join(unknown_fields)}")
        path = asset.get("path")
        content = asset.get("content")
        if not isinstance(path, str) or not path:
            raise ValueError(f"invalid plan asset {index}: path must be a non-empty string")
        if not isinstance(content, str):
            raise ValueError(f"invalid plan asset {index}: content must be a string")
        if path in seen_paths:
            raise ValueError(f"invalid plan asset {index}: duplicate path {path}")
        seen_paths.add(path)
        write_texts.append(f"{path}={content}")
    plan_evidence = {
        "plan_path": str(resolved_path),
        "plan_sha256": sha256_bytes(resolved_path),
        "plan_asset_count": len(write_texts),
    }
    return task, write_texts, plan_evidence


def validate_status_document(data: dict, path: Path) -> tuple[str | None, str | None]:
    if "status" not in data:
        return str(path), "missing_status"
    if not isinstance(data["status"], str) or not data["status"]:
        return str(path), "invalid_status"
    if data["status"] not in VALID_RUN_STATUSES:
        return str(path), "invalid_status"
    return None, None


def validate_ledger_counts(ledger: dict, path: Path) -> tuple[str | None, str | None]:
    for field in LEDGER_COUNT_FIELDS:
        if field in ledger and (not isinstance(ledger[field], int) or ledger[field] < 0):
            return str(path), "invalid_count"
    if all(field in ledger for field in LEDGER_COUNT_FIELDS):
        resolved_count = ledger["completed_count"] + ledger["skipped_count"] + ledger["failed_count"]
        if resolved_count > ledger["requested_count"]:
            return str(path), "count_mismatch"
    return None, None


def validate_checkpoint_evidence(checkpoints: list[dict], path: Path) -> tuple[str | None, str | None]:
    for checkpoint in checkpoints:
        if not isinstance(checkpoint.get("path"), str) or not checkpoint["path"]:
            return str(path), "invalid_checkpoint_evidence"
        if not isinstance(checkpoint.get("sha256"), str) or not checkpoint["sha256"]:
            return str(path), "invalid_checkpoint_evidence"
        if len(checkpoint["sha256"]) != SHA256_HEX_LENGTH:
            return str(path), "invalid_checkpoint_evidence"
        if any(character not in HEX_DIGITS for character in checkpoint["sha256"]):
            return str(path), "invalid_checkpoint_evidence"
        checkpoint_path = Path(checkpoint["path"])
        if not checkpoint_path.is_absolute():
            checkpoint_path = path.parent / checkpoint_path
        if not checkpoint_path.exists():
            return str(path), "missing_checkpoint_file"
        if sha256_file(checkpoint_path) != checkpoint["sha256"]:
            return str(path), "checkpoint_sha_mismatch"
        checkpoint_payload, corrupt_checkpoint_path, corrupt_checkpoint_reason = read_json(checkpoint_path)
        if corrupt_checkpoint_path is not None:
            return corrupt_checkpoint_path, corrupt_checkpoint_reason
        if checkpoint_payload.get("status") != checkpoint.get("status"):
            return str(path), "checkpoint_record_mismatch"
    return None, None


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

    if args.subcommand == "doctor":
        result = run_doctor()
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

    if args.subcommand == "run":
        if args.write_text and (args.write_path is not None or args.write_content is not None):
            parser.error("cannot combine --write-text with --write-path or --write-content")
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
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return IchingKernel.process_exit_code(status=result["status"], reason=result["reason"])

    parser.error(f"unknown command: {args.subcommand}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
