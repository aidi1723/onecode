from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:
    class _HTTPError(Exception):
        pass

    class _ConnectError(_HTTPError):
        pass

    class _MissingHTTPX:
        HTTPError = _HTTPError
        ConnectError = _ConnectError

        @staticmethod
        def post(*args: Any, **kwargs: Any) -> Any:
            raise _ConnectError("httpx is not installed")

    httpx = _MissingHTTPX()


SNAPSHOT_PATH = Path(__file__).with_name("warehouse_snapshot.json")


def load_snapshot(path: Path = SNAPSHOT_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sync_inventory(endpoint: str, snapshot_path: Path = SNAPSHOT_PATH, max_retries: int = 3) -> dict[str, Any]:
    snapshot = load_snapshot(snapshot_path)
    attempts = 0
    while attempts <= max_retries:
        try:
            response = httpx.post(endpoint, json=snapshot, timeout=2.0)
            response.raise_for_status()
            return {"ok": True, "attempts": attempts + 1, "remote_status": response.status_code}
        except httpx.HTTPError:
            # Bug intentionally kept for the epic benchmark: attempts is never incremented,
            # so a persistent network failure can spin forever until the sandbox timeout kills it.
            time.sleep(0.01)
    return {"ok": False, "attempts": attempts}
