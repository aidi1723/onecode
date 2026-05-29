from __future__ import annotations

import argparse
import json
from typing import Any

from .agent_protocol import build_agent_protocol_manifest
from .audit import read_audit_log, verify_audit_chain
from .gateway_server import run_task_payload
from .kernel_policy import ROOT_KERNEL_CODES, get_kernel_policy
from .loader import load_dictionary
from .local_preflight import claude_hook_decision
from .minimal_gateway_core import resolve_with_oneword_dict
from .tool_guard import preflight_tool_call


DEFAULT_DICTIONARY_PATH = "agent_skill_dictionary/programming-agent-skill-dictionary.json"


def main() -> str:
    parser = argparse.ArgumentParser(description="OneWord AgentOS local control CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("protocol", help="Print the agent-agnostic protocol manifest.")
    subparsers.add_parser("doctor", help="Check local OneWord control-plane readiness.")

    resolve_parser = subparsers.add_parser("resolve", help="Resolve input into OneWord opcode metadata.")
    resolve_parser.add_argument("input", help="User input to compile.")

    preflight_parser = subparsers.add_parser("preflight", help="Check a tool call before execution.")
    preflight_parser.add_argument("--active-code", required=True)
    preflight_parser.add_argument("--tool-name", required=True)
    preflight_parser.add_argument("--arguments-json", default="{}")
    preflight_parser.add_argument("--dictionary", default=DEFAULT_DICTIONARY_PATH)

    claude_hook_parser = subparsers.add_parser(
        "claude-pretool-hook",
        help="Evaluate a Claude Code PreToolUse hook payload with OneWord preflight.",
    )
    claude_hook_parser.add_argument("--active-code", required=True)
    claude_hook_parser.add_argument("--payload-json", required=True)
    claude_hook_parser.add_argument("--dictionary", default=DEFAULT_DICTIONARY_PATH)

    run_parser = subparsers.add_parser("run", help="Run the local OneWord-Agent FSM.")
    run_parser.add_argument("input")
    run_parser.add_argument("--workspace", default=".")
    run_parser.add_argument("--disable-executors", action="store_true")
    run_parser.add_argument("--verification-command-json")
    run_parser.add_argument("--use-docker", action="store_true")
    run_parser.add_argument("--require-docker", action="store_true")
    run_parser.add_argument("--docker-image", default="python:3.11-slim")
    run_parser.add_argument("--enable-external-scanners", action="store_true")
    run_parser.add_argument("--require-guard-scanner", action="store_true")
    run_parser.add_argument("--guard-scanner-types", default=None)

    audit_parser = subparsers.add_parser("audit", help="Read an audit JSONL file.")
    audit_parser.add_argument("--path", required=True)

    guarded_run_parser = subparsers.add_parser(
        "build-mode-guarded-run",
        help="Run a local command under Build Mode sovereignty checks.",
    )
    guarded_run_parser.add_argument("--workspace", required=True)
    guarded_run_parser.add_argument("--request-text", required=True)
    guarded_run_parser.add_argument("--timeout-seconds", type=int, default=30)
    guarded_run_parser.add_argument("runtime_command", nargs=argparse.REMAINDER)

    expert_parser = subparsers.add_parser(
        "build-mode-expert-handoff",
        help="Apply a human-authorized expert seed after Build Mode failure gate.",
    )
    expert_parser.add_argument("--workspace", required=True)
    expert_parser.add_argument("--session-id", default="")
    expert_parser.add_argument("--request-text", required=True)
    expert_parser.add_argument("--token", required=True)
    expert_parser.add_argument("--changes-json", required=True)
    expert_parser.add_argument("--verify-command-json", required=True)
    expert_parser.add_argument("--lockdown", action="store_true")

    args = parser.parse_args()
    payload = _dispatch(args)
    output = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    print(output)
    return output


def _dispatch(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "protocol":
        return build_agent_protocol_manifest()
    if args.command == "doctor":
        manifest = build_agent_protocol_manifest()
        load_dictionary(DEFAULT_DICTIONARY_PATH)
        for code in ROOT_KERNEL_CODES:
            get_kernel_policy(code)
        return {
            "ok": True,
            "protocol": manifest["name"],
            "dictionary": "valid",
            "root_opcode_count": len(manifest["root_opcodes"]),
            "commands": ["protocol", "resolve", "preflight", "run", "audit", "doctor"],
        }
    if args.command == "resolve":
        return resolve_with_oneword_dict(args.input)
    if args.command == "preflight":
        return preflight_tool_call(
            load_dictionary(args.dictionary),
            active_code=args.active_code,
            tool_name=args.tool_name,
            arguments=json.loads(args.arguments_json),
        )
    if args.command == "claude-pretool-hook":
        return claude_hook_decision(
            load_dictionary(args.dictionary),
            active_code=args.active_code,
            hook_payload=json.loads(args.payload_json),
        )
    if args.command == "run":
        return run_task_payload(
            {
                "input": args.input,
                "workspace": args.workspace,
                "require_configured_workspace_root": False,
                "require_safe_verification_command": False,
                "enable_all": not args.disable_executors,
                "verification_command": json.loads(getattr(args, "verification_command_json", None))
                if getattr(args, "verification_command_json", None)
                else None,
                "use_docker": getattr(args, "use_docker", False),
                "require_docker": getattr(args, "require_docker", False),
                "docker_image": getattr(args, "docker_image", "python:3.11-slim"),
                "enable_external_scanners": getattr(args, "enable_external_scanners", False),
                "require_guard_scanner": getattr(args, "require_guard_scanner", False),
                "guard_scanner_types": _parse_scanner_types(
                    getattr(args, "guard_scanner_types", None)
                ),
            }
        )
    if args.command == "audit":
        records = read_audit_log(args.path)
        verification = verify_audit_chain(args.path)
        return {
            "path": args.path,
            "count": len(records),
            "valid_chain": verification["valid"],
            "chain_errors": verification["errors"],
            "records": records,
        }
    if args.command == "build-mode-guarded-run":
        from .build_mode_orchestrator import artifact_plan_for_request
        from .build_mode_runtime_guard import run_guarded_runtime

        runtime_command = list(getattr(args, "runtime_command", []))
        if runtime_command and runtime_command[0] == "--":
            runtime_command = runtime_command[1:]
        if not runtime_command:
            return {
                "status": "blocked",
                "exit_code": 126,
                "reason": "empty_runtime_command",
            }
        plan = artifact_plan_for_request(args.request_text)
        if not plan.artifacts:
            return {
                "status": "blocked",
                "exit_code": 126,
                "reason": "unknown_artifact_plan",
            }
        return run_guarded_runtime(
            runtime_command,
            workspace=args.workspace,
            artifact_plan=plan,
            timeout_seconds=args.timeout_seconds,
        )
    if args.command == "build-mode-expert-handoff":
        from .build_mode_expert_handoff import apply_expert_seed
        from .build_mode_orchestrator import artifact_plan_for_request
        from .gateway_server import _build_mode_state_path_for_metadata, _persist_expert_handoff_state

        plan = artifact_plan_for_request(args.request_text)
        if not plan.artifacts:
            return {
                "status": "blocked",
                "exit_code": 126,
                "reason": "unknown_artifact_plan",
            }
        metadata = {"workspace": args.workspace}
        if args.session_id:
            metadata["session_id"] = args.session_id
        state_path = _build_mode_state_path_for_metadata(metadata)
        result = apply_expert_seed(
            workspace=args.workspace,
            artifact_plan=plan,
            token=args.token,
            changes=json.loads(args.changes_json),
            verify_command=json.loads(args.verify_command_json),
            lockdown=bool(args.lockdown),
            state_path=state_path,
        )
        if result.get("status") == "completed":
            _persist_expert_handoff_state(args.workspace, result, metadata)
        return result
    raise ValueError(f"Unsupported command: {args.command}")


def _parse_scanner_types(value: str | None) -> list[str] | None:
    if not value:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or None


if __name__ == "__main__":
    main()
