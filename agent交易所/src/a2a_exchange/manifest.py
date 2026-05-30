"""Models for verified Python capabilities."""
from __future__ import annotations

from typing import Any, Dict, List, Literal

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
    artifact_sha256: str = Field(..., min_length=64, max_length=64)
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


# Temporary compatibility alias while app/registry/discovery are replaced in later tasks.
AgentCapabilityManifest = CapabilityManifest
