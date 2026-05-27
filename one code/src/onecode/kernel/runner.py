import time
from pathlib import Path
from typing import Any

from onecode.kernel.checkpoint import write_checkpoint, write_ledger
from onecode.kernel.context import create_context
from onecode.kernel.hexagram import COMPLETE
from onecode.kernel.logos_gate import LogosGate


def run_task(
    task: str,
    workspace: Path,
    http_timeout_seconds: float = 60,
    run_id: str | None = None,
    simulated_action_seconds: float = 0,
) -> dict[str, Any]:
    context = create_context(
        workspace_root=workspace,
        http_timeout_seconds=http_timeout_seconds,
        run_id=run_id,
    )
    gate = LogosGate(http_timeout_seconds=http_timeout_seconds)

    def action() -> dict[str, Any]:
        if simulated_action_seconds > 0:
            time.sleep(simulated_action_seconds)
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
    }
    write_ledger(context, result)
    return result
