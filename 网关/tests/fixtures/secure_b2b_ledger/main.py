from __future__ import annotations

from fastapi import FastAPI

from ledger import append_entry, load_entries
from sync_node import sync_inventory


app = FastAPI(title="Secure B2B Ledger")


@app.get("/ledger")
def list_ledger() -> list[dict[str, object]]:
    return load_entries()


@app.post("/orders")
def create_order(factory: str, warehouse: str, sku: str, quantity: int, unit: str = "ton") -> dict[str, object]:
    entry = append_entry(factory, warehouse, sku, quantity, unit)
    return {"ok": True, "entry_id": entry.entry_id}


@app.post("/sync")
def sync_node(endpoint: str) -> dict[str, object]:
    return sync_inventory(endpoint)
