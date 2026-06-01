from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from onecode.kernel.approval import ApprovalDecision, write_approval_decision
from onecode.kernel.finalization import finalize_run_event
from onecode.kernel.inspection import (
    read_json,
    validate_checkpoint_evidence,
    validate_ledger_counts,
    validate_status_document,
)
from onecode.kernel.path_guard import PathGuard
from onecode.kernel.patching import PatchIntent, commit_patch
from onecode.kernel.runner import run_task
from onecode.kernel.sandbox import SandboxConfig, build_docker_command
from onecode.kernel.shell_projection import attach_shell_projection
from onecode.kernel.trace import TraceEvent, write_trace_event


@dataclass(frozen=True)
class BenchmarkTask:
    id: str
    prompt: str
    expected_status: str
    assertions: list[dict[str, Any]]
    mode: str = "definition"
    input: dict[str, Any] | None = None


@dataclass(frozen=True)
class BenchmarkScore:
    task_id: str
    passed: bool
    failures: list[str]
    hallucination_failure: bool = False
    asset_complete: bool = True
    evidence_complete: bool = True


def load_benchmark_task(path: Path) -> BenchmarkTask:
    payload = json.loads(path.read_text(encoding="utf-8"))
    for key in ("id", "prompt", "expected_status"):
        if not isinstance(payload.get(key), str) or not payload[key].strip():
            raise ValueError(f"benchmark task missing {key}: {path}")
    assertions = payload.get("assertions", [])
    if not isinstance(assertions, list):
        raise ValueError(f"benchmark assertions must be a list: {path}")
    return BenchmarkTask(
        id=payload["id"],
        prompt=payload["prompt"],
        expected_status=payload["expected_status"],
        assertions=assertions,
        mode=payload.get("mode", "definition") if isinstance(payload.get("mode", "definition"), str) else "definition",
        input=payload.get("input") if isinstance(payload.get("input"), dict) else None,
    )


def load_benchmark_tasks(directory: Path) -> list[BenchmarkTask]:
    if not directory.exists() or not directory.is_dir():
        raise ValueError(f"benchmark task directory does not exist: {directory}")
    return [load_benchmark_task(path) for path in sorted(directory.glob("*.json"))]


def score_benchmark_result(
    task: BenchmarkTask,
    result: dict[str, Any],
    workspace: Path,
) -> BenchmarkScore:
    failures: list[str] = []
    asset_complete = True
    evidence_failures = evidence_completeness_failures(result)
    evidence_complete = not evidence_failures
    hallucination_failure = False
    if result.get("status") != task.expected_status:
        failures.append(
            f"expected status {task.expected_status}, got {result.get('status')}"
        )
        hallucination_failure = True
    for assertion in task.assertions:
        assertion_type = assertion.get("type")
        rel_path = assertion.get("path")
        if assertion_type == "file_exists":
            if not isinstance(rel_path, str) or not (workspace / rel_path).exists():
                failures.append(f"missing expected file: {rel_path}")
                asset_complete = False
        elif assertion_type == "file_absent":
            if isinstance(rel_path, str) and (workspace / rel_path).exists():
                failures.append(f"unexpected file exists: {rel_path}")
                hallucination_failure = True
        elif assertion_type == "no_hallucination":
            if result.get("status") not in {task.expected_status, "completed", "halted", "denied", "skipped"}:
                failures.append("unexpected hallucination-like status")
                hallucination_failure = True
        elif assertion_type == "evidence_complete":
            if evidence_failures:
                failures.extend(evidence_failures)
        else:
            failures.append(f"unknown assertion type: {assertion_type}")
    return BenchmarkScore(
        task_id=task.id,
        passed=not failures,
        failures=failures,
        hallucination_failure=hallucination_failure,
        asset_complete=asset_complete,
        evidence_complete=evidence_complete,
    )


def evidence_completeness_failures(result: dict[str, Any]) -> list[str]:
    if result.get("evidence_mode") == "wal":
        wal_path_value = result.get("wal_path")
        if isinstance(wal_path_value, str) and Path(wal_path_value).exists():
            return []
        return ["missing wal evidence"]

    failures: list[str] = []
    ledger_path_value = result.get("ledger_path")
    manifest_path_value = result.get("manifest_path")
    if not isinstance(ledger_path_value, str) or not Path(ledger_path_value).exists():
        failures.append("missing ledger evidence")
    if not isinstance(manifest_path_value, str) or not Path(manifest_path_value).exists():
        failures.append("missing manifest evidence")
    if failures:
        return failures

    ledger_path = Path(ledger_path_value)
    manifest_path = Path(manifest_path_value)
    ledger, corrupt_ledger_path, corrupt_ledger_reason = read_json(ledger_path)
    if corrupt_ledger_path is not None or ledger is None:
        return [f"invalid ledger evidence: {corrupt_ledger_reason}"]
    manifest, corrupt_manifest_path, corrupt_manifest_reason = read_json(manifest_path)
    if corrupt_manifest_path is not None or manifest is None:
        return [f"invalid manifest evidence: {corrupt_manifest_reason}"]

    for document, path in ((ledger, ledger_path), (manifest, manifest_path)):
        invalid_path, invalid_reason = validate_status_document(document, path)
        if invalid_path is not None:
            failures.append(f"invalid status evidence: {invalid_reason}")
    invalid_path, invalid_reason = validate_ledger_counts(ledger, ledger_path)
    if invalid_path is not None:
        failures.append(f"invalid ledger counts: {invalid_reason}")
    invalid_path, invalid_reason = validate_checkpoint_evidence(
        list(manifest.get("checkpoints", [])),
        manifest_path,
    )
    if invalid_path is not None:
        failures.append(f"invalid checkpoint evidence: {invalid_reason}")
    return failures


