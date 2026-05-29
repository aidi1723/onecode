from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .guard_executor import validate_guard_policy_file
from .loader import load_dictionary
from .minimal_gateway_core import load_oneword_dict


REQUIRED_AUDIT_FIELDS = {
    "timestamp",
    "command",
    "exit_code",
    "stdout_digest",
    "stderr_digest",
    "sha256",
}

ROOT_OPCODES = {"查", "修", "测", "卫", "停", "问", "记", "总"}
WRITE_POLICY_RANK = {
    "forbidden": 0,
    "scoped": 1,
    "scoped_to_impact_files": 1,
    "allowed": 2,
}


def validate_dictionary(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    entries = data.get("entries", [])
    codes = [entry.get("code") for entry in entries]

    for code, count in Counter(codes).items():
        if count > 1:
            errors.append(f"Duplicate execution code: {code}")

    by_code = {entry["code"]: entry for entry in entries if "code" in entry}
    for required in ["查", "修", "测", "源", "卫", "部", "数", "文", "合", "搜", "问", "停", "记", "评", "总"]:
        if required not in by_code:
            errors.append(f"Missing required execution code: {required}")

    for entry in entries:
        code = entry.get("code", "<unknown>")
        tool_policy = entry.get("tool_policy", {})
        runtime = entry.get("runtime_environment", {})
        verification = entry.get("verification", {})
        fallback = entry.get("fallback", {})
        reference_patterns = entry.get("reference_workflow_patterns", [])
        protocol = entry.get("professional_protocol", {})
        root_opcode = entry.get("root_opcode")
        opcode_vector = entry.get("opcode_vector", {})
        inheritance_policy = entry.get("inheritance_policy", {})
        six_phase_workflow = entry.get("six_phase_workflow", [])
        transition_policy = entry.get("transition_policy", {})

        if not isinstance(reference_patterns, list) or not reference_patterns:
            errors.append(f"{code}: reference_workflow_patterns must be non-empty")

        if root_opcode not in ROOT_OPCODES:
            errors.append(f"{code}: root_opcode must be one of {sorted(ROOT_OPCODES)}")
        elif code in ROOT_OPCODES and root_opcode != code:
            errors.append(f"{code}: root opcode entry must point to itself")

        if not isinstance(opcode_vector, dict) or not opcode_vector.get("permission"):
            errors.append(f"{code}: opcode_vector.permission must be set")
        if not isinstance(opcode_vector, dict) or not opcode_vector.get("context"):
            errors.append(f"{code}: opcode_vector.context must be set")
        if not isinstance(opcode_vector.get("evidence"), list) or not opcode_vector.get("evidence"):
            errors.append(f"{code}: opcode_vector.evidence must be non-empty")

        if inheritance_policy.get("can_relax_permission") is not False:
            errors.append(f"{code}: inheritance_policy.can_relax_permission must be false")
        if inheritance_policy.get("can_add_evidence") is not True:
            errors.append(f"{code}: inheritance_policy.can_add_evidence must be true")
        if inheritance_policy.get("context_must_not_expand") is not True:
            errors.append(f"{code}: inheritance_policy.context_must_not_expand must be true")

        if not isinstance(six_phase_workflow, list) or len(six_phase_workflow) < 6:
            errors.append(f"{code}: six_phase_workflow must contain at least 6 steps")

        for key in ["on_success", "on_failure", "on_risk"]:
            values = transition_policy.get(key)
            if not isinstance(values, list) or not values:
                errors.append(f"{code}: transition_policy.{key} must be non-empty")
            elif any(value not in ROOT_OPCODES for value in values):
                errors.append(f"{code}: transition_policy.{key} contains unknown root opcode")

        source_projects = protocol.get("source_projects", [])
        operating_logic = protocol.get("operating_logic", [])
        hard_gates = protocol.get("hard_gates", [])
        if not isinstance(source_projects, list) or not source_projects:
            errors.append(f"{code}: professional_protocol.source_projects must be non-empty")
        if not isinstance(operating_logic, list) or len(operating_logic) < 3:
            errors.append(f"{code}: professional_protocol.operating_logic must contain at least 3 steps")
        if not isinstance(hard_gates, list) or len(hard_gates) < 2:
            errors.append(f"{code}: professional_protocol.hard_gates must contain at least 2 gates")

        if runtime.get("audit_log_write_access") != "system_only":
            errors.append(f"{code}: audit log must be system_only")

        if verification.get("required"):
            audit_fields = set(verification.get("audit_fields", []))
            missing = REQUIRED_AUDIT_FIELDS - audit_fields
            if missing:
                errors.append(f"{code}: missing audit fields {sorted(missing)}")

        if code in {"查", "审", "源", "卫", "隔", "合", "搜", "问", "停", "评", "总"} and tool_policy.get("write") != "forbidden":
            errors.append(f"{code}: read-only/control code must forbid write")

        if code in {"源", "合", "搜", "问", "停", "记", "评", "总"} and tool_policy.get("dependency_install") != "forbidden":
            errors.append(f"{code}: dependency_install must be forbidden")

        if code == "修" and fallback.get("on_max_retry_exceeded") != "MELT_DOWN_TO_查":
            errors.append("修: must melt down to 查 after max retries")

    for entry in entries:
        code = entry.get("code", "<unknown>")
        root_opcode = entry.get("root_opcode")
        if root_opcode not in by_code:
            continue
        root_entry = by_code[root_opcode]
        child_rank = WRITE_POLICY_RANK.get(entry.get("tool_policy", {}).get("write"), 99)
        root_rank = WRITE_POLICY_RANK.get(root_entry.get("tool_policy", {}).get("write"), 99)
        if child_rank > root_rank:
            errors.append(f"{code}: cannot relax root write policy from {root_opcode}")

    return errors


def validate_file(path: str | Path) -> list[str]:
    return validate_dictionary(load_dictionary(path))


def validate_project_files(
    dictionary_path: str | Path = "agent_skill_dictionary/programming-agent-skill-dictionary.json",
    guard_policy_path: str | Path = "agent_skill_dictionary/guard_policy.json",
    oneword_dict_path: str | Path = "agent_skill_dictionary/oneword_dict.json",
) -> list[str]:
    errors = validate_file(dictionary_path)
    errors.extend(f"guard_policy: {error}" for error in validate_guard_policy_file(guard_policy_path))
    try:
        load_oneword_dict(oneword_dict_path)
    except (KeyError, ValueError) as exc:
        errors.append(f"oneword_dict: {exc}")
    return errors


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        validation_errors = validate_file(sys.argv[1])
    else:
        validation_errors = validate_project_files()
    if validation_errors:
        for error in validation_errors:
            print(error)
        raise SystemExit(1)
    print("OK")
