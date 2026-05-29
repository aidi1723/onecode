from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .gateway_rule_adapter import build_gateway_rule
from .kernel_contract import HexagramRouter, assert_preflight_contract
from .kernel_policy import filter_allowed_tools, format_kernel_rule, get_kernel_policy, kernel_policy_metadata
from .loader import lookup_entry
from .inspect_executor import build_native_inspect_card
from .skill_mount_loader import load_skill_mount_excerpt
from .tool_guard import inspect_tool_calls
from .workflow_loader import load_workflow_excerpt


@dataclass(frozen=True)
class IntentResult:
    codes: list[str]
    confidence: float
    reason: str


KEYWORD_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("修", ("bug", "报错", "失败", "跑不通", "异常", "修")),
    ("测", ("测试", "单测", "覆盖率", "验证", "确认")),
    ("源", ("依赖", "来源", "license", "License", "已有组件", "复用", "重复造轮子")),
    ("卫", ("安全", "权限", "危险命令", "注入", "拦截")),
    ("查", ("看看", "找一下", "查", "入口", "结构")),
    ("审", ("review", "审查", "有没有问题", "风险")),
    ("设", ("界面", "样式", "设计", "视觉", "组件")),
    ("解", ("解释", "看不懂", "什么意思", "讲一下")),
    ("造", ("新增", "实现", "做一个", "写一个")),
    ("改", ("优化", "重构", "调整", "改成")),
    ("简", ("简单点", "别大改", "最小改动")),
    ("隔", ("隔离", "不可信", "外部输入", "多 Agent")),
    ("部", ("部署", "发布", "上线", "ci", "CI", "cd", "CD")),
    ("数", ("数据", "表格", "csv", "CSV", "清洗", "转换 JSON")),
    ("文", ("文档", "README", "接口文档", "项目说明")),
    ("合", ("合规", "许可证", "license", "License", "法务", "政策")),
    ("搜", ("搜索", "检索", "外部资料", "官网资料", "查找相关文档")),
    ("问", ("问清楚", "先问", "确认一下", "需求不明确", "澄清")),
    ("停", ("停一下", "不要继续", "人工审批", "熔断")),
    ("记", ("记一下", "项目记忆", "记录这个决策", "写进规则", "ADR")),
    ("评", ("评估", "二次检查", "反面审", "靠谱吗", "质量门")),
    ("总", ("总结", "压缩上下文", "交接摘要", "当前进度", "下一步")),
)

STREAM_GUARD_CODES = {"查", "卫"}
STREAM_TOOL_SIGNATURES: tuple[tuple[str, str], ...] = (
    ('"tool_calls"', "openai_tool_calls"),
    ("'tool_calls'", "openai_tool_calls"),
    ('"type":"tool_use"', "anthropic_tool_use"),
    ('"type": "tool_use"', "anthropic_tool_use"),
    ("'type':'tool_use'", "anthropic_tool_use"),
    ("'type': 'tool_use'", "anthropic_tool_use"),
)
ZERO_TOOL_FAST_PATH_CODES = {"解", "问"}
ZERO_TOOL_ACTIONS = {"ZERO_TOOL_BYPASS", "ZERO_TOOL_CLARIFY"}
ZERO_TOOL_MAX_TOKENS = 150
KERNEL_NOTICE_TEXT = (
    "Kernel Notice: unauthorized tool execution blocked by OneWord state rules. "
    "Action canceled by system."
)
NATIVE_INSPECT_TOOL_NAME = "native_inspect_card"
CLAUDE_INSPECT_TOOL_NAMES = {"Read", "LS", "Glob", "Grep", "Bash"}
SHADOW_INSPECT_TOOL_NAMES = {*CLAUDE_INSPECT_TOOL_NAMES, NATIVE_INSPECT_TOOL_NAME}
NATIVE_INSPECT_FALLBACK_TEXT = (
    "[State]: 101-INSPECT | [Target]: *\n"
    "[Files]: native inspect card unavailable in gateway response context\n"
    "[Symbols]: unavailable\n"
    "[Imports]: unavailable\n"
    "[Risks]: none"
)


