from typing import Any, Protocol

from onecode.kernel.gateway_engine import ALLOWED_STATES, require_string


POLICY_FIELDS = {"state", "preferred_text", "forbidden_text"}
TOKEN_ID_POLICY_FIELDS = {"state", "preferred_token_ids", "forbidden_token_ids"}

ALLOW_TEXT = ["ALLOW_ATOMIC_WRITE", "ALLOW_PATCH_WITH_SHA"]
DANGER_FORBIDDEN_TEXT = ALLOW_TEXT + ["safe_workspace_write", "safe_workspace_patch"]
SAFE_TEXT = ALLOW_TEXT + ["workspace_relative", "evidence_state"]
DENY_TEXT = ["DENY_AND_LEDGER", "undefined_action_intent", "clarify"]
HALT_TEXT = ["SOVEREIGNTY_HALT", "dangerous_host_command", "hard_halt"]
VERIFIER_TEXT = ["RUN_VERIFIER_IN_SANDBOX", "sandbox_required", "verifier_requires_sandbox"]


class TokenizerProtocol(Protocol):
    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        ...


def validate_state_token_policy(policy: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(policy, dict):
        raise ValueError("policy must be an object")
    unknown_fields = sorted(set(policy) - POLICY_FIELDS)
    missing_fields = sorted(POLICY_FIELDS - set(policy))
    if unknown_fields:
        raise ValueError(f"unknown policy fields: {', '.join(unknown_fields)}")
    if missing_fields:
        raise ValueError(f"missing policy fields: {', '.join(missing_fields)}")
    state = require_string(policy["state"], "state")
    if state not in ALLOWED_STATES:
        raise ValueError(f"unknown state: {state}")
    for field in ("preferred_text", "forbidden_text"):
        values = policy[field]
        if not isinstance(values, list) or not all(isinstance(value, str) and value for value in values):
            raise ValueError(f"{field} must be a non-empty string list")
    return {
        "state": state,
        "preferred_text": dedupe_text(policy["preferred_text"]),
        "forbidden_text": dedupe_text(policy["forbidden_text"]),
    }


def validate_state_token_id_policy(policy: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(policy, dict):
        raise ValueError("token id policy must be an object")
    unknown_fields = sorted(set(policy) - TOKEN_ID_POLICY_FIELDS)
    missing_fields = sorted(TOKEN_ID_POLICY_FIELDS - set(policy))
    if unknown_fields:
        raise ValueError(f"unknown token id policy fields: {', '.join(unknown_fields)}")
    if missing_fields:
        raise ValueError(f"missing token id policy fields: {', '.join(missing_fields)}")
    state = require_string(policy["state"], "state")
    if state not in ALLOWED_STATES:
        raise ValueError(f"unknown state: {state}")
    for field in ("preferred_token_ids", "forbidden_token_ids"):
        values = policy[field]
        if not isinstance(values, list) or not all(isinstance(value, int) for value in values):
            raise ValueError(f"{field} must be an integer list")
    return {
        "state": state,
        "preferred_token_ids": dedupe_ints(policy["preferred_token_ids"]),
        "forbidden_token_ids": dedupe_ints(policy["forbidden_token_ids"]),
    }


def dedupe_text(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def dedupe_ints(values: list[int]) -> list[int]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def encode_fragments(tokenizer: TokenizerProtocol, fragments: list[str]) -> list[int]:
    token_ids: list[int] = []
    for fragment in fragments:
        encoded = tokenizer.encode(fragment, add_special_tokens=False)
        if not isinstance(encoded, list) or not all(isinstance(token_id, int) for token_id in encoded):
            raise ValueError("tokenizer.encode must return a list of integers")
        token_ids.extend(encoded)
    return dedupe_ints(token_ids)


def state_token_policy(state: str) -> dict[str, Any]:
    require_string(state, "state")
    if state not in ALLOWED_STATES:
        raise ValueError(f"unknown state: {state}")
    if state == "111111":
        return validate_state_token_policy(
            {
                "state": state,
                "preferred_text": SAFE_TEXT,
                "forbidden_text": ["rm -rf /", "outside_workspace"],
            }
        )
    if state == "010010":
        return validate_state_token_policy(
            {
                "state": state,
                "preferred_text": VERIFIER_TEXT,
                "forbidden_text": ALLOW_TEXT,
            }
        )
    if state == "100001":
        return validate_state_token_policy(
            {
                "state": state,
                "preferred_text": HALT_TEXT,
                "forbidden_text": DANGER_FORBIDDEN_TEXT,
            }
        )
    if state == "000000":
        return validate_state_token_policy(
            {
                "state": state,
                "preferred_text": DENY_TEXT,
                "forbidden_text": ALLOW_TEXT,
            }
        )
    return validate_state_token_policy(
        {
            "state": state,
            "preferred_text": ["DENY_AND_LEDGER", "safe_fallback"],
            "forbidden_text": ALLOW_TEXT,
        }
    )


def text_policy_to_token_id_policy(policy: dict[str, Any], tokenizer: TokenizerProtocol) -> dict[str, Any]:
    text_policy = validate_state_token_policy(policy)
    return validate_state_token_id_policy(
        {
            "state": text_policy["state"],
            "preferred_token_ids": encode_fragments(tokenizer, text_policy["preferred_text"]),
            "forbidden_token_ids": encode_fragments(tokenizer, text_policy["forbidden_text"]),
        }
    )


def state_token_id_policy(state: str, tokenizer: TokenizerProtocol) -> dict[str, Any]:
    return text_policy_to_token_id_policy(state_token_policy(state), tokenizer)


def rich_basis_hints(basis: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    yin_yang = basis.get("yin_yang")
    if isinstance(yin_yang, dict):
        for field in ("balance", "pressure"):
            value = yin_yang.get(field)
            if isinstance(value, str) and value:
                hints.append(value)
    elements = basis.get("elements")
    if isinstance(elements, dict):
        for field in ("relation", "modulation"):
            value = elements.get(field)
            if isinstance(value, str) and value:
                hints.append(value)
    return hints


def token_policy_for_basis(basis: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(basis, dict):
        raise ValueError("basis must be an object")
    state = require_string(basis.get("state"), "basis.state")
    state_label = require_string(basis.get("state_label"), "basis.state_label")
    policy = state_token_policy(state)
    preferred = list(policy["preferred_text"])
    forbidden = list(policy["forbidden_text"])
    if state_label == "kun_clarify_boundary":
        preferred.extend(["clarify", "请说明", "目标文件", "验证方式"])
        forbidden.extend(ALLOW_TEXT)
    elif state_label == "chat_smalltalk":
        preferred.extend(["chat_reply", "你好", "简单回复"])
        forbidden.extend(ALLOW_TEXT)
    elif state_label == "qian_safe_patch":
        preferred.extend(["ALLOW_PATCH_WITH_SHA", "safe_workspace_patch", "VERIFY_SHA256"])
    elif state_label == "qian_safe_write":
        preferred.extend(["ALLOW_ATOMIC_WRITE", "safe_workspace_write"])
    elif state_label == "kan_sandbox_verifier":
        preferred.extend(VERIFIER_TEXT)
        forbidden.extend(ALLOW_TEXT)
    elif state_label == "gen_sovereignty_halt":
        preferred.extend(HALT_TEXT)
        forbidden.extend(DANGER_FORBIDDEN_TEXT)
    elif state_label == "kun_deny_ledger":
        preferred.extend(["DENY_AND_LEDGER", "schema_out_of_contract"])
        forbidden.extend(ALLOW_TEXT)
    forbidden_set = set(forbidden)
    preferred.extend(hint for hint in rich_basis_hints(basis) if hint not in forbidden_set)
    return validate_state_token_policy(
        {
            "state": state,
            "preferred_text": preferred,
            "forbidden_text": forbidden,
        }
    )


def token_id_policy_for_basis(basis: dict[str, Any], tokenizer: TokenizerProtocol) -> dict[str, Any]:
    return text_policy_to_token_id_policy(token_policy_for_basis(basis), tokenizer)


def apply_token_id_policy_to_logits(
    logits: list[float],
    policy: dict[str, Any],
    *,
    preferred_bias: float = 2.0,
) -> list[float]:
    if not isinstance(logits, list) or not all(isinstance(value, int | float) for value in logits):
        raise ValueError("logits must be a numeric list")
    if not isinstance(preferred_bias, int | float):
        raise ValueError("preferred_bias must be numeric")
    token_policy = validate_state_token_id_policy(policy)
    controlled = [float(value) for value in logits]
    for token_id in token_policy["preferred_token_ids"]:
        if 0 <= token_id < len(controlled):
            controlled[token_id] += float(preferred_bias)
    for token_id in token_policy["forbidden_token_ids"]:
        if 0 <= token_id < len(controlled):
            controlled[token_id] = float("-inf")
    return controlled


class YiZiJueLogitsProcessor:
    def __init__(self, policy: dict[str, Any], preferred_bias: float = 2.0) -> None:
        if not isinstance(preferred_bias, int | float):
            raise ValueError("preferred_bias must be numeric")
        self.policy = validate_state_token_id_policy(policy)
        self.preferred_bias = float(preferred_bias)

    def __call__(self, input_ids: Any, scores: Any) -> Any:
        vocab_size = infer_scores_vocab_size(scores)
        for token_id in self.policy["preferred_token_ids"]:
            if 0 <= token_id < vocab_size:
                scores[:, token_id] = [value + self.preferred_bias for value in scores[:, token_id]]
        for token_id in self.policy["forbidden_token_ids"]:
            if 0 <= token_id < vocab_size:
                scores[:, token_id] = float("-inf")
        return scores


def infer_scores_vocab_size(scores: Any) -> int:
    shape = getattr(scores, "shape", None)
    if isinstance(shape, tuple) and len(shape) >= 2 and isinstance(shape[-1], int):
        return shape[-1]
    rows = getattr(scores, "rows", None)
    if isinstance(rows, list) and rows and isinstance(rows[0], list):
        return len(rows[0])
    raise ValueError("scores must expose shape[-1] or rows for vocab size inference")
