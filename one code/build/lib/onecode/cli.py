import argparse
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from onecode.cli_commands.configuration import (
    dispatch_configuration_command,
    register_configuration_commands,
)
from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.diagnostics import run_doctor
from onecode.kernel.run_inspection import (
    align_counts_with_manifest,
    apply_task_resume_evidence,
    apply_verifier_evidence,
    apply_verifier_evidence_from_dicts,
    delivery_summary,
    halted_task_resume_result,
    inspect_run,
    list_runs,
    task_completion_evidence,
    task_status_from_verifier_dicts,
    verifier_dicts,
    verifier_failure,
    write_result_ledger,
)
from onecode.kernel.execution_engine import execute_plan
from onecode.kernel.execution_plan_loader import execution_trace_to_dict, load_execution_plan
from onecode.kernel.runner import run_task
from onecode.kernel.task_plan import load_task_plan
from onecode.kernel.task_resume import PlannedAsset, classify_task_resume
from onecode.kernel.model_loop import (
    build_provider,
    execute_model_plan,
    is_patch_only_repair_plan,
    run_model_task,
)
from onecode.kernel.model_provider import api_key_from_env, build_provider_config
from onecode.kernel.sandbox import SandboxConfig, run_sandbox_smoke
from onecode.kernel.self_audit import audit_self
from onecode.kernel.shell_projection import (
    attach_shell_projection,
    attach_shell_projection_to_runs_payload,
    shell_projection_schema,
)
from onecode.kernel.verifier import (
    DEFAULT_VERIFIER_POLICY_PATH,
    load_verifier_policy,
    run_verifier,
    task_status_from_results,
    validate_selected_verifiers,
)
from onecode.kernel.gateway_engine import adjudicate_gateway_prediction, validate_assistant_content
from onecode.kernel.training_data import (
    build_adjudicated_feedback_samples,
    build_training_corpus,
    build_yizijue_lm_corpus,
    build_yizijue_lm_evalset,
    build_yizijue_lm_state_corpus,
    evaluate_training_predictions,
    evaluate_yizijue_lm_state_predictions,
    evaluate_yizijue_lm_predictions,
    expanded_training_samples,
    export_axolotl_jsonl,
    export_llamafactory_bundle,
    generate_coverage_report,
    generate_pretraining_readiness_report,
    generate_training_benchmark_tasks,
    read_jsonl,
    read_prediction_jsonl,
    read_yizijue_lm_state_prediction_jsonl,
    read_yizijue_lm_prediction_jsonl,
    replay_benchmark_training_samples,
    run_yizijue_lm_eval_predictions,
    schema_correction_training_samples,
    seed_training_samples,
    validate_jsonl,
    write_jsonl,
    write_training_configs,
    training_samples_from_rows,
)
from onecode.kernel.yizijue_transformers import (
    generate_with_yizijue_logits,
    load_transformers_causal_lm,
    run_state_corpus_predictions_with_yizijue_logits,
)
from onecode.benchmark import compare_benchmark_tasks, load_benchmark_tasks, run_benchmark_tasks
from onecode.cli_commands.read_only import dispatch_read_only_command, register_read_only_commands
from onecode.cli_commands.local_interfaces import (
    dispatch_local_interface_command,
    register_local_interface_commands,
)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive number")
    return parsed


