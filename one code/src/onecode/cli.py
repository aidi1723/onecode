import argparse
import json
from pathlib import Path

from onecode.kernel.runner import run_task


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="onecode")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("task")
    run_parser.add_argument("--workspace", default=".")
    run_parser.add_argument("--http-timeout-seconds", type=float, default=60)
    run_parser.add_argument("--run-id", default=None)
    run_parser.add_argument("--simulate-action-seconds", type=float, default=0)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        result = run_task(
            args.task,
            workspace=Path(args.workspace),
            http_timeout_seconds=args.http_timeout_seconds,
            run_id=args.run_id,
            simulated_action_seconds=args.simulate_action_seconds,
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
