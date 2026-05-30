# Trusted Capability Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the old register/discover/checkout marketplace prototype with a verified Python capability trading layer that validates artifacts before discovery, locks quote terms, and releases artifacts only after escrow-shaped checkout.

**Architecture:** Keep the existing `a2a_exchange` package and FastAPI service shape, but replace the core domain model. The service remains in-memory and local-only; verification runs Python artifacts in a subprocess with timeout controls and produces scorecards. Discovery returns artifact-free listings, checkout uses quote IDs, and escrow records preserve transaction semantics for later real settlement.

**Tech Stack:** Python 3.9+, FastAPI, Pydantic v2, uvicorn, stdlib `unittest`, stdlib `subprocess`, stdlib `threading`, stdlib `uuid`, stdlib `datetime`.

---

## File Structure

- Modify: `src/a2a_exchange/manifest.py`
  - Owns interface schema, permission policy, sandbox policy, manifest, scorecard, capability record, and public listing models.
- Create: `src/a2a_exchange/eval_pack.py`
  - Owns eval case and eval pack models.
- Create: `src/a2a_exchange/verifier.py`
  - Runs artifact source in a subprocess, calls `run(input)`, compares outputs, and returns a scorecard.
- Modify: `src/a2a_exchange/registry.py`
  - Stores capabilities by `capability_id` and by `artifact_sha256`; supports version-locked quote lookup.
- Modify: `src/a2a_exchange/discovery.py`
  - Filters verified capability listings and never returns artifact source.
- Create: `src/a2a_exchange/quote.py`
  - Creates and resolves expiring purchase quotes.
- Create: `src/a2a_exchange/escrow.py`
  - Creates escrow records and settles them to `released` or `disputed`.
- Modify: `src/a2a_exchange/credit.py`
  - Keep the mock credit behavior; add no seller ledger.
- Modify: `src/a2a_exchange/app.py`
  - Replace old endpoints with register, discover, quote, checkout, settle, balance, and healthz.
- Modify: `tests/test_exchange.py`
  - Replace old marketplace tests with trusted capability flow tests.
- Modify: `README.md`
  - Update the product description and endpoint table.
- Delete generated files:
  - `src/a2a_exchange/__pycache__/`
  - `tests/__pycache__/`

## Task 1: Replace Tests With Trusted Capability Contract

**Files:**
- Modify: `tests/test_exchange.py`

- [ ] **Step 1: Replace the old tests with failing trusted-flow tests**

Overwrite `tests/test_exchange.py` with:

