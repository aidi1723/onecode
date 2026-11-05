"""Shell-side helpers for the OneCode HTTP API."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from onecode.web.responses import error_payload
from onecode.web.workspace import (
    configured_allowed_workspace_roots,
    require_allowed_workspace,
    workspace_allowed,
)

from onecode.kernel.effective_model_config import resolve_effective_model_config
from onecode.kernel.model_loop import (
    data_contract_guidance,
    failed_model_result,
    initial_asset_prompt,
    missing_required_files,
    named_python_files,
    narrow_plan_prompt,
    required_python_files,
    run_model_task,  # noqa: F401
)
from onecode.kernel.context import create_context
from onecode.kernel.trace import TraceEvent, write_trace_event
from onecode.kernel.agent_memory import load_agent_memory, remember_turn
from onecode.kernel.read_preface import SINGLE_FILE_PREFACE_CHARS, collect_preface, render_workspace_preface
from onecode.kernel.host_stage import stage_bytes
from onecode.kernel.outcome_policy import agent_cycle_decision
from onecode.kernel.sandbox import SandboxConfig
from onecode.kernel.model_config import (
    read_model_config,  # noqa: F401
)
from onecode.kernel.model_provider import MissingModelApiKey, ModelProviderError
from onecode.kernel.preset_tests import (
    is_preset_test_path,
    preset_test_baseline_changed,
    preset_test_hashes,
)
from onecode.kernel.project_context import discover_project_context
from onecode.kernel.skill_context import discover_skill_context, public_skill_context
from onecode.kernel.shell_projection import (
    attach_shell_projection,  # noqa: F401
)
from onecode.kernel.runtime_config import inspect_runtime_config
from onecode.kernel.verifier import (
    DEFAULT_VERIFIER_POLICY_PATH,
)


DEFAULT_MODEL_ID = "onecode-agent"
DIRECT_CHAT_SYSTEM_PROMPT = (
    "你是 OneCode agent 的对话脑。直接回答用户的问题。"
    "当用户要求改文件、写代码到项目、执行命令、检查仓库或生成落盘产物时，说明需要 OneCode 执行任务。"
    "其它数学、理论、解释、设计和普通问答都用自然语言回答。"
)
TASK_PREFIXES = (
    "查：",
    "造：",
    "改：",
    "写：",
    "跑：",
    "执行：",
    "修：",
    "测试：",
)
TASK_MARKERS = (
    "修改",
    "创建",
    "生成文件",
    "写入",
    "检查项目",
    "检查仓库",
    "修复",
    "patch",
    "commit",
)
PATH_MARKERS = ("src/", "tests/", ".py", ".js", ".ts", ".tsx", ".md", ".json", ".yaml", ".yml")
DEFAULT_MODEL_TIMEOUT_SECONDS = 60.0
MAX_MODEL_TIMEOUT_SECONDS = 600.0
APPROVAL_MESSAGE_PATTERN = re.compile(r"^(批准|确认|拒绝)计划\s+([a-f0-9]{32})\s*$")



def _bound(name: str):
    from onecode.web import api
    return getattr(api, name)


def model_timeout_seconds_from_env() -> float:
    raw = os.getenv(
        "ONECODE_MODEL_TIMEOUT_SECONDS", str(DEFAULT_MODEL_TIMEOUT_SECONDS)
    )
    try:
        value = float(raw)
    except ValueError:
        raise ValueError("ONECODE_MODEL_TIMEOUT_SECONDS must be a number") from None
    if not 0 < value <= MAX_MODEL_TIMEOUT_SECONDS:
        raise ValueError(
            "ONECODE_MODEL_TIMEOUT_SECONDS must be greater than zero and at most 600"
        )
    return value


def build_models_payload() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": DEFAULT_MODEL_ID,
                "object": "model",
                "created": 0,
                "owned_by": "onecode",
            }
        ],
    }


def latest_user_message(messages: Any) -> str:
    from onecode.web.api_handlers import message_content_to_text
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        return message_content_to_text(message.get("content"))
    return ""


def query_workspace_param(query: str) -> str | None:
    values = parse_qs(query).get("workspace")
    return values[0] if values else None


def project_status_payload(workspace: Path) -> dict[str, Any]:
    resolved = require_allowed_workspace(workspace)
    policy_path = resolved / DEFAULT_VERIFIER_POLICY_PATH
    runs = _bound("list_runs")(resolved)["runs"]
    latest_run = _bound("attach_shell_projection")(runs[-1]) if runs else None
    effective_model = resolve_effective_model_config(os.environ, _bound("read_model_config")(include_secret=True))
    return {
        "workspace": str(resolved),
        "exists": resolved.exists() and resolved.is_dir(),
        "allowed": workspace_allowed(resolved),
        "allowed_roots": [str(root) for root in configured_allowed_workspace_roots()],
        "git": {"present": (resolved / ".git").exists()},
        "verifier_policy": {"present": policy_path.exists(), "path": str(policy_path)},
        "latest_run": latest_run,
        "project_context": discover_project_context(resolved),
        "runtime_config": inspect_runtime_config(resolved),
        "skill_context": public_skill_context(discover_skill_context(resolved)),
        "effective_model_config": effective_model.public,
    }


def continue_named_files(user_task: str, workspace: Path, written_before: set[str]) -> dict[str, Any] | None:
    missing = missing_required_files(user_task, workspace)
    if not missing:
        return None
    written_after = set(required_python_files(user_task)) - set(missing)
    if written_after == written_before:
        return {"status": "halted", "reason": "no_progress", "partial": True, "requested_count": 1, "completed_count": len(written_after), "skipped_count": 0, "failed_count": 0, "assets": []}
    stored_config = _bound("read_model_config")(include_secret=True)
    effective_model = resolve_effective_model_config(os.environ, stored_config)
    return _bound("run_model_task")(
        narrow_plan_prompt(user_task, {"detail": "continue with the next file", "failure_kind": "resource_budget_exceeded"}, sorted(written_after)),
        workspace=workspace,
        model=effective_model.model,
        api_key=effective_model.api_key,
        provider_kind=effective_model.provider,
        endpoint=effective_model.endpoint,
        require_explicit_approval=True,
        max_repair_attempts=0,
        sandbox_config=SandboxConfig(workspace=workspace),
    )


def _targeted_python_paths(task: str, workspace: Path) -> list[str]:
    if _asks_for_new_tests(task) or _mentioned_json_file(task) is not None:
        return []
    mentioned = _mentioned_existing_python_files(task, workspace)
    if mentioned:
        return mentioned
    ranked = _ranked_implementation_files(task, workspace)
    if ranked:
        return _fit_preface_paths(workspace, ranked)
    return []


def _selected_python_paths(task: str, workspace: Path) -> list[str]:
    targeted = _targeted_python_paths(task, workspace)
    if targeted:
        return targeted
    if _asks_for_new_tests(task) or _mentioned_json_file(task) is not None:
        return []
    existing = _existing_implementation_files(workspace)
    if existing:
        return _fit_preface_paths(workspace, existing)
    return []


def _fit_preface_paths(workspace: Path, ranked: list[str]) -> list[str]:
    chosen: list[str] = []
    total = 0
    for relative in ranked:
        try:
            size = (workspace / relative).stat().st_size
        except OSError:
            continue
        if chosen and total + min(size, SINGLE_FILE_PREFACE_CHARS) > 32_000:
            break
        chosen.append(relative)
        total += min(size, SINGLE_FILE_PREFACE_CHARS)
        if len(chosen) == 4:
            break
    return chosen or ranked[:1]


def _file_exceeds_preface(workspace: Path, relative: str) -> bool:
    try:
        size = (workspace / relative).stat().st_size
        explicit = os.environ.get("ONECODE_PATCH_THRESHOLD_CHARS")
        if explicit:
            return size > int(explicit)
        from onecode.kernel.model_loop import resolve_task_bureau

        bureau = resolve_task_bureau(workspace)
        limit = bureau.get("preview_limit_chars", SINGLE_FILE_PREFACE_CHARS)
        return size > limit
    except (OSError, ValueError):
        return False


def _asset_or_patch_prompt(task: str, workspace: Path, target: str) -> str:
    if _file_exceeds_preface(workspace, target) or os.environ.get("ONECODE_PREFER_PATCH", "").lower() in {"1", "true", "yes"}:
        return (
            "The target file is larger than one complete asset.\n"
            f"Target: {target}\n"
            f"Original task: {task}\n"
            "Return JSON with one patch. "
            "The patch search_block must be copied from the Source window in the preface, not from the Skeleton. "
            "Do not return a full-file asset. "
            "Do not include execution_plan or run_command. "
            "Do not modify tests/."
            + data_contract_guidance(task)
        )
    return initial_asset_prompt(task, target)


def _prompt_for_paths(task: str, workspace: Path, paths: list[str]) -> str:
    if len(paths) == 1 or any(_file_exceeds_preface(workspace, path) for path in paths):
        return _asset_or_patch_prompt(task, workspace, paths[0])
    return _listed_file_prompt(task, paths)


def shell_model_task_extras(task: str, workspace: Path) -> dict[str, Any]:
    repair_env = os.environ.get("ONECODE_MAX_REPAIR_ATTEMPTS")
    if repair_env is not None and repair_env.isdigit():
        turn_budget = int(repair_env)
    elif repair_env == "auto":
        from onecode.kernel.model_loop import resolve_task_bureau

        turn_budget = resolve_task_bureau(workspace).get("turn_budget", 3)
    else:
        turn_budget = 1
    focused = _selected_python_paths(task, workspace)
    if focused:
        if len(focused) == 1 and _file_exceeds_preface(workspace, focused[0]):
            preface = render_workspace_preface(workspace, focused, _task_tokens(task)) or None
        else:
            max_chars = 24_000 if len(focused) == 1 else 12_000
            preface = collect_preface(workspace, focused, max_chars=max_chars) or None
        return {
            "preface": preface,
            "sandbox_config": SandboxConfig(workspace=workspace),
            "max_repair_attempts": turn_budget,
        }
    paths: list[str] = []

    def add(path: str) -> None:
        if path in paths or is_preset_test_path(path) or not (workspace / path).is_file():
            return
        if len(paths) >= 4:
            return
        paths.append(path)

    for path in _mentioned_existing_python_files(task, workspace):
        add(path)
    if _asks_for_new_tests(task):
        refused = _refused_python_files(task)
        for match in _MENTIONED_PYTHON.findall(task):
            relative = match.replace("\\", "/")
            if relative in refused or Path(relative).name in refused:
                add(relative)
    for path in [*named_python_files(task), *_ranked_implementation_files(task, workspace)]:
        add(path)
    preface = collect_preface(workspace, paths) if paths else ""
    return {
        "preface": preface or None,
        "sandbox_config": SandboxConfig(workspace=workspace),
        "max_repair_attempts": turn_budget,
    }


def shell_read_survey(workspace: Path, task: str) -> dict[str, Any]:
    from onecode.kernel.read_preface import read_only_registry_execute, survey_model_reads

    return survey_model_reads(workspace, task, _bound("complete_read_survey"), read_only_registry_execute(workspace))


def complete_read_survey(prompt: str) -> str:
    from onecode.kernel.model_provider import complete_model_text

    stored_config = _bound("read_model_config")(include_secret=True)
    effective_model = resolve_effective_model_config(os.environ, stored_config)
    return complete_model_text(
        provider_kind=effective_model.provider,
        endpoint=effective_model.endpoint,
        model=effective_model.model,
        api_key=effective_model.api_key,
        prompt=prompt,
        timeout_seconds=model_timeout_seconds_from_env(),
    )


def _filter_preface_blocks(preface: str, existing_paths: set[str] | None = None) -> list[str]:
    seen = set(existing_paths or ())
    blocks: list[str] = []
    current_block: list[str] = []
    current_path: str | None = None
    for line in preface.splitlines():
        if line.startswith("## "):
            if current_block and current_path and current_path not in seen and not is_preset_test_path(current_path):
                blocks.append("\n".join(current_block))
                seen.add(current_path)
            current_path = line[3:].strip().replace(" ", "")
            current_block = [line]
        else:
            if current_block:
                current_block.append(line)
    if current_block and current_path and current_path not in seen and not is_preset_test_path(current_path):
        blocks.append("\n".join(current_block))
    return blocks


def _merge_prefaces(primary: str, secondary: str) -> str:
    primary_blocks = _filter_preface_blocks(primary) if primary else []
    existing = set()
    for block in primary_blocks:
        first_line = block.splitlines()[0]
        if first_line.startswith("## "):
            existing.add(first_line[3:].strip().replace(" ", ""))
    secondary_blocks = _filter_preface_blocks(secondary, existing) if secondary else []
    all_blocks = primary_blocks + secondary_blocks
    return "\n".join(all_blocks)


def _workspace_auxiliary_configs(workspace: Path, max_chars_per_file: int = 4_000) -> str:
    configs: dict[str, str] = {}
    config_exts = {".json", ".yaml", ".yml", ".toml"}
    data_sample_exts = {".csv", ".tsv", ".jsonl", ".txt"}
    for search_dir in (workspace / "config", workspace / "data", workspace / "notes", workspace):
        if not search_dir.is_dir():
            continue
        try:
            for item in sorted(search_dir.iterdir()):
                if not item.is_file() or item.name.startswith("."):
                    continue
                is_config = item.suffix in config_exts
                is_data_sample = search_dir.name == "data" and item.suffix in data_sample_exts
                is_note = search_dir.name == "notes" and item.suffix in {".md", ".txt"}
                is_doc = item.suffix in {".md", ".txt"} and (
                    item.name.lower().startswith("readme")
                    or item.name.lower().startswith("spec")
                    or search_dir == workspace
                )
                if is_config or is_data_sample or is_note or is_doc:
                    rel = item.relative_to(workspace).as_posix()
                    limit = 1_500 if is_data_sample else max_chars_per_file
                    if item.stat().st_size <= 65_536:
                        try:
                            sample = item.read_text(encoding="utf-8", errors="replace")[:limit]
                            configs[rel] = sample
                        except OSError:
                            pass
        except OSError:
            pass
    if not configs:
        return ""
    from onecode.kernel.read_preface import preface_text

    return preface_text(configs, max_chars=max_chars_per_file)


def prepare_shell_model_call(task: str, workspace: Path, run_id: str | None = None) -> dict[str, Any]:
    survey = _bound("shell_read_survey")(workspace, task)
    if survey.get("reason") in {"model_provider_timeout", "model_provider_error"}:
        return {"stop": failed_read_survey_result(workspace, task, str(survey.get("reason")), run_id)}
    if survey.get("status") != "completed" and survey.get("reason") not in {
        None,
        "no_progress",
        "resource_budget_exceeded",
        "action_exception",
        "search_miss",
        "repeated_action",
    }:
        return {"stop": _survey_stop(survey)}
    extras = shell_model_task_extras(task, workspace)
    surveyed_text = survey.get("preface")
    named_text = extras.get("preface")
    surveyed = surveyed_text.strip() if isinstance(surveyed_text, str) else ""
    named = named_text.strip() if isinstance(named_text, str) else ""
    aux = _workspace_auxiliary_configs(workspace)
    merged_preface = _merge_prefaces(named, surveyed)
    if aux:
        merged_preface = _merge_prefaces(merged_preface, aux)
    notes = _shell_context_notes(workspace)
    preface = "\n".join(part for part in (merged_preface, notes) if part)
    extras["preface"] = preface or None
    planned = _shell_write_prompt(task, workspace, preface)
    from onecode.kernel.model_guidance import _contract_spec_snippet

    note = _contract_spec_snippet(workspace, task=task)
    if note and note not in planned:
        planned = planned.rstrip() + "\n\n" + note
    return {"task": planned, "extras": extras}


def _opens_complete_rewrite(result: dict[str, Any], patch_only: bool) -> bool:
    reason = result.get("reason")
    if reason == "patch_search_not_found":
        return True
    return reason == "verifier_failed" and patch_only


def _rewrite_already_offered(task: str) -> bool:
    return "Write exactly one complete Python file" in task


def _offer_complete_rewrite(workspace: Path, task: str, failed: dict[str, Any]) -> dict[str, Any]:
    target = _rewrite_target(task, workspace)
    stored_config = _bound("read_model_config")(include_secret=True)
    effective_model = resolve_effective_model_config(os.environ, stored_config)
    try:
        return _bound("run_model_task")(
            initial_asset_prompt(task or target, target),
            workspace=workspace,
            model=effective_model.model,
            api_key=effective_model.api_key,
            provider_kind=effective_model.provider,
            endpoint=effective_model.endpoint,
            require_explicit_approval=True,
            max_repair_attempts=0,
            sandbox_config=SandboxConfig(workspace=workspace),
        )
    except (MissingModelApiKey, ModelProviderError):
        return failed


def _rewrite_target(task: str, workspace: Path) -> str:
    required = required_python_files(task)
    if required:
        return required[0]
    root = workspace / "src"
    if root.is_dir():
        files = [
            path.relative_to(workspace).as_posix()
            for path in sorted(root.rglob("*.py"))
            if "__pycache__" not in path.parts
        ]
        if files:
            return files[0]
    existing = _existing_implementation_files(workspace)
    if existing:
        return existing[0]
    return "src/app.py"


def _shell_context_notes(workspace: Path) -> str:
    notes = [note for note in (_memory_note(workspace), _mcp_note(workspace)) if note]
    return "\n".join(notes)


def _memory_note(workspace: Path) -> str:
    lines: list[str] = []
    for record in load_agent_memory(workspace)[-5:]:
        text = record.get("text") or record.get("note")
        if isinstance(text, str) and text.strip():
            lines.append(text.strip()[:500])
    if not lines:
        return ""
    return "Confirmed memory:\n" + "\n".join(lines)


def _mcp_note(workspace: Path) -> str:
    del workspace
    from onecode.kernel.model_config import onecode_home

    path = onecode_home() / "mcp_servers.json"
    if not path.is_file():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    servers = data.get("mcpServers") if isinstance(data, dict) else None
    if not isinstance(servers, dict) or not servers:
        return ""
    names = ", ".join(sorted(str(name) for name in servers))
    return f"MCP servers available through approval: {names}."


def _remember_confirmed_completion(
    workspace: Path,
    metadata: dict[str, Any],
    task: str,
    result: dict[str, Any],
) -> None:
    if metadata.get("confirm_memory") is not True or result.get("status") != "completed":
        return
    remember_turn(
        workspace,
        {"text": task[:500], "status": "completed"},
        confirmed=True,
        cycle="model_continue",
    )


_MENTIONED_PYTHON = re.compile(r"(?<![\w./-])((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.py)")


_MENTIONED_JSON = re.compile(r"(?<![\w./-])((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.json)")


_JSON_ONLY_TASK = re.compile(r"不要改业务代码|不改业务代码|do not change (?:the )?(?:business )?code", re.IGNORECASE)


_PREFACE_HEADING = re.compile(r"^## ([^\n]+)", re.MULTILINE)


_REFUSED_PYTHON = re.compile(
    r"(?:别改|不要改|不修改|不得修改|do not modify|don't modify)\s*`?([A-Za-z0-9_./-]+\.py)",
    re.IGNORECASE,
)


def _refused_python_files(task: str) -> set[str]:
    refused: set[str] = set()
    for match in _REFUSED_PYTHON.findall(task):
        relative = match.replace("\\", "/")
        refused.add(relative)
        refused.add(Path(relative).name)
    return refused


def _mentioned_existing_python_files(task: str, workspace: Path) -> list[str]:
    refused = _refused_python_files(task)
    found: list[str] = []
    for match in _MENTIONED_PYTHON.findall(task):
        relative = match.replace("\\", "/")
        if relative in found or relative in refused or Path(relative).name in refused or is_preset_test_path(relative):
            continue
        if (workspace / relative).is_file():
            found.append(relative)
        if len(found) == 4:
            break
    return found


_TASK_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")


_CN_CODE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("配置", ("config", "settings", "conf")),
    ("加载", ("load", "loader")),
    ("环境", ("env", "environment")),
    ("前缀", ("prefix",)),
    ("清理", ("cleanup", "clean")),
    ("回收", ("collect", "gc")),
    ("异常", ("exception", "crash")),
    ("校验", ("validate", "validation", "validator")),
    ("认证", ("auth", "authenticate")),
    ("解析", ("parse", "parser")),
    ("路由", ("route", "router")),
    ("中间件", ("middleware",)),
    ("数据库", ("db", "database", "model")),
    ("异步", ("async", "await")),
    ("线程", ("thread", "threading")),
    ("套接字", ("socket",)),
    ("序列化", ("serialize", "serializer")),
)


_TOKEN_STOP = frozenset(
    {
        "this",
        "that",
        "with",
        "from",
        "into",
        "your",
        "file",
        "files",
        "code",
        "task",
        "test",
        "tests",
        "only",
        "return",
        "json",
        "asset",
        "python",
        "existing",
        "modify",
        "change",
        "write",
        "patch",
        "please",
        "class",
        "function",
        "the",
        "and",
        "for",
        "not",
        "but",
        "all",
        "any",
        "can",
        "use",
        "has",
        "had",
        "out",
        "was",
        "are",
        "via",
        "its",
        "per",
        "how",
    }
)


def _task_tokens(task: str) -> list[str]:
    found: list[str] = []
    for cn_key, en_terms in _CN_CODE_KEYWORDS:
        if cn_key in task:
            for term in en_terms:
                if term not in found and term.casefold() not in _TOKEN_STOP:
                    found.append(term)
                    if len(found) >= 12:
                        return found
    for token in _TASK_TOKEN.findall(task):
        if token.casefold() in _TOKEN_STOP or token in found:
            continue
        found.append(token)
        if len(found) == 12:
            break
    return found


def _ranked_implementation_files(task: str, workspace: Path) -> list[str]:
    tokens = _task_tokens(task)
    if not tokens:
        return []
    denied = {"unittest.py", "pytest.py", "conftest.py", "sitecustomize.py", "usercustomize.py"}
    scored: list[tuple[int, str]] = []
    scanned = 0
    for path in sorted(workspace.rglob("*.py")):
        if scanned >= 400:
            break
        if "__pycache__" in path.parts or not path.is_file():
            continue
        relative = path.relative_to(workspace).as_posix()
        if is_preset_test_path(relative) or Path(relative).name in denied:
            continue
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8")[:80_000]
        except (OSError, UnicodeError):
            continue
        score = 0
        for token in tokens:
            if token in path.name or token in relative:
                score += 5
            score += min(text.count(token), 20)
        if score:
            scored.append((score, relative))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [relative for _, relative in scored[:4]]


def _asks_for_new_tests(task: str) -> bool:
    from onecode.kernel.model_guidance import asks_for_new_tests

    return asks_for_new_tests(task)


def _new_test_prompt(task: str) -> str:
    return (
        "Add exactly one new unittest file under tests/.\n"
        "Do not modify any file that already exists under tests/.\n"
        "Do not modify implementation files.\n"
        "Return one complete JSON asset. Do not return patches, execution_plan, or run_command.\n"
        f"Task: {task}"
    )


def _mentioned_json_file(task: str) -> str | None:
    if _JSON_ONLY_TASK.search(task) is None:
        return None
    found: list[str] = []
    for match in _MENTIONED_JSON.findall(task):
        relative = match.replace("\\", "/")
        parts = relative.split("/")
        if ".." in parts or any(part in {".git", ".github", ".onecode"} for part in parts):
            continue
        if is_preset_test_path(relative) or relative in found:
            continue
        found.append(relative)
    if len(found) == 1:
        return found[0]
    return None


def _python_files_in_preface(preface: str, workspace: Path) -> list[str]:
    denied = {"unittest.py", "pytest.py", "conftest.py", "sitecustomize.py", "usercustomize.py"}
    found: list[str] = []
    for heading in _PREFACE_HEADING.findall(preface):
        relative = heading.replace(" / ", "/").strip().replace("\\", "/")
        if not relative.endswith(".py") or Path(relative).name in denied or is_preset_test_path(relative):
            continue
        if relative in found or not (workspace / relative).is_file():
            continue
        found.append(relative)
        if len(found) == 4:
            break
    return found


def _one_file_prompt(task: str, target: str) -> str:
    if target.endswith(".py"):
        return initial_asset_prompt(task, target)
    return (
        "Write exactly one complete file as a JSON asset.\n"
        f"Target: {target}\n"
        f"Original task: {task}\n"
        "The asset content must be the complete non-empty file. "
        "Do not return patches, execution_plan, or run_command. "
        "Do not modify tests/."
    )


def _existing_implementation_files(workspace: Path) -> list[str]:
    denied = {"unittest.py", "pytest.py", "conftest.py", "sitecustomize.py", "usercustomize.py"}
    found: list[str] = []
    for path in sorted(workspace.rglob("*.py")):
        if "__pycache__" in path.parts or not path.is_file():
            continue
        relative = path.relative_to(workspace).as_posix()
        if is_preset_test_path(relative) or Path(relative).name in denied:
            continue
        found.append(relative)
        if len(found) == 8:
            break
    return found


def _listed_file_prompt(task: str, paths: list[str]) -> str:
    listed = ", ".join(paths)
    if os.environ.get("ONECODE_PREFER_PATCH", "").lower() in {"1", "true", "yes"}:
        return (
            "Change an existing Python file from this list using patches.\n"
            f"Existing files: {listed}\n"
            f"Task: {task}\n"
            "Return JSON with patches only. Do not return full-file assets. "
            "Do not include execution_plan or run_command. Do not modify tests/."
            + data_contract_guidance(task)
        )
    return (
        "Change exactly one existing Python file from this list. "
        "Its current text is in the preface above. "
        "Return it as one complete JSON asset. Do not return patches. "
        "Do not include execution_plan or run_command. Do not modify tests/.\n"
        f"Existing files: {listed}\n"
        f"Task: {task}"
        + data_contract_guidance(task)
    )


def _shell_write_prompt(task: str, workspace: Path, preface: str = "") -> str:
    missing = missing_required_files(task, workspace)
    if len(missing) > 1:
        return narrow_plan_prompt(task, {"detail": "start with one named file", "failure_kind": "resource_budget_exceeded"}, [])
    if len(missing) == 1:
        return initial_asset_prompt(task, missing[0])
    required = required_python_files(task)
    if len(required) == 1 and (workspace / required[0]).is_file():
        return _asset_or_patch_prompt(task, workspace, required[0])
    if len(required) == 1:
        return initial_asset_prompt(task, required[0])
    json_target = _mentioned_json_file(task)
    if json_target is not None:
        return _one_file_prompt(task, json_target)
    if _asks_for_new_tests(task):
        return _new_test_prompt(task)
    targeted = _targeted_python_paths(task, workspace)
    if targeted:
        return _prompt_for_paths(task, workspace, targeted)
    surveyed = _python_files_in_preface(preface, workspace)
    if len(surveyed) == 1:
        return _asset_or_patch_prompt(task, workspace, surveyed[0])
    if len(surveyed) > 1:
        return _listed_file_prompt(task, surveyed)
    existing = _existing_implementation_files(workspace)
    if len(existing) == 1:
        return initial_asset_prompt(task, existing[0])
    if existing:
        return _listed_file_prompt(task, existing)
    return task


def failed_read_survey_result(workspace: Path, task: str, reason: str, run_id: str | None) -> dict[str, Any]:
    context = create_context(workspace_root=workspace, run_id=run_id)
    trace_path = context.evidence_root / "trace.jsonl"
    failure = {
        "failure_kind": reason,
        "task_sha256": hashlib.sha256(task.encode("utf-8")).hexdigest(),
        "detail": reason,
        "retryable": False,
    }
    write_trace_event(
        trace_path,
        TraceEvent(
            trace_id=context.run_id,
            run_id=context.run_id,
            span_id="model-call",
            parent_span_id="run",
            event_type="model_call_started",
            status="started",
            payload={"provider": "survey"},
        ),
    )
    write_trace_event(
        trace_path,
        TraceEvent(
            trace_id=context.run_id,
            run_id=context.run_id,
            span_id="model-call",
            parent_span_id="run",
            event_type="model_call_failed",
            status="halted",
            payload=failure,
        ),
    )
    return failed_model_result(context, failure)


def shell_stop_response(stopped: dict[str, Any], model: str) -> tuple[dict[str, Any], int]:
    from onecode.web.api_handlers import chat_completion_payload, format_run_result
    code = {"model_provider_timeout": 504, "model_provider_error": 502}.get(str(stopped.get("reason")))
    if code is None:
        return chat_completion_payload(format_run_result(stopped, "model"), model, stopped, "model"), 200
    payload = error_payload(str(stopped.get("reason")), "model planning failed before execution")
    payload["onecode"] = {"mode": "model", "result": stopped}
    return payload, code


def _survey_stop(survey: dict[str, Any]) -> dict[str, Any]:
    status = str(survey.get("status") or "halted")
    reason = survey.get("reason") if isinstance(survey.get("reason"), str) else None
    return {
        "status": status,
        "reason": reason,
        "status_code": survey.get("status_code"),
        "partial": True,
        "requested_count": 0,
        "completed_count": 0,
        "skipped_count": 0,
        "failed_count": 1,
        "assets": [],
        "cycle": agent_cycle_decision(status, reason),
    }


def _reject_existing_preset_test_stage(workspace: Path, body: dict[str, Any], before: dict[str, str]) -> None:
    stage = body.get("stage")
    if not isinstance(stage, dict):
        return
    path = stage.get("path")
    if not isinstance(path, str) or not is_preset_test_path(path):
        return
    from onecode.kernel.preset_tests import normalized_preset_test_path

    normalized = normalized_preset_test_path(path)
    existing = {normalized_preset_test_path(item).casefold() for item in before}
    if normalized.casefold() in existing or (workspace / normalized).is_file():
        raise ValueError("preset tests cannot be staged")


def _stage_approved_host_bytes(workspace: Path, body: dict[str, Any]) -> None:
    stage = body.get("stage")
    if stage is None:
        return
    if not isinstance(stage, dict):
        raise ValueError("stage must be an object")
    path = stage.get("path")
    content = stage.get("content")
    if not isinstance(path, str) or not isinstance(content, str):
        raise ValueError("stage path and content must be strings")
    encoded = content.encode("utf-8")
    if len(encoded) > 100_000:
        raise ValueError("stage content is too large")
    stage_bytes(workspace, path, encoded, approved=True)


def verify_shell_write(
    result: dict[str, Any],
    workspace: Path,
    before: dict[str, str] | None = None,
    targeted_test: str | None = None,
) -> dict[str, Any]:
    has_internal_tests = (workspace / "tests").is_dir()
    host_cmd_env = os.environ.get("ONECODE_HOST_VERIFIER_CMD")
    has_host_script = (workspace / "verifier.py").is_file()
    if result.get("status") != "completed" or (not has_internal_tests and not host_cmd_env and not has_host_script):
        return result
    current_tests = preset_test_hashes(workspace)
    if before is not None and preset_test_baseline_changed(before, current_tests):
        blocked = dict(result)
        blocked["status"] = "halted"
        blocked["reason"] = "verifier_failed"
        blocked["delivery_status"] = "blocked"
        blocked["preset_tests_changed"] = True
        blocked["preset_test_hashes"] = before
        if blocked.get("run_id"):
            from onecode.kernel.run_inspection import apply_verifier_evidence
            return apply_verifier_evidence(blocked, workspace, [])
        return blocked
    from onecode.kernel.run_inspection import apply_verifier_evidence
    from onecode.kernel.verifier import run_two_stage_verifier, targeted_test_for_path

    resolved_target = targeted_test
    if resolved_target is None:
        for candidate_key in ("path", "target_path"):
            val = result.get(candidate_key)
            if isinstance(val, str):
                resolved_target = targeted_test_for_path(workspace, val)
                if resolved_target:
                    break
        if resolved_target is None and isinstance(result.get("payload"), dict):
            payload_path = result["payload"].get("path")
            if isinstance(payload_path, str):
                resolved_target = targeted_test_for_path(workspace, payload_path)
        if resolved_target is None and isinstance(result.get("assets"), list):
            for asset in result["assets"]:
                if isinstance(asset, dict) and isinstance(asset.get("path"), str):
                    resolved_target = targeted_test_for_path(workspace, asset["path"])
                    if resolved_target:
                        break
        if resolved_target is None and isinstance(result.get("patches"), list):
            for patch_item in result["patches"]:
                if isinstance(patch_item, dict) and isinstance(patch_item.get("path"), str):
                    resolved_target = targeted_test_for_path(workspace, patch_item["path"])
                    if resolved_target:
                        break

    checked, verifier_runs = run_two_stage_verifier(
        workspace,
        targeted_test=resolved_target,
        sandbox_config=SandboxConfig(workspace=workspace),
    )
    if checked.reason == "no_unittest_collected":
        return result
    verified = {**result, "preset_test_hashes": current_tests} if checked.status == "passed" else result
    return apply_verifier_evidence(verified, workspace, verifier_runs)



__all__ = [
    "DEFAULT_MODEL_ID",
    "DIRECT_CHAT_SYSTEM_PROMPT",
    "TASK_PREFIXES",
    "TASK_MARKERS",
    "PATH_MARKERS",
    "DEFAULT_MODEL_TIMEOUT_SECONDS",
    "MAX_MODEL_TIMEOUT_SECONDS",
    "APPROVAL_MESSAGE_PATTERN",
    "model_timeout_seconds_from_env",
    "build_models_payload",
    "latest_user_message",
    "query_workspace_param",
    "project_status_payload",
    "continue_named_files",
    "_targeted_python_paths",
    "_selected_python_paths",
    "_fit_preface_paths",
    "_file_exceeds_preface",
    "_asset_or_patch_prompt",
    "_prompt_for_paths",
    "shell_model_task_extras",
    "shell_read_survey",
    "complete_read_survey",
    "_filter_preface_blocks",
    "_merge_prefaces",
    "_workspace_auxiliary_configs",
    "prepare_shell_model_call",
    "_opens_complete_rewrite",
    "_rewrite_already_offered",
    "_offer_complete_rewrite",
    "_rewrite_target",
    "_shell_context_notes",
    "_memory_note",
    "_mcp_note",
    "_remember_confirmed_completion",
    "_MENTIONED_PYTHON",
    "_MENTIONED_JSON",
    "_JSON_ONLY_TASK",
    "_PREFACE_HEADING",
    "_REFUSED_PYTHON",
    "_refused_python_files",
    "_mentioned_existing_python_files",
    "_TASK_TOKEN",
    "_CN_CODE_KEYWORDS",
    "_TOKEN_STOP",
    "_task_tokens",
    "_ranked_implementation_files",
    "_asks_for_new_tests",
    "_new_test_prompt",
    "_mentioned_json_file",
    "_python_files_in_preface",
    "_one_file_prompt",
    "_existing_implementation_files",
    "_listed_file_prompt",
    "_shell_write_prompt",
    "failed_read_survey_result",
    "shell_stop_response",
    "_survey_stop",
    "_reject_existing_preset_test_stage",
    "_stage_approved_host_bytes",
    "verify_shell_write",
]
