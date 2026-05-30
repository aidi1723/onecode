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
        try:
            output = _run_case(artifact, case.input, sandbox_policy.timeout_ms)
            passed = output == case.expected_output
            if not passed:
                error = f"expected {case.expected_output!r}, got {output!r}"
        except VerificationError as exc:
            error = str(exc)
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
import importlib.util
import json
import pathlib
import sys

artifact_path = pathlib.Path(sys.argv[1])
payload = json.loads(sys.argv[2])
spec = importlib.util.spec_from_file_location("capability_artifact", artifact_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
run = getattr(module, "run", None)
if not callable(run):
    raise RuntimeError("artifact must define callable run(input)")
result = run(payload)
print(json.dumps(result, sort_keys=True, separators=(",", ":")))
""".strip()

    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_path = Path(tmpdir) / "artifact.py"
        artifact_path.write_text(artifact, encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "-c", runner, str(artifact_path), json.dumps(input_value)],
            capture_output=True,
            text=True,
            timeout=timeout_ms / 1000,
            check=False,
        )

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
