"""Run the pinned sandbox verifier only for a kan-hexagram verifier decision."""

from pathlib import Path
from typing import Callable

from onecode.experimental.yizijue_ledger import NON_EXECUTION_REASONS, execution_view
from onecode.kernel.project_gateway import gateway_disagreement
from onecode.kernel.verifier import VERIFIER_POLICY_PRESETS

PINNED_VERIFIER_STATE = "010010"
VERIFIER_ACTION = "RUN_VERIFIER_IN_SANDBOX"
WITHHELD_REASONS = NON_EXECUTION_REASONS
Runner = Callable[[Path, list[str]], dict]


def verifier_block_reason(entry: dict) -> str | None:
    entry = execution_view(entry)
    if entry.get("executed") is True:
        return "already_executed"
    if entry.get("reason") in WITHHELD_REASONS:
        return "withheld"
    if entry.get("yizijue_state") != PINNED_VERIFIER_STATE or entry.get("action") != VERIFIER_ACTION:
        return "not_verifier"
    if entry.get("cycle") != "verify":
        return "not_verifier"
    return gateway_disagreement(entry.get("yizijue_state"), entry.get("facts"), entry.get("action"))


def pinned_verifier_command() -> list[str]:
    return list(VERIFIER_POLICY_PRESETS["python-unittest"]["command"])  # type: ignore


def sandbox_unittest_runner(workspace: Path, command: list[str]) -> dict:
    if list(command) != pinned_verifier_command():
        return {"status": "failed", "reason": "command_rejected"}
    from onecode.kernel.sandbox import SandboxConfig
    from onecode.kernel.verifier import VerifierSpec, run_verifier

    spec = VerifierSpec(id="python-unittest", command=list(command), cwd=".", timeout_ms=30000)
    try:
        result = run_verifier(
            workspace,
            spec,
            sandbox_config=SandboxConfig(workspace=workspace, timeout_seconds=30),
        )
    except Exception as exc:
        return {"status": "failed", "reason": type(exc).__name__, "command": list(command)}
    return {"status": result.status, "reason": result.reason, "command": list(command)}


def run_pinned_verifier(workspace: Path, entry: dict, runner: Runner) -> dict:
    entry = execution_view(entry)
    blocked = verifier_block_reason(entry)
    if blocked is not None:
        return {"ran": False, "executed": False, "reason": blocked}
    command = pinned_verifier_command()
    result = runner(workspace, command)
    if not _verifier_confirmed(result, command):
        return {"ran": False, "executed": False, "reason": "verifier_unconfirmed", "command": command, "result": result}
    return {"ran": True, "executed": True, "command": command, "result": result}


def _verifier_confirmed(result: object, command: list[str]) -> bool:
    if not isinstance(result, dict) or result.get("status") not in {"passed", "failed", "skipped"}:
        return False
    if result.get("reason") == "command_rejected":
        return False
    reported = result.get("command")
    try:
        return list(reported) == list(command)  # type: ignore
    except TypeError:
        return False
