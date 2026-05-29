from __future__ import annotations

from math import log2
from typing import Any


TRIGRAMS = {
    0: ("KUN", "earth"),
    1: ("ZHEN", "wood"),
    2: ("KAN", "water"),
    3: ("DUI", "metal"),
    4: ("GEN", "earth"),
    5: ("XUN", "wood"),
    6: ("LI", "fire"),
    7: ("QIAN", "metal"),
}

GENERATES = {
    "water": "wood",
    "wood": "fire",
    "fire": "earth",
    "earth": "metal",
    "metal": "water",
}

CONTROLS = {
    "water": "fire",
    "fire": "metal",
    "metal": "wood",
    "wood": "earth",
    "earth": "water",
}

STOP_ACTIONS = {"halt", "checkpoint", "discover"}
ROLLBACK_STATUS = 17


def build_gateway_rule(source: dict[str, Any] | None = None) -> dict[str, Any]:
    source = source or {}
    status_code = _status_code_from_source(source)
    outer = (status_code >> 3) & 0b111
    inner = status_code & 0b111
    action, reason = _transition(status_code, source)
    dispatch = "stop" if action in STOP_ACTIONS else "continue"
    return _envelope(
        status_code=status_code,
        action=action,
        reason=reason,
        dispatch_decision=dispatch,
        evidence_required=source.get("evidence_required") if isinstance(source.get("evidence_required"), list) else [],
        evidence_collected=source.get("evidence_collected") if isinstance(source.get("evidence_collected"), dict) else {},
        source=source,
        outer=outer,
        inner=inner,
    )


def aggregate_gateway_statuses(status_codes: list[int], entropy_threshold: float = 0.5) -> dict[str, Any]:
    if not status_codes:
        rule = build_gateway_rule({"event": "policy_gap"})
        return {
            "decision": "discover_empty_statuses",
            "gateway_status_code": rule["gateway_status_code"],
            "gateway_status_binary": rule["gateway_status_binary"],
            "entropy": 0.0,
            "polarity_index": rule["polarity_index"],
            "reason": rule["transition_reason"],
            "dispatch_decision": rule["dispatch_decision"],
        }

    entropy = _global_entropy(status_codes)
    average_polarity = sum(_polarity(code) for code in status_codes) / len(status_codes)
    if entropy < entropy_threshold and average_polarity < 0:
        rule = build_gateway_rule({"status_code": ROLLBACK_STATUS, "reason": "entropy_negative_polarity_rollback"})
        decision = "rollback_negative_polarity"
    elif entropy < entropy_threshold and average_polarity > 0:
        rule = build_gateway_rule({"status_code": max(status_codes), "reason": "accept_positive_polarity"})
        decision = "accept_positive_polarity"
    else:
        rule = build_gateway_rule({"status_code": _collapse_statuses(status_codes), "reason": "accept_entropy_balanced"})
        decision = "accept_entropy_balanced"
    return {
        "decision": decision,
        "gateway_status_code": rule["gateway_status_code"],
        "gateway_status_binary": rule["gateway_status_binary"],
        "entropy": entropy,
        "polarity_index": average_polarity,
        "reason": rule["transition_reason"],
        "dispatch_decision": rule["dispatch_decision"],
    }


def aggregate_gateway_rule_envelope(status_codes: list[int], source: str = "gateway_state") -> dict[str, Any]:
    summary = aggregate_gateway_statuses(status_codes)
    rule = build_gateway_rule(
        {
            "status_code": int(summary["gateway_status_code"]),
            "reason": str(summary["reason"]),
            "source": source,
        }
    )
    return {
        **rule,
        "source": source,
        "aggregation_decision": summary["decision"],
        "global_entropy": summary["entropy"],
        "global_polarity_index": summary["polarity_index"],
        "aggregation_reason": summary["reason"],
    }


