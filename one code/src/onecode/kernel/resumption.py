import json
from dataclasses import dataclass
from pathlib import Path

from onecode.kernel.checkpoint import sha256_file


@dataclass(frozen=True)
class ReadyAsset:
    path: str
    sha256: str
    source_run_id: str
    source_turn_index: int


@dataclass(frozen=True)
class ResumeState:
    source_run_id: str
    ready_assets: dict[str, ReadyAsset]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_asset_path(workspace_root: Path, payload_path: str) -> str | None:
    path = Path(payload_path)
    root = workspace_root.resolve()
    target = path if path.is_absolute() else root / path
    try:
        return str(target.resolve().relative_to(root))
    except ValueError:
        return None


def checkpoint_to_ready_asset(workspace_root: Path, source_run_id: str, checkpoint: dict) -> ReadyAsset | None:
    if checkpoint.get("status") != "completed":
        return None
    if checkpoint.get("intent_type") != "write_text":
        return None
    if checkpoint.get("decision") != "allowed":
        return None

    payload = checkpoint.get("payload")
    if not isinstance(payload, dict):
        return None
    payload_path = payload.get("path")
    payload_sha = payload.get("sha256")
    if not isinstance(payload_path, str) or not isinstance(payload_sha, str):
        return None

    relative_path = normalize_asset_path(workspace_root, payload_path)
    if relative_path is None:
        return None

    asset_path = workspace_root.resolve() / relative_path
    if not asset_path.exists():
        return None
    if sha256_file(asset_path) != payload_sha:
        return None

    return ReadyAsset(
        path=relative_path,
        sha256=payload_sha,
        source_run_id=source_run_id,
        source_turn_index=int(checkpoint.get("turn_index", 0)),
    )


def load_resume_state(workspace_root: Path, resume_from_run_id: str) -> ResumeState:
    root = workspace_root.resolve()
    manifest_path = root / ".onecode" / "runs" / resume_from_run_id / "manifest.json"
    if not manifest_path.exists():
        return ResumeState(source_run_id=resume_from_run_id, ready_assets={})

    manifest = load_json(manifest_path)
    ready_assets: dict[str, ReadyAsset] = {}
    for record in manifest.get("checkpoints", []):
        checkpoint_path_value = record.get("path") if isinstance(record, dict) else None
        if not isinstance(checkpoint_path_value, str):
            continue
        checkpoint_path = Path(checkpoint_path_value)
        if not checkpoint_path.exists():
            continue
        checkpoint = load_json(checkpoint_path)
        ready_asset = checkpoint_to_ready_asset(root, resume_from_run_id, checkpoint)
        if ready_asset is not None:
            ready_assets[ready_asset.path] = ready_asset

    return ResumeState(source_run_id=resume_from_run_id, ready_assets=ready_assets)
