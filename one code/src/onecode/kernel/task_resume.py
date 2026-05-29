import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.resumption import sha256_file
from onecode.kernel.verifier import VerifierSpec


DecisionKind = Literal["ready", "apply", "verify", "halt", "discover"]
TargetType = Literal["asset", "verifier", "task"]


@dataclass(frozen=True)
class PlannedAsset:
    path: str
    content: str


@dataclass(frozen=True)
class TaskResumeDecision:
    kind: DecisionKind
    target_type: TargetType
    target_id: str
    reason: str | None
    status_code: int
    transition_action: str
    transition_reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TaskResumeSummary:
    decisions: list[TaskResumeDecision]
    status_code: int
    transition_action: str
    transition_reason: str
    dispatch_decision: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_resume_decisions": [decision.to_dict() for decision in self.decisions],
            "task_resume_status_code": self.status_code,
            "task_resume_transition_action": self.transition_action,
            "task_resume_transition_reason": self.transition_reason,
            "task_resume_dispatch_decision": self.dispatch_decision,
        }


def decision_status_code(kind: DecisionKind, reason: str | None) -> int:
    if kind == "ready":
        return IchingKernel.classify_resume_audit("ready", None)
    if kind in {"apply", "verify"}:
        return IchingKernel.classify_resume_audit("ignored", reason or "missing_file")
    if kind == "halt":
        return IchingKernel.classify_resume_audit("halted", reason)
    return IchingKernel.classify_outcome("halted", "unknown")


def make_decision(
    kind: DecisionKind,
    target_type: TargetType,
    target_id: str,
    reason: str | None,
) -> TaskResumeDecision:
    status_code = decision_status_code(kind, reason)
    transition = IchingKernel.transition(status_code)
    return TaskResumeDecision(
        kind=kind,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        status_code=status_code,
        transition_action=transition.action,
        transition_reason=transition.reason,
    )


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("task_resume_corrupt_json")
    return data


