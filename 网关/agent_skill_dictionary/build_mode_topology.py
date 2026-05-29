from __future__ import annotations


AXIS_NAMES = ("tool_axis", "context_axis", "boundary_axis")


def hamming_distance(source: str, target: str) -> int:
    source = _validate_hexagram(source)
    target = _validate_hexagram(target)
    return sum(1 for left, right in zip(source, target) if left != right)


def is_edge_transition(source: str, target: str) -> bool:
    return hamming_distance(source, target) <= 1


def transition_axes(source: str, target: str) -> tuple[str, ...]:
    source = _validate_hexagram(source)
    target = _validate_hexagram(target)
    return tuple(name for name, left, right in zip(AXIS_NAMES, source, target) if left != right)


def edge_walk_path(source: str, target: str) -> tuple[str, ...]:
    source = _validate_hexagram(source)
    target = _validate_hexagram(target)
    current = list(source)
    path = [source]
    for index, desired in enumerate(target):
        if current[index] == desired:
            continue
        current[index] = desired
        path.append("".join(current))
    return tuple(path)


def _validate_hexagram(value: str) -> str:
    if len(value) != 3 or any(char not in {"0", "1"} for char in value):
        raise ValueError(f"invalid 3-bit hexagram: {value!r}")
    return value
