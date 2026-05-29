from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DictionaryEntry:
    code: str
    name: str
    definition: str
    routing_target: str
    tool_policy: dict[str, str]
    model_policy: dict[str, Any]
    fallback: dict[str, Any]
    raw: dict[str, Any]


def load_dictionary(path: str | Path) -> dict[str, Any]:
    dictionary_path = Path(path)
    with dictionary_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Dictionary root must be an object")
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Dictionary must contain a non-empty entries list")
    return data


def lookup_entry(dictionary: dict[str, Any], code: str) -> DictionaryEntry:
    for entry in dictionary["entries"]:
        if entry.get("code") == code:
            return DictionaryEntry(
                code=entry["code"],
                name=entry["name"],
                definition=entry["definition"],
                routing_target=entry["routing_target"],
                tool_policy=entry["tool_policy"],
                model_policy=entry["model_policy"],
                fallback=entry["fallback"],
                raw=entry,
            )
    raise KeyError(f"Unknown execution code: {code}")
