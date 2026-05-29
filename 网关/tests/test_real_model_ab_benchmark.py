from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from scripts import real_model_ab_benchmark


class RealModelABBenchmarkTest(unittest.TestCase):
    def test_readiness_fails_without_upstream_configuration(self):
        with TemporaryDirectory() as tmpdir:
            output_json = Path(tmpdir) / "report.json"
            output_md = Path(tmpdir) / "report.md"
            with patch.dict(
                "os.environ",
                {
                    "ONEWORD_UPSTREAM_API_KEY": "",
                    "OPENAI_API_KEY": "",
                    "ONEWORD_UPSTREAM_BASE_URL": "",
                    "OPENAI_BASE_URL": "",
                    "ONEWORD_BENCHMARK_MODEL": "",
                    "OPENAI_MODEL": "",
                },
                clear=False,
            ):
                result = subprocess.run(
                    [
                        sys.executable,
                        "scripts/real_model_ab_benchmark.py",
                        "--output-json",
                        str(output_json),
                        "--output-md",
                        str(output_md),
                        "--no-network",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    env={
                        key: value
                        for key, value in __import__("os").environ.items()
                        if key
                        not in {
                            "ONEWORD_UPSTREAM_API_KEY",
                            "OPENAI_API_KEY",
                            "ONEWORD_UPSTREAM_BASE_URL",
                            "OPENAI_BASE_URL",
                            "ONEWORD_BENCHMARK_MODEL",
                            "OPENAI_MODEL",
                        }
                    },
                )
            self.assertEqual(result.returncode, 2)
            payload = json.loads(output_json.read_text(encoding="utf-8"))
        self.assertFalse(payload["ready"])
        self.assertIn("OPENAI_API_KEY", " ".join(payload["missing"]))

    def test_usage_tokens_are_extracted_from_openai_response(self):
        payload = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        usage = real_model_ab_benchmark.extract_usage(payload)
        self.assertEqual(usage["prompt_tokens"], 10)
        self.assertEqual(usage["completion_tokens"], 5)
        self.assertEqual(usage["total_tokens"], 15)

    def test_light_suite_uses_zero_tool_prompts(self):
        prompts = real_model_ab_benchmark.PROMPT_SUITES["light"]

        self.assertEqual([prompt["task_id"] for prompt in prompts], ["LIGHT_EXPLAIN_ZERO_TOOL", "LIGHT_CLARIFY_ZERO_TOOL"])
        self.assertTrue(all(prompt["expected_guard"] == "zero_tool_bypass" for prompt in prompts))

    def test_run_pair_records_same_model_bare_and_guarded(self):
        responses = [
            {
                "choices": [{"message": {"content": "bare"}}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 7, "total_tokens": 27},
            },
            {
                "choices": [{"message": {"content": "guarded"}}],
                "usage": {"prompt_tokens": 80, "completion_tokens": 3, "total_tokens": 83},
                "yizijue_gateway": {"active_code": "查", "tool_guard": {"allowed": True}},
            },
        ]

        def fake_urlopen(request, timeout):
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            response.status = 200
            response.read.return_value = json.dumps(responses.pop(0)).encode("utf-8")
            return response

        with patch("scripts.real_model_ab_benchmark.urlrequest.urlopen", side_effect=fake_urlopen):
            row = real_model_ab_benchmark.run_benchmark_pair(
                prompt="查：只读检查",
                model="same-model",
                upstream_url="http://upstream.test/v1/chat/completions",
                gateway_url="http://gateway.test/v1/chat/completions",
                api_key="key",
                gateway_token="token",
                timeout=10,
            )

        self.assertEqual(row["model"], "same-model")
        self.assertEqual(row["bare"]["usage"]["total_tokens"], 27)
        self.assertEqual(row["guarded"]["usage"]["total_tokens"], 83)
        self.assertEqual(row["token_delta"], 56)
        self.assertTrue(row["same_model"])


if __name__ == "__main__":
    unittest.main()
