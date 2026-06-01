import argparse
import json
import os
import re
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.inspection import (
    LEDGER_COUNT_FIELDS,
    read_json,
    validate_checkpoint_evidence,
    validate_evidence_chain,
    validate_ledger_counts,
    validate_status_document,
    validate_trace_completion,
)
from onecode.kernel.execution_engine import execute_plan
from onecode.kernel.execution_plan_loader import execution_trace_to_dict, load_execution_plan
from onecode.kernel.checkpoint import wal_entry_hash, write_ledger
from onecode.kernel.runner import run_task
from onecode.kernel.task_plan import load_task_plan
from onecode.kernel.task_resume import PlannedAsset, classify_task_resume
from onecode.kernel.model_loop import (
    build_provider,
    execute_model_plan,
    is_patch_only_repair_plan,
    run_model_task,
)
from onecode.kernel.model_config import discover_models, read_model_config, write_model_config
from onecode.kernel.model_provider import api_key_from_env, build_provider_config
from onecode.kernel.sandbox import SandboxConfig, run_sandbox_smoke
from onecode.kernel.self_audit import audit_self
from onecode.kernel.shell_projection import (
    attach_shell_projection,
    attach_shell_projection_to_runs_payload,
    shell_projection_schema,
)
from onecode.kernel.context import create_context
from onecode.kernel.verifier import (
    DEFAULT_VERIFIER_POLICY_PATH,
    load_verifier_policy,
    run_verifier,
    task_status_from_results,
    validate_selected_verifiers,
    verifier_policy_presets_summary,
    write_verifier_policy,
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
from onecode.kernel.wal import global_wal_paths
from onecode.benchmark import compare_benchmark_tasks, load_benchmark_tasks, run_benchmark_tasks


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

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--workspace", default=".")
    inspect_parser.add_argument("--run-id", required=True)

    list_runs_parser = subparsers.add_parser("list-runs")
    list_runs_parser.add_argument("--workspace", default=".")

    subparsers.add_parser("list-verifier-presets")

    init_verifier_policy_parser = subparsers.add_parser("init-verifier-policy")
    init_verifier_policy_parser.add_argument("--workspace", default=".")
    init_verifier_policy_parser.add_argument("--output", default=DEFAULT_VERIFIER_POLICY_PATH)
    init_verifier_policy_parser.add_argument("--preset", action="append", default=None)
    init_verifier_policy_parser.add_argument("--force", action="store_true")

    subparsers.add_parser("doctor")
    subparsers.add_parser("audit-self")
    subparsers.add_parser("math-audit")
    subparsers.add_parser("shell-schema")

    config_parser = subparsers.add_parser("config")
    config_subparsers = config_parser.add_subparsers(dest="config_action", required=True)
    config_set_model_parser = config_subparsers.add_parser("set-model")
    config_set_model_parser.add_argument("--endpoint", required=True)
    config_set_model_parser.add_argument("--api-key", required=True)
    config_set_model_parser.add_argument("--model", default=None)
    config_set_model_parser.add_argument("--provider", default="openai-compatible")
    config_subparsers.add_parser("show")
    config_discover_parser = config_subparsers.add_parser("discover-models")
    config_discover_parser.add_argument("--endpoint", required=True)
    config_discover_parser.add_argument("--api-key", required=True)

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

    serve_parser = subparsers.add_parser("serve")
    serve_parser.description = "Serve OneCode as an OpenAI-compatible endpoint for LibreChat."
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8080)
    serve_parser.add_argument("--allow-unauthenticated-local", action="store_true")

    shell_parser = subparsers.add_parser("shell")
    shell_parser.description = "Launch the bundled OneCode Agent shell."
    shell_parser.add_argument("--shell-mode", choices=["librechat", "integrated"], default="librechat")
    shell_parser.add_argument("--onecode-root", default=str(Path.cwd()))
    shell_parser.add_argument("--librechat-dir", default=None)
    shell_parser.add_argument("--workspace", default=None)
    shell_parser.add_argument("--onecode-host", default="127.0.0.1")
    shell_parser.add_argument("--onecode-port", type=int, default=19080)
    shell_parser.add_argument("--librechat-host", default="127.0.0.1")
    shell_parser.add_argument("--librechat-port", type=int, default=14080)
    shell_parser.add_argument("--mongo-port", type=int, default=39017)
    shell_parser.add_argument("--api-token", default="dev-local-token")
    shell_parser.add_argument("--email", default="onecode@local.test")
    shell_parser.add_argument("--password", default="OneCode123!")
    shell_parser.add_argument("--show-credentials", action="store_true")
    shell_parser.add_argument("--no-browser", dest="open_browser", action="store_false")
    shell_parser.set_defaults(open_browser=True)

    tui_parser = subparsers.add_parser("tui")
    tui_parser.add_argument("--workspace", default=None)
    tui_parser.add_argument("--model", default=None)
    tui_parser.add_argument(
        "--provider",
        choices=[
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
        default=None,
    )
    return parser


def doctor_check(name: str, passed: bool, detail: dict | None = None) -> dict:
    return {"name": name, "passed": passed, "detail": detail or {}}


def doctor_result_detail(result: dict) -> dict:
    return {
        "run_id": result["run_id"],
        "status": result["status"],
        "reason": result["reason"],
        "iching_status_code": result["iching_status_code"],
        "iching_transition_action": result["iching_transition_action"],
        "iching_transition_reason": result["iching_transition_reason"],
        "dispatch_decision": result["iching_profile"]["dispatch_decision"],
    }


def doctor_rule_passed(result: dict) -> bool:
    profile = result["iching_profile"]
    profile_transition = IchingKernel.transition(profile["status_code"])
    return (
        profile["status_code"] == result["iching_status_code"]
        and profile["transition"]["action"] == profile_transition.action
        and profile["transition"]["reason"] == profile_transition.reason
        and profile["dispatch_decision"] == IchingKernel.dispatch_decision(profile_transition)
    )


def run_doctor() -> dict:
    checks = []
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)

        write_result = run_task(
            "doctor write",
            workspace=workspace,
            run_id="doctor-write",
            write_path="src/doctor_asset.py",
            write_content="value = 1\n",
        )
        checks.append(
            doctor_check(
                "write_text",
                write_result["status"] == "completed"
                and (workspace / "src" / "doctor_asset.py").exists()
                and doctor_rule_passed(write_result),
                doctor_result_detail(write_result),
            )
        )

        run_task(
            "doctor source",
            workspace=workspace,
            run_id="doctor-source",
            write_path="src/resume_asset.py",
            write_content="ready = True\n",
        )
        resume_result = run_task(
            "doctor resume",
            workspace=workspace,
            run_id="doctor-resume",
            resume_from_run_id="doctor-source",
            write_path="src/resume_asset.py",
            write_content="ready = False\n",
        )
        checks.append(
            doctor_check(
                "resume_skip",
                resume_result["status"] == "skipped"
                and resume_result["reason"] == "resumed_asset_ready"
                and (workspace / "src" / "resume_asset.py").read_text(encoding="utf-8") == "ready = True\n"
                and doctor_rule_passed(resume_result),
                doctor_result_detail(resume_result),
            )
        )

        outside = workspace.parent / "onecode-doctor-outside.txt"
        if outside.exists():
            outside.unlink()
        breach_result = run_task(
            "doctor breach",
            workspace=workspace,
            run_id="doctor-breach",
            write_path="../onecode-doctor-outside.txt",
            write_content="blocked\n",
        )
        checks.append(
            doctor_check(
                "sovereignty_breach",
                breach_result["status"] == "halted"
                and breach_result["reason"] == "sovereignty_breach"
                and not outside.exists()
                and doctor_rule_passed(breach_result),
                doctor_result_detail(breach_result),
            )
        )

        timeout_result = run_task(
            "doctor timeout",
            workspace=workspace,
            run_id="doctor-timeout",
            http_timeout_seconds=0.01,
            simulated_action_seconds=0.05,
        )
        checks.append(
            doctor_check(
                "http_timeout",
                timeout_result["status"] == "halted"
                and timeout_result["reason"] == "http_timeout"
                and doctor_rule_passed(timeout_result),
                doctor_result_detail(timeout_result),
            )
        )

    return {"status": "ok" if all(check["passed"] for check in checks) else "failed", "checks": checks}


