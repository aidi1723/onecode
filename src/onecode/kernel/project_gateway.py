from onecode.kernel.gateway_engine import (
    ALLOWED_EVIDENCE_STATES,
    ALLOWED_INTENT_TYPES,
    ALLOWED_PATH_SCOPES,
    ALLOWED_SANDBOX_STATES,
    require_member,
    require_string,
)


FACT_FIELDS = ("intent_type", "path_scope", "sandbox_state", "evidence_state")
FACT_DOMAINS = {
    "intent_type": ALLOWED_INTENT_TYPES,
    "path_scope": ALLOWED_PATH_SCOPES,
    "sandbox_state": ALLOWED_SANDBOX_STATES,
    "evidence_state": ALLOWED_EVIDENCE_STATES,
}


def project_gateway(status_code: int, facts: dict[str, str]) -> str:
    """Map one hexagram code and closed facts to one gateway action.

    Symbolic kernel dynamics stay outside this function. Unmapped pairs deny.
    """
    normalized = _status_code(status_code)
    checked = _facts(facts)
    intent_type = checked["intent_type"]
    path_scope = checked["path_scope"]
    if normalized == 0b100001:
        return "SOVEREIGNTY_HALT"
    if normalized == 0b000000:
        return "DENY_AND_LEDGER"
    if normalized == 0b111111 and intent_type == "write_text" and path_scope == "workspace_relative":
        return "ALLOW_ATOMIC_WRITE"
    if normalized == 0b111111 and intent_type == "patch_text" and path_scope == "workspace_relative":
        return "ALLOW_PATCH_WITH_SHA"
    if normalized == 0b010010 and intent_type == "execute_pytest":
        return "RUN_VERIFIER_IN_SANDBOX"
    return "DENY_AND_LEDGER"


def gateway_disagreement(state: object, facts: object, action: object) -> str | None:
    """Re-read one hexagram through the gateway. Missing facts do not authorize."""
    if not isinstance(state, str) or len(state) != 6 or any(bit not in "01" for bit in state):
        return "gateway_unread"
    if not isinstance(facts, dict):
        return "gateway_unread"
    try:
        projected = project_gateway(int(state, 2), facts)
    except (TypeError, ValueError):
        return "gateway_unread"
    if projected != action:
        return "gateway_mismatch"
    return None


def _status_code(status_code: int) -> int:
    if isinstance(status_code, bool) or not isinstance(status_code, int) or not 0 <= status_code <= 63:
        raise ValueError("status_code must be an int in 0..63")
    return status_code


def _facts(facts: dict[str, str]) -> dict[str, str]:
    if not isinstance(facts, dict):
        raise ValueError("facts must be an object")
    unknown = sorted(set(facts) - set(FACT_FIELDS))
    if unknown:
        raise ValueError(f"unknown fact fields: {', '.join(unknown)}")
    missing = sorted(set(FACT_FIELDS) - set(facts))
    if missing:
        raise ValueError(f"missing fact fields: {', '.join(missing)}")
    checked: dict[str, str] = {}
    for field in FACT_FIELDS:
        value = require_string(facts[field], field)
        require_member(value, FACT_DOMAINS[field], field)
        checked[field] = value
    return checked