```python
"""End-to-end tests for the trusted capability trading layer."""
import unittest

from fastapi.testclient import TestClient

from a2a_exchange.app import create_app
from a2a_exchange.credit import MockCreditGuard


GOOD_ARTIFACT = """
def run(input):
    text = input["text"]
    return {"upper": text.upper()}
""".strip()


BAD_ARTIFACT = """
def run(input):
    return {"upper": "wrong"}
""".strip()


MALFORMED_ARTIFACT = """
def not_run(input):
    return input
""".strip()


def register_payload(artifact=GOOD_ARTIFACT, price=500, expected=None):
    expected_output = expected or {"upper": "HELLO"}
    return {
        "manifest": {
            "name": "uppercase-tool",
            "interface": {
                "input_schema": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                },
                "output_schema": {
                    "type": "object",
                    "properties": {"upper": {"type": "string"}},
                    "required": ["upper"],
                },
            },
            "price_tokens": price,
            "permission_policy": {"network": False, "filesystem": False},
            "description": "Converts text to uppercase.",
        },
        "artifact": artifact,
        "eval_pack": {
            "cases": [
                {
                    "name": "hello uppercase",
                    "input": {"text": "hello"},
                    "expected_output": expected_output,
                }
            ]
        },
        "sandbox_policy": {"network": False, "timeout_ms": 1000, "max_cases": 5},
    }


class TrustedCapabilityFlowTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app())

    def test_register_success_creates_scorecard(self):
        resp = self.client.post("/register", json=register_payload())
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["verification_status"], "verified")
        self.assertTrue(body["scorecard"]["verified"])
        self.assertEqual(body["scorecard"]["cases_total"], 1)
        self.assertEqual(body["scorecard"]["cases_passed"], 1)
        self.assertEqual(body["scorecard"]["pass_rate"], 1.0)
        self.assertEqual(len(body["scorecard"]["artifact_sha256"]), 64)

    def test_failing_eval_is_not_discoverable_by_default(self):
        resp = self.client.post(
            "/register",
            json=register_payload(artifact=BAD_ARTIFACT),
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["verification_status"], "failed")

        discover = self.client.post("/discover", json={})
        self.assertEqual(discover.status_code, 200, discover.text)
        self.assertEqual(discover.json(), [])

    def test_malformed_artifact_rejected(self):
        resp = self.client.post(
            "/register",
            json=register_payload(artifact=MALFORMED_ARTIFACT),
        )
        self.assertEqual(resp.status_code, 422, resp.text)

    def test_discover_filters_and_never_returns_artifact(self):
        self.client.post("/register", json=register_payload(price=500))
        resp = self.client.post(
            "/discover",
            json={
                "required_input_keys": ["text"],
                "max_price": 1000,
                "min_pass_rate": 1.0,
                "max_latency_ms": 1000,
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        hits = resp.json()
        self.assertEqual(len(hits), 1)
        self.assertNotIn("artifact", hits[0])
        self.assertEqual(hits[0]["name"], "uppercase-tool")
        self.assertTrue(hits[0]["scorecard"]["verified"])

        too_cheap = self.client.post("/discover", json={"max_price": 100})
        self.assertEqual(too_cheap.json(), [])

    def test_quote_locks_price_hash_and_scorecard(self):
        registered = self.client.post("/register", json=register_payload()).json()
        quote = self.client.post(
            "/quote",
            json={"buyer_agent_id": "buyer-1", "capability_id": registered["capability_id"]},
        )
        self.assertEqual(quote.status_code, 200, quote.text)
        body = quote.json()
        self.assertEqual(body["buyer_agent_id"], "buyer-1")
        self.assertEqual(body["capability_id"], registered["capability_id"])
        self.assertEqual(body["price_tokens"], 500)
        self.assertEqual(
            body["artifact_sha256"],
            registered["scorecard"]["artifact_sha256"],
        )
        self.assertEqual(body["scorecard_snapshot"]["pass_rate"], 1.0)

    def test_checkout_requires_quote_and_releases_artifact_after_debit(self):
        registered = self.client.post("/register", json=register_payload()).json()
        quote = self.client.post(
            "/quote",
            json={"buyer_agent_id": "buyer-1", "capability_id": registered["capability_id"]},
        ).json()

        checkout = self.client.post("/checkout", json={"quote_id": quote["quote_id"]})
        self.assertEqual(checkout.status_code, 200, checkout.text)
        body = checkout.json()
        self.assertEqual(body["status"], "unlocked")
        self.assertEqual(body["artifact"], GOOD_ARTIFACT)
        self.assertEqual(body["price_paid"], 500)
        self.assertEqual(
            body["remaining_balance"],
            MockCreditGuard.INITIAL_CREDIT - 500,
        )
        self.assertTrue(body["escrow_id"])

        missing = self.client.post("/checkout", json={"quote_id": "missing"})
        self.assertEqual(missing.status_code, 404)

    def test_settle_releases_or_disputes_escrow(self):
        registered = self.client.post("/register", json=register_payload()).json()
        quote = self.client.post(
            "/quote",
            json={"buyer_agent_id": "buyer-1", "capability_id": registered["capability_id"]},
        ).json()
        checkout = self.client.post("/checkout", json={"quote_id": quote["quote_id"]}).json()

        released = self.client.post(
            "/settle",
            json={
                "buyer_agent_id": "buyer-1",
                "escrow_id": checkout["escrow_id"],
                "accepted": True,
            },
        )
        self.assertEqual(released.status_code, 200, released.text)
        self.assertEqual(released.json()["status"], "released")

    def test_existing_quote_survives_later_price_change(self):
        first = self.client.post("/register", json=register_payload(price=500)).json()
        quote = self.client.post(
            "/quote",
            json={"buyer_agent_id": "buyer-1", "capability_id": first["capability_id"]},
        ).json()

        self.client.post("/register", json=register_payload(price=900))

        checkout = self.client.post("/checkout", json={"quote_id": quote["quote_id"]})
        self.assertEqual(checkout.status_code, 200, checkout.text)
        self.assertEqual(checkout.json()["price_paid"], 500)


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

- [ ] **Step 2: Run the tests and verify they fail for the old API**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: failures or errors because `POST /register` still expects the old manifest shape and `/quote` and `/settle` do not exist.

- [ ] **Step 3: Commit the failing contract tests**

```bash
git add agent交易所/tests/test_exchange.py
git commit -m "test: define trusted capability exchange contract"
```

## Task 2: Define Manifest, Eval Pack, and Scorecard Models

**Files:**
- Modify: `src/a2a_exchange/manifest.py`
- Create: `src/a2a_exchange/eval_pack.py`
- Test: `tests/test_exchange.py`

- [ ] **Step 1: Replace `manifest.py` with new domain models**

Use this implementation:

```python
"""Models for verified Python capabilities."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class InterfaceSchema(BaseModel):
    input_schema: Dict[str, Any] = Field(..., description="JSON Schema input contract")
    output_schema: Dict[str, Any] = Field(..., description="JSON Schema output contract")


class PermissionPolicy(BaseModel):
    network: bool = False
    filesystem: bool = False


class SandboxPolicy(BaseModel):
    network: bool = False
    timeout_ms: int = Field(1000, ge=1, le=30_000)
    max_cases: int = Field(20, ge=1, le=100)


class CapabilityManifest(BaseModel):
    name: str = Field(..., min_length=1)
    interface: InterfaceSchema
    price_tokens: int = Field(..., ge=0)
    permission_policy: PermissionPolicy = Field(default_factory=PermissionPolicy)
    description: str = ""


class CaseResult(BaseModel):
    name: str
    passed: bool
    duration_ms: int = Field(..., ge=0)
    error: str = ""


class Scorecard(BaseModel):
    verified: bool
    pass_rate: float = Field(..., ge=0.0, le=1.0)
    cases_total: int = Field(..., ge=0)
    cases_passed: int = Field(..., ge=0)
    avg_latency_ms: int = Field(..., ge=0)
    artifact_sha256: str = Field(..., min_length=64, max_length=64)
    case_results: List[CaseResult] = Field(default_factory=list)


class CapabilityRecord(BaseModel):
    capability_id: str
    manifest: CapabilityManifest
    artifact: str
    artifact_sha256: str
    sandbox_policy: SandboxPolicy
    scorecard: Scorecard
    verification_status: Literal["verified", "failed"]


class CapabilityListing(BaseModel):
    capability_id: str
    name: str
    interface: InterfaceSchema
    price_tokens: int
    permission_policy: PermissionPolicy
    description: str
    verification_status: Literal["verified", "failed"]
    scorecard: Scorecard


def to_listing(record: CapabilityRecord) -> CapabilityListing:
    return CapabilityListing(
        capability_id=record.capability_id,
        name=record.manifest.name,
        interface=record.manifest.interface,
        price_tokens=record.manifest.price_tokens,
        permission_policy=record.manifest.permission_policy,
        description=record.manifest.description,
        verification_status=record.verification_status,
        scorecard=record.scorecard,
    )
```

- [ ] **Step 2: Add `eval_pack.py`**

Use this implementation:

```python
"""Replayable eval packs submitted with capabilities."""
from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    name: str = Field(..., min_length=1)
    input: Dict[str, Any]
    expected_output: Dict[str, Any]


class EvalPack(BaseModel):
    cases: List[EvalCase] = Field(..., min_length=1)
```

- [ ] **Step 3: Run tests and verify model imports progress but endpoints still fail**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: failures remain because app, verifier, registry, quote, and escrow are not implemented yet.

- [ ] **Step 4: Commit models**

```bash
git add agent交易所/src/a2a_exchange/manifest.py agent交易所/src/a2a_exchange/eval_pack.py
git commit -m "feat: define trusted capability models"
```

## Task 3: Implement Subprocess Verifier

**Files:**
- Create: `src/a2a_exchange/verifier.py`
- Test: `tests/test_exchange.py`

- [ ] **Step 1: Add verifier implementation**

Use this implementation:

```python
"""Verify Python capability artifacts with replayable eval packs."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Tuple

