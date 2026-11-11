from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from typing import Any


def _load_benchmark_module() -> Any:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "security_benchmark.py"
    spec = importlib.util.spec_from_file_location("onecode_security_benchmark", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load benchmark script: {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SecurityBenchmarkSuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.benchmark = _load_benchmark_module()

    def test_all_adversarial_security_cases_enforced(self) -> None:
        self.assertEqual(len(self.benchmark.SECURITY_CASES), 18)
        for case_id, category, attack_vector, fn in self.benchmark.SECURITY_CASES:
            with self.subTest(case_id=case_id, category=category, attack_vector=attack_vector):
                blocked, mechanism, observed = fn()
                self.assertTrue(
                    blocked,
                    msg=f"{case_id} ({mechanism}) failed to block/enforce: {observed}",
                )

    def test_security_benchmark_cli_json_report(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rc = self.benchmark.main(["--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["total"], 18)
        self.assertEqual(payload["blocked_or_enforced"], 18)
        self.assertEqual(payload["failed"], 0)
        self.assertEqual(payload["pass_rate_pct"], 100.0)
        self.assertEqual(len(payload["cases"]), 18)


if __name__ == "__main__":
    unittest.main()
