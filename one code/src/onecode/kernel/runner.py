import time
from pathlib import Path
from typing import Any

from onecode.kernel.action_intent import ActionIntent
from onecode.kernel.checkpoint import write_checkpoint, write_ledger
from onecode.kernel.context import create_context
from onecode.kernel.hexagram import COMPLETE, IchingKernel, IchingTransition
from onecode.kernel.logos_gate import LogosGate
from onecode.kernel.path_guard import PathGuard
from onecode.kernel.permission_matrix import Decision
from onecode.kernel.resumption import ReadyAsset


RULE_DRIVEN_RESULT_FIELDS = {
    "assets",
    "completed_count",
    "decision",
    "failed_count",
    "iching_profile",
    "iching_status_code",
    "iching_transition_action",
    "iching_transition_reason",
    "intent_type",
    "ledger_path",
    "manifest_path",
    "partial",
    "payload",
    "reason",
    "requested_count",
    "resumed",
    "resumed_from",
    "run_id",
    "sha256",
    "skipped_count",
    "state",
    "status",
}


def safe_run_metadata(run_metadata: dict[str, Any] | None) -> dict[str, Any]:
    if run_metadata is None:
        return {}
    return {
        key: value
        for key, value in run_metadata.items()
        if key not in RULE_DRIVEN_RESULT_FIELDS
    }


def build_intent(
    intent_type: str,
    write_path: str | None,
    write_content: str | None,
    command: str | None,
) -> ActionIntent:
    if write_path is not None or write_content is not None:
        if write_path is None or write_content is None:
            return ActionIntent.invalid_intent("write_text")
        return ActionIntent.write_text(write_path or "", write_content or "")
    if intent_type == "bash_execution":
        return ActionIntent.bash_execution(command or "")
    if intent_type == "execute_pytest":
        return ActionIntent.execute_pytest(command or "tests")
    if intent_type == "noop":
        return ActionIntent.noop()
    return ActionIntent.invalid_intent(intent_type)


def parse_write_text(value: str) -> tuple[str, str]:
    path, separator, content = value.partition("=")
    if separator == "" or path == "":
        raise ValueError("--write-text must use PATH=CONTENT with a non-empty path")
    return path, content


def build_intents(
    intent_type: str,
    write_path: str | None,
    write_content: str | None,
    command: str | None,
    write_texts: list[str] | None,
) -> list[ActionIntent]:
    if write_texts is not None:
        return [ActionIntent.write_text(*parse_write_text(write_text)) for write_text in write_texts]
    return [build_intent(intent_type, write_path, write_content, command)]


def ready_asset_for_intent(context: Any, intent: ActionIntent) -> ReadyAsset | None:
    if intent.action_type.value != "write_text":
        return None
    if context.resume_state is None:
        return None
    return context.resume_state.ready_assets.get(intent.payload["path"])


def should_skip_ready_asset(ready_asset: ReadyAsset | None, preflight: Any) -> bool:
    if ready_asset is None:
        return False
    if preflight.decision != Decision.ALLOWED:
        return False
    status_code = IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.DUI)
    return IchingKernel.should_skip(status_code)


def iching_transition_for_result(gate_result: dict[str, Any]) -> IchingTransition:
    status_code = IchingKernel.classify_outcome(gate_result["status"], gate_result["reason"])
    return IchingKernel.transition(status_code)


def iching_status_for_result(gate_result: dict[str, Any]) -> int:
    return iching_transition_for_result(gate_result).status_code


def run_intent(
    task: str,
    context: Any,
    gate: LogosGate,
    intent: ActionIntent,
    simulated_action_seconds: float,
) -> tuple[dict[str, Any], Any]:
    preflight = gate.preflight(context, intent)
    ready_asset = ready_asset_for_intent(context, intent)

    if preflight.decision == Decision.DENIED:
        return {
            "status": "denied",
            "partial": False,
            "reason": preflight.reason,
            "payload": preflight.to_dict(),
        }, preflight
    if preflight.decision == Decision.HALTED:
        return {
            "status": "halted",
            "partial": True,
            "reason": preflight.reason,
            "payload": preflight.to_dict(),
        }, preflight
    if should_skip_ready_asset(ready_asset, preflight):
        return {
            "status": "skipped",
            "partial": False,
            "reason": "resumed_asset_ready",
            "payload": {
                "path": ready_asset.path,
                "sha256": ready_asset.sha256,
                "source_run_id": ready_asset.source_run_id,
                "source_turn_index": ready_asset.source_turn_index,
            },
        }, preflight

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

    return gate.run_bounded_action(action), preflight


