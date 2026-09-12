from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from onecode.kernel.checkpoint import run_evidence_write_lock
from onecode.kernel.evidence_policy import CaptureMode, RiskTier, classify_event


@dataclass(frozen=True)
class TraceEvent:
    trace_id: str
    run_id: str
    span_id: str
    parent_span_id: str | None
    event_type: str
    status: str
    payload: dict[str, Any] = field(default_factory=dict)
    duration_ms: int | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    risk_tier: RiskTier | str | None = None
    capture_mode: CaptureMode | str | None = None
    payload_digest: str | None = None
    classification_reason: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("trace_id", "run_id", "span_id", "event_type", "status"):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} must not be empty")
        classification = classify_event(self.event_type)
        escalated = self.status in {"halted", "denied", "failed", "timeout"} or self.payload.get("reason") in {
            "http_timeout",
            "resource_budget_exceeded",
            "sovereignty_breach",
        }
        if escalated and classification.risk_tier not in {RiskTier.CRITICAL, RiskTier.HIGH}:
            classification_risk_tier = RiskTier.HIGH
            classification_capture_mode = CaptureMode.COMPACT
            classification_reason = "anomaly_escalation"
        else:
            classification_risk_tier = classification.risk_tier
            classification_capture_mode = classification.capture_mode
            classification_reason = classification.reason
        if self.risk_tier is None:
            object.__setattr__(self, "risk_tier", classification_risk_tier)
        if self.capture_mode is None:
            object.__setattr__(self, "capture_mode", classification_capture_mode)
        if self.classification_reason is None:
            object.__setattr__(self, "classification_reason", classification_reason)
        if self.payload_digest is None:
            encoded = json.dumps(self.payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            object.__setattr__(self, "payload_digest", sha256(encoded.encode("utf-8")).hexdigest())

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "event_type": self.event_type,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            "risk_tier": str(self.risk_tier),
            "capture_mode": str(self.capture_mode),
            "payload_digest": self.payload_digest,
            "classification_reason": self.classification_reason,
            "payload": self.payload,
        }


