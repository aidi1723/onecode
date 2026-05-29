from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .build_mode_orchestrator import (
    ArtifactGap,
    build_next_artifact_instruction,
    build_repair_gate_instruction,
    build_verify_gate_instruction,
)
from .build_mode_permissions import DEFAULT_PYTHON_TEST_COMMAND


@dataclass(frozen=True)
class BalanceSnapshot:
    total_gaps: int
    present_count: int
    allowed_tool_count: int
    allowed_tool_names: tuple[str, ...]
    yin_resistance: float
    yang_bandwidth: float
    mode: str
    violations: tuple[str, ...] = ()


@dataclass(frozen=True)
class EquilibriumDecision:
    hexagram: str
    source: str
    shadow_action: str
    instruction: str
    tool_name: str | None
    target_path: str | None = None
    metadata_key: str = ""
    metadata: dict[str, Any] | None = None
    force_empty_tools: bool = False
    balance: BalanceSnapshot | None = None


def decide_equilibrium(
    gap: ArtifactGap,
    state: dict[str, Any],
    *,
    repair_target_path: str | None = None,
    available_tools: list[dict[str, Any]] | None = None,
    command: str = DEFAULT_PYTHON_TEST_COMMAND,
) -> EquilibriumDecision:
    needs_repair = _latest_state_needs_repair(state)
    initial_balance = measure_balance(gap, available_tools or [], repair_allowed=needs_repair)
    if not gap.complete and gap.next_artifact is not None:
        tool_name = "write_file"
        balance = rebalance_snapshot(gap, (tool_name,), "incremental_create")
        return EquilibriumDecision(
            hexagram="111",
            source="artifact_continuation_gate",
            shadow_action="scoped_writer",
            instruction=build_next_artifact_instruction(gap),
            tool_name=tool_name,
            target_path=gap.next_artifact.path,
            metadata_key="build_mode_artifact_plan",
            metadata={
                "project_name": gap.plan.project_name,
                "next_path": gap.next_artifact.path,
                "present_paths": list(gap.present_paths),
                "missing_paths": list(gap.missing_paths),
                "initial_balance": balance_to_dict(initial_balance),
            },
            balance=balance,
        )

    if _latest_state_is_successful_return(state):
        balance = rebalance_snapshot(gap, (), "archive_lockdown")
        return EquilibriumDecision(
            hexagram="000",
            source="artifact_archive_gate",
            shadow_action="archive_lockdown",
            instruction=(
                "Build Mode Archive Gate:\n"
                "统一物理验证已经通过，当前轮次禁止继续写文件或运行命令。"
                "请只总结已固化资产与 Manifest 状态。"
            ),
            tool_name=None,
            metadata_key="build_mode_archive_gate",
            metadata={
                "complete": True,
                "project_name": gap.plan.project_name,
                "present_paths": list(gap.present_paths),
                "initial_balance": balance_to_dict(initial_balance),
            },
            force_empty_tools=True,
            balance=balance,
        )

    if needs_repair:
        tool_name = "write_file"
        balance = rebalance_snapshot(gap, (tool_name,), "repair_create")
        return EquilibriumDecision(
            hexagram="111",
            source="artifact_repair_gate",
            shadow_action="scoped_repair_writer",
            instruction=build_repair_gate_instruction(gap, target_path=repair_target_path),
            tool_name=tool_name,
            target_path=repair_target_path,
            metadata_key="build_mode_repair_gate",
            metadata={
                "complete": True,
                "project_name": gap.plan.project_name,
                "present_paths": list(gap.present_paths),
                "target_path": repair_target_path,
                "initial_balance": balance_to_dict(initial_balance),
            },
            balance=balance,
        )

    tool_name = "run_pytest"
    balance = rebalance_snapshot(gap, (tool_name,), "canonical_verify")
    return EquilibriumDecision(
        hexagram="001",
        source="artifact_verify_gate",
        shadow_action="canonical_tester",
        instruction=build_verify_gate_instruction(gap, command=command),
        tool_name=tool_name,
        metadata_key="build_mode_verify_gate",
        metadata={
            "complete": True,
            "project_name": gap.plan.project_name,
            "present_paths": list(gap.present_paths),
            "command": command,
            "initial_balance": balance_to_dict(initial_balance),
        },
        balance=balance,
    )


