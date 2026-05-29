from __future__ import annotations

from typing import Any

from .gateway_core import build_execution_stack, normalize_intent
from .loader import lookup_entry
from .macro_chain import compile_macro_chain, macro_chain_to_dict


def resolve_execution_plan(user_message: str, dictionary: dict[str, Any]) -> dict[str, Any]:
    intent = normalize_intent(user_message, dictionary)
    macro_chain = compile_macro_chain(user_message)
    stack = build_execution_stack(intent.codes)
    active_code = stack[-1]
    active_entry = lookup_entry(dictionary, active_code)
    raw = active_entry.raw

    return {
        "codes": intent.codes,
        "execution_stack": stack,
        "active_code": active_code,
        "confidence": intent.confidence,
        "reason": intent.reason,
        "definition": active_entry.definition,
        "routing_target": active_entry.routing_target,
        "temperature": active_entry.model_policy["temperature"],
        "tool_policy": active_entry.tool_policy,
        "allowed_actions": raw["allowed_actions"],
        "forbidden_actions": raw["forbidden_actions"],
        "verification_required": raw["verification"]["required"],
        "verification": raw["verification"],
        "fallback": active_entry.fallback,
        "macro_chain": macro_chain_to_dict(macro_chain),
    }
