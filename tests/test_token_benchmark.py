"""Regression tests for scripts/token_projection_benchmark.py and symbolic telemetry toggle."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parent.parent


class TokenProjectionBenchmarkTests(unittest.TestCase):
    def test_token_projection_benchmark_cli_json_is_deterministic_and_honest(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT / "src")
        completed = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "token_projection_benchmark.py"), "--json"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(completed.stdout)

        self.assertFalse(payload["api_keys_required"])
        self.assertFalse(payload["claims_mainstream_parity"])
        self.assertFalse(payload["bundled_archives"]["raw_comparator_logs_bundled"])

        ckpt = payload["checkpoint_telemetry_decoupling"]
        self.assertEqual(ckpt["turns"], 8)
        self.assertGreater(ckpt["saved_bytes"], 0)
        self.assertGreater(ckpt["reduction_pct"], 80.0)

        proj = payload["shell_projection_compression"]
        self.assertEqual(len(proj["scenarios"]), 4)
        self.assertGreater(proj["overall_reduction_pct"], 85.0)
        self.assertGreater(len(payload["bundled_archives"]["bundled_archive_jsonl"]), 0)


if __name__ == "__main__":
    unittest.main()