def safe_task_id_for_cli(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()[:80] or "extra"


def cli_evidence_defaults() -> tuple[str, str]:
    profile = os.environ.get("ONECODE_EVIDENCE_PROFILE", "light").strip().lower()
    if profile in {"light", "wal", "wal-relaxed"}:
        return "wal", "relaxed"
    if profile in {"strict", "full", "full-strict"}:
        return "full", "strict"
    raise ValueError("ONECODE_EVIDENCE_PROFILE must be 'light' or 'strict'")


class YiZiJueLmChatProvider:
    def __init__(self, *, api_key: str, endpoint: str) -> None:
        self.api_key = api_key
        self.endpoint = endpoint

    def generate(self, prompt: str, *, model: str, http_timeout_seconds: float) -> str:
        body = json.dumps(
            {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=http_timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except TimeoutError as exc:
            raise TimeoutError("YiZiJue-LM request timed out") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"YiZiJue-LM request failed: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("YiZiJue-LM response envelope was not valid JSON") from exc
        choices = payload.get("choices") if isinstance(payload, dict) else None
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("YiZiJue-LM response missing choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise RuntimeError("YiZiJue-LM response missing message content")
        return message["content"]


def build_yizijue_lm_provider(*, endpoint: str, api_key: str) -> YiZiJueLmChatProvider:
    return YiZiJueLmChatProvider(api_key=api_key, endpoint=normalize_chat_endpoint(endpoint))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="onecode")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("task")
    run_parser.add_argument("--workspace", default=".")
    run_parser.add_argument("--http-timeout-seconds", type=float, default=60)
    run_parser.add_argument("--run-id", default=None)
    run_parser.add_argument("--simulate-action-seconds", type=float, default=0)
    run_parser.add_argument("--write-path", default=None)
    run_parser.add_argument("--write-content", default=None)
    run_parser.add_argument("--write-text", action="append", default=None)
    run_parser.add_argument("--intent-type", default="noop")
    run_parser.add_argument("--command", dest="intent_command", default=None)
    run_parser.add_argument("--resume-from", default=None)
    run_parser.add_argument("--patch-path", default=None)
    run_parser.add_argument("--search-block", default=None)
    run_parser.add_argument("--replace-block", default=None)
    run_parser.add_argument("--max-task-chars", type=positive_int, default=100_000)
    run_parser.add_argument("--max-write-bytes", type=positive_int, default=5_000_000)
    run_parser.add_argument("--max-actions", type=positive_int, default=100)
    run_parser.add_argument("--max-trace-bytes", type=positive_int, default=5_000_000)
    run_parser.add_argument("--max-run-seconds", type=positive_float, default=600.0)
    run_parser.add_argument("--completed-evidence-mode", choices=["full", "wal"], default=None)
    run_parser.add_argument("--evidence-durability", choices=["strict", "relaxed"], default=None)

    run_plan_parser = subparsers.add_parser("run-plan")
    run_plan_parser.add_argument("--workspace", default=".")
    run_plan_parser.add_argument("--plan", required=True)
    run_plan_parser.add_argument("--http-timeout-seconds", type=float, default=60)
    run_plan_parser.add_argument("--run-id", default=None)
    run_plan_parser.add_argument("--resume-from", default=None)
    run_plan_parser.add_argument("--verifier-policy", default=None)
    run_plan_parser.add_argument("--verifier", action="append", default=None)
    run_plan_parser.add_argument("--repair-model", default=None)
    run_plan_parser.add_argument("--repair-provider", default="responses")
    run_plan_parser.add_argument("--repair-endpoint", default=None)
    run_plan_parser.add_argument("--repair-api-key", default=None)
    run_plan_parser.add_argument("--max-repair-attempts", type=int, default=0)

    run_execution_plan_parser = subparsers.add_parser("run-execution-plan")
    run_execution_plan_parser.add_argument("--workspace", default=".")
    run_execution_plan_parser.add_argument("--plan", required=True)
    run_execution_plan_parser.add_argument("--run-id", default=None)
    run_execution_plan_parser.add_argument("--resume-from", default=None)

    run_model_parser = subparsers.add_parser("run-model")
    run_model_parser.add_argument("task")
    run_model_parser.add_argument("--workspace", default=".")
    run_model_parser.add_argument("--http-timeout-seconds", type=float, default=60)
    run_model_parser.add_argument("--run-id", default=None)
    run_model_parser.add_argument("--resume-from", default=None)
    run_model_parser.add_argument("--model", default=None)
    run_model_parser.add_argument("--api-key", default=None)
    run_model_parser.add_argument(
        "--provider",
        choices=[
            "responses",
            "chat",
            "openai-compatible",
            "compatible",
            "qwen",
            "dashscope",
            "deepseek",
            "kimi",
            "moonshot",
            "zhipu",
            "glm",
        ],
        default="responses",
    )
    run_model_parser.add_argument("--endpoint", default=None)
    run_model_parser.add_argument("--verifier-policy", default=None)
    run_model_parser.add_argument("--verifier", action="append", default=None)

    register_read_only_commands(subparsers)

    register_configuration_commands(subparsers)

    subparsers.add_parser("audit-self")

    benchmark_parser = subparsers.add_parser("benchmark")
    benchmark_parser.add_argument("--tasks-dir", default="benchmarks/tasks")
    benchmark_parser.add_argument("--run", action="store_true")
    benchmark_parser.add_argument("--compare-baseline", action="store_true")
    benchmark_parser.add_argument("--workspace-root", default=None)
    benchmark_parser.add_argument("--report", default=None)

    sandbox_smoke_parser = subparsers.add_parser("sandbox-smoke")
    sandbox_smoke_parser.add_argument("--workspace", default=".")
    sandbox_smoke_parser.add_argument("--image", default="python:3.12-slim")
    sandbox_smoke_parser.add_argument("--network", default="none")
    sandbox_smoke_parser.add_argument("--memory", default="512m")
    sandbox_smoke_parser.add_argument("--cpus", default="1")
    sandbox_smoke_parser.add_argument("--timeout-seconds", type=int, default=60)
    sandbox_smoke_parser.add_argument("--report", default=None)

    training_data_parser = subparsers.add_parser("generate-training-data")
    training_data_parser.add_argument("--output", default="data/training/yizijue_qwen15b_seed.jsonl")
    training_data_parser.add_argument("--profile", choices=["seed", "expanded", "benchmark-replay"], default="seed")
    training_data_parser.add_argument("--tasks-dir", default="benchmarks/tasks")
    training_data_parser.add_argument("--workspace-root", default=None)

    validate_training_data_parser = subparsers.add_parser("validate-training-data")
    validate_training_data_parser.add_argument("--input", required=True)

    export_training_data_parser = subparsers.add_parser("export-training-data")
    export_training_data_parser.add_argument("--format", choices=["llamafactory", "axolotl"], required=True)
    export_training_data_parser.add_argument("--profile", choices=["seed", "expanded"], default="expanded")
    export_training_data_parser.add_argument("--output-dir", required=True)

    build_training_corpus_parser = subparsers.add_parser("build-training-corpus")
    build_training_corpus_parser.add_argument("--output-dir", default="data/training/corpus")
    build_training_corpus_parser.add_argument("--tasks-dir", default="benchmarks/tasks")
    build_training_corpus_parser.add_argument("--extra-tasks-dir", action="append", default=None)
    build_training_corpus_parser.add_argument("--extra-jsonl", action="append", default=None)
    build_training_corpus_parser.add_argument("--workspace-root", default=None)
    build_training_corpus_parser.add_argument("--eval-ratio", type=float, default=0.1)

    write_training_configs_parser = subparsers.add_parser("write-training-configs")
    write_training_configs_parser.add_argument("--corpus-dir", default="data/training/corpus")
    write_training_configs_parser.add_argument("--output-dir", default="data/training/configs")

    eval_training_predictions_parser = subparsers.add_parser("eval-training-predictions")
    eval_training_predictions_parser.add_argument("--gold", required=True)
    eval_training_predictions_parser.add_argument("--predictions", required=True)
    eval_training_predictions_parser.add_argument("--adjudicate", action="store_true")

    adjudicated_feedback_parser = subparsers.add_parser("build-adjudicated-feedback")
    adjudicated_feedback_parser.add_argument("--gold", required=True)
    adjudicated_feedback_parser.add_argument("--predictions", required=True)
    adjudicated_feedback_parser.add_argument("--output", required=True)
    adjudicated_feedback_parser.add_argument("--prefix", default="adjudicated-feedback")

    adjudicate_gateway_parser = subparsers.add_parser("adjudicate-gateway")
    adjudicate_gateway_parser.add_argument("--user", required=True)
    adjudicate_gateway_parser.add_argument("--prediction", required=True)

    build_yizijue_lm_corpus_parser = subparsers.add_parser("build-yizijue-lm-corpus")
    build_yizijue_lm_corpus_parser.add_argument("--output", default="data/training/yizijue_lm_corpus.jsonl")
    build_yizijue_lm_corpus_parser.add_argument("--profile", choices=["seed", "expanded"], default="expanded")

    build_yizijue_lm_state_corpus_parser = subparsers.add_parser("build-yizijue-lm-state-corpus")
    build_yizijue_lm_state_corpus_parser.add_argument("--output", default="data/training/yizijue_lm_state_corpus.jsonl")
    build_yizijue_lm_state_corpus_parser.add_argument("--profile", choices=["seed", "expanded"], default="expanded")

    build_yizijue_lm_evalset_parser = subparsers.add_parser("build-yizijue-lm-evalset")
    build_yizijue_lm_evalset_parser.add_argument("--output", default="data/training/yizijue_lm_eval.jsonl")

    eval_yizijue_lm_predictions_parser = subparsers.add_parser("eval-yizijue-lm-predictions")
    eval_yizijue_lm_predictions_parser.add_argument("--gold", required=True)
    eval_yizijue_lm_predictions_parser.add_argument("--predictions", required=True)

    eval_yizijue_lm_state_predictions_parser = subparsers.add_parser("eval-yizijue-lm-state-predictions")
    eval_yizijue_lm_state_predictions_parser.add_argument("--gold", required=True)
    eval_yizijue_lm_state_predictions_parser.add_argument("--predictions", required=True)

    run_yizijue_lm_eval_parser = subparsers.add_parser("run-yizijue-lm-eval")
    run_yizijue_lm_eval_parser.add_argument("--gold", default="data/training/yizijue_lm_eval.jsonl")
    run_yizijue_lm_eval_parser.add_argument("--output", default="data/training/yizijue_lm_predictions.jsonl")
    run_yizijue_lm_eval_parser.add_argument("--model", required=True)
    run_yizijue_lm_eval_parser.add_argument("--endpoint", default="http://127.0.0.1:8000/v1")
    run_yizijue_lm_eval_parser.add_argument("--api-key", default="local")
    run_yizijue_lm_eval_parser.add_argument("--http-timeout-seconds", type=float, default=60)

    run_yizijue_lm_transformers_once_parser = subparsers.add_parser("run-yizijue-lm-transformers-once")
    run_yizijue_lm_transformers_once_parser.add_argument("--input", required=True)
    run_yizijue_lm_transformers_once_parser.add_argument("--basis-json", required=True)
    run_yizijue_lm_transformers_once_parser.add_argument("--model", required=True)
    run_yizijue_lm_transformers_once_parser.add_argument("--max-new-tokens", type=positive_int, default=128)
    run_yizijue_lm_transformers_once_parser.add_argument("--preferred-bias", type=positive_float, default=2.0)
    run_yizijue_lm_transformers_once_parser.add_argument("--sample", action="store_true")

    run_yizijue_lm_transformers_eval_parser = subparsers.add_parser("run-yizijue-lm-transformers-eval")
    run_yizijue_lm_transformers_eval_parser.add_argument("--gold", default="data/training/yizijue_lm_state_corpus.jsonl")
    run_yizijue_lm_transformers_eval_parser.add_argument("--output", default="data/training/yizijue_lm_state_predictions.jsonl")
    run_yizijue_lm_transformers_eval_parser.add_argument("--model", required=True)
    run_yizijue_lm_transformers_eval_parser.add_argument("--max-new-tokens", type=positive_int, default=128)
    run_yizijue_lm_transformers_eval_parser.add_argument("--preferred-bias", type=positive_float, default=2.0)
    run_yizijue_lm_transformers_eval_parser.add_argument("--sample", action="store_true")

    generate_training_benchmarks_parser = subparsers.add_parser("generate-training-benchmarks")
    generate_training_benchmarks_parser.add_argument("--output-dir", default="data/training/benchmarks")

    training_coverage_parser = subparsers.add_parser("training-coverage")
    training_coverage_parser.add_argument("--input", required=True)
    training_coverage_parser.add_argument("--report", default=None)

    pretraining_readiness_parser = subparsers.add_parser("pretraining-readiness")
    pretraining_readiness_parser.add_argument("--corpus-dir", default="data/training/corpus")
    pretraining_readiness_parser.add_argument("--configs-dir", default="data/training/configs")
    pretraining_readiness_parser.add_argument("--report", default="data/training/PRETRAINING_READINESS_REPORT.json")

    register_local_interface_commands(subparsers)
    return parser

def build_run_plan_repair_prompt(
    task: str,
    result: dict,
    verifier_results: list[dict],
    planned_asset_paths: list[str],
) -> str:
    failed_verifiers = [verifier for verifier in verifier_results if verifier.get("status") != "passed"]
    verifier_lines = []
    for verifier in failed_verifiers:
        verifier_lines.append(
            "\n".join(
                [
                    f"- id: {verifier.get('id')}",
                    f"  status: {verifier.get('status')}",
                    f"  reason: {verifier.get('reason')}",
                    f"  exit_code: {verifier.get('exit_code')}",
                    f"  stdout_tail: {verifier.get('stdout_tail')}",
                    f"  stderr_tail: {verifier.get('stderr_tail')}",
                ]
            )
        )
    return (
        "Repair the OneCode run-plan verifier failure using patches only.\n"
        f"Original task: {task}\n"
        f"Run id: {result.get('run_id')}\n"
        f"Planned asset paths: {', '.join(planned_asset_paths)}\n"
        f"Task status code: {result.get('task_status_code')}\n"
        f"Task transition action: {result.get('task_transition_action')}\n"
        f"Task transition reason: {result.get('task_transition_reason')}\n"
        f"Task resume decisions: {json.dumps(result.get('task_resume_decisions', []), ensure_ascii=False)}\n"
        "Failed verifier evidence:\n"
        f"{chr(10).join(verifier_lines) if verifier_lines else '- unavailable'}\n"
        "Return JSON with patches only. Do not return assets or execution_plan."
    )


def repair_provider_for_args(args: Any) -> tuple[Any, str]:
    config = build_provider_config(args.repair_provider, endpoint=args.repair_endpoint, model=args.repair_model)
    api_key = args.repair_api_key if args.repair_api_key is not None else api_key_from_env(provider_kind=args.repair_provider)
    if api_key is None:
        raise ValueError(f"{config.env_key} is required for run-plan repair")
    return build_provider(api_key, args.repair_provider, args.repair_endpoint), config.model


def apply_run_plan_repair(
    result: dict,
    task: str,
    workspace: Path,
    http_timeout_seconds: float,
    verifier_specs: list,
    planned_asset_paths: list[str],
    args: Any,
) -> dict:
    initial_verifiers = verifier_dicts(result.get("verifier_results", []))
    if verifier_failure(initial_verifiers) is None or args.max_repair_attempts <= 0:
        return result

    provider, model = repair_provider_for_args(args)
    repair_results = []
    repair_verifier_results = []
    prompt_evidence = []
    current_result = result
    current_verifiers = initial_verifiers

    for attempt in range(1, args.max_repair_attempts + 1):
        prompt = build_run_plan_repair_prompt(task, current_result, current_verifiers, planned_asset_paths)
        prompt_evidence.append(
            {
                "attempt": attempt,
                "failed_verifier_ids": [
                    verifier.get("id") for verifier in current_verifiers if verifier.get("status") != "passed"
                ],
                "planned_asset_paths": planned_asset_paths,
            }
        )
        repair_plan = provider.create_plan(prompt, model=model, http_timeout_seconds=http_timeout_seconds)
        if not is_patch_only_repair_plan(repair_plan):
            rejected = {
                **current_result,
                "status": "halted",
                "partial": True,
                "repaired": False,
                "repair_attempt_count": attempt,
                "initial_verifier_results": initial_verifiers,
                "repair_verifier_results": repair_verifier_results,
                "repair_results": repair_results,
                "repair_rejected_reason": "repair_plan_must_use_patches_only",
                "repair_prompt_evidence": prompt_evidence,
            }
            return write_result_ledger(workspace, rejected)

        repair_result = execute_model_plan(
            repair_plan,
            workspace=workspace,
            http_timeout_seconds=http_timeout_seconds,
            run_id=current_result["run_id"],
            resume_from_run_id=current_result.get("resumed_from"),
            run_metadata={"repair_attempt": attempt},
        )
        repair_results.append(repair_result)
        latest_verifiers = verifier_dicts([run_verifier(workspace, spec) for spec in verifier_specs])
        repair_verifier_results.append(latest_verifiers)
        current_result = apply_verifier_evidence_from_dicts(current_result, workspace, latest_verifiers)
        current_verifiers = latest_verifiers
        if verifier_failure(latest_verifiers) is None:
            repaired = {
                **align_counts_with_manifest(workspace, current_result),
                "status": "completed",
                "reason": None,
                "partial": False,
                "delivery_status": "deliverable",
                "repaired": True,
                "repair_attempt_count": attempt,
                "initial_verifier_results": initial_verifiers,
                "repair_verifier_results": repair_verifier_results,
                "repair_results": repair_results,
                "repair_rejected_reason": None,
                "repair_prompt_evidence": prompt_evidence,
            }
            return write_result_ledger(workspace, repaired)

    exhausted = {
        **align_counts_with_manifest(workspace, current_result),
        "status": "halted",
        "partial": True,
        "repaired": False,
        "repair_attempt_count": args.max_repair_attempts,
        "initial_verifier_results": initial_verifiers,
        "repair_verifier_results": repair_verifier_results,
        "repair_results": repair_results,
        "repair_rejected_reason": None,
        "repair_prompt_evidence": prompt_evidence,
    }
    return write_result_ledger(workspace, exhausted)


def run_plan_verifier_policy_path(workspace: Path, explicit_policy: str | None) -> Path:
    if explicit_policy is not None:
        return Path(explicit_policy)
    return workspace / DEFAULT_VERIFIER_POLICY_PATH


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    read_only_exit_code = dispatch_read_only_command(args)
    if read_only_exit_code is not None:
        return read_only_exit_code

    local_interface_exit_code = dispatch_local_interface_command(args, parser)
    if local_interface_exit_code is not None:
        return local_interface_exit_code

    configuration_exit_code = dispatch_configuration_command(args, parser)
    if configuration_exit_code is not None:
        return configuration_exit_code

    if args.subcommand == "audit-self":
        result = audit_self(Path.cwd(), run_doctor)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] == "ok" else 1

    if args.subcommand == "benchmark":
        try:
            tasks = load_benchmark_tasks(Path(args.tasks_dir))
        except ValueError as exc:
            parser.error(str(exc))
        if args.compare_baseline:
            result = compare_benchmark_tasks(
                tasks,
                workspace_root=Path(args.workspace_root) if args.workspace_root is not None else None,
                report_path=Path(args.report) if args.report is not None else None,
            )
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 0 if result["status"] == "completed" else 1
        if args.run:
            result = run_benchmark_tasks(
                tasks,
                workspace_root=Path(args.workspace_root) if args.workspace_root is not None else None,
                report_path=Path(args.report) if args.report is not None else None,
            )
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 0 if result["status"] == "completed" else 1
        result = {
            "status": "ready",
            "task_count": len(tasks),
            "tasks": [
                {
                    "id": task.id,
                    "expected_status": task.expected_status,
                    "assertion_count": len(task.assertions),
                }
                for task in tasks
            ],
        }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "sandbox-smoke":
        try:
            sandbox_workspace = Path(args.workspace)
            if not sandbox_workspace.exists():
                sandbox_workspace.mkdir(parents=True)
            result = run_sandbox_smoke(
                SandboxConfig(
                    workspace=sandbox_workspace,
                    image=args.image,
                    network=args.network,
                    memory=args.memory,
                    cpus=args.cpus,
                    timeout_seconds=args.timeout_seconds,
                ),
                report_path=Path(args.report) if args.report is not None else None,
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        if result["status"] == "completed":
            return 0
        if result["status"] == "blocked":
            return 2
        return 1

    if args.subcommand == "generate-training-data":
        if args.profile == "benchmark-replay":
            samples = replay_benchmark_training_samples(
                Path(args.tasks_dir),
                workspace_root=Path(args.workspace_root) if args.workspace_root is not None else None,
            )
        else:
            samples = expanded_training_samples() if args.profile == "expanded" else seed_training_samples()
        result = write_jsonl(Path(args.output), samples)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "validate-training-data":
        try:
            result = validate_jsonl(Path(args.input))
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "export-training-data":
        samples = expanded_training_samples() if args.profile == "expanded" else seed_training_samples()
        if args.format == "llamafactory":
            result = export_llamafactory_bundle(Path(args.output_dir), samples)
        else:
            result = export_axolotl_jsonl(Path(args.output_dir), samples)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "build-training-corpus":
        try:
            workspace_root = Path(args.workspace_root) if args.workspace_root is not None else None
            samples = expanded_training_samples() + schema_correction_training_samples() + replay_benchmark_training_samples(
                Path(args.tasks_dir),
                workspace_root=workspace_root,
            )
            for extra_tasks_dir in args.extra_tasks_dir or []:
                samples.extend(
                    replay_benchmark_training_samples(
                        Path(extra_tasks_dir),
                        workspace_root=workspace_root / safe_task_id_for_cli(extra_tasks_dir) if workspace_root else None,
                    )
                )
            for extra_jsonl in args.extra_jsonl or []:
                samples.extend(training_samples_from_rows(read_jsonl(Path(extra_jsonl))))
            result = build_training_corpus(Path(args.output_dir), samples, eval_ratio=args.eval_ratio)
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "write-training-configs":
        try:
            result = write_training_configs(Path(args.output_dir), Path(args.corpus_dir))
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "eval-training-predictions":
        try:
            gold_samples = training_samples_from_rows(read_jsonl(Path(args.gold)))
            predictions = read_prediction_jsonl(Path(args.predictions))
            result = evaluate_training_predictions(gold_samples, predictions, adjudicate=args.adjudicate)
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] == "ok" else 1

    if args.subcommand == "build-adjudicated-feedback":
        try:
            gold_samples = training_samples_from_rows(read_jsonl(Path(args.gold)))
            predictions = read_prediction_jsonl(Path(args.predictions))
            samples = build_adjudicated_feedback_samples(gold_samples, predictions, prefix=args.prefix)
            result = write_jsonl(Path(args.output), samples)
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "adjudicate-gateway":
        try:
            raw_prediction = validate_assistant_content(args.prediction)
        except ValueError:
            raw_prediction = None
        adjudicated_prediction = adjudicate_gateway_prediction(args.user, args.prediction)
        result = {
            "status": "ok",
            "user": args.user,
            "raw_prediction": raw_prediction,
            "adjudicated_prediction": adjudicated_prediction,
            "changed": raw_prediction != adjudicated_prediction,
        }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "build-yizijue-lm-corpus":
        samples = seed_training_samples() if args.profile == "seed" else expanded_training_samples() + schema_correction_training_samples()
        result = build_yizijue_lm_corpus(Path(args.output), samples)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "build-yizijue-lm-state-corpus":
        samples = seed_training_samples() if args.profile == "seed" else expanded_training_samples() + schema_correction_training_samples()
        result = build_yizijue_lm_state_corpus(Path(args.output), samples)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "build-yizijue-lm-evalset":
        result = build_yizijue_lm_evalset(Path(args.output))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "eval-yizijue-lm-predictions":
        try:
            gold_rows = [
                json.loads(line)
                for line in Path(args.gold).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            predictions = read_yizijue_lm_prediction_jsonl(Path(args.predictions))
            result = evaluate_yizijue_lm_predictions(gold_rows, predictions)
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] == "ok" else 1

    if args.subcommand == "eval-yizijue-lm-state-predictions":
        try:
            gold_rows = [
                json.loads(line)
                for line in Path(args.gold).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            predictions = read_yizijue_lm_state_prediction_jsonl(Path(args.predictions))
            result = evaluate_yizijue_lm_state_predictions(gold_rows, predictions)
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] == "ok" else 1

    if args.subcommand == "run-yizijue-lm-eval":
        try:
            provider = build_yizijue_lm_provider(endpoint=args.endpoint, api_key=args.api_key)
            result = run_yizijue_lm_eval_predictions(
                Path(args.gold),
                Path(args.output),
                provider=provider,
                model=args.model,
                http_timeout_seconds=args.http_timeout_seconds,
            )
        except (RuntimeError, TimeoutError, ValueError) as exc:
            parser.error(str(exc))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "run-yizijue-lm-transformers-once":
        try:
            basis = json.loads(args.basis_json)
            tokenizer, model = load_transformers_causal_lm(args.model)
            result = generate_with_yizijue_logits(
                args.input,
                basis=basis,
                tokenizer=tokenizer,
                model=model,
                max_new_tokens=args.max_new_tokens,
                preferred_bias=args.preferred_bias,
                do_sample=args.sample,
            )
        except (json.JSONDecodeError, RuntimeError, ValueError) as exc:
            parser.error(str(exc))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "run-yizijue-lm-transformers-eval":
        try:
            tokenizer, model = load_transformers_causal_lm(args.model)
            result = run_state_corpus_predictions_with_yizijue_logits(
                Path(args.gold),
                Path(args.output),
                tokenizer=tokenizer,
                model=model,
                max_new_tokens=args.max_new_tokens,
                preferred_bias=args.preferred_bias,
                do_sample=args.sample,
            )
        except (RuntimeError, ValueError) as exc:
            parser.error(str(exc))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "generate-training-benchmarks":
        result = generate_training_benchmark_tasks(Path(args.output_dir))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "training-coverage":
        try:
            rows = read_jsonl(Path(args.input))
            report = generate_coverage_report(training_samples_from_rows(rows))
        except ValueError as exc:
            parser.error(str(exc))
        if args.report is not None:
            report_path = Path(args.report)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["status"] == "ok" else 1

    if args.subcommand == "pretraining-readiness":
        try:
            report = generate_pretraining_readiness_report(Path(args.corpus_dir), Path(args.configs_dir))
        except ValueError as exc:
            parser.error(str(exc))
        if args.report is not None:
            report_path = Path(args.report)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["status"] == "ready" else 1

    if args.subcommand == "run-plan":
        try:
            task, write_texts, plan_evidence = load_task_plan(Path(args.plan))
            if args.max_repair_attempts < 0:
                parser.error("--max-repair-attempts must be non-negative")
            if args.max_repair_attempts > 0 and not args.verifier:
                parser.error("--max-repair-attempts requires --verifier")
            verifier_specs = []
            if args.verifier:
                policy_path = run_plan_verifier_policy_path(Path(args.workspace), args.verifier_policy)
                policy = load_verifier_policy(policy_path)
                verifier_specs = validate_selected_verifiers(Path(args.workspace), policy, args.verifier)
            resume_summary = None
            if args.resume_from is not None:
                planned_assets = [
                    PlannedAsset(path=write_text.partition("=")[0], content=write_text.partition("=")[2])
                    for write_text in write_texts
                ]
                resume_summary = classify_task_resume(
                    workspace=Path(args.workspace),
                    source_run_id=args.resume_from,
                    planned_assets=planned_assets,
                    verifier_specs=verifier_specs,
                )
                if any(decision.kind == "halt" for decision in resume_summary.decisions):
                    result = halted_task_resume_result(
                        Path(args.workspace),
                        args.run_id,
                        args.resume_from,
                        resume_summary,
                    )
                    print(json.dumps(attach_shell_projection(result), ensure_ascii=False, sort_keys=True))
                    return IchingKernel.process_exit_code(status=result["status"], reason=result["reason"])
            result = run_task(
                task,
                workspace=Path(args.workspace),
                http_timeout_seconds=args.http_timeout_seconds,
                run_id=args.run_id,
                write_texts=write_texts,
                resume_from_run_id=args.resume_from,
                run_metadata=plan_evidence,
            )
            if verifier_specs and result["status"] == "completed":
                verifier_results = [run_verifier(Path(args.workspace), spec) for spec in verifier_specs]
                result = apply_verifier_evidence(result, Path(args.workspace), verifier_results)
                result = apply_run_plan_repair(
                    result=result,
                    task=task,
                    workspace=Path(args.workspace),
                    http_timeout_seconds=args.http_timeout_seconds,
                    verifier_specs=verifier_specs,
                    planned_asset_paths=[write_text.partition("=")[0] for write_text in write_texts],
                    args=args,
                )
            result = apply_task_resume_evidence(result, Path(args.workspace), resume_summary)
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(attach_shell_projection(result), ensure_ascii=False, sort_keys=True))
        return IchingKernel.process_exit_code(status=result["status"], reason=result["reason"])

    if args.subcommand == "run-execution-plan":
        try:
            plan = load_execution_plan(Path(args.plan))
            trace = execute_plan(
                plan,
                workspace=Path(args.workspace),
                run_id=args.run_id,
                resume_from_run_id=args.resume_from,
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(execution_trace_to_dict(trace), ensure_ascii=False, sort_keys=True))
        return 0 if trace.success else 1

    if args.subcommand == "run-model":
        try:
            verifier_specs = []
            if args.verifier:
                policy_path = run_plan_verifier_policy_path(Path(args.workspace), args.verifier_policy)
                policy = load_verifier_policy(policy_path)
                verifier_specs = validate_selected_verifiers(Path(args.workspace), policy, args.verifier)
            result = run_model_task(
                args.task,
                workspace=Path(args.workspace),
                http_timeout_seconds=args.http_timeout_seconds,
                run_id=args.run_id,
                resume_from_run_id=args.resume_from,
                model=args.model,
                api_key=args.api_key,
                provider_kind=args.provider,
                endpoint=args.endpoint,
            )
            if verifier_specs and result["status"] == "completed":
                verifier_results = [run_verifier(Path(args.workspace), spec) for spec in verifier_specs]
                result = apply_verifier_evidence(result, Path(args.workspace), verifier_results)
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(attach_shell_projection(result), ensure_ascii=False, sort_keys=True))
        return IchingKernel.process_exit_code(status=result["status"], reason=result["reason"])

    if args.subcommand == "run":
        if args.write_text and (args.write_path is not None or args.write_content is not None):
            parser.error("cannot combine --write-text with --write-path or --write-content")
        if args.write_text and (
            args.patch_path is not None or args.search_block is not None or args.replace_block is not None
        ):
            parser.error("cannot combine --write-text with patch arguments")
        try:
            default_evidence_mode, default_evidence_durability = cli_evidence_defaults()
            result = run_task(
                args.task,
                workspace=Path(args.workspace),
                http_timeout_seconds=args.http_timeout_seconds,
                run_id=args.run_id,
                simulated_action_seconds=args.simulate_action_seconds,
                write_path=args.write_path,
                write_content=args.write_content,
                write_texts=args.write_text,
                intent_type=args.intent_type,
                command=args.intent_command,
                resume_from_run_id=args.resume_from,
                patch_path=args.patch_path,
                search_block=args.search_block,
                replace_block=args.replace_block,
                max_task_chars=args.max_task_chars,
                max_write_bytes=args.max_write_bytes,
                max_actions=args.max_actions,
                max_trace_bytes=args.max_trace_bytes,
                max_run_seconds=args.max_run_seconds,
                completed_evidence_mode=args.completed_evidence_mode or default_evidence_mode,
                evidence_durability=args.evidence_durability or default_evidence_durability,
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(attach_shell_projection(result), ensure_ascii=False, sort_keys=True))
        return IchingKernel.process_exit_code(status=result["status"], reason=result["reason"])

    parser.error(f"unknown command: {args.subcommand}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
