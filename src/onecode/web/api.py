from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qs, urlparse

from onecode.web.auth import LOOPBACK_HOSTS, local_request_allowed, request_authorized
from onecode.web.request_body import read_json_request_body
from onecode.web.responses import encode_json_payload, error_payload
from onecode.web.workspace import (
    configured_allowed_workspace_roots,
    require_allowed_workspace,
    workspace_allowed,
    workspace_from_request,
    workspace_from_value,
)

from onecode.kernel.diagnostics import run_doctor
from onecode.kernel.effective_model_config import resolve_effective_model_config
from onecode.kernel.run_inspection import inspect_run, list_runs
from onecode.kernel.model_loop import (
    _generate_missing_artifacts,
    _modified_paths_from_result,
    _src_files_for_repair,
    data_contract_guidance,
    execute_model_plan,
    failed_model_result,
    initial_asset_prompt,
    missing_required_files,
    named_python_files,
    narrow_plan_prompt,
    repair_prompt,
    required_python_files,
    run_model_task,
)
from onecode.kernel.context import create_context
from onecode.kernel.trace import TraceEvent, write_trace_event
from onecode.kernel.agent_memory import load_agent_memory, remember_turn
from onecode.kernel.read_preface import SINGLE_FILE_PREFACE_CHARS, collect_preface, render_workspace_preface
from onecode.kernel.host_stage import stage_bytes
from onecode.kernel.outcome_policy import agent_cycle_decision
from onecode.kernel.sandbox import SandboxConfig
from onecode.kernel.approval_plans import claim_approval_plan, finalize_approval_plan
from onecode.kernel.model_config import (
    DEFAULT_ONECODE_MODEL,
    discover_models,
    read_bounded_response,
    read_model_config,
    write_model_config,
)
from onecode.kernel.gateway_engine import adjudicate_gateway_prediction, validate_assistant_content
from onecode.kernel.model_provider import MissingModelApiKey, ModelProviderError, api_key_from_env, build_provider_config
from onecode.kernel.allow_evidence import complete_allow_evidence
from onecode.kernel.path_guard import PathGuard, PathGuardError
from onecode.kernel.preset_tests import (
    authoritative_preset_test_hashes,
    is_preset_test_path,
    preset_test_baseline_changed,
    preset_test_hashes,
)
from onecode.kernel.run_inspection import ledger_matches_workspace
from onecode.kernel.prompt_rules import decide_prompt
from onecode.kernel.project_context import discover_project_context
from onecode.kernel.runner import run_task
from onecode.self_audit import audit_self
from onecode.kernel.skill_context import discover_skill_context, public_skill_context
from onecode.kernel.shell_projection import (
    attach_shell_projection,
    attach_shell_projection_to_runs_payload,
    project_run_to_shell,
    shell_projection_schema,
)
from onecode.kernel.runtime_config import inspect_runtime_config
from onecode.kernel.task_classification import classify_task
from onecode.kernel.run_id import validate_optional_run_id, validate_run_id
from onecode.kernel.wal import global_wal_metrics_summary
from onecode.kernel.verifier import (
    DEFAULT_VERIFIER_POLICY_PATH,
    load_verifier_policy,
    verifier_policy_presets_summary,
    write_verifier_policy,
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
    runs = list_runs(resolved)["runs"]
    latest_run = attach_shell_projection(runs[-1]) if runs else None
    effective_model = resolve_effective_model_config(os.environ, read_model_config(include_secret=True))
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
    stored_config = read_model_config(include_secret=True)
    effective_model = resolve_effective_model_config(os.environ, stored_config)
    return run_model_task(
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
        return (workspace / relative).stat().st_size > SINGLE_FILE_PREFACE_CHARS
    except OSError:
        return False


def _asset_or_patch_prompt(task: str, workspace: Path, target: str) -> str:
    if _file_exceeds_preface(workspace, target):
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
            "max_repair_attempts": 1,
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
        "max_repair_attempts": 1,
    }


def shell_read_survey(workspace: Path, task: str) -> dict[str, Any]:
    from onecode.kernel.read_preface import read_only_registry_execute, survey_model_reads

    return survey_model_reads(workspace, task, complete_read_survey, read_only_registry_execute(workspace))


def complete_read_survey(prompt: str) -> str:
    from onecode.kernel.model_provider import complete_model_text

    stored_config = read_model_config(include_secret=True)
    effective_model = resolve_effective_model_config(os.environ, stored_config)
    return complete_model_text(
        provider_kind=effective_model.provider,
        endpoint=effective_model.endpoint,
        model=effective_model.model,
        api_key=effective_model.api_key,
        prompt=prompt,
        timeout_seconds=model_timeout_seconds_from_env(),
    )


def prepare_shell_model_call(task: str, workspace: Path, run_id: str | None = None) -> dict[str, Any]:
    survey = shell_read_survey(workspace, task)
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
    surveyed = "" if _targeted_python_paths(task, workspace) else (surveyed_text.strip() if isinstance(surveyed_text, str) else "")
    named = named_text.strip() if isinstance(named_text, str) else ""
    notes = _shell_context_notes(workspace)
    preface = "\n".join(part for part in (surveyed, named, notes) if part)
    extras["preface"] = preface or None
    planned = _shell_write_prompt(task, workspace, preface)
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
    stored_config = read_model_config(include_secret=True)
    effective_model = resolve_effective_model_config(os.environ, stored_config)
    try:
        return run_model_task(
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
_TESTS_ONLY = re.compile(r"只补测试|只补\s*tests|只添加测试|只新增测试|only add tests", re.IGNORECASE)
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
    return _TESTS_ONLY.search(task) is not None


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
    if result.get("status") != "completed" or not (workspace / "tests").is_dir():
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


def handle_onecode_project_status(params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    return project_status_payload(workspace), 200


def handle_onecode_shell_schema() -> tuple[dict[str, Any], int]:
    return shell_projection_schema(), 200


def handle_onecode_project_init(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(body.get("workspace") if isinstance(body.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    if body.get("git") is True and not (workspace / ".git").exists():
        subprocess.run(["git", "init"], cwd=str(workspace), check=True, capture_output=True, text=True)
    if body.get("verifierPolicy") is True and not (workspace / DEFAULT_VERIFIER_POLICY_PATH).exists():
        write_verifier_policy(workspace, output=DEFAULT_VERIFIER_POLICY_PATH)
    return project_status_payload(workspace), 200


def parse_limit(value: Any, default: int = 20, maximum: int = 100) -> int:
    if isinstance(value, bool):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(parsed, maximum))


def parse_window_seconds(value: Any, default: int = 60, maximum: int = 86_400) -> int:
    if isinstance(value, bool):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(parsed, maximum))


def handle_onecode_runs_list(params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    payload = list_runs(workspace)
    payload["runs"] = payload["runs"][-parse_limit(params.get("limit")) :]
    return attach_shell_projection_to_runs_payload(payload), 200


def handle_onecode_metrics(params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    window_seconds = parse_window_seconds(params.get("window_seconds"))
    try:
        wal_summary = global_wal_metrics_summary(workspace, window_seconds=window_seconds)
    except ValueError as exc:
        return error_payload("invalid_metrics_request", str(exc)), 400
    return {
        "workspace": str(workspace),
        "control_plane": {
            "scope": "summary",
            "raw_entries_included": False,
            "source": "global_wal",
        },
        "global_wal_summary": wal_summary,
    }, 200


def handle_onecode_run_inspect(run_id: str, params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        run_id = validate_run_id(run_id)
    except ValueError as exc:
        return error_payload("invalid_run_id", str(exc)), 400
    try:
        workspace = workspace_from_value(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    exit_code, payload = inspect_run(workspace, run_id)
    payload = attach_shell_projection(payload)
    return payload, 200 if exit_code == 0 else 404


def handle_onecode_run_resume(run_id: str, body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        run_id = validate_run_id(run_id)
    except ValueError as exc:
        return error_payload("invalid_run_id", str(exc)), 400
    try:
        workspace = workspace_from_value(body.get("workspace") if isinstance(body.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    message = body.get("message")
    task = message if isinstance(message, str) and message.strip() else f"继续运行 {run_id}"
    stored_config = read_model_config(include_secret=True)
    effective_model = resolve_effective_model_config(os.environ, stored_config)
    try:
        prepared = prepare_shell_model_call(task, workspace)
    except MissingModelApiKey as exc:
        return error_payload("model_configuration_missing", str(exc)), 503
    if "stop" in prepared:
        stopped = prepared["stop"]
        code = {"model_provider_timeout": 504, "model_provider_error": 502}.get(str(stopped.get("reason")))
        if code is not None:
            payload = error_payload(str(stopped.get("reason")), "model planning failed before execution")
            payload["onecode"] = {"mode": "model", "result": stopped}
            return payload, code
        return attach_shell_projection(stopped), 200
    try:
        result = run_model_task(
            prepared["task"],
            workspace=workspace,
            run_id=None,
            resume_from_run_id=run_id,
            model=effective_model.model,
            api_key=effective_model.api_key,
            provider_kind=effective_model.provider,
            endpoint=effective_model.endpoint,
            require_explicit_approval=True,
            **prepared["extras"],
        )
    except MissingModelApiKey as exc:
        return error_payload("model_configuration_missing", str(exc)), 503
    except ModelProviderError as exc:
        return error_payload("model_provider_error", str(exc)), 502
    return attach_shell_projection(result), 200


def handle_onecode_plan_approval(
    plan_id: str,
    body: dict[str, Any],
    on_turn: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[dict[str, Any], int]:
    approved = body.get("approved")
    if not isinstance(approved, bool):
        return error_payload("invalid_approval", "approved must be boolean"), 400
    try:
        workspace = workspace_from_value(body.get("workspace") if isinstance(body.get("workspace"), str) else None)
        stored = claim_approval_plan(workspace, plan_id)
    except ValueError as exc:
        status = 409 if str(exc) in {"approval_plan_in_progress", "approval_plan_already_resolved"} else 400
        return error_payload("invalid_approval_plan", str(exc)), status
    if not approved:
        result = {  # type: ignore
            "run_id": None,
            "status": "cancelled",
            "reason": "approval_rejected",
            "partial": False,
            "requested_count": 0,
            "completed_count": 0,
            "skipped_count": 1,
            "failed_count": 0,
            "assets": [],
            "plan_id": plan_id,
        }
        finalize_approval_plan(stored, "rejected", result)
        return result, 200
    before = authoritative_preset_test_hashes(workspace)
    try:
        _reject_existing_preset_test_stage(workspace, body, before)
        _stage_approved_host_bytes(workspace, body)
    except (ValueError, PathGuardError) as exc:
        finalize_approval_plan(stored, "rejected", {"status": "halted", "reason": "sovereignty_breach", "assets": []})
        return error_payload("invalid_stage", str(exc)), 400
    ledger_mismatch = ledger_matches_workspace(workspace)
    if ledger_mismatch is not None:
        halt_result = {"status": "halted", "reason": ledger_mismatch, "assets": []}
        finalize_approval_plan(stored, "rejected", halt_result)
        return halt_result, 400
    user_task = stored.model_metadata.get("user_task")
    user_task = user_task if isinstance(user_task, str) else ""
    written_before = set(required_python_files(user_task)) - set(missing_required_files(user_task, workspace)) if user_task else set()
    result = execute_model_plan(
        stored.plan,
        workspace=workspace,
        http_timeout_seconds=60,
        run_id=None,
        resume_from_run_id=None,
        run_metadata={**stored.model_metadata, "approved_plan_id": plan_id},
        approval_callback=lambda _step: True,
        on_turn=on_turn,
    )
    if user_task:
        _generate_missing_artifacts(
            user_task,
            workspace,
            _modified_paths_from_result(result)
            or [a.path for a in stored.plan.assets] + [p.path for p in stored.plan.patches],
        )
    if user_task and missing_required_files(user_task, workspace):
        try:
            continued = continue_named_files(user_task, workspace, written_before)
        except (MissingModelApiKey, ModelProviderError):
            continued = None
        if continued is not None:
            finalize_approval_plan(stored, "approved", result)
            return attach_shell_projection(continued), 200
    result = verify_shell_write(result, workspace, before)
    patch_only = bool(stored.plan.patches) and not stored.plan.assets and not stored.plan.execution_steps
    if _opens_complete_rewrite(result, patch_only) and not _rewrite_already_offered(user_task):
        rewrite = _offer_complete_rewrite(workspace, user_task or stored.plan.task, result)
        finalize_approval_plan(stored, "approved", result)
        return attach_shell_projection(rewrite), 200
    if result.get("reason") == "verifier_failed" and not patch_only:
        failed = {**result, "workspace_files": _src_files_for_repair(workspace)}
        stored_config = read_model_config(include_secret=True)
        effective_model = resolve_effective_model_config(os.environ, stored_config)
        try:
            repair = run_model_task(
                repair_prompt(stored.plan.task, failed),
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
            repair = result
        tail = _verifier_tail(result)
        if isinstance(repair, dict) and tail:
            repair = {**repair, "verifier_tail": tail}
        finalize_approval_plan(stored, "approved", result)
        return attach_shell_projection(repair), 200
    finalize_approval_plan(stored, "approved", result)
    return attach_shell_projection(result), 200


def run_light_task(task: str, *, workspace: Path, run_id: str | None = None, resume_from_run_id: str | None = None) -> dict[str, Any]:
    return run_task(
        task,
        workspace=workspace,
        run_id=run_id,
        resume_from_run_id=resume_from_run_id,
        completed_evidence_mode="wal",
        evidence_durability="relaxed",
    )


def handle_onecode_verifier_presets() -> tuple[dict[str, Any], int]:
    return verifier_policy_presets_summary(), 200


def verifier_policy_payload(workspace: Path) -> dict[str, Any]:
    resolved = require_allowed_workspace(workspace)
    policy_path = resolved / DEFAULT_VERIFIER_POLICY_PATH
    payload: dict[str, Any] = {
        "workspace": str(resolved),
        "path": str(policy_path),
        "exists": policy_path.exists(),
        "valid": False,
        "policy": None,
    }
    if not policy_path.exists():
        return payload
    try:
        policy = load_verifier_policy(policy_path)
        payload["policy"] = {
            "verifiers": [
                {
                    "id": spec.id,
                    "command": spec.command,
                    "cwd": spec.cwd,
                    "timeout_ms": spec.timeout_ms,
                }
                for spec in policy.specs.values()
            ]
        }
        payload["valid"] = True
    except ValueError as exc:
        payload["error"] = str(exc)
    return payload


def handle_onecode_verifier_policy_get(params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    return verifier_policy_payload(workspace), 200


def handle_onecode_verifier_policy_write(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(body.get("workspace") if isinstance(body.get("workspace"), str) else None)
        preset_ids = body.get("presetIds")
        if preset_ids is not None and not isinstance(preset_ids, list):
            return error_payload("invalid_verifier_policy", "presetIds must be a list of strings"), 400
        if isinstance(preset_ids, list) and not all(isinstance(item, str) for item in preset_ids):
            return error_payload("invalid_verifier_policy", "presetIds must be a list of strings"), 400
        write_verifier_policy(
            workspace=workspace,
            output=DEFAULT_VERIFIER_POLICY_PATH,
            preset_ids=preset_ids if isinstance(preset_ids, list) else None,
            force=body.get("force") is True,
        )
    except ValueError as exc:
        return error_payload("invalid_verifier_policy", str(exc)), 400
    return verifier_policy_payload(workspace), 200


def handle_onecode_model_config_get() -> tuple[dict[str, Any], int]:
    try:
        return read_model_config(), 200
    except ValueError as exc:
        return error_payload("invalid_model_config", str(exc)), 400


def handle_onecode_model_config_write(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    endpoint = body.get("endpoint")
    api_key = body.get("apiKey") or body.get("api_key")
    model = body.get("model")
    provider = body.get("provider")
    models = body.get("models")
    try:
        payload = write_model_config(
            endpoint=endpoint if isinstance(endpoint, str) else "",
            api_key=api_key if isinstance(api_key, str) else "",
            model=model if isinstance(model, str) else None,
            provider=provider if isinstance(provider, str) and provider.strip() else "openai-compatible",
            models=models if isinstance(models, list) else None,
            preserve_existing_secret=True,
        )
    except ValueError as exc:
        return error_payload("invalid_model_config", str(exc)), 400
    return payload, 200


def handle_onecode_models_discover(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    endpoint = body.get("endpoint")
    api_key = body.get("apiKey") or body.get("api_key")
    model = body.get("model")
    if not isinstance(endpoint, str) or not endpoint.strip():
        return error_payload("invalid_model_config", "endpoint is required"), 400
    if not isinstance(api_key, str) or not api_key.strip():
        return error_payload("invalid_model_config", "apiKey is required"), 400
    payload = discover_models(endpoint, api_key)
    models = payload["models"]
    selected_model = model if isinstance(model, str) and model.strip() else (models[0] if models else DEFAULT_ONECODE_MODEL)
    result: dict[str, Any] = {
        **payload,
        "selected_model": selected_model,
    }
    if body.get("save") is True:
        result["config"] = write_model_config(
            endpoint=endpoint,
            api_key=api_key,
            model=selected_model,
            models=models,
        )
    return result, 200


def handle_onecode_gateway_adjudicate(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    user = body.get("user")
    prediction = body.get("prediction")
    if not isinstance(user, str) or user.strip() == "":
        return error_payload("invalid_request", "user must be a non-empty string"), 400
    if not isinstance(prediction, str) or prediction.strip() == "":
        return error_payload("invalid_request", "prediction must be a non-empty JSON string"), 400
    try:
        raw_prediction = validate_assistant_content(prediction)
    except ValueError:
        raw_prediction = None
    adjudicated_prediction = adjudicate_gateway_prediction(user, prediction)
    facts = adjudicated_prediction.get("facts") if isinstance(adjudicated_prediction, dict) else {}
    action = adjudicated_prediction.get("action") if isinstance(adjudicated_prediction, dict) else ""
    evidence = complete_allow_evidence(
        action if isinstance(action, str) else "",
        facts if isinstance(facts, dict) else {},
        user,
        Path.cwd(),
    )
    return {
        "status": "ok",
        "user": user,
        "raw_prediction": raw_prediction,
        "adjudicated_prediction": adjudicated_prediction,
        "changed": raw_prediction != adjudicated_prediction,
        "prompt_decision": decide_prompt(user),
        "allow_evidence": evidence,
    }, 200


def read_json_document(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "missing_file"
    except json.JSONDecodeError:
        return None, "invalid_json"
    if not isinstance(value, dict):
        return None, "not_object"
    return value, None


def handle_onecode_doctor() -> tuple[dict[str, Any], int]:
    return run_doctor(), 200


def handle_onecode_audit_self() -> tuple[dict[str, Any], int]:
    return audit_self(Path.cwd(), run_doctor, run_unittest=False), 200


def handle_onecode_run_evidence(run_id: str, params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        run_id = validate_run_id(run_id)
    except ValueError as exc:
        return error_payload("invalid_run_id", str(exc)), 400
    try:
        workspace = workspace_from_value(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    exit_code, summary = inspect_run(workspace, run_id)
    if exit_code != 0:
        return attach_shell_projection(summary), 404
    summary = attach_shell_projection(summary)
    ledger_path_value = summary.get("ledger_path")
    manifest_path_value = summary.get("manifest_path")
    if summary.get("evidence_mode") == "wal" or not isinstance(ledger_path_value, str) or not isinstance(manifest_path_value, str):
        return {
            "summary": summary,
            "ledger": None,
            "ledger_error": "wal_only",
            "manifest": None,
            "manifest_error": "wal_only",
            "checkpoints": [],
            "wal_path": summary.get("wal_path"),
        }, 200
    evidence_root = workspace / ".onecode" / "runs" / run_id
    try:
        ledger_path = PathGuard.resolve_contained(evidence_root, ledger_path_value)
        manifest_path = PathGuard.resolve_contained(evidence_root, manifest_path_value)
    except PathGuardError:
        return error_payload("path_outside_evidence", "evidence path escapes the run directory"), 400
    ledger, ledger_error = read_json_document(ledger_path)
    manifest, manifest_error = read_json_document(manifest_path)
    checkpoints = []
    for record in (manifest or {}).get("checkpoints", []):
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            checkpoints.append({"record": record, "error": "invalid_checkpoint_record"})
            continue
        try:
            checkpoint_path = PathGuard.resolve_contained(evidence_root, record["path"])
        except PathGuardError:
            checkpoints.append({"path": record["path"], "record": record, "document": None, "error": "path_outside_evidence"})
            continue
        document, error = read_json_document(checkpoint_path)
        checkpoints.append(
            {
                "path": str(checkpoint_path),
                "record": record,
                "document": document,
                "error": error,
            }
        )
    return {
        "summary": summary,
        "ledger": ledger,
        "ledger_error": ledger_error,
        "manifest": manifest,
        "manifest_error": manifest_error,
        "checkpoints": checkpoints,
    }, 200


def message_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return ""


def should_run_onecode_task(user_message: str) -> bool:
    return classify_task(user_message) != "chat"


def parse_approval_message(user_message: str) -> tuple[str, bool] | None:
    match = APPROVAL_MESSAGE_PATTERN.fullmatch(user_message.strip())
    if match is None:
        return None
    return match.group(2), match.group(1) != "拒绝"


def direct_chat_completion(
    messages: list[dict[str, Any]],
    *,
    model: str,
    provider_kind: str,
    endpoint: str | None,
    api_key: str | None = None,
    timeout_seconds: float = 60,
) -> str:
    config = build_provider_config(provider_kind, endpoint=endpoint, model=model)
    resolved_api_key = api_key if api_key is not None else api_key_from_env(provider_kind=provider_kind)
    if resolved_api_key is None:
        raise MissingModelApiKey(f"{config.env_key} is required for direct chat")
    chat_messages = [{"role": "system", "content": DIRECT_CHAT_SYSTEM_PROMPT}]
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in {"user", "assistant", "system"}:
            continue
        content = message_content_to_text(message.get("content"))
        if content.strip():
            chat_messages.append({"role": message["role"], "content": content})
    body = json.dumps({"model": config.model, "messages": chat_messages}).encode("utf-8")
    request = urllib.request.Request(
        config.endpoint,
        data=body,
        headers={"Authorization": f"Bearer {resolved_api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(read_bounded_response(response).decode("utf-8"))
    except TimeoutError as exc:
        raise TimeoutError("direct chat request timed out") from exc
    except urllib.error.URLError as exc:
        raise ModelProviderError(f"direct chat request failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise ModelProviderError("direct chat response was not valid JSON") from exc
    except ValueError as exc:
        raise ModelProviderError("direct chat response exceeds maximum size") from exc
    if not isinstance(payload, dict):
        raise ModelProviderError("direct chat response must be an object")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ModelProviderError("direct chat response missing choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None  # type: ignore
    content = message.get("content") if isinstance(message, dict) else None  # type: ignore
    if not isinstance(content, str) or content.strip() == "":
        raise ModelProviderError("direct chat response missing message content")
    return content


def chat_completion_payload(
    content: str,
    model: str,
    run_result: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    created = int(time.time())
    summary = project_run_to_shell(run_result)
    return {
        "id": f"onecode-{run_result.get('run_id') or created}",
        "object": "chat.completion",
        "created": created,
        "model": model or DEFAULT_MODEL_ID,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
        "onecode": {
            "mode": mode,
            "summary": summary,
            "result": run_result,
        },
    }


def handle_chat_completion(
    body: dict[str, Any],
    on_turn: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[dict[str, Any], int]:
    user_message = latest_user_message(body.get("messages"))
    if user_message.strip() == "":
        return error_payload("invalid_request", "messages must include a user message"), 400

    try:
        workspace = workspace_from_request(body)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    model = str(body.get("model") or DEFAULT_MODEL_ID)
    approval_message = parse_approval_message(user_message)
    if approval_message is not None:
        plan_id, approved = approval_message
        result, status_code = handle_onecode_plan_approval(
            plan_id,
            {"workspace": str(workspace), "approved": approved},
            on_turn=on_turn,
        )
        if status_code != 200:
            return result, status_code
        return chat_completion_payload(format_run_result(result, "approval"), model, result, "approval"), 200
    metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
    explicit_mode = metadata.get("onecode_mode") if isinstance(metadata.get("onecode_mode"), str) else None  # type: ignore
    try:
        task_mode = classify_task(user_message, explicit_mode=explicit_mode)
    except ValueError as exc:
        return error_payload("invalid_task_mode", str(exc)), 400
    stored_config = read_model_config(include_secret=True)
    effective_model = resolve_effective_model_config(os.environ, stored_config)
    execution_model = effective_model.model if model == DEFAULT_MODEL_ID else model
    provider_kind = effective_model.provider
    endpoint = effective_model.endpoint
    stored_api_key = effective_model.api_key
    run_id = metadata.get("run_id")  # type: ignore
    try:
        run_id = validate_optional_run_id(str(run_id) if run_id else None)
    except ValueError as exc:
        return error_payload("invalid_run_id", str(exc)), 400
    if task_mode == "chat":
        try:
            content = direct_chat_completion(
                body.get("messages") if isinstance(body.get("messages"), list) else [],  # type: ignore
                model=execution_model,
                provider_kind=provider_kind,
                endpoint=endpoint,
                api_key=stored_api_key,
            )
        except MissingModelApiKey as exc:
            return error_payload("model_configuration_missing", str(exc)), 503
        except ModelProviderError as exc:
            return error_payload("model_provider_error", str(exc)), 502
        return chat_completion_payload(content, model, {"status": "completed", "run_id": run_id}, "chat"), 200

    try:
        model_timeout_seconds = model_timeout_seconds_from_env()
    except ValueError as exc:
        return error_payload("invalid_model_timeout", str(exc)), 503

    try:
        prepared = prepare_shell_model_call(user_message, workspace, run_id=str(run_id) if run_id else None)
    except MissingModelApiKey as exc:
        return error_payload("model_configuration_missing", str(exc)), 503
    if "stop" in prepared:
        return shell_stop_response(prepared["stop"], model)
    try:
        result = run_model_task(
            prepared["task"],
            workspace=workspace,
            run_id=str(run_id) if run_id else None,
            model=execution_model,
            api_key=stored_api_key,
            provider_kind=provider_kind,
            endpoint=endpoint,
            task_mode=task_mode,
            require_explicit_approval=True,
            http_timeout_seconds=model_timeout_seconds,
            on_turn=on_turn,
            **prepared["extras"],
        )
        failure_statuses = {
            "model_provider_timeout": 504,
            "model_provider_error": 502,
            "invalid_model_plan": 502,
        }
        failure_reason = result.get("reason")
        if failure_reason in failure_statuses:
            detail = result.get("payload")
            extra = detail.get("detail") if isinstance(detail, dict) else None
            message = "model planning failed before execution"
            if isinstance(extra, str) and extra.strip():
                message = f"{message}: {extra.strip()[:300]}"
            payload = error_payload(str(failure_reason), message)
            payload["onecode"] = {"mode": "model", "result": result}
            return payload, failure_statuses[failure_reason]
        if failure_reason == "no_actionable_plan":
            mode = "no_action"
        elif failure_reason == "approval_required":
            mode = "approval_required"
        else:
            mode = "model"
    except MissingModelApiKey as exc:
        return error_payload("model_configuration_missing", str(exc)), 503
    except ValueError as exc:
        if "plan must include at least one asset" not in str(exc):
            return error_payload("invalid_model_plan", str(exc)), 502
        result = {
            "run_id": str(run_id) if run_id else None,
            "status": "halted",
            "reason": "no_actionable_plan",
            "detail": str(exc),
            "partial": True,
            "intent_type": "no_action",
            "requested_count": 0,
            "completed_count": 0,
            "skipped_count": 0,
            "failed_count": 1,
            "assets": [],
        }
        mode = "no_action"
    except ModelProviderError as exc:
        return error_payload("model_provider_error", str(exc)), 502

    content = format_run_result(result, mode)
    if isinstance(metadata, dict):
        _remember_confirmed_completion(workspace, metadata, user_message, result)
    return chat_completion_payload(content, model, result, mode), 200


def stream_chat_completion(
    body: dict[str, Any],
    write: Callable[[bytes], None],
) -> tuple[dict[str, Any], int]:
    def on_turn(turn: dict[str, Any]) -> None:
        write(_sse_bytes(tool_turn_chunk(turn)))

    payload, status = handle_chat_completion(body, on_turn=on_turn)
    if status != 200:
        return payload, status
    write(_sse_bytes(content_chunk(payload)))
    write(_sse_bytes(stop_chunk(payload)))
    write(b"data: [DONE]\n\n")
    return payload, status


def tool_turn_chunk(turn: dict[str, Any]) -> dict[str, Any]:
    tool_names = [name for name in turn.get("tool_names", []) if isinstance(name, str)]
    reason = turn.get("reason")
    label = ", ".join(tool_names) or str(turn.get("step_id") or "tool")
    content = f"{label}: {turn.get('status') or 'completed'}"
    if isinstance(reason, str) and reason:
        content += f" | {reason}"
    return {
        "object": "chat.completion.chunk",
        "choices": [{"index": 0, "delta": {"content": content + "\n"}, "finish_reason": None}],
        "onecode": {
            "event": "tool_turn",
            "step_id": turn.get("step_id"),
            "tool_names": tool_names,
            "status": turn.get("status"),
            "reason": reason,
        },
    }


def content_chunk(payload: dict[str, Any]) -> dict[str, Any]:
    choice = payload.get("choices", [{}])[0] if isinstance(payload.get("choices"), list) else {}
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    content = message.get("content") if isinstance(message, dict) else ""
    return {
        "id": payload.get("id"),
        "object": "chat.completion.chunk",
        "created": payload.get("created"),
        "model": payload.get("model"),
        "choices": [
            {
                "index": 0,
                "delta": {"role": "assistant", "content": content if isinstance(content, str) else ""},
                "finish_reason": None,
            }
        ],
    }


def stop_chunk(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": payload.get("id"),
        "object": "chat.completion.chunk",
        "created": payload.get("created"),
        "model": payload.get("model"),
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }


def _sse_bytes(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


def format_run_result(result: dict[str, Any], mode: str) -> str:
    if mode == "approval" and result.get("status") == "cancelled":
        return "计划已拒绝，未执行任何变更。"
    if mode == "approval" and result.get("status") == "completed":
        return "计划已批准并执行完成，结果已写入 OneCode 证据链。"
    if result.get("reason") == "approval_required":
        message = (
            "计划已生成，但包含写入或命令操作，尚未执行。"
            f"审批计划 ID：`{result.get('plan_id')}`。确认后再执行。"
        )
        summary = result.get("plan_summary")
        actions = summary.get("actions") if isinstance(summary, dict) else None
        if isinstance(actions, list):
            message += "\n待审批操作：\n```json\n" + json.dumps(actions, ensure_ascii=False, indent=2) + "\n```"
        visible = _approval_visible_text(result, actions if isinstance(actions, list) else [])
        if visible:
            message += "\n" + visible
        return message
    if result.get("reason") == "no_actionable_plan":
        return "模型没有生成可执行计划，本次任务未执行。请补充明确目标或检查模型配置。"
    if mode == "chat_fallback":
        return (
            "我收到了这条消息，但模型没有生成文件变更或执行计划。"
            "这次已记录为普通 OneCode 对话运行；如果你要我改代码或写文件，请明确说明目标文件和期望内容。"
        )
    projection = project_run_to_shell(result)
    evidence_ref = projection["evidence_ref"]
    lines = [
        f"{projection['compact_message']} ({mode} mode).",
    ]
    ledger_path = evidence_ref.get("ledger_path")
    wal_path = evidence_ref.get("wal_path")
    if ledger_path is not None:
        lines.append(f"Evidence ledger: `{ledger_path}`.")
    elif wal_path is not None:
        lines.append(f"Evidence WAL: `{wal_path}`.")
    return "\n".join(lines)


def _verifier_tail(result: dict[str, Any]) -> str:
    raw = result.get("verifier_results")
    if not isinstance(raw, list):
        return ""
    tails = [
        str(item.get("stderr_tail")).strip()[-400:]
        for item in raw
        if isinstance(item, dict) and isinstance(item.get("stderr_tail"), str) and str(item.get("stderr_tail")).strip()
    ]
    return "\n".join(tails)


def _approval_visible_text(result: dict[str, Any], actions: list[Any]) -> str:
    parts: list[str] = []
    tail = result.get("verifier_tail")
    if isinstance(tail, str) and tail.strip():
        parts.append("测试失败：\n```\n" + tail.strip()[:4000] + "\n```")
    for action in actions:
        if not isinstance(action, dict):
            continue
        diff = action.get("diff")
        if isinstance(diff, str) and diff.strip():
            label = action.get("path") if isinstance(action.get("path"), str) and action.get("path") else action.get("tool")
            parts.append(f"变更 {label}：\n```diff\n{diff.rstrip()}\n```")
        if action.get("tool") == "patch_text":
            search = action.get("search_preview")
            replace = action.get("replace_preview")
            path = action.get("path") if isinstance(action.get("path"), str) else ""
            if isinstance(search, str) and isinstance(replace, str):
                parts.append(f"补丁 {path}：\n查找：\n```\n{search.rstrip()}\n```\n替换：\n```\n{replace.rstrip()}\n```")
        if action.get("host_execution") or (isinstance(action.get("tool"), str) and action["tool"].startswith("mcp.")):
            cmd = action.get("command")
            cmd_str = " ".join(cmd) if isinstance(cmd, list) and cmd else "<未配置命令>"
            args = action.get("arguments", {})
            args_str = json.dumps(args, ensure_ascii=False) if args else "{}"
            where = "宿主机" if action.get("host_execution") else "沙盒"
            parts.append(f"MCP 外部命令（将在{where}执行）：`{cmd_str}`\n参数：`{args_str}`")
    return "\n".join(parts)


def gateway_console_html() -> str:
    return Path(__file__).with_name("gateway_console.html").read_text(encoding="utf-8")



class OneCodeRequestHandler(BaseHTTPRequestHandler):
    server_version = "OneCodeHTTP/1.0"
    timeout = 30

    def do_GET(self) -> None:
        if not self._local_boundary_allowed():
            return
        path = urlparse(self.path).path
        if path == "/":
            self._send_html(gateway_console_html())
            return
        if path == "/health":
            self._send_json({"status": "ok", "service": "onecode"})
            return
        if path == "/v1/models":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            self._send_json(build_models_payload())
            return
        if path == "/v1/onecode/project/status":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            parsed = urlparse(self.path)
            payload, status_code = handle_onecode_project_status({"workspace": query_workspace_param(parsed.query)})
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/shell/schema":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            payload, status_code = handle_onecode_shell_schema()
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/runs":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            payload, status_code = handle_onecode_runs_list(
                {
                    "workspace": query.get("workspace", [None])[0],
                    "limit": query.get("limit", [None])[0],
                }
            )
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/metrics":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            payload, status_code = handle_onecode_metrics(
                {
                    "workspace": query.get("workspace", [None])[0],
                    "window_seconds": query.get("window_seconds", [None])[0],
                }
            )
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/verifier/presets":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            payload, status_code = handle_onecode_verifier_presets()
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/verifier/policy":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            parsed = urlparse(self.path)
            payload, status_code = handle_onecode_verifier_policy_get({"workspace": query_workspace_param(parsed.query)})
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/model-config":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            payload, status_code = handle_onecode_model_config_get()
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/gateway/adjudicate":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            if query.get("demo", [""])[0] in {"1", "true", "yes", "on"}:
                demo_prediction = json.dumps(
                    {
                        "action": "ALLOW_PATCH_WITH_SHA",
                        "facts": {
                            "evidence_state": "required",
                            "intent_type": "patch_text",
                            "path_scope": "workspace_relative",
                            "sandbox_state": "not_required",
                        },
                        "reason": "safe_workspace_patch",
                        "yizijue_state": "111111",
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                payload, status_code = handle_onecode_gateway_adjudicate(
                    {
                        "user": "随便处理一下这个项目",
                        "prediction": demo_prediction,
                    }
                )
                self._send_json(payload, status_code=status_code)
                return
            self._send_json(
                {
                    "status": "ok",
                    "endpoint": "/v1/onecode/gateway/adjudicate",
                    "method": "POST",
                    "demo_url": "/v1/onecode/gateway/adjudicate?demo=1",
                    "required_fields": ["user", "prediction"],
                    "description": "Submit a model candidate JSON string for deterministic OneCode/YiZiJue adjudication.",
                }
            )
            return
        if path.startswith("/v1/onecode/runs/") and path.endswith("/inspect"):
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            run_id = path.removeprefix("/v1/onecode/runs/").removesuffix("/inspect").strip("/")
            parsed = urlparse(self.path)
            payload, status_code = handle_onecode_run_inspect(run_id, {"workspace": query_workspace_param(parsed.query)})
            self._send_json(payload, status_code=status_code)
            return
        if path.startswith("/v1/onecode/runs/") and path.endswith("/evidence"):
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            run_id = path.removeprefix("/v1/onecode/runs/").removesuffix("/evidence").strip("/")
            parsed = urlparse(self.path)
            payload, status_code = handle_onecode_run_evidence(run_id, {"workspace": query_workspace_param(parsed.query)})
            self._send_json(payload, status_code=status_code)
            return
        self._send_json(error_payload("not_found", f"unknown path: {path}"), status_code=404)

    def do_POST(self) -> None:
        if not self._local_boundary_allowed():
            return
        path = urlparse(self.path).path
        if path == "/v1/onecode/project/init":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json_or_send_error()
            if body is None:
                return
            payload, status_code = handle_onecode_project_init(body)
            self._send_json(payload, status_code=status_code)
            return
        if path.startswith("/v1/onecode/runs/") and path.endswith("/resume"):
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json_or_send_error()
            if body is None:
                return
            run_id = path.removeprefix("/v1/onecode/runs/").removesuffix("/resume").strip("/")
            payload, status_code = handle_onecode_run_resume(run_id, body)
            self._send_json(payload, status_code=status_code)
            return
        if path.startswith("/v1/onecode/plans/") and path.endswith("/approval"):
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json_or_send_error()
            if body is None:
                return
            plan_id = path.removeprefix("/v1/onecode/plans/").removesuffix("/approval").strip("/")
            payload, status_code = handle_onecode_plan_approval(plan_id, body)
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/verifier/policy":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json_or_send_error()
            if body is None:
                return
            payload, status_code = handle_onecode_verifier_policy_write(body)
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/model-config":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json_or_send_error()
            if body is None:
                return
            payload, status_code = handle_onecode_model_config_write(body)
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/models/discover":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json_or_send_error()
            if body is None:
                return
            payload, status_code = handle_onecode_models_discover(body)
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/gateway/adjudicate":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json_or_send_error()
            if body is None:
                return
            payload, status_code = handle_onecode_gateway_adjudicate(body)
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/doctor":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            payload, status_code = handle_onecode_doctor()
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/audit-self":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            payload, status_code = handle_onecode_audit_self()
            self._send_json(payload, status_code=status_code)
            return
        if path != "/v1/chat/completions":
            self._send_json(error_payload("not_found", f"unknown path: {path}"), status_code=404)
            return
        if not self._authorized():
            self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
            return
        body = self._read_json_or_send_error()
        if body is None:
            return
        if body.get("stream") is True:
            self._send_streaming_chat(body)
            return
        payload, status_code = handle_chat_completion(body)
        self._send_json(payload, status_code=status_code)

    def log_message(self, format: str, *args: Any) -> None:
        if os.getenv("ONECODE_HTTP_ACCESS_LOG", "").lower() in {"1", "true", "yes", "on"}:
            super().log_message(format, *args)

    def _local_boundary_allowed(self) -> bool:
        port = int(self.server.server_address[1])  # type: ignore
        if local_request_allowed(self.headers, bound_port=port):  # type: ignore
            return True
        self._send_json(
            error_payload("forbidden_origin", "request host or origin is not local"),
            status_code=403,
        )
        return False

    def _authorized(self) -> bool:
        allow_unauthenticated = os.getenv("ONECODE_ALLOW_UNAUTHENTICATED", "").lower() in {"1", "true", "yes", "on"}
        host = self.server.server_address[0]  # type: ignore
        from onecode.kernel.deployment_boundary import api_token

        return request_authorized(
            dict(self.headers.items()),
            api_token() or None,
            allow_unauthenticated=allow_unauthenticated,
            host=host,
        )

    def _read_json(self) -> dict[str, Any] | None:
        return read_json_request_body(self.headers, self.rfile).payload  # type: ignore

    def _read_json_or_send_error(self) -> dict[str, Any] | None:
        result = read_json_request_body(self.headers, self.rfile)  # type: ignore
        if result.payload is not None:
            return result.payload
        self._send_json(
            error_payload(result.error_type or "invalid_json", result.error_message or "request body must be valid JSON"),
            status_code=result.status_code,
        )
        return None

    def _send_json(self, payload: dict[str, Any], status_code: int = 200) -> None:
        encoded = encode_json_payload(payload)
        self.send_response(status_code)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_html(self, html: str, status_code: int = 200) -> None:
        encoded = html.encode("utf-8")
        self.send_response(status_code)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_streaming_chat(self, body: dict[str, Any]) -> None:
        started = False

        def write(data: bytes) -> None:
            nonlocal started
            if not started:
                self.send_response(200)
                self.send_header("content-type", "text/event-stream; charset=utf-8")
                self.send_header("cache-control", "no-cache")
                self.send_header("connection", "close")
                self.end_headers()
                started = True
            self.wfile.write(data)
            self.wfile.flush()

        payload, status = stream_chat_completion(body, write)
        if not started:
            self._send_json(payload, status_code=status)


def run_server(host: str = "127.0.0.1", port: int = 19080) -> None:
    # Security check: non-loopback hosts must have a token configured
    from onecode.kernel.deployment_boundary import api_token

    token = api_token() or None
    allow_unauthenticated = os.getenv("ONECODE_ALLOW_UNAUTHENTICATED", "").lower() in {"1", "true", "yes", "on"}

    if host not in LOOPBACK_HOSTS and allow_unauthenticated and not token:
        raise ValueError(
            f"Security error: Cannot bind to non-loopback host '{host}' with allow_unauthenticated=true and no ONECODE_API_TOKEN. "
            "Either bind to a loopback address (127.0.0.1, localhost, ::1), set ONECODE_API_TOKEN, or disable allow_unauthenticated."
        )

    server = ThreadingHTTPServer((host, port), OneCodeRequestHandler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
