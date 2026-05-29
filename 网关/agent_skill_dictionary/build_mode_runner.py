from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from typing import Any

from .build_mode_archive import finalize_manifest
from .build_mode_feedback import rewrite_to_soft_payload
from .build_mode_fsm import next_hexagram
from .build_mode_intent import resolve_intent
from .build_mode_sandbox import run_isolated_test
from .build_mode_types import (
    HEX_CORRECT,
    HEX_CREATE,
    HEX_HALT,
    HEX_INSPECT,
    HEX_RETURN,
    HEX_VERIFY,
    SandboxEvidence,
    ViolationEvidence,
)
from .build_mode_writer import safe_write


def run_build_mode_task(
    user_input: str,
    workspace: str | Path,
    writes: list[dict[str, str]] | None = None,
    verification_command: list[str] | None = None,
    use_docker: bool = False,
    timeout_seconds: int = 15,
    lockdown: bool = False,
) -> dict[str, Any]:
    root = Path(workspace).resolve()
    trace: list[str] = []
    intent = resolve_intent({"messages": [{"role": "user", "content": user_input}]})
    current = intent.hexagram if intent.hexagram == HEX_CREATE else HEX_CREATE
    trace.append(current)

    changed_files: list[str] = []
    for item in writes or []:
        evidence = safe_write(root, str(item.get("path", "")), str(item.get("content", "")))
        if isinstance(evidence, ViolationEvidence):
            halt_state = next_hexagram(current, evidence)
            trace.append(halt_state)
            feedback = rewrite_to_soft_payload(evidence)
            trace.append(HEX_CORRECT)
            return {
                "status": "halted",
                "trace": trace,
                "intent": intent,
                "violation": evidence,
                "feedback": feedback,
            }
        changed_files.extend(evidence.changed_files)

    if not changed_files:
        violation = ViolationEvidence("write:none", "no_changed_files", "build_mode_runner")
        trace.append(HEX_HALT)
        feedback = rewrite_to_soft_payload(violation)
        trace.append(HEX_CORRECT)
        return {"status": "halted", "trace": trace, "intent": intent, "feedback": feedback}

    current = HEX_VERIFY
    trace.append(current)
    sandbox = run_isolated_test(
        verification_command or ["python3", "-m", "unittest", "discover"],
        root,
        use_docker=use_docker,
        timeout_seconds=timeout_seconds,
    )
    next_state = next_hexagram(current, sandbox)
    if next_state == HEX_RETURN:
        trace.append(HEX_RETURN)
        archive = finalize_manifest(root, lockdown=lockdown)
        summary_state = next_hexagram(HEX_RETURN, archive)
        trace.append(summary_state)
        return {
            "status": "completed",
            "trace": trace,
            "intent": intent,
            "changed_files": changed_files,
            "sandbox": sandbox,
            "archive": archive,
            "summary": _summary_text(user_input, changed_files, sandbox),
        }
    if next_state == HEX_HALT:
        trace.append(HEX_HALT)
        violation = _sandbox_violation(sandbox)
        feedback = rewrite_to_soft_payload(violation)
        trace.append(HEX_CORRECT)
        return {
            "status": "halted",
            "trace": trace,
            "intent": intent,
            "changed_files": changed_files,
            "sandbox": sandbox,
            "feedback": feedback,
        }

    trace.append(HEX_CORRECT)
    feedback = rewrite_to_soft_payload(sandbox)
    trace.append(HEX_INSPECT)
    return {
        "status": "needs_fix",
        "trace": trace,
        "intent": intent,
        "changed_files": changed_files,
        "sandbox": sandbox,
        "feedback": feedback,
        "repo_card": _repo_card(root, changed_files, sandbox),
    }


def main() -> str:
    parser = argparse.ArgumentParser(description="Run a deterministic Build Mode task.")
    parser.add_argument("input", help="User request.")
    parser.add_argument("--workspace", default=".", help="Workspace root.")
    parser.add_argument(
        "--write",
        action="append",
        default=[],
        help="Scoped write in path=content form. Can be repeated.",
    )
    parser.add_argument("--verify", default=None, help="Verification command.")
    parser.add_argument("--use-docker", action="store_true", help="Run verification in Docker when available.")
    parser.add_argument("--lockdown", action="store_true", help="Enable chmod lockdown during archive.")
    args = parser.parse_args()
    result = run_build_mode_task(
        args.input,
        workspace=args.workspace,
        writes=_parse_writes(args.write),
        verification_command=shlex.split(args.verify) if args.verify else None,
        use_docker=args.use_docker,
        lockdown=args.lockdown,
    )
    output = json.dumps(_jsonable(result), ensure_ascii=False, sort_keys=True)
    print(output)
    return output


def _parse_writes(values: list[str]) -> list[dict[str, str]]:
    writes: list[dict[str, str]] = []
    for value in values:
        path, separator, content = value.partition("=")
        if not separator or not path:
            raise ValueError("--write must use path=content form")
        writes.append({"path": path, "content": content})
    return writes


def _jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        from .build_mode_types import dto_to_dict

        return dto_to_dict(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    return value


def _sandbox_violation(evidence: SandboxEvidence) -> ViolationEvidence:
    if evidence.timed_out:
        reason = "sandbox_timeout"
    elif evidence.oom:
        reason = "sandbox_oom"
    else:
        reason = "sandbox_halt"
    return ViolationEvidence("run_test", reason, "sandbox_runner", exit_code=evidence.exit_code)


def _repo_card(root: Path, changed_files: list[str], sandbox: SandboxEvidence) -> dict[str, Any]:
    return {
        "workspace": str(root),
        "changed_files": changed_files,
        "last_exit_code": sandbox.exit_code,
        "pytest_status": sandbox.pytest_status,
        "stdout_sha256": sandbox.stdout_sha256,
        "stderr_sha256": sandbox.stderr_sha256,
    }


def _summary_text(user_input: str, changed_files: list[str], sandbox: SandboxEvidence) -> str:
    files = ", ".join(changed_files) if changed_files else "none"
    return (
        "# Build Mode Summary\n\n"
        f"- Request: {user_input}\n"
        f"- Changed files: {files}\n"
        f"- Verification exit code: {sandbox.exit_code}\n"
        f"- Verification status: {sandbox.pytest_status}\n"
    )


if __name__ == "__main__":
    main()
