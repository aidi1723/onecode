"""One cast of six Da Yan lines, then the kernel's changed hexagram.

Line values stay in {6, 7, 8, 9}. Young lines are static. Old lines move.
The changed hexagram is ``mutate_lines`` of the primary hexagram. It is one of
the existing sixty-four, not an extra class.
"""

from onecode.kernel.hexagram import IchingKernel

LINE_VALUES = (6, 7, 8, 9)
YANG_VALUES = {7, 9}
MOVING_VALUES = {6, 9}
LINE_NAMES = ("初爻", "二爻", "三爻", "四爻", "五爻", "上爻")


def motion_token_indexes(pieces: list[str]) -> list[int] | None:
    """Locate each line's 阴 or 阳 token, in bottom-to-top order."""
    spans = []
    cursor = 0
    for piece in pieces:
        spans.append(cursor)
        cursor += len(piece)
    full = "".join(pieces)
    indexes = []
    for name in LINE_NAMES:
        start = full.find(name)
        if start < 0:
            return None
        window_start = start + len(name)
        window = full[window_start : window_start + 12]
        positions = [window.find(mark) for mark in ("阴", "阳")]
        positions = [pos for pos in positions if pos >= 0]
        if not positions:
            return None
        value_at = window_start + min(positions)
        indexes.append(max(index for index, span in enumerate(spans) if span <= value_at))
    return indexes


def cast_from_lines(values: list[int]) -> dict[str, object]:
    if len(values) != 6 or any(value not in LINE_VALUES for value in values):
        raise ValueError("a cast needs six line values in {6, 7, 8, 9}")
    before = 0
    moving: list[int] = []
    for index, value in enumerate(values):
        if value in YANG_VALUES:
            before |= 1 << index
        if value in MOVING_VALUES:
            moving.append(index)
    after = IchingKernel.mutate_lines(before, moving)
    return {
        "values": list(values),
        "before": before,
        "after": after,
        "moving": moving,
    }