from .eval_pack import EvalPack
from .manifest import CaseResult, SandboxPolicy, Scorecard


class VerificationError(Exception):
    """Raised when an artifact cannot be evaluated at all."""


def compute_artifact_sha256(artifact: str) -> str:
    return hashlib.sha256(artifact.encode("utf-8")).hexdigest()


def verify_artifact(
    artifact: str,
    eval_pack: EvalPack,
    sandbox_policy: SandboxPolicy,
) -> Scorecard:
    if not artifact.strip():
        raise VerificationError("artifact is empty")
    if len(eval_pack.cases) > sandbox_policy.max_cases:
        raise VerificationError("eval pack exceeds sandbox max_cases")

    artifact_sha256 = compute_artifact_sha256(artifact)
    case_results: list[CaseResult] = []

    for case in eval_pack.cases:
        start = time.monotonic()
        passed = False
        error = ""
        try:
            output = _run_case(artifact, case.input, sandbox_policy.timeout_ms)
            passed = output == case.expected_output
            if not passed:
                error = f"expected {case.expected_output!r}, got {output!r}"
        except VerificationError as exc:
            error = str(exc)
        duration_ms = max(0, int((time.monotonic() - start) * 1000))
        case_results.append(
            CaseResult(
                name=case.name,
                passed=passed,
                duration_ms=duration_ms,
                error=error,
            )
        )

    cases_total = len(case_results)
    cases_passed = sum(1 for result in case_results if result.passed)
    avg_latency_ms = (
        int(sum(result.duration_ms for result in case_results) / cases_total)
        if cases_total
        else 0
    )
    return Scorecard(
        verified=cases_total > 0 and cases_passed == cases_total,
        pass_rate=cases_passed / cases_total if cases_total else 0.0,
        cases_total=cases_total,
        cases_passed=cases_passed,
        avg_latency_ms=avg_latency_ms,
        artifact_sha256=artifact_sha256,
        case_results=case_results,
    )


