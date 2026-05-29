from __future__ import annotations

from typing import Any


TRIGRAM_CONTRACTS: dict[str, dict[str, Any]] = {
    "记": {
        "hexagram": "坤",
        "binary_trigram": "000",
        "yin_yang_profile": "纯阴之卦",
        "control_bias": "SYSTEM_STRONG_WRITE",
        "physical_control_flows": {
            "model_forward": "restricted",
            "source_write": "forbidden",
            "tool_execution": "storage_only",
        },
    },
    "停": {
        "hexagram": "艮",
        "binary_trigram": "001",
        "yin_yang_profile": "两阴一阳",
        "control_bias": "SYSTEM_HARD_HALT",
        "physical_control_flows": {
            "model_forward": "blocked",
            "source_write": "forbidden",
            "tool_execution": "blocked",
        },
    },
    "卫": {
        "hexagram": "坎",
        "binary_trigram": "010",
        "yin_yang_profile": "两阴夹一阳",
        "control_bias": "SECURITY_FILTER_ISOLATION",
        "physical_control_flows": {
            "model_forward": "restricted",
            "source_write": "forbidden",
            "tool_execution": "security_scan_only",
        },
    },
    "测": {
        "hexagram": "巽",
        "binary_trigram": "011",
        "yin_yang_profile": "一阴两阳",
        "control_bias": "SANDBOX_EXECUTE_VERIFY",
        "physical_control_flows": {
            "model_forward": "restricted",
            "source_write": "forbidden",
            "tool_execution": "sandbox_execute",
        },
    },
    "修": {
        "hexagram": "震",
        "binary_trigram": "100",
        "yin_yang_profile": "两阴一阳",
        "control_bias": "SURGICAL_ACTION_PATCH",
        "physical_control_flows": {
            "model_forward": "allowed",
            "source_write": "scoped",
            "tool_execution": "edit_scoped_only",
        },
    },
    "查": {
        "hexagram": "离",
        "binary_trigram": "101",
        "yin_yang_profile": "两阳夹一阴",
        "control_bias": "READ_ONLY_INSPECT",
        "physical_control_flows": {
            "model_forward": "allowed",
            "source_write": "forbidden",
            "tool_execution": "read_only",
        },
    },
    "问": {
        "hexagram": "兑",
        "binary_trigram": "110",
        "yin_yang_profile": "一阴两阳",
        "control_bias": "HUMAN_INTERACTION_PROMPT",
        "physical_control_flows": {
            "model_forward": "allowed",
            "source_write": "forbidden",
            "tool_execution": "human_prompt_only",
        },
    },
    "总": {
        "hexagram": "乾",
        "binary_trigram": "111",
        "yin_yang_profile": "纯阳之卦",
        "control_bias": "CONTEXT_COMPRESS_SUMMARIZE",
        "physical_control_flows": {
            "model_forward": "allowed",
            "source_write": "forbidden",
            "tool_execution": "context_only",
        },
    },
}

_ROOT_BY_TRIGRAM = {
    contract["binary_trigram"]: code
    for code, contract in TRIGRAM_CONTRACTS.items()
}

_LIFECYCLE_PHASES: tuple[tuple[str, str], ...] = (
    ("发端", "捕获当前物理环境、用户意图和状态入口。"),
    ("见形", "解析静态上下文、作用域、工具边界和证据需求。"),
    ("危机", "在最小隔离面内复现风险、失败、歧义或上下文压力。"),
    ("抉择", "按当前根字权限执行最小必要动作或阻断。"),
    ("成效", "读取系统层证据，固化退出码、哈希、扫描结果或人类选择。"),
    ("终局", "依据硬证据触发变卦、归档、追问、熔断或上下文收束。"),
)

