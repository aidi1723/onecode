import time
from pathlib import Path
from typing import Any

from onecode.kernel.action_intent import ActionIntent
from onecode.kernel.checkpoint import write_checkpoint, write_ledger
from onecode.kernel.context import create_context
from onecode.kernel.hexagram import COMPLETE
from onecode.kernel.logos_gate import LogosGate
from onecode.kernel.path_guard import PathGuard
from onecode.kernel.permission_matrix import Decision


def build_intent(
    intent_type: str,
    write_path: str | None,
    write_content: str | None,
    command: str | None,
) -> ActionIntent:
    if write_path is not None or write_content is not None:
        return ActionIntent.write_text(write_path or "", write_content or "")
    if intent_type == "bash_execution":
        return ActionIntent.bash_execution(command or "")
    if intent_type == "execute_pytest":
        return ActionIntent.execute_pytest(command or "tests")
    return ActionIntent.noop()


def run_task(
    task: str,
    workspace: Path,
    http_timeout_seconds: float = 60,
    run_id: str | None = None,
    simulated_action_seconds: float = 0,
    write_path: str | None = None,
    write_content: str | None = None,
    intent_type: str = "noop",
    command: str | None = None,
    resume_from_run_id: str | None = None,
) -> dict[str, Any]:
    context = create_context(
        workspace_root=workspace,
        http_timeout_seconds=http_timeout_seconds,
        run_id=run_id,
        resume_from_run_id=resume_from_run_id,
    )
    gate = LogosGate(http_timeout_seconds=http_timeout_seconds)
    intent = build_intent(intent_type, write_path, write_content, command)
    preflight = gate.preflight(context, intent)

    if preflight.decision == Decision.DENIED:
        gate_result = {
            "status": "denied",
            "partial": False,
            "reason": preflight.reason,
            "payload": preflight.to_dict(),
        }
    elif preflight.decision == Decision.HALTED:
        gate_result = {
            "status": "halted",
            "partial": True,
            "reason": preflight.reason,
            "payload": preflight.to_dict(),
        }
    else:

        def action() -> dict[str, Any]:
            if simulated_action_seconds > 0:
                time.sleep(simulated_action_seconds)
            if intent.action_type.value == "write_text":
                return PathGuard.write_text(context.workspace_root, intent.payload["path"], intent.payload["content"])
            return {
                "task": task,
                "run_id": context.run_id,
                "turn_index": context.turn_index + 1,
            }

        gate_result = gate.run_bounded_action(action)

    write_checkpoint(
        context=context,
        payload=gate_result["payload"],
        next_state=COMPLETE,
        status=gate_result["status"],
        partial=gate_result["partial"],
        reason=gate_result["reason"],
        intent_type=intent.action_type.value,
        decision=preflight.decision.value,
    )

    ledger_path = context.evidence_root / "ledger.json"
    result = {
        "run_id": context.run_id,
        "status": gate_result["status"],
        "state": str(COMPLETE),
        "manifest_path": str(context.manifest_path),
        "ledger_path": str(ledger_path),
        "partial": gate_result["partial"],
        "reason": gate_result["reason"],
        "decision": preflight.decision.value,
        "intent_type": intent.action_type.value,
        "payload": gate_result["payload"],
        "resumed_from": resume_from_run_id,
    }
    if "sha256" in gate_result["payload"]:
        result["sha256"] = gate_result["payload"]["sha256"]
    write_ledger(context, result)
    return result
