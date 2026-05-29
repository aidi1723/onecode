from __future__ import annotations

from dataclasses import dataclass

from .build_mode_types import (
    HEX_CORRECT,
    HEX_CREATE,
    HEX_HALT,
    HEX_INSPECT,
    HEX_ISOLATE,
    HEX_PROMPT,
    HEX_RETURN,
    HEX_VERIFY,
    SCOPE_SHAOYANG,
    SCOPE_SHAOYIN,
    SCOPE_TAIYANG,
    SCOPE_TAIYIN,
)
from .build_mode_v3_balancer import BAGUA_ELEMENT_MAP


TWO_FORCES = ("yin", "yang")

FOUR象_SCOPE_MAP = {
    SCOPE_TAIYIN: {
        "name": "太阴",
        "force": "yin",
        "permission_posture": "archive_or_zero_tool",
    },
    SCOPE_SHAOYANG: {
        "name": "少阳",
        "force": "yang",
        "permission_posture": "human_or_decay_prompt",
    },
    SCOPE_SHAOYIN: {
        "name": "少阴",
        "force": "yin",
        "permission_posture": "inspect_or_halt",
    },
    SCOPE_TAIYANG: {
        "name": "太阳",
        "force": "yang",
        "permission_posture": "create_or_correct",
    },
}

HEXAGRAM_SCOPE_MAP = {
    HEX_RETURN: SCOPE_TAIYIN,
    HEX_VERIFY: SCOPE_SHAOYIN,
    HEX_ISOLATE: SCOPE_SHAOYIN,
    HEX_PROMPT: SCOPE_SHAOYANG,
    HEX_HALT: SCOPE_SHAOYIN,
    HEX_INSPECT: SCOPE_SHAOYIN,
    HEX_CORRECT: SCOPE_TAIYANG,
    HEX_CREATE: SCOPE_TAIYANG,
}

HEXAGRAM_FORCE_MAP = {
    HEX_RETURN: "yin",
    HEX_VERIFY: "yin",
    HEX_ISOLATE: "yin",
    HEX_PROMPT: "yang",
    HEX_HALT: "yin",
    HEX_INSPECT: "yin",
    HEX_CORRECT: "yang",
    HEX_CREATE: "yang",
}

MUTUAL_GENERATION_EDGES = (
    (HEX_ISOLATE, HEX_PROMPT, "water_buffers_long_streams_to_preserve_reasoning_motion"),
    (HEX_PROMPT, HEX_INSPECT, "wood_decay_audit_triggers_fire_dehydration"),
    (HEX_INSPECT, HEX_CREATE, "fire_digest_guides_scoped_disk_write"),
    (HEX_CREATE, HEX_VERIFY, "asset_write_hands_control_to_verification"),
    (HEX_VERIFY, HEX_RETURN, "passed_verification_archives_manifest"),
)

MUTUAL_OVERCOMING_EDGES = (
    (HEX_CREATE, HEX_HALT, "metal_policy_blocks_dangerous_growth"),
    (HEX_INSPECT, HEX_VERIFY, "fire_schema_injection_breaks_empty_tool_deadlock"),
    (HEX_HALT, HEX_RETURN, "earth_handoff_archives_after_model_privileges_stop"),
    (HEX_CORRECT, HEX_INSPECT, "soft_rewrite_routes_failed_action_to_inspection"),
)


@dataclass(frozen=True)
class CosmologyProfile:
    hexagram: str
    trigram_name: str
    force: str
    scope: str
    scope_name: str
    element: str
    resource_role: str
    permission_role: str


def cosmology_profile(hexagram: str) -> CosmologyProfile:
    element = BAGUA_ELEMENT_MAP[hexagram]
    scope = HEXAGRAM_SCOPE_MAP[hexagram]
    scope_info = FOUR象_SCOPE_MAP[scope]
    return CosmologyProfile(
        hexagram=hexagram,
        trigram_name=element.trigram_name,
        force=HEXAGRAM_FORCE_MAP[hexagram],
        scope=scope,
        scope_name=str(scope_info["name"]),
        element=element.element,
        resource_role=element.resource_role,
        permission_role=element.control_role,
    )


def validate_cosmology_contract() -> list[str]:
    errors: list[str] = []
    all_hexagrams = set(BAGUA_ELEMENT_MAP)
    if set(HEXAGRAM_SCOPE_MAP) != all_hexagrams:
        errors.append("hexagram_scope_map_must_cover_all_bagua")
    if set(HEXAGRAM_FORCE_MAP) != all_hexagrams:
        errors.append("hexagram_force_map_must_cover_all_bagua")
    if set(FOUR象_SCOPE_MAP) != {SCOPE_TAIYIN, SCOPE_SHAOYANG, SCOPE_SHAOYIN, SCOPE_TAIYANG}:
        errors.append("four_scope_map_must_cover_all_four_symbols")
    for force in HEXAGRAM_FORCE_MAP.values():
        if force not in TWO_FORCES:
            errors.append(f"unknown_force:{force}")
    for source, target, reason in [*MUTUAL_GENERATION_EDGES, *MUTUAL_OVERCOMING_EDGES]:
        if source not in all_hexagrams:
            errors.append(f"unknown_source:{reason}:{source}")
        if target not in all_hexagrams:
            errors.append(f"unknown_target:{reason}:{target}")
    return errors
