"""Mock escrow state machine for prototype settlement semantics."""
from __future__ import annotations

import threading
import uuid
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field


EscrowStatus = Literal["held", "released", "disputed"]


class EscrowRecord(BaseModel):
    escrow_id: str
    quote_id: str
    buyer_agent_id: str
    capability_id: str
    artifact_sha256: str
    amount_tokens: int = Field(..., ge=0)
    status: EscrowStatus = "held"


class EscrowBook:
    def __init__(self) -> None:
        self._escrows: Dict[str, EscrowRecord] = {}
        self._lock = threading.Lock()

    def create(
        self,
        quote_id: str,
        buyer_agent_id: str,
        capability_id: str,
        artifact_sha256: str,
        amount_tokens: int,
    ) -> EscrowRecord:
        escrow = EscrowRecord(
            escrow_id=f"escrow_{uuid.uuid4().hex}",
            quote_id=quote_id,
            buyer_agent_id=buyer_agent_id,
            capability_id=capability_id,
            artifact_sha256=artifact_sha256,
            amount_tokens=amount_tokens,
        )
        with self._lock:
            self._escrows[escrow.escrow_id] = escrow
        return escrow.model_copy(deep=True)

    def get(self, escrow_id: str) -> Optional[EscrowRecord]:
        with self._lock:
            escrow = self._escrows.get(escrow_id)
            if escrow is None:
                return None
            return escrow.model_copy(deep=True)

    def settle(self, escrow_id: str, buyer_agent_id: str, accepted: bool) -> Optional[EscrowRecord]:
        with self._lock:
            escrow = self._escrows.get(escrow_id)
            if escrow is None or escrow.buyer_agent_id != buyer_agent_id:
                return None
            if escrow.status != "held":
                return escrow.model_copy(deep=True)
            escrow.status = "released" if accepted else "disputed"
            self._escrows[escrow_id] = escrow
            return escrow.model_copy(deep=True)

    def __len__(self) -> int:
        with self._lock:
            return len(self._escrows)
