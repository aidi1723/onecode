from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any, Callable


class LogosGate:
    def __init__(self, http_timeout_seconds: float = 60) -> None:
        if http_timeout_seconds <= 0:
            raise ValueError("http_timeout_seconds must be greater than zero")
        self.http_timeout_seconds = http_timeout_seconds

    def run_bounded_action(self, action: Callable[[], dict[str, Any] | None]) -> dict[str, Any]:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(action)
        try:
            payload = future.result(timeout=self.http_timeout_seconds)
        except TimeoutError:
            future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
            return {
                "status": "halted",
                "partial": True,
                "reason": "http_timeout",
                "payload": {},
            }
        finally:
            if future.done():
                executor.shutdown(wait=True, cancel_futures=True)

        return {
            "status": "completed",
            "partial": False,
            "reason": None,
            "payload": payload or {},
        }
