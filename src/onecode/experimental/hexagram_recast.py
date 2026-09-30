"""A review may name another hexagram. It may not name an action."""

from onecode.kernel.project_gateway import project_gateway


def parse_hexagram(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError("recast must be one of the 64 hexagrams")
    if isinstance(value, int):
        if not 0 <= value <= 63:
            raise ValueError("recast must be one of the 64 hexagrams")
        return value
    if len(value) == 6 and set(value) <= {"0", "1"}:
        return int(value, 2)
    raise ValueError("recast must be one of the 64 hexagrams")


def apply_hexagram_recast(decision: dict, raw: object) -> dict:
    if not decision.get("observe"):
        return decision
    try:
        status_code = parse_hexagram(raw)
    except ValueError:
        rejected = dict(decision)
        rejected["recast_rejected"] = True
        return rejected
    facts = decision["facts"]
    projected = project_gateway(status_code, facts)
    updated = dict(decision)
    updated.update(
        {
            "status_code": status_code,
            "yizijue_state": format(status_code, "06b"),
            "action": projected,
            "projected_action": projected,
            "observe": False,
            "abstained": False,
            "recast_from": decision.get("yizijue_state"),
            "recast_rejected": False,
            "reason": "hexagram_recast",
        }
    )
    return updated