_ROOT_LIFECYCLE_EVIDENCE: dict[str, tuple[str, ...]] = {
    "查": (
        "Original_Input",
        "Repository_Map",
        "Read_Only_Code_Reasoning",
        "Grep_Verified_Text",
        "Target_File_Line_Range",
        "Inspect_Handoff",
    ),
    "修": (
        "Failure_Line_Context",
        "Minimal_Patch_Plan",
        "Scoped_Write",
        "AST_Interface_Check",
        "Git_Diff_Patch",
        "Source_Snapshot",
    ),
    "测": (
        "Patch_Test_Scope",
        "Docker_Test_Runner",
        "Exit_Code",
        "Coverage_Percentage",
        "Exit_Code_Nonzero",
        "Exit_Code_0_SHA256",
    ),
    "卫": (
        "Intercepted_Data_Flow",
        "OSV_Semgrep_Scan",
        "Risk_Rating",
        "Risk_High_Trigger",
        "Guard_Pass_Log",
        "Security_Audit_Report",
    ),
    "停": (
        "Context_Circuit_Breaker",
        "Agent_Thread_Suspended",
        "Kernel_Panic_Dump",
        "Memory_State_Dump",
        "Human_Unlock_Token",
        "Resume_Target_State",
    ),
    "问": (
        "Ambiguity_Source",
        "Human_Readable_Question",
        "JSON_Choice_Prompt",
        "Rendered_Options",
        "Human_Response_Block",
        "Human_Decision_Evidence",
    ),
    "记": (
        "Artifact_Summary",
        "Knowledge_Base_Path",
        "Markdown_Archive",
        "SHA256",
        "Git_Commit",
        "SUCCESS_CLOSE",
    ),
    "总": (
        "Session_History_Scan",
        "Core_State_Extraction",
        "Compressed_Context",
        "Context_Circuit_Breaker",
        "Clean_Context_Window",
        "Next_Opcode_Handoff",
    ),
}


def get_trigram_contract(code: str) -> dict[str, Any]:
    try:
        return TRIGRAM_CONTRACTS[code]
    except KeyError as exc:
        raise KeyError(f"Unknown trigram root code: {code}") from exc


def root_by_trigram(binary_trigram: str) -> str:
    _validate_binary_trigram(binary_trigram)
    try:
        return _ROOT_BY_TRIGRAM[binary_trigram]
    except KeyError as exc:
        raise KeyError(f"Unknown binary trigram: {binary_trigram}") from exc


def invert_trigram(binary_trigram: str) -> str:
    _validate_binary_trigram(binary_trigram)
    return "".join("1" if bit == "0" else "0" for bit in binary_trigram)


def reverse_trigram(binary_trigram: str) -> str:
    _validate_binary_trigram(binary_trigram)
    return binary_trigram[::-1]


def opposite_root(code: str) -> str:
    contract = get_trigram_contract(code)
    return root_by_trigram(invert_trigram(contract["binary_trigram"]))


def reverse_root(code: str) -> str:
    contract = get_trigram_contract(code)
    return root_by_trigram(reverse_trigram(contract["binary_trigram"]))


def get_trigram_relations(code: str) -> dict[str, str]:
    contract = get_trigram_contract(code)
    opposite = opposite_root(code)
    reversed_code = reverse_root(code)
    return {
        "opposite_root": opposite,
        "opposite_trigram": get_trigram_contract(opposite)["binary_trigram"],
        "reverse_root": reversed_code,
        "reverse_trigram": get_trigram_contract(reversed_code)["binary_trigram"],
    }


def get_lifecycle_steps(code: str) -> list[dict[str, Any]]:
    get_trigram_contract(code)
    evidence = _ROOT_LIFECYCLE_EVIDENCE[code]
    return [
        {
            "index": index,
            "phase": phase,
            "description": description,
            "evidence": evidence[index - 1],
        }
        for index, (phase, description) in enumerate(_LIFECYCLE_PHASES, start=1)
    ]


