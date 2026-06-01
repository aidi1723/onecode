from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any, Callable

from onecode.kernel.action_intent import ActionIntent, ActionType
from onecode.kernel.context import OneCodeContext
from onecode.kernel.path_guard import PathGuard, PathGuardError
from onecode.kernel.permission_matrix import Decision, PermissionDecision, PermissionMatrix


class LogosGate:
    def __init__(
        self,
        http_timeout_seconds: float = 60,
        permission_matrix: PermissionMatrix | None = None,
        executor_pool_size: int = 1,
    ) -> None:
        if http_timeout_seconds <= 0:
            raise ValueError("http_timeout_seconds must be greater than zero")
        if executor_pool_size <= 0:
            raise ValueError("executor_pool_size must be greater than zero")
        self.http_timeout_seconds = http_timeout_seconds
        self.permission_matrix = permission_matrix or PermissionMatrix()
        self.executor_pool_size = executor_pool_size
        self._executor: ThreadPoolExecutor | None = None

    def __enter__(self) -> "LogosGate":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=True)
            self._executor = None

    def reset_executor(self, *, wait: bool = False) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=wait, cancel_futures=True)
            self._executor = None

    def executor(self) -> ThreadPoolExecutor:
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self.executor_pool_size)
        return self._executor

    def pool_polarity(self, busy_count: int = 0) -> dict[str, float | int | str]:
        busy = min(max(busy_count, 0), self.executor_pool_size)
        idle = self.executor_pool_size - busy
        delta_phi = (busy - idle) / self.executor_pool_size
        if delta_phi > 1 / 3:
            flow_control = "throttle"
        elif delta_phi < -1 / 3:
            flow_control = "activate"
        else:
            flow_control = "stable"
        return {
            "capacity": self.executor_pool_size,
            "busy": busy,
            "idle": idle,
            "delta_phi": delta_phi,
            "flow_control": flow_control,
        }

    def next_executor_slot(self, occupancy: list[int]) -> int | None:
        for index, busy in enumerate(occupancy[: self.executor_pool_size]):
            if busy == 0:
                return index
        return None

    def preflight(self, context: OneCodeContext, intent: ActionIntent) -> PermissionDecision:
        matrix_decision = self.permission_matrix.evaluate(context.state, intent)
        if matrix_decision.decision != Decision.ALLOWED:
            return matrix_decision

        if intent.action_type in {ActionType.WRITE_TEXT, ActionType.PATCH_TEXT}:
            try:
                PathGuard.resolve_target(context.workspace_root, intent.payload["path"])
            except PathGuardError:
                return PermissionDecision(
                    decision=Decision.HALTED,
                    reason="sovereignty_breach",
                    intent_type=intent.action_type.value,
                    state=str(context.state),
                    evidence_required=[],
                )

        return matrix_decision

    def run_bounded_action(self, action: Callable[[], dict[str, Any] | None]) -> dict[str, Any]:
        future = self.executor().submit(action)
        try:
            payload = future.result(timeout=self.http_timeout_seconds)
        except TimeoutError:
            future.cancel()
            self.reset_executor(wait=False)
            return {
                "status": "halted",
                "partial": True,
                "reason": "http_timeout",
                "payload": {},
            }
        except Exception as exc:
            future.cancel()
            return {
                "status": "halted",
                "partial": True,
                "reason": "action_exception",
                "payload": {
                    "error_type": type(exc).__name__,
                    "error_message_tail": str(exc)[-1024:],
                },
            }

        return {
            "status": "completed",
            "partial": False,
            "reason": None,
            "payload": payload or {},
        }
