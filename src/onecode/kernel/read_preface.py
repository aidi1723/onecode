import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from onecode.kernel.agent_cycle import READ_ONLY_TOOLS, run_agent_cycle
from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.model_provider import ModelProviderError, ModelProviderTimeout, json_object_from_model_text
from onecode.kernel.path_guard import PathGuard, PathGuardError

Proposal = dict[str, Any]
Propose = Callable[[list[dict[str, Any]], frozenset[str]], list[Proposal]]
Execute = Callable[[str, dict[str, Any]], dict[str, Any]]


class ReadPrefaceError(ValueError):
    pass


def assert_read_only(tool_names: list[str]) -> None:
    refused = [name for name in tool_names if name not in READ_ONLY_TOOLS]
    if refused:
        raise ReadPrefaceError(f"preface tools must be read-only: {', '.join(refused)}")


def preface_text(files: dict[str, str]) -> str:
    blocks: list[str] = []
    for path in sorted(files):
        content = files[path]
        if content == "":
            continue
        blocks.append(f"## {path}\n{content[:4000]}")
    return "\n".join(blocks)


def with_preface(task: str, preface: str | None) -> str:
    if not preface:
        return task
    return f"{preface.rstrip()}\n\n{task}"


def survey_reads(
    workspace: Path,
    task: str,
    propose: Propose,
    execute: Execute,
    max_turns: int = 4,
    *,
    max_read_misses: int = 4,
    output_limit: int = 4_000,
) -> dict[str, Any]:
    result = run_agent_cycle(
        propose=_read_only_propose(propose),
        execute=execute,
        max_turns=max_turns,
        task=task,
        workspace=workspace,
        remember=False,
        approve=lambda _tool_name, _params: False,
        max_read_misses=max_read_misses,
        output_limit=output_limit,
    )
    reason = result.get("reason") if isinstance(result.get("reason"), str) else None
    status = str(result.get("status") or "halted")
    return {
        "status": status,
        "reason": reason,
        "status_code": IchingKernel.classify_outcome(status, reason),
        "preface": _preface_from_turns(result.get("turns") or []),
        "turns": result.get("turns") or [],
    }


def _read_only_propose(propose: Propose) -> Propose:
    def guarded(history: list[dict[str, Any]], allowed: frozenset[str]) -> list[Proposal]:
        narrowed = allowed & READ_ONLY_TOOLS
        kept: list[Proposal] = []
        for item in propose(history, narrowed) or []:
            if isinstance(item, dict) and item.get("tool_name") in READ_ONLY_TOOLS:
                kept.append(item)
        return kept[:2]

    return guarded


def _preface_from_turns(turns: list[Any]) -> str:
    blocks: list[str] = []
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        calls = turn.get("calls")
        records = calls if isinstance(calls, list) and calls else [turn]
        for record in records:
            if not isinstance(record, dict):
                continue
            output = record.get("output")
            if isinstance(output, str) and output.strip():
                blocks.append(output[:4000])
    return "\n".join(blocks)


def survey_model_reads(
    workspace: Path,
    task: str,
    complete: Callable[[str], str],
    execute: Execute,
    max_turns: int = 4,
) -> dict[str, Any]:
    proposer = _ModelReadProposer(task, complete, default_read_proposer(workspace, task))
    result = survey_reads(workspace, task, proposer, execute, max_turns=max_turns)
    if proposer.halt_reason is not None:
        result["status"] = "halted"
        result["reason"] = proposer.halt_reason
        result["status_code"] = IchingKernel.classify_outcome("halted", proposer.halt_reason)
    return result


class _ModelReadProposer:
    def __init__(self, task: str, complete: Callable[[str], str], fallback: Propose) -> None:
        self._task = task
        self._complete = complete
        self._fallback = fallback
        self.halt_reason: str | None = None
        self._model_done = False

    def __call__(self, history: list[dict[str, Any]], allowed: frozenset[str]) -> list[Proposal]:
        if self.halt_reason is not None:
            return []
        if self._model_done:
            return [] if history else self._fallback(history, allowed)
        tools = self._ask(history, allowed)
        if self.halt_reason is not None or tools is None:
            self._model_done = True
            if self.halt_reason is not None or history:
                return []
            return self._fallback(history, allowed)
        reads = [item for item in tools if item.get("tool_name") in allowed]
        if not reads:
            self._model_done = True
            if history:
                return []
            return self._fallback(history, allowed)
        return reads[:2]

    def _ask(self, history: list[dict[str, Any]], allowed: frozenset[str]) -> list[Proposal] | None:
        prompt = _survey_prompt(self._task, history, allowed)
        text = self._once(prompt)
        if text is None:
            return None
        tools = _parse_survey_tools(text)
        if tools is not None:
            return tools
        retry = self._once(prompt + "\nThe previous response was not valid JSON. Return one JSON object with a tools array.")
        if retry is None:
            return None
        return _parse_survey_tools(retry)

    def _once(self, prompt: str) -> str | None:
        try:
            return self._complete(prompt)
        except ModelProviderTimeout:
            self.halt_reason = "model_provider_timeout"
        except ModelProviderError:
            self.halt_reason = "model_provider_error"
        return None


