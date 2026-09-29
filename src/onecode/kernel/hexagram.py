"""OneCode I Ching Kernel - Deterministic State Control System

This module implements the mathematical foundation of OneCode's control flow using
I Ching (易经) hexagram encoding. Every run produces a 6-bit status code (0-63)
representing one of the 64 hexagrams, which deterministically maps to transition
actions and dispatch decisions.

## Core Concepts

**Six-Line Encoding**: Each bit represents a yin (0) or yang (1) line
  - Bits 0-2: inner trigram (task state)
  - Bits 3-5: outer trigram (environment/context)
  - Example: 0b101000 = outer Li (fire) over inner Kun (earth)

**Trigram → Element Mapping**:
  - Qian (乾 111), Dui (兑 011) → metal
  - Zhen (震 001), Xun (巽 110) → wood
  - Kan (坎 010) → water
  - Li (离 101) → fire
  - Kun (坤 000), Gen (艮 100) → earth

**Five-Element Relations Drive Transitions**:
  - Generation cycle: wood→fire→earth→metal→water (accelerate/continue)
  - Control cycle: wood→earth→water→fire→metal (halt/throttle/prune)

**Transition Priority** (enforced in this order):
  1. Hard safety (path breach, timeout) overrides all symbolic rules
  2. Yin-yang pressure (pure yang → cooldown, pure yin → discover)
  3. Five-element relations (outer acts on inner)
  4. Neutral fallback (continue or discover)

## Design Documentation

For detailed mathematical proofs and rule derivation, see:
- docs/superpowers/specs/2026-05-28-onecode-v0.5-iching-complete-rule-kernel-design.md
- docs/superpowers/specs/2026-06-01-onecode-yinyang-wuxing-runtime-rule-mapping-design.md
- docs/superpowers/specs/2026-05-28-onecode-iching-source-alignment.md

## Rule Closure Principle

External facts (file presence, SHA256 matches, timeouts) are sampled as physical
evidence, then collapsed into this rule surface. Bug fixes must close inside the
existing 64-state system without adding parallel control variables (confidence,
priority, mood, retry scores).

"""
from dataclasses import dataclass


from onecode.kernel.hexagram_profile import IchingProfileMixin
from onecode.kernel.hexagram_dynamics import IchingDynamicsMixin
from onecode.kernel.hexagram_certificates import IchingCertificatesMixin



@dataclass(frozen=True)
class IchingTransition:
    status_code: int
    action: str
    reason: str | None


