"""Terminal-mode model task execution."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from onecode.kernel.terminal_loop import TerminalAction, TerminalStep, run_terminal_session


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


def _write_trace_and_notify_turn(
    trace_path: Path,
    step: TerminalStep,
    on_turn: Callable[[dict[str, Any]], None] | None,
    phase_tracker: dict[str, Any] | None = None,
) -> None:
    from onecode.kernel.model_loop import _record_kernel_fault
    from onecode.kernel.hypercube_vector import (
        StateVector6D,
        PhaseSpaceState12D,
        DEFAULT_DIAGONAL_MASS,
    )

    try:
        vec = StateVector6D.from_discrete_code(step.hexagram_code)
        p_coords = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        if phase_tracker is not None:
            last_vec = phase_tracker.get("last_vec")
            last_ns = phase_tracker.get("last_ns", 0)
            if last_vec is not None and isinstance(last_vec, StateVector6D):
                dt = max(0.5, (step.timestamp_ns - last_ns) / 1e9) if (step.timestamp_ns and last_ns) else 1.0
                p_list = []
                for i in range(6):
                    v_i = (vec.coords[i] - last_vec.coords[i]) / dt
                    p_i = DEFAULT_DIAGONAL_MASS[i] * v_i
                    p_list.append(round(p_i, 4))
                p_coords = tuple(p_list)  # type: ignore[assignment]
            phase_tracker["last_vec"] = vec
            phase_tracker["last_ns"] = step.timestamp_ns

        phase = PhaseSpaceState12D.from_vectors(vec, p_coords)
        t_energy = phase.kinetic_energy()
        v_energy = vec.lyapunov_energy()
        h_total = phase.hamiltonian()
        pos_code, mom_code = phase.to_jiao_yanshou_dual_codes()

        spatial_info = {
            "coords": list(vec.coords),
            "momentum": list(p_coords),
            "kinetic_energy": round(t_energy, 6),
            "lyapunov_energy": round(v_energy, 6),
            "hamiltonian": round(h_total, 6),
            "jiao_yanshou_dual": [pos_code, mom_code],
            "project_3d": [round(x, 4) for x in vec.project_3d()],
        }
    except Exception:
        spatial_info = None

    step_payload = {
        "step_type": "terminal_step",
        "turn_index": step.turn_index,
        "action": step.action.to_dict(),
        "observation": step.observation.to_dict(),
        "hexagram_code": step.hexagram_code,
        "timestamp_ns": step.timestamp_ns,
    }
    if spatial_info is not None:
        step_payload["spatial_vector"] = spatial_info

    try:
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with open(trace_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(step_payload) + "\n")
    except OSError:
        pass
    if on_turn is not None:
        try:
            turn_payload = {
                "turn": step.turn_index,
                "action": step.action.to_dict(),
                "observation": step.observation.to_dict(),
                "hexagram_code": step.hexagram_code,
            }
            if spatial_info is not None:
                turn_payload["spatial_vector"] = spatial_info
            on_turn(turn_payload)
        except Exception as ex:
            _record_kernel_fault("terminal_on_turn", ex)


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
    max_turns: int | None = None,
    phased: bool = False,
    execution_scope: str = "full_terminal",
    rollback_on_failure: bool = False,
) -> dict[str, Any]:
    from onecode.kernel.model_repair import _with_sandbox_tests, ledger_fields_for_iching

    effective_rollback = rollback_on_failure or (
        os.environ.get("ONECODE_ROLLBACK_ON_FAILURE", "").lower() in {"1", "true", "yes"}
    )
    if max_turns is None or max_turns < 1:
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

    adapted_provider = _TerminalProviderAdapter(active_provider, resolved_model, http_timeout_seconds)

    phase_tracker: dict[str, Any] = {}

    def on_step_callback(step: TerminalStep) -> None:
        _write_trace_and_notify_turn(trace_path, step, on_turn, phase_tracker=phase_tracker)

    effective_phased = phased or (os.environ.get("ONECODE_PHASED_SESSION", "").lower() in {"1", "true", "yes"})
    if effective_phased:
        from onecode.kernel.phased_terminal import run_phased_terminal_session
        term_result = run_phased_terminal_session(
            task,
            workspace,
            adapted_provider,
            max_turns=max_turns,
            approval_mode=approval_mode,
            execution_approval=term_approval_callback,
            auto_approved_for_eval=auto_approved_for_eval,
            on_step=on_step_callback,
            execution_scope=execution_scope,
            rollback_on_failure=effective_rollback,
        )
    else:
        term_result = run_terminal_session(
            task,
            workspace,
            adapted_provider,
            max_turns=max_turns,
            approval_mode=approval_mode,
            execution_approval=term_approval_callback,
            auto_approved_for_eval=auto_approved_for_eval,
            on_step=on_step_callback,
            execution_scope=execution_scope,
            rollback_on_failure=effective_rollback,
        )

    is_completed = term_result.get("status") == "completed"
    status = "completed" if is_completed else "halted"
    reason = term_result.get("explanation") if is_completed else term_result.get("reason", "terminal_loop_halted")
    iching_code = 63 if is_completed else (40 if term_result.get("reason") in {"stagnation_loop", "preset_test_immutable"} else 39)

    steps_list = term_result.get("steps", [])
    applied_patches = [
        s["action"] for s in steps_list
        if s.get("action", {}).get("action_type") in {"patch", "write_file"}
    ]
    modified_paths: list[str] = []
    for p in applied_patches:
        path_str = p.get("path")
        if path_str and path_str not in modified_paths:
            modified_paths.append(path_str)
    command_modified_files: list[str] = []
    for cmd_path in term_result.get("command_modified_files", []):
        if isinstance(cmd_path, str) and cmd_path:
            if cmd_path not in command_modified_files:
                command_modified_files.append(cmd_path)
            if cmd_path not in modified_paths:
                modified_paths.append(cmd_path)

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
        "command_modified_files": command_modified_files,
        "modified_files": modified_paths,
        "written": modified_paths,
        "requested_count": len(modified_paths),
        "completed_count": len(modified_paths) if is_completed else 0,
        "skipped_count": 0,
        "failed_count": 0 if is_completed else 1,
        "run_id": model_context.run_id,
        "trace_path": str(trace_path),
        "agent_mode": "phased_terminal" if effective_phased else "terminal",
        "resolved_model": resolved_model,
        "approval_mode": term_result.get("approval_mode", approval_mode),
        "auto_approved_for_eval": term_result.get("auto_approved_for_eval", auto_approved_for_eval),
        "approved_actions_count": term_result.get("approved_actions_count", 0),
        "blocked_approvals_count": term_result.get("blocked_approvals_count", 0),
        "phase1_turns": term_result.get("phase1_turns"),
        "phase2_turns": term_result.get("phase2_turns"),
        "phase1_summary": term_result.get("phase1_summary"),
    }
    if "rollback" in term_result:
        raw_result["rollback"] = term_result["rollback"]

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
