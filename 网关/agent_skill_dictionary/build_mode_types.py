from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

HEX_RETURN = "000"
HEX_VERIFY = "001"
HEX_ISOLATE = "010"
HEX_PROMPT = "011"
HEX_HALT = "100"
HEX_INSPECT = "101"
HEX_CORRECT = "110"
HEX_CREATE = "111"

SCOPE_TAIYANG = "11"
SCOPE_SHAOYIN = "10"
SCOPE_SHAOYANG = "01"
SCOPE_TAIYIN = "00"


@dataclass(frozen=True)
class SystemStateContext:
    trace_id: str
    current_hexagram: str
    current_scope: str
    workspace_root: str
    last_exit_code: int | None = None
    consecutive_failures: int = 0
    evidence_gate_locked: bool = False
    lockdown: bool = False


@dataclass(frozen=True)
class IntentEvidence:
    yin_yang: str
    quadrant: str
    hexagram: str
    confidence: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class WriteEvidence:
    ok: bool
    changed_files: tuple[str, ...]
    path_scope: str
    patch_digest: str
    violation: str | None = None


@dataclass(frozen=True)
class SandboxEvidence:
    exit_code: int
    pytest_status: str
    stdout_sha256: str
    stderr_sha256: str
    duration_ms: int
    timed_out: bool = False
    oom: bool = False
    failure_summary: str = ""


@dataclass(frozen=True)
class ViolationEvidence:
    blocked_action: str
    reason: str
    source: str
    exit_code: int = 126


@dataclass(frozen=True)
class FeedbackEvidence:
    status: str
    source_hexagram: str
    next_hexagram: str
    summary: str
    line_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ArchiveEvidence:
    manifest_path: str
    sha256_map: dict[str, str]
    readonly_status: str
    lockdown: bool


@dataclass(frozen=True)
class TransitionPlanEvidence:
    source_hexagram: str
    target_hexagram: str
    edge_path: tuple[str, ...]
    changed_axes: tuple[str, ...]
    emergency_override: bool = False


@dataclass(frozen=True)
class BehaviorFingerprintEvidence:
    suspicious: bool
    text_sha256: str
    tool_name: str
    tool_intent: str
    text_intent: str
    reasons: tuple[str, ...]
    recommended_hexagram: str


@dataclass(frozen=True)
class EntropyDecayEvidence:
    previous_sha256: str
    current_sha256: str
    similarity_ratio: float
    base_threshold: int
    dynamic_threshold: int
    deadlock_suspected: bool


@dataclass(frozen=True)
class EvidenceEnvelope:
    node_id: str
    hexagram: str
    evidence: dict[str, Any]
    timestamp_ms: int
    evidence_sha256: str
    signature: str


def dto_to_dict(value: Any) -> dict[str, Any]:
    if not hasattr(value, "__dataclass_fields__"):
        raise TypeError("expected dataclass DTO")
    converted = _jsonable(asdict(value))
    if not isinstance(converted, dict):
        raise TypeError("expected dataclass DTO to convert to dict")
    return converted


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def evidence_allows_completion(sandbox: Any, archive: Any) -> bool:
    if not isinstance(sandbox, SandboxEvidence):
        return False
    if not isinstance(archive, ArchiveEvidence):
        return False
    return (
        sandbox.exit_code == 0
        and sandbox.pytest_status == "passed"
        and bool(sandbox.stdout_sha256)
        and bool(archive.manifest_path)
        and bool(archive.sha256_map)
    )