class StreamBufferInterceptor:
    def __init__(self, metadata: dict[str, Any], max_buffer_chars: int = 4096) -> None:
        self.metadata = metadata
        self.max_buffer_chars = max_buffer_chars
        self._buffer = ""

    def feed(self, chunk: bytes | str) -> dict[str, Any] | None:
        active_code = str(self.metadata.get("root_opcode") or self.metadata.get("active_code") or "")
        if active_code not in STREAM_GUARD_CODES:
            return None
        text = chunk.decode("utf-8", errors="ignore") if isinstance(chunk, bytes) else str(chunk)
        self._buffer = (self._buffer + text)[-self.max_buffer_chars :]
        normalized = self._buffer.lower().replace("\\n", "").replace("\\r", "")
        compact = "".join(normalized.split())
        for signature, violation_type in STREAM_TOOL_SIGNATURES:
            signature_compact = "".join(signature.lower().split())
            if signature_compact in compact:
                return {
                    "type": violation_type,
                    "active_code": active_code,
                    "signature": signature,
                }
        return None


def normalize_intent(user_message: str, dictionary: dict[str, Any]) -> IntentResult:
    known_codes = {entry["code"] for entry in dictionary["entries"]}
    stripped = user_message.strip()
    explicit_code = _explicit_code(stripped, known_codes)
    if explicit_code:
        return IntentResult(codes=[explicit_code], confidence=1.0, reason="explicit_prefix")

    lower_message = stripped.lower()
    halt_code = _halt_control_code(lower_message, known_codes)
    if halt_code:
        return IntentResult(codes=[halt_code], confidence=0.92, reason="high_priority_control")

    codes = _keyword_codes(lower_message, known_codes)
    if _has_action_code(codes):
        return IntentResult(codes=_action_sequence_codes(codes), confidence=0.88, reason="sequential_action_keywords")

    high_priority_code = _high_priority_control_code(lower_message, known_codes)
    if high_priority_code:
        return IntentResult(codes=[high_priority_code], confidence=0.92, reason="high_priority_control")

    if not codes:
        return IntentResult(codes=["查"], confidence=0.6, reason="fallback_to_inspect")

    return IntentResult(codes=_dedupe(codes), confidence=0.86, reason="keyword_rules")


def _keyword_codes(message: str, known_codes: set[str]) -> list[str]:
    codes: list[str] = []
    for code, keywords in KEYWORD_RULES:
        if code not in known_codes:
            continue
        if any(keyword.lower() in message for keyword in keywords):
            codes.append(code)
    return codes


def _has_action_code(codes: list[str]) -> bool:
    return any(code in {"修", "造", "改", "测"} for code in codes)


def _action_sequence_codes(codes: list[str]) -> list[str]:
    priority = ("修", "造", "改", "测", "总")
    deduped = _dedupe(codes)
    sequence = [code for code in priority if code in deduped]
    return sequence or deduped


def _halt_control_code(message: str, known_codes: set[str]) -> str | None:
    if "停" not in known_codes:
        return None
    if any(keyword in message for keyword in ("停一下", "不要继续", "熔断")):
        return "停"
    return None


def _high_priority_control_code(message: str, known_codes: set[str]) -> str | None:
    priority_rules: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("停", ("停一下", "不要继续", "熔断")),
        ("问", ("问清楚", "需求不明确", "澄清")),
        ("记", ("记一下", "记录这个决策", "写进规则", "adr")),
        ("评", ("评估", "二次检查", "反面审", "靠谱吗")),
        ("总", ("总结", "压缩上下文", "交接摘要", "当前进度")),
    )
    for code, keywords in priority_rules:
        if code in known_codes and any(keyword.lower() in message for keyword in keywords):
            return code
    return None


def build_execution_stack(codes: list[str]) -> list[str]:
    return list(reversed(codes))