def asset_entry(
    index: int,
    gate_result: dict[str, Any],
    preflight_decision: Any,
    intent_type: str,
    iching_transition: IchingTransition,
    iching_profile: dict[str, Any],
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry = {
        "index": index,
        "status": gate_result["status"],
        "partial": gate_result["partial"],
        "reason": gate_result["reason"],
        "decision": preflight_decision.decision.value,
        "intent_type": intent_type,
        "payload": payload if payload is not None else gate_result["payload"],
        "raw_payload": gate_result["payload"],
        "resumed": gate_result["status"] == "skipped",
        "iching_status_code": iching_transition.status_code,
        "iching_transition_action": iching_transition.action,
        "iching_transition_reason": iching_transition.reason,
        "iching_profile": iching_profile,
    }
    if "sha256" in gate_result["payload"]:
        entry["sha256"] = gate_result["payload"]["sha256"]
    return entry


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
    write_texts: list[str] | None = None,
    run_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = create_context(
        workspace_root=workspace,
        http_timeout_seconds=http_timeout_seconds,
        run_id=run_id,
        resume_from_run_id=resume_from_run_id,
    )
    gate = LogosGate(http_timeout_seconds=http_timeout_seconds)
    intents = build_intents(intent_type, write_path, write_content, command, write_texts)
    assets = []

    for index, intent in enumerate(intents, start=1):
        gate_result, preflight = run_intent(task, context, gate, intent, simulated_action_seconds)
        iching_transition = iching_transition_for_result(gate_result)
        iching_profile = IchingKernel.cross_cutting_profile(iching_transition.status_code)
        checkpoint_payload = gate_result["payload"]
        entry_payload = checkpoint_payload
        if intent.action_type.value == "write_text" and "sha256" in checkpoint_payload:
            entry_payload = {**checkpoint_payload, "path": intent.payload["path"]}

        write_checkpoint(
            context=context,
            payload=checkpoint_payload,
            next_state=COMPLETE,
            status=gate_result["status"],
            partial=gate_result["partial"],
            reason=gate_result["reason"],
            intent_type=intent.action_type.value,
            decision=preflight.decision.value,
            iching_status_code=iching_transition.status_code,
            iching_transition_action=iching_transition.action,
            iching_transition_reason=iching_transition.reason,
            iching_profile=iching_profile,
        )
        assets.append(
            asset_entry(
                index,
                gate_result,
                preflight,
                intent.action_type.value,
                iching_transition,
                iching_profile,
                entry_payload,
            )
        )
        if IchingKernel.dispatch_decision(iching_transition) == "stop":
            break

    ledger_path = context.evidence_root / "ledger.json"
    last_asset = assets[-1]
    completed_count = sum(asset["status"] == "completed" for asset in assets)
    skipped_count = sum(asset["status"] == "skipped" for asset in assets)
    failed_count = sum(asset["status"] in {"denied", "halted"} for asset in assets)
    aggregate_success = write_texts is not None and failed_count == 0
    result_payload = last_asset["payload"] if write_texts is not None else last_asset["raw_payload"]
    result = {
        "run_id": context.run_id,
        "status": "completed" if aggregate_success else last_asset["status"],
        "state": str(COMPLETE),
        "manifest_path": str(context.manifest_path),
        "ledger_path": str(ledger_path),
        "partial": last_asset["partial"],
        "reason": None if aggregate_success else last_asset["reason"],
        "decision": last_asset["decision"],
        "intent_type": last_asset["intent_type"],
        "payload": result_payload,
        "resumed_from": resume_from_run_id,
        "resumed": last_asset["resumed"],
        "assets": assets,
        "requested_count": len(intents),
        "completed_count": completed_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
        "iching_status_code": last_asset["iching_status_code"],
        "iching_transition_action": last_asset["iching_transition_action"],
        "iching_transition_reason": last_asset["iching_transition_reason"],
        "iching_profile": last_asset["iching_profile"],
    }
    if "sha256" in last_asset:
        result["sha256"] = last_asset["sha256"]
    result = result | safe_run_metadata(run_metadata)
    write_ledger(context, result)
    return result
