"""Terminal-mode model task execution."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable



def _run_terminal_model_task(
    *,
    task: str,
    workspace: Path,
    active_provider: Any,
    model_context: Any,
    trace_path: Path,
    sandbox_config: Any | None,
    max_repair_attempts: int,
    on_turn: Callable[[dict[str, Any]], None] | None,
    resolved_model: str,
    http_timeout_seconds: float = 60.0,
    approval_mode: str = "strict",
    require_explicit_approval: bool = True,
    execution_approval: Callable[[Any], bool] | None = None,
    plan_approval: Callable[[Any], bool] | None = None,
) -> dict[str, Any]:
    from onecode.kernel.model_loop import _record_kernel_fault
    from onecode.kernel.model_repair import _with_sandbox_tests, ledger_fields_for_iching
    from onecode.kernel.terminal_loop import TerminalAction, TerminalStep, run_terminal_session

    max_turns = max(10, max_repair_attempts * 3)
    auto_approved_for_eval = (approval_mode == "scoped_auto") or (not require_explicit_approval and execution_approval is None)
    term_approval_callback: Callable[[TerminalAction], bool] | None = None
    if execution_approval is not None:
        term_approval_callback = execution_approval

    if trace_path.exists():
        try:
            trace_path.unlink()
        except OSError:
            pass

    class _TerminalProviderAdapter:
        def __init__(self, inner: Any, model: str, timeout: float) -> None:
            self.inner = inner
            self.model = model
            self.timeout = timeout

        def complete(self, prompt: str) -> str:
            if hasattr(self.inner, "complete"):
                try:
                    return str(self.inner.complete(prompt, model=self.model, http_timeout_seconds=self.timeout))
                except TypeError:
                    return str(self.inner.complete(prompt))
            if callable(self.inner):
                return str(self.inner(prompt))
            raise RuntimeError(f"Provider {self.inner!r} has no complete method and is not callable")

        def __call__(self, prompt: str) -> str:
            return self.complete(prompt)

    adapted_provider = _TerminalProviderAdapter(active_provider, resolved_model, http_timeout_seconds)

    def on_step_callback(step: TerminalStep) -> None:
        try:
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            with open(trace_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "step_type": "terminal_step",
                    "turn_index": step.turn_index,
                    "action": step.action.to_dict(),
                    "observation": step.observation.to_dict(),
                    "hexagram_code": step.hexagram_code,
                    "timestamp_ns": step.timestamp_ns,
                }) + "\n")
        except OSError:
            pass
        if on_turn is not None:
            try:
                on_turn({
                    "turn": step.turn_index,
                    "action": step.action.to_dict(),
                    "observation": step.observation.to_dict(),
                    "hexagram_code": step.hexagram_code,
                })
            except Exception as ex:
                _record_kernel_fault("terminal_on_turn", ex)

    term_result = run_terminal_session(
        task,
        workspace,
        adapted_provider,
        max_turns=max_turns,
        approval_mode=approval_mode,
        execution_approval=term_approval_callback,
        auto_approved_for_eval=auto_approved_for_eval,
        on_step=on_step_callback,
    )

    is_completed = term_result.get("status") == "completed"
    status = "completed" if is_completed else "halted"
    reason = term_result.get("explanation") if is_completed else term_result.get("reason", "terminal_loop_halted")
    iching_code = 63 if is_completed else (40 if term_result.get("reason") in {"stagnation_loop", "preset_test_immutable"} else 39)

    steps_list = term_result.get("steps", [])
    applied_patches = [
        s["action"] for s in steps_list
        if s.get("action", {}).get("action_type") == "patch"
    ]
    modified_paths: list[str] = []
    for p in applied_patches:
        path_str = p.get("path")
        if path_str and path_str not in modified_paths:
            modified_paths.append(path_str)

    raw_result: dict[str, Any] = {
        "status": status,
        "reason": reason,
        "detail": term_result.get("error") or reason,
        "error": term_result.get("error"),
        **ledger_fields_for_iching(iching_code),
        "repair_attempt_count": len(applied_patches),
        "turns_completed": term_result.get("turns_completed", 0),
        "terminal_steps": steps_list,
        "applied_patches": applied_patches,
        "modified_files": modified_paths,
        "written": modified_paths,
        "run_id": model_context.run_id,
        "trace_path": str(trace_path),
        "agent_mode": "terminal",
        "resolved_model": resolved_model,
        "approval_mode": term_result.get("approval_mode", approval_mode),
        "auto_approved_for_eval": term_result.get("auto_approved_for_eval", auto_approved_for_eval),
        "approved_actions_count": term_result.get("approved_actions_count", 0),
        "blocked_approvals_count": term_result.get("blocked_approvals_count", 0),
    }

    verified = _with_sandbox_tests(raw_result, workspace, sandbox_config)

    if verified.get("status") == "completed" and verified.get("reason") != "verifier_failed":
        try:
            from onecode.kernel.checkpoint import write_global_wal
            write_global_wal(model_context, verified)
            verified["wal_write_status"] = "ok"
        except OSError as ex:
            verified["wal_write_status"] = "failed"
            verified["wal_write_error_count"] = verified.get("wal_write_error_count", 0) + 1
            verified.setdefault("warnings", []).append(f"wal_write_failed: {type(ex).__name__}: {ex}")

    return verified