def delivery_summary(ledger: dict) -> dict[str, int | str]:
    return IchingKernel.delivery_decision(
        status=ledger.get("status"),
        requested_count=ledger.get("requested_count"),
        completed_count=ledger.get("completed_count"),
        skipped_count=ledger.get("skipped_count"),
        failed_count=ledger.get("failed_count"),
    )


def ledger_history_present(ledger_path: str | None) -> bool:
    if not isinstance(ledger_path, str):
        return False
    return Path(ledger_path).with_suffix(".jsonl").exists()


def task_completion_evidence(result: dict, verifier_results: list[dict]) -> dict:
    manifest_path = result.get("manifest_path")
    ledger_path = result.get("ledger_path")
    assets_complete = (
        result.get("status") == "completed"
        and result.get("failed_count") == 0
        and result.get("requested_count")
        == result.get("completed_count", 0) + result.get("skipped_count", 0)
    )
    verifiers_passed = all(verifier.get("status") == "passed" for verifier in verifier_results)
    return {
        "assets_complete": assets_complete,
        "verifiers_passed": verifiers_passed,
        "ledger_present": isinstance(ledger_path, str) and Path(ledger_path).exists(),
        "ledger_history_present": ledger_history_present(ledger_path),
        "manifest_present": isinstance(manifest_path, str) and Path(manifest_path).exists(),
        "checkpoint_count": len(result.get("assets", [])) if isinstance(result.get("assets"), list) else 0,
    }


