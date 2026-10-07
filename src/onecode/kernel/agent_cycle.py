"""Bounded multi-turn tool cycle controlled by the existing hexagram policy."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from onecode.kernel.agent_memory import compact_agent_history, remember_turn
from onecode.kernel.cycle_approvals import find_pending_approval, persist_pending_approval
from onecode.kernel.execution_tools import tool_requires_approval
from onecode.kernel.outcome_policy import agent_cycle_decision, agent_cycle_decision_for_tool
from onecode.kernel.path_guard import PathGuard


READ_ONLY_TOOLS = frozenset({"read_text", "list_files", "search_text", "git_status", "git_diff", "glob_files", "outline"})
ALL_TOOLS = READ_ONLY_TOOLS | frozenset({"write_text", "patch_text", "run_command", "git_commit"})
OUTPUT_LIMIT = 1_500
UNREACHABLE_NOTICE = "依赖或文件不存在，任务不可达"
Proposal = dict[str, Any]
Propose = Callable[[list[dict[str, Any]], frozenset[str]], list[Proposal]]
Execute = Callable[[str, dict[str, Any]], dict[str, Any]]
Approve = Callable[[str, dict[str, Any]], bool]


def run_agent_cycle(
    *,
    propose: Propose,
    execute: Execute,
    max_turns: int = 8,
    task: str = "",
    max_history_chars: int | None = None,
    workspace: Path | None = None,
    remember: bool = False,
    approve: Approve | None = None,
    granted_approval_ids: frozenset[str] | None = None,
    admission: dict[str, Any] | None = None,
    verifier_runner: Callable[[Path, list[str]], dict[str, Any]] | None = None,
    write_runner: Callable[[Path, str, str], dict[str, Any]] | None = None,
    write_content: str | None = None,
) -> dict[str, Any]:
    if isinstance(max_turns, bool) or not isinstance(max_turns, int) or max_turns <= 0:
        raise ValueError("max_turns must be a positive integer")
    if admission is not None:
        return _admission_halt(
            admission,
            workspace,
            verifier_runner=verifier_runner,
            write_runner=write_runner,
            write_content=write_content,
        )
    if workspace is not None:
        PathGuard.discard_interrupted_writes(workspace)
    history: list[dict[str, Any]] = []
    allowed = ALL_TOOLS
    repeat = {
        "signature": None,
        "warned": False,
        "output": "",
        "miss_streak": 0,
        "progress_output": None,
        "retryable": False,
        "retry_streak": 0,
    }
    granted = granted_approval_ids or frozenset()
    for _turn in range(max_turns):
        visible = _visible_history(task, history, max_history_chars)
        proposal = list(propose(visible, allowed) or [])
        if not proposal:
            if _stop_is_success(history):
                result = {"status": "completed", "reason": None, "turn_count": len(history) + 1, "turns": history}
                _maybe_remember(workspace, remember, {"role": "task", "text": task}, "model_continue", result)
                return result
            return _halt("no_progress", history)
        observation = _run_proposal(proposal[:2], allowed, execute, repeat, approve, workspace, granted)
        history.append(observation)
        decision = agent_cycle_decision_for_tool(
            observation["status"],
            observation["reason"],
            retryable=observation.get("retryable") is True,
        )
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


def _run_proposal(
    proposal: list[Proposal],
    allowed: frozenset[str],
    execute: Execute,
    repeat: dict[str, Any],
    approve: Approve | None,
    workspace: Path | None,
    granted: frozenset[str],
) -> dict[str, Any]:
    calls = []  # type: ignore
    for call in proposal:
        tool_name = call.get("tool_name")
        params = call.get("params") if isinstance(call.get("params"), dict) else {}
        if not isinstance(tool_name, str) or not _tool_allowed(tool_name, allowed):
            return {
                "status": "halted",
                "reason": "permission_denied",
                "tool_name": tool_name if isinstance(tool_name, str) else "",
                "output": "",
                "calls": calls,
            }
        if repeat["miss_streak"] >= 2:
            return _no_progress(tool_name, calls)
        gate = _approval_gate(tool_name, params, approve, calls, workspace, granted)  # type: ignore
        if gate is not None:
            return gate
        signature = _call_signature(tool_name, params)  # type: ignore
        if signature == repeat["signature"] and not repeat["retryable"]:
            if repeat["warned"]:
                return {
                    "status": "halted",
                    "reason": "repeated_action",
                    "tool_name": tool_name,
                    "notice": "repeated_action",
                    "output": repeat["output"],
                    "calls": calls,
                }
            repeat["warned"] = True
            return {
                "status": "completed",
                "reason": None,
                "tool_name": tool_name,
                "notice": "repeated_action",
                "output": repeat["output"],
                "calls": calls,
            }
        before = _workspace_fingerprint(workspace) if workspace is not None else None
        outcome = execute(tool_name, params)  # type: ignore
        output = _tool_output(outcome)
        record = {
            "tool_name": tool_name,
            "status": outcome.get("status", "completed"),
            "reason": outcome.get("reason"),
            "output": output,
        }
        if "returncode" in outcome:
            record["returncode"] = outcome["returncode"]
        calls.append(record)
        repeat["signature"] = signature
        repeat["warned"] = False
        repeat["output"] = output
        if outcome.get("retryable") is True:
            record["retryable"] = True
            repeat["retryable"] = True
            repeat["retry_streak"] += 1
            repeat["miss_streak"] = 0
            repeat["progress_output"] = output
            if repeat["retry_streak"] >= 3:
                record["retryable"] = False
                repeat["retryable"] = False
                return {**record, "status": "halted", "reason": "no_progress", "calls": calls}
        else:
            repeat["retryable"] = False
            repeat["retry_streak"] = 0
            changed = workspace is None or _workspace_fingerprint(workspace) != before
            _note_progress(repeat, record, changed)
        if record["status"] != "completed" or record["reason"] not in {None, "search_miss", "path_not_found"}:
            return {**record, "calls": calls}
    last = calls[-1]
    return {**last, "calls": calls}


def _no_progress(tool_name: str, calls: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "halted",
        "reason": "no_progress",
        "tool_name": tool_name,
        "notice": "no_progress",
        "output": UNREACHABLE_NOTICE,
        "calls": calls,
    }


def _note_progress(repeat: dict[str, Any], record: dict[str, Any], fingerprint_changed: bool) -> None:
    if _unproductive(record, fingerprint_changed, repeat.get("progress_output")):
        repeat["miss_streak"] += 1
    else:
        repeat["miss_streak"] = 0
    repeat["progress_output"] = record.get("output")


def _unproductive(record: dict[str, Any], fingerprint_changed: bool, previous_output: object) -> bool:
    if record.get("reason") in {"search_miss", "path_not_found"}:
        return True
    if record.get("tool_name") in READ_ONLY_TOOLS and record.get("output") == "" and record.get("reason") is None:
        return True
    if record.get("tool_name") in READ_ONLY_TOOLS or fingerprint_changed:
        return False
    return previous_output is None or record.get("output") == previous_output


def _workspace_fingerprint(workspace: Path) -> str:
    rows: list[str] = []
    ignored_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", ".mypy_cache", ".ruff_cache", ".pytest_cache", ".onecode"}
    
    # We use os.walk to effectively prune ignored directories instead of rglob
    for dirpath, dirnames, filenames in os.walk(workspace):  # type: ignore
        dirnames[:] = [d for d in dirnames if d not in ignored_dirs]
        
        for filename in sorted(filenames):
            if len(rows) >= 2_000:
                break
            
            path = Path(dirpath) / filename
            if not path.is_file() or path.is_symlink():
                continue
                
            try:
                relative = path.relative_to(workspace).as_posix()
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                continue
            rows.append(f"{relative}:{digest}")
            
        if len(rows) >= 2_000:
            break
            
    # Sort the final rows to ensure consistent hashing
    rows.sort()
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()



def _approval_gate(
    tool_name: str,
    params: dict[str, Any],
    approve: Approve | None,
    calls: list[dict[str, Any]],
    workspace: Path | None,
    granted: frozenset[str],
) -> dict[str, Any] | None:
    if not tool_requires_approval(tool_name):
        return None
    if workspace is not None:
        existing = find_pending_approval(workspace, tool_name, params)
        if existing is not None and existing["id"] not in granted:
            return _pending_result(existing, calls)
    if approve is not None and approve(tool_name, params):
        return None
    if approve is not None:
        return {
            "status": "halted",
            "reason": "permission_denied",
            "tool_name": tool_name,
            "output": "",
            "calls": calls,
        }
    record = (
        persist_pending_approval(workspace, tool_name, params)
        if workspace is not None
        else {
            "id": "",
            "status": "PENDING_APPROVAL",
            "tool_name": tool_name,
            "params": params,
            "reason": "approval_required",
        }
    )
    return _pending_result(record, calls)


def _pending_result(record: dict[str, Any], calls: list[dict[str, Any]]) -> dict[str, Any]:
    pending = {"tool_name": record["tool_name"], "params": record["params"]}
    return {
        "status": "halted",
        "reason": "approval_required",
        "tool_name": record["tool_name"],
        "params": record["params"],
        "pending": pending,
        "pending_id": record.get("id", ""),
        "approval_status": record.get("status", "PENDING_APPROVAL"),
        "output": "",
        "calls": calls,
    }


def _call_signature(tool_name: str, params: dict[str, Any]) -> str:
    return json.dumps({"tool": tool_name, "params": params}, ensure_ascii=False, sort_keys=True, default=str)


def _tool_output(outcome: dict[str, Any]) -> str:
    chunks: list[str] = []
    for key in ("stdout", "stderr", "diff"):
        value = outcome.get(key)
        if isinstance(value, str) and value:
            chunks.append(value)
    content = outcome.get("content")
    if isinstance(content, str) and content:
        chunks.append(content)
    entries = outcome.get("entries")
    if isinstance(entries, list) and entries:
        chunks.append("\n".join(str(item) for item in entries[:40]))
    paths = outcome.get("paths")
    if isinstance(paths, list) and paths:
        chunks.append("\n".join(str(item) for item in paths[:40]))
    symbols = outcome.get("symbols")
    if isinstance(symbols, list) and symbols:
        names = [str(item.get("name")) for item in symbols if isinstance(item, dict) and item.get("name")]
        if names:
            chunks.append(", ".join(names))
    matches = outcome.get("matches")
    if isinstance(matches, list) and matches:
        lines = []
        for item in matches[:40]:
            if isinstance(item, dict):
                lines.append(f"{item.get('path', '')}:{item.get('line', '')}:{item.get('text', '')}")
            else:
                lines.append(str(item))
        chunks.append("\n".join(lines))
    text = "\n".join(chunks)
    return _truncate(text)


def _truncate(text: str) -> str:
    if len(text) <= OUTPUT_LIMIT:
        return text
    tail_len = 480
    for _ in range(4):
        omitted = len(text) - (OUTPUT_LIMIT - tail_len)
        marker = f"\n[truncated remaining={max(omitted, 0)}]\n"
        head_len = OUTPUT_LIMIT - len(marker) - tail_len
        if head_len < 80:
            tail_len = max(120, tail_len - 80)
            continue
        omitted = len(text) - head_len - tail_len
        marker = f"\n[truncated remaining={omitted}]\n"
        head_len = OUTPUT_LIMIT - len(marker) - tail_len
        if omitted == len(text) - head_len - tail_len and head_len > 0:
            break
    head = text[:head_len]
    tail = text[-tail_len:]
    omitted = len(text) - len(head) - len(tail)
    marker = f"\n[truncated remaining={omitted}]\n"
    if len(head) + len(marker) + len(tail) > OUTPUT_LIMIT:
        head = text[: OUTPUT_LIMIT - len(marker) - len(tail)]
        omitted = len(text) - len(head) - len(tail)
        marker = f"\n[truncated remaining={omitted}]\n"
        head = text[: OUTPUT_LIMIT - len(marker) - len(tail)]
    return head + marker + tail


def _stop_is_success(history: list[dict[str, Any]]) -> bool:
    if not history:
        return False
    last = history[-1]
    if last.get("retryable") is True or last.get("status") != "completed":
        return False
    if last.get("returncode") not in {None, 0}:
        return False
    return last.get("reason") in {None, "search_miss", "path_not_found"}


def _tool_allowed(tool_name: str, allowed: frozenset[str]) -> bool:
    if tool_name in allowed:
        return True
    if allowed != ALL_TOOLS or not tool_name.startswith("mcp."):
        return False
    server, dot, remote = tool_name.removeprefix("mcp.").partition(".")
    return bool(dot) and _mcp_segment(server) and _mcp_segment(remote)


def _mcp_segment(value: str) -> bool:
    return bool(value) and len(value) <= 64 and value.replace("-", "").replace("_", "").isalnum()


def _admission_halt(
    admission: dict[str, Any],
    workspace: Path | None,
    *,
    verifier_runner: Callable[[Path, list[str]], dict[str, Any]] | None,
    write_runner: Callable[[Path, str, str], dict[str, Any]] | None,
    write_content: str | None,
) -> dict[str, Any]:
    from onecode.experimental.yizijue_ledger import yizijue_ledger_entry
    from onecode.experimental.yizijue_verifier import run_pinned_verifier
    from onecode.experimental.yizijue_write import run_pinned_write

    try:
        entry = yizijue_ledger_entry(admission)
    except ValueError:
        if workspace is not None:
            from onecode.experimental.yizijue_ledger import append_rejected_ledger_entry

            append_rejected_ledger_entry(workspace, admission)
        return _halt("yizijue_admission_rejected", [])
    reason = "verifier_requires_sandbox" if entry.get("cycle") == "verify" else entry.get("reason") or "yizijue_stop"
    result = _halt(str(reason), [])
    result["yizijue_state"] = entry.get("yizijue_state")
    result["yizijue_action"] = entry.get("action")
    if workspace is None:
        return result
    from onecode.experimental.yizijue_ledger import append_yizijue_effect, append_yizijue_ledger

    append_yizijue_ledger(workspace, admission)
    facts = admission.get("facts") if isinstance(admission.get("facts"), dict) else None
    gated = {**entry, "facts": facts}
    if verifier_runner is not None:
        outcome = run_pinned_verifier(workspace, gated, verifier_runner)
        _publish_effect(result, "verifier", outcome, _record_effect(workspace, append_yizijue_effect, entry, "verifier", outcome))
    if write_runner is not None and write_content is not None:
        evidence = admission.get("evidence") if isinstance(admission.get("evidence"), dict) else None
        outcome = run_pinned_write(
            workspace,
            {**gated, "evidence": evidence, "executed": False},
            write_content,
            write_runner,
        )
        _publish_effect(result, "write", outcome, _record_effect(workspace, append_yizijue_effect, entry, "write", outcome))
    _sync_halt_reason(result)
    return result


def _sync_halt_reason(result: dict[str, Any]) -> None:
    verifier = result.get("verifier")
    write = result.get("write")
    if isinstance(verifier, dict) and verifier.get("executed") is True:
        return
    if isinstance(write, dict) and write.get("executed") is True:
        return
    if result.get("yizijue_action") in {"ALLOW_ATOMIC_WRITE", "ALLOW_PATCH_WITH_SHA"} and isinstance(write, dict) and write.get("reason"):
        result["reason"] = write["reason"]
        return
    if result.get("reason") == "verifier_requires_sandbox" and isinstance(verifier, dict) and verifier.get("reason"):
        result["reason"] = verifier["reason"]


def _effect_view(outcome: dict[str, Any]) -> dict[str, Any]:
    view = {"ran": outcome["ran"], "executed": outcome["executed"]}
    if outcome.get("reason") is not None:
        view["reason"] = outcome["reason"]
    result_body = outcome.get("result")
    if isinstance(result_body, dict) and result_body.get("status") is not None:
        view["status"] = result_body["status"]
    if outcome.get("executed") is True:
        from onecode.experimental.yizijue_ledger import confirmed_proof

        view.update(confirmed_proof(outcome))
    return view


def _publish_effect(result: dict[str, Any], key: str, outcome: dict[str, Any], recorded: bool) -> None:
    view = _effect_view(outcome)
    if not recorded and view.get("executed") is True:
        view = {"ran": False, "executed": False, "reason": "effect_not_recorded"}
    result[key] = view


def _record_effect(workspace: Path, append, entry: dict[str, Any], effect: str, outcome: dict[str, Any]) -> bool:
    try:
        append(
            workspace,
            {
                "effect": effect,
                "yizijue_state": entry.get("yizijue_state"),
                "action": entry.get("action"),
                "reason": outcome.get("reason") or entry.get("reason"),
                "ran": outcome.get("ran") is True,
                "command": outcome.get("command"),
                "path": outcome.get("path"),
                "sha256": outcome.get("sha256"),
            },
        )
        return True
    except ValueError:
        return False


def _halt(reason: str | None, history: list[dict[str, Any]]) -> dict[str, Any]:
    result = {
        "status": "halted",
        "reason": reason,
        "turn_count": len(history),
        "turns": history,
        "cycle": history[-1].get("cycle") if history else None,
    }
    pending = history[-1].get("pending") if history else None
    if isinstance(pending, dict):
        result["pending"] = pending
    if history and history[-1].get("pending_id"):
        result["pending_id"] = history[-1]["pending_id"]
        result["approval_status"] = history[-1].get("approval_status", "PENDING_APPROVAL")
    return result
