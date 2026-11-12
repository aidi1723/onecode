"""Verifier repair loop, snapshots, and reward-guided retries."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Callable

from onecode.kernel.model_provider import (
    ModelPlan,
    ModelPlanPatch,
)
from onecode.kernel.execution_contracts import ExecutionStep
from onecode.kernel.checkpoint import write_ledger
from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.path_guard import PathGuard, PathGuardError
from onecode.kernel.preset_tests import is_preset_test_path
from onecode.kernel.symbolic_telemetry import (
    call_symbolic_profile,
    compute_cycle_gain_multiplier,
    compute_systemic_intervention,
    resolve_state_governance_mode,
    symbolic_telemetry_enabled,
)


def _same_step_retry(failure: dict[str, Any] | None) -> bool:
    if not isinstance(failure, dict) or failure.get("failure_kind") != "invalid_model_plan":
        return False
    detail = str(failure.get("detail") or "")
    return (
        "model response was not valid JSON" in detail
        or "no_action cannot be combined with actions" in detail
        or "task must be a non-empty string" in detail
    )


def _modified_paths_from_result(result: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for a in result.get("assets", []):
        if isinstance(a, dict) and isinstance(a.get("path"), str):
            paths.append(a["path"])
    for p in result.get("patches", []):
        if isinstance(p, dict) and isinstance(p.get("path"), str):
            paths.append(p["path"])
    trace = result.get("execution_trace")
    if isinstance(trace, dict):
        for rr in trace.get("runner_results", []):
            if isinstance(rr, dict) and rr.get("status") == "completed":
                payload = rr.get("payload")
                if isinstance(payload, dict) and isinstance(payload.get("path"), str):
                    paths.append(payload["path"])
    return list(dict.fromkeys(paths))


def _generate_missing_artifacts(task: str, workspace: Path, modified_paths: list[str]) -> None:
    from onecode.kernel.model_guidance import _OUTPUT_DATA_FILE
    data_files = [f for f in _OUTPUT_DATA_FILE.findall(task) if not (workspace / f).is_file()]
    if not data_files:
        return
    candidates = [p for p in modified_paths if p.endswith(".py") and (workspace / p).is_file()]
    for p in (
        "app/export.py",
        "export.py",
        "src/export.py",
        "scripts/export.py",
        "bin/export.py",
        "app/report.py",
        "report.py",
        "pipeline.py",
    ):
        if (workspace / p).is_file() and p not in candidates:
            candidates.append(p)
    import os
    import sys

    env = {**os.environ, "PYTHONPATH": str(workspace)}
    for script in candidates:
        try:
            subprocess.run([sys.executable, script], cwd=str(workspace), env=env, capture_output=True, timeout=15)
        except (subprocess.SubprocessError, OSError):
            pass
        if all((workspace / f).is_file() for f in data_files):
            break
        if "/" in script:
            mod_name = script.removesuffix(".py").replace("/", ".")
            try:
                subprocess.run([sys.executable, "-m", mod_name], cwd=str(workspace), env=env, capture_output=True, timeout=15)
            except (subprocess.SubprocessError, OSError):
                pass
            if all((workspace / f).is_file() for f in data_files):
                break
        for data_file in data_files:
            if not (workspace / data_file).is_file():
                for arg in (data_file, f"--output={data_file}", f"--out={data_file}"):
                    try:
                        subprocess.run([sys.executable, script, arg], cwd=str(workspace), env=env, capture_output=True, timeout=15)
                    except (subprocess.SubprocessError, OSError):
                        pass
                    if (workspace / data_file).is_file():
                        break
        if all((workspace / f).is_file() for f in data_files):
            break


def _repair_roots(workspace: Path) -> list[Path]:
    from onecode.kernel.model_guidance import _REPAIR_SKIP
    src = workspace / "src"
    if src.is_dir():
        return [src]
    if not workspace.is_dir():
        return []
    roots: list[Path] = []
    for child in sorted(workspace.iterdir()):
        if child.name in _REPAIR_SKIP or child.name.startswith("."):
            continue
        if child.is_dir() or (child.is_file() and child.suffix == ".py"):
            roots.append(child)
    return roots


def _src_files_for_repair(
    workspace: Path,
    preview_limit: int | None = None,
    max_files: int | None = None,
    priority_paths: list[str] | None = None,
) -> dict[str, str]:
    from onecode.kernel.model_guidance import resolve_task_bureau
    if preview_limit is None or max_files is None:
        bureau = resolve_task_bureau(workspace)
        if preview_limit is None:
            preview_limit = bureau.get("preview_limit_chars", 4000)
        if max_files is None:
            max_files = bureau.get("repair_file_limit", 8)
    files: dict[str, str] = {}
    if priority_paths:
        for p in priority_paths:
            if len(files) >= max_files:
                break
            cand = workspace / p
            if cand.is_file() and not is_preset_test_path(p) and not PathGuard.is_sensitive_read_path(Path(p)):
                try:
                    content = cand.read_text(encoding="utf-8")
                    if len(content) > preview_limit:
                        files[p] = (
                            content[:preview_limit]
                            + f"\n# [TRUNCATED: preview limited to {preview_limit} of {len(content)} chars. Use search_block/replace_block patches rather than rewriting full file]"
                        )
                    else:
                        files[p] = content
                except OSError:
                    pass
    for root in _repair_roots(workspace):
        paths = [root] if root.is_file() else sorted(root.rglob("*.py"))
        for path in paths:
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            relative = path.relative_to(workspace).as_posix()
            if relative in files:
                continue
            if is_preset_test_path(relative) or Path(relative).name in {"unittest.py", "pytest.py", "conftest.py"}:
                continue
            content = path.read_text(encoding="utf-8")
            if len(content) > preview_limit:
                files[relative] = (
                    content[:preview_limit]
                    + f"\n# [TRUNCATED: preview limited to {preview_limit} of {len(content)} chars. Use search_block/replace_block patches rather than rewriting full file]"
                )
            else:
                files[relative] = content
            if len(files) >= max_files:
                return files
    return files


def _repair_source_block(failed_result: dict[str, Any]) -> str:
    files = failed_result.get("workspace_files")
    if not isinstance(files, dict):
        return ""
    blocks: list[str] = []
    for path in sorted(files):
        if not isinstance(path, str) or not path.endswith(".py") or path.startswith("tests/"):
            continue
        content = files.get(path)
        if not isinstance(content, str) or content == "":
            continue
        blocks.append(f"## {path}\n{content}")
    if not blocks:
        return ""
    return "Current source:\n" + "\n".join(blocks) + "\n"


def _is_test_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return normalized == "tests" or normalized.startswith("tests/")


def _detail_mentions_tests(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    path = payload.get("path")
    return isinstance(path, str) and _is_test_path(path)


def _drop_protected_changes(plan: ModelPlan, task: str) -> ModelPlan:
    from onecode.kernel.model_guidance import protected_python_files
    protected = set(protected_python_files(task))
    if not protected:
        return plan

    def _is_protected(p: str) -> bool:
        clean = p.replace("\\", "/")
        return clean in protected or Path(clean).name in protected

    assets = [asset for asset in plan.assets if not _is_protected(asset.path)]
    patches = [patch for patch in plan.patches if not _is_protected(patch.path)]
    steps = []
    for step in plan.execution_steps:
        blocked = any(
            isinstance(call.params, dict) and isinstance(call.params.get("path"), str) and _is_protected(call.params["path"])
            for call in step.tool_calls
        )
        if not blocked:
            steps.append(step)
    if len(assets) == len(plan.assets) and len(patches) == len(plan.patches) and len(steps) == len(plan.execution_steps):
        return plan
    return ModelPlan(task=plan.task, assets=assets, patches=patches, execution_steps=steps, no_action_reason=plan.no_action_reason)


def is_patch_only_repair_plan(plan: ModelPlan) -> bool:
    return bool(plan.patches) and not plan.assets and not plan.execution_steps


_TEST_ASSET_SHADOWS = {"unittest.py", "pytest.py", "conftest.py", "sitecustomize.py", "usercustomize.py"}


def _is_new_test_asset_plan(plan: ModelPlan) -> bool:
    if plan.patches or plan.execution_steps or len(plan.assets) != 1:
        return False
    path = plan.assets[0].path.replace("\\", "/")
    name = path.rsplit("/", 1)[-1].lower()
    return path.startswith("tests/") and path.endswith(".py") and name not in _TEST_ASSET_SHADOWS


def _repair_diff_blocks(before: str, after: str) -> tuple[str, str] | None:
    if before == "" or before == after:
        return None
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    prefix = 0
    limit = min(len(before_lines), len(after_lines))
    while prefix < limit and before_lines[prefix] == after_lines[prefix]:
        prefix += 1
    suffix = 0
    while (
        suffix < len(before_lines) - prefix
        and suffix < len(after_lines) - prefix
        and before_lines[-1 - suffix] == after_lines[-1 - suffix]
    ):
        suffix += 1
    start = prefix
    before_end = len(before_lines) - suffix
    after_end = len(after_lines) - suffix
    if prefix == before_end:
        if prefix > 0:
            start = prefix - 1
        elif suffix > 0:
            before_end = prefix + 1
            after_end = prefix + 1
        else:
            return None
    search = "".join(before_lines[start:before_end])
    replace = "".join(after_lines[start:after_end])
    if search == "" or before.count(search) != 1:
        search, replace = before, after
    if search == "" or before.count(search) != 1:
        return None
    return search, replace


def synthesize_single_asset_repair(plan: ModelPlan, workspace: Path) -> ModelPlan:
    """Turn one full-file rewrite of an existing source file into a unique patch."""
    if plan.patches or len(plan.assets) != 1 or plan.no_action_reason is not None:
        return plan
    asset = plan.assets[0]
    candidate_path = asset.path.lstrip("/") if asset.path.startswith("/") else asset.path
    if _is_test_path(candidate_path):
        return plan
    target: Path | None = None
    resolved_rel = candidate_path
    try:
        cand = PathGuard.resolve_target(workspace, candidate_path)
        if cand.is_file():
            target = cand
    except PathGuardError:
        pass
    if target is None:
        name = Path(candidate_path).name
        matches = [
            p for p in workspace.rglob(name)
            if p.is_file() and not _is_test_path(str(p.relative_to(workspace))) and ".onecode" not in p.parts
        ]
        if len(matches) == 1:
            target = matches[0]
            resolved_rel = str(matches[0].relative_to(workspace)).replace("\\", "/")
    if target is None or not target.is_file():
        return plan
    try:
        before = target.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return plan
    blocks = _repair_diff_blocks(before, asset.content)
    if blocks is None:
        return plan
    search, replace = blocks
    return ModelPlan(
        task=plan.task,
        patches=[ModelPlanPatch(path=resolved_rel, search_block=search, replace_block=replace)],
    )


def repair_rejected_result(
    initial_result: dict[str, Any],
    run_id: str | None,
    reason: str,
    repair_attempt_count: int = 1,
) -> dict[str, Any]:
    return {
        **initial_result,
        "run_id": run_id,
        "status": "halted",
        "reason": reason,
        "partial": True,
        "repaired": False,
        "repair_attempt_count": repair_attempt_count,
        "initial_status": initial_result.get("status"),
        "initial_reason": initial_result.get("reason"),
    }


def merge_repair_result(
    initial_result: dict[str, Any],
    repair_result: dict[str, Any],
    repair_attempt_count: int,
) -> dict[str, Any]:
    history = list(initial_result.get("turn_history", []))
    if not history:
        history.append({
            "turn_id": 1,
            "branch_name": _TURN_BRANCHES[0],
            "modified_files": _modified_paths_from_result(initial_result),
            "status": initial_result.get("status"),
            "reason": initial_result.get("reason"),
        })
    turn_id = repair_attempt_count + 1
    branch_idx = (turn_id - 1) % 12
    history.append({
        "turn_id": turn_id,
        "branch_name": _TURN_BRANCHES[branch_idx % len(_TURN_BRANCHES)],
        "modified_files": _modified_paths_from_result(repair_result),
        "status": repair_result.get("status"),
        "reason": repair_result.get("reason"),
    })
    return {
        **repair_result,
        "repaired": repair_result.get("status") == "completed",
        "repair_attempt_count": repair_attempt_count,
        "initial_status": initial_result.get("status"),
        "initial_reason": initial_result.get("reason"),
        "initial_execution_trace": initial_result.get("execution_trace"),
        "turn_history": history,
    }


def _plan_has_existing_file_rewrite(plan: ModelPlan, workspace: Path) -> bool:
    from onecode.kernel.model_loop import _record_kernel_fault
    """Return True if plan attempts to fully rewrite an existing file with write_text/asset."""
    for asset in plan.assets:
        try:
            target = PathGuard.resolve_target(workspace, asset.path)
            if target.is_file() and target.stat().st_size > 0:
                return True
        except (OSError, PathGuardError) as ex:
            _record_kernel_fault("rewrite_probe", ex)
            continue
    for step in plan.execution_steps:
        for tool_call in step.tool_calls:
            if tool_call.tool_name == "write_text":
                path_val = tool_call.params.get("path")
                if isinstance(path_val, str):
                    try:
                        target = PathGuard.resolve_target(workspace, path_val)
                        if target.is_file() and target.stat().st_size > 0:
                            return True
                    except (OSError, PathGuardError) as ex:
                        _record_kernel_fault("rewrite_probe", ex)
                        continue
    return False


def _resolve_governance_mode(run_metadata: dict[str, Any]) -> str:
    from onecode.kernel.model_loop import _record_kernel_fault
    """Resolve governance mode from metadata or status code."""
    mode = run_metadata.get("governance_mode")
    if isinstance(mode, str):
        return mode
    brightness = run_metadata.get("star_brightness")
    if isinstance(brightness, dict) and isinstance(brightness.get("governance_mode"), str):
        return str(brightness["governance_mode"])
    raw_status = run_metadata.get("iching_status_code")
    if raw_status is None:
        raw_status = run_metadata.get("task_status_code")
    if raw_status is not None:
        try:
            status_int = int(raw_status)
            return resolve_state_governance_mode(status_int)
        except (TypeError, ValueError, KeyError) as ex:
            _record_kernel_fault("governance_mode", ex)
    if os.environ.get("ONECODE_GOVERNANCE_MODE"):
        return os.environ["ONECODE_GOVERNANCE_MODE"]
    return "autonomous"


def _enrich_failed_model_with_repair_state(
    failed_model: dict[str, Any],
    last_state: dict[str, Any],
    attempt: int,
) -> dict[str, Any]:
    enriched = dict(failed_model)
    for k in (
        "host_reward",
        "container_id",
        "container_image",
        "container_arch",
        "turn_history",
        "verifier_results",
    ):
        if k in last_state and k not in enriched:
            enriched[k] = last_state[k]
    if "repair_attempt_count" not in enriched:
        enriched["repair_attempt_count"] = last_state.get(
            "repair_attempt_count", max(0, attempt - 1)
        )
    return enriched


def ledger_fields_for_iching(code: int) -> dict[str, Any]:
    """Shared outcome fields for classic and terminal runs. The code stays the hexagram integer."""
    transition = IchingKernel.transition(code)
    return {
        "iching_status_code": code,
        "outcome_status_code": code,
        "global_status_code": code,
        "iching_transition_action": transition.action,
        "iching_transition_reason": transition.reason,
        "global_transition_action": transition.action,
        "global_transition_reason": transition.reason,
        "dispatch_decision": IchingKernel.dispatch_decision(transition),
    }


def _execution_rule_fields(
    trace: Any,
    *,
    status: str,
    requested_count: int,
    completed_count: int,
    skipped_count: int,
    failed_count: int,
) -> dict[str, Any]:
    transition = trace.global_transition
    fields: dict[str, Any] = {
        "global_status_code": trace.global_status_code,
        "outcome_status_code": trace.global_status_code,
        "transition_status_code": transition.status_code if transition is not None else None,
        "global_transition_action": transition.action if transition is not None else None,
        "global_transition_reason": transition.reason if transition is not None else None,
        "global_entropy": trace.global_entropy,
        "global_entropy_decision": trace.global_entropy_decision,
        "global_entropy_reason": trace.global_entropy_reason,
    }
    if transition is not None:
        fields["iching_status_code"] = transition.status_code
        fields["iching_transition_action"] = transition.action
        fields["iching_transition_reason"] = transition.reason
        fields["dispatch_decision"] = IchingKernel.dispatch_decision(transition)
    return fields | IchingKernel.delivery_decision(
        status, requested_count, completed_count, skipped_count, failed_count
    )


def _merge_narrow_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    merged = dict(results[-1])
    assets: list[Any] = []
    requested = completed = skipped = failed = asset_count = 0
    for result in results:
        result_assets = result.get("assets")
        if isinstance(result_assets, list):
            assets.extend(result_assets)
        requested += int(result.get("requested_count") or 0)
        completed += int(result.get("completed_count") or 0)
        skipped += int(result.get("skipped_count") or 0)
        failed += int(result.get("failed_count") or 0)
        asset_count += int(result.get("model_plan_asset_count") or 0)
    merged["assets"] = assets
    merged["requested_count"] = requested
    merged["completed_count"] = completed
    merged["skipped_count"] = skipped
    merged["failed_count"] = failed
    merged["model_plan_asset_count"] = asset_count
    return merged


def _close_narrow_sequence(
    results: list[dict[str, Any]],
    *,
    status: str,
    reason: str | None,
    model_context: Any,
    outstanding: bool,
) -> dict[str, Any]:
    merged = _merge_narrow_results(results)
    if outstanding:
        merged["requested_count"] = int(merged["completed_count"]) + 1
    status_code = IchingKernel.classify_outcome(status, reason)
    transition = IchingKernel.transition(status_code)
    delivery = IchingKernel.delivery_decision(
        status,
        merged["requested_count"],
        merged["completed_count"],
        merged["skipped_count"],
        merged["failed_count"],
    )
    closed = {
        **merged,
        "status": status,
        "reason": reason,
        "partial": status != "completed",
        "iching_status_code": transition.status_code,
        "iching_transition_action": transition.action,
        "iching_transition_reason": transition.reason,
        "global_status_code": transition.status_code,
        "global_transition_action": transition.action,
        "global_transition_reason": transition.reason,
        "dispatch_decision": IchingKernel.dispatch_decision(transition),
        **delivery,
    }
    write_ledger(model_context, closed)
    return closed


def _write_following_narrow_files(
    *,
    task: str,
    plan: ModelPlan,
    result: dict[str, Any],
    max_repair_attempts: int,
    provider: Any,
    model_context: Any,
    trace_path: Path,
    provider_config: Any,
    resolved_model: str,
    http_timeout_seconds: float,
    planning_context: dict[str, Any],
    workspace: Path,
    run_id: str | None,
    resume_from_run_id: str | None,
    run_metadata: dict[str, Any],
    require_explicit_approval: bool,
    execution_approval: Callable[[ExecutionStep], bool] | None,
    on_turn: Callable[[dict[str, Any]], None] | None,
) -> dict[str, Any]:
    from onecode.kernel.model_guidance import _required_files_landed, file_write_slots, narrow_plan_prompt, required_python_files
    from onecode.kernel.model_planning import execute_model_plan, traced_provider_plan_retrying
    written = [asset.path for asset in plan.assets]
    results = [result]
    slots = file_write_slots(task, max_repair_attempts)
    for index in range(2, slots + 1):
        if _required_files_landed(task, written):
            return _close_narrow_sequence(
                results,
                status="completed",
                reason=None,
                model_context=model_context,
                outstanding=False,
            )
        next_plan, failure = traced_provider_plan_retrying(
            provider=provider,
            task=narrow_plan_prompt(
                task,
                {"detail": "continue with the next file", "failure_kind": "resource_budget_exceeded"},
                written,
            ),
            model_context=model_context,
            trace_path=trace_path,
            provider_config=provider_config,
            resolved_model=resolved_model,
            http_timeout_seconds=http_timeout_seconds,
            planning_context=planning_context,
            span_id=f"model-narrow-{index}",
        )
        if failure is not None or next_plan is None:
            return _close_narrow_sequence(
                results,
                status="halted",
                reason=failure["failure_kind"] if failure is not None else "invalid_model_plan",
                model_context=model_context,
                outstanding=True,
            )
        next_plan = _drop_protected_changes(next_plan, task)
        if next_plan.no_action_reason is not None or (
            _required_files_landed(task, written) and not next_plan.assets and not next_plan.patches and not next_plan.execution_steps
        ):
            return _close_narrow_sequence(
                results,
                status="completed",
                reason=None,
                model_context=model_context,
                outstanding=False,
            )
        if not next_plan.assets and not next_plan.patches and not next_plan.execution_steps:
            return _close_narrow_sequence(
                results,
                status="halted",
                reason="invalid_model_plan",
                model_context=model_context,
                outstanding=True,
            )
        latest = execute_model_plan(
            next_plan,
            workspace=workspace,
            http_timeout_seconds=http_timeout_seconds,
            run_id=run_id,
            resume_from_run_id=resume_from_run_id,
            run_metadata={
                **run_metadata,
                "model_plan_asset_count": len(next_plan.assets),
                "model_plan_patch_count": len(next_plan.patches),
                "model_plan_execution_step_count": len(next_plan.execution_steps),
            },
            require_explicit_approval=require_explicit_approval,
            approval_callback=execution_approval,
            on_turn=on_turn,
        )
        results.append(latest)
        if latest["status"] != "completed":
            return _close_narrow_sequence(
                results,
                status=latest["status"],
                reason=latest.get("reason"),
                model_context=model_context,
                outstanding=False,
            )
        written.extend(asset.path for asset in next_plan.assets)
    if len(required_python_files(task)) > max_repair_attempts:
        close_plan, close_failure = traced_provider_plan_retrying(
            provider=provider,
            task=narrow_plan_prompt(task, {"detail": "close the finished files", "failure_kind": "resource_budget_exceeded"}, written),
            model_context=model_context,
            trace_path=trace_path,
            provider_config=provider_config,
            resolved_model=resolved_model,
            http_timeout_seconds=http_timeout_seconds,
            planning_context=planning_context,
            span_id="model-narrow-close",
        )
        if close_failure is not None or close_plan is None:
            return _close_narrow_sequence(
                results,
                status="halted",
                reason=close_failure["failure_kind"] if close_failure is not None else "invalid_model_plan",
                model_context=model_context,
                outstanding=True,
            )
        if close_plan.no_action_reason is not None:
            return _close_narrow_sequence(
                results,
                status="completed",
                reason=None,
                model_context=model_context,
                outstanding=False,
            )
        latest = execute_model_plan(
            close_plan,
            workspace=workspace,
            http_timeout_seconds=http_timeout_seconds,
            run_id=run_id,
            resume_from_run_id=resume_from_run_id,
            run_metadata=run_metadata,
            require_explicit_approval=require_explicit_approval,
            approval_callback=execution_approval,
            on_turn=on_turn,
        )
        results.append(latest)
    if _required_files_landed(task, written):
        return _close_narrow_sequence(
            results,
            status="completed",
            reason=None,
            model_context=model_context,
            outstanding=False,
        )
    return _close_narrow_sequence(
        results,
        status="halted",
        reason="resource_budget_exceeded",
        model_context=model_context,
        outstanding=True,
    )


def _repair_touches_tests(plan: ModelPlan) -> bool:
    for patch in plan.patches:
        path = patch.path.replace("\\", "/")
        if path == "tests" or path.startswith("tests/"):
            return True
    return False


def _compute_repair_cooldown(
    run_metadata: dict[str, Any],
    attempt: int,
    failed_code: int,
    scenario: str = "verifier_failure",
) -> int:
    from onecode.kernel.model_loop import _record_kernel_fault
    cooldown_ms = run_metadata.get("cooldown_pause_ms", 0)
    if attempt >= 2 and cooldown_ms < 50:
        cooldown_ms = min(200, 50 * (attempt - 1))
    try:
        from onecode.kernel.recovery_policy import recovery_status

        rec = recovery_status(
            scenario,
            turn_number=attempt,
            attempted=True,
            attempt_count=max(0, attempt - 1),
            status_code=failed_code,
        )
        damping_raw = rec.get("lyapunov_damping_factor")
        if damping_raw is None:
            jie = rec.get("jie_shen_relief", {})
            if jie.get("relief_effective"):
                damping_raw = jie.get("damping_factor", 0.75)
        if damping_raw is not None:
            damping = float(damping_raw)
            if damping > 0:
                base_ms = cooldown_ms if cooldown_ms > 0 else (50 if attempt >= 2 else 0)
                if base_ms > 0:
                    cooldown_ms = int(base_ms / damping)
    except (TypeError, ValueError, KeyError, ImportError) as ex:
        _record_kernel_fault("recovery_cooldown", ex)
    return cooldown_ms


def _snapshot_workspace_files(workspace: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for p in workspace.rglob("*"):
        if p.is_file() and not any(part in {".git", "__pycache__", ".venv", ".onecode"} for part in p.parts):
            try:
                rel = p.relative_to(workspace).as_posix()
                snapshot[rel] = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError, ValueError):
                pass
    return snapshot


def _restore_workspace_snapshot(workspace: Path, snapshot: dict[str, str]) -> None:
    current_files: set[str] = set()
    for p in workspace.rglob("*"):
        if p.is_file() and not any(part in {".git", "__pycache__", ".venv", ".onecode"} for part in p.parts):
            try:
                current_files.add(p.relative_to(workspace).as_posix())
            except ValueError:
                pass
    for rel_path in current_files - snapshot.keys():
        try:
            (workspace / rel_path).unlink()
        except OSError:
            pass
    for rel_path, content in snapshot.items():
        target = workspace / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_text(content, encoding="utf-8")
        except OSError:
            pass


def repair_budget_after_score(
    budget: int,
    previous: float | None,
    current: float | None,
    flat_rounds: int,
) -> tuple[int, int, bool]:
    """Extend a rising repair budget, and stop after two rounds with no score change."""
    if isinstance(current, bool) or not isinstance(current, (int, float)):
        return budget, flat_rounds, False
    if previous is None or isinstance(previous, bool) or not isinstance(previous, (int, float)):
        return budget, 0, False
    delta = float(current) - float(previous)
    if delta <= 1e-9:
        flat_rounds += 1
        return budget, flat_rounds, flat_rounds >= 2
    flat_rounds = 0
    if delta >= 0.15 or (float(current) >= 0.90 and delta > 0):
        budget = min(5, budget + 1)
    return budget, flat_rounds, False


def _numeric_reward(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _repair_posture(score: float | None) -> str:
    """Choose a micro patch, an ordinary patch, or a full rewrite from the current score."""
    if score is None:
        return "patch"
    if score < 0.40:
        return "macro"
    if score >= 0.85:
        return "micro"
    return "patch"


def _task_repair_posture(task: str, score: float | None) -> str:
    """Keep test-only repairs on the tests. A low score must not rewrite the implementation."""
    posture = _repair_posture(score)
    if posture == "macro" and _testing_only_task(task):
        return "patch"
    return posture


def _append_repair_turn(checked: dict[str, Any], result: dict[str, Any], reason: str) -> None:
    hist = list(checked.get("turn_history") or [])
    hist.append({
        "turn_id": len(hist) + 1,
        "branch_name": _TURN_BRANCHES[len(hist) % len(_TURN_BRANCHES)],
        "status": "halted",
        "reason": reason,
        "modified_files": [],
    })
    checked["turn_history"] = hist
    result["turn_history"] = hist


def _patch_line_count(text: str) -> int:
    return len(text.splitlines())


def _micro_line_limit(score: float | None) -> int:
    """Keep a 15-line edge fix for a near-perfect score, and allow a wider fix below that."""
    if score is not None and score >= 0.97:
        return 15
    return 40


def _micro_patch_too_wide(plan: ModelPlan, limit: int) -> bool:
    return any(
        _patch_line_count(patch.search_block) > limit or _patch_line_count(patch.replace_block) > limit
        for patch in plan.patches
    )


def _apply_scored_repair(
    workspace: Path,
    tested: dict[str, Any],
    best_checked: dict[str, Any],
    best_snapshot: dict[str, str],
    prev_reward: float | None,
    flat_rounds: int,
    effective_attempts: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str], float | None, int, int, bool]:
    """Keep the highest-scoring files. A lower or flat score counts as no progress."""
    cur_rew = _numeric_reward(tested.get("host_reward"))
    if cur_rew is None:
        return tested, best_checked, best_snapshot, prev_reward, flat_rounds, effective_attempts, False
    effective_attempts, flat_rounds, stop = repair_budget_after_score(
        effective_attempts,
        prev_reward,
        cur_rew,
        flat_rounds,
    )
    best_rew = _numeric_reward(best_checked.get("host_reward"))
    if best_rew is None or cur_rew > best_rew:
        return (
            tested,
            dict(tested),
            _snapshot_workspace_files(workspace),
            cur_rew,
            flat_rounds,
            effective_attempts,
            stop,
        )
    _restore_workspace_snapshot(workspace, best_snapshot)
    restored = dict(best_checked)
    restored["turn_history"] = tested.get("turn_history") or best_checked.get("turn_history")
    if tested.get("repair_attempt_count") is not None:
        restored["repair_attempt_count"] = tested.get("repair_attempt_count")
    return restored, best_checked, best_snapshot, best_rew, flat_rounds, effective_attempts, stop


def _testing_only_task(task: str) -> bool:
    from onecode.kernel.model_guidance import asks_for_new_tests

    return asks_for_new_tests(task)


def _deliver_best_repair(
    workspace: Path,
    current: dict[str, Any],
    best_checked: dict[str, Any],
    best_snapshot: dict[str, str],
) -> dict[str, Any]:
    """Return the higher host score and put that workspace snapshot back."""
    delivered = dict(current)
    best_reward = best_checked.get("host_reward")
    current_reward = current.get("host_reward")
    if isinstance(best_reward, (int, float)) and not isinstance(best_reward, bool):
        worse = (
            not isinstance(current_reward, (int, float))
            or isinstance(current_reward, bool)
            or float(best_reward) > float(current_reward)
        )
        if worse:
            _restore_workspace_snapshot(workspace, best_snapshot)
            delivered = dict(best_checked)
            delivered["host_reward"] = float(best_reward)
    reward = delivered.get("host_reward")
    if isinstance(reward, (int, float)) and not isinstance(reward, bool) and float(reward) >= 1.0 - 1e-9:
        delivered["status"] = "completed"
        delivered["reason"] = None
        delivered["partial"] = False
        return delivered
    if isinstance(reward, (int, float)) and not isinstance(reward, bool):
        delivered["status"] = "completed"
        delivered["partial"] = True
        delivered["verifier_status"] = "partial"
        if not delivered.get("reason"):
            delivered["reason"] = "verifier_failed"
        return delivered
    return delivered


def _build_repair_prompt_context(
    task: str,
    workspace: Path,
    current_checked: dict[str, Any],
    attempt: int,
    run_metadata: dict[str, Any],
    format_error_guidance: str | None,
    stalled_progress: bool,
    posture: str = "patch",
) -> tuple[str, str, int, int]:
    from onecode.kernel.model_guidance import format_verifier_diagnostics, repair_prompt
    failed_status = current_checked.get("iching_status_code") or current_checked.get("task_status_code")
    failed_code = int(failed_status) if failed_status is not None else 32
    if attempt >= 2:
        failed_code = 47
    cooldown_ms = _compute_repair_cooldown(run_metadata, attempt, failed_code, "verifier_failure")
    if cooldown_ms > 0:
        time.sleep(cooldown_ms / 1000.0)
    tails: list[str] = []
    for item in (current_checked.get("verifier_results") or []):
        if not isinstance(item, dict):
            continue
        err = str(item.get("stderr_tail") or "").strip()
        out = str(item.get("stdout_tail") or "").strip()
        diag = format_verifier_diagnostics(out, err)
        if diag:
            tails.append(diag)
        else:
            if err:
                tails.append(err[-600:])
            if out:
                tails.append(out[-600:])
    preview_limit = 20000 if posture == "macro" else None
    prompt = repair_prompt(
        task,
        {**current_checked, "workspace_files": _src_files_for_repair(workspace, preview_limit=preview_limit)},
        workspace=workspace,
    )
    if _testing_only_task(task):
        prompt = prompt.replace(
            "Do not patch any path under tests/.",
            "STRICT: Do NOT touch application source code. Modify tests only.",
        )
        prompt = prompt.replace(
            "Return JSON with patches only. Do not return assets, execution_plan, or no_action. ",
            "Return one new test asset, or patches to that new test file. Do not return execution_plan or no_action. ",
        )
        from onecode.kernel.model_guidance import protected_python_files

        protected = protected_python_files(task)
        if protected:
            prompt += "\nForbidden files: " + ", ".join(protected) + "."
    else:
        prompt += "\nDo not patch any path under tests/. Change the implementation so the existing tests pass."
    if tails and all(t not in prompt for t in tails):
        prompt += "\nVerifier output:\n" + "\n".join(tails)
    if format_error_guidance:
        prompt += f"\n\nCRITICAL FIX FROM PREVIOUS TURN FORMAT ERROR:\n{format_error_guidance}\nYou must output valid JSON with a 'patches' list only."
    if stalled_progress and posture == "micro":
        prompt += (
            "\n\nNOTICE - STALLED MICRO PATCH:\n"
            "The previous repair did not raise the score. "
            "Stay inside the line limit and inspect a different edge: 0, None, empty collections, case, or int versus str."
        )
    elif stalled_progress and posture != "macro":
        prompt += (
            "\n\nNOTICE - STALLED PROGRESS MUTATION DIRECTIVE:\n"
            "The previous repair attempt made NO score progress and failed the exact same checks.\n"
            "Do NOT repeat minor variations of the same logic. Pivot and rethink core assumptions:\n"
            "1. Check scalar and object types: are numbers parsed as int/float instead of strings? Are structured sub-objects preserved as dicts instead of flattened?\n"
            "2. Check duplicate handling: are duplicate records being counted twice or merged incorrectly?\n"
            "3. Check default parameter values, missing edge-case returns, and error type constants.\n"
            "4. Check if a related helper function in another workspace file needs the fix instead."
        )
    if posture == "micro":
        limit = _micro_line_limit(_numeric_reward(current_checked.get("host_reward")))
        prompt += (
            "\n\nMICRO-PATCH ONLY: the current score is at least 0.85. "
            f"Keep every search_block and replace_block within {limit} lines. "
            "Focus on edges: 0, None, empty lists, case folding, and int versus str. "
            "Leave passing behavior in place."
        )
    elif posture == "macro":
        prompt += (
            "\n\nMACRO-REPLAN: the current score is below 0.40. "
            "Replace the whole implementation in one patch. "
            "search_block must be the complete current file and replace_block the rewritten file. "
            "Keep the public function names. Do not edit tests or protected files."
        )
    if _testing_only_task(task):
        prompt += (
            "\n\nCRITICAL: Do not modify implementation files. "
            "Every new assertion must pass against the current implementation. "
            "If the new test fails on unchanged code, fix the test.\n"
            "If the new test file does not exist, return one JSON asset under tests/. "
            'Format: {"task":"modify tests only","assets":[{"path":"tests/<new_test>.py","content":"<complete unittest file>"}]}. '
            "If that file already exists, return patches only for it."
        )
    else:
        prompt += (
            "\n\nCRITICAL: Return valid JSON with patches only. Do NOT include execution_plan or assets.\n"
            "If multiple modifications are needed in the same file, combine them into ONE single patch for that file to prevent patch offset conflicts.\n"
            'Format: {"task":"repair verifier failure","patches":[{"path":"<file>","search_block":"<exact lines>","replace_block":"<fixed lines>"}]}'
        )
    span_id = "model-repair-after-check" if attempt == 1 else f"model-repair-after-check-{attempt}"
    resolved_file = workspace / ".onecode" / "resolved_approvals.json"
    if resolved_file.is_file():
        try:
            resolved_data = json.loads(resolved_file.read_text(encoding="utf-8"))
            for entry in resolved_data:
                res_val = entry.get("resolution")
                if res_val:
                    prompt += f"\n\nEngineer specification resolution: {res_val}."
        except Exception:
            pass
    return prompt, span_id, cooldown_ms, failed_code


def _apply_repair_state_interventions(
    run_metadata: dict[str, Any],
    failed_code: int,
    attempt: int,
    cooldown_ms: int,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from onecode.kernel.model_loop import _record_kernel_fault

    state_gov_mode = resolve_state_governance_mode(failed_code)
    repair_gov_mode = (
        "degraded"
        if attempt >= 2 or run_metadata.get("governance_mode") == "degraded"
        else state_gov_mode
    )
    metadata: dict[str, Any] = {
        **run_metadata,
        "governance_mode": repair_gov_mode,
        "cooldown_pause_ms": cooldown_ms,
    }
    if extra:
        metadata.update(extra)
    try:
        interv = compute_systemic_intervention(failed_code)
        if interv.get("force_wal_checkpoint_sync"):
            metadata["force_wal_checkpoint_sync"] = True
        if interv.get("adaptive_cooldown_ms", 0) > 0:
            metadata["cooldown_pause_ms"] = interv["adaptive_cooldown_ms"]
        if symbolic_telemetry_enabled():
            sb = call_symbolic_profile(IchingKernel, "star_brightness_profile", failed_code)
            sc = call_symbolic_profile(IchingKernel, "systemic_coupling_profile", hexagram_state=failed_code)
            if sb is not None:
                metadata["star_brightness"] = sb
            if sc is not None:
                metadata["systemic_coupling"] = sc
    except (TypeError, ValueError, KeyError, ImportError) as ex:
        _record_kernel_fault("repair_coupling", ex)
    return metadata


def _build_repair_metadata(
    run_metadata: dict[str, Any],
    failed_code: int,
    attempt: int,
    cooldown_ms: int,
) -> dict[str, Any]:
    return _apply_repair_state_interventions(run_metadata, failed_code, attempt, cooldown_ms)


_TURN_BRANCHES = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")


def _seed_turn_history(result: dict[str, Any], modified: list[str] | None = None) -> list[dict[str, Any]]:
    existing = result.get("turn_history")
    if isinstance(existing, list) and existing:
        return existing
    files = modified if modified is not None else _modified_paths_from_result(result)
    return [{
        "turn_id": 1,
        "branch_name": _TURN_BRANCHES[0],
        "modified_files": files,
        "status": result.get("status"),
        "reason": result.get("reason"),
    }]


def _host_detail_from_stdout(stdout: str) -> dict:
    decoder = json.JSONDecoder()
    for index, char in enumerate(stdout):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(stdout[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and isinstance(parsed.get("tests"), list):
            return parsed
    return {}


def apply_sanitized_host_grade(result: dict[str, Any], reward: object, detail: dict) -> dict[str, Any]:
    """Record an external host score without placing the verifier or its expected answers in the workspace."""
    from onecode.kernel.model_guidance import sanitize_host_failure_summary

    updated = dict(result)
    if isinstance(reward, bool) or not isinstance(reward, (int, float)):
        return updated
    score = float(reward)
    updated["host_reward"] = score
    if score >= 1.0 - 1e-9:
        updated["status"] = "completed"
        updated["reason"] = None
        return updated
    summary = sanitize_host_failure_summary(detail if isinstance(detail, dict) else {})
    updated["status"] = "halted"
    updated["reason"] = "verifier_failed"
    updated["verifier_results"] = [
        {
            "id": "host-verifier",
            "status": "failed",
            "reason": "verifier_failed",
            "stdout_tail": summary,
            "stderr_tail": "",
        }
    ]
    return updated


def _apply_external_host_grade(
    result: dict[str, Any],
    workspace: Path,
    run_metadata: dict[str, Any],
) -> dict[str, Any]:
    raw = str(run_metadata.get("host_verifier_path") or "").strip()
    if not raw:
        return result
    path = Path(raw).expanduser()
    try:
        resolved = path.resolve()
        root = workspace.resolve()
    except OSError:
        return result
    if not resolved.is_file() or resolved.is_relative_to(root):
        return result
    from onecode.kernel.verifier import run_host_verifier

    checked, reward = run_host_verifier(workspace, resolved)
    detail = _host_detail_from_stdout(checked.stdout_tail)
    graded = apply_sanitized_host_grade(result, reward, detail)
    if checked.container_id:
        graded["container_id"] = checked.container_id
        graded["container_image"] = checked.container_image
        graded["container_arch"] = checked.container_arch
    return graded


def _contract_has_reason_enum(workspace: Path) -> bool:
    """Check if visible contract documents explicitly enumerate allowed reason slugs."""
    from onecode.kernel.model_guidance import _iter_contract_docs

    docs = _iter_contract_docs(workspace)
    if not docs:
        return False
    combined = "\n\n".join(doc.read_text(encoding="utf-8", errors="ignore") for doc in docs if doc.is_file())
    if not combined:
        return False
    lowered = combined.lower()
    if "reason" not in lowered and "decision" not in lowered:
        return True

    if re.search(r"(?i)(?:allowed|valid|possible|return|reject)?\s*reasons?[:\s]+(?:\n\s*[-*+]\s+[`'\"]?[a-z0-9_-]+[`'\"]?)+", combined):
        return True
    if re.search(r"(?i)\|\s*(?:reason|reason_code|code)\s*\|[^\n]+\|\n\|[-:\s|]+\|\n(?:\|\s*[`'\"]?[a-z0-9_-]+[`'\"]?\s*\|[^\n]+\|\n?)+", combined):
        return True
    if re.search(r"(?i)class\s+\w*Reason\w*\s*\(\s*(?:str,\s*)?Enum\s*\):", combined):
        return True
    if re.search(r"(?i)Literal\[(?:\s*['\"][a-z0-9_-]+['\"]\s*,?)+\]", combined):
        return True
    if re.search(r"(?i)reasons?\s+(?:are|can be|must be|include|one of)[:\s]+(?:\s*[`'\"][a-z0-9_-]+[`'\"]\s*,?)+", combined):
        return True

    return False


def _extract_failing_checks(checked: dict[str, Any]) -> list[str]:
    """Extract failed test names from verifier output or structured results."""
    failures: list[str] = []
    for key in ("failed_tests", "failing_checks", "failures"):
        val = checked.get(key)
        if isinstance(val, list):
            for item in val:
                if isinstance(item, str) and item not in failures:
                    failures.append(item)

    for res in checked.get("verifier_results") or []:
        if not isinstance(res, dict):
            continue
        out = str(res.get("stdout_tail") or "")
        err = str(res.get("stderr_tail") or "")
        for match in re.finditer(r'\{\s*"(?:overall|tests)"', out):
            idx = match.start()
            try:
                candidate, _ = json.JSONDecoder().raw_decode(out[idx:])
                if isinstance(candidate, dict) and "tests" in candidate and isinstance(candidate["tests"], list):
                    for t in candidate["tests"]:
                        if isinstance(t, dict) and not t.get("passed"):
                            name = str(t.get("name") or "")
                            if name and name not in failures:
                                failures.append(name)
            except Exception:
                pass
        for line in out.splitlines() + err.splitlines():
            line = line.strip()
            fail_m = re.match(r"^-\s*\[FAIL\]\s*([a-zA-Z0-9_.:-]+)", line)
            if fail_m:
                name = fail_m.group(1).strip().rstrip(":")
                if name and name not in failures:
                    failures.append(name)
            fail_m2 = re.match(r"^(?:FAIL|ERROR):\s*([a-zA-Z0-9_.:-]+)", line)
            if fail_m2:
                name = fail_m2.group(1).strip().rstrip(":")
                if name and name not in failures:
                    failures.append(name)
    return failures


def _extract_emitted_reasons(workspace: Path, tested: dict[str, Any] | None = None) -> list[str]:
    """Extract model-emitted reason strings from decisions.json, python files, or verifier output."""
    emitted: list[str] = []
    decisions_candidates = [workspace / "decisions.json"]
    for p in sorted(workspace.glob("**/decisions.json")):
        if p not in decisions_candidates:
            decisions_candidates.append(p)
    for path in decisions_candidates:
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                items = data if isinstance(data, list) else data.get("decisions") or data.get("results") or [data]
                if isinstance(items, list):
                    for it in items:
                        if isinstance(it, dict):
                            r = it.get("reason")
                            if isinstance(r, str) and r and r not in emitted:
                                emitted.append(r)
            except Exception:
                pass

    skip_dirs = {".git", ".onecode", "__pycache__", ".venv", "tests"}
    for py_file in sorted(workspace.rglob("*.py")):
        if any(part in skip_dirs for part in py_file.relative_to(workspace).parts):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for m in re.finditer(r'["\']reason["\']\s*:\s*["\']([a-z0-9_]+)["\']', content):
                val = m.group(1).strip()
                if val and val not in {"none", "unknown", "error", "reason", "null"} and val not in emitted:
                    emitted.append(val)
            for m in re.finditer(r'\breason\s*=\s*["\']([a-z0-9_]+)["\']', content):
                val = m.group(1).strip()
                if val and val not in {"none", "unknown", "error", "reason", "null"} and val not in emitted:
                    emitted.append(val)
        except Exception:
            pass

    if tested:
        for res in tested.get("verifier_results") or []:
            if isinstance(res, dict):
                text = str(res.get("stdout_tail") or "") + "\n" + str(res.get("stderr_tail") or "")
                for m in re.finditer(r"AssertionError:\s*['\"]([a-z0-9_]+)['\"]\s*!=", text):
                    val = m.group(1).strip()
                    if val and val not in emitted:
                        emitted.append(val)
    return emitted


def _maybe_open_reason_clarification_approval(
    workspace: Path,
    task: str,
    tested: dict[str, Any],
    current_checked: dict[str, Any],
    best_checked: dict[str, Any],
    attempt: int = 1,
    best_snapshot: dict[str, str] | None = None,
    run_metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """When visible contract lacks reason enum and repair stagnates, open a pending approval."""
    if _contract_has_reason_enum(workspace):
        return None

    failing_checks = _extract_failing_checks(tested) or _extract_failing_checks(current_checked)
    emitted_reasons = _extract_emitted_reasons(workspace, tested)

    lowered_task = task.lower()
    policy_keywords = ("reason", "policy", "eligibility", "eligible", "refund", "coupon", "deny", "decision")
    is_policy_context = (
        any(k in lowered_task for k in policy_keywords)
        or any(any(k in check.lower() for k in policy_keywords) for check in failing_checks)
        or bool(emitted_reasons)
        or (workspace / "decisions.json").is_file()
    )
    if not is_policy_context:
        return None

    from onecode.kernel.cycle_approvals import persist_pending_approval

    best_rew = _numeric_reward(best_checked.get("host_reward"))
    tool_name = "clarify_decision_reason"
    params = {
        "task": task,
        "failing_checks": failing_checks or ["policy_decision_check"],
        "emitted_reasons": emitted_reasons,
        "stalled_reward": best_rew,
        "best_snapshot": best_snapshot or _snapshot_workspace_files(workspace),
        "run_metadata": run_metadata or {},
        "question": "Specification does not enumerate allowed reason codes. Select or specify the expected short code before continuing.",
    }
    return persist_pending_approval(workspace, tool_name, params)


def _handle_repair_budget_stop(
    workspace: Path,
    task: str,
    tested: dict[str, Any],
    current_checked: dict[str, Any],
    best_checked: dict[str, Any],
    best_snapshot: dict[str, str],
    attempt: int,
    run_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    delivered = _deliver_best_repair(workspace, current_checked, best_checked, best_snapshot)
    delivered["repair_attempt_count"] = attempt
    approval = _maybe_open_reason_clarification_approval(
        workspace=workspace,
        task=task,
        tested=tested,
        current_checked=current_checked,
        best_checked=best_checked,
        attempt=attempt,
        best_snapshot=best_snapshot,
        run_metadata=run_metadata,
    )
    if approval is not None:
        delivered["status"] = "halted"
        delivered["reason"] = "approval_required"
        delivered["pending_approval_id"] = approval.get("id")
        delivered["pending"] = {"tool_name": approval.get("tool_name"), "params": approval.get("params")}
        delivered["approval_status"] = approval.get("status", "PENDING_APPROVAL")
        _append_repair_turn(delivered, delivered, "approval_required")
    return delivered


def _select_target_slugs_to_replace(
    emitted_reasons: list[str],
    selected_slug: str,
    failing_checks: list[str] | None = None,
    explicit_target: str | None = None,
) -> list[str]:
    """Select the specific candidate reason slug(s) to replace rather than replacing all."""
    if explicit_target and explicit_target in emitted_reasons:
        return [explicit_target]
    if explicit_target:
        return [explicit_target]
    if not emitted_reasons:
        return []
    if len(emitted_reasons) == 1:
        return list(emitted_reasons)

    def _tokens(s: str) -> set[str]:
        return {w.lower() for w in re.findall(r"[a-zA-Z0-9]+", s)}

    slug_tokens = _tokens(selected_slug)
    check_tokens: set[str] = set()
    for c in (failing_checks or []):
        check_tokens.update(_tokens(c))

    scored: list[tuple[int, str]] = []
    for cand in emitted_reasons:
        cand_tokens = _tokens(cand)
        score = len(cand_tokens & slug_tokens) * 3 + len(cand_tokens & check_tokens) * 2
        scored.append((score, cand))

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_cand = scored[0]
    if best_score > 0:
        return [best_cand]
    return list(emitted_reasons)


def apply_approved_slug_repair(
    workspace: Path,
    approval_params: dict[str, Any],
    selected_slug: str,
) -> dict[str, Any]:
    """Resume from highest-scoring snapshot, apply engineer-provided reason short code, and re-grade."""
    if not selected_slug:
        return {"status": "unchanged", "reason": "no_slug_provided"}

    best_snapshot = approval_params.get("best_snapshot")
    if isinstance(best_snapshot, dict) and best_snapshot:
        _restore_workspace_snapshot(workspace, best_snapshot)

    emitted_reasons = approval_params.get("emitted_reasons") or _extract_emitted_reasons(workspace)
    explicit_target = approval_params.get("target_slug") or approval_params.get("replace_slug")
    failing_checks = approval_params.get("failing_checks") or []
    targets_to_replace = _select_target_slugs_to_replace(
        emitted_reasons,
        selected_slug,
        failing_checks=failing_checks,
        explicit_target=explicit_target,
    )
    skip_dirs = {".git", ".onecode", "__pycache__", ".venv", "tests"}
    modified_paths: list[str] = []

    for py_file in sorted(workspace.rglob("*.py")):
        if any(part in skip_dirs for part in py_file.relative_to(workspace).parts):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
            orig = content
            for old_reason in targets_to_replace:
                if old_reason and old_reason in content:
                    content = re.sub(
                        r"([\'\"])" + re.escape(old_reason) + r"\1",
                        r"\g<1>" + selected_slug + r"\g<1>",
                        content,
                    )
            if content != orig:
                py_file.write_text(content, encoding="utf-8")
                modified_paths.append(py_file.relative_to(workspace).as_posix())
        except (OSError, UnicodeDecodeError):
            pass

    for json_file in sorted(workspace.glob("**/decisions.json")):
        try:
            content = json_file.read_text(encoding="utf-8")
            orig = content
            for old_reason in targets_to_replace:
                if old_reason and old_reason in content:
                    content = re.sub(
                        r"([\'\"])" + re.escape(old_reason) + r"\1",
                        r"\g<1>" + selected_slug + r"\g<1>",
                        content,
                    )
            if content != orig:
                json_file.write_text(content, encoding="utf-8")
                modified_paths.append(json_file.relative_to(workspace).as_posix())
        except (OSError, UnicodeDecodeError):
            pass

    run_metadata = dict(approval_params.get("run_metadata") or {})
    if not run_metadata.get("host_verifier_path"):
        raw_verifier = run_metadata.get("host_verifier") or _resolve_host_verifier_path(workspace)
        if raw_verifier:
            run_metadata["host_verifier_path"] = str(raw_verifier)

    base_result: dict[str, Any] = {
        "status": "completed",
        "reason": None,
        "host_reward": approval_params.get("stalled_reward", 0.0),
        "modified_paths": modified_paths,
    }
    regraded = _with_sandbox_tests(base_result, workspace, run_metadata.get("sandbox_config"))
    regraded = _apply_external_host_grade(regraded, workspace, run_metadata)
    new_reward = _numeric_reward(regraded.get("host_reward"))
    if new_reward is not None and new_reward >= 1.0 - 1e-9:
        regraded["status"] = "completed"
        regraded["reason"] = None
        regraded["partial"] = False
    elif new_reward is not None:
        regraded["status"] = "completed"
        regraded["partial"] = True
        regraded["reason"] = "verifier_failed" if new_reward < 1.0 else None

    return regraded


def _reset_macro_posture_if_needed(
    task: str,
    workspace: Path,
    current_checked: dict[str, Any],
    initial_snapshot: dict[str, str],
    run_metadata: dict[str, Any],
) -> tuple[dict[str, Any], str, bool]:
    if _snapshot_workspace_files(workspace) != initial_snapshot:
        _restore_workspace_snapshot(workspace, initial_snapshot)
        regraded = _apply_external_host_grade(dict(current_checked), workspace, run_metadata)
        regraded["turn_history"] = current_checked.get("turn_history")
        if regraded.get("reason") != "verifier_failed":
            return regraded, "", True
        posture = _task_repair_posture(task, _numeric_reward(regraded.get("host_reward")))
        return regraded, posture, False
    return current_checked, "macro", False


def _finish_verified_task(
    result: dict[str, Any],
    task: str,
    workspace: Path,
    sandbox_config: Any | None,
    max_repair_attempts: int,
    provider: Any,
    model_context: Any,
    trace_path: Path,
    provider_config: Any,
    resolved_model: str,
    http_timeout_seconds: float,
    planning_context: dict[str, Any],
    run_id: str | None,
    resume_from_run_id: str | None,
    run_metadata: dict[str, Any],
    require_explicit_approval: bool,
    execution_approval: Callable[[ExecutionStep], bool] | None,
    on_turn: Callable[[dict[str, Any]], None] | None,
) -> dict[str, Any]:
    from onecode.kernel.model_planning import execute_model_plan, failed_model_result, traced_provider_plan_retrying
    modified = _modified_paths_from_result(result)
    _generate_missing_artifacts(task, workspace, modified)
    checked = _with_sandbox_tests(result, workspace, sandbox_config)
    checked = _apply_external_host_grade(checked, workspace, run_metadata)
    has_testable_verifier = sandbox_config is not None or bool(str(run_metadata.get("host_verifier_path") or "").strip())
    if checked.get("reason") != "verifier_failed" or max_repair_attempts <= 0 or not has_testable_verifier:
        return checked
    current_checked = dict(checked)
    current_result = dict(result)
    best_checked = dict(checked)
    best_snapshot = _snapshot_workspace_files(workspace)
    initial_snapshot = dict(best_snapshot)
    initial_history = _seed_turn_history(checked, modified)
    current_checked["turn_history"] = initial_history
    current_result["turn_history"] = initial_history
    bureau_budget = run_metadata.get("bureau_turn_budget", max_repair_attempts)
    effective_attempts = min(max_repair_attempts, bureau_budget) if max_repair_attempts > 0 else 0
    format_error_guidance: str | None = None
    prev_reward = _numeric_reward(checked.get("host_reward"))
    flat_rounds = 0
    macro_done = False

    attempt = 1
    while attempt <= effective_attempts:
        posture = _task_repair_posture(task, _numeric_reward(current_checked.get("host_reward")))
        if posture == "macro" and not macro_done:
            current_checked, posture, early_exit = _reset_macro_posture_if_needed(
                task, workspace, current_checked, initial_snapshot, run_metadata
            )
            if early_exit:
                return current_checked
            current_result = dict(current_checked)
            macro_done = True
        prompt, span_id, cooldown_ms, failed_code = _build_repair_prompt_context(
            task=task,
            workspace=workspace,
            current_checked=current_checked,
            attempt=attempt,
            run_metadata=run_metadata,
            format_error_guidance=format_error_guidance,
            stalled_progress=flat_rounds >= 1,
            posture=posture,
        )
        plan, failure = traced_provider_plan_retrying(
            provider=provider,
            task=prompt,
            model_context=model_context,
            trace_path=trace_path,
            provider_config=provider_config,
            resolved_model=resolved_model,
            http_timeout_seconds=http_timeout_seconds,
            planning_context=planning_context,
            span_id=span_id,
        )
        if failure is not None:
            failure_kind = failure.get("failure_kind")
            if attempt < effective_attempts and failure_kind in {"invalid_model_plan", "no_actionable_plan"}:
                format_error_guidance = f"Previous turn failed with format error ({failure_kind}): {failure.get('detail') or 'Output was not a valid patch plan'}."
                _append_repair_turn(current_checked, current_result, str(failure_kind))
                attempt += 1
                continue
            failed_model = _enrich_failed_model_with_repair_state(
                failed_model_result(model_context, failure),
                current_checked,
                attempt,
            )
            best_reward = _numeric_reward(best_checked.get("host_reward"))
            failed_reward = _numeric_reward(failed_model.get("host_reward"))
            if best_reward is not None and (failed_reward is None or best_reward > failed_reward):
                return _deliver_best_repair(workspace, failed_model, best_checked, best_snapshot)
            return failed_model
        if plan is None:
            failed_model = failed_model_result(model_context, failure or {"failure_kind": "no_actionable_plan"})
            return _enrich_failed_model_with_repair_state(failed_model, current_checked, attempt)
        plan = synthesize_single_asset_repair(plan, workspace)
        if plan.patches and plan.execution_steps:
            plan = ModelPlan(task=plan.task, patches=plan.patches, no_action_reason=plan.no_action_reason)
        limit = _micro_line_limit(_numeric_reward(current_checked.get("host_reward")))
        safety_err, guidance = _validate_repair_plan_safety(plan, task, micro_patch=posture == "micro", micro_line_limit=limit)
        if safety_err is not None:
            if attempt < effective_attempts:
                format_error_guidance = guidance
                _append_repair_turn(current_checked, current_result, safety_err)
                attempt += 1
                continue
            final_err = "repair_plan_must_use_patches_only" if safety_err == "repair_plan_cannot_modify_tests" else safety_err
            rejected = repair_rejected_result(current_checked, run_id, final_err, repair_attempt_count=attempt)
            return _deliver_best_repair(workspace, rejected, best_checked, best_snapshot)
        repair_metadata = _build_repair_metadata(run_metadata, failed_code, attempt, cooldown_ms)
        repaired = execute_model_plan(
            plan,
            workspace=workspace,
            http_timeout_seconds=http_timeout_seconds,
            run_id=run_id,
            resume_from_run_id=resume_from_run_id,
            run_metadata=repair_metadata,
            require_explicit_approval=require_explicit_approval,
            approval_callback=execution_approval,
            on_turn=on_turn,
        )
        merged = merge_repair_result(current_result, repaired, repair_attempt_count=attempt)
        if repaired.get("status") != "completed":
            _restore_workspace_snapshot(workspace, best_snapshot)
            _append_repair_turn(current_checked, current_result, str(repaired.get("reason") or "repair_execution_failed"))
            attempt += 1
            continue
        tested = _with_sandbox_tests(merged, workspace, sandbox_config)
        tested = _apply_external_host_grade(tested, workspace, run_metadata)
        if tested.get("reason") != "verifier_failed":
            return tested
        (
            current_checked,
            best_checked,
            best_snapshot,
            prev_reward,
            flat_rounds,
            effective_attempts,
            stop,
        ) = _apply_scored_repair(
            workspace,
            tested,
            best_checked,
            best_snapshot,
            prev_reward,
            flat_rounds,
            effective_attempts,
        )
        current_result = dict(current_checked)
        if stop:
            return _handle_repair_budget_stop(
                workspace, task, tested, current_checked, best_checked, best_snapshot, attempt, run_metadata
            )
        attempt += 1
    delivered = _deliver_best_repair(workspace, current_checked, best_checked, best_snapshot)
    delivered["repair_attempt_count"] = max(int(delivered.get("repair_attempt_count") or 0), attempt - 1)
    return delivered


def _resolve_host_verifier_path(workspace: Path) -> str:
    """Read a hidden-verifier pointer. The solve loop must not grade through it."""
    marker = workspace / ".onecode_host_verifier"
    if marker.is_file():
        try:
            val = marker.read_text(encoding="utf-8").strip()
            if val:
                return val
        except OSError:
            pass
    return os.environ.get("ONECODE_HOST_VERIFIER", "").strip()


def _with_sandbox_tests(result: dict[str, Any], workspace: Path, sandbox_config: Any | None) -> dict[str, Any]:
    if result.get("status") != "completed":
        return result
    from onecode.kernel.preset_tests import preset_test_hashes
    from onecode.kernel.run_inspection import apply_verifier_evidence
    from onecode.kernel.verifier import VerifierSpec, run_verifier

    if sandbox_config is None:
        return result

    if not (workspace / "tests").is_dir():
        return result

    spec = VerifierSpec(
        id="python-unittest",
        command=["python3", "-m", "unittest", "discover", "-s", "tests"],
        cwd=".",
        timeout_ms=max(1000, int(sandbox_config.timeout_seconds * 1000)),
    )

    checked = run_verifier(workspace, spec, sandbox_config=sandbox_config)
    verified = {**result, "preset_test_hashes": preset_test_hashes(workspace)} if checked.status == "passed" else result
    return apply_verifier_evidence(verified, workspace, [checked])


def _plan_user_rejected_result(plan: ModelPlan, run_id: str | None, provider_config: Any, resolved_model: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "status": "cancelled",
        "reason": "user_rejected_diff",
        "partial": False,
        "requested_count": len(plan.assets),
        "completed_count": 0,
        "skipped_count": 0,
        "failed_count": 0,
        "assets": [],
        "model_provider": "openai" if provider_config.env_key == "OPENAI_API_KEY" else provider_config.provider_kind,
        "model": resolved_model,
        "model_plan_task": plan.task,
        "model_plan_asset_count": len(plan.assets),
        "model_plan_patch_count": len(plan.patches),
        "model_plan_execution_step_count": len(plan.execution_steps),
    }


def _enrich_bureau_and_brightness_metadata(workspace: Path, run_metadata: dict[str, Any]) -> None:
    from onecode.kernel.model_guidance import resolve_task_bureau
    from onecode.kernel.model_loop import _record_kernel_fault
    bureau = resolve_task_bureau(workspace)
    run_metadata["task_bureau"] = bureau["bureau_name"]
    run_metadata["task_scale"] = bureau["scale"]
    run_metadata["bureau_turn_budget"] = bureau["turn_budget"]
    run_metadata["bureau_patch_strategy"] = bureau["patch_strategy"]
    status_code = run_metadata.get("iching_status_code")
    if status_code is not None:
        try:
            code_int = int(status_code)
            bureau_id = bureau.get("bureau", 2)
            ming_branch = (code_int & 0b111) % 12
            year_branch = ((code_int >> 3) & 0b111) % 12
            gain_multiplier = compute_cycle_gain_multiplier(
                bureau=bureau_id,
                ming_branch=ming_branch,
                year_branch=year_branch,
            )
            intervention = compute_systemic_intervention(code_int)

            if gain_multiplier > 1.0:
                base_budget = run_metadata["bureau_turn_budget"]
                run_metadata["bureau_turn_budget"] = int(base_budget * gain_multiplier)

            damping_factor = intervention.get("turn_budget_damping_factor", 1.0)
            if damping_factor < 1.0:
                curr_budget = run_metadata["bureau_turn_budget"]
                run_metadata["bureau_turn_budget"] = max(1, int(curr_budget * damping_factor))

            gov_mode = resolve_state_governance_mode(code_int)
            if intervention.get("execution_mode") == "degraded":
                gov_mode = "degraded"
            if intervention.get("force_wal_checkpoint_sync"):
                run_metadata["force_wal_checkpoint_sync"] = True
            if intervention.get("adaptive_cooldown_ms", 0) > 0:
                run_metadata["cooldown_pause_ms"] = intervention["adaptive_cooldown_ms"]
            run_metadata.setdefault("governance_mode", gov_mode)

            if symbolic_telemetry_enabled():
                optional_fields = {
                    "star_brightness": call_symbolic_profile(IchingKernel, "star_brightness_profile", code_int),
                    "pattern_breaking": call_symbolic_profile(IchingKernel, "pattern_breaking_profile", code_int),
                    "tri_level_time_flow": call_symbolic_profile(
                        IchingKernel,
                        "tri_level_time_flow_profile",
                        bureau=bureau_id,
                        ming_branch=ming_branch,
                        year_branch=year_branch,
                    ),
                    "palace_star_duality": call_symbolic_profile(
                        IchingKernel,
                        "palace_star_duality_profile",
                        active_palace=code_int % 12,
                    ),
                    "systemic_coupling": call_symbolic_profile(
                        IchingKernel,
                        "systemic_coupling_profile",
                        hexagram_state=code_int,
                    ),
                }
                for key, value in optional_fields.items():
                    if value is not None:
                        run_metadata[key] = value
        except (TypeError, ValueError, KeyError, ImportError) as ex:
            _record_kernel_fault("bureau_profile", ex)


def _validate_repair_plan_safety(
    repair_plan: ModelPlan,
    task: str,
    *,
    micro_patch: bool = False,
    micro_line_limit: int = 40,
) -> tuple[str | None, str | None]:
    from onecode.kernel.model_guidance import asks_for_new_tests, protected_python_files, required_python_files
    is_testing_task = asks_for_new_tests(task) or any(_is_test_path(p) for p in required_python_files(task))
    if is_testing_task and _is_new_test_asset_plan(repair_plan):
        return None, None
    if not is_patch_only_repair_plan(repair_plan):
        return (
            "repair_plan_must_use_patches_only",
            "repair_plan_must_use_patches_only: return valid JSON containing 'patches' only (do NOT return assets or execution_plan).",
        )
    if micro_patch and _micro_patch_too_wide(repair_plan, micro_line_limit):
        return (
            "repair_plan_exceeds_micro_patch",
            f"repair_plan_exceeds_micro_patch: the score is already high. Keep every patch within {micro_line_limit} lines.",
        )
    if not is_testing_task and any(_is_test_path(p.path) for p in repair_plan.patches):
        return (
            "repair_plan_cannot_modify_tests",
            "repair_plan_cannot_modify_tests: modifying paths under tests/ is forbidden. Patch implementation files only.",
        )
    protected_files = set(protected_python_files(task))
    if any(
        (p.path in protected_files or Path(p.path).name in protected_files)
        for p in repair_plan.patches
    ):
        return (
            "repair_plan_cannot_modify_protected_files",
            f"repair_plan_cannot_modify_protected_files: modifying protected files ({', '.join(protected_files)}) is forbidden.",
        )
    return None, None


def _run_model_task_repair_loop(
    result: dict[str, Any],
    task: str,
    workspace: Path,
    run_metadata: dict[str, Any],
    max_repair_attempts: int,
    active_provider: Any,
    model_context: Any,
    trace_path: Path,
    provider_config: Any,
    resolved_model: str,
    http_timeout_seconds: float,
    planning_context: dict[str, Any],
    run_id: str | None,
    resume_from_run_id: str | None,
    require_explicit_approval: bool,
    execution_approval: Callable[[ExecutionStep], bool] | None,
    on_turn: Callable[[dict[str, Any]], None] | None,
    sandbox_config: Any | None,
) -> dict[str, Any]:
    from onecode.kernel.model_guidance import repair_prompt
    from onecode.kernel.model_planning import execute_model_plan, failed_model_result, traced_provider_plan
    failed_result = dict(result)
    failed_result["turn_history"] = _seed_turn_history(failed_result)
    bureau_budget = run_metadata.get("bureau_turn_budget", max_repair_attempts)
    effective_attempts = min(max_repair_attempts, bureau_budget) if max_repair_attempts > 0 else 0
    format_error_guidance: str | None = None
    for attempt in range(1, effective_attempts + 1):
        failed_status = failed_result.get("iching_status_code") or failed_result.get("task_status_code")
        failed_code = int(failed_status) if failed_status is not None else 32
        if attempt >= 2:
            failed_code = 47
        scenario = "verifier_failure" if failed_result.get("status") == "verifier_failed" else "provider_failure"
        cooldown_ms = _compute_repair_cooldown(run_metadata, attempt, failed_code, scenario)
        if cooldown_ms > 0:
            time.sleep(cooldown_ms / 1000.0)
        repair_task_prompt = repair_prompt(
            task,
            {**failed_result, "workspace_files": _src_files_for_repair(workspace)},
            workspace=workspace,
        )
        if format_error_guidance:
            repair_task_prompt += f"\n\nCRITICAL FIX FROM PREVIOUS TURN FORMAT ERROR:\n{format_error_guidance}\nYou must output valid JSON with a 'patches' list only."
        repair_plan, failure = traced_provider_plan(
            provider=active_provider,
            task=repair_task_prompt,
            model_context=model_context,
            trace_path=trace_path,
            provider_config=provider_config,
            resolved_model=resolved_model,
            http_timeout_seconds=http_timeout_seconds,
            planning_context=planning_context,
            span_id=f"model-repair-{attempt}",
        )
        if failure is not None:
            failure_kind = failure.get("failure_kind")
            if attempt < effective_attempts and failure_kind in {"invalid_model_plan", "no_actionable_plan"}:
                format_error_guidance = f"Previous turn failed with format error ({failure_kind}): {failure.get('detail') or 'Output was not a valid patch plan'}."
                hist = list(failed_result.get("turn_history") or [])
                hist.append({
                    "turn_id": len(hist) + 1,
                    "branch_name": _TURN_BRANCHES[len(hist) % len(_TURN_BRANCHES)],
                    "status": "halted",
                    "reason": failure_kind,
                    "modified_files": [],
                })
                failed_result = dict(failed_result)
                failed_result["turn_history"] = hist
                continue
            failed_model = failed_model_result(model_context, failure)
            return _enrich_failed_model_with_repair_state(failed_model, failed_result, attempt)
        assert repair_plan is not None
        repair_plan = synthesize_single_asset_repair(repair_plan, workspace)
        safety_err, guidance = _validate_repair_plan_safety(repair_plan, task)
        if safety_err is not None:
            if attempt < effective_attempts:
                format_error_guidance = guidance
                hist = list(failed_result.get("turn_history") or [])
                hist.append({
                    "turn_id": len(hist) + 1,
                    "branch_name": _TURN_BRANCHES[len(hist) % len(_TURN_BRANCHES)],
                    "status": "halted",
                    "reason": safety_err,
                    "modified_files": [],
                })
                failed_result = dict(failed_result)
                failed_result["turn_history"] = hist
                continue
            return repair_rejected_result(
                failed_result,
                run_id,
                safety_err,
                repair_attempt_count=attempt,
            )
        repair_metadata = _apply_repair_state_interventions(
            run_metadata,
            failed_code,
            attempt,
            cooldown_ms,
            extra={
                "model_plan_task": repair_plan.task,
                "model_plan_asset_count": len(repair_plan.assets),
                "model_plan_patch_count": len(repair_plan.patches),
                "model_plan_execution_step_count": len(repair_plan.execution_steps),
                "repair_of_run_id": run_id,
            },
        )
        repair_result = execute_model_plan(
            repair_plan,
            workspace=workspace,
            http_timeout_seconds=http_timeout_seconds,
            run_id=run_id,
            resume_from_run_id=resume_from_run_id,
            run_metadata=repair_metadata,
            require_explicit_approval=require_explicit_approval,
            approval_callback=execution_approval,
            on_turn=on_turn,
        )
        merged = merge_repair_result(failed_result, repair_result, repair_attempt_count=attempt)
        if repair_result.get("status") == "completed":
            return _with_sandbox_tests(merged, workspace, sandbox_config)
        has_testable_verifier = sandbox_config is not None
        if has_testable_verifier and (repair_result.get("completed_count", 0) > 0 or _modified_paths_from_result(repair_result)):
            provisional = dict(merged)
            provisional["status"] = "completed"
            provisional["reason"] = None
            verified = _with_sandbox_tests(provisional, workspace, sandbox_config)
            if verified.get("status") == "completed" and verified.get("reason") is None:
                verified["repaired"] = True
                return verified
        failed_result = merged
    has_testable_verifier = sandbox_config is not None
    if has_testable_verifier and failed_result.get("status") != "completed":
        provisional = dict(failed_result)
        provisional["status"] = "completed"
        provisional["reason"] = None
        verified = _with_sandbox_tests(provisional, workspace, sandbox_config)
        if verified.get("status") == "completed" and verified.get("reason") is None:
            verified["repaired"] = True
            return verified
        for key in ("host_reward", "container_id", "container_image", "container_arch"):
            if key in verified and key not in failed_result:
                failed_result[key] = verified[key]
    return failed_result


