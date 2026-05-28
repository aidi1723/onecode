import argparse
import json
import tempfile
from pathlib import Path

from onecode.kernel.runner import run_task


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


def read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def inspect_run(workspace: Path, run_id: str) -> tuple[int, dict]:
    evidence_root = workspace.resolve() / ".onecode" / "runs" / run_id
    manifest_path = evidence_root / "manifest.json"
    ledger_path = evidence_root / "ledger.json"
    manifest = read_json(manifest_path)
    ledger = read_json(ledger_path)
    if manifest is None or ledger is None:
        return 1, {
            "run_id": run_id,
            "status": "missing",
            "manifest_path": str(manifest_path),
            "ledger_path": str(ledger_path),
        }
    checkpoints = manifest.get("checkpoints", [])
    return 0, {
        "run_id": run_id,
        "status": ledger.get("status", manifest.get("status")),
        "partial": ledger.get("partial", manifest.get("partial")),
        "reason": ledger.get("reason", manifest.get("reason")),
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
        "manifest_path": str(manifest_path),
        "ledger_path": str(ledger_path),
    }


def list_runs(workspace: Path) -> dict:
    resolved_workspace = workspace.resolve()
    runs_root = resolved_workspace / ".onecode" / "runs"
    if not runs_root.exists():
        return {"workspace": str(workspace), "runs": []}
    runs = []
    for run_dir in sorted(path for path in runs_root.iterdir() if path.is_dir()):
        exit_code, summary = inspect_run(resolved_workspace, run_dir.name)
        if exit_code == 0:
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

    if args.subcommand == "run":
        if args.write_text and (args.write_path is not None or args.write_content is not None):
            parser.error("cannot combine --write-text with --write-path or --write-content")
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
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    parser.error(f"unknown command: {args.subcommand}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