def rewrite_chat_completion_request(
    body: dict[str, Any],
    dictionary: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    rewritten = deepcopy(body)
    user_message = _latest_user_message(rewritten.get("messages", []))
    intent = normalize_intent(user_message, dictionary)
    stack = build_execution_stack(intent.codes)
    active_code = stack[-1]
    active_entry = lookup_entry(dictionary, active_code)
    root_code = active_entry.raw.get("root_opcode", active_code)
    root_entry = lookup_entry(dictionary, root_code)
    kernel_policy = get_kernel_policy(root_code)
    hexagram_route = determine_hexagram_route(active_code, root_code, kernel_policy, rewritten, intent.codes)
    zero_tool_fast_path = route_allows_zero_tool_fast_path(active_code, hexagram_route)
    system_instruction = (
        build_lightweight_system_instruction(
            active_entry.raw,
            intent.codes,
            stack,
            root_entry.raw,
            kernel_policy,
        )
        if zero_tool_fast_path
        else build_system_instruction(
            active_entry.raw,
            intent.codes,
            stack,
            root_entry.raw,
            kernel_policy,
        )
    )

    messages = rewritten.setdefault("messages", [])
    messages.insert(0, {"role": "system", "content": system_instruction})
    rewritten["temperature"] = kernel_policy.model_overrides.get(
        "temperature",
        active_entry.model_policy["temperature"],
    )
    if zero_tool_fast_path and "tools" in rewritten:
        rewritten["tools"] = []
    elif "tools" in rewritten and isinstance(rewritten["tools"], list):
        rewritten["tools"] = _prefer_native_inspect_chat_tools(
            filter_allowed_tools(rewritten["tools"], kernel_policy),
            root_code,
        )
    if zero_tool_fast_path:
        rewritten["max_tokens"] = ZERO_TOOL_MAX_TOKENS
    assert_preflight_contract(root_code, rewritten)

    metadata = {
        "codes": intent.codes,
        "execution_stack": stack,
        "active_code": active_code,
        "root_opcode": root_code,
        "kernel_policy": kernel_policy_metadata(kernel_policy),
        "confidence": intent.confidence,
        "routing_target": active_entry.routing_target,
        "tool_policy": active_entry.tool_policy,
        "zero_tool_fast_path": zero_tool_fast_path,
        "hexagram_route": hexagram_route,
        "gateway_rule": build_gateway_rule({"source": "gateway_core", "evidence_required": []}),
    }
    return rewritten, metadata


def rewrite_anthropic_messages_request(
    body: dict[str, Any],
    dictionary: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    rewritten = deepcopy(body)
    user_message = _latest_anthropic_user_message(rewritten.get("messages", []))
    intent = normalize_intent(user_message, dictionary)
    stack = build_execution_stack(intent.codes)
    active_code = stack[-1]
    active_entry = lookup_entry(dictionary, active_code)
    root_code = active_entry.raw.get("root_opcode", active_code)
    root_entry = lookup_entry(dictionary, root_code)
    kernel_policy = get_kernel_policy(root_code)
    hexagram_route = determine_hexagram_route(active_code, root_code, kernel_policy, rewritten, intent.codes)
    zero_tool_fast_path = route_allows_zero_tool_fast_path(active_code, hexagram_route)
    system_instruction = (
        build_lightweight_system_instruction(
            active_entry.raw,
            intent.codes,
            stack,
            root_entry.raw,
            kernel_policy,
        )
        if zero_tool_fast_path
        else build_system_instruction(
            active_entry.raw,
            intent.codes,
            stack,
            root_entry.raw,
            kernel_policy,
        )
    )

    rewritten["system"] = _merge_anthropic_system(system_instruction, rewritten.get("system"))
    rewritten["temperature"] = kernel_policy.model_overrides.get(
        "temperature",
        active_entry.model_policy["temperature"],
    )
    shadow_tool_injection = {"applied": False, "source_tools": [], "target_tool": None}
    if zero_tool_fast_path and "tools" in rewritten:
        rewritten["tools"] = []
    elif "tools" in rewritten and isinstance(rewritten["tools"], list):
        rewritten["tools"], shadow_tool_injection = _rewrite_anthropic_inspect_tools(
            rewritten["tools"],
            kernel_policy,
            root_code,
        )
    if zero_tool_fast_path:
        rewritten["max_tokens"] = ZERO_TOOL_MAX_TOKENS
    assert_preflight_contract(root_code, {"tools": _anthropic_tools_for_preflight(rewritten.get("tools", []))})

    metadata = {
        "codes": intent.codes,
        "execution_stack": stack,
        "active_code": active_code,
        "root_opcode": root_code,
        "kernel_policy": kernel_policy_metadata(kernel_policy),
        "confidence": intent.confidence,
        "routing_target": active_entry.routing_target,
        "tool_policy": active_entry.tool_policy,
        "protocol": "anthropic_messages",
        "zero_tool_fast_path": zero_tool_fast_path,
        "hexagram_route": hexagram_route,
        "shadow_tool_injection": shadow_tool_injection,
        "gateway_rule": build_gateway_rule({"source": "gateway_core", "evidence_required": []}),
    }
    return rewritten, metadata


def annotate_chat_completion_response(
    payload: dict[str, Any],
    metadata: dict[str, Any],
    dictionary: dict[str, Any],
) -> dict[str, Any]:
    if metadata.get("zero_tool_fast_path"):
        annotated = deepcopy(payload)
        annotated["yizijue_gateway"] = {
            **metadata,
            "tool_guard": {
                "allowed": True,
                "violations": [],
                "inspected_tool_calls": 0,
                "mode": "bypassed_zero_tool",
            },
        }
        return annotated
    active_entry = lookup_entry(dictionary, metadata["active_code"])
    tool_calls = extract_tool_calls(payload)
    decision = inspect_tool_calls(active_entry, tool_calls)
    annotated = deepcopy(payload)
    annotated["yizijue_gateway"] = {
        **metadata,
        "tool_guard": {
            "allowed": decision.allowed,
            "violations": decision.violations,
            "inspected_tool_calls": len(tool_calls),
        },
    }
    if not decision.allowed:
        annotated["yizijue_gateway"]["blocked"] = True
    return annotated


def block_disallowed_tool_response(
    payload: dict[str, Any],
    metadata: dict[str, Any],
    dictionary: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    annotated = annotate_chat_completion_response(payload, metadata, dictionary)
    guard = annotated["yizijue_gateway"]["tool_guard"]
    if guard["allowed"]:
        return annotated, 200
    rewritten = deepcopy(payload)
    for choice in rewritten.get("choices", []):
        message = choice.setdefault("message", {})
        message.pop("tool_calls", None)
        message["content"] = KERNEL_NOTICE_TEXT
        if choice.get("finish_reason") == "tool_calls":
            choice["finish_reason"] = "stop"
    rewritten["yizijue_gateway"] = {
        **metadata,
        "blocked": True,
        "response_mode": "soft_rewrite",
        "tool_guard": guard,
    }
    return rewritten, 200


def block_disallowed_anthropic_response(
    payload: dict[str, Any],
    metadata: dict[str, Any],
    dictionary: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    annotated = annotate_anthropic_messages_response(payload, metadata, dictionary)
    guard = annotated["yizijue_gateway"]["tool_guard"]
    shadow_payload = shadow_rewrite_anthropic_inspect_tool_response(payload, metadata, guard)
    if shadow_payload is not None:
        return shadow_payload, 200
    if guard["allowed"]:
        return annotated, 200
    rewritten = deepcopy(payload)
    rewritten["content"] = [{"type": "text", "text": KERNEL_NOTICE_TEXT}]
    rewritten["stop_reason"] = "end_turn"
    rewritten["yizijue_gateway"] = {
        **metadata,
        "blocked": True,
        "response_mode": "soft_rewrite",
        "tool_guard": guard,
    }
    return rewritten, 200


def shadow_rewrite_anthropic_inspect_tool_response(
    payload: dict[str, Any],
    metadata: dict[str, Any],
    guard: dict[str, Any],
) -> dict[str, Any] | None:
    if str(metadata.get("root_opcode") or metadata.get("active_code")) != "查":
        return None
    tool_uses = [
        block
        for block in payload.get("content", [])
        if isinstance(block, dict) and block.get("type") == "tool_use"
    ]
    if not tool_uses:
        return None
    names = {str(block.get("name", "")) for block in tool_uses}
    if not names or not names <= SHADOW_INSPECT_TOOL_NAMES:
        return None
    text = _native_inspect_text_for_metadata(metadata)
    rewritten = deepcopy(payload)
    rewritten["content"] = [{"type": "text", "text": text}]
    rewritten["stop_reason"] = "end_turn"
    rewritten["yizijue_gateway"] = {
        **metadata,
        "response_mode": "shadow_native_inspect",
        "tool_guard": guard,
        "shadow_tool_mapping": {
            "applied": True,
            "source_tools": sorted(names),
            "target_tool": "native_inspect_card",
        },
    }
    return rewritten


def _native_inspect_text_for_metadata(metadata: dict[str, Any]) -> str:
    workspace = metadata.get("workspace") or metadata.get("workspace_root")
    if isinstance(workspace, str) and workspace:
        try:
            return build_native_inspect_card(workspace, max_chars=1200)["text"]
        except (OSError, ValueError):
            return NATIVE_INSPECT_FALLBACK_TEXT
    return NATIVE_INSPECT_FALLBACK_TEXT


def inject_native_inspect_context(payload: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    if str(metadata.get("root_opcode") or metadata.get("active_code")) != "查":
        return payload
    shadow = metadata.get("shadow_tool_injection", {})
    if not bool(shadow.get("applied")):
        return payload
    injected = deepcopy(payload)
    native_card = _native_inspect_text_for_metadata(metadata)
    context_block = "\n".join(
        [
            "Native Inspect Context:",
            native_card,
            "Use this read-only evidence as the inspected project context.",
            "The system has already performed the physical read. Return the final answer directly.",
            "Do not call local tools, do not request more reads, and do not emit XML/function call syntax such as <function_calls> or <invoke>.",
        ]
    )
    injected["system"] = _merge_anthropic_system(context_block, injected.get("system"))
    injected["tools"] = []
    metadata["native_context_injection"] = {
        "applied": True,
        "chars": len(native_card),
        "source": "native_inspect_card",
    }
    return injected


def annotate_anthropic_messages_response(
    payload: dict[str, Any],
    metadata: dict[str, Any],
    dictionary: dict[str, Any],
) -> dict[str, Any]:
    active_entry = lookup_entry(dictionary, metadata["active_code"])
    tool_calls = extract_anthropic_tool_uses(payload)
    decision = inspect_tool_calls(active_entry, tool_calls)
    annotated = deepcopy(payload)
    annotated["yizijue_gateway"] = {
        **metadata,
        "tool_guard": {
            "allowed": decision.allowed,
            "violations": decision.violations,
            "inspected_tool_calls": len(tool_calls),
        },
    }
    if not decision.allowed:
        annotated["yizijue_gateway"]["blocked"] = True
    return annotated


def should_halt_model_forwarding(metadata: dict[str, Any]) -> bool:
    kernel_policy = metadata.get("kernel_policy", {})
    return bool(kernel_policy.get("halt_model_forwarding"))


def stream_not_supported_response(metadata: dict[str, Any]) -> tuple[dict[str, Any], int]:
    return (
        {
            "error": {
                "type": "yizijue_stream_not_supported",
                "message": "Streaming chat completions are not supported by this 一字诀 gateway yet. Retry with stream=false.",
            },
            "yizijue_gateway": {
                **metadata,
                "blocked": True,
            },
        },
        400,
    )


def build_stream_tool_block_response(
    metadata: dict[str, Any],
    violation: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    return (
        {
            "choices": [{"delta": {"content": KERNEL_NOTICE_TEXT}, "finish_reason": "stop"}],
            "yizijue_gateway": {
                **metadata,
                "blocked": True,
                "response_mode": "soft_rewrite",
                "stream_guard": {
                    "allowed": False,
                    "violation": violation,
                },
            },
        },
        200,
    )


def extract_tool_calls(payload: dict[str, Any]) -> list[dict[str, Any]]:
    tool_calls: list[dict[str, Any]] = []
    for choice in payload.get("choices", []):
        message = choice.get("message", {})
        for call in message.get("tool_calls", []) or []:
            function = call.get("function", {})
            tool_calls.append(
                {
                    "name": function.get("name") or call.get("name", ""),
                    "arguments": function.get("arguments") or call.get("arguments", {}),
                }
            )
    return tool_calls


def extract_anthropic_tool_uses(payload: dict[str, Any]) -> list[dict[str, Any]]:
    tool_calls: list[dict[str, Any]] = []
    content = payload.get("content", [])
    if not isinstance(content, list):
        return tool_calls
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        tool_calls.append(
            {
                "name": block.get("name", ""),
                "arguments": block.get("input", {}),
            }
        )
    return tool_calls


def build_system_instruction(
    entry: dict[str, Any],
    codes: list[str],
    stack: list[str],
    root_entry: dict[str, Any] | None = None,
    kernel_policy: Any | None = None,
) -> str:
    root = root_entry or entry
    policy = kernel_policy or get_kernel_policy(root["code"])
    workflow_excerpt = load_workflow_excerpt(root["code"])
    skill_mount_excerpt = load_skill_mount_excerpt(entry["code"], root["code"])
    return "\n".join(
        [
            "一字诀网关已接管本次请求。",
            f"执行字: {entry['code']}",
            f"定义: {entry['definition']}",
            f"根字 Opcode: {root['code']}",
            f"根字定义: {root['definition']}",
            f"根字 Workflow 摘要:\n{workflow_excerpt}",
            f"根字 Skill Mount 摘要:\n{skill_mount_excerpt}",
            format_kernel_rule(policy),
            f"三维控制向量: {entry.get('opcode_vector', {})}",
            f"六步工作流: {' -> '.join(entry.get('six_phase_workflow', []))}",
            f"状态转移策略: {entry.get('transition_policy', {})}",
            f"识别序列: {' + '.join(codes)}",
            f"指令堆栈: {stack}",
            f"路由目标: {entry['routing_target']}",
            f"允许动作: {', '.join(entry['allowed_actions'])}",
            f"禁止动作: {', '.join(entry['forbidden_actions'])}",
            f"参考工作流模式: {', '.join(entry.get('reference_workflow_patterns', []))}",
            f"专业运行逻辑: {_format_protocol(entry.get('professional_protocol', {}))}",
            f"工具权限: {entry['tool_policy']}",
            f"验证要求: {entry['verification']}",
            f"失败回退: {entry['fallback']}",
            "必须遵守该执行字的权限、上下文和验证规则；不得声明未由系统层证据支持的结果。",
        ]
    )


def should_use_zero_tool_fast_path(active_code: str, root_code: str, body: dict[str, Any]) -> bool:
    policy = get_kernel_policy(root_code)
    route = determine_hexagram_route(active_code, root_code, policy, body, [active_code])
    return route_allows_zero_tool_fast_path(active_code, route)


def determine_hexagram_route(
    active_code: str,
    root_code: str,
    kernel_policy: Any,
    body: dict[str, Any],
    codes: list[str] | None = None,
) -> dict[str, Any]:
    normalized_codes = codes or [active_code]
    requirements = compile_tool_requirements(active_code, root_code, body, normalized_codes)
    outer_trigram = compile_outer_trigram_for_codes(normalized_codes, requirements)
    route = HexagramRouter.determine_skill_mount(kernel_policy.binary_trigram, outer_trigram)
    return {
        **route,
        "requirements": requirements,
    }


def route_allows_zero_tool_fast_path(active_code: str, route: dict[str, Any]) -> bool:
    return active_code in ZERO_TOOL_FAST_PATH_CODES and route["action"] in ZERO_TOOL_ACTIONS


def compile_outer_trigram_for_codes(codes: list[str], requirements: dict[str, bool]) -> str:
    if "修" in codes and "测" in codes:
        return "011"
    return HexagramRouter.compile_outer_trigram(requirements)


def compile_tool_requirements(
    active_code: str,
    root_code: str,
    body: dict[str, Any],
    codes: list[str],
) -> dict[str, bool]:
    if active_code in ZERO_TOOL_FAST_PATH_CODES and root_code in {"查", "问"} and not bool(body.get("stream")):
        return {"write": False, "network": False, "execute": False}
    return {
        "write": root_code in {"修", "记"} or any(code in {"修", "改", "造", "记"} for code in codes),
        "network": root_code in {"卫", "搜"} or any(code in {"卫", "源", "搜"} for code in codes),
        "execute": root_code in {"测", "卫"} or any(code in {"测", "卫"} for code in codes),
    }


def build_lightweight_system_instruction(
    entry: dict[str, Any],
    codes: list[str],
    stack: list[str],
    root_entry: dict[str, Any] | None = None,
    kernel_policy: Any | None = None,
) -> str:
    root = root_entry or entry
    policy = kernel_policy or get_kernel_policy(root["code"])
    return "\n".join(
        [
            "一字诀网关已接管本次请求。",
            "轻量零工具模式: 本轮不下放任何工具，禁止声明已读取、已修改或已验证外部文件。",
            f"执行字: {entry['code']}",
            f"根字 Opcode: {root['code']}",
            f"二进制爻象: {policy.binary_trigram}",
            f"控制偏置: {policy.control_bias}",
            f"工具权限锁: NONE",
            f"禁止动作: {', '.join(entry['forbidden_actions'])}",
            f"识别序列: {' + '.join(codes)}",
            f"指令堆栈: {stack}",
            "[Output-Constraint]: Reply in Chinese. Max 120 Chinese words. Concise only.",
            "只回答当前问题；事实、推断和不确定项必须分开；需要文件证据时转入查而不是伪造证据。",
        ]
    )


def _format_protocol(protocol: dict[str, Any]) -> str:
    source_projects = protocol.get("source_projects", [])
    operating_logic = protocol.get("operating_logic", [])
    hard_gates = protocol.get("hard_gates", [])
    return " | ".join(
        [
            f"来源: {', '.join(source_projects)}",
            f"步骤: {'; '.join(operating_logic)}",
            f"硬门: {'; '.join(hard_gates)}",
        ]
    )


def _explicit_code(message: str, known_codes: set[str]) -> str | None:
    if len(message) >= 2 and message[0] in known_codes and message[1] in {":", "："}:
        return message[0]
    return None


def _latest_user_message(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            content = message.get("content", "")
            if isinstance(content, str):
                return content
            return str(content)
    return ""


def _latest_anthropic_user_message(messages: Any) -> str:
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        return _anthropic_content_to_text(message.get("content", ""))
    return ""


def _anthropic_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(part for part in parts if part)
    return str(content)


def _merge_anthropic_system(system_instruction: str, existing_system: Any) -> str | list[dict[str, Any]]:
    if not existing_system:
        return system_instruction
    if isinstance(existing_system, str):
        return f"{system_instruction}\n\n上游原始 system:\n{existing_system}"
    if isinstance(existing_system, list):
        return [{"type": "text", "text": system_instruction}, *existing_system]
    return f"{system_instruction}\n\n上游原始 system:\n{existing_system}"


def _filter_anthropic_tools(tools: list[dict[str, Any]], kernel_policy: Any) -> list[dict[str, Any]]:
    allowed = set(kernel_policy.allowed_tools)
    filtered: list[dict[str, Any]] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        if str(tool.get("name", "")) in allowed:
            filtered.append(tool)
    return filtered


def _prefer_native_inspect_chat_tools(tools: list[dict[str, Any]], root_code: str) -> list[dict[str, Any]]:
    if root_code != "查":
        return tools
    native = [
        tool
        for tool in tools
        if isinstance(tool.get("function"), dict)
        and tool["function"].get("name") == "native_inspect_card"
    ]
    return native or tools


def _prefer_native_inspect_anthropic_tools(tools: list[dict[str, Any]], root_code: str) -> list[dict[str, Any]]:
    if root_code != "查":
        return tools
    native = [tool for tool in tools if str(tool.get("name", "")) == NATIVE_INSPECT_TOOL_NAME]
    return native or tools


def _rewrite_anthropic_inspect_tools(
    tools: list[dict[str, Any]],
    kernel_policy: Any,
    root_code: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    filtered = _filter_anthropic_tools(tools, kernel_policy)
    injection = {"applied": False, "source_tools": [], "target_tool": None}
    if root_code != "查":
        return filtered, injection
    native = _prefer_native_inspect_anthropic_tools(filtered, root_code)
    if native:
        return native, injection
    source_tools = sorted(
        {
            str(tool.get("name", ""))
            for tool in tools
            if isinstance(tool, dict) and str(tool.get("name", "")) in CLAUDE_INSPECT_TOOL_NAMES
        }
    )
    if not source_tools:
        return filtered, injection
    return [_native_inspect_anthropic_tool_schema()], {
        "applied": True,
        "source_tools": source_tools,
        "target_tool": NATIVE_INSPECT_TOOL_NAME,
    }


def _native_inspect_anthropic_tool_schema() -> dict[str, Any]:
    return {
        "name": NATIVE_INSPECT_TOOL_NAME,
        "description": "Return a compact read-only 101-INSPECT repo card. No local file edits or shell execution.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Optional relative file or directory to inspect.",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum card characters.",
                },
            },
            "additionalProperties": False,
        },
    }


def _anthropic_tools_for_preflight(tools: Any) -> list[dict[str, Any]]:
    if not isinstance(tools, list):
        return []
    return [
        {"type": "function", "function": {"name": str(tool.get("name", ""))}}
        for tool in tools
        if isinstance(tool, dict) and tool.get("name")
    ]


def _dedupe(codes: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for code in codes:
        if code not in seen:
            result.append(code)
            seen.add(code)
    return result
