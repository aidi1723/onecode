import argparse
import json
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
    run_parser.add_argument("--intent-type", default="noop")
    run_parser.add_argument("--command", dest="intent_command", default=None)
    run_parser.add_argument("--resume-from", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.subcommand == "run":
        result = run_task(
            args.task,
            workspace=Path(args.workspace),
            http_timeout_seconds=args.http_timeout_seconds,
            run_id=args.run_id,
            simulated_action_seconds=args.simulate_action_seconds,
            write_path=args.write_path,
            write_content=args.write_content,
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
