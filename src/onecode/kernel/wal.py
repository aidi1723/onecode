import hashlib
import json
from pathlib import Path
from typing import Any


def global_wal_paths(workspace_root: Path) -> list[Path]:
    onecode_root = workspace_root.resolve() / ".onecode"
    active_path = onecode_root / "global-ledger.jsonl"
    rotated_paths = sorted(
        onecode_root.glob("global-ledger.*.jsonl"),
        key=lambda path: int(path.name.removeprefix("global-ledger.").removesuffix(".jsonl"))
        if path.name.removeprefix("global-ledger.").removesuffix(".jsonl").isdigit()
        else -1,
    )
    return [path for path in rotated_paths if path.name != active_path.name] + [active_path]


def read_unsafe_raw_global_wal_entries(workspace_root: Path) -> list[dict[str, Any]]:
    """Read WAL JSONL without validating hash chains.

    This exists only for low-level diagnostics. Runtime consumers that make
    resume or trust decisions must use read_validated_global_wal_entries().
    """
    entries: list[dict[str, Any]] = []
    for wal_path in global_wal_paths(workspace_root):
        if not wal_path.exists():
            continue
        for line in wal_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                entries.append(value)
    return entries


def read_raw_global_wal_entries(workspace_root: Path) -> list[dict[str, Any]]:
    return read_unsafe_raw_global_wal_entries(workspace_root)


def canonical_json_line(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def wal_entry_hash(entry: dict[str, Any]) -> str:
    encoded = canonical_json_line({key: value for key, value in entry.items() if key != "hash"})
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def read_validated_global_wal_entries(workspace_root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for wal_path in global_wal_paths(workspace_root):
        entries.extend(read_validated_global_wal_segment(wal_path))
    return entries


def read_validated_global_wal_segment(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    previous_hash: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError("invalid_global_wal_entry")
        if "hash" in value or "prev" in value:
            if value.get("prev") != previous_hash:
                raise ValueError("global_wal_chain_prev_mismatch")
            expected_hash = wal_entry_hash(value)
            if value.get("hash") != expected_hash:
                raise ValueError("global_wal_chain_hash_mismatch")
            previous_hash = expected_hash
        entries.append({**value, "_wal_path": str(path.resolve())})
    return entries
