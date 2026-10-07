from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from onecode.kernel.agent_cycle import run_agent_cycle
from onecode.kernel.approval import ApprovalDecision, write_approval_decision
from onecode.kernel.execution_tools import default_tool_registry
from onecode.kernel.finalization import finalize_run_event
from onecode.kernel.inspection import (
    read_json,
    validate_checkpoint_evidence,
    validate_ledger_counts,
    validate_status_document,
)
from onecode.kernel.iching_encoding import ACTIVE_RULE_SCHEMA
from onecode.kernel.path_guard import PathGuard, PathGuardError
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
        elif assertion_type == "file_contains":
            text = assertion.get("text")
            target = workspace / rel_path if isinstance(rel_path, str) else None
            if not isinstance(text, str) or target is None or not target.is_file() or text not in target.read_text(encoding="utf-8"):
                failures.append(f"file missing text: {rel_path}")
                asset_complete = False
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

    ledger_path = Path(ledger_path_value)  # type: ignore
    manifest_path = Path(manifest_path_value)  # type: ignore
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

    if task.mode == "agent":
        result = _run_agent_benchmark_task(task, workspace)
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
                    path=patch_path,  # type: ignore
                    search_block=search_block,  # type: ignore
                    replace_block=replace_block,  # type: ignore
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
        "rule_schema": ACTIVE_RULE_SCHEMA,
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


SWEBENCH_LITE_SUBSET_IDS = (
    "django__django-11099",
    "sympy__sympy-20590",
    "pytest-dev__pytest-5692",
    "astropy__astropy-12907",
    "sphinx-doc__sphinx-10325",
)


def agent_pass_rate_record(report: dict[str, Any]) -> dict[str, Any]:
    tasks = []
    entries = report.get("entries") if isinstance(report.get("entries"), list) else []
    scores = report.get("scores") if isinstance(report.get("scores"), list) else []
    for score, entry in zip(scores, entries):  # type: ignore
        result = entry.get("result") if isinstance(entry, dict) else {}
        if not isinstance(result, dict):
            result = {}
        tasks.append(
            {
                "task_id": score.get("task_id") if isinstance(score, dict) else "",
                "passed": bool(score.get("passed")) if isinstance(score, dict) else False,
                "turn_count": result.get("turn_count"),
                "stop_reason": result.get("reason"),
            }
        )
    passed_count = sum(1 for item in tasks if item["passed"])
    task_count = len(tasks)
    return {
        "runner": "scripted_oracle",
        "task_count": task_count,
        "passed_count": passed_count,
        "pass_rate": passed_count / task_count if task_count else 0.0,
        "claims_mainstream_parity": False,
        "tasks": tasks,
    }


def swebench_lite_subset_report(dataset_path: Path | None) -> dict[str, Any]:
    report: dict[str, Any] = {
        "subset_ids": list(SWEBENCH_LITE_SUBSET_IDS),
        "claims_mainstream_parity": False,
        "loaded_count": 0,
    }
    if dataset_path is None or not dataset_path.is_file():
        report["status"] = "not_connected"
        report["reason"] = "swebench_lite_dataset_missing"
        return report
    wanted = set(SWEBENCH_LITE_SUBSET_IDS)
    instances = []
    for line in dataset_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item, dict) or item.get("instance_id") not in wanted:
            continue
        if not isinstance(item.get("repo"), str) or not isinstance(item.get("problem_statement"), str):
            continue
        instances.append({"instance_id": item["instance_id"], "repo": item["repo"]})
    order = {instance_id: index for index, instance_id in enumerate(SWEBENCH_LITE_SUBSET_IDS)}
    instances.sort(key=lambda item: order[item["instance_id"]])
    report["loaded_count"] = len(instances)
    report["instances"] = instances
    if instances:
        report["status"] = "loaded"
        report["reason"] = "subset_loaded_without_public_eval"
    else:
        report["status"] = "not_connected"
        report["reason"] = "swebench_lite_subset_not_in_dataset"
    return report


def vendored_swebench_lite_subset_report() -> dict[str, Any]:
    dataset_path = Path(__file__).resolve().parents[2] / "benchmarks" / "swebench-lite" / "subset.jsonl"
    report = swebench_lite_subset_report(dataset_path)
    report["eval_status"] = "not_executed"
    report["eval_reason"] = "historical_repositories_need_their_original_python"
    report["claims_mainstream_parity"] = False
    return report


