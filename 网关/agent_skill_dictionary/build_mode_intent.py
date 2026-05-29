from __future__ import annotations

from typing import Any

from .build_mode_types import (
    HEX_CREATE,
    HEX_HALT,
    HEX_INSPECT,
    HEX_PROMPT,
    IntentEvidence,
    SCOPE_SHAOYANG,
    SCOPE_TAIYANG,
    SCOPE_TAIYIN,
)

WRITE_MARKERS = ("创建", "新建", "写", "修改", "修复", "实现", "生成项目", "write", "patch", "mkdir", "implement")
TEST_MARKERS = ("pytest", "测试", "单测", "run test", "npm test")
READONLY_MARKERS = ("只读", "审查", "分析", "查看", "解释", "review", "inspect")
DANGEROUS_MARKERS = ("rm -rf", "curl | sh", "chmod -R", "/etc/passwd", "~/.ssh", "~/.codex", "~/.claude")
REJECTED_DANGER_MARKERS = ("拒绝", "不要执行", "不执行", "不可信", "投毒", "攻击输入", "do not execute", "reject")
DIRECT_DANGER_ACTION_MARKERS = ("执行", "运行", "删除", "抹除", "清空", "execute", "run ", "delete", "remove")


def resolve_intent(payload: dict[str, Any]) -> IntentEvidence:
    text = _payload_text(payload)
    lowered = text.lower()
    reasons: list[str] = []

    if any(marker in lowered for marker in DANGEROUS_MARKERS) and not _is_rejected_danger_reference(lowered):
        return IntentEvidence("yin", SCOPE_TAIYIN, HEX_HALT, 1.0, ("dangerous_command",))

    if _is_explicit_readonly(lowered):
        return IntentEvidence("yin", SCOPE_SHAOYANG, HEX_INSPECT, 0.86, ("readonly_inspect",))

    if any(marker in lowered for marker in WRITE_MARKERS):
        reasons.append("requires_file_write")
    if any(marker in lowered for marker in TEST_MARKERS):
        reasons.append("requires_tests")

    if reasons:
        return IntentEvidence("yang", SCOPE_TAIYANG, HEX_CREATE, 0.9, tuple(reasons))

    if any(marker in lowered for marker in READONLY_MARKERS):
        if "只读" in lowered or "审查" in lowered or "review" in lowered or "inspect" in lowered:
            return IntentEvidence("yin", SCOPE_SHAOYANG, HEX_INSPECT, 0.82, ("readonly_inspect",))
        return IntentEvidence("yin", SCOPE_SHAOYANG, HEX_PROMPT, 0.78, ("pure_text",))

    return IntentEvidence("yin", SCOPE_SHAOYANG, HEX_PROMPT, 0.55, ("low_confidence_prompt",))


def _is_explicit_readonly(lowered: str) -> bool:
    readonly = "只读" in lowered or "不要修改" in lowered or "不修改" in lowered or "no write" in lowered
    inspect = "审查" in lowered or "查看" in lowered or "分析" in lowered or "review" in lowered or "inspect" in lowered
    return readonly and inspect


def _is_rejected_danger_reference(lowered: str) -> bool:
    if not any(marker in lowered for marker in REJECTED_DANGER_MARKERS):
        return False
    if not any(marker in lowered for marker in WRITE_MARKERS + TEST_MARKERS):
        return False
    direct_action = any(marker in lowered for marker in DIRECT_DANGER_ACTION_MARKERS)
    return not direct_action or "不要执行" in lowered or "不执行" in lowered or "拒绝" in lowered


def _payload_text(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    input_value = payload.get("input")
    if isinstance(input_value, str):
        parts.append(input_value)
    elif isinstance(input_value, list):
        for item in input_value:
            if isinstance(item, dict):
                parts.append(_content_text(item.get("content", "")))
            else:
                parts.append(str(item))
    for message in payload.get("messages", []):
        if isinstance(message, dict) and str(message.get("role") or "").lower() == "system":
            continue
        content = message.get("content", "")
        parts.append(_content_text(content))
    for tool in payload.get("tools", []):
        if not isinstance(tool, dict):
            continue
        function = tool.get("function") if isinstance(tool.get("function"), dict) else {}
        parts.append(str(tool.get("name") or function.get("name") or tool.get("type") or ""))
    return "\n".join(parts)


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    return str(content or "")