def _status_code_from_source(source: dict[str, Any]) -> int:
    if isinstance(source.get("status_code"), int):
        return int(source["status_code"]) & 0b111111
    event = str(source.get("event") or "")
    if event in {"sovereignty_breach", "preflight_breach", "tool_violation"}:
        return 48
    if event in {"upstream_timeout", "http_timeout", "stream_timeout"}:
        return 17
    if event in {"policy_gap", "unknown", "unmapped"}:
        return 0
    bits = [
        _bit(source, "sovereignty", True),
        _bit(source, "upstream", True),
        _bit(source, "policy", True),
        _bit(source, "artifact", True),
        _bit(source, "execution", True),
        _bit(source, "time", True),
    ]
    status = 0
    for bit in bits:
        status = (status << 1) | bit
    return status


def _bit(source: dict[str, Any], key: str, default: bool) -> int:
    value = source.get(key, default)
    return 1 if bool(value) else 0


def _transition(status_code: int, source: dict[str, Any]) -> tuple[str, str]:
    explicit_reason = source.get("reason")
    if explicit_reason == "entropy_negative_polarity_rollback":
        return "checkpoint", "entropy_negative_polarity_rollback"
    if explicit_reason == "accept_positive_polarity":
        return "cooldown", "accept_positive_polarity"
    if status_code == 0:
        return "discover", "rule_gap_discovery"

    outer = (status_code >> 3) & 0b111
    inner = status_code & 0b111
    if outer == 6:
        return "halt", "sovereignty_fire_boundary"
    if status_code == 17:
        return "checkpoint", "network_water_preserves_resume_seed"

    polarity = _polarity(status_code)
    if polarity >= 1.0:
        return "cooldown", "yang_overload_cooldown"
    if polarity <= -1.0:
        return "activate", "yin_stagnation_activate"

    relation = _element_relation(outer, inner)
    if relation == "generates":
        return "accelerate", "element_generation_accelerates"
    if relation == "controls":
        return "moderate", "element_control_moderates"
    return "continue", "balanced_continue"


def _envelope(
    *,
    status_code: int,
    action: str,
    reason: str,
    dispatch_decision: str,
    evidence_required: list[Any],
    evidence_collected: dict[str, Any],
    source: dict[str, Any],
    outer: int,
    inner: int,
) -> dict[str, Any]:
    outer_name, outer_element = TRIGRAMS[outer]
    inner_name, inner_element = TRIGRAMS[inner]
    binary = format(status_code, "06b")
    return {
        "gateway_status_code": status_code,
        "gateway_status_binary": binary,
        "outer_trigram": binary[:3],
        "inner_trigram": binary[3:],
        "outer_trigram_name": outer_name,
        "inner_trigram_name": inner_name,
        "outer_plane": "environment",
        "inner_plane": "asset",
        "polarity_index": _polarity(status_code),
        "four_symbols": [binary[0:2], binary[2:4], binary[4:6]],
        "element_relation": _element_relation(outer, inner),
        "outer_element": outer_element,
        "inner_element": inner_element,
        "transition_action": action,
        "transition_reason": reason,
        "dispatch_decision": dispatch_decision,
        "evidence_required": evidence_required,
        "evidence_collected": evidence_collected,
        "source": str(source.get("source") or "gateway_rule_adapter"),
    }


def _polarity(status_code: int) -> float:
    return ((int(status_code) & 0b111111).bit_count() - 3) / 3


def _element_relation(outer: int, inner: int) -> str:
    outer_element = TRIGRAMS[outer][1]
    inner_element = TRIGRAMS[inner][1]
    if outer_element == inner_element:
        return "same"
    if GENERATES.get(outer_element) == inner_element:
        return "generates"
    if CONTROLS.get(outer_element) == inner_element:
        return "controls"
    return "neutral"


def _global_entropy(status_codes: list[int]) -> float:
    total_bits = len(status_codes) * 6
    ones = sum((int(code) & 0b111111).bit_count() for code in status_codes)
    p1 = ones / total_bits
    p0 = 1.0 - p1
    entropy = -sum(p * log2(p) for p in (p0, p1) if p > 0)
    return entropy + 0.0


def _collapse_statuses(status_codes: list[int]) -> int:
    status = 0
    for code in status_codes:
        status |= int(code) & 0b111111
    return status