def checkpoint_payloads_by_path(workspace: Path, manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    checkpoints = manifest.get("checkpoints", [])
    if not isinstance(checkpoints, list):
        raise ValueError("task_resume_corrupt_manifest")
    for record in checkpoints:
        if not isinstance(record, dict) or record.get("status") != "completed":
            continue
        checkpoint_path_value = record.get("path")
        if not isinstance(checkpoint_path_value, str):
            continue
        checkpoint_path = Path(checkpoint_path_value)
        if not checkpoint_path.exists():
            continue
        if "sha256" in record and sha256_file(checkpoint_path) != record["sha256"]:
            raise ValueError("checkpoint_hash_mismatch")
        checkpoint = read_json(checkpoint_path)
        if checkpoint is None:
            continue
        payload = checkpoint.get("payload")
        if not isinstance(payload, dict):
            continue
        payload_path = payload.get("path")
        payload_sha = payload.get("sha256")
        if not isinstance(payload_path, str) or not isinstance(payload_sha, str):
            continue
        target = (workspace.resolve() / payload_path).resolve()
        try:
            relative_path = str(target.relative_to(workspace.resolve()))
        except ValueError as exc:
            raise ValueError("checkpoint_path_outside_workspace") from exc
        result[relative_path] = payload
    return result


def verifier_by_id(ledger: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if ledger is None:
        return {}
    verifiers = ledger.get("verifier_results", [])
    if not isinstance(verifiers, list):
        return {}
    return {
        verifier["id"]: verifier
        for verifier in verifiers
        if isinstance(verifier, dict) and isinstance(verifier.get("id"), str)
    }


def verifier_matches_spec(result: dict[str, Any], spec: VerifierSpec) -> bool | None:
    command = result.get("command")
    cwd = result.get("cwd")
    timeout_ms = result.get("timeout_ms")
    if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
        return None
    if not isinstance(cwd, str):
        return None
    if timeout_ms is not None and not isinstance(timeout_ms, int):
        return None
    return command == spec.command and cwd == spec.cwd and (timeout_ms is None or timeout_ms == spec.timeout_ms)


def classify_verifier(spec: VerifierSpec, prior: dict[str, dict[str, Any]]) -> TaskResumeDecision:
    result = prior.get(spec.id)
    if result is None:
        return make_decision("apply", "verifier", spec.id, "missing_verifier_evidence")
    matches = verifier_matches_spec(result, spec)
    if matches is None:
        return make_decision("discover", "verifier", spec.id, "verifier_evidence_unmapped")
    if not matches:
        return make_decision("halt", "verifier", spec.id, "verifier_policy_changed")
    if result.get("status") == "passed":
        return make_decision("ready", "verifier", spec.id, None)
    return make_decision("halt", "verifier", spec.id, result.get("reason") or "verifier_failed")


def aggregate_summary(decisions: list[TaskResumeDecision]) -> TaskResumeSummary:
    if any(decision.kind == "halt" for decision in decisions):
        status_code = IchingKernel.classify_resume_audit("halted", "task_resume_halt")
    elif any(decision.kind == "discover" for decision in decisions):
        status_code = IchingKernel.classify_outcome("halted", "unknown")
    elif all(decision.kind == "ready" for decision in decisions):
        status_code = IchingKernel.classify_resume_audit("ready", None)
    else:
        status_code = IchingKernel.classify_resume_audit("ignored", "task_resume_apply")
    transition = IchingKernel.transition(status_code)
    return TaskResumeSummary(
        decisions=decisions,
        status_code=status_code,
        transition_action=transition.action,
        transition_reason=transition.reason,
        dispatch_decision=IchingKernel.dispatch_decision(transition),
    )


def classify_task_resume(
    workspace: Path,
    source_run_id: str,
    planned_assets: list[PlannedAsset],
    verifier_specs: list[VerifierSpec],
) -> TaskResumeSummary:
    source_root = workspace.resolve() / ".onecode" / "runs" / source_run_id
    manifest_path = source_root / "manifest.json"
    ledger_path = source_root / "ledger.json"
    decisions: list[TaskResumeDecision] = []

    if not manifest_path.exists():
        for asset in planned_assets:
            decisions.append(make_decision("apply", "asset", asset.path, "missing_source_manifest"))
        for spec in verifier_specs:
            decisions.append(make_decision("apply", "verifier", spec.id, "missing_source_manifest"))
        return aggregate_summary(decisions)

    try:
        manifest = read_json(manifest_path)
        ledger = read_json(ledger_path)
        payloads = checkpoint_payloads_by_path(workspace, manifest or {})
    except (json.JSONDecodeError, ValueError):
        decisions.append(make_decision("halt", "task", source_run_id, "source_evidence_corrupt"))
        return aggregate_summary(decisions)

    prior_verifiers = verifier_by_id(ledger)
    verifier_decisions = [classify_verifier(spec, prior_verifiers) for spec in verifier_specs]
    all_verifiers_ready = bool(verifier_specs) and all(decision.kind == "ready" for decision in verifier_decisions)

    for asset in planned_assets:
        payload = payloads.get(asset.path)
        if payload is None:
            decisions.append(make_decision("apply", "asset", asset.path, "missing_asset_evidence"))
            continue
        target = workspace.resolve() / asset.path
        expected_sha = payload.get("sha256")
        if not target.exists():
            decisions.append(make_decision("apply", "asset", asset.path, "missing_physical_asset"))
            continue
        if not isinstance(expected_sha, str) or sha256_file(target) != expected_sha:
            decisions.append(make_decision("halt", "asset", asset.path, "asset_hash_conflict"))
            continue
        if verifier_specs and not all_verifiers_ready:
            decisions.append(make_decision("verify", "asset", asset.path, "missing_verifier_evidence"))
        else:
            decisions.append(make_decision("ready", "asset", asset.path, None))

    decisions.extend(verifier_decisions)
    return aggregate_summary(decisions)
