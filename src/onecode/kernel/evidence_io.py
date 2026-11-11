from __future__ import annotations

import hashlib
import json
import os
import fcntl
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


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
        temp_path = handle.name
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, path)


def ensure_private_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
    finally:
        os.close(descriptor)


def append_json_line(path: Path, data: dict[str, Any], *, fsync: bool = True) -> str:
    ensure_private_file(path)
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(encoded)
        handle.flush()
        if fsync:
            os.fsync(handle.fileno())
    return encoded


def canonical_json_line(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
