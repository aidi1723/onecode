from __future__ import annotations



from typing import ClassVar, cast, Any

class IchingProfileMixin:
    DIMENSION_LABELS: ClassVar[dict[int, str]]
    TRIADIC_BANDS: ClassVar[Any]
    RULE_LAYERS: ClassVar[Any]
    FOUR_SYMBOLS: ClassVar[dict[int, str]]
    DAYAN_PROBABILITIES: ClassVar[dict[int, float]]
    FOUR_SYMBOL_RUNTIME_SEMANTICS: ClassVar[dict[str, str]]
    LINE_POSITION_NAMES: ClassVar[Any]
    RESPONSE_PAIRS: ClassVar[Any]
    TRIGRAM_NAMES: ClassVar[dict[int, str]]
    TRIGRAM_VIRTUES: ClassVar[dict[int, tuple[str, str | int]]]
    TRIGRAM_ELEMENTS: ClassVar[dict[int, str]]
    ELEMENT_GENERATION_ORDER: ClassVar[Any]
    GENERATES: ClassVar[dict[str, str]]
    CONTROLS: ClassVar[dict[str, str]]
    HARMONY_RELATION_SCORES: ClassVar[dict[str, int]]
    RUNTIME_CONTROL_MODULATION_POLICY: ClassVar[dict[str, tuple[str, str | None]]]
    RUNTIME_RELATION_POLICY: ClassVar[dict[str, tuple[str, str | None]]]
    ELEMENT_EXECUTION_BANDWIDTH: ClassVar[dict[tuple[str, str], float]]
    KUN: ClassVar[int]

    @classmethod
    def balance_mask(cls, status_code: int, threshold: float | None = None) -> int: raise NotImplementedError

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
    def dayan_line_probability(cls, value: int) -> float:
        """Return the classical Da Yan stalk probability for line value in {6, 7, 8, 9}."""
        if value not in cls.DAYAN_PROBABILITIES:
            raise ValueError(f"Invalid Da Yan line value: {value!r}, must be in {{6, 7, 8, 9}}")
        return cls.DAYAN_PROBABILITIES[value]
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
        windows: list[dict[str, int | str]] = []
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
    def line_position_profile(cls, status_code: int) -> dict[str, object]:
        normalized = status_code & 0b111111
        lines = []
        for line_index, position_name in enumerate(cls.LINE_POSITION_NAMES):
            value = (normalized >> line_index) & 1
            expected_value = 1 if line_index % 2 == 0 else 0
            central = line_index in {1, 4}
            proper = value == expected_value
            lines.append(
                {
                    "line_index": line_index,
                    "position_name": position_name,
                    "value": value,
                    "polarity": "yang" if value else "yin",
                    "expected_polarity": "yang" if expected_value else "yin",
                    "proper": proper,
                    "central": central,
                    "central_and_proper": central and proper,
                }
            )
        central_lines = [int(cast(int, line["line_index"])) for line in lines if line["central"]]
        central_proper_lines = [int(cast(int, line["line_index"])) for line in lines if line["central_and_proper"]]
        return {
            "lines": lines,
            "proper_line_count": sum(bool(line["proper"]) for line in lines),
            "central_lines": central_lines,
            "central_proper_lines": central_proper_lines,
            "middle_alignment": central_proper_lines == central_lines,
        }
    @classmethod
    def correspondence_profile(cls, status_code: int) -> dict[str, object]:
        normalized = status_code & 0b111111
        values = [(normalized >> line_index) & 1 for line_index in range(6)]
        response_pairs = [
            {
                "line_indexes": [inner_index, outer_index],
                "polarities": ["yang" if values[inner_index] else "yin", "yang" if values[outer_index] else "yin"],
                "responsive": values[inner_index] != values[outer_index],
            }
            for inner_index, outer_index in cls.RESPONSE_PAIRS
        ]
        adjacent_pairs = [
            {
                "line_indexes": [line_index, line_index + 1],
                "same_polarity": values[line_index] == values[line_index + 1],
                "responsive": values[line_index] != values[line_index + 1],
            }
            for line_index in range(5)
        ]
        return {
            "response_pairs": response_pairs,
            "responsive_pair_count": sum(bool(pair["responsive"]) for pair in response_pairs),
            "adjacent_pairs": adjacent_pairs,
            "third_fourth_boundary": adjacent_pairs[2],
        }
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
    def trigram_virtue_record(cls, trigram: int) -> dict[str, str | int]:
        normalized = trigram & 0b111
        virtue, runtime_tendency = cls.TRIGRAM_VIRTUES[normalized]
        return {
            "trigram": normalized,
            "name": cls.TRIGRAM_NAMES[normalized],
            "virtue": virtue,
            "runtime_tendency": runtime_tendency,
        }
    @classmethod
    def trigram_virtue_records(cls) -> dict[int, dict[str, str | int]]:
        return {trigram: cls.trigram_virtue_record(trigram) for trigram in range(8)}
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
            "pressure": cls.balance_pressure(cast(str, global_profile["balance"])),
            "polarity_index": cls.polarity_index(normalized),
            "balance_mask": cls.balance_mask(normalized),
            "lines": lines,
            "four_symbol_windows": [
                cast(dict[str, int | str], {"pair_index": pair_index})
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
