import hashlib
import json
import os
import fcntl
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from collections.abc import Iterator
from typing import Any

from onecode.kernel.context import OneCodeContext
from onecode.kernel.hexagram import HexagramStatusCode
from onecode.kernel.wal import wal_entry_hash

_RUN_LOCKS: dict[Path, threading.Lock] = {}
_RUN_LOCKS_GUARD = threading.Lock()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_evidence_lock(evidence_root: Path) -> threading.Lock:
    resolved = evidence_root.resolve()
    with _RUN_LOCKS_GUARD:
        lock = _RUN_LOCKS.get(resolved)
        if lock is None:
            lock = threading.Lock()
            _RUN_LOCKS[resolved] = lock
        return lock


@contextmanager
def file_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def run_evidence_write_lock(evidence_root: Path) -> Iterator[None]:
    with run_evidence_lock(evidence_root):
        with file_lock(evidence_root / ".write.lock"):
            yield


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    temp_path.replace(path)


def append_json_line(path: Path, data: dict[str, Any], *, fsync: bool = True) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(encoded)
        handle.flush()
        if fsync:
            os.fsync(handle.fileno())
    return encoded


def canonical_json_line(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def last_global_wal_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    last_hash = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if isinstance(value, dict) and isinstance(value.get("hash"), str):
            last_hash = value["hash"]
    return last_hash


def wal_rotate_limit_bytes() -> int | None:
    raw_value = os.environ.get("ONECODE_WAL_ROTATE_BYTES")
    if raw_value is None or raw_value.strip() == "":
        return None
    try:
        parsed = int(raw_value)
    except ValueError:
        raise ValueError("ONECODE_WAL_ROTATE_BYTES must be a positive integer") from None
    if parsed <= 0:
        raise ValueError("ONECODE_WAL_ROTATE_BYTES must be a positive integer")
    return parsed


def rotated_global_wal_path(wal_path: Path, index: int) -> Path:
    return wal_path.with_name(f"{wal_path.stem}.{index}{wal_path.suffix}")


def rotate_global_wal_if_needed(wal_path: Path) -> None:
    rotate_limit = wal_rotate_limit_bytes()
    if rotate_limit is None or not wal_path.exists() or wal_path.stat().st_size < rotate_limit:
        return
    index = 1
    while rotated_global_wal_path(wal_path, index).exists():
        index += 1
    wal_path.replace(rotated_global_wal_path(wal_path, index))


STATIC_PROFILE_KEYS = {
    "status_code",
    "binary",
    "math",
    "dimension",
    "triadic",
    "mutation",
    "nuclear",
    "outer_trigram",
    "inner_trigram",
    "lines",
    "liangyi",
    "outer_trigram_record",
    "inner_trigram_record",
    "trigram_records",
    "outer_element",
    "inner_element",
    "element_records",
    "element_matrix",
    "element_relation",
    "element_dynamics",
    "runtime_policy",
    "execution_bandwidth",
    "evolved_element_modulation",
    "harmony",
    "yin_yang",
    "four_symbols",
    "overlapping_four_symbols",
    "four_symbol_balance",
    "transition",
    "dispatch_decision",
    "rule_layers",
}


def static_profile_projection(profile: dict[str, Any]) -> dict[str, Any]:
    return {key: profile[key] for key in sorted(STATIC_PROFILE_KEYS) if key in profile}


def profile_sha256(profile: dict[str, Any]) -> str:
    return sha256_text(canonical_json_line(static_profile_projection(profile)))


def profile_registry_ref(profile_hash: str) -> str:
    return f".onecode/profile-registry/{profile_hash}.json"


def workspace_relative_path(workspace_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def ensure_profile_registry_entry(workspace_root: Path, profile: dict[str, Any] | None) -> str | None:
    if profile is None:
        return None
    digest = profile_sha256(profile)
    path = workspace_root / profile_registry_ref(digest)
    registry_root = path.parent
    with file_lock(registry_root / ".registry.lock"):
        if not path.exists():
            static_profile = static_profile_projection(profile)
            atomic_write_json(path, static_profile)
            atomic_write_json(path.with_suffix(".json.bak"), static_profile)
        elif not path.with_suffix(".json.bak").exists():
            atomic_write_json(path.with_suffix(".json.bak"), json.loads(path.read_text(encoding="utf-8")))
    return profile_registry_ref(digest)


def compact_iching_profile(
    profile: dict[str, Any] | None,
    *,
    registry_ref: str | None = None,
) -> dict[str, Any] | None:
    if profile is None:
        return None
    digest = profile_sha256(profile)
    yin_yang = profile.get("yin_yang")
    if not isinstance(yin_yang, dict):
        yin_yang = {}
    transition = profile.get("transition")
    if not isinstance(transition, dict):
        transition = {}
    runtime_policy = profile.get("runtime_policy")
    if not isinstance(runtime_policy, dict):
        runtime_policy = {}
    element_dynamics = profile.get("element_dynamics")
    if not isinstance(element_dynamics, dict):
        element_dynamics = {}
    harmony = profile.get("harmony")
    if not isinstance(harmony, dict):
        harmony = {}
    return {
        "profile_format": "compact_v1",
        "profile_sha256": digest,
        "profile_registry_ref": registry_ref or profile_registry_ref(digest),
        "status_code": profile.get("status_code"),
        "binary": profile.get("binary"),
        "dispatch_decision": profile.get("dispatch_decision"),
        "transition": {
            "status_code": transition.get("status_code"),
            "action": transition.get("action"),
            "reason": transition.get("reason"),
        },
        "runtime_policy": {
            "action": runtime_policy.get("action"),
            "reason": runtime_policy.get("reason"),
        },
        "inner_trigram": profile.get("inner_trigram"),
        "outer_trigram": profile.get("outer_trigram"),
        "inner_element": profile.get("inner_element"),
        "outer_element": profile.get("outer_element"),
        "element_relation": profile.get("element_relation"),
        "element_dynamics": {
            "relation": element_dynamics.get("relation"),
            "cross_relation": element_dynamics.get("cross_relation"),
            "modulation": element_dynamics.get("modulation"),
            "yin_yang_pressure": element_dynamics.get("yin_yang_pressure"),
        },
        "yin_yang": {
            "balance": yin_yang.get("balance"),
            "pressure": yin_yang.get("pressure"),
            "yang_count": yin_yang.get("yang_count"),
            "yin_count": yin_yang.get("yin_count"),
        },
        "harmony": {
            "score": harmony.get("score"),
            "relation": harmony.get("relation"),
        },
    }


def compact_completed_evidence_profile(
    status: str,
    partial: bool,
    reason: str | None,
    profile: dict[str, Any] | None,
    registry_ref: str | None = None,
) -> dict[str, Any] | None:
    if status == "completed" and not partial and reason is None:
        return compact_iching_profile(profile, registry_ref=registry_ref)
    return profile


def compact_completed_ledger_result(
    result: dict[str, Any],
    *,
    registry_ref: str | None = None,
) -> dict[str, Any]:
    if result.get("status") != "completed" or result.get("partial") is True or result.get("reason") is not None:
        return result
    compacted = dict(result)
    if isinstance(compacted.get("iching_profile"), dict):
        compacted["iching_profile"] = compact_iching_profile(compacted["iching_profile"], registry_ref=registry_ref)
    assets = compacted.get("assets")
    if isinstance(assets, list):
        compacted_assets = []
        for asset in assets:
            if not isinstance(asset, dict):
                compacted_assets.append(asset)
                continue
            compacted_asset = dict(asset)
            if isinstance(compacted_asset.get("iching_profile"), dict):
                compacted_asset["iching_profile"] = compact_iching_profile(
                    compacted_asset["iching_profile"],
                    registry_ref=registry_ref,
                )
            compacted_assets.append(compacted_asset)
        compacted["assets"] = compacted_assets
    return compacted


def global_wal_entry(context: OneCodeContext, result: dict[str, Any]) -> dict[str, Any]:
    profile = result.get("iching_profile")
    compact_profile = profile if isinstance(profile, dict) else {}
    profile_hash = compact_profile.get("profile_sha256")
    profile_ref = compact_profile.get("profile_registry_ref")
    evidence_mode = result.get("evidence_mode", "full")
    entry = {
        "v": 1,
        "ts": utc_now_iso(),
        "em": evidence_mode,
        "rid": result.get("run_id"),
        "st": result.get("status"),
        "pc": bool(result.get("partial")),
        "rs": result.get("reason"),
        "it": result.get("intent_type"),
        "rc": result.get("requested_count"),
        "cc": result.get("completed_count"),
        "sc": result.get("skipped_count"),
        "fc": result.get("failed_count"),
        "isc": result.get("iching_status_code"),
        "ita": result.get("iching_transition_action"),
        "ph": profile_hash,
        "pr": profile_ref,
        "lp": None if evidence_mode == "wal" else workspace_relative_path(context.workspace_root, context.evidence_root / "ledger.json"),
        "mp": None if evidence_mode == "wal" else workspace_relative_path(context.workspace_root, context.manifest_path),
    }
    if evidence_mode == "wal":
        wal_assets = global_wal_asset_entries(result)
        if wal_assets:
            entry["as"] = wal_assets
    return entry


def global_wal_asset_entries(result: dict[str, Any]) -> list[dict[str, Any]]:
    assets = result.get("assets")
    if not isinstance(assets, list):
        return []
    entries = []
    for asset in assets:
        if not isinstance(asset, dict) or asset.get("status") != "completed":
            continue
        intent_type = asset.get("intent_type")
        if intent_type not in {"write_text", "patch_text"}:
            continue
        payload = asset.get("payload")
        if not isinstance(payload, dict):
            continue
        path = payload.get("path")
        sha256 = payload.get("sha256")
        if not isinstance(path, str) or not isinstance(sha256, str):
            continue
        entry = {
            "p": path,
            "s": sha256,
            "i": intent_type,
            "t": asset.get("index"),
        }
        if intent_type == "patch_text":
            for source_key, target_key in (
                ("pre_sha256", "pre"),
                ("post_sha256", "post"),
                ("search_block_sha256", "search"),
                ("replace_block_sha256", "replace"),
            ):
                value = payload.get(source_key)
                if isinstance(value, str):
                    entry[target_key] = value
        entries.append(entry)
    return entries


def append_global_wal_entry(context: OneCodeContext, result: dict[str, Any], *, fsync: bool = True) -> str:
    wal_path = context.workspace_root / ".onecode" / "global-ledger.jsonl"
    with file_lock(wal_path.with_suffix(".lock")):
        rotate_global_wal_if_needed(wal_path)
        entry = global_wal_entry(context, result)
        entry["prev"] = last_global_wal_hash(wal_path)
        entry["hash"] = wal_entry_hash(entry)
        return append_json_line(wal_path, entry, fsync=fsync)


def write_global_wal(context: OneCodeContext, result: dict[str, Any], *, fsync: bool = True) -> Path:
    registry_ref = None
    if result.get("status") == "completed" and result.get("partial") is not True and result.get("reason") is None:
        profile = result.get("iching_profile")
        registry_ref = ensure_profile_registry_entry(context.workspace_root, profile if isinstance(profile, dict) else None)
    evidence_result = compact_completed_ledger_result(result, registry_ref=registry_ref)
    append_global_wal_entry(context, evidence_result, fsync=fsync)
    return context.workspace_root / ".onecode" / "global-ledger.jsonl"


def evidence_chain_hash(record: dict[str, Any]) -> str:
    return sha256_text(canonical_json_line({key: value for key, value in record.items() if key != "chain_hash"}))


def read_last_evidence_chain_record(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    last_line = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            last_line = line
    if not last_line:
        return None
    value = json.loads(last_line)
    if not isinstance(value, dict):
        raise ValueError("invalid evidence chain record")
    return value


def append_evidence_chain_record(
    evidence_root: Path,
    *,
    artifact_type: str,
    artifact_path: Path,
    artifact_sha256: str,
    artifact_line_number: int | None = None,
) -> dict[str, Any]:
    chain_path = evidence_root / "evidence-chain.jsonl"
    previous_record = read_last_evidence_chain_record(chain_path)
    previous_hash = previous_record.get("chain_hash") if previous_record else "0" * 64
    previous_sequence = previous_record.get("sequence") if previous_record else 0
    sequence = previous_sequence + 1 if isinstance(previous_sequence, int) else 1
    record = {
        "sequence": sequence,
        "artifact_type": artifact_type,
        "artifact_path": str(artifact_path),
        "artifact_sha256": artifact_sha256,
        "previous_chain_hash": previous_hash,
        "created_at": utc_now_iso(),
    }
    if artifact_line_number is not None:
        record["artifact_line_number"] = artifact_line_number
    record["chain_hash"] = evidence_chain_hash(record)
    append_json_line(chain_path, record)
    return record


def read_manifest(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def ready_assets_summary(context: OneCodeContext) -> dict[str, dict[str, Any]]:
    if context.resume_state is None:
        return {}
    return {
        path: {
            "sha256": asset.sha256,
            "source_run_id": asset.source_run_id,
            "source_turn_index": asset.source_turn_index,
        }
        for path, asset in sorted(context.resume_state.ready_assets.items())
    }


def resume_audit_events_summary(context: OneCodeContext) -> list[dict[str, Any]]:
    if context.resume_state is None:
        return []
    return list(context.resume_state.audit_events)


def write_checkpoint(
    context: OneCodeContext,
    payload: dict[str, Any],
    next_state: HexagramStatusCode,
    status: str,
    partial: bool,
    reason: str | None,
    intent_type: str | None = None,
    decision: str | None = None,
    iching_status_code: int | None = None,
    iching_transition_action: str | None = None,
    iching_transition_reason: str | None = None,
    iching_profile: dict[str, Any] | None = None,
    duration_ms: int = 0,
    run_control: dict[str, Any] | None = None,
) -> Path:
    with run_evidence_write_lock(context.evidence_root):
        existing_manifest = read_manifest(context.manifest_path)
        existing_checkpoints = []
        if existing_manifest is not None:
            existing_checkpoints = list(existing_manifest.get("checkpoints", []))

        turn_number = len(existing_checkpoints) + 1
        checkpoint_path = context.evidence_root / "checkpoints" / f"{turn_number:04d}.json"
        resumed_from = context.resume_from_run_id
        ready_assets = ready_assets_summary(context)
        resume_audit_events = resume_audit_events_summary(context)
        registry_ref = None
        if status == "completed" and not partial and reason is None:
            registry_ref = ensure_profile_registry_entry(context.workspace_root, iching_profile)
        evidence_profile = compact_completed_evidence_profile(status, partial, reason, iching_profile, registry_ref)
        checkpoint = {
            "run_id": context.run_id,
            "turn_index": turn_number,
            "previous_state": str(context.state),
            "next_state": str(next_state),
            "status": status,
            "partial": partial,
            "reason": reason,
            "intent_type": intent_type,
            "decision": decision,
            "iching_status_code": iching_status_code,
            "iching_transition_action": iching_transition_action,
            "iching_transition_reason": iching_transition_reason,
            "iching_profile": evidence_profile,
            "duration_ms": duration_ms,
            "run_control": run_control,
            "resumed_from": resumed_from,
            "ready_assets": ready_assets,
            "resume_audit_events": resume_audit_events,
            "created_at": utc_now_iso(),
            "payload": payload,
        }
        atomic_write_json(checkpoint_path, checkpoint)

        checkpoint_hash = sha256_file(checkpoint_path)
        checkpoint_record = {
            "path": str(checkpoint_path),
            "sha256": checkpoint_hash,
            "turn_index": turn_number,
            "status": status,
            "partial": partial,
            "reason": reason,
            "intent_type": intent_type,
            "decision": decision,
            "iching_status_code": iching_status_code,
            "iching_transition_action": iching_transition_action,
            "iching_transition_reason": iching_transition_reason,
            "iching_profile": evidence_profile,
            "duration_ms": duration_ms,
            "run_control": run_control,
            "resumed_from": resumed_from,
            "ready_assets": ready_assets,
            "resume_audit_events": resume_audit_events,
        }
        if intent_type == "patch_text":
            patch_evidence_keys = [
                "pre_sha256",
                "post_sha256",
                "search_block_sha256",
                "replace_block_sha256",
            ]
            patch_evidence = {
                key: payload[key]
                for key in patch_evidence_keys
                if isinstance(payload.get(key), str)
            }
            if patch_evidence:
                checkpoint_record["patch_evidence"] = patch_evidence
        manifest = {
            "run_id": context.run_id,
            "created_at": existing_manifest.get("created_at") if existing_manifest else utc_now_iso(),
            "updated_at": utc_now_iso(),
            "workspace_root": str(context.workspace_root),
            "current_state": str(next_state),
            "status": status,
            "partial": partial,
            "reason": reason,
            "iching_status_code": iching_status_code,
            "iching_transition_action": iching_transition_action,
            "iching_transition_reason": iching_transition_reason,
            "iching_profile": evidence_profile,
            **(run_control or {}),
            "resumed_from": resumed_from,
            "ready_assets": ready_assets,
            "resume_audit_events": resume_audit_events,
            "checkpoints": existing_checkpoints + [checkpoint_record],
        }
        atomic_write_json(context.manifest_path, manifest)
        return checkpoint_path


def write_ledger(context: OneCodeContext, result: dict[str, Any]) -> Path:
    ledger_path = context.evidence_root / "ledger.json"
    ledger_history_path = context.evidence_root / "ledger.jsonl"
    registry_ref = None
    if result.get("status") == "completed" and result.get("partial") is not True and result.get("reason") is None:
        profile = result.get("iching_profile")
        registry_ref = ensure_profile_registry_entry(context.workspace_root, profile if isinstance(profile, dict) else None)
    evidence_result = compact_completed_ledger_result(result, registry_ref=registry_ref)
    with run_evidence_write_lock(context.evidence_root):
        atomic_write_json(ledger_path, evidence_result)
        ledger_line = append_json_line(ledger_history_path, evidence_result)
        line_count = sum(
            1
            for line in ledger_history_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
        append_evidence_chain_record(
            context.evidence_root,
            artifact_type="ledger",
            artifact_path=ledger_history_path,
            artifact_sha256=sha256_text(ledger_line),
            artifact_line_number=line_count,
        )
        append_global_wal_entry(context, evidence_result)
    return ledger_path
