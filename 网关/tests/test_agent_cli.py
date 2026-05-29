import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from agent_skill_dictionary.audit import append_audit_record, build_evidence_record
from agent_skill_dictionary import cli


class AgentCliTest(unittest.TestCase):
    def _run_cli(self, argv):
        output_buffer = StringIO()
        with patch("sys.argv", ["oneword"] + argv), redirect_stdout(output_buffer):
            output = cli.main()
        self.assertEqual(output_buffer.getvalue().strip(), output)
        return json.loads(output)

    def test_protocol_command_outputs_agent_agnostic_manifest(self):
        payload = self._run_cli(["protocol"])

        self.assertEqual(payload["name"], "oneword-agent-control-protocol")
        self.assertEqual(payload["compatibility"], "agent-agnostic")
        self.assertIn("root_opcodes", payload)

    def test_resolve_command_outputs_opcode_plan(self):
        payload = self._run_cli(["resolve", "查：看看项目结构"])

        self.assertEqual(payload["active_code"], "查")
        self.assertEqual(payload["binary_trigram"], "101")
        self.assertEqual(
            payload["allowed_tools"],
            ["native_inspect_card", "read_file", "list_directory", "grep_code", "git_diff"],
        )

    def test_preflight_command_blocks_forbidden_tool(self):
        payload = self._run_cli(
            [
                "preflight",
                "--active-code",
                "查",
                "--tool-name",
                "write_file",
                "--arguments-json",
                '{"path":"app.py"}',
            ]
        )

        self.assertFalse(payload["allowed"])
        self.assertEqual(payload["violations"][0]["reason"], "write_forbidden")

    def test_claude_pretool_hook_blocks_bash_for_inspect(self):
        payload = self._run_cli(
            [
                "claude-pretool-hook",
                "--active-code",
                "查",
                "--payload-json",
                json.dumps(
                    {
                        "hook_event_name": "PreToolUse",
                        "tool_name": "Bash",
                        "tool_input": {"command": "rm -f DANGER_SENTINEL_DO_NOT_DELETE.txt"},
                    }
                ),
            ]
        )

        self.assertFalse(payload["allowed"])
        hook_output = payload["hook_output"]["hookSpecificOutput"]
        self.assertEqual(hook_output["permissionDecision"], "deny")
        self.assertEqual(payload["normalized_tool"], "execute_command")

    def test_audit_command_reads_jsonl_log(self):
        with TemporaryDirectory() as tmpdir:
            audit_path = Path(tmpdir) / "audit.jsonl"
            append_audit_record(audit_path, build_evidence_record("cmd", 0, "OK\n", ""))

            payload = self._run_cli(["audit", "--path", str(audit_path)])

            self.assertEqual(payload["count"], 1)
            self.assertTrue(payload["valid_chain"])
            self.assertEqual(payload["chain_errors"], [])

    def test_doctor_command_reports_ready_state(self):
        payload = self._run_cli(["doctor"])

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["root_opcode_count"], 8)
        self.assertEqual(payload["protocol"], "oneword-agent-control-protocol")
        self.assertEqual(payload["dictionary"], "valid")

    def test_run_command_can_require_docker(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")

            with patch("agent_skill_dictionary.executor.shutil.which", return_value=None):
                payload = self._run_cli(
                    [
                        "run",
                        "请运行测试验证",
                        "--workspace",
                        str(workspace),
                        "--verification-command-json",
                        '["python3", "-c", "print(\\"must-not-run\\")"]',
                        "--use-docker",
                        "--require-docker",
                    ]
                )

        verify_result = payload["history"][0]["result"]
        self.assertEqual(verify_result["sandbox"], "docker")
        self.assertEqual(verify_result["exit_code"], 126)

    def test_run_command_can_require_guard_scanner(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "app.py").write_text("print('hello')\n", encoding="utf-8")

            with patch("agent_skill_dictionary.guard_executor.shutil.which", return_value=None):
                payload = self._run_cli(
                    [
                        "run",
                        "检查是否有安全风险",
                        "--workspace",
                        str(workspace),
                        "--enable-external-scanners",
                        "--require-guard-scanner",
                        "--guard-scanner-types",
                        "semgrep",
                    ]
                )

        guard_result = payload["history"][0]["result"]
        self.assertEqual(payload["trace"], ["卫", "停"])
        self.assertEqual(guard_result["findings"][0]["rule_id"], "guard-scanner-missing")

    def test_build_mode_guarded_run_quarantines_unplanned_shim(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            payload = self._run_cli(
                [
                    "build-mode-guarded-run",
                    "--workspace",
                    str(workspace),
                    "--request-text",
                    "实现 cluster-state-sync",
                    "--",
                    sys.executable,
                    "-c",
                    "from pathlib import Path; Path('fastapi').mkdir(); Path('fastapi/__init__.py').write_text('fake')",
                ]
            )

            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["reason"], "post_run_unplanned_artifacts")
            self.assertIn("fastapi/__init__.py", payload["unplanned_paths"])
            self.assertFalse((workspace / "fastapi" / "__init__.py").exists())
            self.assertTrue((workspace / ".yizijue" / "quarantine" / "fastapi" / "__init__.py").exists())

    def test_expert_handoff_requires_token_and_failure_gate(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            state_dir = workspace / ".yizijue"
            state_dir.mkdir()
            (state_dir / "build-mode-state.json").write_text(
                json.dumps({"consecutive_failures": 2}),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {"ONEWORD_EXPERT_HANDOFF_TOKEN": "secret"},
                clear=False,
            ):
                payload = self._run_cli(
                    [
                        "build-mode-expert-handoff",
                        "--workspace",
                        str(workspace),
                        "--request-text",
                        "实现 cluster-state-sync",
                        "--token",
                        "secret",
                        "--changes-json",
                        '{"sync/models.py":"VALUE = 1\\n"}',
                        "--verify-command-json",
                        json.dumps([sys.executable, "-c", "from pathlib import Path; assert Path('sync/models.py').exists()"]),
                    ]
                )

            self.assertEqual(payload["status"], "completed")
            self.assertEqual(payload["hexagram"], "000")
            self.assertTrue((workspace / "sync" / "models.py").exists())
            state = json.loads((state_dir / "build-mode-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["consecutive_failures"], 0)
            self.assertEqual(state["results"][-1]["source"], "expert_handoff")

    def test_expert_handoff_cli_uses_session_state(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            state_dir = workspace / ".yizijue"
            state_dir.mkdir()
            (state_dir / "build-mode-state-session-cli.json").write_text(
                json.dumps({"consecutive_failures": 2}),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {"ONEWORD_EXPERT_HANDOFF_TOKEN": "secret"},
                clear=False,
            ):
                payload = self._run_cli(
                    [
                        "build-mode-expert-handoff",
                        "--workspace",
                        str(workspace),
                        "--session-id",
                        "session-cli",
                        "--request-text",
                        "实现 cluster-state-sync",
                        "--token",
                        "secret",
                        "--changes-json",
                        '{"sync/models.py":"VALUE = 1\\n"}',
                        "--verify-command-json",
                        json.dumps([sys.executable, "-c", "from pathlib import Path; assert Path('sync/models.py').exists()"]),
                    ]
                )

            state = json.loads((state_dir / "build-mode-state-session-cli.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "completed")
            self.assertEqual(state["consecutive_failures"], 0)
            self.assertEqual(state["results"][-1]["source"], "expert_handoff")


if __name__ == "__main__":
    unittest.main()
