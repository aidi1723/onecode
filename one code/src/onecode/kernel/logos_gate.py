from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any, Callable

from onecode.kernel.action_intent import ActionIntent, ActionType
from onecode.kernel.context import OneCodeContext
from onecode.kernel.path_guard import PathGuard, PathGuardError
from onecode.kernel.permission_matrix import Decision, PermissionDecision, PermissionMatrix


class LogosGate:
    def __init__(self, http_timeout_seconds: float = 60, permission_matrix: PermissionMatrix | None = None) -> None:
        if http_timeout_seconds <= 0:
            raise ValueError("http_timeout_seconds must be greater than zero")
        self.http_timeout_seconds = http_timeout_seconds
        self.permission_matrix = permission_matrix or PermissionMatrix()

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
