from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .kernel_policy import get_kernel_policy


SUCCESS_STATES = {"记", "总"}
VERIFY_TOOLS = {"run_pytest", "run_npm_test", "capture_coverage"}
SUMMARY_REQUIRED_FIELDS = ("implemented_patch_sha256", "remaining_risk")
TOOL_REQUIREMENT_BITS = ("write", "network", "execute")


@dataclass
class KernelContractError(AssertionError):
    reason: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return f"{self.reason}: {self.details}"


class HexagramRouter:
    """
    Deterministic six-line router.

    inner_trigram is the locked root kernel state; outer_trigram is compiled from
    runtime tool requirements in write/network/execute order.
    """

    ROUTING_MATRIX: dict[str, dict[str, Any]] = {
        "000101": {
            "action": "ZERO_TOOL_BYPASS",
            "allowed_skills": [],
            "force_tools": [],
            "hexagram_name": "地火明夷",
        },
        "000110": {
            "action": "ZERO_TOOL_CLARIFY",
            "allowed_skills": [],
            "force_tools": [],
            "hexagram_name": "地泽临",
        },
        "011010": {
            "action": "LAUNCH_PHYSICAL_GUARD",
            "allowed_skills": ["osv_scanner_scan", "semgrep_audit"],
            "force_tools": ["run_security_scan"],
            "hexagram_name": "风水涣",
        },
        "011100": {
            "action": "LAUNCH_ISOLATED_SANDBOX",
            "allowed_skills": ["docker_pytest_verify", "surgical_patch_apply"],
            "force_tools": ["run_pytest_in_sandbox", "edit_scoped_file"],
            "hexagram_name": "风雷益",
        },
    }

    DEFAULT_ROUTE: dict[str, Any] = {
        "action": "FORCE_HALT_TO_HUMAN",
        "allowed_skills": [],
        "force_tools": [],
        "hexagram_name": "unknown",
    }

    @staticmethod
    def determine_skill_mount(inner_trigram: str, outer_trigram: str) -> dict[str, Any]:
        hexagram_code = f"{outer_trigram}{inner_trigram}"
        route = HexagramRouter.ROUTING_MATRIX.get(hexagram_code, HexagramRouter.DEFAULT_ROUTE)
        return {
            "hexagram_code": hexagram_code,
            "inner_trigram": inner_trigram,
            "outer_trigram": outer_trigram,
            **route,
        }

    @staticmethod
    def compile_outer_trigram(requirements: dict[str, Any]) -> str:
        return "".join("1" if requirements.get(bit) else "0" for bit in TOOL_REQUIREMENT_BITS)


def assert_runtime_contract(
    active_opcode: str,
    model_request: dict[str, Any],
    sandbox_response: dict[str, Any],
) -> None:
    _assert_preflight_contract(
        active_opcode,
        model_request,
        tool_not_allowed_reason="tool_not_allowed",
    )
    _assert_postflight_contract(
        active_opcode,
        sandbox_response,
        invalid_failure_route_reason="invalid_failure_route",
    )


def assert_preflight_contract(active_opcode: str, model_request: dict[str, Any]) -> None:
    _assert_preflight_contract(
        active_opcode,
        model_request,
        tool_not_allowed_reason="preflight_tool_not_allowed",
    )


def assert_postflight_contract(active_opcode: str, sandbox_response: dict[str, Any]) -> None:
    _assert_postflight_contract(
        active_opcode,
        sandbox_response,
        invalid_failure_route_reason="postflight_invalid_failure_route",
    )


def _assert_preflight_contract(
    active_opcode: str,
    model_request: dict[str, Any],
    tool_not_allowed_reason: str,
) -> None:
    policy = get_kernel_policy(active_opcode)
    tool_names = _tool_names(model_request.get("tools", []))
    if active_opcode == "测" and not (set(tool_names) & VERIFY_TOOLS):
        raise KernelContractError(
            "required_tool_missing",
            {
                "active_opcode": active_opcode,
                "required_any": sorted(VERIFY_TOOLS),
                "tools": tool_names,
            },
        )

    disallowed = sorted(set(tool_names) - set(policy.allowed_tools))
    if disallowed:
        raise KernelContractError(
            tool_not_allowed_reason,
            {
                "active_opcode": active_opcode,
                "disallowed_tools": disallowed,
                "allowed_tools": list(policy.allowed_tools),
            },
        )


def _assert_postflight_contract(
    active_opcode: str,
    sandbox_response: dict[str, Any],
    invalid_failure_route_reason: str,
) -> None:
    exit_code = sandbox_response.get("exit_code")
    next_suggested_state = sandbox_response.get("next_suggested_state")
    if exit_code not in (None, 0) and next_suggested_state in SUCCESS_STATES:
        raise KernelContractError(
            invalid_failure_route_reason,
            {
                "active_opcode": active_opcode,
                "exit_code": exit_code,
                "next_suggested_state": next_suggested_state,
            },
        )


def validate_summary_contract(summary_payload: Any) -> dict[str, Any]:
    if not isinstance(summary_payload, dict):
        raise KernelContractError(
            "summary_contract_invalid_type",
            {"expected": "object", "actual": type(summary_payload).__name__},
        )

    missing = [field for field in SUMMARY_REQUIRED_FIELDS if not summary_payload.get(field)]
    if missing:
        raise KernelContractError(
            "summary_contract_missing_fields",
            {
                "missing_fields": missing,
                "required_fields": list(SUMMARY_REQUIRED_FIELDS),
            },
        )

    patch_sha = str(summary_payload["implemented_patch_sha256"])
    if not re_fullmatch_sha256(patch_sha):
        raise KernelContractError(
            "summary_contract_invalid_patch_sha256",
            {"implemented_patch_sha256": patch_sha},
        )

    return dict(summary_payload)


def re_fullmatch_sha256(value: str) -> bool:
    if len(value) != 64:
        return False
    return all(char in "0123456789abcdefABCDEF" for char in value)


def _tool_names(tools: Any) -> list[str]:
    if not isinstance(tools, list):
        return []
    names: list[str] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        if isinstance(tool.get("function"), dict):
            name = tool["function"].get("name")
        else:
            name = tool.get("name")
        if name:
            names.append(str(name))
    return names
