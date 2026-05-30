"""Verify Python capability artifacts with replayable eval packs."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict

from .eval_pack import EvalPack
from .manifest import CaseResult, SandboxPolicy, Scorecard


class VerificationError(Exception):
    """Raised when an artifact cannot be evaluated at all."""


def compute_artifact_sha256(artifact: str) -> str:
    return hashlib.sha256(artifact.encode("utf-8")).hexdigest()


def verify_artifact(
    artifact: str,
    eval_pack: EvalPack,
    sandbox_policy: SandboxPolicy,
) -> Scorecard:
    if not artifact.strip():
        raise VerificationError("artifact is empty")
    if len(eval_pack.cases) > sandbox_policy.max_cases:
        raise VerificationError("eval pack exceeds sandbox max_cases")

    artifact_sha256 = compute_artifact_sha256(artifact)
    case_results: list[CaseResult] = []

    for case in eval_pack.cases:
        start = time.monotonic()
        passed = False
        error = ""
        output = _run_case(artifact, case.input, sandbox_policy.timeout_ms)
        passed = output == case.expected_output
        if not passed:
            error = f"expected {case.expected_output!r}, got {output!r}"
        duration_ms = max(0, int((time.monotonic() - start) * 1000))
        case_results.append(
            CaseResult(
                name=case.name,
                passed=passed,
                duration_ms=duration_ms,
                error=error,
            )
        )

    cases_total = len(case_results)
    cases_passed = sum(1 for result in case_results if result.passed)
    avg_latency_ms = (
        int(sum(result.duration_ms for result in case_results) / cases_total)
        if cases_total
        else 0
    )
    return Scorecard(
        verified=cases_total > 0 and cases_passed == cases_total,
        pass_rate=cases_passed / cases_total if cases_total else 0.0,
        cases_total=cases_total,
        cases_passed=cases_passed,
        avg_latency_ms=avg_latency_ms,
        artifact_sha256=artifact_sha256,
        case_results=case_results,
    )


def _run_case(artifact: str, input_value: Dict[str, Any], timeout_ms: int) -> Dict[str, Any]:
    runner = """
import contextlib
import json
import os
import pathlib
import sys

artifact_path = pathlib.Path(sys.argv[1])
payload = json.loads(sys.argv[2])
namespace = {"__name__": "capability_artifact", "__file__": str(artifact_path)}
source = artifact_path.read_text(encoding="utf-8")
exec(compile(source, str(artifact_path), "exec"), namespace)
run = namespace.get("run")
if not callable(run):
    raise RuntimeError("artifact must define callable run(input)")
with open(os.devnull, "w", encoding="utf-8") as devnull:
    with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
        result = run(payload)
print(json.dumps(result, sort_keys=True, separators=(",", ":")))
""".strip()

    try:
        input_json = json.dumps(input_value)
    except (TypeError, ValueError) as exc:
        raise VerificationError(f"eval input is not json-serializable: {exc}") from exc

    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_path = Path(tmpdir) / "artifact.py"
        artifact_path.write_text(artifact, encoding="utf-8")
        try:
            completed = subprocess.run(
                [sys.executable, "-c", runner, str(artifact_path), input_json],
                capture_output=True,
                text=True,
                timeout=timeout_ms / 1000,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise VerificationError("artifact execution timed out") from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise VerificationError(detail or "artifact execution failed")
    try:
        output = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise VerificationError(f"artifact returned non-json output: {exc}") from exc
    if not isinstance(output, dict):
        raise VerificationError("artifact run(input) must return a JSON object")
    return output
