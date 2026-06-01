from __future__ import annotations

from pathlib import Path
from typing import Any

from onecode.kernel.checkpoint import write_checkpoint, write_ledger
from onecode.kernel.context import create_context
from onecode.kernel.hexagram import COMPLETE, IchingKernel
from onecode.kernel.trace import TraceEvent, write_trace_event


def finalize_run_event(
    task: str,
    workspace: Path,
    run_id: str,
    intent_type: str,
    status: str,
    payload: dict[str, Any] | None = None,
    partial: bool = False,
    reason: str | None = None,
    decision: str = "allowed",
    http_timeout_seconds: float = 60,
) -> dict[str, Any]:
    context = create_context(
        workspace_root=workspace,
        http_timeout_seconds=http_timeout_seconds,
        run_id=run_id,
    )
    trace_path = context.evidence_root / "trace.jsonl"
    event_payload = payload or {}
    write_trace_event(
        trace_path,
        TraceEvent(
            trace_id=context.run_id,
            run_id=context.run_id,
            span_id="run",
            parent_span_id=None,
            event_type="run_started",
            status="started",
            payload={"task": task, "intent_type": intent_type},
        ),
    )

    raw_status_code = IchingKernel.classify_outcome(status, reason)
    iching_transition = IchingKernel.transition(raw_status_code)
    iching_profile = IchingKernel.cross_cutting_profile(iching_transition.status_code)
    balanced_status_code = IchingKernel.apply_balanced_event(raw_status_code, reason or status)
    balance_mask = IchingKernel.balance_mask(raw_status_code)
    balanced_transition = IchingKernel.transition(balanced_status_code)
    four_symbol_balance = IchingKernel.four_symbol_balance_vector(raw_status_code)
    run_control = IchingKernel.entropy_regulated_status([raw_status_code])
    global_status_code = int(run_control["status_code"])
    global_transition = IchingKernel.transition(global_status_code)
    run_control_payload = {
        "global_status_code": global_status_code,
        "global_transition_action": global_transition.action,
        "global_transition_reason": global_transition.reason,
        "global_entropy": run_control["entropy"],
        "global_entropy_decision": run_control["decision"],
        "global_entropy_reason": run_control.get("reason"),
    }
    write_checkpoint(
        context=context,
        payload=event_payload,
        next_state=COMPLETE,
        status=status,
        partial=partial,
        reason=reason,
        intent_type=intent_type,
        decision=decision,
        iching_status_code=iching_transition.status_code,
        iching_transition_action=iching_transition.action,
        iching_transition_reason=iching_transition.reason,
        iching_profile=iching_profile,
        run_control=run_control_payload,
    )
    write_trace_event(
        trace_path,
        TraceEvent(
            trace_id=context.run_id,
            run_id=context.run_id,
            span_id="checkpoint-1",
            parent_span_id="run",
            event_type="checkpoint_written",
            status=status,
            payload={"intent_type": intent_type, "status": status},
        ),
    )
    completed_count = 1 if status == "completed" else 0
    skipped_count = 1 if status == "skipped" else 0
    failed_count = 1 if status in {"denied", "halted"} else 0
    result = {
        "run_id": context.run_id,
        "status": status,
        "state": str(COMPLETE),
        "manifest_path": str(context.manifest_path),
        "ledger_path": str(context.evidence_root / "ledger.json"),
        "trace_id": context.run_id,
        "trace_path": str(trace_path),
        "partial": partial,
        "reason": reason,
        "decision": decision,
        "intent_type": intent_type,
        "payload": event_payload,
        "assets": [
            {
                "index": 1,
                "status": status,
                "partial": partial,
                "reason": reason,
                "decision": decision,
                "intent_type": intent_type,
                "duration_ms": 0,
                "raw_status_code": raw_status_code,
                "balanced_status_code": balanced_status_code,
                "balance_mask": balance_mask,
                "balance_action": balanced_transition.action,
                "four_symbol_decision": str(four_symbol_balance["decision"]),
                "four_symbol_change_mask": int(four_symbol_balance["change_mask"]),
                "four_symbol_reason": four_symbol_balance["reason"] if isinstance(four_symbol_balance["reason"], str) else None,
                "payload": event_payload,
                "raw_payload": event_payload,
                "resumed": False,
                "iching_status_code": iching_transition.status_code,
                "iching_transition_action": iching_transition.action,
                "iching_transition_reason": iching_transition.reason,
                "iching_profile": iching_profile,
            }
        ],
        "requested_count": 1,
        "completed_count": completed_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
        "global_status_code": global_status_code,
        "global_transition_action": global_transition.action,
        "global_transition_reason": global_transition.reason,
        "global_entropy": run_control["entropy"],
        "global_entropy_decision": run_control["decision"],
        "global_entropy_reason": run_control.get("reason"),
        "iching_status_code": iching_transition.status_code,
        "iching_transition_action": iching_transition.action,
        "iching_transition_reason": iching_transition.reason,
        "iching_profile": iching_profile,
    }
    write_trace_event(
        trace_path,
        TraceEvent(
            trace_id=context.run_id,
            run_id=context.run_id,
            span_id="run",
            parent_span_id=None,
            event_type="run_completed",
            status=status,
            payload={
                "reason": reason,
                "requested_count": 1,
                "completed_count": completed_count,
                "skipped_count": skipped_count,
                "failed_count": failed_count,
            },
        ),
    )
    write_ledger(context, result)
    return result
