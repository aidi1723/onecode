from dataclasses import dataclass
import math


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
    FOUR_SYMBOL_RUNTIME_SEMANTICS = {
        "tai_yin": "halted",
        "shao_yang": "safe_read_skip",
        "shao_yin": "write_commit",
        "tai_yang": "overload_clash",
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
    def compute_status(cls, outer_trigram: int, inner_trigram: int) -> int:
        return ((outer_trigram & 0b111) << 3) | (inner_trigram & 0b111)

    @classmethod
    def liangyi_values(cls) -> tuple[int, int]:
        return (0, 1)

    @classmethod
    def cartesian_states(cls, width: int) -> list[int]:
        if width < 0:
            raise ValueError(f"width must be non-negative: {width!r}")
        return list(range(1 << width))

    @classmethod
    def dimension_profile(cls, width: int) -> dict[str, int | str]:
        if width <= 0:
            raise ValueError(f"width must be positive: {width!r}")
        return {
            "width": width,
            "state_count": 1 << width,
            "bit_order": "bottom_to_top",
            "state_space": f"Y^{width}",
            "label": cls.DIMENSION_LABELS.get(width, "binary_state_space"),
        }

    @classmethod
    def triadic_profile(cls, status_code: int) -> dict[str, dict[str, int | str | list[int]]]:
        normalized = status_code & 0b111111
        profile: dict[str, dict[str, int | str | list[int]]] = {}
        for name, role, line_indexes in cls.TRIADIC_BANDS:
            start = line_indexes[0]
            bits = (normalized >> start) & 0b11
            yin_yang = cls.yin_yang_profile_for_bits(bits, width=2)
            profile[name] = {
                "name": name,
                "role": role,
                "line_indexes": list(line_indexes),
                "bits": bits,
                "symbol": cls.four_symbol_for_bits(bits),
                "yang_count": yin_yang["yang_count"],
                "yin_count": yin_yang["yin_count"],
                "balance": yin_yang["balance"],
            }
        return profile

    @classmethod
    def bits_for_state(cls, value: int, width: int) -> list[int]:
        if width < 0:
            raise ValueError(f"width must be non-negative: {width!r}")
        return [(value >> bit_index) & 1 for bit_index in range(width)]

    @classmethod
    def state_for_bits(cls, bits: list[int]) -> int:
        value = 0
        for bit_index, bit in enumerate(bits):
            if bit not in {0, 1}:
                raise ValueError(f"bits must contain only 0 or 1: {bit!r}")
            value |= bit << bit_index
        return value

    @classmethod
    def four_symbol_for_pair(cls, bits: int) -> str:
        return cls.four_symbol_for_bits(bits)

    @classmethod
    def trigram_for_bits(cls, bits: int) -> dict:
        return cls.standalone_trigram_record(bits)

    @classmethod
    def hexagram_status(cls, outer: int, inner: int) -> int:
        return cls.compute_status(outer, inner)

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
    def liangyi_bits(cls, status_code: int) -> list[dict[str, int | str]]:
        normalized = status_code & 0b111111
        return [
            {
                "bit_index": bit_index,
                "value": (normalized >> bit_index) & 1,
                "polarity": "yang" if ((normalized >> bit_index) & 1) else "yin",
                "runtime_semantics": "active" if ((normalized >> bit_index) & 1) else "inactive",
            }
            for bit_index in range(6)
        ]

    @classmethod
    def overlapping_four_symbols(cls, status_code: int) -> list[dict[str, int | str]]:
        normalized = status_code & 0b111111
        windows = []
        for window_index in range(5):
            bits = (normalized >> window_index) & 0b11
            symbol = cls.four_symbol_for_bits(bits)
            windows.append(
                {
                    "window_index": window_index,
                    "bits": bits,
                    "symbol": symbol,
                    "runtime_semantics": cls.FOUR_SYMBOL_RUNTIME_SEMANTICS[symbol],
                }
            )
        return windows

    @classmethod
    def four_symbol_balance_vector(cls, status_code: int) -> dict[str, dict[str, int] | int | str | None]:
        counts = {symbol: 0 for symbol in cls.FOUR_SYMBOLS.values()}
        for window in cls.overlapping_four_symbols(status_code):
            counts[str(window["symbol"])] += 1
        if counts["tai_yang"] > counts["shao_yang"] + counts["shao_yin"]:
            return {
                "counts": counts,
                "decision": "overflow",
                "change_mask": 0b100000,
                "reason": "tai_yang_exceeds_minor_symbols",
            }
        return {"counts": counts, "decision": "stable", "change_mask": 0, "reason": None}

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
            "polarity_index": cls.polarity_index(normalized),
            "balance_mask": cls.balance_mask(normalized),
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
    def element_distance(cls, source: str, target: str) -> int:
        if source not in cls.ELEMENT_GENERATION_ORDER:
            raise ValueError(f"unknown source element: {source!r}")
        if target not in cls.ELEMENT_GENERATION_ORDER:
            raise ValueError(f"unknown target element: {target!r}")
        source_index = cls.ELEMENT_GENERATION_ORDER.index(source)
        target_index = cls.ELEMENT_GENERATION_ORDER.index(target)
        return (target_index - source_index) % len(cls.ELEMENT_GENERATION_ORDER)

    @classmethod
    def generate_element(cls, element: str) -> str:
        if element not in cls.ELEMENT_GENERATION_ORDER:
            raise ValueError(f"unknown element: {element!r}")
        index = cls.ELEMENT_GENERATION_ORDER.index(element)
        return cls.ELEMENT_GENERATION_ORDER[(index + 1) % len(cls.ELEMENT_GENERATION_ORDER)]

    @classmethod
    def control_element(cls, element: str) -> str:
        if element not in cls.ELEMENT_GENERATION_ORDER:
            raise ValueError(f"unknown element: {element!r}")
        index = cls.ELEMENT_GENERATION_ORDER.index(element)
        return cls.ELEMENT_GENERATION_ORDER[(index + 2) % len(cls.ELEMENT_GENERATION_ORDER)]

    @classmethod
    def element_relation(cls, source: str, target: str) -> str:
        distance = cls.element_distance(source, target)
        if distance == 0:
            return "same"
        if distance == 1:
            return "generates"
        if distance == 2:
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
    def harmony_score(cls, status_code: int) -> dict[str, int | str]:
        normalized = status_code & 0b111111
        inner = normalized & 0b111
        outer = (normalized >> 3) & 0b111
        outer_element = cls.element_for_trigram(outer)
        inner_element = cls.element_for_trigram(inner)
        relation = cls.element_cross_relation(outer_element, inner_element)
        return {
            "score": cls.HARMONY_RELATION_SCORES[relation],
            "relation": relation,
            "outer_element": outer_element,
            "inner_element": inner_element,
            "method": "outer_inner_element_relation",
        }

    @classmethod
    def runtime_relation_policy(cls, relation: str, modulation: str) -> tuple[str, str | None]:
        if relation == "controls":
            return cls.RUNTIME_CONTROL_MODULATION_POLICY.get(
                modulation,
                cls.RUNTIME_CONTROL_MODULATION_POLICY["normal"],
            )
        return cls.RUNTIME_RELATION_POLICY.get(relation, cls.RUNTIME_RELATION_POLICY["neutral"])

    @classmethod
    def execution_bandwidth(cls, status_code: int, base: float = 1.0) -> float:
        normalized = status_code & 0b111111
        inner = normalized & 0b111
        outer = (normalized >> 3) & 0b111
        outer_element = cls.element_for_trigram(outer)
        inner_element = cls.element_for_trigram(inner)
        return base * cls.ELEMENT_EXECUTION_BANDWIDTH[(outer_element, inner_element)]

    @classmethod
    def aggregate_status(cls, status_codes: list[int]) -> int:
        if not status_codes:
            return cls.compute_status(cls.KUN, cls.KUN)
        outer_global = 0
        inner_global = 0b111
        for status_code in status_codes:
            normalized = status_code & 0b111111
            outer_global |= (normalized >> 3) & 0b111
            inner_global &= normalized & 0b111
        return cls.compute_status(outer_global, inner_global)

    @classmethod
    def polarity_index(cls, status_code: int) -> float:
        return (((status_code & 0b111111).bit_count()) - 3) / 3

    @classmethod
    def balance_mask(cls, status_code: int, threshold: float | None = None) -> int:
        polarity = cls.polarity_index(status_code)
        active_threshold = cls.POLARITY_THRESHOLD if threshold is None else threshold
        if abs(polarity) <= active_threshold:
            return 0b000000
        if polarity > active_threshold:
            return 0b100000
        return 0b000001

    @classmethod
    def apply_balanced_event(cls, status_code: int, event: str, threshold: float | None = None) -> int:
        normalized = status_code & 0b111111
        return normalized ^ cls.change_mask_for_event(normalized, event) ^ cls.balance_mask(normalized, threshold)

    @classmethod
    def evolved_element_labels(cls) -> list[str]:
        return [f"{element}+" for element in cls.ELEMENT_ORDER] + [f"{element}-" for element in cls.ELEMENT_ORDER]

    @classmethod
    def element_polarity(cls, trigram: int) -> str:
        profile = cls.yin_yang_profile_for_bits(trigram, width=3)
        return "+" if profile["yang_count"] >= profile["yin_count"] else "-"

    @classmethod
    def evolved_element_tensor(cls, status_code: int, alpha: float | None = None) -> list[list[float]]:
        polarity = cls.polarity_index(status_code)
        damping_alpha = cls.ELEMENT_DAMPING_ALPHA if alpha is None else alpha
        positive_to_negative = math.exp(damping_alpha * max(0.0, polarity))
        negative_to_positive = math.exp(damping_alpha * max(0.0, -polarity))
        tensor: list[list[float]] = []
        for source_label in cls.evolved_element_labels():
            source_element, source_polarity = source_label[:-1], source_label[-1]
            row = []
            for target_label in cls.evolved_element_labels():
                target_element, target_polarity = target_label[:-1], target_label[-1]
                coefficient = cls.ELEMENT_EXECUTION_BANDWIDTH[(source_element, target_element)]
                if source_polarity == "+" and target_polarity == "-":
                    coefficient *= positive_to_negative
                elif source_polarity == "-" and target_polarity == "+":
                    coefficient *= negative_to_positive
                row.append(coefficient)
            tensor.append(row)
        return tensor

    @classmethod
    def evolved_element_modulation(cls, status_code: int) -> dict[str, float | str]:
        normalized = status_code & 0b111111
        inner = normalized & 0b111
        outer = (normalized >> 3) & 0b111
        outer_label = f"{cls.element_for_trigram(outer)}{cls.element_polarity(outer)}"
        inner_label = f"{cls.element_for_trigram(inner)}{cls.element_polarity(inner)}"
        labels = cls.evolved_element_labels()
        tensor = cls.evolved_element_tensor(normalized)
        return {
            "outer_label": outer_label,
            "inner_label": inner_label,
            "coefficient": tensor[labels.index(outer_label)][labels.index(inner_label)],
            "polarity_index": cls.polarity_index(normalized),
        }

    @classmethod
    def global_entropy(cls, status_codes: list[int]) -> dict[str, float | str]:
        if not status_codes:
            return {"p1": 0.0, "p0": 1.0, "entropy": 0.0, "polarity_index": -1.0, "polarity_state": "low_entropy_negative"}
        total_bits = 6 * len(status_codes)
        yang_count = sum((status_code & 0b111111).bit_count() for status_code in status_codes)
        p1 = yang_count / total_bits
        p0 = 1 - p1
        polarity_index = (yang_count - (total_bits / 2)) / (total_bits / 2)

        def term(probability: float) -> float:
            return 0.0 if probability == 0.0 else probability * math.log2(probability)

        entropy = max(0.0, -(term(p0) + term(p1)))
        if entropy >= cls.ENTROPY_THRESHOLD:
            polarity_state = "entropy_balanced"
        elif polarity_index > 0:
            polarity_state = "low_entropy_positive"
        elif polarity_index < 0:
            polarity_state = "low_entropy_negative"
        else:
            polarity_state = "low_entropy_neutral"
        return {
            "p1": p1,
            "p0": p0,
            "entropy": entropy,
            "polarity_index": polarity_index,
            "polarity_state": polarity_state,
        }

    @classmethod
    def entropy_regulated_status(cls, status_codes: list[int]) -> dict[str, float | int | str]:
        entropy = cls.global_entropy(status_codes)
        if entropy["entropy"] < cls.ENTROPY_THRESHOLD:
            if entropy["polarity_index"] > 0:
                return {
                    "status_code": cls.aggregate_status(status_codes),
                    "decision": "accept_positive_polarity",
                    "entropy": entropy["entropy"],
                    "threshold": cls.ENTROPY_THRESHOLD,
                }
            return {
                "status_code": cls.ROLLBACK_STATUS,
                "decision": "rollback_negative_polarity",
                "reason": "entropy_negative_polarity_rollback",
                "entropy": entropy["entropy"],
                "threshold": cls.ENTROPY_THRESHOLD,
            }
        return {
            "status_code": cls.aggregate_status(status_codes),
            "decision": "accept",
            "entropy": entropy["entropy"],
            "threshold": cls.ENTROPY_THRESHOLD,
        }

    @classmethod
    def state_distribution_entropy(cls, status_codes: list[int]) -> dict[str, float | int | dict[int, float]]:
        if not status_codes:
            return {"entropy": 0.0, "max_entropy": 0.0, "unique_state_count": 0, "distribution": {}}
        counts: dict[int, int] = {}
        for status_code in status_codes:
            normalized = status_code & 0b111111
            counts[normalized] = counts.get(normalized, 0) + 1
        total = len(status_codes)
        distribution = {status_code: count / total for status_code, count in sorted(counts.items())}
        entropy = -sum(probability * math.log2(probability) for probability in distribution.values())
        max_entropy = math.log2(len(distribution)) if distribution else 0.0
        return {
            "entropy": entropy,
            "max_entropy": max_entropy,
            "unique_state_count": len(distribution),
            "distribution": distribution,
        }

    @classmethod
    def transition_graph(cls) -> dict[int, int]:
        return {
            status_code: cls.transition(status_code).status_code & 0b111111
            for status_code in range(64)
        }

    @classmethod
    def attractor_analysis(cls) -> dict[str, int | list[list[int]] | list[int]]:
        graph = cls.transition_graph()
        attractors: list[list[int]] = []
        classified: set[int] = set()
        seen_cycles: set[tuple[int, ...]] = set()
        for start in range(64):
            path: list[int] = []
            positions: dict[int, int] = {}
            current = start
            while current not in positions and current not in classified:
                positions[current] = len(path)
                path.append(current)
                current = graph[current]
            if current in positions:
                cycle = path[positions[current]:]
                canonical = min(tuple(cycle[index:] + cycle[:index]) for index in range(len(cycle)))
                if canonical not in seen_cycles:
                    seen_cycles.add(canonical)
                    attractors.append(list(canonical))
            classified.update(path)
        return {
            "state_count": 64,
            "attractors": sorted(attractors, key=lambda cycle: (len(cycle), cycle)),
            "unclassified_states": sorted(set(range(64)) - classified),
        }

    @classmethod
    def stability_analysis(cls) -> dict[str, int | float | dict[int, int]]:
        graph = cls.transition_graph()
        attractors = cls.attractor_analysis()
        steps_to_attractor: dict[int, int] = {}
        for start in range(64):
            current = start
            seen: dict[int, int] = {}
            steps = 0
            while current not in seen:
                seen[current] = steps
                next_state = graph[current]
                if next_state == current:
                    steps_to_attractor[start] = steps
                    break
                current = next_state
                steps += 1
            else:
                steps_to_attractor[start] = seen[current]
            if start not in steps_to_attractor:
                steps_to_attractor[start] = steps

        energy_deltas = [
            cls.lyapunov_energy(graph[status_code]) - cls.lyapunov_energy(status_code)
            for status_code in range(64)
        ]
        return {
            "state_count": 64,
            "limit_cycle_count": len(attractors["attractors"]),
            "nontrivial_limit_cycle_count": sum(1 for cycle in attractors["attractors"] if len(cycle) > 1),
            "unclassified_state_count": len(attractors["unclassified_states"]),
            "steps_to_attractor": steps_to_attractor,
            "max_steps_to_attractor": max(steps_to_attractor.values()) if steps_to_attractor else 0,
            "energy_increase_transition_count": sum(1 for delta in energy_deltas if delta > 0),
            "energy_decrease_transition_count": sum(1 for delta in energy_deltas if delta < 0),
            "energy_flat_transition_count": sum(1 for delta in energy_deltas if delta == 0),
            "min_energy_delta": min(energy_deltas) if energy_deltas else 0.0,
            "max_energy_delta": max(energy_deltas) if energy_deltas else 0.0,
        }

    @staticmethod
    def hamming_distance(left: int, right: int) -> int:
        return ((left ^ right) & 0b111111).bit_count()

    @classmethod
    def topology_certificate(cls) -> dict[str, int | str | dict[int, int]]:
        graph = cls.transition_graph()
        distance_histogram = {distance: 0 for distance in range(7)}
        closed_transition_count = 0
        fixed_point_count = 0
        hypercube_edge_transition_count = 0
        long_jump_transition_count = 0
        for source, target in graph.items():
            if 0 <= target < 64:
                closed_transition_count += 1
            distance = cls.hamming_distance(source, target)
            distance_histogram[distance] += 1
            if distance == 0:
                fixed_point_count += 1
            elif distance == 1:
                hypercube_edge_transition_count += 1
            else:
                long_jump_transition_count += 1
        return {
            "state_space": "Q6",
            "vertex_count": 64,
            "dimension": 6,
            "hypercube_edge_count": 6 * (2 ** 5),
            "transition_count": len(graph),
            "closed_transition_count": closed_transition_count,
            "unclosed_transition_count": len(graph) - closed_transition_count,
            "fixed_point_count": fixed_point_count,
            "hypercube_edge_transition_count": hypercube_edge_transition_count,
            "long_jump_transition_count": long_jump_transition_count,
            "hamming_distance_histogram": distance_histogram,
        }

    @classmethod
    def lyapunov_certificate(cls) -> dict[str, bool | int | float | list[dict[str, float | int]]]:
        graph = cls.transition_graph()
        deltas: list[float] = []
        violating_transitions: list[dict[str, float | int]] = []
        for source, target in graph.items():
            source_energy = cls.lyapunov_energy(source)
            target_energy = cls.lyapunov_energy(target)
            delta = target_energy - source_energy
            deltas.append(delta)
            if delta > 0:
                violating_transitions.append(
                    {
                        "source": source,
                        "target": target,
                        "source_energy": source_energy,
                        "target_energy": target_energy,
                        "delta": delta,
                    }
                )
        return {
            "state_count": len(graph),
            "nonincreasing": not violating_transitions,
            "energy_increase_transition_count": len(violating_transitions),
            "energy_decrease_transition_count": sum(1 for delta in deltas if delta < 0),
            "energy_flat_transition_count": sum(1 for delta in deltas if delta == 0),
            "min_energy_delta": min(deltas) if deltas else 0.0,
            "max_energy_delta": max(deltas) if deltas else 0.0,
            "violating_transitions": violating_transitions,
        }

    @classmethod
    def entropy_gate_certificate(cls, status_codes: list[int]) -> dict[str, float | int | str]:
        distribution = cls.state_distribution_entropy(status_codes)
        max_entropy = float(distribution["max_entropy"])
        entropy = float(distribution["entropy"])
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
        sample_count = len(status_codes)
        unique_state_count = int(distribution["unique_state_count"])
        transition_actions = [
            cls.transition(status_code).action
            for status_code in status_codes
        ]
        halt_count = sum(1 for action in transition_actions if action == "halt")
        checkpoint_count = sum(1 for action in transition_actions if action == "checkpoint")
        if sample_count == 0:
            decision = "observe"
            reason = "empty_sequence"
        elif normalized_entropy <= cls.ENTROPY_THRESHOLD and halt_count > 0:
            decision = "sovereignty_halt"
            reason = "low_entropy_repeated_halt"
        elif normalized_entropy <= cls.ENTROPY_THRESHOLD and checkpoint_count > 0:
            decision = "checkpoint"
            reason = "low_entropy_repeated_checkpoint"
        elif normalized_entropy > cls.ENTROPY_THRESHOLD:
            decision = "observe"
            reason = "high_entropy_exploration"
        else:
            decision = "continue"
            reason = "low_entropy_stable"
        return {
            "sample_count": sample_count,
            "unique_state_count": unique_state_count,
            "entropy": entropy,
            "max_entropy": max_entropy,
            "normalized_entropy": normalized_entropy,
            "threshold": cls.ENTROPY_THRESHOLD,
            "halt_count": halt_count,
            "checkpoint_count": checkpoint_count,
            "decision": decision,
            "reason": reason,
        }

    @classmethod
    def totality_samples(cls) -> list[dict[str, str | bool | None]]:
        return [
            {"kind": "runtime", "status": "completed", "reason": None, "dangerous": False},
            {"kind": "runtime", "status": "skipped", "reason": "resumed_asset_ready", "dangerous": False},
            {"kind": "runtime", "status": "halted", "reason": "sovereignty_breach", "dangerous": True},
            {"kind": "runtime", "status": "denied", "reason": "permission_denied", "dangerous": True},
            {"kind": "runtime", "status": "halted", "reason": "invalid_intent", "dangerous": True},
            {"kind": "runtime", "status": "halted", "reason": "self_audit_check_failed", "dangerous": True},
            {"kind": "runtime", "status": "halted", "reason": "http_timeout", "dangerous": True},
            {"kind": "runtime", "status": "halted", "reason": "action_exception", "dangerous": True},
            {"kind": "runtime", "status": "halted", "reason": "run_exception", "dangerous": True},
            {"kind": "runtime", "status": "unknown", "reason": "malformed_input", "dangerous": True},
            {"kind": "runtime", "status": "unknown", "reason": "oversized_input", "dangerous": True},
            {"kind": "runtime", "status": "halted", "reason": "resource_budget_exceeded", "dangerous": True},
            {"kind": "resume", "status": "ready", "reason": None, "dangerous": False},
            {"kind": "resume", "status": "ignored", "reason": "path_outside_workspace", "dangerous": True},
            {"kind": "resume", "status": "ignored", "reason": "missing_file", "dangerous": True},
            {"kind": "resume", "status": "ignored", "reason": "sha256_mismatch", "dangerous": True},
            {"kind": "resume", "status": "ignored", "reason": "malformed_manifest", "dangerous": True},
            {"kind": "resume", "status": "ignored", "reason": "invalid_checkpoint_evidence", "dangerous": True},
            {"kind": "resume", "status": "ignored", "reason": "checkpoint_sha_mismatch", "dangerous": True},
        ]

    @classmethod
    def classify_known_input(cls, sample: dict[str, str | bool | None]) -> int:
        kind = sample["kind"]
        status = str(sample["status"])
        reason = sample["reason"]
        reason_value = str(reason) if reason is not None else None
        if kind == "resume":
            return cls.classify_resume_audit(status, reason_value)
        return cls.classify_outcome(status, reason_value)

    @classmethod
    def totality_certificate(cls) -> dict[str, bool | int | str | list[str]]:
        samples = cls.totality_samples()
        mapped = [cls.classify_known_input(sample) for sample in samples]
        unmapped_count = sum(1 for status_code in mapped if not 0 <= status_code < 64)
        return {
            "domain": "known_runtime_and_resume_inputs",
            "codomain": "Q6",
            "sample_count": len(samples),
            "mapped_count": len(mapped) - unmapped_count,
            "unmapped_count": unmapped_count,
            "total_over_known_inputs": unmapped_count == 0,
            "safe_domain": ["halt", "checkpoint", "discover"],
        }

    @classmethod
    def safety_dominance_certificate(cls) -> dict[str, bool | int | list[dict[str, int | str | bool | None]] | dict[str, int]]:
        unsafe_pass_through_samples: list[dict[str, int | str | bool | None]] = []
        histogram: dict[str, int] = {}
        dangerous_sample_count = 0
        for sample in cls.totality_samples():
            if not bool(sample["dangerous"]):
                continue
            dangerous_sample_count += 1
            status_code = cls.classify_known_input(sample)
            transition = cls.transition(status_code)
            histogram[transition.action] = histogram.get(transition.action, 0) + 1
            if transition.action in {"continue", "accelerate", "activate"}:
                unsafe_pass_through_samples.append(
                    {
                        "kind": sample["kind"],
                        "status": sample["status"],
                        "reason": sample["reason"],
                        "status_code": status_code,
                        "transition_action": transition.action,
                        "transition_reason": transition.reason,
                    }
                )
        return {
            "dangerous_sample_count": dangerous_sample_count,
            "dangerous_action_histogram": histogram,
            "unsafe_pass_through_count": len(unsafe_pass_through_samples),
            "unsafe_pass_through_samples": unsafe_pass_through_samples,
            "safe": not unsafe_pass_through_samples,
        }

    @classmethod
    def collision_risk_certificate(cls) -> dict[str, bool | int | list[dict[str, int | str | list[str]]]]:
        grouped: dict[int, list[dict[str, str | bool | None]]] = {}
        for sample in cls.totality_samples():
            status_code = cls.classify_known_input(sample)
            grouped.setdefault(status_code, []).append(sample)
        unsafe_collisions: list[dict[str, int | str | list[str]]] = []
        for status_code, samples in grouped.items():
            if len(samples) < 2:
                continue
            has_dangerous = any(bool(sample["dangerous"]) for sample in samples)
            has_nondangerous = any(not bool(sample["dangerous"]) for sample in samples)
            transition = cls.transition(status_code)
            if has_dangerous and has_nondangerous and transition.action in {"continue", "accelerate", "activate"}:
                unsafe_collisions.append(
                    {
                        "status_code": status_code,
                        "transition_action": transition.action,
                        "sample_reasons": [
                            str(sample["reason"]) if sample["reason"] is not None else str(sample["status"])
                            for sample in samples
                        ],
                    }
                )
        return {
            "sample_count": len(cls.totality_samples()),
            "collision_state_count": sum(1 for samples in grouped.values() if len(samples) > 1),
            "unsafe_collision_count": len(unsafe_collisions),
            "unsafe_collisions": unsafe_collisions,
            "safe": not unsafe_collisions,
        }

    @classmethod
    def lyapunov_energy(cls, status_code: int) -> float:
        normalized = status_code & 0b111111
        profile = cls.yin_yang_profile(normalized)
        balance_penalty = abs(float(profile["yang_count"]) - 3.0) / 3.0
        transition = cls.transition(normalized)
        action_penalties = {
            "continue": 0.0,
            "recover": 0.0,
            "accelerate": 0.1,
            "activate": 0.2,
            "cooldown": 0.35,
            "throttle": 0.45,
            "prune": 0.55,
            "checkpoint": 0.75,
            "discover": 0.85,
            "halt": 1.0,
        }
        bandwidth_penalty = 1.0 - cls.execution_bandwidth(normalized)
        return balance_penalty + action_penalties.get(transition.action, 0.5) + bandwidth_penalty

    @classmethod
    def hysteresis_gate(cls, value: float, previous: int, low: float, high: float) -> int:
        if low >= high:
            raise ValueError("low must be less than high")
        previous_bit = 1 if previous else 0
        if value <= low:
            return 0
        if value >= high:
            return 1
        return previous_bit

    @classmethod
    def element_dynamics(cls, status_code: int) -> dict[str, str]:
        normalized = status_code & 0b111111
        inner = normalized & 0b111
        outer = (normalized >> 3) & 0b111
        outer_element = cls.element_for_trigram(outer)
        inner_element = cls.element_for_trigram(inner)
        relation = cls.element_relation(outer_element, inner_element)
        cross_relation = cls.element_cross_relation(outer_element, inner_element)
        pressure = cls.yin_yang_cross_profile(normalized)["pressure"]
        if cross_relation == "controls" and outer_element == "fire" and inner_element == "metal":
            modulation = "hard_control"
        elif cross_relation == "generates" and outer_element == "water" and inner_element == "wood":
            modulation = "recovery_seed"
        elif cross_relation == "controls" and outer_element == "water" and inner_element == "fire":
            modulation = "quench"
        elif cross_relation == "controls" and outer_element == "metal" and inner_element == "wood":
            modulation = "prune"
        elif cross_relation == "generates" and outer_element == "wood" and inner_element == "fire":
            modulation = "fuel"
        elif cross_relation == "controls" and outer_element == "earth" and inner_element == "water":
            modulation = "dam"
        elif cross_relation == "controls" and outer_element == "wood" and inner_element == "earth":
            modulation = "break_ground"
        else:
            modulation = "normal"
        return {
            "outer_element": outer_element,
            "inner_element": inner_element,
            "relation": relation,
            "cross_relation": cross_relation,
            "yin_yang_pressure": str(pressure),
            "modulation": modulation,
        }

    @classmethod
    def cross_cutting_profile(cls, status_code: int) -> dict:
        normalized = status_code & 0b111111
        inner = normalized & 0b111
        outer = (normalized >> 3) & 0b111
        outer_element = cls.element_for_trigram(outer)
        inner_element = cls.element_for_trigram(inner)
        dynamics = cls.element_dynamics(normalized)
        transition = cls.transition(normalized)
        runtime_action, runtime_reason = cls.runtime_relation_policy(dynamics["cross_relation"], dynamics["modulation"])
        if dynamics["modulation"] == "recovery_seed" and transition.action == "checkpoint":
            runtime_action, runtime_reason = transition.action, transition.reason
        dispatch_decision = cls.dispatch_decision(transition)
        return {
            "status_code": normalized,
            "binary": format(normalized, "06b"),
            "math": {
                "liangyi": list(cls.liangyi_values()),
                "state_space_sizes": {
                    "liangyi": 1 << 1,
                    "sixiang": 1 << 2,
                    "bagua": 1 << 3,
                    "hexagram": 1 << 6,
                },
            },
            "dimension": cls.dimension_profile(6),
            "triadic": cls.triadic_profile(normalized),
            "mutation": None,
            "nuclear": cls.nuclear_profile(normalized),
            "outer_trigram": outer,
            "inner_trigram": inner,
            "lines": cls.line_records(normalized),
            "liangyi": cls.liangyi_bits(normalized),
            "outer_trigram_record": cls.trigram_record(normalized, "outer"),
            "inner_trigram_record": cls.trigram_record(normalized, "inner"),
            "trigram_records": cls.trigram_records(),
            "outer_element": outer_element,
            "inner_element": inner_element,
            "element_records": cls.element_records(),
            "element_matrix": {f"{source}->{target}": relation for (source, target), relation in cls.element_matrix().items()},
            "element_relation": cls.element_relation(outer_element, inner_element),
            "element_dynamics": dynamics,
            "runtime_policy": {
                "action": runtime_action,
                "reason": runtime_reason,
            },
            "execution_bandwidth": cls.execution_bandwidth(normalized),
            "evolved_element_modulation": cls.evolved_element_modulation(normalized),
            "harmony": cls.harmony_score(normalized),
            "yin_yang": cls.yin_yang_cross_profile(normalized),
            "four_symbols": cls.four_symbols(normalized),
            "overlapping_four_symbols": cls.overlapping_four_symbols(normalized),
            "four_symbol_balance": cls.four_symbol_balance_vector(normalized),
            "transition": {
                "status_code": transition.status_code,
                "action": transition.action,
                "reason": transition.reason,
            },
            "dispatch_decision": dispatch_decision,
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
    def mutate_lines(cls, status_code: int, line_indexes) -> int:
        normalized = status_code & 0b111111
        mask = 0
        for line_index in sorted(set(line_indexes)):
            if line_index < 0 or line_index > 5:
                raise ValueError(f"line_index must be between 0 and 5: {line_index!r}")
            mask |= 1 << line_index
        return normalized ^ mask

    @classmethod
    def changed_lines(cls, before: int, after: int) -> list[int]:
        change_mask = (before ^ after) & 0b111111
        return [line_index for line_index in range(6) if change_mask & (1 << line_index)]

    @classmethod
    def mutation_profile(cls, before: int, after: int) -> dict[str, int | list[int] | list[str]]:
        normalized_before = before & 0b111111
        normalized_after = after & 0b111111
        changed = cls.changed_lines(normalized_before, normalized_after)
        changed_bands = [
            name
            for name, _role, line_indexes in cls.TRIADIC_BANDS
            if any(line_index in line_indexes for line_index in changed)
        ]
        return {
            "before": normalized_before,
            "after": normalized_after,
            "changed_lines": changed,
            "change_count": len(changed),
            "changed_bands": changed_bands,
        }

    @classmethod
    def nuclear_hexagram(cls, status_code: int) -> int:
        bits = cls.bits_for_state(status_code & 0b111111, width=6)
        return cls.state_for_bits([bits[1], bits[2], bits[3], bits[2], bits[3], bits[4]])

    @classmethod
    def nuclear_profile(cls, status_code: int) -> dict[str, int | str]:
        nuclear = cls.nuclear_hexagram(status_code)
        inner = nuclear & 0b111
        outer = (nuclear >> 3) & 0b111
        outer_element = cls.element_for_trigram(outer)
        inner_element = cls.element_for_trigram(inner)
        transition = cls.transition(nuclear)
        return {
            "status_code": nuclear,
            "binary": format(nuclear, "06b"),
            "inner_trigram": inner,
            "outer_trigram": outer,
            "outer_element": outer_element,
            "inner_element": inner_element,
            "element_relation": cls.element_cross_relation(outer_element, inner_element),
            "transition_action": transition.action,
            "transition_reason": transition.reason,
        }

    @classmethod
    def target_status_for_event(cls, event: str) -> int:
        if event in {"completed", "write_completed", "patch_completed"}:
            return cls.compute_status(cls.QIAN, cls.QIAN)
        if event in {"skipped", "resumed_asset_ready"}:
            return cls.compute_status(cls.QIAN, cls.DUI)
        if event in {"http_timeout", "network_timeout"}:
            return cls.compute_status(cls.KAN, cls.ZHEN)
        if event in {"action_exception", "run_exception", "local_executor_fault"}:
            return cls.compute_status(cls.GEN, cls.KUN)
        if event in {"sovereignty_breach", "permission_denied", "invalid_intent"}:
            return cls.compute_status(cls.LI, cls.KUN)
        return cls.compute_status(cls.KUN, cls.KUN)

    @classmethod
    def change_mask_for_event(cls, status_code: int, event: str) -> int:
        return (status_code & 0b111111) ^ cls.target_status_for_event(event)

    @classmethod
    def apply_event(cls, status_code: int, event: str) -> int:
        return (status_code & 0b111111) ^ cls.change_mask_for_event(status_code, event)

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
        if all(isinstance(value, int) for value in (requested_count, completed_count, skipped_count, failed_count)):
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
