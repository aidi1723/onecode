"""Artifact-free discovery for verified capability listings."""
from __future__ import annotations

from typing import List, Optional, Sequence

from .manifest import CapabilityListing, to_listing
from .registry import CapabilityRegistry


class CapabilityDiscovery:
    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry

    def find_matches(
        self,
        required_input_keys: Optional[Sequence[str]] = None,
        max_price: Optional[int] = None,
        min_pass_rate: Optional[float] = None,
        max_latency_ms: Optional[int] = None,
        verified_only: bool = True,
    ) -> List[CapabilityListing]:
        required = list(required_input_keys or [])
        matches: list[CapabilityListing] = []

        for record in self.registry.all():
            if verified_only and not record.scorecard.verified:
                continue
            if max_price is not None and record.manifest.price_tokens > max_price:
                continue
            if min_pass_rate is not None and record.scorecard.pass_rate < min_pass_rate:
                continue
            if max_latency_ms is not None and record.scorecard.avg_latency_ms > max_latency_ms:
                continue

            props = record.manifest.interface.input_schema.get("properties", {})
            if all(key in props for key in required):
                matches.append(to_listing(record))

        return matches
