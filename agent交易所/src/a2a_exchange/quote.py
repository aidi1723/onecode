"""Version-locked purchase quotes."""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from pydantic import BaseModel, Field

from .manifest import Scorecard


class Quote(BaseModel):
    quote_id: str
    buyer_agent_id: str
    capability_id: str
    artifact_sha256: str
    price_tokens: int = Field(..., ge=0)
    scorecard_snapshot: Scorecard
    expires_at: datetime


class QuoteBook:
    def __init__(self, ttl_seconds: int = 300) -> None:
        self.ttl_seconds = ttl_seconds
        self._quotes: Dict[str, Quote] = {}
        self._consumed: set[str] = set()
        self._lock = threading.Lock()

    def create(
        self,
        buyer_agent_id: str,
        capability_id: str,
        artifact_sha256: str,
        price_tokens: int,
        scorecard: Scorecard,
    ) -> Quote:
        quote = Quote(
            quote_id=f"quote_{uuid.uuid4().hex}",
            buyer_agent_id=buyer_agent_id,
            capability_id=capability_id,
            artifact_sha256=artifact_sha256,
            price_tokens=price_tokens,
            scorecard_snapshot=scorecard.model_copy(deep=True),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=self.ttl_seconds),
        )
        with self._lock:
            self._quotes[quote.quote_id] = quote
        return quote.model_copy(deep=True)

    def get(self, quote_id: str) -> Optional[Quote]:
        with self._lock:
            quote = self._quotes.get(quote_id)
            if quote is None:
                return None
            return quote.model_copy(deep=True)

    def consume(self, quote_id: str) -> Optional[Quote]:
        with self._lock:
            quote = self._quotes.get(quote_id)
            if quote is None or quote_id in self._consumed:
                return None
            self._consumed.add(quote_id)
            return quote.model_copy(deep=True)

    def is_expired(self, quote: Quote) -> bool:
        return datetime.now(timezone.utc) >= quote.expires_at

    def __len__(self) -> int:
        with self._lock:
            return len(self._quotes)
