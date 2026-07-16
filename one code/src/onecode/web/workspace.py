from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def configured_allowed_workspace_roots() -> list[Path]:
    raw_roots = os.getenv("ONECODE_ALLOWED_WORKSPACE_ROOTS", "")
    roots = [part for part in raw_roots.split(os.pathsep) if part.strip()]
    if not roots:
        roots = [os.getenv("ONECODE_WORKSPACE_ROOT", os.getcwd())]
    return [Path(root).expanduser().resolve() for root in roots]


def path_inside_root(path: Path, root: Path) -> bool:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    return resolved_path == resolved_root or resolved_root in resolved_path.parents


def workspace_allowed(workspace: Path, roots: list[Path] | None = None) -> bool:
    allowed_roots = roots if roots is not None else configured_allowed_workspace_roots()
    return any(path_inside_root(workspace, root) for root in allowed_roots)


def require_allowed_workspace(workspace: Path) -> Path:
    resolved = workspace.resolve()
    if not workspace_allowed(resolved):
        raise ValueError(f"workspace outside allowed workspace roots: {resolved}")
    return resolved


def workspace_from_value(value: str | None) -> Path:
    workspace = Path(
        value if isinstance(value, str) and value.strip() else os.getenv("ONECODE_WORKSPACE_ROOT", os.getcwd())
    ).expanduser().resolve()
    if not workspace.exists() or not workspace.is_dir():
        raise ValueError(f"workspace does not exist or is not a directory: {workspace}")
    return require_allowed_workspace(workspace)


def explicit_task_workspace_required() -> bool:
    return os.getenv("ONECODE_REQUIRE_EXPLICIT_TASK_WORKSPACE", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def request_workspace_value(body: dict[str, Any]) -> str | None:
    metadata = body.get("metadata")
    workspace_value = metadata.get("workspace") if isinstance(metadata, dict) else None
    if not isinstance(workspace_value, str) or not workspace_value.strip():
        return None
    return workspace_value.strip()


def workspace_from_request(
    body: dict[str, Any], *, require_explicit: bool = False
) -> Path:
    workspace_value = request_workspace_value(body)
    if require_explicit and workspace_value is None:
        raise ValueError("workspace_required")
    return workspace_from_value(workspace_value)
