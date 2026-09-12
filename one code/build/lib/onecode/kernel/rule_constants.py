"""Centralized vocabulary for the I Ching runtime rule engine.

`hexagram.py` drives dispatch decisions from string literals for transition
actions, transition reasons, and element-dynamics modulations. Those literals
were previously hardcoded at each use site, which made it easy to introduce
typos or divergent copies of the same concept. This module is the single
source of truth for that vocabulary.

`StrEnum` members compare equal to their plain string value, so introducing
these enums does not change any externally observed behavior (dataclass
fields typed `str`, dict keys, and test assertions using bare string
literals all continue to work unchanged).

See `docs/ONECODE_ICHING_TERMINOLOGY_GLOSSARY.md` for the mapping from these
identifiers to their engineering meaning.
"""

from __future__ import annotations

from enum import StrEnum


class TransitionAction(StrEnum):
    CONTINUE = "continue"
    ACCELERATE = "accelerate"
    RECOVER = "recover"
    CHECKPOINT = "checkpoint"
    DISCOVER = "discover"
    HALT = "halt"
    COOLDOWN = "cooldown"
    THROTTLE = "throttle"
    PRUNE = "prune"
    ACTIVATE = "activate"


class TransitionReason(StrEnum):
    RULE_GAP_REQUIRES_DISCOVERY = "rule_gap_requires_discovery"
    SOVEREIGNTY_FIRE_SUPPRESSES_ASSET = "sovereignty_fire_suppresses_asset"
    SOVEREIGNTY_FIRE_BOUNDARY_HALT = "sovereignty_fire_boundary_halt"
    MOUNTAIN_CONTAINS_LOCAL_EXECUTOR_FAULT = "mountain_contains_local_executor_fault"
    YANG_OVERLOAD_COOLDOWN = "yang_overload_cooldown"
    NETWORK_WATER_PRESERVES_RESUME_SEED = "network_water_preserves_resume_seed"
    YIN_EXCESS_REQUIRES_ACTIVATION = "yin_excess_requires_activation"
    GENERATING_RELATION_ACCELERATES_EXECUTION = "generating_relation_accelerates_execution"
    GENERATED_BY_RELATION_RECOVERS_EXECUTION = "generated_by_relation_recovers_execution"
    CONTROLLED_BY_RELATION_REQUIRES_VERIFIER = "controlled_by_relation_requires_verifier"
    NEUTRAL_RELATION_REQUIRES_DISCOVERY = "neutral_relation_requires_discovery"
    WATER_QUENCHES_FIRE_BOUNDARY = "water_quenches_fire_boundary"
    METAL_PRUNES_WOOD_SCOPE = "metal_prunes_wood_scope"
    EARTH_DAMS_WATER_FLOW = "earth_dams_water_flow"
    WOOD_BREAKS_INERT_GROUND = "wood_breaks_inert_ground"
    CONTROLLING_RELATION_THROTTLES_EXECUTION = "controlling_relation_throttles_execution"
    SAME_ELEMENT_BALANCED_CONTINUE = "same_element_balanced_continue"


class ElementModulation(StrEnum):
    HARD_CONTROL = "hard_control"
    RECOVERY_SEED = "recovery_seed"
    QUENCH = "quench"
    PRUNE = "prune"
    FUEL = "fuel"
    DAM = "dam"
    BREAK_GROUND = "break_ground"
    REFINE = "refine"      # 火生土：炼化精制
    FORGE = "forge"        # 土生金：铸造强化
    TEMPER = "temper"      # 金生水：淬炼冷却
    NORMAL = "normal"


# Keyed by (cross_relation, outer_element, inner_element). Order does not
# matter here (unlike hexagram.IchingKernel.transition's priority cascade)
# because each key names a single, non-overlapping element pair.
ELEMENT_DYNAMICS_MODULATION_TABLE: dict[tuple[str, str, str], ElementModulation] = {
    ("controls", "fire", "metal"): ElementModulation.HARD_CONTROL,
    ("generates", "water", "wood"): ElementModulation.RECOVERY_SEED,
    ("controls", "water", "fire"): ElementModulation.QUENCH,
    ("controls", "metal", "wood"): ElementModulation.PRUNE,
    ("generates", "wood", "fire"): ElementModulation.FUEL,
    ("controls", "earth", "water"): ElementModulation.DAM,
    ("controls", "wood", "earth"): ElementModulation.BREAK_GROUND,
    ("generates", "fire", "earth"): ElementModulation.REFINE,
    ("generates", "earth", "metal"): ElementModulation.FORGE,
    ("generates", "metal", "water"): ElementModulation.TEMPER,
}
