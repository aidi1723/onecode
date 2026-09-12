from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast


TaskMode = Literal["chat", "read_task", "change_task"]
VALID_TASK_MODES = frozenset({"chat", "read_task", "change_task"})

CHANGE_PREFIXES = ("造：", "改：", "写：", "跑：", "执行：", "修：", "测试：")
ENGLISH_FILE_CHANGE_PREFIXES = ("create ", "write ", "edit ", "delete ")
READ_PREFIXES = ("查：", "检查：", "审查：", "诊断：")
CHANGE_SIGNALS = (
    "修改",
    "创建",
    "生成文件",
    "写入",
    "修复",
    "删除",
    "执行命令",
    "运行命令",
    "运行测试",
    "安装",
    "升级依赖",
    "patch",
    "commit",
    "write file",
    "modify",
    "create file",
    "run command",
    "run tests",
    "install",
)
READ_SIGNALS = (
    "检查",
    "审查",
    "查看",
    "列出",
    "搜索",
    "查找",
    "诊断",
    "分析项目",
    "项目状态",
    "仓库状态",
    "inspect",
    "review",
    "list files",
    "search",
    "diagnose",
    "check project",
    "git status",
)
PATH_SIGNALS = (
    "src/",
    "tests/",
    "docs/",
    "readme",
    ".txt",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".md",
    ".json",
    ".yaml",
    ".yml",
)
EXPLANATION_PREFIXES = ("什么是", "为什么", "如何理解", "解释一下", "介绍一下", "what is", "why ")
MUTATION_ACTIONS = (
    "修改",
    "创建",
    "写入",
    "写一个",
    "写个",
    "写文件",
    "修复",
    "修一下",
    "运行一下",
    "跑一下",
    "fix ",
    "create ",
    "write ",
    "edit ",
    "run tests",
    "run command",
)
READ_ACTIONS = (
    "检查",
    "查看",
    "看看",
    "审查",
    "分析",
    "诊断",
    "inspect",
    "review",
    "check",
    "read",
)
PROJECT_OBJECTS = (
    "项目",
    "仓库",
    "代码",
    "测试",
    "命令",
    "文件",
    "bug",
    "src",
    "repo",
    "project",
    "code",
    "test",
)


@dataclass(frozen=True)
class TaskClassification:
    mode: TaskMode
    reason: str


def classify_task(text: str, *, explicit_mode: str | None = None) -> TaskMode:
    return classify_task_with_reason(text, explicit_mode=explicit_mode).mode


def classify_task_with_reason(
    text: str,
    *,
    explicit_mode: str | None = None,
) -> TaskClassification:
    if explicit_mode is not None:
        if explicit_mode not in VALID_TASK_MODES:
            raise ValueError("metadata.onecode_mode must be chat, read_task, or change_task")
        return TaskClassification(cast(TaskMode, explicit_mode), "explicit_mode")
    if not isinstance(text, str) or not text.strip():
        return TaskClassification("chat", "default_chat")

    stripped = text.strip()
    lowered = stripped.lower()
    has_path = any(signal in lowered for signal in PATH_SIGNALS)
    has_project_object = has_path or any(signal in lowered for signal in PROJECT_OBJECTS)
    if stripped.startswith(CHANGE_PREFIXES):
        return TaskClassification("change_task", "explicit_change_prefix")
    if _is_explanation_request(lowered) and not has_path:
        return TaskClassification("chat", "default_chat")
    if (
        _starts_english_file_change_request(lowered)
        or any(signal in lowered for signal in CHANGE_SIGNALS)
    ):
        return TaskClassification("change_task", "mutation_signal")
    if any(action in lowered for action in MUTATION_ACTIONS) and has_project_object:
        reason = "mutation_action_with_path" if has_path else "mutation_action_with_project_object"
        return TaskClassification("change_task", reason)
    if stripped.startswith(READ_PREFIXES):
        return TaskClassification("read_task", "explicit_read_prefix")
    if any(signal in lowered for signal in READ_SIGNALS):
        return TaskClassification("read_task", "read_signal")
    if any(action in lowered for action in READ_ACTIONS) and has_project_object:
        reason = "read_action_with_path" if has_path else "read_action_with_project_object"
        return TaskClassification("read_task", reason)
    if any(signal in lowered for signal in PATH_SIGNALS) and _has_imperative_signal(lowered):
        return TaskClassification("read_task", "read_action_with_path")
    return TaskClassification("chat", "default_chat")


def _has_imperative_signal(text: str) -> bool:
    return any(signal in text for signal in ("看", "读", "查", "解释", "review", "read", "check", "inspect"))


def _starts_english_file_change_request(text: str) -> bool:
    if not text.startswith(ENGLISH_FILE_CHANGE_PREFIXES):
        return False
    return " file " in f" {text} " or any(signal in text for signal in PATH_SIGNALS)


def _is_explanation_request(text: str) -> bool:
    return text.startswith(EXPLANATION_PREFIXES) or " explanation of " in f" {text} "
