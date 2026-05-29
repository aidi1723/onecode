from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

from .build_mode_archive import finalize_manifest
from .build_mode_audit import audit_behavior_fingerprint
from .build_mode_decay import compute_decay_gate
from .build_mode_feedback import rewrite_empty_patch_retry_payload, rewrite_to_soft_payload
from .build_mode_fsm import next_hexagram
from .build_mode_permissions import map_shadow_tool
from .build_mode_permissions import DEFAULT_PYTHON_TEST_COMMAND
from .build_mode_repair import build_repair_card
from .build_mode_runtime_guard import run_guarded_runtime
from .build_mode_sandbox import run_isolated_test
from .build_mode_orchestrator import RequiredArtifactPlan
from .build_mode_sovereignty import SUPPORT_FILES
from .build_mode_types import (
    HEX_CREATE,
    HEX_HALT,
    HEX_INSPECT,
    HEX_RETURN,
    HEX_VERIFY,
    ViolationEvidence,
    dto_to_dict,
)
from .build_mode_v3_balancer import FiveElementsDynamicBalancer
from .build_mode_writer import safe_write
from .inspect_executor import build_native_inspect_card


CREATE_PATCH_TOOLS = {"apply_patch", "patch"}


def execute_build_mode_tool(
    workspace: str | Path,
    tool_name: str,
    arguments: Any,
    use_docker: bool = False,
    timeout_seconds: int = 15,
    lockdown: bool = False,
    previous_failure_summary: str = "",
    assistant_text: str = "",
    artifact_plan: RequiredArtifactPlan | None = None,
) -> dict[str, Any]:
    root = Path(workspace).resolve()
    if assistant_text:
        audit = audit_behavior_fingerprint(assistant_text, tool_name, arguments)
        if audit.suspicious:
            violation = ViolationEvidence(
                blocked_action=tool_name,
                reason="behavior_fingerprint_suspicious",
                source="build_mode_audit",
            )
            payload = _blocked_payload(HEX_HALT, violation)
            payload["audit"] = dto_to_dict(audit)
            return payload
    mapping = map_shadow_tool(tool_name, arguments)
    if mapping.hexagram == HEX_CREATE:
        if tool_name in CREATE_PATCH_TOOLS:
            evidence = _apply_scoped_patch(root, _patch_text(arguments), artifact_plan=artifact_plan)
        else:
            path, content = _write_args(arguments)
            violation = _plan_path_violation(path, artifact_plan)
            if violation is not None:
                return _blocked_payload(mapping.hexagram, violation)
            evidence = safe_write(root, path, content)
        if isinstance(evidence, ViolationEvidence):
            if tool_name in CREATE_PATCH_TOOLS and evidence.reason == "empty_patch":
                return _empty_patch_retry_payload(evidence)
            return _blocked_payload(mapping.hexagram, evidence)
        return {
            "status": "ok",
            "hexagram": HEX_CREATE,
            "next_hexagram": next_hexagram(HEX_CREATE, evidence),
            "shadow_action": mapping.shadow_action,
            "evidence": dto_to_dict(evidence),
        }
    if mapping.hexagram == HEX_VERIFY:
        command = _command_args(arguments)
        runtime_guard_result = None
        if artifact_plan is not None and not use_docker:
            runtime_guard_result = run_guarded_runtime(
                command,
                workspace=root,
                artifact_plan=artifact_plan,
                timeout_seconds=timeout_seconds,
            )
            sandbox = _sandbox_from_runtime_guard(runtime_guard_result)
        else:
            sandbox = run_isolated_test(command, root, use_docker=use_docker, timeout_seconds=timeout_seconds)
        next_state = next_hexagram(HEX_VERIFY, sandbox)
        payload: dict[str, Any] = {
            "status": "completed" if next_state == HEX_RETURN else "needs_fix",
            "hexagram": HEX_VERIFY,
            "next_hexagram": next_state,
            "shadow_action": mapping.shadow_action,
            "evidence": dto_to_dict(sandbox),
        }
        if runtime_guard_result is not None:
            payload["runtime_guard"] = runtime_guard_result
        if next_state == HEX_RETURN:
            archive = finalize_manifest(root, lockdown=lockdown)
            payload["archive"] = dto_to_dict(archive)
            payload["final_next_hexagram"] = next_hexagram(HEX_RETURN, archive)
        else:
            payload["feedback"] = rewrite_to_soft_payload(sandbox)
            fire_digest = FiveElementsDynamicBalancer(_python_artifacts(root)).fire_digest(
                root,
                _sandbox_failure_text(sandbox),
            )
            payload["repair_card"] = build_repair_card(root, fire_digest.text)
            payload["v3"] = {
                "element": "火",
                "fire_digest": fire_digest.text,
                "line_refs": list(fire_digest.line_refs),
                "exception": fire_digest.exception,
            }
            if previous_failure_summary and sandbox.failure_summary:
                payload["decay"] = dto_to_dict(
                    compute_decay_gate(previous_failure_summary, sandbox.failure_summary)
                )
        return payload
    if mapping.hexagram == HEX_INSPECT:
        target = _inspect_target(arguments)
        card = build_native_inspect_card(root, target=target)
        return {
            "status": "ok",
            "hexagram": HEX_INSPECT,
            "next_hexagram": HEX_CREATE,
            "shadow_action": mapping.shadow_action,
            "repo_card": card,
            "repo_card_text": card["text"],
        }
    if mapping.hexagram == HEX_HALT:
        violation = ViolationEvidence(
            blocked_action=_command_text(arguments) or tool_name,
            reason=mapping.reason,
            source="build_mode_tool_executor",
        )
        return _blocked_payload(HEX_HALT, violation)
    violation = ViolationEvidence(
        blocked_action=_command_text(arguments) or tool_name,
        reason=mapping.reason,
        source="build_mode_tool_executor",
    )
    return _blocked_payload(mapping.hexagram, violation)