def summarize_swebench_eval(results: list[dict[str, Any]]) -> dict[str, Any]:
    executed = [item for item in results if item.get("status") in {"passed", "failed"}]
    passed = [item for item in executed if item.get("status") == "passed"]
    return {
        "runner": "official_gold_patch",
        "claims_mainstream_parity": False,
        "loaded_count": len(results),
        "executed_count": len(executed),
        "passed_count": len(passed),
        "pass_rate": (len(passed) / len(executed)) if executed else None,
        "eval_status": "executed" if executed else "not_executed",
        "blocked_count": sum(1 for item in results if item.get("status") == "blocked"),
        "note": "pass_rate counts published patches that reproduce FAIL_TO_PASS. It is not an OneCode agent solve rate.",
        "instances": results,
    }


def evaluate_swebench_instance(
    instance: dict[str, Any],
    workspace: Path,
    *,
    python: str,
    install: bool = True,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "instance_id": str(instance.get("instance_id") or ""),
        "status": "blocked",
        "reason": None,
        "before_returncode": None,
        "after_returncode": None,
    }
    repo = instance.get("repo")
    commit = instance.get("base_commit")
    test_patch = instance.get("test_patch")
    gold_patch = instance.get("patch")
    if not all(isinstance(item, str) and item for item in (repo, commit, test_patch, gold_patch)):
        result["reason"] = "instance_missing_patch"
        return result
    workspace.mkdir(parents=True, exist_ok=True)
    checkout = workspace / "repo"
    clone_reason = _clone_commit(repo, commit, checkout)  # type: ignore
    if clone_reason is not None:
        result["reason"] = clone_reason
        return result
    if not _apply_text_patch(checkout, test_patch):  # type: ignore
        result["reason"] = "test_patch_failed"
        return result
    python_bin = python
    if install:
        python_bin, install_reason = _install_checkout(checkout, str(repo), python, timeout_seconds)
        if install_reason is not None:
            result["reason"] = install_reason
            return result
    before = _run_argv(_instance_test_argv(instance, python_bin), checkout, timeout_seconds)
    result["before_returncode"] = before
    if before == 0:
        result["status"] = "failed"
        result["reason"] = "tests_already_passing"
        return result
    if not _apply_text_patch(checkout, gold_patch):  # type: ignore
        result["status"] = "failed"
        result["reason"] = "gold_patch_failed"
        return result
    after = _run_argv(_instance_test_argv(instance, python_bin), checkout, timeout_seconds)
    result["after_returncode"] = after
    if after == 0:
        result["status"] = "passed"
        result["reason"] = None
        return result
    result["status"] = "failed"
    result["reason"] = "tests_still_failing"
    return result


def _clone_commit(repo: str, commit: str, dest: Path) -> str | None:
    if dest.exists():
        return "checkout_exists"
    url = repo if repo.startswith("/") or repo.startswith("file:") else f"https://github.com/{repo}.git"
    cloned = subprocess.run(
        ["git", "clone", "--no-checkout", url, str(dest)],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if cloned.returncode != 0:
        return "clone_failed"
    present = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=dest,
        capture_output=True,
        text=True,
        check=False,
    )
    if present.returncode != 0:
        fetched = subprocess.run(
            ["git", "fetch", "--depth", "1", "origin", commit],
            cwd=dest,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if fetched.returncode != 0:
            return "fetch_failed"
    checked_out = subprocess.run(
        ["git", "checkout", commit],
        cwd=dest,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if checked_out.returncode != 0:
        return "checkout_failed"
    return None


def _apply_text_patch(repo: Path, patch: str) -> bool:
    patch_path = repo / ".onecode-eval.patch"
    patch_path.write_text(patch if patch.endswith("\n") else patch + "\n", encoding="utf-8")
    completed = subprocess.run(
        ["git", "apply", "--whitespace=nowarn", str(patch_path.name)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    patch_path.unlink(missing_ok=True)
    return completed.returncode == 0


def _install_checkout(repo: Path, repo_name: str, python: str, timeout_seconds: int) -> tuple[str, str | None]:
    venv = repo.parent / "venv"
    created = subprocess.run([python, "-m", "venv", str(venv)], capture_output=True, text=True, check=False)
    if created.returncode != 0:
        return python, "venv_failed"
    python_bin = str(venv / "bin" / "python")
    for command in _install_commands(repo_name):
        try:
            installed = subprocess.run(
                [python_bin, *command],
                cwd=repo,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return python_bin, "install_failed"
        if installed.returncode != 0:
            return python_bin, "install_failed"
    return python_bin, None


def _install_commands(repo_name: str) -> list[list[str]]:
    if repo_name == "sphinx-doc/sphinx":
        return [["-m", "pip", "install", "-e", ".[test]"]]
    if repo_name == "astropy/astropy":
        return [
            ["-m", "pip", "install", "setuptools==57.5.0", "numpy", "cython"],
            ["-m", "pip", "install", "-e", ".", "--no-build-isolation"],
        ]
    return [["-m", "pip", "install", "-e", "."]]


def _instance_test_argv(instance: dict[str, Any], python_bin: str) -> list[str]:
    argv = instance.get("test_argv")
    if isinstance(argv, list) and argv and all(isinstance(item, str) and item for item in argv):
        return [python_bin if item == "{python}" else item for item in argv]
    tests = _fail_to_pass_tests(instance)
    repo = instance.get("repo") if isinstance(instance.get("repo"), str) else ""
    if repo == "django/django":
        return [python_bin, "tests/runtests.py", "--verbosity", "1", "--settings=test_sqlite", *[_django_label(item) for item in tests]]
    if repo == "sympy/sympy":
        files = [path for path in _patched_paths(str(instance.get("test_patch") or "")) if path.startswith("sympy/") and "/tests/" in path]
        if files:
            return [python_bin, "bin/test", *files]
        return [python_bin, "bin/test", *tests]
    return [python_bin, "-m", "pytest", "-q", *tests]


def _fail_to_pass_tests(instance: dict[str, Any]) -> list[str]:
    raw = instance.get("FAIL_TO_PASS")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, str)]
    if isinstance(raw, str) and raw:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, str)]
    return []


def _patched_paths(patch: str) -> list[str]:
    paths = []
    for line in patch.splitlines():
        if not line.startswith("diff --git "):
            continue
        parts = line.split()
        if len(parts) >= 4 and parts[3].startswith("b/"):
            paths.append(parts[3][2:])
    return paths


def _django_label(label: str) -> str:
    if " (" in label and label.endswith(")"):
        test_name, _, class_path = label.partition(" (")
        return f"{class_path[:-1]}.{test_name}"
    return label


def _run_argv(argv: list[str], cwd: Path, timeout_seconds: int) -> int:
    cache = cwd / "__pycache__"
    if cache.is_dir():
        for child in cache.glob("*.pyc"):
            child.unlink()
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env=environment,
        )
    except subprocess.TimeoutExpired:
        return -1
    return completed.returncode


