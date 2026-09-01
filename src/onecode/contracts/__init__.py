from __future__ import annotations

import json
from importlib.resources import files
from typing import Any


def _load_json_object(name: str) -> dict[str, Any]:
    value = json.loads(files(__package__).joinpath(name).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"invalid_contract_asset:{name}")
    return value


def load_shell_projection_v4_schema() -> dict[str, Any]:
    return _load_json_object("shell_projection_v4_schema.json")


def load_shell_projection_v4_cases() -> list[dict[str, Any]]:
    name = "shell_projection_v4_cases.json"
    value = json.loads(files(__package__).joinpath(name).read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError(f"invalid_contract_asset:{name}")
    cases: list[dict[str, Any]] = []
    for case in value:
        if (
            not isinstance(case, dict)
            or not isinstance(case.get("name"), str)
            or not case["name"].strip()
            or not isinstance(case.get("input"), dict)
            or not isinstance(case.get("expected"), dict)
        ):
            raise ValueError(f"invalid_contract_asset:{name}")
        cases.append(case)
    return cases
