import tempfile
import unittest
from pathlib import Path

from agent_skill_dictionary.build_mode_orchestrator import artifact_plan_for_request
from agent_skill_dictionary.build_mode_tool_executor import execute_build_mode_tool


class BuildModeToolExecutorTest(unittest.TestCase):
    def test_write_file_tool_returns_write_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = execute_build_mode_tool(
                workspace=tmp,
                tool_name="write_file",
                arguments={"path": "app/main.py", "content": "VALUE = 1\n"},
            )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["hexagram"], "111")
            self.assertEqual(result["next_hexagram"], "001")
            self.assertTrue((Path(tmp) / "app" / "main.py").exists())
            self.assertEqual(result["evidence"]["changed_files"], ["app/main.py"])

    def test_write_file_tool_with_empty_path_returns_soft_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = execute_build_mode_tool(
                workspace=tmp,
                tool_name="write_file",
                arguments={"path": "", "content": "bad"},
            )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["hexagram"], "111")
            self.assertEqual(result["next_hexagram"], "110")
            self.assertEqual(result["evidence"]["reason"], "empty_path")
            self.assertEqual(result["feedback"]["http_status"], 200)
            self.assertEqual(result["feedback"]["stderr"], "")

    def test_write_file_tool_blocks_unplanned_shim_when_artifact_plan_is_bound(self):
        plan = artifact_plan_for_request("实现 cluster-state-sync")
        with tempfile.TemporaryDirectory() as tmp:
            result = execute_build_mode_tool(
                workspace=tmp,
                tool_name="write_file",
                arguments={"path": "fastapi/__init__.py", "content": "fake\n"},
                artifact_plan=plan,
            )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["hexagram"], "111")
            self.assertEqual(result["next_hexagram"], "110")
            self.assertEqual(result["evidence"]["reason"], "unplanned_artifact_path")
            self.assertFalse((Path(tmp) / "fastapi" / "__init__.py").exists())

    def test_apply_patch_tool_blocks_unplanned_shim_when_artifact_plan_is_bound(self):
        plan = artifact_plan_for_request("实现 cluster-state-sync")
        patch = (
            "*** Begin Patch\n"
            "*** Add File: sqlmodel/__init__.py\n"
            "+fake\n"
            "*** End Patch\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = execute_build_mode_tool(
                workspace=tmp,
                tool_name="apply_patch",
                arguments={"patch": patch},
                artifact_plan=plan,
            )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["evidence"]["reason"], "unplanned_artifact_path")
            self.assertFalse((Path(tmp) / "sqlmodel" / "__init__.py").exists())

    def test_apply_patch_tool_adds_files_inside_workspace(self):
        patch = (
            "*** Begin Patch\n"
            "*** Add File: index.html\n"
            "+<canvas id=\"game\"></canvas>\n"
            "+<script>console.log('ok')</script>\n"
            "*** Add File: README.md\n"
            "+# Star Catcher\n"
            "+Open index.html directly.\n"
            "*** End Patch\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = execute_build_mode_tool(
                workspace=tmp,
                tool_name="apply_patch",
                arguments={"patch": patch},
            )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["hexagram"], "111")
            self.assertEqual(result["next_hexagram"], "001")
            self.assertEqual(
                result["evidence"]["changed_files"],
                ["index.html", "README.md"],
            )
            self.assertIn("<canvas", (Path(tmp) / "index.html").read_text(encoding="utf-8"))
            self.assertIn("Star Catcher", (Path(tmp) / "README.md").read_text(encoding="utf-8"))

    def test_apply_patch_tool_blocks_path_escape(self):
        patch = (
            "*** Begin Patch\n"
            "*** Add File: ../escape.txt\n"
            "+bad\n"
            "*** End Patch\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = execute_build_mode_tool(
                workspace=tmp,
                tool_name="apply_patch",
                arguments={"patch": patch},
            )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["hexagram"], "111")
            self.assertEqual(result["next_hexagram"], "110")
            self.assertEqual(result["evidence"]["reason"], "path_escape")

    def test_apply_patch_tool_empty_patch_requests_write_file_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = execute_build_mode_tool(
                workspace=tmp,
                tool_name="apply_patch",
                arguments={"patch": ""},
            )

            self.assertEqual(result["status"], "needs_retry")
            self.assertEqual(result["hexagram"], "110")
            self.assertEqual(result["next_hexagram"], "111")
            self.assertEqual(result["reason"], "empty_patch")
            self.assertEqual(result["fallback_tools"], ["write_file"])
            self.assertEqual(result["feedback"]["http_status"], 200)
            self.assertEqual(result["feedback"]["stderr"], "")
            self.assertIn("write_file", result["feedback"]["message"])
            self.assertFalse(any(Path(tmp).iterdir()))

    def test_run_pytest_tool_returns_sandbox_and_archive_on_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "test_ok.py").write_text(
                "import unittest\n\n"
                "class OkTest(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            result = execute_build_mode_tool(
                workspace=tmp,
                tool_name="run_pytest",
                arguments={"command": "python3 -m unittest discover"},
                use_docker=False,
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["hexagram"], "001")
            self.assertEqual(result["next_hexagram"], "000")
            self.assertEqual(result["archive"]["manifest_path"], ".yizijue/manifest.json")

    def test_run_pytest_empty_command_uses_unittest_discover_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tests").mkdir()
            (root / "tests" / "test_ok.py").write_text(
                "import unittest\n\n"
                "class OkTest(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )

            result = execute_build_mode_tool(
                workspace=tmp,
                tool_name="run_pytest",
                arguments={},
                use_docker=False,
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["next_hexagram"], "000")

    def test_run_pytest_tool_with_artifact_plan_quarantines_unplanned_test_side_effects(self):
        import sys

        plan = artifact_plan_for_request("实现 cluster-state-sync")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = execute_build_mode_tool(
                workspace=tmp,
                tool_name="run_pytest",
                arguments={
                    "command": (
                        f"{sys.executable} -c \"from pathlib import Path; "
                        "Path('fastapi').mkdir(); "
                        "Path('fastapi/__init__.py').write_text('fake')\""
                    )
                },
                use_docker=False,
                artifact_plan=plan,
            )

            self.assertEqual(result["status"], "needs_fix")
            self.assertEqual(result["hexagram"], "001")
            self.assertEqual(result["next_hexagram"], "110")
            self.assertEqual(result["runtime_guard"]["reason"], "post_run_unplanned_artifacts")
            self.assertFalse((root / "fastapi" / "__init__.py").exists())
            self.assertTrue((root / ".yizijue" / "quarantine" / "fastapi" / "__init__.py").exists())
            self.assertNotIn("archive", result)

    def test_run_pytest_tool_returns_repair_card_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "api").mkdir()
            (root / "api" / "server.py").write_text(
                "class SecureMeshServer:\n"
                "    def __init__(self, private_key):\n"
                "        pass\n",
                encoding="utf-8",
            )
            result = execute_build_mode_tool(
                workspace=tmp,
                tool_name="run_pytest",
                arguments={
                    "command": (
                        "python3 -c \"print('FAILED tests/test_mesh.py::test_duplicate - "
                        "TypeError: SecureMeshServer.__init__() got bad arg'); "
                        "raise SystemExit(1)\""
                    )
                },
                use_docker=False,
            )

            self.assertEqual(result["status"], "needs_fix")
            self.assertIn("failure_summary", result["evidence"])
            self.assertIn("test_duplicate", result["evidence"]["failure_summary"])
            self.assertIn("repair_card", result)
            self.assertIn("Build Mode Repair Card", result["repair_card"])
            self.assertIn("SecureMeshServer.__init__", result["repair_card"])

    def test_run_pytest_failure_adds_v3_fire_digest_without_raw_trace_bloat(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sync_node.py").write_text(
                "def sync_inventory(endpoint, snapshot):\n"
                "    return None\n",
                encoding="utf-8",
            )
            noisy_lines = "; ".join("print('DEBUG noisy ledger trace')" for _ in range(300))
            result = execute_build_mode_tool(
                workspace=tmp,
                tool_name="run_pytest",
                arguments={
                    "command": (
                        "python3 -c \""
                        "print('Traceback (most recent call last):'); "
                        "print('  File \\\"/tmp/work/sync_node.py\\\", line 40, in sync_inventory'); "
                        "print('httpx.ConnectError: manila node unavailable'); "
                        f"{noisy_lines}; "
                        "print('FAILED tests/test_sync.py::test_retry - httpx.ConnectError: manila node unavailable'); "
                        "raise SystemExit(1)\""
                    )
                },
                use_docker=False,
            )

            self.assertIn("v3", result)
            fire = result["v3"]["fire_digest"]
            self.assertLessEqual(len(fire), 900)
            self.assertIn("sync_node.py:40", fire)
            self.assertIn("httpx.ConnectError", fire)
            self.assertNotIn("DEBUG noisy ledger trace", fire)

    def test_run_pytest_timeout_keeps_compact_causal_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sync_node.py").write_text(
                "import time\n\n"
                "class ConnectError(Exception):\n"
                "    pass\n\n"
                "def sync_inventory():\n"
                "    while True:\n"
                "        print('DEBUG LEDGER TRACE: sync_node.py:8 in sync_inventory ConnectError', flush=True)\n"
                "        time.sleep(0.001)\n",
                encoding="utf-8",
            )
            (root / "tests").mkdir()
            (root / "tests" / "test_sync.py").write_text(
                "import unittest\n"
                "from sync_node import sync_inventory\n\n"
                "class SyncTest(unittest.TestCase):\n"
                "    def test_retry_budget(self):\n"
                "        sync_inventory()\n",
                encoding="utf-8",
            )

            result = execute_build_mode_tool(
                workspace=tmp,
                tool_name="run_pytest",
                arguments={},
                use_docker=False,
                timeout_seconds=1,
            )

            self.assertEqual(result["status"], "needs_fix")
            self.assertEqual(result["evidence"]["exit_code"], 124)
            self.assertIn("sync_node.py:8", result["evidence"]["failure_summary"])
            fire = result["v3"]["fire_digest"]
            self.assertIn("ConnectError", fire)
            self.assertIn("sync_node.py:8", fire)
            self.assertLessEqual(len(fire), 900)

    def test_repeated_failure_summary_adds_decay_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous = "FAILED tests/test_mesh.py::test_duplicate - TypeError: bad arg"
            result = execute_build_mode_tool(
                workspace=tmp,
                tool_name="run_pytest",
                arguments={
                    "command": (
                        "python3 -c \"print('FAILED tests/test_mesh.py::test_duplicate - "
                        "TypeError: bad arg'); raise SystemExit(1)\""
                    )
                },
                use_docker=False,
                previous_failure_summary=previous,
            )

            self.assertIn("decay", result)
            self.assertEqual(result["decay"]["dynamic_threshold"], 1)

    def test_native_inspect_card_tool_returns_repo_card_and_create_next_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")

            result = execute_build_mode_tool(
                workspace=tmp,
                tool_name="native_inspect_card",
                arguments={"target": "app.py"},
                use_docker=False,
            )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["hexagram"], "101")
            self.assertEqual(result["next_hexagram"], "111")
            self.assertIn("[State]: 101-INSPECT", result["repo_card_text"])
            self.assertEqual(result["repo_card"]["target"], "app.py")

    def test_dangerous_tool_returns_soft_feedback(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = execute_build_mode_tool(
                workspace=tmp,
                tool_name="bash",
                arguments={"command": "rm -rf /tmp/x"},
                use_docker=False,
            )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["hexagram"], "100")
            self.assertEqual(result["next_hexagram"], "110")
            self.assertEqual(result["feedback"]["http_status"], 200)
            self.assertEqual(result["feedback"]["stderr"], "")

    def test_assistant_text_destructive_intent_blocks_even_safe_looking_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = execute_build_mode_tool(
                workspace=tmp,
                tool_name="write_file",
                arguments={"path": "README.md", "content": "safe\n"},
                assistant_text="Before testing, remove ~/SENTINEL.txt with rm -rf.",
            )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["hexagram"], "100")
            self.assertEqual(result["next_hexagram"], "110")
            self.assertTrue(result["audit"]["suspicious"])
            self.assertIn("destructive_text_intent", result["audit"]["reasons"])
            self.assertFalse((Path(tmp) / "README.md").exists())


if __name__ == "__main__":
    unittest.main()
