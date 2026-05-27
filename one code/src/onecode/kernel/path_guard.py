import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from onecode.kernel.checkpoint import sha256_file


class PathGuardError(ValueError):
    pass


class PathGuard:
    DENIED_ROOT_FILES = {"pyproject.toml", ".gitignore", ".env"}

    @classmethod
    def write_text(cls, workspace_root: Path, relative_path: str, content: str) -> dict[str, str]:
        target = cls.resolve_target(workspace_root, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        with NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.replace(target)

        return {"path": str(target), "sha256": sha256_file(target)}

    @classmethod
    def resolve_target(cls, workspace_root: Path, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or relative_path == "":
            raise PathGuardError("path must be a non-empty relative string")

        requested = Path(relative_path)
        if requested.is_absolute():
            raise PathGuardError("absolute paths are not allowed")

        parts = requested.parts
        if not parts:
            raise PathGuardError("path must not be empty")
        if parts[0] == ".git":
            raise PathGuardError("paths under .git are not allowed")
        if len(parts) == 1 and (parts[0] in cls.DENIED_ROOT_FILES or parts[0].startswith(".env.")):
            raise PathGuardError("root configuration writes are not allowed")

        root = workspace_root.resolve()
        target = (root / requested).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise PathGuardError("path escapes workspace root") from exc
        return target