def apply_verifier_evidence(result: dict, workspace: Path, verifier_results: list) -> dict:
    verifier_dicts = [verifier.to_dict() for verifier in verifier_results]
    return apply_verifier_evidence_from_dicts(result, workspace, verifier_dicts)


def apply_verifier_evidence_from_dicts(result: dict, workspace: Path, verifier_dicts: list[dict]) -> dict:
    first_failure = next((verifier for verifier in verifier_dicts if verifier["status"] != "passed"), None)
    evidence = task_completion_evidence(result, verifier_dicts)
    task_status = task_status_from_verifier_dicts(result, verifier_dicts)
    enhanced = {
        **result,
        "verifier_results": verifier_dicts,
        "task_completion_evidence": evidence,
        "delivery_status": "deliverable" if first_failure is None and evidence["assets_complete"] else "blocked",
        **task_status,
    }
    if first_failure is not None:
        enhanced = {
            **enhanced,
            "status": "halted",
            "reason": first_failure["reason"],
            "partial": True,
        }
    context = create_context(
        workspace_root=workspace,
        http_timeout_seconds=60,
        run_id=enhanced["run_id"],
        resume_from_run_id=enhanced.get("resumed_from"),
    )
    write_ledger(context, enhanced)
    return enhanced


def task_status_from_verifier_dicts(result: dict, verifier_dicts: list[dict]) -> dict:
    status_codes = [
        asset.get("raw_status_code")
        for asset in result.get("assets", [])
        if isinstance(asset, dict) and isinstance(asset.get("raw_status_code"), int)
    ]
    for verifier in verifier_dicts:
        status_codes.append(
            IchingKernel.classify_outcome(
                "completed" if verifier.get("status") == "passed" else "halted",
                verifier.get("reason"),
            )
        )
    entropy = IchingKernel.entropy_regulated_status(status_codes)
    status_code = int(entropy["status_code"])
    transition = IchingKernel.transition(status_code)
    return {
        "task_status_code": status_code,
        "task_transition_action": transition.action,
        "task_transition_reason": transition.reason,
        "task_dispatch_decision": IchingKernel.dispatch_decision(transition),
        "task_entropy": entropy["entropy"],
        "task_entropy_decision": entropy["decision"],
        "task_entropy_reason": entropy.get("reason"),
    }


def verifier_dicts(verifier_results: list) -> list[dict]:
    return [verifier.to_dict() if hasattr(verifier, "to_dict") else dict(verifier) for verifier in verifier_results]


def verifier_failure(verifier_results: list[dict]) -> dict | None:
    return next((verifier for verifier in verifier_results if verifier.get("status") != "passed"), None)


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


