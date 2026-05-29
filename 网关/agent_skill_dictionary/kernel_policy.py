from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .trigram_contract import get_trigram_contract


ROOT_KERNEL_CODES = {"查", "修", "测", "卫", "停", "问", "记", "总"}


@dataclass(frozen=True)
class KernelPolicy:
    code: str
    hexagram: str
    binary_trigram: str
    yin_yang_profile: str
    control_bias: str
    physical_control_flows: dict[str, str]
    name: str
    allowed_tools: tuple[str, ...]
    blocked_tools: tuple[str, ...]
    model_overrides: dict[str, Any]
    system_prompt: str
    evidence_required: tuple[str, ...]
    halt_model_forwarding: bool = False


@dataclass(frozen=True)
class EvidenceDecision:
    allowed: bool
    missing_fields: list[str]


KERNEL_POLICIES: dict[str, KernelPolicy] = {
    "查": KernelPolicy(
        code="查",
        hexagram="离",
        binary_trigram="101",
        yin_yang_profile="两阳夹一阴",
        control_bias="READ_ONLY_INSPECT",
        physical_control_flows={
            "model_forward": "allowed",
            "source_write": "forbidden",
            "tool_execution": "read_only",
        },
        name="inspect",
        allowed_tools=("native_inspect_card", "read_file", "list_directory", "grep_code", "git_diff"),
        blocked_tools=("write_file", "edit_file", "execute_command", "install_dependency"),
        model_overrides={"temperature": 0.0},
        system_prompt=(
            "你当前处于绝对只读模式。唯一任务是收集上下文、梳理依赖、定位可疑行号。"
            "严禁修改代码，严禁猜测未读文件内容；输出必须基于物理读取到的真实文本。"
        ),
        evidence_required=("Target_Files_List", "Line_Numbers", "Log_Context_Snippets"),
    ),
    "修": KernelPolicy(
        code="修",
        hexagram="震",
        binary_trigram="100",
        yin_yang_profile="两阴一阳",
        control_bias="SURGICAL_ACTION_PATCH",
        physical_control_flows={
            "model_forward": "allowed",
            "source_write": "scoped",
            "tool_execution": "edit_scoped_only",
        },
        name="fix",
        allowed_tools=("read_file", "edit_scoped_file", "create_new_file"),
        blocked_tools=("install_dependency", "rm_rf", "delete_file", "git_reset_hard"),
        model_overrides={"temperature": 0.0},
        system_prompt=(
            "你现在是外科手术式 Debug 专家。严格基于报错日志分析根因；"
            "只能在受影响代码块内做最小必要修改；严禁大面积重写无关函数或周边逻辑。"
        ),
        evidence_required=("Git_Diff_Patch", "Modified_Line_Numbers", "Fix_Logic_Explanation"),
    ),
    "测": KernelPolicy(
        code="测",
        hexagram="巽",
        binary_trigram="011",
        yin_yang_profile="一阴两阳",
        control_bias="SANDBOX_EXECUTE_VERIFY",
        physical_control_flows={
            "model_forward": "restricted",
            "source_write": "forbidden",
            "tool_execution": "sandbox_execute",
        },
        name="verify",
        allowed_tools=("run_pytest", "run_npm_test", "capture_coverage"),
        blocked_tools=("write_file", "edit_file", "install_dependency", "delete_file"),
        model_overrides={"temperature": 0.0},
        system_prompt=(
            "你现在是极度苛刻的自动化测试机。必须运行或生成对应验证；"
            "覆盖正常边界值、极端空值和异常捕获。证据不足或覆盖率不足必须如实报告失败。"
        ),
        evidence_required=("Test_Stdout_Log", "Coverage_Percentage", "Exit_Code"),
    ),
    "卫": KernelPolicy(
        code="卫",
        hexagram="坎",
        binary_trigram="010",
        yin_yang_profile="两阴夹一阳",
        control_bias="SECURITY_FILTER_ISOLATION",
        physical_control_flows={
            "model_forward": "restricted",
            "source_write": "forbidden",
            "tool_execution": "security_scan_only",
        },
        name="guard",
        allowed_tools=("dependency_security_scan", "ast_vulnerability_check"),
        blocked_tools=("execute_command", "install_dependency", "network_request", "write_file"),
        model_overrides={"temperature": 0.0},
        system_prompt=(
            "你现在是最高合规风险卫士。检查高危命令、注入漏洞、供应链风险和许可证冲突；"
            "只要发现可疑风险，先阻断并输出证据，严禁无证据放行。"
        ),
        evidence_required=("Security_Audit_Report", "Risk_Level", "Blocked_Evidence"),
    ),
    "停": KernelPolicy(
        code="停",
        hexagram="艮",
        binary_trigram="001",
        yin_yang_profile="两阴一阳",
        control_bias="SYSTEM_HARD_HALT",
        physical_control_flows={
            "model_forward": "blocked",
            "source_write": "forbidden",
            "tool_execution": "blocked",
        },
        name="halt",
        allowed_tools=(),
        blocked_tools=("*",),
        model_overrides={"temperature": 0.0},
        system_prompt=(
            "系统进入硬熔断状态。由于连续失败或安全越界，自动化流水线已挂起；"
            "等待人类确认恢复、降级或终止。"
        ),
        evidence_required=("Memory_State_Dump", "Failure_Counter", "Activation_Token_Status"),
        halt_model_forwarding=True,
    ),
    "问": KernelPolicy(
        code="问",
        hexagram="兑",
        binary_trigram="110",
        yin_yang_profile="一阴两阳",
        control_bias="HUMAN_INTERACTION_PROMPT",
        physical_control_flows={
            "model_forward": "allowed",
            "source_write": "forbidden",
            "tool_execution": "human_prompt_only",
        },
        name="prompt",
        allowed_tools=("send_user_message", "render_ui_options"),
        blocked_tools=("write_file", "edit_file", "execute_command", "install_dependency"),
        model_overrides={"temperature": 0.2},
        system_prompt=(
            "你遇到了无法确定的歧义。禁止擅自猜测；"
            "请把矛盾点或风险点梳理成极简、客观、温和的选择题，等待人类选择。"
        ),
        evidence_required=("JSON_Choice_Prompt",),
    ),
    "记": KernelPolicy(
        code="记",
        hexagram="坤",
        binary_trigram="000",
        yin_yang_profile="纯阴之卦",
        control_bias="SYSTEM_STRONG_WRITE",
        physical_control_flows={
            "model_forward": "restricted",
            "source_write": "forbidden",
            "tool_execution": "storage_only",
        },
        name="store",
        allowed_tools=("append_knowledge_base", "write_markdown_doc", "git_commit"),
        blocked_tools=("edit_source_code", "deploy", "execute_command", "install_dependency"),
        model_overrides={"temperature": 0.0},
        system_prompt=(
            "你现在是系统史官。只记录成功闭环后的事实、决策依据和稳定规则；"
            "以克制 Markdown 写入指定知识库，严禁触碰生产环境和业务源码。"
        ),
        evidence_required=("Stored_File_Path", "SHA256"),
    ),
    "总": KernelPolicy(
        code="总",
        hexagram="乾",
        binary_trigram="111",
        yin_yang_profile="纯阳之卦",
        control_bias="CONTEXT_COMPRESS_SUMMARIZE",
        physical_control_flows={
            "model_forward": "allowed",
            "source_write": "forbidden",
            "tool_execution": "context_only",
        },
        name="summarize",
        allowed_tools=("compress_tokens",),
        blocked_tools=("write_file", "edit_file", "execute_command", "install_dependency"),
        model_overrides={"temperature": 0.0},
        system_prompt=(
            "你现在是上下文收束内核。只压缩事实、证据、风险和下一步；"
            "禁止把计划写成已完成，禁止丢弃阻塞项或失败证据。"
        ),
        evidence_required=("Summary_Markdown", "Open_Risk_List", "Next_Opcode_Recommendation"),
    ),
}


