import ast
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


SINGLE_FILE_PREFACE_CHARS = 24_000
SURVEY_READ_CHARS = 16_000
SURVEY_READ_LINES = 600
SOURCE_WINDOW_CHARS = 8_000
SKELETON_CHARS = 4_000


def preface_text(files: dict[str, str], *, max_chars: int = 4_000) -> str:
    blocks: list[str] = []
    for path in sorted(files):
        content = files[path]
        if content == "":
            continue
        blocks.append(f"## {path}\n{content[:max_chars]}")
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
    output_limit: int = SURVEY_READ_CHARS,
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
                blocks.append(output[:SURVEY_READ_CHARS])
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
        self._got_model_text = False

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
            text = self._complete(prompt)
        except ModelProviderTimeout:
            self.halt_reason = "model_provider_timeout"
            return None
        except ModelProviderError:
            if not self._got_model_text:
                self.halt_reason = "model_provider_error"
            return None
        self._got_model_text = True
        return text


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
        "Return one JSON object with a tools array. "
        "Each item has a tool_name and a params object. "
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
    from onecode.web.api import _existing_implementation_files, _ranked_implementation_files

    ranked = _ranked_implementation_files(task, workspace)
    named = [path for path in named_python_files(task) if (workspace / path).is_file() and path not in ranked]
    selected = [*ranked, *named][:2]
    if not selected:
        selected = _existing_implementation_files(workspace)[:2]
    read = {"max_bytes": SURVEY_READ_CHARS, "max_lines": SURVEY_READ_LINES}
    queue: list[Proposal] = [
        {"tool_name": "read_text", "params": {"path": path, **read}}
        for path in selected
    ]
    for path in selected:
        if not path.startswith("src/") or not path.endswith(".py"):
            continue
        test_path = f"tests/test_{Path(path).stem}.py"
        if (workspace / test_path).is_file():
            queue.append(
                {"tool_name": "read_text", "params": {"path": test_path, "max_bytes": SURVEY_READ_CHARS, "max_lines": SURVEY_READ_LINES}}
            )
            break
    if selected and selected[0].endswith(".py"):
        queue.append({"tool_name": "outline", "params": {"path": selected[0]}})
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
    return {**outcome, "content": f"## {path.replace('/', ' / ')}\n{content[:SURVEY_READ_CHARS]}"}


def collect_preface(workspace: Path, relative_paths: list[str], *, max_chars: int = 4_000) -> str:
    files: dict[str, str] = {}
    for relative in relative_paths:
        target = PathGuard.resolve_read_target(workspace, relative)
        if target.is_file():
            files[relative.replace("\\", "/")] = target.read_text(encoding="utf-8")[:max_chars]
    return preface_text(files, max_chars=max_chars)


def render_source_excerpt(text: str, tokens: list[str], *, limit: int = SINGLE_FILE_PREFACE_CHARS) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, True
    parts: list[str] = []
    skeleton = _source_skeleton(text, SKELETON_CHARS)
    if skeleton:
        parts.append("Skeleton:\n" + skeleton)
    parts.append("Source window:\n" + _source_window(text, tokens, SOURCE_WINDOW_CHARS))
    return "\n".join(parts), False


def render_workspace_preface(workspace: Path, relative_paths: list[str], tokens: list[str]) -> str:
    blocks: list[str] = []
    for relative in relative_paths:
        target = PathGuard.resolve_read_target(workspace, relative)
        if not target.is_file():
            continue
        text = target.read_text(encoding="utf-8")
        if text == "":
            continue
        excerpt, complete = render_source_excerpt(text, tokens)
        heading = f"## {relative.replace(chr(92), '/')}"
        if not complete:
            heading += "\nThis excerpt is not the whole file."
        blocks.append(f"{heading}\n{excerpt}")
    return "\n".join(blocks)


def _source_window(text: str, tokens: list[str], limit: int) -> str:
    chunks: list[str] = []
    used = 0
    for body in _named_function_bodies(text, tokens):
        if used >= limit:
            break
        piece = body[: limit - used]
        chunks.append(piece)
        used += len(piece)
    if used < limit:
        rest = _token_windows(text, tokens, limit - used)
        if rest:
            chunks.append(rest)
    return "\n\n# ...\n\n".join(chunks)[:limit]


def _named_function_bodies(source: str, tokens: list[str]) -> list[str]:
    wanted = {token for token in tokens if token.isidentifier()}
    if not wanted:
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    bodies: list[str] = []
    seen: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name not in wanted or node.name in seen:
            continue
        segment = ast.get_source_segment(source, node)
        if not segment:
            continue
        bodies.append(segment)
        seen.add(node.name)
        if len(bodies) == 3:
            break
    return bodies


def _token_windows(text: str, tokens: list[str], limit: int) -> str:
    positions: list[int] = []
    for token in tokens:
        if not token:
            continue
        start = 0
        while len(positions) < 3:
            index = text.find(token, start)
            if index < 0:
                break
            if all(abs(index - earlier) > 200 for earlier in positions):
                positions.append(index)
            start = index + len(token)
    if not positions:
        return text[:limit]
    per_hit = max(1200, limit // len(positions))
    chunks: list[str] = []
    for center in positions:
        start = max(0, center - per_hit // 5)
        newline = text.rfind("\n", 0, start)
        if newline >= 0:
            start = newline + 1
        chunks.append(text[start : start + per_hit])
    return "\n\n# ...\n\n".join(chunks)[:limit]


def _source_skeleton(source: str, limit: int) -> str:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""
    lines = source.splitlines()
    kept: list[str] = []
    assignments = 0
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            kept.extend(_node_lines(lines, node))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            if assignments < 8:
                kept.extend(_node_lines(lines, node)[:4])
                assignments += 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kept.extend(_folded_signature(lines, node))
        elif isinstance(node, ast.ClassDef):
            kept.extend(_folded_signature(lines, node))
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    kept.extend(_folded_signature(lines, child))
        if sum(len(item) + 1 for item in kept) >= limit:
            break
    return "\n".join(kept)[:limit]


def _node_lines(lines: list[str], node: ast.AST) -> list[str]:
    start = getattr(node, "lineno", 1) - 1
    end = getattr(node, "end_lineno", start + 1) or (start + 1)
    return lines[start:end]


def _folded_signature(lines: list[str], node: ast.AST) -> list[str]:
    start = getattr(node, "lineno", 1) - 1
    end = start + 1
    last = getattr(node, "end_lineno", end) or end
    while end < last and end < len(lines) and not lines[end - 1].rstrip().endswith(":"):
        end += 1
        if end - start > 8:
            break
    signature = lines[start:end]
    pad = _leading_indent(signature[0] if signature else "")
    return [*signature, f"{pad}# ... existing implementation ..."]


def _leading_indent(line: str) -> str:
    return line[: len(line) - len(line.lstrip(" "))] + "    "