def write_result_ledger(workspace: Path, result: dict) -> dict:
    context = create_context(
        workspace_root=workspace,
        http_timeout_seconds=60,
        run_id=result["run_id"],
        resume_from_run_id=result.get("resumed_from"),
    )
    write_ledger(context, result)
    return result


def align_counts_with_manifest(workspace: Path, result: dict) -> dict:
    manifest_path = result.get("manifest_path")
    if not isinstance(manifest_path, str) or not Path(manifest_path).exists():
        return result
    manifest, _, _ = read_json(Path(manifest_path))
    checkpoints = manifest.get("checkpoints") if isinstance(manifest, dict) else None
    if not isinstance(checkpoints, list):
        return result
    completed_count = sum(1 for checkpoint in checkpoints if checkpoint.get("status") == "completed")
    skipped_count = sum(1 for checkpoint in checkpoints if checkpoint.get("status") == "skipped")
    failed_count = sum(1 for checkpoint in checkpoints if checkpoint.get("status") in {"denied", "halted"})
    return {
        **result,
        "requested_count": len(checkpoints),
        "completed_count": completed_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
    }


def apply_task_resume_evidence(result: dict, workspace: Path, resume_summary: Any | None) -> dict:
    if resume_summary is None:
        return result
    enhanced = {**result, **resume_summary.to_dict()}
    write_result_ledger(workspace, enhanced)
    return enhanced


def halted_task_resume_result(
    workspace: Path,
    run_id: str | None,
    resume_from_run_id: str,
    resume_summary: Any,
) -> dict:
    first_halt = next(
        (decision for decision in resume_summary.decisions if decision.kind == "halt"),
        None,
    )
    context = create_context(
        workspace_root=workspace,
        run_id=run_id,
        resume_from_run_id=resume_from_run_id,
    )
    result = {
        "run_id": context.run_id,
        "status": "halted",
        "state": "000000",
        "manifest_path": str(context.manifest_path),
        "ledger_path": str(context.evidence_root / "ledger.json"),
        "partial": True,
        "reason": first_halt.reason if first_halt is not None else "task_resume_halt",
        "decision": "halted",
        "intent_type": "task_resume",
        "payload": {},
        "resumed_from": resume_from_run_id,
        "resumed": False,
        "assets": [],
        "requested_count": 0,
        "completed_count": 0,
        "skipped_count": 0,
        "failed_count": 1,
        **resume_summary.to_dict(),
    }
    write_ledger(context, result)
    return result


def checkpoint_asset_path(payload: dict | None, workspace_root: Path) -> str | None:
    if not isinstance(payload, dict) or not isinstance(payload.get("path"), str):
        return None
    path = Path(payload["path"])
    if not path.is_absolute():
        return payload["path"]
    try:
        return str(path.resolve().relative_to(workspace_root))
    except ValueError:
        return None


def checkpoint_assets(checkpoints: list[dict], workspace_root: Path) -> list[dict]:
    assets = []
    for checkpoint in checkpoints:
        checkpoint_payload, _, _ = read_json(Path(checkpoint["path"]))
        payload = checkpoint_payload.get("payload") if isinstance(checkpoint_payload, dict) else None
        assets.append(
            {
                "turn_index": checkpoint.get("turn_index"),
                "status": checkpoint.get("status"),
                "reason": checkpoint.get("reason"),
                "intent_type": checkpoint.get("intent_type"),
                "decision": checkpoint.get("decision"),
                "path": checkpoint_asset_path(payload, workspace_root),
                "iching_status_code": checkpoint.get("iching_status_code"),
            }
        )
    return assets


TASK_INSPECT_FIELDS = [
    "verifier_results",
    "task_status_code",
    "task_transition_action",
    "task_transition_reason",
    "task_dispatch_decision",
    "task_entropy",
    "task_entropy_decision",
    "task_entropy_reason",
    "task_completion_evidence",
    "task_resume_decisions",
    "task_resume_status_code",
    "task_resume_transition_action",
    "task_resume_transition_reason",
    "task_resume_dispatch_decision",
    "repair_attempt_count",
    "repaired",
    "initial_verifier_results",
    "repair_verifier_results",
    "repair_results",
    "repair_rejected_reason",
    "repair_prompt_evidence",
]


