import hashlib
import json
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from onecode.kernel.hexagram import IchingKernel


VerifierStatus = Literal["passed", "failed", "skipped"]
TAIL_LIMIT = 4096


@dataclass(frozen=True)
class VerifierSpec:
    id: str
    command: list[str]
    cwd: str
    timeout_ms: int

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or self.id == "":
            raise ValueError("verifier id must be a non-empty string")
        if not isinstance(self.command, list) or not self.command:
            raise ValueError("verifier command must be a non-empty string list")
        if not all(isinstance(part, str) and part != "" for part in self.command):
            raise ValueError("verifier command must be a non-empty string list")
        if not isinstance(self.cwd, str) or self.cwd == "":
            raise ValueError("verifier cwd must be a non-empty string")
        if not isinstance(self.timeout_ms, int) or self.timeout_ms <= 0:
            raise ValueError("verifier timeout_ms must be positive")


@dataclass(frozen=True)
class VerifierResult:
    id: str
    status: VerifierStatus
    reason: str | None
    exit_code: int | None
    duration_ms: int
    stdout_tail: str
    stderr_tail: str
    stdout_sha256: str
    stderr_sha256: str
    cwd: str
    command: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerifierPolicy:
    specs: dict[str, VerifierSpec]

    def require(self, verifier_id: str) -> VerifierSpec:
        try:
            return self.specs[verifier_id]
        except KeyError as exc:
            raise ValueError(f"unknown verifier id: {verifier_id}") from exc


def load_verifier_policy(path: Path) -> VerifierPolicy:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError("invalid verifier policy: missing_file") from exc
    except json.JSONDecodeError as exc:
        raise ValueError("invalid verifier policy: invalid_json") from exc
    if not isinstance(data, dict):
        raise ValueError("invalid verifier policy: root must be an object")
    verifiers = data.get("verifiers")
    if not isinstance(verifiers, list):
        raise ValueError("invalid verifier policy: verifiers must be a list")
    specs: dict[str, VerifierSpec] = {}
    for index, value in enumerate(verifiers, start=1):
        if not isinstance(value, dict):
            raise ValueError(f"invalid verifier {index}: verifier must be an object")
        unknown_fields = sorted(set(value) - {"id", "command", "cwd", "timeout_ms"})
        if unknown_fields:
            raise ValueError(f"invalid verifier {index}: unknown fields: {', '.join(unknown_fields)}")
        spec = VerifierSpec(
            id=value.get("id", ""),
            command=value.get("command", []),
            cwd=value.get("cwd", ""),
            timeout_ms=value.get("timeout_ms", 0),
        )
        if spec.id in specs:
            raise ValueError(f"duplicate verifier id: {spec.id}")
        specs[spec.id] = spec
    return VerifierPolicy(specs=specs)


def resolve_verifier_cwd(workspace: Path, cwd: str) -> Path:
    workspace_root = workspace.resolve()
    resolved = (workspace_root / cwd).resolve()
    if resolved != workspace_root and workspace_root not in resolved.parents:
        raise ValueError("verifier cwd outside workspace")
    return resolved


def tail_text(value: bytes) -> str:
    return value[-TAIL_LIMIT:].decode("utf-8", errors="replace")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def run_verifier(workspace: Path, spec: VerifierSpec) -> VerifierResult:
    resolved_cwd = resolve_verifier_cwd(workspace, spec.cwd)
    started_at = time.monotonic()
    stdout = b""
    stderr = b""
    try:
        completed = subprocess.run(
            spec.command,
            cwd=resolved_cwd,
            capture_output=True,
            timeout=spec.timeout_ms / 1000,
            check=False,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        status: VerifierStatus = "passed" if completed.returncode == 0 else "failed"
        reason = None if completed.returncode == 0 else "verifier_failed"
        exit_code: int | None = completed.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, bytes) else b""
        stderr = exc.stderr if isinstance(exc.stderr, bytes) else b""
        status = "failed"
        reason = "verifier_timeout"
        exit_code = None
    duration_ms = int((time.monotonic() - started_at) * 1000)
    return VerifierResult(
        id=spec.id,
        status=status,
        reason=reason,
        exit_code=exit_code,
        duration_ms=duration_ms,
        stdout_tail=tail_text(stdout),
        stderr_tail=tail_text(stderr),
        stdout_sha256=sha256_bytes(stdout),
        stderr_sha256=sha256_bytes(stderr),
        cwd=spec.cwd,
        command=list(spec.command),
    )


def validate_selected_verifiers(workspace: Path, policy: VerifierPolicy, verifier_ids: list[str]) -> list[VerifierSpec]:
    specs = [policy.require(verifier_id) for verifier_id in verifier_ids]
    for spec in specs:
        resolve_verifier_cwd(workspace, spec.cwd)
    return specs


def task_status_from_results(asset_result: dict[str, Any], verifier_results: list[VerifierResult]) -> dict[str, Any]:
    status_codes = [
        asset.get("raw_status_code")
        for asset in asset_result.get("assets", [])
        if isinstance(asset, dict) and isinstance(asset.get("raw_status_code"), int)
    ]
    for result in verifier_results:
        status_codes.append(
            IchingKernel.classify_outcome(
                "completed" if result.status == "passed" else "halted",
                result.reason,
            )
        )
    entropy = IchingKernel.entropy_regulated_status(status_codes)
    status_code = int(entropy["status_code"])
    transition = IchingKernel.transition(status_code)
    return {
        "task_status_code": status_code,
        "task_transition_action": transition.action,
        "task_transition_reason": transition.reason,
        "task_dispatch_decision": IchingKernel.dispatch_decision(transition),
        "task_entropy": entropy["entropy"],
        "task_entropy_decision": entropy["decision"],
        "task_entropy_reason": entropy.get("reason"),
    }
