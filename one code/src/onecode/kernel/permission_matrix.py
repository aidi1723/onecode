from dataclasses import dataclass
from enum import StrEnum

from onecode.kernel.action_intent import ActionIntent, ActionType
from onecode.kernel.hexagram import BUILD_ENTRY, HexagramStatusCode


class Decision(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"
    HALTED = "halted"


@dataclass(frozen=True)
class PermissionDecision:
    decision: Decision
    reason: str | None
    intent_type: str
    state: str
    evidence_required: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "intent_type": self.intent_type,
            "state": self.state,
            "evidence_required": self.evidence_required,
        }


class PermissionMatrix:
    def evaluate(self, state: HexagramStatusCode, intent: ActionIntent) -> PermissionDecision:
        if state == BUILD_ENTRY and intent.action_type in {ActionType.NOOP, ActionType.WRITE_TEXT}:
            evidence = ["path", "sha256"] if intent.action_type == ActionType.WRITE_TEXT else []
            return PermissionDecision(
                decision=Decision.ALLOWED,
                reason=None,
                intent_type=intent.action_type.value,
                state=str(state),
                evidence_required=evidence,
            )

        if state == BUILD_ENTRY and intent.action_type in {ActionType.EXECUTE_PYTEST, ActionType.BASH_EXECUTION}:
            return PermissionDecision(
                decision=Decision.DENIED,
                reason="permission_denied",
                intent_type=intent.action_type.value,
                state=str(state),
                evidence_required=[],
            )

        return PermissionDecision(
            decision=Decision.HALTED,
            reason="invalid_intent",
            intent_type=intent.action_type.value,
            state=str(state),
            evidence_required=[],
        )