def measure_balance(
    gap: ArtifactGap,
    tools: list[dict[str, Any]],
    *,
    repair_allowed: bool = False,
) -> BalanceSnapshot:
    tool_names = tuple(name for name in (_tool_name(item) for item in tools) if name)
    total_gaps = len(gap.missing_paths)
    yin_resistance = 1.0 if total_gaps == 0 else min(1.0, total_gaps / max(1, len(gap.plan.artifacts)))
    yang_bandwidth = min(1.0, len(tool_names) / 3)
    violations: list[str] = []
    if total_gaps > 0 and "write_file" not in tool_names:
        violations.append("gap_without_write_channel")
    if total_gaps == 0 and not tool_names:
        violations.append("complete_plan_without_exit_or_verify_channel")
    if len(tool_names) > 3:
        violations.append("tool_overexposure")
    if (
        total_gaps == 0
        and not repair_allowed
        and any(name in {"write_file", "apply_patch", "patch"} for name in tool_names)
    ):
        violations.append("write_channel_after_gap_zero")
    return BalanceSnapshot(
        total_gaps=total_gaps,
        present_count=len(gap.present_paths),
        allowed_tool_count=len(tool_names),
        allowed_tool_names=tool_names,
        yin_resistance=yin_resistance,
        yang_bandwidth=yang_bandwidth,
        mode="observed",
        violations=tuple(violations),
    )


def rebalance_snapshot(gap: ArtifactGap, tool_names: tuple[str, ...], mode: str) -> BalanceSnapshot:
    total_gaps = len(gap.missing_paths)
    yin_resistance = 1.0 if total_gaps == 0 else min(1.0, total_gaps / max(1, len(gap.plan.artifacts)))
    yang_bandwidth = min(1.0, len(tool_names) / 3)
    return BalanceSnapshot(
        total_gaps=total_gaps,
        present_count=len(gap.present_paths),
        allowed_tool_count=len(tool_names),
        allowed_tool_names=tool_names,
        yin_resistance=yin_resistance,
        yang_bandwidth=yang_bandwidth,
        mode=mode,
        violations=(),
    )


def balance_to_dict(snapshot: BalanceSnapshot | None) -> dict[str, Any]:
    if snapshot is None:
        return {}
    return {
        "total_gaps": snapshot.total_gaps,
        "present_count": snapshot.present_count,
        "allowed_tool_count": snapshot.allowed_tool_count,
        "allowed_tool_names": list(snapshot.allowed_tool_names),
        "yin_resistance": snapshot.yin_resistance,
        "yang_bandwidth": snapshot.yang_bandwidth,
        "mode": snapshot.mode,
        "violations": list(snapshot.violations),
    }


def infer_repair_target_path(state: dict[str, Any], present_paths: tuple[str, ...]) -> str | None:
    haystack = _state_failure_text(state)
    if (
        "plaintext must be bytes" in haystack
        or "message must be bytes" in haystack
        or "test_encrypt" in haystack
        or "test_signature" in haystack
        or "test_wrong_key_decrypt_failure" in haystack
    ):
        if "core/crypto.py" in present_paths:
            return "core/crypto.py"
    if "SecureMeshServer" in haystack or "/stats" in haystack or "message_id" in haystack:
        if "api/server.py" in present_paths:
            return "api/server.py"
    for path in present_paths:
        if path in haystack:
            return path
    if "test_" in haystack and "tests/test_mesh.py" in present_paths:
        return "tests/test_mesh.py"
    return None


def _tool_name(item: dict[str, Any]) -> str:
    if "function" in item and isinstance(item["function"], dict):
        return str(item["function"].get("name") or "")
    if str(item.get("type") or "") == "function" and item.get("name"):
        return str(item.get("name") or "")
    return str(item.get("name") or "")


def _latest_state_needs_repair(state: dict[str, Any]) -> bool:
    results = state.get("results") if isinstance(state.get("results"), list) else []
    for result in reversed(results):
        if not isinstance(result, dict):
            continue
        if result.get("status") == "ok" and result.get("hexagram") == "111":
            return False
        if result.get("hexagram") == "001" and result.get("status") == "needs_fix":
            return True
        exit_code = result.get("exit_code")
        if result.get("hexagram") == "001" and isinstance(exit_code, int) and exit_code != 0:
            return True
        break
    failures = state.get("consecutive_failures")
    return isinstance(failures, int) and failures > 0


def _latest_state_is_successful_return(state: dict[str, Any]) -> bool:
    results = state.get("results") if isinstance(state.get("results"), list) else []
    for result in reversed(results):
        if not isinstance(result, dict):
            continue
        if result.get("hexagram") == "001" and result.get("status") == "completed":
            return True
        if result.get("hexagram") == "001" and result.get("next_hexagram") == "000":
            return True
        exit_code = result.get("exit_code")
        if result.get("hexagram") == "001" and exit_code == 0:
            return True
        break
    return False


def _state_failure_text(state: dict[str, Any]) -> str:
    parts: list[str] = []
    repair_card = state.get("repair_card")
    if isinstance(repair_card, str):
        parts.append(repair_card)
    results = state.get("results") if isinstance(state.get("results"), list) else []
    for result in results:
        if not isinstance(result, dict):
            continue
        summary = result.get("failure_summary")
        if isinstance(summary, str):
            parts.append(summary)
    return "\n".join(parts)