def _run_agent_benchmark_task(task: BenchmarkTask, workspace: Path) -> dict[str, Any]:
    task_input = task.input or {}
    _seed_benchmark_files(workspace, task_input.get("files"))
    script = task_input.get("script") if isinstance(task_input.get("script"), list) else []
    max_turns = task_input.get("max_turns", 8)
    if isinstance(max_turns, bool) or not isinstance(max_turns, int) or max_turns <= 0:
        max_turns = 8
    cursor = {"index": 0}

    def propose(history: list[dict[str, Any]], allowed: frozenset[str]) -> list[dict[str, Any]]:
        del history, allowed
        if cursor["index"] >= len(script):  # type: ignore
            return []
        call = script[cursor["index"]]  # type: ignore
        cursor["index"] += 1
        if not isinstance(call, dict):
            return []
        params = call.get("params") if isinstance(call.get("params"), dict) else {}
        return [{"tool_name": call.get("tool_name"), "params": params}]

    registry = default_tool_registry()

    def execute(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "write_text":
            content = params.get("content") if isinstance(params.get("content"), str) else ""
            path = params.get("path") if isinstance(params.get("path"), str) else ""
            try:
                written = PathGuard.write_text(workspace, path, content)  # type: ignore
            except PathGuardError:
                return {"status": "halted", "reason": "sovereignty_breach"}
            return {"status": "completed", "reason": None, "path": written["path"]}
        tool = registry.get(tool_name) if isinstance(tool_name, str) else None
        if tool is None:
            return {"status": "halted", "reason": "action_exception"}
        try:
            outcome = tool.execute(params, workspace)
        except PathGuardError:
            return {"status": "halted", "reason": "sovereignty_breach"}
        except (OSError, ValueError, subprocess.SubprocessError):
            return {"status": "halted", "reason": "action_exception"}
        if not isinstance(outcome, dict):
            return {"status": "halted", "reason": "action_exception"}
        if "status" not in outcome:
            outcome = {**outcome, "status": "completed"}
        if "reason" not in outcome:
            outcome = {**outcome, "reason": None}
        return outcome

    result = run_agent_cycle(
        propose=propose,
        execute=execute,
        max_turns=max_turns,
        task=task.prompt,
        workspace=workspace,
        remember=False,
        approve=_scripted_oracle_approved,
    )
    result["run_id"] = f"benchmark-{task.id}"
    return result


def _scripted_oracle_approved(tool_name: str, params: dict[str, Any]) -> bool:
    del tool_name, params
    return True


def _seed_benchmark_files(workspace: Path, files: object) -> None:
    if not isinstance(files, list):
        return
    for file_entry in files:
        if not isinstance(file_entry, dict):
            continue
        path = file_entry.get("path")
        content = file_entry.get("content")
        if isinstance(path, str) and isinstance(content, str):
            PathGuard.write_text(workspace, path, content)


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
        "rule_schema": ACTIVE_RULE_SCHEMA,
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