def _survey_prompt(task: str, history: list[dict[str, Any]], allowed: frozenset[str]) -> str:
    names = ", ".join(sorted(name for name in allowed if name in READ_ONLY_TOOLS))
    observations: list[str] = []
    for turn in history[-4:]:
        output = turn.get("output") if isinstance(turn, dict) else None
        if isinstance(output, str) and output.strip():
            observations.append(output[:500])
    return (
        "Choose the next read-only tools for this task. "
        f"Allowed tools: {names}. "
        'Return one JSON object {"tools":[{"tool_name":"read_text","params":{"path":"src/file.py"}}]}. '
        "Use an empty tools array when you have enough to stop. Do not write files.\n"
        f"Task: {task}\nObservations:\n" + "\n".join(observations)
    )


def _parse_survey_tools(text: str) -> list[Proposal] | None:
    try:
        payload = json_object_from_model_text(text)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("tools"), list):
        return None
    parsed: list[Proposal] = []
    for item in payload["tools"]:
        if not isinstance(item, dict) or not isinstance(item.get("tool_name"), str) or not item["tool_name"]:
            return None
        params = item.get("params") if item.get("params") is not None else {}
        if not isinstance(params, dict):
            return None
        parsed.append({"tool_name": item["tool_name"], "params": params})
    return parsed


def default_read_proposer(workspace: Path, task: str) -> Propose:
    queue = _survey_queue(workspace, task)

    def propose(history: list[dict[str, Any]], allowed: frozenset[str]) -> list[Proposal]:
        del history
        batch: list[Proposal] = []
        while queue and len(batch) < 2:
            item = queue.pop(0)
            if item["tool_name"] in allowed:
                batch.append(item)
        return batch

    return propose


def _survey_queue(workspace: Path, task: str) -> list[Proposal]:
    from onecode.kernel.model_loop import named_python_files

    named = [path for path in named_python_files(task) if (workspace / path).is_file()]
    queue: list[Proposal] = [
        {"tool_name": "read_text", "params": {"path": path, "max_bytes": 4000, "max_lines": 200}}
        for path in named[:2]
    ]
    for path in named:
        if not path.startswith("src/") or not path.endswith(".py"):
            continue
        test_path = f"tests/test_{Path(path).stem}.py"
        if (workspace / test_path).is_file():
            queue.append(
                {"tool_name": "read_text", "params": {"path": test_path, "max_bytes": 4000, "max_lines": 200}}
            )
            break
    if named and named[0].endswith(".py"):
        queue.append({"tool_name": "outline", "params": {"path": named[0]}})
    return queue[:4]


def read_only_registry_execute(workspace: Path) -> Execute:
    import subprocess

    from onecode.kernel.execution_tools import default_tool_registry

    registry = default_tool_registry()

    def execute(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        if tool_name not in READ_ONLY_TOOLS:
            return {"status": "halted", "reason": "permission_denied"}
        tool = registry.get(tool_name)
        if tool is None:
            return {"status": "halted", "reason": "tool_not_found"}
        try:
            outcome = tool.execute(params, workspace)
        except PathGuardError:
            return {"status": "halted", "reason": "sovereignty_breach"}
        except ValueError as exc:
            reason = str(exc)
            if reason not in {"path_not_found", "read_target_not_file", "list_target_not_found", "search_miss"}:
                reason = "search_miss"
            return {"status": "completed", "reason": reason, "content": str(exc)}
        except (OSError, subprocess.SubprocessError):
            return {"status": "halted", "reason": "action_exception"}
        if not isinstance(outcome, dict):
            return {"status": "halted", "reason": "action_exception"}
        if "status" not in outcome:
            outcome = {**outcome, "status": "completed"}
        if "reason" not in outcome:
            outcome = {**outcome, "reason": None}
        return _headed_read(outcome, params)

    return execute


def _headed_read(outcome: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    content = outcome.get("content")
    path = params.get("path") if isinstance(params.get("path"), str) else outcome.get("path")
    if not isinstance(content, str) or not isinstance(path, str):
        return outcome
    return {**outcome, "content": f"## {path.replace('/', ' / ')}\n{content[:4000]}"}


def collect_preface(workspace: Path, relative_paths: list[str]) -> str:
    files: dict[str, str] = {}
    for relative in relative_paths:
        target = PathGuard.resolve_read_target(workspace, relative)
        if target.is_file():
            files[relative.replace("\\", "/")] = target.read_text(encoding="utf-8")[:4000]
    return preface_text(files)
