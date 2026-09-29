"""Bounded multi-turn tool cycle controlled by the existing hexagram policy."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from onecode.kernel.agent_memory import compact_agent_history, remember_turn
from onecode.kernel.outcome_policy import agent_cycle_decision


READ_ONLY_TOOLS = frozenset({"read_text", "list_files", "search_text", "git_status", "git_diff", "glob_files", "outline"})
ALL_TOOLS = READ_ONLY_TOOLS | frozenset({"write_text", "patch_text", "run_command", "git_commit"})
Proposal = dict[str, Any]
Propose = Callable[[list[dict[str, Any]], frozenset[str]], list[Proposal]]
Execute = Callable[[str, dict[str, Any]], dict[str, Any]]


def run_agent_cycle(
    *,
    propose: Propose,
    execute: Execute,
    max_turns: int = 8,
    task: str = "",
    max_history_chars: int | None = None,
    workspace: Path | None = None,
    remember: bool = False,
) -> dict[str, Any]:
    if isinstance(max_turns, bool) or not isinstance(max_turns, int) or max_turns <= 0:
        raise ValueError("max_turns must be a positive integer")
    history: list[dict[str, Any]] = []
    allowed = ALL_TOOLS
    for _turn in range(max_turns):
        visible = _visible_history(task, history, max_history_chars)
        proposal = list(propose(visible, allowed) or [])
        if not proposal:
            result = {"status": "completed", "reason": None, "turn_count": len(history) + 1, "turns": history}
            _maybe_remember(workspace, remember, {"role": "task", "text": task}, "model_continue", result)
            return result
        observation = _run_proposal(proposal[:2], allowed, execute)
        history.append(observation)
        decision = agent_cycle_decision(observation["status"], observation["reason"])
        observation["cycle"] = decision
        if decision["cycle"] == "stop":
            return _halt(observation["reason"], history)
        if decision["cycle"] == "verify":
            return _halt(observation["reason"] or "action_exception", history)
        if decision["cycle"] == "read_only_continue":
            allowed = READ_ONLY_TOOLS
        else:
            allowed = ALL_TOOLS
    decision = agent_cycle_decision("halted", "resource_budget_exceeded")
    return {
        "status": "halted",
        "reason": "resource_budget_exceeded",
        "turn_count": len(history),
        "turns": history,
        "cycle": decision,
    }


def _visible_history(task: str, history: list[dict[str, Any]], max_history_chars: int | None) -> list[dict[str, Any]]:
    if max_history_chars is None:
        return history
    return compact_agent_history(task, history, max_history_chars)


def _maybe_remember(
    workspace: Path | None,
    remember: bool,
    record: dict[str, Any],
    cycle: str,
    result: dict[str, Any],
) -> None:
    if workspace is None or not remember:
        return
    if remember_turn(workspace, record, confirmed=True, cycle=cycle):
        result["memory_path"] = str(workspace.resolve() / ".onecode" / "memory.jsonl")


def _run_proposal(proposal: list[Proposal], allowed: frozenset[str], execute: Execute) -> dict[str, Any]:
    calls = []
    for call in proposal:
        tool_name = call.get("tool_name")
        params = call.get("params") if isinstance(call.get("params"), dict) else {}
        if not isinstance(tool_name, str) or not _tool_allowed(tool_name, allowed):
            return {
                "status": "halted",
                "reason": "permission_denied",
                "tool_name": tool_name if isinstance(tool_name, str) else "",
                "calls": calls,
            }
        outcome = execute(tool_name, params)
        record = {
            "tool_name": tool_name,
            "status": outcome.get("status", "completed"),
            "reason": outcome.get("reason"),
        }
        calls.append(record)
        if record["status"] != "completed" or record["reason"] not in {None, "search_miss", "path_not_found"}:
            return {**record, "calls": calls}
    last = calls[-1]
    return {**last, "calls": calls}


def _tool_allowed(tool_name: str, allowed: frozenset[str]) -> bool:
    if tool_name in allowed:
        return True
    if allowed != ALL_TOOLS or not tool_name.startswith("mcp."):
        return False
    server, dot, remote = tool_name.removeprefix("mcp.").partition(".")
    return bool(dot) and _mcp_segment(server) and _mcp_segment(remote)


def _mcp_segment(value: str) -> bool:
    return bool(value) and len(value) <= 64 and value.replace("-", "").replace("_", "").isalnum()


def _halt(reason: str | None, history: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "halted",
        "reason": reason,
        "turn_count": len(history),
        "turns": history,
        "cycle": history[-1].get("cycle") if history else None,
    }
