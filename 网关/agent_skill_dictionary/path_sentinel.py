from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Sequence

from .build_mode_orchestrator import artifact_plan_for_request
from .build_mode_sovereignty import (
    audit_environment_gate,
    audit_workspace_sovereignty,
)
from .loader import load_dictionary
from .local_preflight import preflight_claude_tool_call


DEFAULT_DICTIONARY_PATH = "agent_skill_dictionary/programming-agent-skill-dictionary.json"

DEFAULT_REAL_BINARIES = {
    "bash": "/bin/bash",
    "sh": "/bin/sh",
    "zsh": "/bin/zsh",
    "rm": "/bin/rm",
    "tee": "/usr/bin/tee",
    "mv": "/bin/mv",
    "cp": "/bin/cp",
    "chmod": "/bin/chmod",
    "python": sys.executable,
    "python3": sys.executable,
    "node": "/usr/bin/node",
}


def run_bash_sentinel(argv: Sequence[str]) -> int:
    return run_command_sentinel("bash", argv)


def run_rm_sentinel(argv: Sequence[str]) -> int:
    return run_command_sentinel("rm", argv)


def run_command_sentinel(kind: str, argv: Sequence[str]) -> int:
    command = _command_string(kind, argv)
    sovereignty = _build_mode_sovereignty_decision()
    if sovereignty is not None:
        _print_sovereignty_denied(sovereignty)
        return 126
    if _build_mode_runtime_passthrough_allowed(kind):
        real_binary = _real_binary(kind)
        os.execv(real_binary, [real_binary, *argv])
        return 127
    decision = _preflight("Bash", {"command": command})
    if not decision["allowed"]:
        _print_denied(decision)
        return 126
    real_binary = _real_binary(kind)
    os.execv(real_binary, [real_binary, *argv])
    return 127


def _command_string(kind: str, argv: Sequence[str]) -> str:
    args = " ".join(str(item) for item in argv)
    if not args:
        return kind
    return f"{kind} {args}"


def _real_binary(kind: str) -> str:
    env_name = "ONEWORD_REAL_" + kind.upper().replace("-", "_")
    configured = os.getenv(env_name)
    if configured:
        return configured
    default = DEFAULT_REAL_BINARIES.get(kind)
    if default and Path(default).exists():
        return default
    found = shutil.which(kind)
    if found:
        return found
    return default or kind


def _preflight(tool_name: str, tool_input: dict[str, str]) -> dict[str, object]:
    dictionary_path = os.getenv("ONEWORD_DICTIONARY_PATH", DEFAULT_DICTIONARY_PATH)
    active_code = os.getenv("ONEWORD_ACTIVE_CODE", "查")
    dictionary = load_dictionary(dictionary_path)
    return preflight_claude_tool_call(dictionary, active_code, tool_name, tool_input)


def _build_mode_sovereignty_decision() -> dict[str, object] | None:
    if os.getenv("ONEWORD_BUILD_MODE", "").lower() not in {"1", "true", "yes", "on"}:
        return None
    workspace = os.getenv("ONEWORD_BUILD_MODE_WORKSPACE") or os.getenv("ONEWORD_WORKSPACE_ROOT")
    request_text = os.getenv("ONEWORD_BUILD_MODE_REQUEST_TEXT") or os.getenv("ONEWORD_BUILD_MODE_PROJECT") or ""
    if not workspace or not request_text:
        return None
    plan = artifact_plan_for_request(request_text)
    if not plan.artifacts:
        return None
    if os.getenv("ONEWORD_BUILD_MODE_REQUIRE_REAL_DEPS", "").lower() in {"1", "true", "yes", "on"}:
        python_executable = os.getenv("ONEWORD_BUILD_MODE_PYTHON") or sys.executable
        env_report = audit_environment_gate(plan, python_executable=python_executable)
        if not env_report.ok:
            return {
                "source": "sovereignty_environment_gate",
                "hexagram": "100",
                "missing_packages": list(env_report.missing_packages),
                "python_executable": env_report.python_executable,
            }
    workspace_report = audit_workspace_sovereignty(workspace, plan)
    if not workspace_report.ok:
        return {
            "source": "sovereignty_workspace_gate",
            "hexagram": "100",
            "unplanned_paths": list(workspace_report.unplanned_paths),
        }
    return None


def _build_mode_runtime_passthrough_allowed(kind: str) -> bool:
    if os.getenv("ONEWORD_BUILD_MODE_RUNTIME_PASSTHROUGH", "").lower() not in {"1", "true", "yes", "on"}:
        return False
    if os.getenv("ONEWORD_BUILD_MODE", "").lower() not in {"1", "true", "yes", "on"}:
        return False
    if os.getenv("ONEWORD_ACTIVE_CODE") != "测":
        return False
    return kind in {"python", "python3"}


def _print_denied(decision: dict[str, object]) -> None:
    violations = decision.get("violations", [])
    print("oneword local preflight denied", file=sys.stderr)
    print(f"active_code={decision.get('active_code')}", file=sys.stderr)
    print(f"tool={decision.get('original_tool')} normalized={decision.get('normalized_tool')}", file=sys.stderr)
    print(f"violations={violations}", file=sys.stderr)


def _print_sovereignty_denied(decision: dict[str, object]) -> None:
    print("oneword build mode sovereignty denied", file=sys.stderr)
    print(f"source={decision.get('source')} hexagram={decision.get('hexagram')}", file=sys.stderr)
    if decision.get("missing_packages"):
        print(f"missing_packages={decision.get('missing_packages')}", file=sys.stderr)
    if decision.get("unplanned_paths"):
        print(f"unplanned_paths={decision.get('unplanned_paths')}", file=sys.stderr)


def main(kind: str, argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if kind == "bash":
        return run_bash_sentinel(args)
    if kind == "rm":
        return run_rm_sentinel(args)
    return run_command_sentinel(kind, args)
