from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4


LEDGER_PATH = Path(__file__).with_name("ledger.json")


@dataclass(frozen=True)
class LedgerEntry:
    entry_id: str
    factory: str
    warehouse: str
    sku: str
    quantity: int
    unit: str
    status: str


def load_entries(path: Path = LEDGER_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def append_entry(factory: str, warehouse: str, sku: str, quantity: int, unit: str) -> LedgerEntry:
    if quantity <= 0:
        raise ValueError("quantity must be positive")

    entry = LedgerEntry(
        entry_id=uuid4().hex,
        factory=factory,
        warehouse=warehouse,
        sku=sku,
        quantity=quantity,
        unit=unit,
        status="pending_sync",
    )
    entries = load_entries()
    entries.append(asdict(entry))
    LEDGER_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    return entry


def mark_synced(entry_id: str) -> bool:
    entries = load_entries()
    updated = False
    for item in entries:
        if item.get("entry_id") == entry_id:
            item["status"] = "synced"
            updated = True
    LEDGER_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    return updated
