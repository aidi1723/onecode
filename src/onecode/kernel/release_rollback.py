"""Snapshot and restore a local kernel release without touching the running source tree."""

from __future__ import annotations

import json
import re
from pathlib import Path

from onecode.kernel.model_config import write_private_text


_VERSION = re.compile(r"\A[0-9A-Za-z][0-9A-Za-z._-]{0,31}\Z")
_HISTORY = ".onecode/release-history"
_RELEASES = ".onecode/releases"


def snapshot_release(root: Path, version: str) -> Path:
    _check_version(version)
    base = Path(root).resolve()
    destination = base / _RELEASES / version
    if destination.exists():
        raise ValueError("release snapshot already exists")
    destination.mkdir(parents=True)
    copied = []
    for relative in ("VERSION", "config.json"):
        source = base / relative
        if source.is_file():
            _store(destination, relative, source.read_bytes())
            copied.append(relative)
    pending = base / ".onecode" / "pending-cycle"
    if pending.is_dir():
        for source in sorted(pending.glob("*.json")):
            relative = source.relative_to(base).as_posix()
            _store(destination, relative, source.read_bytes())
            copied.append(relative)
    _store(destination, "manifest.json", json.dumps({"version": version, "files": copied}, sort_keys=True).encode() + b"\n")
    _append_history(base, version)
    return destination


def stage_release(root: Path, version: str, files: dict[str, str]) -> None:
    _check_version(version)
    base = Path(root).resolve()
    for relative, content in files.items():
        _checked_relative(relative)
        if not isinstance(content, str):
            raise ValueError("release file content must be text")
        target = base / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        write_private_text(target, content)
    version_path = base / "VERSION"
    if "VERSION" not in files:
        write_private_text(version_path, version + "\n")
    _append_history(base, version)


def rollback_release(root: Path) -> dict[str, str]:
    base = Path(root).resolve()
    history = _read_history(base)
    if len(history) < 2:
        raise ValueError("no previous release")
    previous = history[-2]
    snapshot = base / _RELEASES / previous
    manifest_path = snapshot / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("release snapshot is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("files")
    if manifest.get("version") != previous or not isinstance(files, list):
        raise ValueError("release snapshot is invalid")
    current_pending = base / ".onecode" / "pending-cycle"
    if current_pending.is_dir():
        for path in current_pending.glob("*.json"):
            path.unlink()
    for relative in files:
        if not isinstance(relative, str):
            raise ValueError("release snapshot is invalid")
        _checked_relative(relative)
        source = snapshot / relative
        target = base / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        write_private_text(target, source.read_text(encoding="utf-8"))
    write_private_text(base / "VERSION", previous + "\n")
    _write_history(base, history[:-1])
    return {"version": previous}


def _check_version(version: str) -> None:
    if not isinstance(version, str) or _VERSION.fullmatch(version) is None:
        raise ValueError("release version is invalid")


def _checked_relative(relative: str) -> None:
    if not isinstance(relative, str) or relative == "" or "\\" in relative or "\x00" in relative:
        raise ValueError("release path is invalid")
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or relative.startswith(".onecode/releases"):
        raise ValueError("release path is invalid")


def _store(snapshot: Path, relative: str, content: bytes) -> None:
    target = snapshot / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    write_private_text(target, content.decode("utf-8"))


def _append_history(root: Path, version: str) -> None:
    history = _read_history(root)
    history.append(version)
    _write_history(root, history)


def _read_history(root: Path) -> list[str]:
    path = root / _HISTORY
    if not path.is_file():
        return []
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line]


def _write_history(root: Path, history: list[str]) -> None:
    path = root / _HISTORY
    path.parent.mkdir(parents=True, exist_ok=True)
    write_private_text(path, "".join(f"{item}\n" for item in history))
