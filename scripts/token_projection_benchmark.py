#!/usr/bin/env python3
"""Zero-API-key reproducible benchmark for OneCode checkpoint telemetry decoupling,
shell_projection context compression, and bundled archive manifest verification.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from onecode.kernel.checkpoint import write_checkpoint  # noqa: E402
from onecode.kernel.context import create_context  # noqa: E402
from onecode.kernel.shell_projection import project_run_to_shell  # noqa: E402


@contextmanager
def _symbolic_telemetry_env(enabled: bool) -> Iterator[None]:
    key = "ONECODE_SYMBOLIC_TELEMETRY"
    prior = os.environ.get(key)
    os.environ[key] = "1" if enabled else "0"
    try:
        yield
    finally:
        if prior is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = prior


def _ensure_companion_extension_for_benchmark() -> bool:
    """Attach optional `onecode-symbolic-audit` companion package if present in repo."""
    from onecode.kernel.hexagram import IchingKernel
    from onecode.kernel.symbolic_telemetry import attach_symbolic_extension, symbolic_extension_loaded

    if symbolic_extension_loaded():
        return True
    companion_src = REPO_ROOT / "packages" / "onecode-symbolic-audit" / "src"
    if companion_src.is_dir():
        companion_str = str(companion_src)
        if companion_str not in sys.path:
            sys.path.insert(0, companion_str)
        return attach_symbolic_extension(IchingKernel)
    return False


def benchmark_checkpoint_telemetry_decoupling(turns: int = 8) -> dict[str, Any]:
    """Compare per-turn serialized telemetry size under default vs opt-in symbolic mode."""
    sample_states = [39, 40, 47, 7, 15, 31, 62, 63]
    extension_loaded = _ensure_companion_extension_for_benchmark()

    def _measure(enabled: bool) -> tuple[int, list[int]]:
        sizes: list[int] = []
        with tempfile.TemporaryDirectory() as tmp, _symbolic_telemetry_env(enabled):
            ctx = create_context(Path(tmp), run_id=f"bench-sym-{int(enabled)}")
            for idx in range(turns):
                state = sample_states[idx % len(sample_states)]
                chk = write_checkpoint(
                    context=ctx,
                    payload={"turn": idx + 1, "op": "patch_text", "path": "src/engine.py"},
                    next_state=state,
                    status="completed",
                    partial=False,
                    reason=None,
                    iching_status_code=state,
                )
                data = json.loads(chk.read_text(encoding="utf-8"))
                telemetry_json = json.dumps(data.get("telemetry", {}), ensure_ascii=False, sort_keys=True)
                sizes.append(len(telemetry_json.encode("utf-8")))
        return sum(sizes), sizes

    default_total_bytes, default_per_turn = _measure(False)
    symbolic_total_bytes, symbolic_per_turn = _measure(True)
    saved_bytes = symbolic_total_bytes - default_total_bytes
    reduction_pct = round((saved_bytes / symbolic_total_bytes) * 100.0, 2) if symbolic_total_bytes else 0.0
    return {
        "turns": turns,
        "symbolic_extension_loaded": extension_loaded,
        "default_telemetry_bytes": default_total_bytes,
        "symbolic_telemetry_bytes": symbolic_total_bytes,
        "saved_bytes": saved_bytes,
        "reduction_pct": reduction_pct,
        "default_avg_bytes_per_turn": round(default_total_bytes / max(turns, 1), 1),
        "symbolic_avg_bytes_per_turn": round(symbolic_total_bytes / max(turns, 1), 1),
        "default_per_turn_bytes": default_per_turn,
        "symbolic_per_turn_bytes": symbolic_per_turn,
    }


def _build_synthetic_reference_runs() -> list[dict[str, Any]]:
    """Build representative multi-turn synthetic runs for projection compression measurement."""
    scenarios = [
        ("packml-packaging-fsm", "patch_text", "src/packml_machine.py", 10),
        ("tep-chemical-safety-interlock", "verifier_run", "src/reactor_interlock.py", 10),
        ("modbus-iiot-gateway", "patch_text", "src/modbus_gateway.py", 10),
        ("repo-fault-repair", "repair_patch", "src/billing/invoice.py", 6),
    ]
    runs: list[dict[str, Any]] = []
    for scenario_id, op_name, target_path, step_count in scenarios:
        step_results = []
        runner_results = []
        for idx in range(1, step_count + 1):
            stdout_sample = "\n".join(
                [
                    f"[step {idx}/{step_count}] scanning {target_path} ast definitions and call graph...",
                    f"[verifier {idx}] AssertionError: expected bounded transition state for cycle {idx}",
                    "diff context: " + ("x = validate_bound(payload[key])\n" * 6),
                ]
            )
            step_results.append(
                {
                    "step_id": f"step-{idx:02d}",
                    "status": "completed",
                    "reason": None,
                    "tool_results": [
                        {
                            "tool_name": op_name,
                            "success": True,
                            "stdout_tail": stdout_sample,
                            "stderr_tail": "",
                        }
                    ],
                }
            )
            runner_results.append(
                {
                    "status": "completed",
                    "reason": None,
                    "payload": {
                        "path": target_path,
                        "search_block": "def step():\n    return None\n" * 3,
                        "replace_block": "def step():\n    return state_ok()\n" * 3,
                        "stdout_excerpt": stdout_sample,
                    },
                }
            )
        runs.append(
            {
                "run_id": f"synthetic-{scenario_id}",
                "status": "completed",
                "partial": False,
                "iching_status_code": 39,
                "iching_transition_action": "continue",
                "iching_transition_reason": "synthetic_benchmark_transition",
                "dispatch_decision": "continue",
                "requested_count": step_count,
                "completed_count": step_count,
                "skipped_count": 0,
                "failed_count": 0,
                "project_context_status": "ok",
                "runtime_config_status": "ok",
                "skill_context_status": "ok",
                "recovery_action": "inspect",
                "ledger_path": f".onecode/runs/{scenario_id}/ledger.json",
                "manifest_path": f".onecode/runs/{scenario_id}/manifest.json",
                "trace_path": f".onecode/runs/{scenario_id}/trace.jsonl",
                "balance_mutation_summary": {
                    "changed_asset_count": 1,
                    "total_changed_line_count": step_count * 4,
                    "changed_bands": ["inner"],
                    "latest_before_status_code": 40,
                    "latest_after_status_code": 39,
                },
                "execution_trace": {
                    "step_results": step_results,
                    "runner_results": runner_results,
                    "workspace_excerpt": {target_path: ("# reference implementation line\n" * 40)},
                },
                "verifier_results": [
                    {
                        "id": f"verify-{scenario_id}",
                        "status": "passed",
                        "stdout_tail": "\n".join(f"test_case_{i} ... ok" for i in range(1, 25)),
                        "stderr_tail": "",
                    }
                ],
            }
        )
    return runs


def benchmark_shell_projection_compression() -> dict[str, Any]:
    """Measure UTF-8 JSON bytes & heuristic BPE (~4 chars/token) across raw vs shell_projection."""
    per_scenario: list[dict[str, Any]] = []
    total_raw_bytes = 0
    total_proj_bytes = 0
    for run in _build_synthetic_reference_runs():
        raw_json = json.dumps(run, ensure_ascii=False, sort_keys=True)
        proj = project_run_to_shell(run)
        proj_json = json.dumps(proj, ensure_ascii=False, sort_keys=True)
        raw_bytes = len(raw_json.encode("utf-8"))
        proj_bytes = len(proj_json.encode("utf-8"))
        total_raw_bytes += raw_bytes
        total_proj_bytes += proj_bytes
        per_scenario.append(
            {
                "run_id": run["run_id"],
                "raw_bytes": raw_bytes,
                "projected_bytes": proj_bytes,
                "raw_est_tokens_chars_div_4": round(len(raw_json) / 4.0, 1),
                "projected_est_tokens_chars_div_4": round(len(proj_json) / 4.0, 1),
                "reduction_pct": round((1.0 - (proj_bytes / raw_bytes)) * 100.0, 2) if raw_bytes else 0.0,
            }
        )
    overall_reduction = round((1.0 - (total_proj_bytes / total_raw_bytes)) * 100.0, 2) if total_raw_bytes else 0.0
    return {
        "benchmark_scope": "synthetic_multi_turn_run_projection",
        "token_estimator": "heuristic_chars_div_4",
        "total_raw_bytes": total_raw_bytes,
        "total_projected_bytes": total_proj_bytes,
        "overall_reduction_pct": overall_reduction,
        "scenarios": per_scenario,
    }


def audit_bundled_archives(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Inspect bundled benchmark JSONL/JSON manifests in the repository."""
    archive_dir = repo_root / "benchmarks" / "archive"
    archive_files = (
        sorted(archive_dir.glob("*.jsonl"))
        if archive_dir.is_dir()
        else sorted(repo_root.glob("results-*.jsonl"))
    )
    jsonl_summaries: list[dict[str, Any]] = []
    for path in archive_files:
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        passed = sum(
            1
            for rec in records
            if rec.get("passed") is True or rec.get("status") == "completed" or rec.get("host_reward") == 1.0
        )
        jsonl_summaries.append(
            {
                "file": path.relative_to(repo_root).as_posix(),
                "records": len(records),
                "passed_count": passed,
                "models": sorted({str(rec.get("model")) for rec in records if rec.get("model")}),
            }
        )

    swebench_report_path = repo_root / "benchmarks" / "reports" / "swebench_agent_evaluation_report_v1.1.json"
    swebench_summary: dict[str, Any] = {}
    if swebench_report_path.is_file():
        report = json.loads(swebench_report_path.read_text(encoding="utf-8"))
        swebench_summary = {
            "total_evaluated": report.get("total_evaluated"),
            "resolved": report.get("resolved"),
            "resolve_rate": report.get("resolve_rate"),
            "total_input_tokens": report.get("total_input_tokens"),
            "total_output_tokens": report.get("total_output_tokens"),
        }

    return {
        "raw_comparator_logs_bundled": False,
        "note": (
            "External third-party comparator traces (e.g., raw Claude Code CLI session logs "
            "from industrial N100 test nodes) are not stored inside this public repository."
        ),
        "bundled_archive_jsonl": jsonl_summaries,
        "bundled_swebench_v1_1_summary": swebench_summary,
    }