def write_trace_event(path: Path, event: TraceEvent) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    event_payload = event.to_dict()
    event_payload["write_latency_ms"] = "000000.000"
    latency_field = b'"write_latency_ms": "000000.000"'
    latency_value_offset = len(b'"write_latency_ms": ')
    started = time.perf_counter()
    encoded = (json.dumps(event_payload, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    placeholder_index = encoded.rindex(latency_field) + latency_value_offset
    with run_evidence_write_lock(path.parent):
        line_start = path.stat().st_size if path.exists() else 0
        with path.open("ab") as handle:
            handle.write(encoded)
            handle.flush()
        latency_ms = min((time.perf_counter() - started) * 1000, 999999.999)
        replacement = f'"{latency_ms:010.3f}"'.encode("ascii")
        with path.open("r+b") as handle:
            handle.seek(line_start + placeholder_index)
            handle.write(replacement)


@dataclass
class _AggregateBucket:
    trace_id: str
    run_id: str
    event_type: str
    status: str
    risk_tier: str
    count: int = 0
    first_timestamp: str | None = None
    last_timestamp: str | None = None
    rolling_digest: str = "0" * 64

    def add(self, event: TraceEvent) -> None:
        event_dict = event.to_dict()
        self.count += 1
        if self.first_timestamp is None:
            self.first_timestamp = event.timestamp
        self.last_timestamp = event.timestamp
        encoded = json.dumps(event_dict, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.rolling_digest = sha256((self.rolling_digest + encoded).encode("utf-8")).hexdigest()

    def to_event(self) -> TraceEvent:
        return TraceEvent(
            trace_id=self.trace_id,
            run_id=self.run_id,
            span_id=f"{self.event_type}-aggregate",
            parent_span_id=None,
            event_type=f"{self.event_type}_aggregate",
            status=self.status,
            payload={
                "count": self.count,
                "first_timestamp": self.first_timestamp,
                "last_timestamp": self.last_timestamp,
                "rolling_digest": self.rolling_digest,
            },
            risk_tier=self.risk_tier,
            capture_mode=CaptureMode.AGGREGATE,
            classification_reason="low_risk_events_coalesced",
        )


class TraceAggregator:
    def __init__(self, path: Path):
        self.path = path
        self._buckets: dict[tuple[str, str, str, str], _AggregateBucket] = {}

    def record(self, event: TraceEvent) -> None:
        if str(event.capture_mode) != CaptureMode.AGGREGATE:
            if self._buckets and (str(event.risk_tier) == RiskTier.CRITICAL or str(event.capture_mode) == CaptureMode.FULL):
                self.flush()
            write_trace_event(self.path, event)
            return
        key = (event.trace_id, event.run_id, event.event_type, event.status)
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = _AggregateBucket(
                trace_id=event.trace_id,
                run_id=event.run_id,
                event_type=event.event_type,
                status=event.status,
                risk_tier=str(event.risk_tier),
            )
            self._buckets[key] = bucket
        bucket.add(event)

    def flush(self) -> None:
        for key in sorted(self._buckets):
            write_trace_event(self.path, self._buckets[key].to_event())
        self._buckets.clear()


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def trace_evidence_metrics(path: Path, *, aggregate_gap_threshold_seconds: int = 300) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "event_count": 0,
        "aggregate_event_count": 0,
        "total_bytes": 0,
        "events_by_risk_tier": {},
        "events_by_capture_mode": {},
        "bytes_by_risk_tier": {},
        "bytes_by_capture_mode": {},
        "write_latency_ms": {"count": 0, "max": 0.0, "p95": 0.0},
        "aggregate_gap_count": 0,
        "max_aggregate_gap_seconds": 0.0,
    }
    if not path.exists():
        return metrics
    latencies: list[float] = []
    aggregate_windows: list[tuple[datetime, datetime]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        line_bytes = len((line + "\n").encode("utf-8"))
        event = json.loads(line)
        if not isinstance(event, dict):
            continue
        risk_tier = str(event.get("risk_tier") or "unknown")
        capture_mode = str(event.get("capture_mode") or "unknown")
        metrics["event_count"] += 1
        metrics["total_bytes"] += line_bytes
        if capture_mode == CaptureMode.AGGREGATE:
            metrics["aggregate_event_count"] += 1
            payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
            aggregate_start = _parse_timestamp(payload.get("first_timestamp"))
            aggregate_end = _parse_timestamp(payload.get("last_timestamp"))
            if aggregate_start is not None and aggregate_end is not None:
                aggregate_windows.append((aggregate_start, aggregate_end))
        latency = event.get("write_latency_ms")
        if isinstance(latency, str):
            try:
                latency = float(latency)
            except ValueError:
                latency = None
        if isinstance(latency, int | float):
            latencies.append(float(latency))
        events_by_risk = metrics["events_by_risk_tier"]
        events_by_mode = metrics["events_by_capture_mode"]
        bytes_by_risk = metrics["bytes_by_risk_tier"]
        bytes_by_mode = metrics["bytes_by_capture_mode"]
        events_by_risk[risk_tier] = events_by_risk.get(risk_tier, 0) + 1
        events_by_mode[capture_mode] = events_by_mode.get(capture_mode, 0) + 1
        bytes_by_risk[risk_tier] = bytes_by_risk.get(risk_tier, 0) + line_bytes
        bytes_by_mode[capture_mode] = bytes_by_mode.get(capture_mode, 0) + line_bytes
    if latencies:
        ordered = sorted(latencies)
        p95_index = min(len(ordered) - 1, int((len(ordered) - 1) * 0.95))
        metrics["write_latency_ms"] = {
            "count": len(ordered),
            "max": max(ordered),
            "p95": ordered[p95_index],
        }
    last_aggregate_end: datetime | None = None
    for aggregate_start, aggregate_end in sorted(aggregate_windows, key=lambda window: window[0]):
        if last_aggregate_end is not None:
            gap_seconds = (aggregate_start - last_aggregate_end).total_seconds()
            if gap_seconds > aggregate_gap_threshold_seconds:
                metrics["aggregate_gap_count"] += 1
                metrics["max_aggregate_gap_seconds"] = max(metrics["max_aggregate_gap_seconds"], gap_seconds)
        last_aggregate_end = aggregate_end
    return metrics