def derive_hidden_intent_locks(code: str, metadata: dict[str, Any]) -> list[str]:
    get_trigram_contract(code)
    requested_tools = {
        str(tool)
        for tool in metadata.get("requested_tools", [])
        if isinstance(tool, str)
    }
    message = str(metadata.get("message", "")).lower()
    risky_tools = {"network_request", "install_dependency", "execute_command", "rm_rf"}
    risky_markers = (
        "curl",
        "wget",
        "| sh",
        "rm -rf",
        "sudo",
        "chmod 777",
        "pip install",
        "npm install",
        "http://",
        "https://",
    )
    if any(marker in message for marker in risky_markers):
        return ["卫"]
    if code == "修" and requested_tools & risky_tools:
        return ["卫"]
    return []


def validate_trigram_contract(code: str, config: dict[str, Any]) -> list[str]:
    expected = get_trigram_contract(code)
    errors: list[str] = []
    for key in ("hexagram", "binary_trigram", "yin_yang_profile", "control_bias"):
        if config.get(key) != expected[key]:
            errors.append(f"{code}: {key} must be {expected[key]}")
    if config.get("physical_control_flows") != expected["physical_control_flows"]:
        errors.append(f"{code}: physical_control_flows must match trigram contract")

    tools = set(config.get("allowed_tools", []))
    halt_flag = bool(config.get("halt_model_forwarding"))
    temperature = config.get("temperature")
    flows = config.get("physical_control_flows", {})
    source_write = flows.get("source_write") if isinstance(flows, dict) else None

    if code == "记":
        if "edit_scoped_file" in tools or "run_pytest" in tools:
            errors.append("记: pure store must not expose edit or test execution tools")
        if list(config.get("allowed_tools", [])) != [
            "append_knowledge_base",
            "write_markdown_doc",
            "git_commit",
        ]:
            errors.append("记: allowed_tools must match final store contract")
        if temperature != 0.0:
            errors.append("记: temperature must be 0.0")
    elif code == "停":
        if not halt_flag:
            errors.append("停: halt_model_forwarding must be true")
        if tools:
            errors.append("停: allowed_tools must be empty")
    elif code == "查":
        if "edit_scoped_file" in tools or "create_new_file" in tools:
            errors.append("查: read-only inspect must not expose write tools")
        if source_write != "forbidden":
            errors.append("查: source_write must be forbidden")
    elif code == "卫":
        if "dependency_security_scan" not in tools:
            errors.append("卫: guard must expose dependency_security_scan")
        if list(config.get("allowed_tools", [])) != [
            "dependency_security_scan",
            "ast_vulnerability_check",
        ]:
            errors.append("卫: allowed_tools must match final guard contract")
    elif code == "测":
        if list(config.get("allowed_tools", [])) != [
            "run_pytest",
            "run_npm_test",
            "capture_coverage",
        ]:
            errors.append("测: allowed_tools must match final verify contract")
    elif code in {"问", "总", "测", "停", "记"}:
        if source_write != "forbidden":
            errors.append(f"{code}: source_write must be forbidden")
    elif code == "修":
        if source_write != "scoped":
            errors.append("修: source_write must be scoped")
        if list(config.get("allowed_tools", [])) != [
            "read_file",
            "edit_scoped_file",
            "create_new_file",
        ]:
            errors.append("修: allowed_tools must match final action contract")
    if code == "总" and list(config.get("allowed_tools", [])) != ["compress_tokens"]:
        errors.append("总: allowed_tools must match final context compression contract")
    try:
        get_trigram_relations(code)
        get_lifecycle_steps(code)
    except (KeyError, ValueError) as exc:
        errors.append(f"{code}: trigram runtime relation contract is invalid: {exc}")
    return errors


def _validate_binary_trigram(binary_trigram: str) -> None:
    if len(binary_trigram) != 3 or set(binary_trigram) - {"0", "1"}:
        raise ValueError(f"Invalid binary trigram: {binary_trigram}")