def optional_task_inspect_fields(ledger: dict) -> dict:
    return {field: ledger[field] for field in TASK_INSPECT_FIELDS if field in ledger}


def read_global_wal_segment(path: Path) -> tuple[list[dict] | None, str | None]:
    if not path.exists():
        return [], None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None, "global_wal_unreadable"
    entries = []
    previous_hash = None
    for line in lines:
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            return None, "invalid_global_wal_json"
        if not isinstance(value, dict):
            return None, "invalid_global_wal_entry"
        if "hash" in value or "prev" in value:
            if value.get("prev") != previous_hash:
                return None, "global_wal_chain_prev_mismatch"
            expected_hash = wal_entry_hash(value)
            if value.get("hash") != expected_hash:
                return None, "global_wal_chain_hash_mismatch"
            previous_hash = expected_hash
        value = {**value, "_wal_path": str(path)}
        entries.append(value)
    return entries, None


def read_global_wal_entries(workspace: Path) -> tuple[list[dict] | None, str | None, str | None]:
    entries = []
    for wal_path in global_wal_paths(workspace):
        segment_entries, corrupt_reason = read_global_wal_segment(wal_path)
        if corrupt_reason is not None or segment_entries is None:
            return None, str(wal_path), corrupt_reason
        entries.extend(segment_entries)
    return entries, None, None


def read_global_wal_run_entry(workspace: Path, run_id: str) -> tuple[dict | None, str | None, str | None]:
    entries, corrupt_path, corrupt_reason = read_global_wal_entries(workspace)
    if corrupt_path is not None or entries is None:
        return None, corrupt_path, corrupt_reason
    matched = None
    for value in entries:
        if value.get("rid") == run_id:
            matched = value
    return matched, None, None


def inspect_global_wal_run(workspace: Path, run_id: str) -> tuple[int, dict] | None:
    entry, corrupt_path, corrupt_reason = read_global_wal_run_entry(workspace, run_id)
    wal_path = workspace.resolve() / ".onecode" / "global-ledger.jsonl"
    if corrupt_path is not None:
        return 1, {
            "run_id": run_id,
            "status": "corrupt",
            "corrupt_path": corrupt_path,
            "corrupt_reason": corrupt_reason,
            "wal_path": str(wal_path),
        }
    if entry is None or entry.get("em") != "wal":
        return None
    entry_wal_path = entry.get("_wal_path") if isinstance(entry.get("_wal_path"), str) else str(wal_path)
    ledger = {
        "status": entry.get("st"),
        "requested_count": entry.get("rc"),
        "completed_count": entry.get("cc"),
        "skipped_count": entry.get("sc"),
        "failed_count": entry.get("fc"),
    }
    return 0, {
        "run_id": run_id,
        "status": entry.get("st"),
        "partial": entry.get("pc"),
        "reason": entry.get("rs"),
        "evidence_mode": "wal",
        "requested_count": entry.get("rc"),
        "completed_count": entry.get("cc"),
        "skipped_count": entry.get("sc"),
        "failed_count": entry.get("fc"),
        "checkpoint_count": None,
        "iching_status_code": entry.get("isc"),
        "iching_transition_action": entry.get("ita"),
        "profile_sha256": entry.get("ph"),
        "profile_registry_ref": entry.get("pr"),
        "manifest_path": entry.get("mp"),
        "ledger_path": entry.get("lp"),
        "wal_path": entry_wal_path,
    } | delivery_summary(ledger)


def global_wal_run_summaries(workspace: Path) -> tuple[list[dict] | None, dict | None]:
    entries, corrupt_path, corrupt_reason = read_global_wal_entries(workspace)
    wal_path = workspace.resolve() / ".onecode" / "global-ledger.jsonl"
    if corrupt_path is not None or entries is None:
        return None, {
            "run_id": None,
            "status": "corrupt",
            "corrupt_path": corrupt_path,
            "corrupt_reason": corrupt_reason,
            "wal_path": str(wal_path),
        }
    latest_by_run_id = {}
    for entry in entries:
        run_id = entry.get("rid")
        if isinstance(run_id, str) and entry.get("em") == "wal":
            latest_by_run_id[run_id] = entry
    summaries = []
    for run_id in sorted(latest_by_run_id):
        inspected = inspect_global_wal_run(workspace, run_id)
        if inspected is not None:
            _, summary = inspected
            summaries.append(summary)
    return summaries, None