def run_benchmark_task(task: BenchmarkTask, workspace: Path) -> tuple[dict[str, Any], BenchmarkScore]:
    if task.mode == "trace":
        trace_path = workspace / ".onecode" / "trace.jsonl"
        write_trace_event(
            trace_path,
            TraceEvent(
                trace_id=f"benchmark-{task.id}",
                run_id=f"benchmark-{task.id}",
                span_id="benchmark",
                parent_span_id=None,
                event_type="run_started",
                status="completed",
                payload={"task_id": task.id},
            ),
        )
        result = finalize_run_event(
            task=task.prompt,
            workspace=workspace,
            run_id=f"benchmark-{task.id}",
            intent_type="trace",
            status="completed",
            payload={"trace_path": str(trace_path)},
        )
        return result, score_benchmark_result(task, result, workspace)

    if task.mode == "approval":
        approvals_path = workspace / ".onecode" / "approvals.jsonl"
        write_approval_decision(
            approvals_path,
            ApprovalDecision(
                run_id=f"benchmark-{task.id}",
                decision_id="benchmark-decision",
                action="approve",
                reason="benchmark approval record",
            ),
        )
        result = finalize_run_event(
            task=task.prompt,
            workspace=workspace,
            run_id=f"benchmark-{task.id}",
            intent_type="approval",
            status="completed",
            payload={"approvals_path": str(approvals_path)},
        )
        return result, score_benchmark_result(task, result, workspace)

    if task.mode == "sandbox":
        command = build_docker_command(SandboxConfig(workspace=workspace), ["python", "-V"])
        result = finalize_run_event(
            task=task.prompt,
            workspace=workspace,
            run_id=f"benchmark-{task.id}",
            intent_type="sandbox",
            status="completed",
            payload={"sandbox_command": command},
        )
        return result, score_benchmark_result(task, result, workspace)

    if task.mode != "rule":
        result = {
            "run_id": None,
            "status": "skipped",
            "reason": "benchmark_task_mode_not_executable",
        }
        return result, BenchmarkScore(
            task_id=task.id,
            passed=False,
            failures=[f"unsupported executable benchmark mode: {task.mode}"],
        )

    task_input = task.input or {}
    for file_entry in task_input.get("files", []):
        if not isinstance(file_entry, dict):
            continue
        path = file_entry.get("path")
        content = file_entry.get("content")
        if isinstance(path, str) and isinstance(content, str):
            PathGuard.write_text(workspace, path, content)
    result = run_task(
        task.prompt,
        workspace=workspace,
        run_id=f"benchmark-{task.id}",
        write_path=task_input.get("write_path"),
        write_content=task_input.get("write_content"),
        intent_type=task_input.get("intent_type", "noop"),
        command=task_input.get("command"),
        patch_path=task_input.get("patch_path"),
        search_block=task_input.get("search_block"),
        replace_block=task_input.get("replace_block"),
        write_texts=task_input.get("write_texts"),
        simulated_action_seconds=float(task_input.get("simulated_action_seconds", 0)),
        http_timeout_seconds=float(task_input.get("http_timeout_seconds", 60)),
        completed_evidence_mode=task_input.get("completed_evidence_mode", "wal"),
        evidence_durability=task_input.get("evidence_durability", "relaxed"),
    )
    return result, score_benchmark_result(task, result, workspace)