def run_benchmark(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    return {
        "benchmark": "onecode_token_projection_and_telemetry_evidence",
        "api_keys_required": False,
        "claims_mainstream_parity": False,
        "checkpoint_telemetry_decoupling": benchmark_checkpoint_telemetry_decoupling(),
        "shell_projection_compression": benchmark_shell_projection_compression(),
        "bundled_archives": audit_bundled_archives(repo_root),
    }


def _render_markdown(report: dict[str, Any]) -> str:
    ckpt = report["checkpoint_telemetry_decoupling"]
    proj = report["shell_projection_compression"]
    arch = report["bundled_archives"]
    lines = [
        "# OneCode Zero-API Telemetry & Shell Projection Benchmark",
        "",
        "## 1. Checkpoint Telemetry Decoupling (`ONECODE_SYMBOLIC_TELEMETRY=0` vs `1`)",
        f"- Turns benchmarked: `{ckpt['turns']}`",
        f"- Default core telemetry total bytes: `{ckpt['default_telemetry_bytes']}` B (`{ckpt['default_avg_bytes_per_turn']}` B/turn)",
        f"- Opt-in symbolic telemetry total bytes: `{ckpt['symbolic_telemetry_bytes']}` B (`{ckpt['symbolic_avg_bytes_per_turn']}` B/turn)",
        f"- Bytes eliminated per checkpoint stream by default decoupling: `{ckpt['saved_bytes']}` B (`{ckpt['reduction_pct']}%` reduction)",
        "",
        "## 2. `shell_projection` Payload Compression (Synthetic Multi-Turn Runs)",
        f"- Token estimation note: exact UTF-8 byte sizes (`{proj['token_estimator']}` approximations listed below; zero live API calls)",
        f"- Total raw unprojected JSON: `{proj['total_raw_bytes']}` B -> projected shell state: `{proj['total_projected_bytes']}` B (`{proj['overall_reduction_pct']}%` reduction)",
        "",
        "| Synthetic Run ID | Raw Bytes | Projected Bytes | Raw Est. Tokens | Projected Est. Tokens | Reduction |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in proj["scenarios"]:
        lines.append(
            f"| `{item['run_id']}` | {item['raw_bytes']} | {item['projected_bytes']} | "
            f"{item['raw_est_tokens_chars_div_4']} | {item['projected_est_tokens_chars_div_4']} | "
            f"{item['reduction_pct']}% |"
        )
    lines.extend(
        [
            "",
            "## 3. Bundled Repository Archives & Provenance",
            f"- `raw_comparator_logs_bundled`: `{arch['raw_comparator_logs_bundled']}`",
            f"- Note: {arch['note']}",
        ]
    )
    for entry in arch["bundled_archive_jsonl"]:
        lines.append(
            f"- `{entry['file']}`: `{entry['passed_count']}/{entry['records']}` passed (models: {', '.join(entry['models']) or 'unknown'})"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproducible zero-API benchmark for OneCode telemetry decoupling and shell_projection.")
    parser.add_argument("--json", action="store_true", help="Emit structured JSON report.")
    args = parser.parse_args(argv)
    report = run_benchmark()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(_render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