def inspect_run(workspace: Path, run_id: str) -> tuple[int, dict]:
    evidence_root = workspace.resolve() / ".onecode" / "runs" / run_id
    manifest_path = evidence_root / "manifest.json"
    ledger_path = evidence_root / "ledger.json"
    manifest, corrupt_manifest_path, corrupt_manifest_reason = read_json(manifest_path)
    ledger, corrupt_ledger_path, corrupt_ledger_reason = read_json(ledger_path)
    corrupt_path = corrupt_manifest_path or corrupt_ledger_path
    corrupt_reason = corrupt_manifest_reason or corrupt_ledger_reason
    if corrupt_path is not None:
        return 1, {
            "run_id": run_id,
            "status": "corrupt",
            "corrupt_path": corrupt_path,
            "corrupt_reason": corrupt_reason,
            "manifest_path": str(manifest_path),
            "ledger_path": str(ledger_path),
        }
    if manifest is None or ledger is None:
        wal_result = inspect_global_wal_run(workspace, run_id)
        if wal_result is not None:
            return wal_result
        return 1, {
            "run_id": run_id,
            "status": "missing",
            "manifest_path": str(manifest_path),
            "ledger_path": str(ledger_path),
        }
    corrupt_path, corrupt_reason = validate_status_document(manifest, manifest_path)
    if corrupt_path is None:
        corrupt_path, corrupt_reason = validate_status_document(ledger, ledger_path)
    if corrupt_path is not None:
        return 1, {
            "run_id": run_id,
            "status": "corrupt",
            "corrupt_path": corrupt_path,
            "corrupt_reason": corrupt_reason,
            "manifest_path": str(manifest_path),
            "ledger_path": str(ledger_path),
        }
    if manifest["status"] != ledger["status"]:
        return 1, {
            "run_id": run_id,
            "status": "corrupt",
            "corrupt_path": str(ledger_path),
            "corrupt_reason": "status_mismatch",
            "manifest_path": str(manifest_path),
            "ledger_path": str(ledger_path),
        }
    corrupt_path, corrupt_reason = validate_ledger_counts(ledger, ledger_path)
    if corrupt_path is not None:
        return 1, {
            "run_id": run_id,
            "status": "corrupt",
            "corrupt_path": corrupt_path,
            "corrupt_reason": corrupt_reason,
            "manifest_path": str(manifest_path),
            "ledger_path": str(ledger_path),
        }
    if "checkpoints" not in manifest:
        return 1, {
            "run_id": run_id,
            "status": "corrupt",
            "corrupt_path": str(manifest_path),
            "corrupt_reason": "missing_checkpoints",
            "manifest_path": str(manifest_path),
            "ledger_path": str(ledger_path),
        }
    checkpoints = manifest["checkpoints"]
    if not isinstance(checkpoints, list):
        return 1, {
            "run_id": run_id,
            "status": "corrupt",
            "corrupt_path": str(manifest_path),
            "corrupt_reason": "invalid_checkpoints",
            "manifest_path": str(manifest_path),
            "ledger_path": str(ledger_path),
        }
    if not all(isinstance(checkpoint, dict) for checkpoint in checkpoints):
        return 1, {
            "run_id": run_id,
            "status": "corrupt",
            "corrupt_path": str(manifest_path),
            "corrupt_reason": "invalid_checkpoint_entry",
            "manifest_path": str(manifest_path),
            "ledger_path": str(ledger_path),
        }
    corrupt_path, corrupt_reason = validate_checkpoint_evidence(checkpoints, manifest_path)
    if corrupt_path is not None:
        return 1, {
            "run_id": run_id,
            "status": "corrupt",
            "corrupt_path": corrupt_path,
            "corrupt_reason": corrupt_reason,
            "manifest_path": str(manifest_path),
            "ledger_path": str(ledger_path),
        }
    if all(field in ledger for field in LEDGER_COUNT_FIELDS):
        resolved_count = ledger["completed_count"] + ledger["skipped_count"] + ledger["failed_count"]
        if resolved_count != len(checkpoints):
            return 1, {
                "run_id": run_id,
                "status": "corrupt",
                "corrupt_path": str(manifest_path),
                "corrupt_reason": "checkpoint_count_mismatch",
                "manifest_path": str(manifest_path),
                "ledger_path": str(ledger_path),
            }
    trace_value = ledger.get("trace_path")
    if isinstance(trace_value, str):
        corrupt_path, corrupt_reason = validate_trace_completion(ledger, Path(trace_value))
        if corrupt_path is not None:
            return 1, {
                "run_id": run_id,
                "status": "corrupt",
                "corrupt_path": corrupt_path,
                "corrupt_reason": corrupt_reason,
                "manifest_path": str(manifest_path),
                "ledger_path": str(ledger_path),
            }
    corrupt_path, corrupt_reason = validate_evidence_chain(evidence_root / "evidence-chain.jsonl")
    if corrupt_path is not None:
        return 1, {
            "run_id": run_id,
            "status": "corrupt",
            "corrupt_path": corrupt_path,
            "corrupt_reason": corrupt_reason,
            "manifest_path": str(manifest_path),
            "ledger_path": str(ledger_path),
        }
    workspace_root = (
        Path(manifest["workspace_root"]).resolve()
        if isinstance(manifest.get("workspace_root"), str)
        else workspace.resolve()
    )
    return 0, {
        "run_id": run_id,
        "status": ledger.get("status", manifest.get("status")),
        "partial": ledger.get("partial", manifest.get("partial")),
        "reason": ledger.get("reason", manifest.get("reason")),
        "resumed_from": ledger.get("resumed_from", manifest.get("resumed_from")),
        "plan_path": ledger.get("plan_path"),
        "plan_sha256": ledger.get("plan_sha256"),
        "plan_asset_count": ledger.get("plan_asset_count"),
        "requested_count": ledger.get("requested_count"),
        "completed_count": ledger.get("completed_count"),
        "skipped_count": ledger.get("skipped_count"),
        "failed_count": ledger.get("failed_count"),
        "checkpoint_count": len(checkpoints),
        "iching_status_code": ledger.get("iching_status_code", manifest.get("iching_status_code")),
        "iching_transition_action": ledger.get(
            "iching_transition_action", manifest.get("iching_transition_action")
        ),
        "iching_transition_reason": ledger.get(
            "iching_transition_reason", manifest.get("iching_transition_reason")
        ),
        "assets": checkpoint_assets(checkpoints, workspace_root),
        "manifest_path": str(manifest_path),
        "ledger_path": str(ledger_path),
    } | delivery_summary(ledger) | optional_task_inspect_fields(ledger)