def _sandbox_from_runtime_guard(result: dict[str, object]) -> Any:
    from .build_mode_sandbox import sandbox_evidence_from_result

    evidence_input = {
        "exit_code": int(result.get("exit_code", 1)),
        "stdout": str(result.get("stdout", "")),
        "stderr": str(result.get("stderr", "")),
    }
    if result.get("status") == "blocked":
        reason = str(result.get("reason") or "runtime_guard_blocked")
        details = ", ".join(str(path) for path in result.get("unplanned_paths", []))
        evidence_input["stderr"] = "\n".join(
            part for part in (evidence_input["stderr"], f"{reason}: {details}") if part
        )
    return sandbox_evidence_from_result(evidence_input, 0)


def _sandbox_failure_text(sandbox: Any) -> str:
    return str(getattr(sandbox, "failure_summary", "") or "")


def _python_artifacts(root: Path) -> list[str]:
    return [
        str(path.relative_to(root))
        for path in root.rglob("*.py")
        if ".yizijue" not in path.parts and "__pycache__" not in path.parts
    ][:80]


def _blocked_payload(hexagram: str, evidence: ViolationEvidence) -> dict[str, Any]:
    return {
        "status": "blocked",
        "hexagram": hexagram,
        "next_hexagram": "110",
        "evidence": dto_to_dict(evidence),
        "feedback": rewrite_to_soft_payload(evidence),
    }


def _empty_patch_retry_payload(evidence: ViolationEvidence) -> dict[str, Any]:
    return {
        "status": "needs_retry",
        "hexagram": "110",
        "next_hexagram": HEX_CREATE,
        "reason": "empty_patch",
        "fallback_tools": ["write_file"],
        "evidence": dto_to_dict(evidence),
        "feedback": rewrite_empty_patch_retry_payload(evidence),
    }


def _write_args(arguments: Any) -> tuple[str, str]:
    if not isinstance(arguments, dict):
        raise ValueError("write tool arguments must be an object")
    path = str(arguments.get("path") or arguments.get("file_path") or "")
    content = str(arguments.get("content") or arguments.get("text") or "")
    return path, content