class IchingKernel(IchingProfileMixin, IchingDynamicsMixin, IchingCertificatesMixin):
    KUN = 0b000
    ZHEN = 0b001
    KAN = 0b010
    DUI = 0b011
    GEN = 0b100
    LI = 0b101
    XUN = 0b110
    QIAN = 0b111

    TRIGRAM_NAMES = {
        KUN: "kun",
        ZHEN: "zhen",
        KAN: "kan",
        DUI: "dui",
        GEN: "gen",
        XUN: "xun",
        LI: "li",
        QIAN: "qian",
    }
    TRIGRAM_VIRTUES = {
        KUN: ("receptivity", "receive"),
        ZHEN: ("initiation", "activate"),
        KAN: ("risk", "checkpoint"),
        DUI: ("exchange", "deliver"),
        GEN: ("stopping", "stop"),
        LI: ("clarity_attachment", "inspect"),
        XUN: ("penetration", "refine"),
        QIAN: ("strength", "advance"),
    }
    LINE_POSITION_NAMES = ("initial", "second", "third", "fourth", "fifth", "top")
    RESPONSE_PAIRS = ((0, 3), (1, 4), (2, 5))
    FOUR_SYMBOLS = {
        0b00: "tai_yin",
        0b01: "shao_yin",
        0b10: "shao_yang",
        0b11: "tai_yang",
    }
    FOUR_SYMBOL_RUNTIME_SEMANTICS = {
        "tai_yin": "halted",
        "shao_yin": "write_commit",
        "shao_yang": "safe_read_skip",
        "tai_yang": "overload_clash",
    }
    # Classical Da Yan (大衍之数) discrete stalk probability measure:
    # 9 (Old Yang, moving): 3/16 (0.1875)
    # 8 (Young Yin, static): 5/16 (0.3125)
    # 7 (Young Yang, static): 5/16 (0.3125)
    # 6 (Old Yin, moving): 3/16 (0.1875)
    DAYAN_PROBABILITIES = {
        9: 3 / 16,
        8: 5 / 16,
        7: 5 / 16,
        6: 3 / 16,
    }
    DIMENSION_LABELS = {
        1: "liangyi",
        2: "four_symbols",
        3: "bagua",
        6: "hexagram",
    }
    TRIADIC_BANDS = (
        ("earth", "environment", (0, 1)),
        ("human", "agent", (2, 3)),
        ("heaven", "feedback", (4, 5)),
    )
    # Correspondence layer: these mappings are traditional associations, not bit-derived facts.
    TRIGRAM_ELEMENTS = {
        KUN: "earth",
        ZHEN: "wood",
        KAN: "water",
        DUI: "metal",
        GEN: "earth",
        XUN: "wood",
        LI: "fire",
        QIAN: "metal",
    }
    GENERATES = {
        "wood": "fire",
        "fire": "earth",
        "earth": "metal",
        "metal": "water",
        "water": "wood",
    }
    CONTROLS = {
        "wood": "earth",
        "earth": "water",
        "water": "fire",
        "fire": "metal",
        "metal": "wood",
    }
    ELEMENT_ORDER = ("metal", "wood", "water", "fire", "earth")
    ELEMENT_GENERATION_ORDER = ("wood", "fire", "earth", "metal", "water")
    POLARITY_THRESHOLD = 1 / 3
    ROLLBACK_STATUS = 0b010001
    ENTROPY_THRESHOLD = 0.5
    ELEMENT_DAMPING_ALPHA = 1.0
    ELEMENT_EXECUTION_BANDWIDTH = {
        ("metal", "metal"): 1.0,
        ("metal", "wood"): 0.0,
        ("metal", "water"): 1.0,
        ("metal", "fire"): 1.0,
        ("metal", "earth"): 1.0,
        ("wood", "metal"): 1.0,
        ("wood", "wood"): 1.0,
        ("wood", "water"): 0.0,
        ("wood", "fire"): 1.0,
        ("wood", "earth"): 0.0,
        ("water", "metal"): 0.0,
        ("water", "wood"): 1.0,
        ("water", "water"): 1.0,
        ("water", "fire"): 0.0,
        ("water", "earth"): 1.0,
        ("fire", "metal"): 0.0,
        ("fire", "wood"): 1.0,
        ("fire", "water"): 1.0,
        ("fire", "fire"): 1.0,
        ("fire", "earth"): 1.0,
        ("earth", "metal"): 1.0,
        ("earth", "wood"): 1.0,
        ("earth", "water"): 1.0,
        ("earth", "fire"): 0.0,
        ("earth", "earth"): 1.0,
    }
    RUNTIME_RELATION_POLICY = {
        "generates": ("accelerate", "generating_relation_accelerates_execution"),
        "same": ("continue", None),
        "generated_by": ("recover", "generated_by_relation_recovers_execution"),
        "controlled_by": ("checkpoint", "controlled_by_relation_requires_verifier"),
        "neutral": ("discover", "neutral_relation_requires_discovery"),
    }
    HARMONY_RELATION_SCORES = {
        "generates": 2,
        "same": 1,
        "generated_by": 1,
        "neutral": 0,
        "controls": -1,
        "controlled_by": -2,
    }
    RUNTIME_CONTROL_MODULATION_POLICY = {
        "hard_control": ("halt", "sovereignty_fire_suppresses_asset"),
        "quench": ("halt", "water_quenches_fire_boundary"),
        "prune": ("prune", "metal_prunes_wood_scope"),
        "dam": ("throttle", "earth_dams_water_flow"),
        "break_ground": ("activate", "wood_breaks_inert_ground"),
        "normal": ("throttle", "controlling_relation_throttles_execution"),
    }
    RULE_LAYERS = {
        "bit_derived": [
            "status_code",
            "binary",
            "math",
            "dimension",
            "triadic",
            "position",
            "correspondence",
            "perspective",
            "mutation",
            "nuclear",
            "inner_trigram",
            "outer_trigram",
            "trigram_records",
            "liangyi",
            "yin_yang",
            "polarity_index",
            "balance_mask",
            "four_symbols",
            "overlapping_four_symbols",
            "four_symbol_balance",
        ],
        "correspondence_derived": [
            "inner_element",
            "outer_element",
            "element_records",
            "element_matrix",
            "element_relation",
            "element_dynamics",
            "evolved_element_modulation",
            "harmony",
            "inner_trigram_virtue",
            "outer_trigram_virtue",
        ],
        "onecode_runtime": [
            "transition",
            "dispatch_decision",
            "runtime_policy",
            "execution_bandwidth",
            "global_entropy",
            "state_distribution_entropy",
            "transition_graph",
            "attractor_analysis",
            "stability_analysis",
            "topology_certificate",
            "lyapunov_certificate",
            "entropy_gate_certificate",
            "totality_certificate",
            "safety_dominance_certificate",
            "collision_risk_certificate",
            "lyapunov_energy",
            "hysteresis_gate",
        ],
    }

    @classmethod
    def should_skip(cls, status_code: int) -> bool:
        return bool(cls.skip_decision(status_code)["should_skip"])
    @classmethod
    def skip_decision(cls, status_code: int) -> dict[str, bool | int | str]:
        inner = status_code & 0b111
        outer = (status_code >> 3) & 0b111
        if outer == cls.LI:
            reason = "sovereignty_fire_blocks_skip"
            should_skip = False
        elif inner == cls.DUI:
            reason = "asset_ready_without_sovereignty_fire"
            should_skip = True
        else:
            reason = "asset_not_ready_for_skip"
            should_skip = False
        return {
            "should_skip": should_skip,
            "reason": reason,
            "inner_trigram": inner,
            "outer_trigram": outer,
            "inner_element": cls.element_for_trigram(inner),
            "outer_element": cls.element_for_trigram(outer),
            "rule": "inner_dui_ready_and_outer_not_li",
        }
    @classmethod
    def classify_outcome(cls, status: str, reason: str | None) -> int:
        if reason in {"sovereignty_breach", "permission_denied"}:
            return cls.compute_status(cls.LI, cls.KUN)
        if reason in {"malformed_input", "oversized_input", "resource_budget_exceeded"}:
            return cls.compute_status(cls.LI, cls.KUN)
        if reason == "http_timeout":
            return cls.compute_status(cls.KAN, cls.ZHEN)
        if reason in {"search_miss", "path_not_found"}:
            return cls.compute_status(cls.KUN, cls.KUN)
        if reason in {"action_exception", "run_exception"}:
            return cls.compute_status(cls.GEN, cls.KUN)
        if reason == "invalid_intent":
            return cls.compute_status(cls.LI, cls.KUN)
        if reason == "self_audit_check_failed":
            return cls.compute_status(cls.LI, cls.KUN)
        if status == "skipped":
            return cls.compute_status(cls.QIAN, cls.DUI)
        if status == "completed":
            return cls.compute_status(cls.QIAN, cls.QIAN)
        return cls.compute_status(cls.KUN, cls.KUN)
    @classmethod
    def classify_resume_audit(cls, status: str, reason: str | None) -> int:
        if status == "ready":
            return cls.compute_status(cls.QIAN, cls.DUI)
        if reason == "path_outside_workspace":
            return cls.compute_status(cls.LI, cls.KUN)
        if reason in {"malformed_manifest", "invalid_checkpoint_evidence", "checkpoint_sha_mismatch"}:
            return cls.compute_status(cls.LI, cls.KUN)
        if reason in {"missing_file", "sha256_mismatch"}:
            return cls.compute_status(cls.KAN, cls.ZHEN)
        return cls.compute_status(cls.KUN, cls.KUN)
    @classmethod
    def classify_skill_context(cls, status: str, reason: str | None) -> int:
        if status == "blocked" or reason in {"unsafe_executable_skill", "outside_project"}:
            return cls.compute_status(cls.LI, cls.KUN)
        if status == "warning" or reason in {"invalid_manifest", "duplicate_name"}:
            return cls.compute_status(cls.KAN, cls.GEN)
        if status == "ok":
            return cls.compute_status(cls.KAN, cls.ZHEN)
        return cls.compute_status(cls.KUN, cls.KUN)
    @classmethod
    def transition(cls, status_code: int) -> IchingTransition:
        normalized = status_code & 0b111111
        inner = normalized & 0b111
        outer = (normalized >> 3) & 0b111
        dynamics = cls.element_dynamics(normalized)

        if normalized == cls.compute_status(cls.KUN, cls.KUN):
            return IchingTransition(
                status_code=normalized,
                action="discover",
                reason="rule_gap_requires_discovery",
            )
        if dynamics["modulation"] == "hard_control":
            return IchingTransition(
                status_code=cls.compute_status(cls.LI, cls.KUN),
                action="halt",
                reason="sovereignty_fire_suppresses_asset",
            )
        if outer == cls.LI:
            return IchingTransition(
                status_code=normalized,
                action="halt",
                reason="sovereignty_fire_boundary_halt",
            )
        if normalized == cls.compute_status(cls.GEN, cls.KUN):
            return IchingTransition(
                status_code=normalized,
                action="checkpoint",
                reason="mountain_contains_local_executor_fault",
            )

        profile = cls.yin_yang_profile(normalized)
        if profile["balance"] in {"pure_yang", "yang_excess"}:
            return IchingTransition(
                status_code=cls.compute_status(cls.GEN, inner),
                action="cooldown",
                reason="yang_overload_cooldown",
            )
        if profile["balance"] == "pure_yin":
            return IchingTransition(
                status_code=normalized,
                action="discover",
                reason="rule_gap_requires_discovery",
            )
        if dynamics["modulation"] == "recovery_seed":
            return IchingTransition(
                status_code=normalized,
                action="checkpoint",
                reason="network_water_preserves_resume_seed",
            )
        if profile["balance"] == "yin_excess" and inner != cls.KUN:
            return IchingTransition(
                status_code=normalized,
                action="activate",
                reason="yin_excess_requires_activation",
            )

        action, reason = cls.runtime_relation_policy(dynamics["cross_relation"], dynamics["modulation"])
        return IchingTransition(status_code=normalized, action=action, reason=reason)
    @classmethod
    def dispatch_decision(cls, transition: IchingTransition) -> str:
        if transition.action in {"halt", "checkpoint", "discover"}:
            return "stop"
        return "continue"
    @classmethod
    def delivery_decision(
        cls,
        status: str | None,
        requested_count: int | None,
        completed_count: int | None,
        skipped_count: int | None,
        failed_count: int | None,
    ) -> dict[str, int | str]:
        if all(isinstance(value, int) and not isinstance(value, bool) for value in (requested_count, completed_count, skipped_count, failed_count)):
            resolved = completed_count + skipped_count + failed_count
            counts = {
                "resolved_count": resolved,
                "remaining_count": max(requested_count - resolved, 0),
            }
            if status == "completed" and failed_count == 0 and resolved == requested_count:
                return {"delivery_status": "deliverable", "next_action": "idle"} | counts
            if failed_count > 0 or status in {"halted", "denied"}:
                return {"delivery_status": "blocked", "next_action": "resume"} | counts
            if resolved < requested_count:
                return {"delivery_status": "partial", "next_action": "resume"} | counts
        if status == "completed":
            return {"delivery_status": "deliverable", "next_action": "idle"}
        return {"delivery_status": "unknown", "next_action": "inspect"}
    @classmethod
    def process_exit_code(cls, status: str, reason: str | None) -> int:
        status_code = cls.classify_outcome(status, reason)
        transition = cls.transition(status_code)
        return 1 if cls.dispatch_decision(transition) == "stop" else 0


def is_valid_hexagram_code(value: str) -> bool:
    return len(value) == 6 and all(char in "01" for char in value)


@dataclass(frozen=True)
class HexagramStatusCode:
    value: str

    def __post_init__(self) -> None:
        if not is_valid_hexagram_code(self.value):
            raise ValueError(f"invalid hexagram status code: {self.value!r}")

    def __str__(self) -> str:
        return self.value


BUILD_ENTRY = HexagramStatusCode("111111")
VERIFY_GATE = HexagramStatusCode("000001")
CORRECTION_GATE = HexagramStatusCode("110000")
INSPECT_GATE = HexagramStatusCode("101000")
COMPLETE = HexagramStatusCode("000000")