def run_baseline_benchmark_task(task: BenchmarkTask, workspace: Path) -> tuple[dict[str, Any], BenchmarkScore]:
    task_input = task.input or {}
    for file_entry in task_input.get("files", []):
        if not isinstance(file_entry, dict):
            continue
        path = file_entry.get("path")
        content = file_entry.get("content")
        if isinstance(path, str) and isinstance(content, str):
            PathGuard.write_text(workspace, path, content)

    result: dict[str, Any] = {
        "run_id": f"baseline-{task.id}",
        "status": "completed",
        "runner": "baseline",
    }
    if task.mode != "rule":
        result["status"] = "skipped"
        result["reason"] = "baseline_only_supports_rule_mode"
        return result, score_benchmark_result(task, result, workspace)

    write_path = task_input.get("write_path")
    write_content = task_input.get("write_content")
    write_texts = task_input.get("write_texts")
    patch_path = task_input.get("patch_path")
    search_block = task_input.get("search_block")
    replace_block = task_input.get("replace_block")

    try:
        if isinstance(write_texts, list):
            for item in write_texts:
                if not isinstance(item, str):
                    continue
                path, separator, content = item.partition("=")
                if separator:
                    PathGuard.write_text(workspace, path, content)
        elif isinstance(write_path, str) and isinstance(write_content, str):
            PathGuard.write_text(workspace, write_path, write_content)
        elif all(isinstance(value, str) for value in (patch_path, search_block, replace_block)):
            commit_patch(
                workspace,
                PatchIntent(
                    path=patch_path,
                    search_block=search_block,
                    replace_block=replace_block,
                ),
            )
        elif task_input.get("intent_type") in {"bash_execution", "teleport_asset"}:
            result["status"] = "completed"
    except (ValueError, OSError) as exc:
        result["status"] = "failed"
        result["reason"] = str(exc)

    return result, score_benchmark_result(task, result, workspace)


def run_benchmark_tasks(
    tasks: list[BenchmarkTask],
    workspace_root: Path | None = None,
    report_path: Path | None = None,
) -> dict[str, Any]:
    if workspace_root is None:
        workspace_root = Path(tempfile.mkdtemp(prefix="onecode-benchmark-"))
    report = run_benchmark_tasks_with_runner(
        tasks,
        workspace_root=workspace_root,
        runner=run_benchmark_task,
    )
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def compare_benchmark_tasks(
    tasks: list[BenchmarkTask],
    workspace_root: Path | None = None,
    report_path: Path | None = None,
) -> dict[str, Any]:
    if workspace_root is None:
        workspace_root = Path(tempfile.mkdtemp(prefix="onecode-benchmark-ab-"))
    workspace_root.mkdir(parents=True, exist_ok=True)

    baseline = run_benchmark_tasks_with_runner(
        tasks,
        workspace_root=workspace_root / "baseline",
        runner=run_baseline_benchmark_task,
    )
    onecode = run_benchmark_tasks_with_runner(
        tasks,
        workspace_root=workspace_root / "onecode",
        runner=run_benchmark_task,
    )
    baseline_metrics = baseline["metrics"]
    onecode_metrics = onecode["metrics"]
    report = {
        "status": "completed" if onecode["status"] == "completed" else "failed",
        "task_count": len(tasks),
        "arms": {
            "baseline": baseline,
            "onecode": onecode,
        },
        "delta": {
            "pass_at_1": onecode_metrics["pass_at_1"] - baseline_metrics["pass_at_1"],
            "hallucination_rate": onecode_metrics["hallucination_rate"] - baseline_metrics["hallucination_rate"],
            "asset_completeness": onecode_metrics["asset_completeness"] - baseline_metrics["asset_completeness"],
            "evidence_completeness": onecode_metrics["evidence_completeness"] - baseline_metrics["evidence_completeness"],
        },
    }
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def run_benchmark_tasks_with_runner(
    tasks: list[BenchmarkTask],
    workspace_root: Path,
    runner: Any,
) -> dict[str, Any]:
    workspace_root.mkdir(parents=True, exist_ok=True)
    entries = []
    scores = []
    for task in tasks:
        workspace = workspace_root / task.id
        workspace.mkdir(parents=True, exist_ok=True)
        result, score = runner(task, workspace)
        entries.append(
            {
                "task_id": task.id,
                "workspace": str(workspace),
                "result": attach_shell_projection(result),
            }
        )
        scores.append(score_to_dict(score))
    return benchmark_report_from_scores(tasks, entries, scores)


def score_to_dict(score: BenchmarkScore) -> dict[str, Any]:
    return {
        "task_id": score.task_id,
        "passed": score.passed,
        "failures": score.failures,
        "hallucination_failure": score.hallucination_failure,
        "asset_complete": score.asset_complete,
        "evidence_complete": score.evidence_complete,
    }


def benchmark_report_from_scores(
    tasks: list[BenchmarkTask],
    entries: list[dict[str, Any]],
    scores: list[dict[str, Any]],
) -> dict[str, Any]:
    passed_count = sum(1 for score in scores if score["passed"])
    task_count = len(scores)
    hallucination_failures = sum(1 for score in scores if score["hallucination_failure"])
    asset_complete_count = sum(1 for score in scores if score["asset_complete"])
    evidence_complete_count = sum(1 for score in scores if score["evidence_complete"])
    return {
        "status": "completed" if passed_count == len(scores) else "failed",
        "task_count": len(tasks),
        "passed_count": passed_count,
        "failed_count": len(scores) - passed_count,
        "metrics": {
            "pass_at_1": passed_count / task_count if task_count else 0.0,
            "hallucination_failures": hallucination_failures,
            "hallucination_rate": hallucination_failures / task_count if task_count else 0.0,
            "asset_completeness": asset_complete_count / task_count if task_count else 0.0,
            "evidence_completeness": evidence_complete_count / task_count if task_count else 0.0,
        },
        "scores": scores,
        "entries": entries,
    }
