from __future__ import annotations

from typing import Any

from .kernel_policy import ROOT_KERNEL_CODES, get_kernel_policy
from .trigram_contract import get_lifecycle_steps, get_trigram_relations


def build_agent_protocol_manifest() -> dict[str, Any]:
    return {
        "name": "oneword-agent-control-protocol",
        "version": "1.0.0",
        "compatibility": "agent-agnostic",
        "description": (
            "A transport-neutral control-plane contract for connecting any Agent "
            "to OneWord AgentOS runtime constraints."
        ),
        "required_agent_loop": [
            "resolve",
            "preflight_tool",
            "execute_allowed_tool",
            "submit_evidence",
            "respect_halt_or_human_prompt",
        ],
        "reference_adapter": {
            "module": "agent_skill_dictionary.reference_agent_adapter",
            "cli": "python3 -m agent_skill_dictionary.reference_agent_adapter",
            "purpose": (
                "A deterministic external-Agent harness that demonstrates the required "
                "resolve -> preflight -> execute -> submit-evidence loop."
            ),
        },
        "endpoints": [
            {
                "method": "GET",
                "path": "/v1/yizijue/protocol",
                "purpose": "Return this integration contract without invoking a model.",
            },
            {
                "method": "POST",
                "path": "/v1/yizijue/resolve",
                "purpose": "Compile user input into an active OneWord opcode and execution metadata.",
                "request": {"input": "string"},
                "response_keys": [
                    "active_code",
                    "root_opcode",
                    "allowed_tools",
                    "evidence_required",
                    "binary_trigram",
                ],
            },
            {
                "method": "POST",
                "path": "/v1/yizijue/preflight-tool",
                "purpose": "Authorize or deny a tool call before any Agent executes it.",
                "request": {
                    "active_code": "string",
                    "tool_name": "string",
                    "arguments": "object",
                },
                "response_keys": ["allowed", "violations", "kernel_policy"],
            },
            {
                "method": "POST",
                "path": "/v1/yizijue/submit-evidence",
                "purpose": "Append system-observed external Agent evidence to the immutable audit chain.",
                "request": {
                    "workspace": "path",
                    "command": "string",
                    "exit_code": "integer",
                    "stdout": "string",
                    "stderr": "string",
                },
                "response_keys": ["status", "audit_log_path", "evidence"],
            },
            {
                "method": "POST",
                "path": "/v1/yizijue/run",
                "purpose": "Run the local OneWord-Agent finite-state-machine executor.",
                "request": {"input": "string", "workspace": "path"},
                "response_keys": ["status", "trace", "audit_log_path", "artifacts"],
            },
            {
                "method": "POST",
                "path": "/v1/chat/completions",
                "purpose": "OpenAI-compatible proxy path for Agents that can change base URL.",
            },
        ],
        "statuses": {
            "completed": "Task finished with system evidence.",
            "halted": "Hard halt. The Agent must stop until a human unlock path is provided.",
            "waiting_for_human": "The Agent must surface a structured human choice and wait.",
            "max_steps_exceeded": "FSM safety ceiling was reached.",
        },
        "evidence_contract": {
            "source": "system_only",
            "audit_log_write_access": "system_only",
            "audit_fields": [
                "timestamp",
                "command",
                "exit_code",
                "stdout_digest",
                "stderr_digest",
                "sha256",
                "previous_sha256",
            ],
            "completion_claim_rule": "No Agent may claim completion without system evidence.",
        },
        "root_opcodes": _root_opcode_contracts(),
    }


def _root_opcode_contracts() -> dict[str, dict[str, Any]]:
    contracts: dict[str, dict[str, Any]] = {}
    for code in sorted(ROOT_KERNEL_CODES, key=_root_sort_key):
        policy = get_kernel_policy(code)
        relations = get_trigram_relations(code)
        contracts[code] = {
            "hexagram": policy.hexagram,
            "binary_trigram": policy.binary_trigram,
            "yin_yang_profile": policy.yin_yang_profile,
            "control_bias": policy.control_bias,
            "physical_control_flows": dict(policy.physical_control_flows),
            "allowed_tools": list(policy.allowed_tools),
            "blocked_tools": list(policy.blocked_tools),
            "evidence_required": list(policy.evidence_required),
            "halt_model_forwarding": policy.halt_model_forwarding,
            "opposite_root": relations["opposite_root"],
            "reverse_root": relations["reverse_root"],
            "lifecycle_steps": get_lifecycle_steps(code),
        }
    return contracts


def _root_sort_key(code: str) -> str:
    return get_kernel_policy(code).binary_trigram
