"""Core training data structures, constants, and validation functions.

This module provides the fundamental components for the training data system:
- TrainingSample dataclass for representing training examples
- Constants for model configuration and validation
- Validation functions for training samples and YiZiJue-LM samples
- State basis enrichment with I Ching kernel profiles
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from onecode.kernel.gateway_engine import (
    ALLOWED_ACTIONS,
    ALLOWED_EVIDENCE_STATES,
    ALLOWED_INTENT_TYPES,
    ALLOWED_PATH_SCOPES,
    ALLOWED_SANDBOX_STATES,
    ALLOWED_STATES,
    adjudicate_gateway_prediction,
    assistant_payload,
    require_member,
    require_string,
    validate_assistant_content,
)
from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.iching_encoding import ACTIVE_RULE_SCHEMA, convert_status, normalize_rule_schema


MODEL_BASE = "Qwen2.5-Coder-1.5B-Instruct"
MODEL_REPOSITORY = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
SYSTEM_PROMPT = "You translate user intent into strict YiZiJue safety gateway JSON. Output JSON only."
YIZIJUE_LM_SYSTEM_PROMPT = (
    "You are YiZiJue-LM. Translate natural language into simple replies or strict OneCode/YiZiJue JSON. "
    "Output JSON only when an action is needed."
)
YIZIJUE_LM_OUTPUT_TYPES = {"chat_reply", "clarify", "action_json"}
YIZIJUE_LM_REQUIRED_BASIS_FIELDS = {"projection", "state", "state_label", "transition", "rule"}
YIZIJUE_LM_OPTIONAL_BASIS_FIELDS = {"yin_yang", "trigrams", "elements"}
YIZIJUE_LM_BASIS_FIELDS = YIZIJUE_LM_REQUIRED_BASIS_FIELDS | YIZIJUE_LM_OPTIONAL_BASIS_FIELDS

REQUIRED_ACTION_COVERAGE = {
    "ALLOW_ATOMIC_WRITE",
    "ALLOW_PATCH_WITH_SHA",
    "RUN_VERIFIER_IN_SANDBOX",
    "DENY_AND_LEDGER",
    "SOVEREIGNTY_HALT",
}
REQUIRED_DIMENSION_COVERAGE = {
    "intent_type": ALLOWED_INTENT_TYPES,
    "path_scope": ALLOWED_PATH_SCOPES,
    "sandbox_state": {"required", "not_required", "missing"},
    "evidence_state": {"required", "failed"},
    "action": REQUIRED_ACTION_COVERAGE,
    "yizijue_state": {"000000", "010010", "100001", "111111"},
}


@dataclass(frozen=True)
class TrainingSample:
    id: str
    user: str
    facts: dict[str, str]
    yizijue_state: str
    action: str
    reason: str
    model_base: str = MODEL_BASE
    rule_schema: str = ACTIVE_RULE_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "model_base": self.model_base,
            "rule_schema": normalize_rule_schema(self.rule_schema),
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self.user},
                {
                    "role": "assistant",
                    "content": assistant_payload(
                        facts=self.facts,
                        yizijue_state=self.yizijue_state,
                        action=self.action,
                        reason=self.reason,
                    ),
                },
            ],
        }


def build_adjudicated_feedback_samples(
    gold_samples: list[TrainingSample],
    predictions: dict[str, str],
    prefix: str = "adjudicated-feedback",
) -> list[TrainingSample]:
    samples: list[TrainingSample] = []
    for sample in gold_samples:
        prediction = predictions.get(sample.id)
        if prediction is None:
            continue
        payload = adjudicate_gateway_prediction(sample.user, prediction)
        feedback_sample = TrainingSample(
            id=f"{prefix}-{sample.id}",
            user=sample.user,
            facts=dict(payload["facts"]),
            yizijue_state=str(payload["yizijue_state"]),
            action=str(payload["action"]),
            reason=str(payload["reason"]),
            model_base=sample.model_base,
        )
        validate_training_sample(feedback_sample.to_dict())
        samples.append(feedback_sample)
    return samples


def validate_training_sample(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("training sample must be an object")
    allowed_fields = {"id", "messages", "model_base", "rule_schema"}
    if set(data) - allowed_fields or not {"id", "messages", "model_base"}.issubset(data):
        raise ValueError("training sample fields must be id, messages, model_base, and optional rule_schema")
    rule_schema = normalize_rule_schema(data.get("rule_schema"))
    require_string(data["id"], "id")
    if data["model_base"] != MODEL_BASE:
        raise ValueError(f"model_base must be {MODEL_BASE}")

    messages = data.get("messages")
    if not isinstance(messages, list) or len(messages) != 3:
        raise ValueError("messages must contain system, user, assistant")

    expected_roles = ["system", "user", "assistant"]
    for index, role in enumerate(expected_roles):
        message = messages[index]
        if not isinstance(message, dict) or sorted(message) != ["content", "role"]:
            raise ValueError(f"message {index + 1} must contain role and content")
        if message["role"] != role:
            raise ValueError(f"message {index + 1} role must be {role}")
        require_string(message["content"], f"message {index + 1} content")
    if messages[0]["content"] != SYSTEM_PROMPT:
        raise ValueError("system prompt does not match training contract")

    validate_assistant_content(messages[2]["content"])
    return {**data, "rule_schema": rule_schema}


def write_jsonl(path: Path, samples: list[TrainingSample]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for sample in samples:
            data = validate_training_sample(sample.to_dict())
            handle.write(json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n")
    return {"status": "completed", "path": str(path), "sample_count": len(samples)}


def validate_yizijue_lm_sample(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("YiZiJue-LM sample must be an object")
    allowed_fields = {"action", "id", "input", "output_type", "reply", "rule_schema"}
    required_fields = {"action", "id", "input", "output_type", "reply"}
    if set(data) - allowed_fields or not required_fields.issubset(data):
        raise ValueError("YiZiJue-LM sample fields must be action, id, input, output_type, reply, and optional rule_schema")
    rule_schema = normalize_rule_schema(data.get("rule_schema"))
    require_string(data["id"], "id")
    require_string(data["input"], "input")
    output_type = require_string(data["output_type"], "output_type")
    if output_type not in YIZIJUE_LM_OUTPUT_TYPES:
        raise ValueError(f"unknown output_type: {output_type}")
    if not isinstance(data["reply"], str):
        raise ValueError("reply must be a string")
    action = data["action"]
    if output_type == "action_json":
        if not isinstance(action, dict):
            raise ValueError("action_json samples require action object")
        validate_assistant_content(json.dumps(action, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        if data["reply"] != "":
            raise ValueError("action_json reply must be empty")
    else:
        if action is not None:
            raise ValueError(f"{output_type} samples require action to be null")
        require_string(data["reply"], "reply")
    return {**data, "rule_schema": rule_schema}


def validate_yizijue_lm_state_sample(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("YiZiJue-LM state sample must be an object")
    allowed_fields = {"action", "basis", "id", "input", "output_type", "reply", "rule_schema"}
    required_fields = {"action", "basis", "id", "input", "output_type", "reply"}
    if set(data) - allowed_fields or not required_fields.issubset(data):
        raise ValueError(
            "YiZiJue-LM state sample fields must be action, basis, id, input, output_type, reply, and optional rule_schema"
        )
    base = validate_yizijue_lm_sample(
        {
            "id": data["id"],
            "input": data["input"],
            "output_type": data["output_type"],
            "reply": data["reply"],
            "action": data["action"],
            **({"rule_schema": data["rule_schema"]} if "rule_schema" in data else {}),
        }
    )
    basis = data["basis"]
    if not isinstance(basis, dict):
        raise ValueError("basis must be an object")
    unknown_fields = sorted(set(basis) - YIZIJUE_LM_BASIS_FIELDS)
    missing_fields = sorted(YIZIJUE_LM_REQUIRED_BASIS_FIELDS - set(basis))
    if unknown_fields:
        raise ValueError(f"unknown basis fields: {', '.join(unknown_fields)}")
    if missing_fields:
        raise ValueError(f"missing basis fields: {', '.join(missing_fields)}")
    for field in sorted(YIZIJUE_LM_REQUIRED_BASIS_FIELDS):
        require_string(basis[field], f"basis.{field}")
    optional_string_fields = {
        "yin_yang": ("balance", "pressure"),
        "trigrams": ("outer", "inner"),
        "elements": ("outer", "inner", "relation", "modulation"),
    }
    for field, subfields in optional_string_fields.items():
        if field not in basis:
            continue
        if not isinstance(basis[field], dict):
            raise ValueError(f"basis.{field} must be an object")
        unknown_subfields = sorted(set(basis[field]) - set(subfields))
        missing_subfields = sorted(set(subfields) - set(basis[field]))
        if unknown_subfields:
            raise ValueError(f"unknown basis.{field} fields: {', '.join(unknown_subfields)}")
        if missing_subfields:
            raise ValueError(f"missing basis.{field} fields: {', '.join(missing_subfields)}")
        for subfield in subfields:
            require_string(basis[field][subfield], f"basis.{field}.{subfield}")
    require_member(basis["state"], ALLOWED_STATES, "basis.state")
    if base["output_type"] == "action_json" and basis["state"] != base["action"]["yizijue_state"]:
        raise ValueError("basis.state must match action.yizijue_state")
    return {**base, "basis": basis}


def enrich_basis_with_kernel_profile(basis: dict[str, Any], rule_schema: str = ACTIVE_RULE_SCHEMA) -> dict[str, Any]:
    state = require_string(basis["state"], "basis.state")
    source_schema = normalize_rule_schema(rule_schema)
    status_code = convert_status(int(state, 2), source_schema, ACTIVE_RULE_SCHEMA)
    profile = IchingKernel.cross_cutting_profile(status_code)
    yin_yang = profile["yin_yang"]
    inner_record = profile["inner_trigram_record"]
    outer_record = profile["outer_trigram_record"]
    trigram_records = profile["trigram_records"]
    dynamics = profile["element_dynamics"]
    return {
        **basis,
        "yin_yang": {
            "balance": str(yin_yang["balance"]),
            "pressure": str(yin_yang["pressure"]),
        },
        "trigrams": {
            "outer": str(trigram_records[outer_record["trigram"]]["name"]),
            "inner": str(trigram_records[inner_record["trigram"]]["name"]),
        },
        "elements": {
            "outer": str(dynamics["outer_element"]),
            "inner": str(dynamics["inner_element"]),
            "relation": str(dynamics["cross_relation"]),
            "modulation": str(dynamics["modulation"]),
        },
    }


def state_basis_for_lm_row(row: dict[str, Any]) -> dict[str, Any]:
    sample = validate_yizijue_lm_sample(row)
    rule_schema = sample["rule_schema"]
    if sample["output_type"] == "chat_reply":
        return enrich_basis_with_kernel_profile({
            "projection": "simple_chat",
            "state": "000000",
            "state_label": "chat_smalltalk",
            "transition": "reply_only",
            "rule": "simple chat returns a short local reply without execution",
        }, rule_schema)
    if sample["output_type"] == "clarify":
        return enrich_basis_with_kernel_profile({
            "projection": "ambiguous_request",
            "state": "000000",
            "state_label": "kun_clarify_boundary",
            "transition": "clarify_required",
            "rule": "ambiguous requests must ask for target, scope, and verification",
        }, rule_schema)
    action = sample["action"]
    action_name = action["action"]
    facts = action["facts"]
    if action_name == "ALLOW_ATOMIC_WRITE":
        return enrich_basis_with_kernel_profile({
            "projection": "safe_workspace_write",
            "state": action["yizijue_state"],
            "state_label": "qian_safe_write",
            "transition": "atomic_write_allowed",
            "rule": "workspace-relative writes may proceed with evidence",
        }, rule_schema)
    if action_name == "ALLOW_PATCH_WITH_SHA":
        return enrich_basis_with_kernel_profile({
            "projection": "safe_workspace_patch",
            "state": action["yizijue_state"],
            "state_label": "qian_safe_patch",
            "transition": "sha_patch_allowed",
            "rule": "workspace-relative patches require sha verification",
        }, rule_schema)
    if action_name == "RUN_VERIFIER_IN_SANDBOX":
        return enrich_basis_with_kernel_profile({
            "projection": "verification_request",
            "state": action["yizijue_state"],
            "state_label": "kan_sandbox_verifier",
            "transition": "sandbox_required",
            "rule": "verification commands must run in a sandbox",
        }, rule_schema)
    if action_name == "SOVEREIGNTY_HALT":
        return enrich_basis_with_kernel_profile({
            "projection": "danger_or_boundary_breach",
            "state": action["yizijue_state"],
            "state_label": "gen_sovereignty_halt",
            "transition": "hard_halt",
            "rule": "dangerous or outside-workspace actions must halt",
        }, rule_schema)
    if facts["intent_type"] == "invalid_intent":
        projection = "undefined_intent"
        rule = "undefined intent must be denied and recorded"
    else:
        projection = "denied_non_executable_request"
        rule = "non-executable or unsupported requests must be denied and recorded"
    return enrich_basis_with_kernel_profile({
        "projection": projection,
        "state": action["yizijue_state"],
        "state_label": "kun_deny_ledger",
        "transition": "deny_and_record",
        "rule": rule,
    }, rule_schema)


def yizijue_lm_state_rows_from_lm_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    state_rows = []
    for row in rows:
        sample = validate_yizijue_lm_sample(row)
        state_rows.append(
            validate_yizijue_lm_state_sample(
                {
                    **sample,
                    "basis": state_basis_for_lm_row(sample),
                }
            )
        )
    return state_rows
