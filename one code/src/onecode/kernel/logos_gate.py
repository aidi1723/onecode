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

    def executor(self) -> ThreadPoolExecutor:
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self.executor_pool_size)
        return self._executor

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
            return {
                "status": "halted",
                "partial": True,
                "reason": "http_timeout",
                "payload": {},
            }

        return {
            "status": "completed",
            "partial": False,
            "reason": None,
            "payload": payload or {},
        }