def _run_case(artifact: str, input_value: Dict[str, Any], timeout_ms: int) -> Dict[str, Any]:
    runner = """
import importlib.util
import json
import pathlib
import sys

artifact_path = pathlib.Path(sys.argv[1])
payload = json.loads(sys.argv[2])
spec = importlib.util.spec_from_file_location("capability_artifact", artifact_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
run = getattr(module, "run", None)
if not callable(run):
    raise RuntimeError("artifact must define callable run(input)")
result = run(payload)
print(json.dumps(result, sort_keys=True, separators=(",", ":")))
""".strip()

    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_path = Path(tmpdir) / "artifact.py"
        artifact_path.write_text(artifact, encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "-c", runner, str(artifact_path), json.dumps(input_value)],
            capture_output=True,
            text=True,
            timeout=timeout_ms / 1000,
            check=False,
        )

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise VerificationError(detail or "artifact execution failed")
    try:
        output = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise VerificationError(f"artifact returned non-json output: {exc}") from exc
    if not isinstance(output, dict):
        raise VerificationError("artifact run(input) must return a JSON object")
    return output
```

- [ ] **Step 2: Run tests and verify verifier errors now surface through missing app wiring**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: endpoint-related failures remain; verifier import succeeds.

- [ ] **Step 3: Commit verifier**

```bash
git add agent交易所/src/a2a_exchange/verifier.py
git commit -m "feat: add python capability verifier"
```

## Task 4: Replace Registry and Discovery

**Files:**
- Modify: `src/a2a_exchange/registry.py`
- Modify: `src/a2a_exchange/discovery.py`
- Test: `tests/test_exchange.py`

- [ ] **Step 1: Replace `registry.py`**

Use this implementation:

```python
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
```

- [ ] **Step 2: Replace `discovery.py`**

Use this implementation:

```python
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
```

- [ ] **Step 3: Run tests and verify app wiring still fails**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: failures remain because FastAPI request and response models still use the old API.

- [ ] **Step 4: Commit registry and discovery**

```bash
git add agent交易所/src/a2a_exchange/registry.py agent交易所/src/a2a_exchange/discovery.py
git commit -m "feat: store verified capabilities and safe listings"
```

## Task 5: Add Quote and Escrow Services

**Files:**
- Create: `src/a2a_exchange/quote.py`
- Create: `src/a2a_exchange/escrow.py`
- Test: `tests/test_exchange.py`

- [ ] **Step 1: Add `quote.py`**

Use this implementation:

```python
"""Version-locked purchase quotes."""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from pydantic import BaseModel

