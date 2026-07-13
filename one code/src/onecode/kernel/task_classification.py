from __future__ import annotations

from typing import Literal, cast


TaskMode = Literal["chat", "read_task", "change_task"]
VALID_TASK_MODES = frozenset({"chat", "read_task", "change_task"})

CHANGE_PREFIXES = ("造：", "改：", "写：", "跑：", "执行：", "修：", "测试：")
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
PATH_SIGNALS = ("src/", "tests/", "docs/", "readme", ".py", ".js", ".ts", ".tsx", ".md", ".json", ".yaml", ".yml")
EXPLANATION_PREFIXES = ("什么是", "为什么", "如何理解", "解释一下", "介绍一下", "what is", "why ")


def classify_task(text: str, *, explicit_mode: str | None = None) -> TaskMode:
    if explicit_mode is not None:
        if explicit_mode not in VALID_TASK_MODES:
            raise ValueError("metadata.onecode_mode must be chat, read_task, or change_task")
        return cast(TaskMode, explicit_mode)
    if not isinstance(text, str) or not text.strip():
        return "chat"

    stripped = text.strip()
    lowered = stripped.lower()
    if stripped.startswith(CHANGE_PREFIXES) or any(signal in lowered for signal in CHANGE_SIGNALS):
        return "change_task"
    if stripped.startswith(READ_PREFIXES):
        return "read_task"
    if lowered.startswith(EXPLANATION_PREFIXES) and not any(signal in lowered for signal in READ_SIGNALS):
        return "chat"
    if any(signal in lowered for signal in READ_SIGNALS):
        return "read_task"
    if any(signal in lowered for signal in PATH_SIGNALS) and _has_imperative_signal(lowered):
        return "read_task"
    return "chat"


def _has_imperative_signal(text: str) -> bool:
    return any(signal in text for signal in ("看", "读", "查", "解释", "review", "read", "check", "inspect"))
