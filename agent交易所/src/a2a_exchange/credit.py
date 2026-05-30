"""Mock credit guard: dimensionality-reduced static credit stub.

v0.1 skips anti-sybil and clearing logic. Every buyer agent gets a
fixed genesis credit line on first contact; checkout is an in-memory
subtraction. Atomic per-agent so concurrent checkouts cannot oversell.

NOTE: agent_id is self-reported and unauthenticated in v0.1. Any caller
can mint a fresh balance by claiming a new id. Not for public exposure.
"""
from __future__ import annotations

import threading


class MockCreditGuard:
    INITIAL_CREDIT = 10_000_000_000  # 10 billion genesis credit

    def __init__(self) -> None:
        self._balances: dict[str, int] = {}
        self._lock = threading.Lock()

    def get_or_create_balance(self, agent_id: str) -> int:
        with self._lock:
            return self._balances.setdefault(agent_id, self.INITIAL_CREDIT)

    def execute_purchase(self, agent_id: str, price: int) -> bool:
        """Atomic debit. Returns False if balance is insufficient."""
        if price < 0:
            raise ValueError("price must be non-negative")
        with self._lock:
            current = self._balances.setdefault(agent_id, self.INITIAL_CREDIT)
            if current < price:
                return False
            self._balances[agent_id] = current - price
            return True