def list_runs(workspace: Path) -> dict:
    resolved_workspace = workspace.resolve()
    runs_root = resolved_workspace / ".onecode" / "runs"
    runs = []
    seen_run_ids = set()
    if runs_root.exists():
        for run_dir in sorted(path for path in runs_root.iterdir() if path.is_dir()):
            _, summary = inspect_run(resolved_workspace, run_dir.name)
            runs.append(summary)
            if isinstance(summary.get("run_id"), str):
                seen_run_ids.add(summary["run_id"])
    wal_summaries, corrupt_summary = global_wal_run_summaries(resolved_workspace)
    if corrupt_summary is not None:
        runs.append(corrupt_summary)
    else:
        for summary in wal_summaries or []:
            run_id = summary.get("run_id")
            if isinstance(run_id, str) and run_id not in seen_run_ids:
                runs.append(summary)
    runs.sort(key=lambda run: str(run.get("run_id") or ""))
    return {"workspace": str(workspace), "runs": runs}


def run_plan_verifier_policy_path(workspace: Path, explicit_policy: str | None) -> Path:
    if explicit_policy is not None:
        return Path(explicit_policy)
    return workspace / DEFAULT_VERIFIER_POLICY_PATH


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.subcommand == "inspect":
        exit_code, result = inspect_run(Path(args.workspace), args.run_id)
        print(json.dumps(attach_shell_projection(result), ensure_ascii=False, sort_keys=True))
        return exit_code

    if args.subcommand == "list-runs":
        result = list_runs(Path(args.workspace))
        print(json.dumps(attach_shell_projection_to_runs_payload(result), ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "list-verifier-presets":
        print(json.dumps(verifier_policy_presets_summary(), ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "init-verifier-policy":
        try:
            result = write_verifier_policy(
                workspace=Path(args.workspace),
                output=args.output,
                preset_ids=args.preset,
                force=args.force,
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "tui":
        from onecode.tui.app import run_tui
        run_tui(
            workspace=Path(args.workspace) if args.workspace is not None else None,
            model=args.model,
            provider_kind=args.provider,
        )
        return 0

    if args.subcommand == "serve":
        from onecode.web.api import run_server

        if args.allow_unauthenticated_local:
            os.environ["ONECODE_ALLOW_UNAUTHENTICATED"] = "true"
        run_server(host=args.host, port=args.port)
        return 0

    if args.subcommand == "shell":
        from onecode.shell_launcher import config_from_args, launch_shell

        try:
            return launch_shell(config_from_args(args))
        except (FileNotFoundError, RuntimeError) as exc:
            parser.error(str(exc))

    if args.subcommand == "doctor":
        result = run_doctor()
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] == "ok" else 1

    if args.subcommand == "audit-self":
        result = audit_self(Path.cwd(), run_doctor)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] == "ok" else 1

    if args.subcommand == "math-audit":
        graph = IchingKernel.transition_graph()
        attractors = IchingKernel.attractor_analysis()
        stability = IchingKernel.stability_analysis()
        topology = IchingKernel.topology_certificate()
        lyapunov = IchingKernel.lyapunov_certificate()
        totality = IchingKernel.totality_certificate()
        safety_dominance = IchingKernel.safety_dominance_certificate()
        collision_risk = IchingKernel.collision_risk_certificate()
        entropy_gate = {
            "low_entropy_halt_probe": IchingKernel.entropy_gate_certificate(
                [
                    IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN),
                    IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN),
                    IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN),
                ]
            ),
            "exploration_probe": IchingKernel.entropy_gate_certificate(
                [
                    IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.KUN),
                    IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN),
                    IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.ZHEN),
                    IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.QIAN),
                ]
            ),
        }
        energies = [IchingKernel.lyapunov_energy(status_code) for status_code in range(64)]
        result = {
            "status": "ok",
            "state_count": len(graph),
            "transition_count": len(graph),
            "attractor_count": len(attractors["attractors"]),
            "attractors": attractors["attractors"],
            "unclassified_state_count": len(attractors["unclassified_states"]),
            "lyapunov_min": min(energies),
            "lyapunov_max": max(energies),
            "stability": stability,
            "topology": topology,
            "lyapunov": lyapunov,
            "entropy_gate": entropy_gate,
            "totality": totality,
            "safety_dominance": safety_dominance,
            "collision_risk": collision_risk,
            "accepted_mappings": [
                "transition_graph",
                "attractor_analysis",
                "stability_analysis",
                "topology_certificate",
                "lyapunov_certificate",
                "entropy_gate_certificate",
                "totality_certificate",
                "safety_dominance_certificate",
                "collision_risk_certificate",
                "lyapunov_energy",
                "state_distribution_entropy",
                "hysteresis_gate",
            ],
            "reference_only": [
                "probabilistic_sampling",
                "runtime_gain_learning",
                "multi_agent_tensor_product",
            ],
        }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "shell-schema":
        print(json.dumps(shell_projection_schema(), ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "config":
        if args.config_action == "set-model":
            result = write_model_config(
                endpoint=args.endpoint,
                api_key=args.api_key,
                model=args.model,
                provider=args.provider,
            )
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 0
        if args.config_action == "show":
            print(json.dumps(read_model_config(), ensure_ascii=False, sort_keys=True))
            return 0
        if args.config_action == "discover-models":
            print(json.dumps(discover_models(args.endpoint, args.api_key), ensure_ascii=False, sort_keys=True))
            return 0

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
            result = run_sandbox_smoke(
                SandboxConfig(
                    workspace=Path(args.workspace),
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
