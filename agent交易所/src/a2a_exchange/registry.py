"""Thread-safe in-memory capability registry."""
from __future__ import annotations

import threading
import uuid
from typing import Dict, List, Optional

from .manifest import CapabilityRecord


class CapabilityRegistry:
    def __init__(self) -> None:
        self._by_id: Dict[str, CapabilityRecord] = {}
        self._by_hash: Dict[str, CapabilityRecord] = {}
        self._lock = threading.Lock()

    def register(self, record: CapabilityRecord) -> CapabilityRecord:
        with self._lock:
            self._by_id[record.capability_id] = record
            self._by_hash[record.artifact_sha256] = record
        return record

    def next_capability_id(self) -> str:
        return f"cap_{uuid.uuid4().hex}"

    def get(self, capability_id: str) -> Optional[CapabilityRecord]:
        with self._lock:
            return self._by_id.get(capability_id)

    def get_by_hash(self, artifact_sha256: str) -> Optional[CapabilityRecord]:
        with self._lock:
            return self._by_hash.get(artifact_sha256)

    def all(self) -> List[CapabilityRecord]:
        with self._lock:
            return list(self._by_id.values())

    def __len__(self) -> int:
        with self._lock:
            return len(self._by_id)