def get_kernel_policy(root_code: str) -> KernelPolicy:
    try:
        return KERNEL_POLICIES[root_code]
    except KeyError as exc:
        raise KeyError(f"Unknown root kernel code: {root_code}") from exc


def filter_allowed_tools(tools: list[dict[str, Any]], policy: KernelPolicy) -> list[dict[str, Any]]:
    allowed = set(policy.allowed_tools)
    filtered: list[dict[str, Any]] = []
    for tool in tools:
        name = _tool_name(tool)
        if name in allowed:
            filtered.append(tool)
    return filtered


def verify_evidence_chain(policy: KernelPolicy, evidence: dict[str, Any]) -> EvidenceDecision:
    missing = [field for field in policy.evidence_required if field not in evidence]
    return EvidenceDecision(allowed=not missing, missing_fields=missing)


def kernel_policy_metadata(policy: KernelPolicy) -> dict[str, Any]:
    return {
        "code": policy.code,
        "hexagram": policy.hexagram,
        "binary_trigram": policy.binary_trigram,
        "yin_yang_profile": policy.yin_yang_profile,
        "control_bias": policy.control_bias,
        "physical_control_flows": dict(policy.physical_control_flows),
        "name": policy.name,
        "allowed_tools": list(policy.allowed_tools),
        "blocked_tools": list(policy.blocked_tools),
        "evidence_required": list(policy.evidence_required),
        "halt_model_forwarding": policy.halt_model_forwarding,
    }


def format_kernel_rule(policy: KernelPolicy) -> str:
    return "\n".join(
        [
            "内核运行规训:",
            f"卦象: {policy.hexagram}",
            f"二进制爻象: {policy.binary_trigram}",
            f"阴阳结构: {policy.yin_yang_profile}",
            f"控制偏置: {policy.control_bias}",
            f"物理控制流: {policy.physical_control_flows}",
            f"工具权限锁: {', '.join(policy.allowed_tools) if policy.allowed_tools else 'NONE'}",
            f"危险拦截: {', '.join(policy.blocked_tools)}",
            f"模型参数锁: {policy.model_overrides}",
            f"内核行为规训: {policy.system_prompt}",
            f"原子证据链: {', '.join(policy.evidence_required)}",
        ]
    )


for _code, _policy in KERNEL_POLICIES.items():
    _contract = get_trigram_contract(_code)
    assert _policy.hexagram == _contract["hexagram"]
    assert _policy.binary_trigram == _contract["binary_trigram"]
    assert _policy.yin_yang_profile == _contract["yin_yang_profile"]
    assert _policy.control_bias == _contract["control_bias"]
    assert _policy.physical_control_flows == _contract["physical_control_flows"]


def _tool_name(tool: dict[str, Any]) -> str:
    if "function" in tool and isinstance(tool["function"], dict):
        return str(tool["function"].get("name", ""))
    return str(tool.get("name", ""))