def _patch_text(arguments: Any) -> str:
    if isinstance(arguments, dict):
        return str(arguments.get("patch") or arguments.get("content") or arguments.get("text") or "")
    return str(arguments or "")


def _apply_scoped_patch(
    root: Path,
    patch_text: str,
    *,
    artifact_plan: RequiredArtifactPlan | None = None,
) -> Any:
    changes = _parse_add_file_patch(patch_text)
    if isinstance(changes, ViolationEvidence):
        return changes
    changed_files: list[str] = []
    digests: list[str] = []
    for relative_path, content in changes:
        violation = _plan_path_violation(relative_path, artifact_plan)
        if violation is not None:
            return violation
        evidence = safe_write(root, relative_path, content)
        if isinstance(evidence, ViolationEvidence):
            return evidence
        changed_files.extend(evidence.changed_files)
        digests.append(evidence.patch_digest)
    import hashlib

    digest = hashlib.sha256("\n".join(digests).encode("utf-8")).hexdigest()
    from .build_mode_types import WriteEvidence

    return WriteEvidence(
        ok=True,
        changed_files=tuple(changed_files),
        path_scope=str(root),
        patch_digest=digest,
    )


def _parse_add_file_patch(patch_text: str) -> list[tuple[str, str]] | ViolationEvidence:
    if not patch_text.strip():
        return ViolationEvidence(
            blocked_action="apply_patch",
            reason="empty_patch",
            source="build_mode_tool_executor",
        )
    lines = patch_text.splitlines()
    if not lines or lines[0].strip() != "*** Begin Patch" or lines[-1].strip() != "*** End Patch":
        return ViolationEvidence(
            blocked_action="apply_patch",
            reason="unsupported_patch_format",
            source="build_mode_tool_executor",
        )
    changes: list[tuple[str, str]] = []
    index = 1
    while index < len(lines) - 1:
        line = lines[index]
        if line.startswith("*** Add File: "):
            relative_path = line[len("*** Add File: ") :].strip()
            index += 1
            content_lines: list[str] = []
            while index < len(lines) - 1 and not lines[index].startswith("*** "):
                content_line = lines[index]
                if not content_line.startswith("+"):
                    return ViolationEvidence(
                        blocked_action=f"apply_patch:{relative_path}",
                        reason="unsupported_patch_hunk",
                        source="build_mode_tool_executor",
                    )
                content_lines.append(content_line[1:])
                index += 1
            changes.append((relative_path, "\n".join(content_lines) + "\n"))
            continue
        return ViolationEvidence(
            blocked_action="apply_patch",
            reason="unsupported_patch_operation",
            source="build_mode_tool_executor",
        )
    if not changes:
        return ViolationEvidence(
            blocked_action="apply_patch",
            reason="empty_patch",
            source="build_mode_tool_executor",
        )
    return changes


def _plan_path_violation(
    relative_path: str,
    artifact_plan: RequiredArtifactPlan | None,
) -> ViolationEvidence | None:
    if artifact_plan is None or not artifact_plan.artifacts:
        return None
    normalized = Path(str(relative_path)).as_posix()
    allowed = {artifact.path for artifact in artifact_plan.artifacts}
    allowed.update(SUPPORT_FILES.get(artifact_plan.project_name, ()))
    if normalized in allowed:
        return None
    return ViolationEvidence(
        blocked_action=f"write:{relative_path}",
        reason="unplanned_artifact_path",
        source="build_mode_sovereignty",
    )


def _command_args(arguments: Any) -> list[str]:
    text = _command_text(arguments)
    if not text:
        text = DEFAULT_PYTHON_TEST_COMMAND
    return shlex.split(text)


def _command_text(arguments: Any) -> str:
    if isinstance(arguments, dict):
        return str(arguments.get("command") or arguments.get("cmd") or "")
    return str(arguments or "")


def _inspect_target(arguments: Any) -> str | None:
    if not isinstance(arguments, dict):
        return None
    value = arguments.get("target") or arguments.get("path") or arguments.get("file_path")
    return str(value) if value else None
