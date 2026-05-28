import hashlib
import json
from pathlib import Path


PLAN_ASSET_FIELDS = {"path", "content"}


def read_plan_json(path: Path) -> tuple[dict | None, str | None]:
    if not path.exists():
        return None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, "invalid_json"
    if not isinstance(data, dict):
        return None, "non_object_json"
    return data, None


def sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_task_plan(path: Path) -> tuple[str, list[str], dict]:
    resolved_path = path.resolve()
    data, corrupt_reason = read_plan_json(path)
    if corrupt_reason is not None:
        raise ValueError(f"invalid plan: {corrupt_reason}")
    if data is None:
        raise ValueError("invalid plan: missing_file")
    task = data.get("task", "plan")
    if not isinstance(task, str) or not task:
        raise ValueError("invalid plan: task must be a non-empty string")
    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("invalid plan: assets must be a non-empty list")

    write_texts = []
    seen_paths = set()
    for index, asset in enumerate(assets, start=1):
        if not isinstance(asset, dict):
            raise ValueError(f"invalid plan asset {index}: asset must be an object")
        unknown_fields = sorted(set(asset) - PLAN_ASSET_FIELDS)
        if unknown_fields:
            raise ValueError(f"invalid plan asset {index}: unknown fields {', '.join(unknown_fields)}")
        path = asset.get("path")
        content = asset.get("content")
        if not isinstance(path, str) or not path:
            raise ValueError(f"invalid plan asset {index}: path must be a non-empty string")
        if not isinstance(content, str):
            raise ValueError(f"invalid plan asset {index}: content must be a string")
        if path in seen_paths:
            raise ValueError(f"invalid plan asset {index}: duplicate path {path}")
        seen_paths.add(path)
        write_texts.append(f"{path}={content}")
    plan_evidence = {
        "plan_path": str(resolved_path),
        "plan_sha256": sha256_bytes(resolved_path),
        "plan_asset_count": len(write_texts),
    }
    return task, write_texts, plan_evidence
