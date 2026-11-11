"""Two-phase session orchestration for autonomous terminal exploration.

Phase 1: Investigation & Root-Cause Analysis (Plan isolation).
Phase 2: Surgical Implementation & Verification (Clean context execution).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from onecode.kernel.terminal_loop import (
    TerminalAction,
    TerminalStep,
    run_terminal_session,
)


def _format_phase1_task(task: str, plan_turns: int) -> str:
    return (
        f"[PHASE 1: INVESTIGATION & ROOT-CAUSE ANALYSIS (BUDGET: {plan_turns} TURNS)]\n\n"
        f"USER TASK:\n{task}\n\n"
        "PHASE 1 DIRECTIVES:\n"
        "1. Inspect the codebase using 'read_file' and inspection commands (git status, git diff, grep, find, pytest, etc.).\n"
        "2. Locate the bug, reproduce it if helpful, and identify the exact files and functions to modify.\n"
        "3. DO NOT write or modify test files (tests are immutable across all languages).\n"
        "4. Focus on diagnosis and repair strategy. Do not apply patches in Phase 1.\n"
        "5. Once your investigation is complete, submit an action_type='finish' with your detailed explanation covering:\n"
        "   - (a) Root cause explanation\n"
        "   - (b) Exact target files and functions to patch\n"
        "   - (c) Specific patch and verification plan\n"
        "Your finish explanation will be distilled and handed over to Phase 2 with a clean context."
    )


def _format_phase2_task(task: str, plan_summary: str) -> str:
    return (
        f"[PHASE 2: IMPLEMENTATION & VERIFICATION]\n\n"
        f"USER TASK:\n{task}\n\n"
        f"INVESTIGATION FINDINGS & REPAIR PLAN FROM PHASE 1:\n"
        f"\"\"\"\n{plan_summary}\n\"\"\"\n\n"
        "PHASE 2 DIRECTIVES:\n"
        "1. Root cause and target locations are already diagnosed above in the Phase 1 plan. "
        "Proceed directly to applying the surgical patch with 'patch'. Avoid redundant re-reading of the entire codebase.\n"
        "2. Do NOT touch or modify test files (tests are strictly immutable across all languages).\n"
        "3. Run tests or reproduction commands to verify your changes resolve the issue without regressions.\n"
        "4. When verified or when all planned patches are in place, submit action_type='finish' immediately to conclude the task."
    )


def _extract_plan_summary(phase1_result: dict[str, Any]) -> str:
    explanation = (phase1_result.get("explanation") or "").strip()
    if explanation:
        return explanation
    steps = phase1_result.get("steps", [])
    if not steps:
        return "Phase 1 completed with no recorded exploration steps."

    lines: list[str] = ["Automated summary of Phase 1 investigation:"]
    read_paths: list[str] = []
    executed_cmds: list[str] = []
    last_explanations: list[str] = []

    for s in steps:
        action = s.get("action", {})
        act_type = action.get("action_type")
        act_expl = (action.get("explanation") or "").strip()
        if act_expl and act_expl not in last_explanations:
            last_explanations.append(act_expl)
        if act_type == "read_file":
            p = action.get("path")
            if p and p not in read_paths:
                read_paths.append(str(p))
        elif act_type == "command":
            cmd = action.get("command")
            if cmd:
                cmd_str = " ".join(cmd) if isinstance(cmd, (list, tuple)) else str(cmd)
                executed_cmds.append(cmd_str)

    if read_paths:
        lines.append(f"- Inspected source files: {', '.join(read_paths[:10])}")
    if executed_cmds:
        lines.append(f"- Executed commands: {'; '.join(executed_cmds[-5:])}")
    if last_explanations:
        lines.append("- Hypotheses & Findings:")
        for exp in last_explanations[-4:]:
            lines.append(f"  * {exp}")

    for s in reversed(steps):
        obs = s.get("observation", {})
        stderr = (obs.get("stderr") or "").strip()
        stdout = (obs.get("stdout") or "").strip()
        if stderr or (obs.get("exit_code", 0) != 0 and stdout):
            snippet = (stderr or stdout)[-600:].strip()
            lines.append(f"- Diagnostic output tail:\n{snippet}")
            break

    return "\n".join(lines)


def run_phased_terminal_session(
    task: str,
    workspace: Path,
    provider: Any,
    *,
    max_turns: int = 15,
    plan_turns: int = 5,
    require_modification: bool = True,
    approval_mode: str = "strict",
    execution_approval: Callable[[TerminalAction], bool] | None = None,
    auto_approved_for_eval: bool = False,
    on_step: Callable[[TerminalStep], None] | None = None,
    execution_scope: str = "full_terminal",
    rollback_on_failure: bool = False,
) -> dict[str, Any]:
    """Runs a two-phase terminal session: Phase 1 (Plan/Investigation) -> Phase 2 (Execute/Verify)."""
    if max_turns < 4:
        return run_terminal_session(
            task,
            workspace,
            provider,
            max_turns=max_turns,
            require_modification=require_modification,
            approval_mode=approval_mode,
            execution_approval=execution_approval,
            auto_approved_for_eval=auto_approved_for_eval,
            on_step=on_step,
            execution_scope=execution_scope,
            rollback_on_failure=rollback_on_failure,
        )

    phase1_max = min(plan_turns, max(2, max_turns // 3))
    phase1_task = _format_phase1_task(task, phase1_max)

    def phase1_approval(action: TerminalAction) -> bool:
        if action.action_type == "patch":
            return False
        if execution_approval is not None:
            return execution_approval(action)
        return True

    phase1_steps_recorded: list[TerminalStep] = []

    def phase1_on_step(step: TerminalStep) -> None:
        phase1_steps_recorded.append(step)
        if on_step is not None:
            on_step(step)

    phase1_result = run_terminal_session(
        phase1_task,
        workspace,
        provider,
        max_turns=phase1_max,
        require_modification=False,
        approval_mode="strict",
        execution_approval=phase1_approval,
        auto_approved_for_eval=False,
        on_step=phase1_on_step,
        execution_scope="read_only",
    )

    p1_reason = phase1_result.get("reason", "")
    if p1_reason in {"preset_test_immutable", "provider_error"}:
        return phase1_result

    plan_summary = _extract_plan_summary(phase1_result)
    phase1_step_count = len(phase1_result.get("steps", []))
    remaining_turns = max_turns - phase1_step_count

    if remaining_turns < 1:
        return phase1_result

    phase2_task = _format_phase2_task(task, plan_summary)

    def phase2_on_step(step: TerminalStep) -> None:
        if on_step is not None:
            offset_step = TerminalStep(
                turn_index=phase1_step_count + step.turn_index,
                action=step.action,
                observation=step.observation,
                hexagram_code=step.hexagram_code,
                timestamp_ns=step.timestamp_ns,
            )
            on_step(offset_step)

    phase2_result = run_terminal_session(
        phase2_task,
        workspace,
        provider,
        max_turns=remaining_turns,
        require_modification=require_modification,
        approval_mode=approval_mode,
        execution_approval=execution_approval,
        auto_approved_for_eval=auto_approved_for_eval,
        on_step=phase2_on_step,
        execution_scope=execution_scope,
        rollback_on_failure=rollback_on_failure,
    )

    combined_steps: list[dict[str, Any]] = []
    for s in phase1_result.get("steps", []):
        combined_steps.append(dict(s))
    for s in phase2_result.get("steps", []):
        step_dict = dict(s)
        step_dict["turn_index"] = phase1_step_count + step_dict.get("turn_index", 1)
        combined_steps.append(step_dict)

    result_dict: dict[str, Any] = {
        "status": phase2_result.get("status", "halted"),
        "reason": phase2_result.get("reason", "unknown"),
        "explanation": phase2_result.get("explanation", ""),
        "error": phase2_result.get("error"),
        "turns_completed": len(combined_steps),
        "steps": combined_steps,
        "approval_mode": approval_mode,
        "auto_approved_for_eval": auto_approved_for_eval,
        "approved_actions_count": (
            phase1_result.get("approved_actions_count", 0)
            + phase2_result.get("approved_actions_count", 0)
        ),
        "blocked_approvals_count": (
            phase1_result.get("blocked_approvals_count", 0)
            + phase2_result.get("blocked_approvals_count", 0)
        ),
        "phase1_turns": phase1_step_count,
        "phase2_turns": len(phase2_result.get("steps", [])),
        "phase1_summary": plan_summary,
        "phase1_status": phase1_result.get("status"),
        "phase2_status": phase2_result.get("status"),
    }
    if "rollback" in phase2_result:
        result_dict["rollback"] = phase2_result["rollback"]
    return result_dict