from .manifest import Scorecard


class Quote(BaseModel):
    quote_id: str
    buyer_agent_id: str
    capability_id: str
    artifact_sha256: str
    price_tokens: int
    scorecard_snapshot: Scorecard
    expires_at: datetime


class QuoteBook:
    def __init__(self, ttl_seconds: int = 300) -> None:
        self.ttl_seconds = ttl_seconds
        self._quotes: Dict[str, Quote] = {}
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
        return quote

    def get(self, quote_id: str) -> Optional[Quote]:
        with self._lock:
            return self._quotes.get(quote_id)

    def is_expired(self, quote: Quote) -> bool:
        return datetime.now(timezone.utc) >= quote.expires_at

    def __len__(self) -> int:
        with self._lock:
            return len(self._quotes)
```

- [ ] **Step 2: Add `escrow.py`**

Use this implementation:

```python
"""Mock escrow state machine for prototype settlement semantics."""
from __future__ import annotations

import threading
import uuid
from typing import Dict, Literal, Optional

from pydantic import BaseModel


EscrowStatus = Literal["held", "released", "disputed"]


class EscrowRecord(BaseModel):
    escrow_id: str
    quote_id: str
    buyer_agent_id: str
    capability_id: str
    artifact_sha256: str
    amount_tokens: int
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
        return escrow

    def get(self, escrow_id: str) -> Optional[EscrowRecord]:
        with self._lock:
            return self._escrows.get(escrow_id)

    def settle(self, escrow_id: str, buyer_agent_id: str, accepted: bool) -> Optional[EscrowRecord]:
        with self._lock:
            escrow = self._escrows.get(escrow_id)
            if escrow is None or escrow.buyer_agent_id != buyer_agent_id:
                return None
            escrow.status = "released" if accepted else "disputed"
            self._escrows[escrow_id] = escrow
            return escrow

    def __len__(self) -> int:
        with self._lock:
            return len(self._escrows)
```

- [ ] **Step 3: Run tests and verify quote endpoints are still missing**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: failures remain until `app.py` is wired.

- [ ] **Step 4: Commit quote and escrow**

```bash
git add agent交易所/src/a2a_exchange/quote.py agent交易所/src/a2a_exchange/escrow.py
git commit -m "feat: add quote and escrow books"
```

## Task 6: Wire FastAPI Endpoints

**Files:**
- Modify: `src/a2a_exchange/app.py`
- Test: `tests/test_exchange.py`

- [ ] **Step 1: Replace `app.py` with trusted capability endpoints**

Use this implementation:

```python
"""FastAPI HTTP surface for the trusted capability trading layer."""
from __future__ import annotations

from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .credit import MockCreditGuard
from .discovery import CapabilityDiscovery
from .escrow import EscrowBook, EscrowRecord
from .eval_pack import EvalPack
from .manifest import (
    CapabilityListing,
    CapabilityManifest,
    CapabilityRecord,
    SandboxPolicy,
    Scorecard,
)
from .quote import Quote, QuoteBook
from .registry import CapabilityRegistry
from .verifier import VerificationError, verify_artifact


class RegisterCapabilityRequest(BaseModel):
    manifest: CapabilityManifest
    artifact: str = Field(..., min_length=1)
    eval_pack: EvalPack
    sandbox_policy: SandboxPolicy = Field(default_factory=SandboxPolicy)


class RegisterResponse(BaseModel):
    capability_id: str
    verification_status: str
    scorecard: Scorecard


class DiscoverRequest(BaseModel):
    required_input_keys: List[str] = Field(default_factory=list)
    max_price: Optional[int] = Field(default=None, ge=0)
    min_pass_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_latency_ms: Optional[int] = Field(default=None, ge=0)
    verified_only: bool = True


class QuoteRequest(BaseModel):
    buyer_agent_id: str = Field(..., min_length=1)
    capability_id: str = Field(..., min_length=1)


class CheckoutRequest(BaseModel):
    quote_id: str = Field(..., min_length=1)


class CheckoutResponse(BaseModel):
    status: str
    quote_id: str
    escrow_id: str
    capability_id: str
    artifact_sha256: str
    price_paid: int
    remaining_balance: int
    artifact: str


class SettleRequest(BaseModel):
    buyer_agent_id: str = Field(..., min_length=1)
    escrow_id: str = Field(..., min_length=1)
    accepted: bool


