from dataclasses import dataclass


@dataclass(frozen=True)
class IchingTransition:
    status_code: int
    action: str
    reason: str | None


class IchingKernel:
    KUN = 0b000
    ZHEN = 0b001
    KAN = 0b010
    DUI = 0b011
    GEN = 0b100
    XUN = 0b101
    LI = 0b110
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
    FOUR_SYMBOLS = {
        0b00: "tai_yin",
        0b01: "shao_yang",
        0b10: "shao_yin",
        0b11: "tai_yang",
    }
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
    RULE_LAYERS = {
        "bit_derived": [
            "status_code",
            "binary",
            "inner_trigram",
            "outer_trigram",
            "trigram_records",
            "yin_yang",
            "four_symbols",
        ],
        "correspondence_derived": [
            "inner_element",
            "outer_element",
            "element_records",
            "element_matrix",
            "element_relation",
            "element_dynamics",
        ],
        "onecode_runtime": ["transition"],
    }

    @classmethod
    def compute_status(cls, outer_trigram: int, inner_trigram: int) -> int:
        return ((outer_trigram & 0b111) << 3) | (inner_trigram & 0b111)

    @classmethod
    def rule_layers(cls) -> dict[str, list[str]]:
        return {layer: list(fields) for layer, fields in cls.RULE_LAYERS.items()}

    @classmethod
    def four_symbol_for_bits(cls, bits: int) -> str:
        return cls.FOUR_SYMBOLS[bits & 0b11]

    @classmethod
    def four_symbols(cls, status_code: int) -> list[dict[str, int | str]]:
        return [
            {
                "pair_index": pair_index,
                "bits": (status_code >> (pair_index * 2)) & 0b11,
                "symbol": cls.four_symbol_for_bits((status_code >> (pair_index * 2)) & 0b11),
            }
            for pair_index in range(3)
        ]

    @classmethod
    def yin_yang_profile(cls, status_code: int) -> dict[str, int | str]:
        yang_count = (status_code & 0b111111).bit_count()
        yin_count = 6 - yang_count
        return cls.yin_yang_counts(yang_count, yin_count, width=6)

    @classmethod
    def yin_yang_counts(cls, yang_count: int, yin_count: int, width: int) -> dict[str, int | str]:
        if yang_count == width:
            balance = "pure_yang"
        elif yin_count == width:
            balance = "pure_yin"
        elif width == 6 and yang_count == 5:
            balance = "yang_excess"
        elif width == 6 and yang_count in {3, 4}:
            balance = "balanced"
        elif width < 6 and abs(yang_count - yin_count) <= 1:
            balance = "balanced"
        elif yang_count > yin_count:
            balance = "yang_excess"
        else:
            balance = "yin_excess"
        return {"yang_count": yang_count, "yin_count": yin_count, "balance": balance}

    @classmethod
    def yin_yang_profile_for_bits(cls, value: int, width: int) -> dict[str, int | str]:
        mask = (1 << width) - 1
        yang_count = (value & mask).bit_count()
        return cls.yin_yang_counts(yang_count, width - yang_count, width=width)

    @classmethod
    def line_records(cls, status_code: int) -> list[dict[str, int | str]]:
        normalized = status_code & 0b111111
        return [
            {
                "line_index": line_index,
                "value": (normalized >> line_index) & 1,
                "polarity": "yang" if ((normalized >> line_index) & 1) else "yin",
            }
            for line_index in range(6)
        ]

    @classmethod
    def trigram_record(cls, status_code: int, scope: str) -> dict:
        normalized = status_code & 0b111111
        if scope == "inner":
            trigram = normalized & 0b111
            lines = cls.line_records(normalized)[:3]
        elif scope == "outer":
            trigram = (normalized >> 3) & 0b111
            lines = cls.line_records(normalized)[3:]
        else:
            raise ValueError(f"scope must be 'inner' or 'outer': {scope!r}")
        return {
            "scope": scope,
            "trigram": trigram,
            "binary": format(trigram, "03b"),
            "element": cls.element_for_trigram(trigram),
            "yin_yang": cls.yin_yang_profile_for_bits(trigram, width=3),
            "lines": lines,
        }

    @classmethod
    def standalone_trigram_record(cls, trigram: int) -> dict:
        normalized = trigram & 0b111
        return {
            "trigram": normalized,
            "name": cls.TRIGRAM_NAMES[normalized],
            "binary": format(normalized, "03b"),
            "element": cls.element_for_trigram(normalized),
            "yin_yang": cls.yin_yang_profile_for_bits(normalized, width=3),
            "lines": [
                {
                    "line_index": line_index,
                    "value": (normalized >> line_index) & 1,
                    "polarity": "yang" if ((normalized >> line_index) & 1) else "yin",
                }
                for line_index in range(3)
            ],
        }

    @classmethod
    def trigram_records(cls) -> dict[int, dict]:
        return {trigram: cls.standalone_trigram_record(trigram) for trigram in range(8)}

    @classmethod
    def yin_yang_cross_profile(cls, status_code: int) -> dict:
        normalized = status_code & 0b111111
        lines = cls.line_records(normalized)
        global_profile = cls.yin_yang_profile(normalized)
        profile = {
            "yang_count": global_profile["yang_count"],
            "yin_count": global_profile["yin_count"],
            "balance": global_profile["balance"],
            "global": global_profile,
            "pressure": cls.balance_pressure(global_profile["balance"]),
            "lines": lines,
            "four_symbol_windows": [
                {"pair_index": pair_index}
                | cls.yin_yang_profile_for_bits((normalized >> (pair_index * 2)) & 0b11, width=2)
                for pair_index in range(3)
            ],
            "inner_trigram": cls.yin_yang_profile_for_bits(normalized & 0b111, width=3),
            "outer_trigram": cls.yin_yang_profile_for_bits((normalized >> 3) & 0b111, width=3),
        }
        return profile

    @classmethod
    def balance_pressure(cls, balance: str) -> str:
        if balance in {"pure_yang", "yang_excess"}:
            return "cooldown"
        if balance in {"pure_yin", "yin_excess"}:
            return "activate"
        return "stable"

    @classmethod
    def element_for_trigram(cls, trigram: int) -> str:
        return cls.TRIGRAM_ELEMENTS[trigram & 0b111]

    @classmethod
    def element_relation(cls, source: str, target: str) -> str:
        if source == target:
            return "same"
        if cls.GENERATES.get(source) == target:
            return "generates"
        if cls.CONTROLS.get(source) == target:
            return "controls"
        return "neutral"

    @classmethod
    def element_records(cls) -> dict[str, dict[str, str]]:
        elements = tuple(cls.GENERATES.keys())
        return {
            element: {
                "element": element,
                "generates": cls.GENERATES[element],
                "generated_by": next(source for source, target in cls.GENERATES.items() if target == element),
                "controls": cls.CONTROLS[element],
                "controlled_by": next(source for source, target in cls.CONTROLS.items() if target == element),
            }
            for element in elements
        }

    @classmethod
    def element_matrix(cls) -> dict[tuple[str, str], str]:
        elements = tuple(cls.GENERATES.keys())
        return {
            (source, target): cls.element_cross_relation(source, target)
            for source in elements
            for target in elements
        }

    @classmethod
    def element_cross_relation(cls, source: str, target: str) -> str:
        relation = cls.element_relation(source, target)
        if relation != "neutral":
            return relation
        if cls.GENERATES.get(target) == source:
            return "generated_by"
        if cls.CONTROLS.get(target) == source:
            return "controlled_by"
        return "neutral"

    @classmethod
    def element_dynamics(cls, status_code: int) -> dict[str, str]:
        normalized = status_code & 0b111111
        inner = normalized & 0b111
        outer = (normalized >> 3) & 0b111
        outer_element = cls.element_for_trigram(outer)
        inner_element = cls.element_for_trigram(inner)
        relation = cls.element_relation(outer_element, inner_element)
        pressure = cls.yin_yang_cross_profile(normalized)["pressure"]
        if relation == "controls" and outer_element == "fire" and inner_element == "metal":
            modulation = "hard_control"
        elif relation == "generates" and outer_element == "water" and inner_element == "wood":
            modulation = "recovery_seed"
        else:
            modulation = "normal"
        return {
            "outer_element": outer_element,
            "inner_element": inner_element,
            "relation": relation,
            "yin_yang_pressure": pressure,
            "modulation": modulation,
        }

    @classmethod
    def cross_cutting_profile(cls, status_code: int) -> dict:
        normalized = status_code & 0b111111
        inner = normalized & 0b111
        outer = (normalized >> 3) & 0b111
        outer_element = cls.element_for_trigram(outer)
        inner_element = cls.element_for_trigram(inner)
        transition = cls.transition(normalized)
        return {
            "status_code": normalized,
            "binary": format(normalized, "06b"),
            "outer_trigram": outer,
            "inner_trigram": inner,
            "lines": cls.line_records(normalized),
            "outer_trigram_record": cls.trigram_record(normalized, "outer"),
            "inner_trigram_record": cls.trigram_record(normalized, "inner"),
            "trigram_records": cls.trigram_records(),
            "outer_element": outer_element,
            "inner_element": inner_element,
            "element_records": cls.element_records(),
            "element_matrix": {f"{source}->{target}": relation for (source, target), relation in cls.element_matrix().items()},
            "element_relation": cls.element_relation(outer_element, inner_element),
            "element_dynamics": cls.element_dynamics(normalized),
            "yin_yang": cls.yin_yang_cross_profile(normalized),
            "four_symbols": cls.four_symbols(normalized),
            "transition": {
                "status_code": transition.status_code,
                "action": transition.action,
                "reason": transition.reason,
            },
            "rule_layers": cls.rule_layers(),
        }

    @classmethod
    def hexagram_record(cls, status_code: int) -> dict:
        return cls.cross_cutting_profile(status_code)

    @classmethod
    def hexagram_records(cls) -> dict[int, dict]:
        return {status_code: cls.hexagram_record(status_code) for status_code in range(64)}

    @classmethod
    def flip_line(cls, status_code: int, line_index: int) -> int:
        if line_index < 0 or line_index > 5:
            raise ValueError(f"line_index must be between 0 and 5: {line_index!r}")
        return (status_code & 0b111111) ^ (1 << line_index)

    @classmethod
    def should_skip(cls, status_code: int) -> bool:
        inner = status_code & 0b111
        outer = (status_code >> 3) & 0b111
        return inner == cls.DUI and outer != cls.LI

    @classmethod
    def classify_outcome(cls, status: str, reason: str | None) -> int:
        if reason in {"sovereignty_breach", "permission_denied"}:
            return cls.compute_status(cls.LI, cls.KUN)
        if reason == "http_timeout":
            return cls.compute_status(cls.KAN, cls.ZHEN)
        if reason == "invalid_intent":
            return cls.compute_status(cls.KUN, cls.KUN)
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
        if reason in {"missing_file", "sha256_mismatch"}:
            return cls.compute_status(cls.KAN, cls.ZHEN)
        return cls.compute_status(cls.KUN, cls.KUN)

    @classmethod
    def transition(cls, status_code: int) -> IchingTransition:
        inner = status_code & 0b111
        dynamics = cls.element_dynamics(status_code)

        if dynamics["modulation"] == "hard_control":
            return IchingTransition(
                status_code=cls.compute_status(cls.LI, cls.KUN),
                action="halt",
                reason="sovereignty_fire_suppresses_asset",
            )
        if (status_code >> 3) & 0b111 == cls.LI:
            return IchingTransition(
                status_code=status_code,
                action="halt",
                reason="sovereignty_fire_boundary_halt",
            )
        if dynamics["modulation"] == "recovery_seed":
            return IchingTransition(
                status_code=status_code,
                action="checkpoint",
                reason="network_water_preserves_resume_seed",
            )
        profile = cls.yin_yang_profile(status_code)
        if profile["balance"] in {"pure_yang", "yang_excess"}:
            return IchingTransition(
                status_code=cls.compute_status(cls.GEN, inner),
                action="cooldown",
                reason="yang_overload_cooldown",
            )
        if status_code == cls.compute_status(cls.KUN, cls.KUN):
            return IchingTransition(
                status_code=status_code,
                action="discover",
                reason="rule_gap_requires_mapping",
            )
        return IchingTransition(status_code=status_code, action="continue", reason=None)


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
