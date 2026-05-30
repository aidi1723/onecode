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
