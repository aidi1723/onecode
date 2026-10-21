from pathlib import Path

from onecode.kernel.path_guard import PathGuard


def stage_bytes(workspace: Path, relative_path: str, content: bytes, *, approved: bool) -> Path:
    if not approved:
        raise PermissionError("host staging requires approval")
    target = PathGuard.resolve_target(workspace, relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return target
