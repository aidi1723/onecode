import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

from onecode.kernel.checkpoint import sha256_file


class PathGuardError(ValueError):
    pass


_INTERRUPTED_WRITE = re.compile(r"\A\..+\.[A-Za-z0-9]{8}\Z")


class PathGuard:
    DENIED_ROOT_FILES = {"pyproject.toml", ".gitignore", ".env"}
    DENIED_EXECUTABLE_ROOT_FILES = {
        ".pre-commit-config.yaml",
        "Makefile",
        "setup.cfg",
        "setup.py",
    }
    DENIED_DIRECTORIES = {".git", ".github", ".onecode"}

    @classmethod
    def write_text(cls, workspace_root: Path, relative_path: str, content: str) -> dict[str, str]:
        target = cls.resolve_target(workspace_root, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        temp_path: str | None = None
        try:
            with NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, prefix=f".{target.name}.", delete=False) as handle:
                temp_path = handle.name
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            if target.exists():
                os.chmod(temp_path, target.stat().st_mode & 0o777)
            os.replace(temp_path, target)
            temp_path = None
        finally:
            if temp_path is not None:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

        return {"path": str(target), "sha256": sha256_file(target)}

    @classmethod
    def discard_interrupted_writes(cls, workspace_root: Path) -> list[str]:
        root = workspace_root.resolve()
        removed: list[str] = []
        if not root.is_dir():
            return removed
        for directory, dirnames, filenames in os.walk(root):
            dirnames[:] = [name for name in dirnames if name not in cls.DENIED_DIRECTORIES]
            for name in filenames:
                if _INTERRUPTED_WRITE.fullmatch(name) is None:
                    continue
                path = Path(directory) / name
                path.unlink(missing_ok=True)
                removed.append(path.relative_to(root).as_posix())
        return removed

    @classmethod
    def resolve_target(cls, workspace_root: Path, relative_path: str) -> Path:
        requested = cls._requested_relative_path(relative_path)
        if not requested.parts:
            raise PathGuardError("path must not be empty")
        cls._reject_lexical_controls(requested)
        root = workspace_root.resolve()
        cls._reject_symlinks(root, requested)
        target = (root / requested).resolve()
        try:
            resolved_relative = target.relative_to(root)
        except ValueError as exc:
            raise PathGuardError("path escapes workspace root") from exc
        cls._reject_lexical_controls(resolved_relative)
        return target

    @classmethod
    def resolve_read_target(cls, workspace_root: Path, relative_path: str) -> Path:
        requested = cls._requested_relative_path(relative_path)
        if ".." in requested.parts:
            raise PathGuardError("path traversal is not allowed")
        if cls.is_sensitive_read_path(requested):
            raise PathGuardError("sensitive paths are not readable")

        root = workspace_root.resolve()
        target = (root / requested).resolve()
        try:
            resolved_relative = target.relative_to(root)
        except ValueError as exc:
            raise PathGuardError("path escapes workspace root") from exc
        if cls.is_sensitive_read_path(resolved_relative):
            raise PathGuardError("sensitive paths are not readable")
        return target

    @staticmethod
    def resolve_contained(root: Path, candidate: str | Path) -> Path:
        if not isinstance(candidate, (str, Path)) or str(candidate) == "":
            raise PathGuardError("path must be a non-empty string")
        root_resolved = root.resolve()
        raw = Path(candidate)
        target = raw if raw.is_absolute() else root_resolved / raw
        resolved = target.resolve()
        try:
            resolved.relative_to(root_resolved)
        except ValueError as exc:
            raise PathGuardError("path escapes evidence root") from exc
        return resolved

    @staticmethod
    def is_sensitive_read_path(path: Path) -> bool:
        return any(
            part.casefold() == ".git" or part.casefold() == ".env" or part.casefold().startswith(".env.")
            for part in path.parts
        )

    @classmethod
    def _requested_relative_path(cls, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or relative_path == "":
            raise PathGuardError("path must be a non-empty relative string")
        if "\x00" in relative_path:
            raise PathGuardError("path contains a null byte")
        if len(relative_path) > 4_096:
            raise PathGuardError("path is too long")
        requested = Path(relative_path)
        if requested.is_absolute():
            raise PathGuardError("absolute paths are not allowed")
        if not requested.parts and relative_path not in {".", "./"}:
            raise PathGuardError("path must not be empty")
        return requested

    @classmethod
    def _reject_lexical_controls(cls, path: Path) -> None:
        folded = tuple(part.casefold() for part in path.parts)
        if ".." in path.parts:
            raise PathGuardError("path traversal is not allowed")
        if ".git" in folded:
            raise PathGuardError("paths under .git are not allowed")
        if ".github" in folded:
            raise PathGuardError("github automation writes are not allowed")
        if ".onecode" in folded:
            raise PathGuardError("paths under .onecode are not allowed")
        denied_root = {name.casefold() for name in cls.DENIED_ROOT_FILES | cls.DENIED_EXECUTABLE_ROOT_FILES}
        if len(folded) == 1 and (folded[0] in denied_root or folded[0].startswith(".env.")):
            raise PathGuardError("root configuration writes are not allowed")

    @staticmethod
    def _reject_symlinks(root: Path, requested: Path) -> None:
        current = root
        for part in requested.parts:
            current = current / part
            if current.is_symlink():
                raise PathGuardError("symlink paths are not allowed")