class BalanceResponse(BaseModel):
    agent_id: str
    balance: int


def create_app(
    registry: Optional[CapabilityRegistry] = None,
    credit: Optional[MockCreditGuard] = None,
    quote_book: Optional[QuoteBook] = None,
    escrow_book: Optional[EscrowBook] = None,
) -> FastAPI:
    if registry is None:
        registry = CapabilityRegistry()
    if credit is None:
        credit = MockCreditGuard()
    if quote_book is None:
        quote_book = QuoteBook()
    if escrow_book is None:
        escrow_book = EscrowBook()

    discovery = CapabilityDiscovery(registry)
    app = FastAPI(title="Trusted A2A Capability Exchange", version="0.2.0")
    app.state.registry = registry
    app.state.credit = credit
    app.state.discovery = discovery
    app.state.quote_book = quote_book
    app.state.escrow_book = escrow_book

    @app.get("/healthz")
    def healthz() -> dict:
        return {
            "status": "ok",
            "listings": len(registry),
            "quotes": len(quote_book),
            "escrows": len(escrow_book),
        }

    @app.post("/register", response_model=RegisterResponse)
    def register(req: RegisterCapabilityRequest) -> RegisterResponse:
        try:
            scorecard = verify_artifact(req.artifact, req.eval_pack, req.sandbox_policy)
        except VerificationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        verification_status = "verified" if scorecard.verified else "failed"
        record = CapabilityRecord(
            capability_id=registry.next_capability_id(),
            manifest=req.manifest,
            artifact=req.artifact,
            artifact_sha256=scorecard.artifact_sha256,
            sandbox_policy=req.sandbox_policy,
            scorecard=scorecard,
            verification_status=verification_status,
        )
        registry.register(record)
        return RegisterResponse(
            capability_id=record.capability_id,
            verification_status=record.verification_status,
            scorecard=record.scorecard,
        )

    @app.post("/discover", response_model=List[CapabilityListing])
    def discover(req: DiscoverRequest) -> List[CapabilityListing]:
        return discovery.find_matches(
            required_input_keys=req.required_input_keys,
            max_price=req.max_price,
            min_pass_rate=req.min_pass_rate,
            max_latency_ms=req.max_latency_ms,
            verified_only=req.verified_only,
        )

    @app.post("/quote", response_model=Quote)
    def quote(req: QuoteRequest) -> Quote:
        cap = registry.get(req.capability_id)
        if cap is None:
            raise HTTPException(status_code=404, detail="capability not found")
        if not cap.scorecard.verified:
            raise HTTPException(status_code=409, detail="capability is not verified")
        return quote_book.create(
            buyer_agent_id=req.buyer_agent_id,
            capability_id=cap.capability_id,
            artifact_sha256=cap.artifact_sha256,
            price_tokens=cap.manifest.price_tokens,
            scorecard=cap.scorecard,
        )

    @app.post("/checkout", response_model=CheckoutResponse)
    def checkout(req: CheckoutRequest) -> CheckoutResponse:
        quote = quote_book.get(req.quote_id)
        if quote is None:
            raise HTTPException(status_code=404, detail="quote not found")
        if quote_book.is_expired(quote):
            raise HTTPException(status_code=410, detail="quote expired")

        cap = registry.get_by_hash(quote.artifact_sha256)
        if cap is None:
            raise HTTPException(status_code=409, detail="quoted capability version unavailable")

        ok = credit.execute_purchase(quote.buyer_agent_id, quote.price_tokens)
        if not ok:
            raise HTTPException(status_code=402, detail="insufficient credit")

        escrow = escrow_book.create(
            quote_id=quote.quote_id,
            buyer_agent_id=quote.buyer_agent_id,
            capability_id=quote.capability_id,
            artifact_sha256=quote.artifact_sha256,
            amount_tokens=quote.price_tokens,
        )
        return CheckoutResponse(
            status="unlocked",
            quote_id=quote.quote_id,
            escrow_id=escrow.escrow_id,
            capability_id=quote.capability_id,
            artifact_sha256=quote.artifact_sha256,
            price_paid=quote.price_tokens,
            remaining_balance=credit.get_or_create_balance(quote.buyer_agent_id),
            artifact=cap.artifact,
        )

    @app.post("/settle", response_model=EscrowRecord)
    def settle(req: SettleRequest) -> EscrowRecord:
        escrow = escrow_book.settle(req.escrow_id, req.buyer_agent_id, req.accepted)
        if escrow is None:
            raise HTTPException(status_code=404, detail="escrow not found")
        return escrow

    @app.get("/balance/{agent_id}", response_model=BalanceResponse)
    def balance(agent_id: str) -> BalanceResponse:
        return BalanceResponse(
            agent_id=agent_id,
            balance=credit.get_or_create_balance(agent_id),
        )

    return app


