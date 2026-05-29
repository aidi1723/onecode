from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .build_mode_types import EvidenceEnvelope


def sign_evidence_envelope(
    node_id: str,
    hexagram: str,
    evidence: dict[str, Any],
    secret: bytes,
    timestamp_ms: int | None = None,
) -> EvidenceEnvelope:
    timestamp = int(time.time() * 1000) if timestamp_ms is None else timestamp_ms
    evidence_json = json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    evidence_sha256 = hashlib.sha256(evidence_json.encode("utf-8")).hexdigest()
    payload = f"{node_id}|{hexagram}|{timestamp}|{evidence_sha256}".encode("utf-8")
    signature = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return EvidenceEnvelope(
        node_id=node_id,
        hexagram=hexagram,
        evidence=evidence,
        timestamp_ms=timestamp,
        evidence_sha256=evidence_sha256,
        signature=signature,
    )


def verify_evidence_envelope(envelope: EvidenceEnvelope, secret: bytes) -> bool:
    expected = sign_evidence_envelope(
        envelope.node_id,
        envelope.hexagram,
        envelope.evidence,
        secret,
        timestamp_ms=envelope.timestamp_ms,
    )
    return hmac.compare_digest(expected.signature, envelope.signature)


def append_node_event(path: str | Path, envelope: EvidenceEnvelope) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(envelope), ensure_ascii=False, sort_keys=True) + "\n")
