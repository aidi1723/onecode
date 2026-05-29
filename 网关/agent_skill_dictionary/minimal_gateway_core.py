from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .trigram_contract import (
    derive_hidden_intent_locks,
    get_lifecycle_steps,
    get_trigram_relations,
    validate_trigram_contract,
)


DEFAULT_ONEWORD_DICT = Path(__file__).with_name("oneword_dict.json")
LOW_CONFIDENCE_THRESHOLD = 0.75


@dataclass(frozen=True)
class CompileResult:
    active_code: str
    requested_code: str
    confidence: float
    reason: str


def load_oneword_dict(path: str | Path = DEFAULT_ONEWORD_DICT) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    roots = data.get("roots")
    if not isinstance(roots, dict) or not roots:
        raise ValueError("oneword_dict.json must contain a non-empty roots object")
    errors = []
    for code, root in roots.items():
        errors.extend(validate_trigram_contract(str(code), root))
    if errors:
        raise ValueError(f"oneword_dict.json trigram contract errors: {errors}")
    return data


def rewrite_with_oneword_dict(
    body: dict[str, Any],
    dictionary: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    config = dictionary or load_oneword_dict()
    rewritten = deepcopy(body)
    user_message = _latest_user_message(rewritten.get("messages", []))
    compile_result = _compile_to_root_code(user_message, config)
    tool_names = [_tool_name(tool) for tool in rewritten.get("tools", [])] if isinstance(rewritten.get("tools"), list) else []
    hidden_intent_locks = derive_hidden_intent_locks(
        compile_result.active_code,
        {"requested_tools": tool_names, "message": user_message},
    )
    compile_result = _apply_hidden_intent_locks(compile_result, hidden_intent_locks)
    root = config["roots"][compile_result.active_code]

    rewritten.setdefault("messages", []).insert(
        0,
        {
            "role": "system",
            "content": _build_minimal_system_prompt(compile_result.active_code, root),
        },
    )
    rewritten["temperature"] = root["temperature"]
    if isinstance(rewritten.get("tools"), list):
        rewritten["tools"] = _filter_tools(rewritten["tools"], set(root["allowed_tools"]))

    metadata = {
        "active_code": compile_result.active_code,
        "requested_code": compile_result.requested_code,
        "confidence": compile_result.confidence,
        "compile_reason": compile_result.reason,
        "hexagram": root["hexagram"],
        "binary_trigram": root["binary_trigram"],
        "yin_yang_profile": root["yin_yang_profile"],
        "control_bias": root["control_bias"],
        "physical_control_flows": root["physical_control_flows"],
        "allowed_tools": root["allowed_tools"],
        "evidence_required": root["evidence_required"],
        "halt_model_forwarding": bool(root.get("halt_model_forwarding")),
    }
    metadata.update(get_trigram_relations(compile_result.active_code))
    metadata["lifecycle_steps"] = get_lifecycle_steps(compile_result.active_code)
    metadata["hidden_intent_locks"] = hidden_intent_locks
    return rewritten, metadata


def resolve_with_oneword_dict(
    message: str,
    dictionary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = dictionary or load_oneword_dict()
    compile_result = _compile_to_root_code(message, config)
    hidden_intent_locks = derive_hidden_intent_locks(
        compile_result.active_code,
        {"requested_tools": [], "message": message},
    )
    compile_result = _apply_hidden_intent_locks(compile_result, hidden_intent_locks)
    root = config["roots"][compile_result.active_code]
    metadata = {
        "active_code": compile_result.active_code,
        "requested_code": compile_result.requested_code,
        "confidence": compile_result.confidence,
        "compile_reason": compile_result.reason,
        "hexagram": root["hexagram"],
        "binary_trigram": root["binary_trigram"],
        "yin_yang_profile": root["yin_yang_profile"],
        "control_bias": root["control_bias"],
        "physical_control_flows": root["physical_control_flows"],
        "temperature": root["temperature"],
        "allowed_tools": root["allowed_tools"],
        "blocked_tools": root["blocked_tools"],
        "control_vector": root["control_vector"],
        "evidence_required": root["evidence_required"],
        "halt_model_forwarding": bool(root.get("halt_model_forwarding")),
    }
    metadata.update(get_trigram_relations(compile_result.active_code))
    metadata["lifecycle_steps"] = get_lifecycle_steps(compile_result.active_code)
    metadata["hidden_intent_locks"] = hidden_intent_locks
    return metadata


def _apply_hidden_intent_locks(
    compile_result: CompileResult,
    hidden_intent_locks: list[str],
) -> CompileResult:
    if "卫" not in hidden_intent_locks:
        return compile_result
    return CompileResult(
        active_code="卫",
        requested_code=compile_result.active_code,
        confidence=1.0,
        reason=f"{compile_result.reason}+hidden_intent_guard_lock",
    )


def _compile_to_root_code(message: str, dictionary: dict[str, Any]) -> CompileResult:
    roots = dictionary["roots"]
    stripped = message.strip()
    explicit_aliases = {"审": "查"}
    if len(stripped) >= 2 and stripped[1] in {":", "："}:
        requested = stripped[0]
        if requested in roots:
            return CompileResult(requested, requested, 1.0, "explicit_root_prefix")
        if requested in explicit_aliases and explicit_aliases[requested] in roots:
            return CompileResult(explicit_aliases[requested], requested, 1.0, "explicit_alias_prefix")

    lowered = stripped.lower()
    rules: tuple[tuple[str, float, tuple[str, ...]], ...] = (
        ("停", 0.95, ("停一下", "暂停", "熔断", "不要继续")),
        ("问", 0.9, ("不明确", "问清楚", "澄清", "确认一下")),
        ("卫", 0.88, ("安全", "危险", "注入", "权限", "漏洞", "供应链", "依赖风险", "cve", "rm -rf")),
        ("修", 0.86, ("bug", "报错", "失败", "跑不通", "修复", "异常")),
        ("测", 0.86, ("测试", "验证", "覆盖率", "单测")),
        ("记", 0.84, ("记一下", "记录", "adr", "项目记忆")),
        ("总", 0.84, ("总结", "交接", "压缩上下文")),
        ("查", 0.82, ("查", "看看", "找一下", "结构", "入口", "审查", "review")),
    )
    for code, confidence, keywords in rules:
        if code in roots and any(keyword in lowered for keyword in keywords):
            return CompileResult(code, code, confidence, "keyword_rules")
    return CompileResult("问", "unknown", 0.6, "low_confidence_to_prompt")


def _build_minimal_system_prompt(code: str, root: dict[str, Any]) -> str:
    return "\n".join(
        [
            "一字诀 MVP 网关已接管请求。",
            f"根字: {code}",
            f"卦象: {root['hexagram']}",
            f"二进制爻象: {root['binary_trigram']}",
            f"控制偏置: {root['control_bias']}",
            f"物理控制流: {root['physical_control_flows']}",
            f"工具白名单: {', '.join(root['allowed_tools']) if root['allowed_tools'] else 'NONE'}",
            f"系统铁律: {root['system_prompt']}",
            f"证据要求: {', '.join(root['evidence_required'])}",
            "不得声明未由系统层证据支持的完成状态。",
        ]
    )


def _filter_tools(tools: list[dict[str, Any]], allowed_names: set[str]) -> list[dict[str, Any]]:
    return [tool for tool in tools if _tool_name(tool) in allowed_names]


def _tool_name(tool: dict[str, Any]) -> str:
    if isinstance(tool.get("function"), dict):
        return str(tool["function"].get("name", ""))
    return str(tool.get("name", ""))


def _latest_user_message(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content", ""))
    return ""