app = create_app()
```

- [ ] **Step 2: Run full tests and verify they pass**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 3: Run compile check**

Run:

```bash
PYTHONPATH=src python3 -m compileall -q src tests
```

Expected: no output and exit code 0.

- [ ] **Step 4: Commit app wiring**

```bash
git add agent交易所/src/a2a_exchange/app.py
git commit -m "feat: wire trusted exchange endpoints"
```

## Task 7: Clean Generated Files and Refresh README

**Files:**
- Modify: `README.md`
- Delete: `src/a2a_exchange/__pycache__/`
- Delete: `tests/__pycache__/`

- [ ] **Step 1: Replace README product description and endpoint table**

Update `README.md` so the opening section reads:

```markdown
# Trusted A2A Capability Exchange (v0.2 prototype)

A machine-first trusted capability trading layer where autonomous agents can
publish Python capabilities with replayable eval packs, receive a machine-readable
scorecard, and sell access through quote-locked checkout and mock escrow.

This is not a production sandbox or public marketplace. It is a local prototype
for testing whether buyer agents can evaluate capability evidence before paying.
```

Update the endpoint table to:

```markdown
| Method | Path                  | Actor  | Purpose                                      |
|--------|-----------------------|--------|----------------------------------------------|
| POST   | `/register`           | seller | verify and list a Python capability          |
| POST   | `/discover`           | buyer  | discover verified listings without artifacts |
| POST   | `/quote`              | buyer  | lock price, artifact hash, and scorecard     |
| POST   | `/checkout`           | buyer  | debit mock credit and unlock artifact        |
| POST   | `/settle`             | buyer  | release or dispute mock escrow               |
| GET    | `/balance/{agent_id}` | buyer  | inspect mock credit                          |
| GET    | `/healthz`            | -      | liveness plus listing, quote, escrow counts  |
```

Ensure the security section states:

```markdown
The verifier runs untrusted Python in a subprocess with timeouts. This is not a
security sandbox. Run only locally or on an isolated network.
```

- [ ] **Step 2: Remove generated bytecode caches**

Run:

```bash
rm -rf agent交易所/src/a2a_exchange/__pycache__ agent交易所/tests/__pycache__
```

Expected: generated cache directories are gone.

- [ ] **Step 3: Run final verification**

Run:

```bash
PYTHONPATH=src python3 -m compileall -q src tests
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: compile succeeds and all tests pass.

- [ ] **Step 4: Commit docs and cleanup**

```bash
git add agent交易所/README.md
git add -u agent交易所/src/a2a_exchange agent交易所/tests
git commit -m "docs: describe trusted capability exchange"
```

## Self-Review

Spec coverage:

- Verified Python Capability object: Task 2 and Task 3.
- Eval pack execution and scorecard: Task 2 and Task 3.
- Artifact-free discovery: Task 1 and Task 4.
- Quote locking: Task 1 and Task 5.
- Checkout through escrow: Task 1, Task 5, and Task 6.
- Settle endpoint: Task 1, Task 5, and Task 6.
- Healthz counts: Task 6.
- Required tests from the spec: Task 1 covers them as end-to-end tests.
- Security boundary and non-goals: Task 7 updates README, spec already records the boundary.

Placeholder scan:

- No `TBD`, `TODO`, `FIXME`, or unspecified implementation steps are used.
- Each implementation task includes concrete file paths, code, commands, expected results, and commits.

Type consistency:

- `CapabilityRecord.artifact_sha256` matches `Quote.artifact_sha256` and `EscrowRecord.artifact_sha256`.
- `Scorecard` is shared by register response, discovery listing, and quote snapshot.
- `CheckoutRequest` uses only `quote_id`, matching the new transaction model.
