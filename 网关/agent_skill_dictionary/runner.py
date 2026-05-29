from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .one_word_agent import OneWordAgent


def run_oneword_task(
    user_input: str,
    workspace: str | Path,
    enable_all: bool = False,
    verification_command: list[str] | None = None,
    patch_plan: list[dict[str, Any]] | None = None,
    use_docker: bool = False,
    docker_image: str = "python:3.11-slim",
    require_docker: bool = False,
    enable_external_scanners: bool = False,
    require_guard_scanner: bool = False,
    guard_scanner_types: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    root = Path(workspace).resolve()
    run_dir = root / ".oneword"
    audit_log_path = run_dir / "audit.jsonl"
    docker_required_by_policy = _env_flag("ONEWORD_REQUIRE_DOCKER_FOR_VERIFY")
    effective_require_docker = require_docker or docker_required_by_policy
    effective_use_docker = use_docker or effective_require_docker
    guard_required_by_policy = _env_flag("ONEWORD_REQUIRE_GUARD_SCANNER")
    effective_require_guard_scanner = require_guard_scanner or guard_required_by_policy
    effective_guard_scanner_types = guard_scanner_types or _env_list("ONEWORD_GUARD_SCANNER_TYPE")
    effective_external_scanners = enable_external_scanners or effective_require_guard_scanner
    agent = OneWordAgent(
        codebase_path=str(root),
        verification_command=verification_command,
        audit_log_path=audit_log_path,
        enable_real_inspect=enable_all,
        enable_real_guard=enable_all,
        enable_real_summary=enable_all,
        enable_real_memory=enable_all,
        enable_real_halt=enable_all,
        enable_real_prompt=enable_all,
        enable_real_patch=enable_all,
        use_docker=effective_use_docker,
        docker_image=docker_image,
        require_docker=effective_require_docker,
        enable_external_scanners=effective_external_scanners,
        require_guard_scanner=effective_require_guard_scanner,
        guard_scanner_types=effective_guard_scanner_types,
        memory_dir=run_dir / "memory",
        halt_snapshot_dir=run_dir / "halt",
        prompt_ticket_dir=run_dir / "tickets",
        patch_plan=patch_plan,
        max_steps=12,
    )
    result = agent.run(user_input)
    return {
        **result,
        "audit_log_path": str(audit_log_path),
        "artifacts": _collect_artifacts(agent.context.get("history", [])),
        "history": list(agent.context.get("history", [])),
    }


def main() -> str:
    parser = argparse.ArgumentParser(description="Run a OneWord AgentOS task.")
    parser.add_argument("input", help="User request to compile and run.")
    parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    parser.add_argument(
        "--no-enable-all",
        action="store_true",
        help="Disable real executors and run the minimal FSM path.",
    )
    parser.add_argument("--use-docker", action="store_true", help="Run verification commands in Docker when available.")
    parser.add_argument("--require-docker", action="store_true", help="Fail verification if Docker sandbox is unavailable.")
    parser.add_argument("--docker-image", default="python:3.11-slim", help="Docker image for verification sandbox.")
    parser.add_argument("--enable-external-scanners", action="store_true", help="Enable Semgrep/OSV scanner integration when installed.")
    parser.add_argument("--require-guard-scanner", action="store_true", help="Fail guard if configured scanner binaries are unavailable.")
    parser.add_argument("--guard-scanner-types", default=None, help="Comma-separated scanner list: semgrep,osv-scanner.")
    args = parser.parse_args()
    result = run_oneword_task(
        args.input,
        workspace=args.workspace,
        enable_all=not args.no_enable_all,
        use_docker=args.use_docker,
        docker_image=args.docker_image,
        require_docker=args.require_docker,
        enable_external_scanners=args.enable_external_scanners,
        require_guard_scanner=args.require_guard_scanner,
        guard_scanner_types=_parse_scanner_types(args.guard_scanner_types),
    )
    output = json.dumps(result, ensure_ascii=False, sort_keys=True)
    print(output)
    return output


def _collect_artifacts(history: list[dict[str, Any]]) -> dict[str, Any]:
    artifacts: dict[str, Any] = {
        "summary_markdown": None,
        "memory_archive": None,
        "halt_snapshot": None,
        "confirmation_ticket": None,
        "changed_files": [],
    }
    for item in history:
        result = item.get("result", {}) if isinstance(item.get("result"), dict) else {}
        state = item.get("state")
        if state == "总" and result.get("markdown"):
            artifacts["summary_markdown"] = result["markdown"]
        if state == "记" and result.get("path"):
            artifacts["memory_archive"] = result["path"]
        if state == "停" and result.get("path"):
            artifacts["halt_snapshot"] = result["path"]
        if state == "问" and result.get("path"):
            artifacts["confirmation_ticket"] = result["path"]
        if state == "修" and result.get("changed_files"):
            artifacts["changed_files"] = list(result["changed_files"])
    return artifacts


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str) -> list[str] | None:
    return _parse_scanner_types(os.getenv(name))


def _parse_scanner_types(value: str | None) -> list[str] | None:
    if not value:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or None


if __name__ == "__main__":
    main()
