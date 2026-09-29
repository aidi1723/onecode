"""Local release snapshot commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from onecode.kernel.release_rollback import rollback_release, snapshot_release, stage_release


def register_release_commands(subparsers: argparse._SubParsersAction) -> None:
    release_parser = subparsers.add_parser("release")
    release_subparsers = release_parser.add_subparsers(dest="release_action", required=True)
    snapshot_parser = release_subparsers.add_parser("snapshot")
    snapshot_parser.add_argument("--root", required=True)
    snapshot_parser.add_argument("--version", required=True)
    stage_parser = release_subparsers.add_parser("stage")
    stage_parser.add_argument("--root", required=True)
    stage_parser.add_argument("--version", required=True)
    rollback_parser = release_subparsers.add_parser("rollback")
    rollback_parser.add_argument("--root", required=True)


def dispatch_release_command(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int | None:
    if args.subcommand != "release":
        return None
    root = Path(args.root)
    try:
        if args.release_action == "snapshot":
            path = snapshot_release(root, args.version)
            print(json.dumps({"version": args.version, "snapshot": str(path)}, ensure_ascii=False, sort_keys=True))
            return 0
        if args.release_action == "stage":
            stage_release(root, args.version, {})
            print(json.dumps({"version": args.version}, ensure_ascii=False, sort_keys=True))
            return 0
        if args.release_action == "rollback":
            restored = rollback_release(root)
            print(json.dumps(restored, ensure_ascii=False, sort_keys=True))
            return 0
    except ValueError as exc:
        parser.error(str(exc))
    parser.error(f"unknown release action: {args.release_action}")
    return 2
