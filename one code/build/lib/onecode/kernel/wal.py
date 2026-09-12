import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def global_wal_paths(workspace_root: Path) -> list[Path]:
    onecode_root = workspace_root.resolve() / ".onecode"
    active_path = onecode_root / "global-ledger.jsonl"
    rotated_paths = [
        path
        for path in onecode_root.glob("global-ledger.*.jsonl")
        if path.name.removeprefix("global-ledger.").removesuffix(".jsonl").isdigit()
    ]
    rotated_paths = sorted(
        rotated_paths,
        key=lambda path: int(path.name.removeprefix("global-ledger.").removesuffix(".jsonl")),
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


def decode_balance_mutation_tuple(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError("invalid_global_wal_balance_mutation")
    changed_assets, changed_lines, before, after = value
    values = (changed_assets, changed_lines, before, after)
    if any(isinstance(item, bool) or not isinstance(item, int) for item in values):
        raise ValueError("invalid_global_wal_balance_mutation")
    if changed_assets < 0 or changed_lines < 0 or changed_lines > changed_assets * 6:
        raise ValueError("invalid_global_wal_balance_mutation")
    if not 0 <= before <= 63 or not 0 <= after <= 63:
        raise ValueError("invalid_global_wal_balance_mutation")
    return {
        "changed_asset_count": changed_assets,
        "total_changed_line_count": changed_lines,
        "latest_before_status_code": before,
        "latest_after_status_code": after,
        "changed_bands": [],
    }


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
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid_global_wal_json") from exc
        if not isinstance(value, dict):
            raise ValueError("invalid_global_wal_entry")
        decode_balance_mutation_tuple(value.get("bm"))
        if "hash" in value or "prev" in value:
            if value.get("prev") != previous_hash:
                raise ValueError("global_wal_chain_prev_mismatch")
            expected_hash = wal_entry_hash(value)
            if value.get("hash") != expected_hash:
                raise ValueError("global_wal_chain_hash_mismatch")
            previous_hash = expected_hash
        entries.append({**value, "_wal_path": str(path.resolve())})
    return entries


def global_wal_evidence_metrics(workspace_root: Path) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "entry_count": 0,
        "total_bytes": 0,
        "entries_by_risk_tier": {},
        "entries_by_capture_mode": {},
        "bytes_by_risk_tier": {},
        "bytes_by_capture_mode": {},
    }
    for wal_path in global_wal_paths(workspace_root):
        if not wal_path.exists():
            continue
        read_validated_global_wal_segment(wal_path)
        for line in wal_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            line_bytes = len((line + "\n").encode("utf-8"))
            entry = json.loads(line)
            if not isinstance(entry, dict):
                continue
            risk_tier = str(entry.get("rt") or "unknown")
            capture_mode = str(entry.get("cm") or "unknown")
            metrics["entry_count"] += 1
            metrics["total_bytes"] += line_bytes
            entries_by_risk = metrics["entries_by_risk_tier"]
            entries_by_mode = metrics["entries_by_capture_mode"]
            bytes_by_risk = metrics["bytes_by_risk_tier"]
            bytes_by_mode = metrics["bytes_by_capture_mode"]
            entries_by_risk[risk_tier] = entries_by_risk.get(risk_tier, 0) + 1
            entries_by_mode[capture_mode] = entries_by_mode.get(capture_mode, 0) + 1
            bytes_by_risk[risk_tier] = bytes_by_risk.get(risk_tier, 0) + line_bytes
            bytes_by_mode[capture_mode] = bytes_by_mode.get(capture_mode, 0) + line_bytes
    return metrics


def _parse_wal_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _increment_metric_group(container: dict[str, int], key: str, amount: int = 1) -> None:
    container[key] = container.get(key, 0) + amount


def global_wal_metrics_summary(workspace_root: Path, *, window_seconds: int = 60) -> dict[str, Any]:
    if window_seconds <= 0:
        raise ValueError("window_seconds_must_be_positive")
    summary: dict[str, Any] = {
        "summary_schema_version": 1,
        "window_seconds": window_seconds,
        "entry_count": 0,
        "total_bytes": 0,
        "entries_by_risk_tier": {},
        "entries_by_capture_mode": {},
        "bytes_by_risk_tier": {},
        "bytes_by_capture_mode": {},
        "windows": [],
    }
    windows: dict[int, dict[str, Any]] = {}
    for wal_path in global_wal_paths(workspace_root):
        if not wal_path.exists():
            continue
        read_validated_global_wal_segment(wal_path)
        for line in wal_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            line_bytes = len((line + "\n").encode("utf-8"))
            entry = json.loads(line)
            if not isinstance(entry, dict):
                continue
            risk_tier = str(entry.get("rt") or "unknown")
            capture_mode = str(entry.get("cm") or "unknown")
            summary["entry_count"] += 1
            summary["total_bytes"] += line_bytes
            _increment_metric_group(summary["entries_by_risk_tier"], risk_tier)
            _increment_metric_group(summary["entries_by_capture_mode"], capture_mode)
            _increment_metric_group(summary["bytes_by_risk_tier"], risk_tier, line_bytes)
            _increment_metric_group(summary["bytes_by_capture_mode"], capture_mode, line_bytes)

            timestamp = _parse_wal_timestamp(entry.get("ts"))
            bucket = 0 if timestamp is None else int(timestamp.timestamp()) // window_seconds * window_seconds
            window = windows.get(bucket)
            if window is None:
                window_start = datetime.fromtimestamp(bucket, UTC).isoformat()
                window = {
                    "window_start": window_start,
                    "entry_count": 0,
                    "total_bytes": 0,
                    "entries_by_risk_tier": {},
                    "entries_by_capture_mode": {},
                    "bytes_by_risk_tier": {},
                    "bytes_by_capture_mode": {},
                }
                windows[bucket] = window
            window["entry_count"] += 1
            window["total_bytes"] += line_bytes
            _increment_metric_group(window["entries_by_risk_tier"], risk_tier)
            _increment_metric_group(window["entries_by_capture_mode"], capture_mode)
            _increment_metric_group(window["bytes_by_risk_tier"], risk_tier, line_bytes)
            _increment_metric_group(window["bytes_by_capture_mode"], capture_mode, line_bytes)
    summary["windows"] = [windows[key] for key in sorted(windows)]
    return summary
