from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from onecode.kernel.cycle_approvals import load_pending_approvals
from onecode.web.api_handlers import (
    handle_onecode_approval_resolve,
    handle_onecode_pending_approvals,
)


def register_approvals_commands(subparsers: argparse._SubParsersAction) -> None:
    approvals_parser = subparsers.add_parser("approvals", help="Manage pending human-in-the-loop approvals")
    approvals_sub = approvals_parser.add_subparsers(dest="approvals_subcommand", required=True)

    # list
    list_parser = approvals_sub.add_parser("list", help="List pending approvals")
    list_parser.add_argument("--workspace", default=".", help="Workspace directory")
    list_parser.add_argument("--json", action="store_true", help="Output raw JSON")

    # show
    show_parser = approvals_sub.add_parser("show", help="Show details of a pending approval")
    show_parser.add_argument("approval_id", help="Approval ticket ID")
    show_parser.add_argument("--workspace", default=".", help="Workspace directory")
    show_parser.add_argument("--json", action="store_true", help="Output raw JSON")

    # resolve
    resolve_parser = approvals_sub.add_parser("resolve", help="Resolve a pending approval and resume")
    resolve_parser.add_argument("approval_id", help="Approval ticket ID")
    resolve_parser.add_argument("--decision", choices=["approved", "rejected"], default="approved", help="Decision")
    resolve_parser.add_argument("--selected-slug", default=None, help="Engineer-selected short code")
    resolve_parser.add_argument("--target-slug", default=None, help="Target slug to replace")
    resolve_parser.add_argument("--workspace", default=".", help="Workspace directory")
    resolve_parser.add_argument("--json", action="store_true", help="Output raw JSON")


def dispatch_approvals_command(args: argparse.Namespace) -> int | None:
    if getattr(args, "subcommand", None) != "approvals":
        return None

    workspace = Path(args.workspace).resolve()
    orig_allowed = os.environ.get("ONECODE_ALLOWED_WORKSPACE_ROOTS")
    allowed_roots = [p for p in (orig_allowed or "").split(os.pathsep) if p]
    if str(workspace) not in allowed_roots:
        allowed_roots.append(str(workspace))
        os.environ["ONECODE_ALLOWED_WORKSPACE_ROOTS"] = os.pathsep.join(allowed_roots)

    try:
        return _execute_approvals_command(args, workspace)
    finally:
        if orig_allowed is None:
            os.environ.pop("ONECODE_ALLOWED_WORKSPACE_ROOTS", None)
        else:
            os.environ["ONECODE_ALLOWED_WORKSPACE_ROOTS"] = orig_allowed


def _execute_approvals_command(args: argparse.Namespace, workspace: Path) -> int:
    sub = getattr(args, "approvals_subcommand", None)
    if sub == "list":
        res, code = handle_onecode_pending_approvals({"workspace": str(workspace)})
        if getattr(args, "json", False):
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            items = res.get("approvals", [])
            print(f"Pending Approvals: {len(items)}")
            for it in items:
                aid = it.get("id")
                tool = it.get("tool_name")
                params = it.get("params") or {}
                checks = params.get("failing_checks") or []
                reasons = params.get("emitted_reasons") or []
                print(f"- ID: {aid}")
                print(f"  Tool: {tool}")
                if checks:
                    print(f"  Failing Checks: {', '.join(checks)}")
                if reasons:
                    print(f"  Emitted Reasons: {', '.join(reasons)}")
        return 0 if code == 200 else 1

    if sub == "show":
        aid = args.approval_id
        items = load_pending_approvals(workspace)
        match = next((x for x in items if x.get("id") == aid), None)
        if not match:
            print(f"Error: Approval ticket '{aid}' not found.", file=sys.stderr)
            return 1
        if getattr(args, "json", False):
            print(json.dumps(match, ensure_ascii=False, indent=2))
        else:
            print(f"Approval ID: {match.get('id')}")
            print(f"Status: {match.get('status')}")
            print(f"Tool Name: {match.get('tool_name')}")
            params = match.get("params") or {}
            print(f"Params: {json.dumps(params, ensure_ascii=False, indent=2)}")
        return 0

    if sub == "resolve":
        aid = args.approval_id
        body = {
            "workspace": str(workspace),
            "decision": args.decision,
        }
        if args.selected_slug:
            body["selected_slug"] = args.selected_slug
        if args.target_slug:
            body["target_slug"] = args.target_slug

        res, code = handle_onecode_approval_resolve(aid, body)
        if getattr(args, "json", False):
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            if code == 200:
                print(f"Approval {aid} resolved successfully.")
                if res.get("repair_applied"):
                    print("Repair Applied: True")
                    print(f"Regraded Host Reward: {res.get('host_reward')}")
                    print(f"Status: {res.get('repair_status')}")
            else:
                print(f"Failed to resolve approval (HTTP {code}): {json.dumps(res, ensure_ascii=False)}", file=sys.stderr)
        return 0 if code == 200 else 1

    return 1
