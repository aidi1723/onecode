"""At most three read-only subagents, merged with the existing status aggregate."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from onecode.kernel.agent_cycle import READ_ONLY_TOOLS, Execute, Proposal, run_agent_cycle
from onecode.kernel.evidence_io import ensure_private_file
from onecode.kernel.hexagram import IchingKernel


MAX_SUBAGENTS = 3
_AGENT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
ProposeAgent = Callable[[str, list[dict[str, Any]], frozenset[str]], list[Proposal]]


def run_read_only_subagents(
    *,
    workspace: Path,
    agents: list[dict[str, str]],
    propose: ProposeAgent,
    execute: Execute,
    max_turns: int = 4,
) -> dict[str, Any]:
    if len(agents) > MAX_SUBAGENTS:
        return _stopped("resource_budget_exceeded")
    identities = [agent.get("id") for agent in agents]
    if any(not isinstance(agent_id, str) or _AGENT_ID.fullmatch(agent_id) is None for agent_id in identities):
        return _stopped("malformed_input")
    if len(set(identities)) != len(identities):
        return _stopped("malformed_input")
    records = [
        _run_one(workspace, str(agent["id"]), str(agent.get("task", "")), propose, execute, max_turns)
        for agent in agents
    ]
    halted = next((record for record in records if record["status"] != "completed"), None)
    return {
        "status": "halted" if halted is not None else "completed",
        "reason": None if halted is None else halted["reason"],
        "status_code": IchingKernel.aggregate_status([record["status_code"] for record in records]),
        "subagents": records,
    }


def _run_one(
    workspace: Path,
    agent_id: str,
    task: str,
    propose: ProposeAgent,
    execute: Execute,
    max_turns: int,
) -> dict[str, Any]:
    def agent_propose(history: list[dict[str, Any]], allowed: frozenset[str], task: str = task) -> list[Proposal]:
        return propose(task, history, allowed)

    result = run_agent_cycle(
        propose=agent_propose,
        execute=_read_only_execute(execute),
        max_turns=max_turns,
        task=task,
        workspace=workspace,
        remember=False,
        approve=lambda tool_name, params: False,
    )
    status_code = IchingKernel.classify_outcome(result["status"], result.get("reason"))
    evidence_dir = workspace.resolve() / ".onecode" / "subagents" / agent_id
    payload = {
        "id": agent_id,
        "status": result["status"],
        "reason": result.get("reason"),
        "status_code": status_code,
        "turn_count": result.get("turn_count"),
    }
    path = evidence_dir / "result.json"
    ensure_private_file(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return {**payload, "evidence_dir": str(evidence_dir)}


def _read_only_execute(execute: Execute) -> Execute:
    def wrapped(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        if tool_name not in READ_ONLY_TOOLS:
            return {"status": "halted", "reason": "permission_denied"}
        return execute(tool_name, params)

    return wrapped


def _stopped(reason: str) -> dict[str, Any]:
    return {
        "status": "halted",
        "reason": reason,
        "status_code": IchingKernel.classify_outcome("halted", reason),
        "subagents": [],
    }
