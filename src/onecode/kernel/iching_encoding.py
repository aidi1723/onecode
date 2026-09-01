from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType


RULE_SCHEMA_V1 = "onecode-iching-v1"
RULE_SCHEMA_V2 = "onecode-iching-v2"
ACTIVE_RULE_SCHEMA = RULE_SCHEMA_V2

LEGACY_TRIGRAMS: Mapping[str, int] = MappingProxyType(
    {
        "kun": 0b000,
        "zhen": 0b001,
        "kan": 0b010,
        "dui": 0b011,
        "gen": 0b100,
        "xun": 0b101,
        "li": 0b110,
        "qian": 0b111,
    }
)

CANONICAL_TRIGRAMS: Mapping[str, int] = MappingProxyType(
    {
        "kun": 0b000,
        "zhen": 0b001,
        "kan": 0b010,
        "dui": 0b011,
        "gen": 0b100,
        "li": 0b101,
        "xun": 0b110,
        "qian": 0b111,
    }
)

CANONICAL_LINE_PATTERNS: Mapping[str, tuple[int, int, int]] = MappingProxyType(
    {
        "kun": (0, 0, 0),
        "zhen": (1, 0, 0),
        "kan": (0, 1, 0),
        "dui": (1, 1, 0),
        "gen": (0, 0, 1),
        "li": (1, 0, 1),
        "xun": (0, 1, 1),
        "qian": (1, 1, 1),
    }
)

CANONICAL_COMPLEMENT_PAIRS = (
    ("kun", "qian"),
    ("zhen", "xun"),
    ("kan", "li"),
    ("dui", "gen"),
)


def trigram_table(schema: str) -> Mapping[str, int]:
    if schema == RULE_SCHEMA_V1:
        return LEGACY_TRIGRAMS
    if schema == RULE_SCHEMA_V2:
        return CANONICAL_TRIGRAMS
    raise ValueError(f"unknown I Ching rule schema: {schema!r}")


def normalize_rule_schema(schema: object) -> str:
    if schema is None:
        return RULE_SCHEMA_V1
    if not isinstance(schema, str):
        raise ValueError(f"I Ching rule schema must be a string: {schema!r}")
    trigram_table(schema)
    return schema


def validate_trigram(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0b111:
        raise ValueError(f"trigram must be an integer between 0 and 7: {value!r}")
    return value


def validate_status(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0b111111:
        raise ValueError(f"status must be an integer between 0 and 63: {value!r}")
    return value


def convert_trigram(value: int, source_schema: str, target_schema: str) -> int:
    source = trigram_table(source_schema)
    target = trigram_table(target_schema)
    name_by_value = {bits: name for name, bits in source.items()}
    return target[name_by_value[validate_trigram(value)]]


def convert_status(value: int, source_schema: str, target_schema: str) -> int:
    status = validate_status(value)
    inner = convert_trigram(status & 0b111, source_schema, target_schema)
    outer = convert_trigram((status >> 3) & 0b111, source_schema, target_schema)
    return (outer << 3) | inner


def canonical_encoding_certificate() -> dict[str, object]:
    invalid_line_patterns = []
    for name, expected_lines in CANONICAL_LINE_PATTERNS.items():
        bits = CANONICAL_TRIGRAMS[name]
        actual_lines = tuple((bits >> line_index) & 1 for line_index in range(3))
        if actual_lines != expected_lines:
            invalid_line_patterns.append(
                {
                    "name": name,
                    "bits": bits,
                    "expected_lines": list(expected_lines),
                    "actual_lines": list(actual_lines),
                }
            )

    invalid_complement_pairs = []
    for left_name, right_name in CANONICAL_COMPLEMENT_PAIRS:
        complement = CANONICAL_TRIGRAMS[left_name] ^ 0b111
        if complement != CANONICAL_TRIGRAMS[right_name]:
            invalid_complement_pairs.append(
                {
                    "left": left_name,
                    "right": right_name,
                    "actual": complement,
                    "expected": CANONICAL_TRIGRAMS[right_name],
                }
            )

    return {
        "schema": RULE_SCHEMA_V2,
        "trigram_count": len(CANONICAL_TRIGRAMS),
        "complement_pairs": [list(pair) for pair in CANONICAL_COMPLEMENT_PAIRS],
        "invalid_line_patterns": invalid_line_patterns,
        "invalid_complement_pairs": invalid_complement_pairs,
        "valid": not invalid_line_patterns and not invalid_complement_pairs,
    }
