import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from agent_skill_dictionary import build_mode_runner
from agent_skill_dictionary.build_mode_runner import run_build_mode_task


class BuildModeRunnerTest(unittest.TestCase):
    def test_create_verify_archive_summary_success_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_build_mode_task(
                "创建一个最小 Python 项目并运行测试",
                workspace=tmp,
                writes=[{"path": "app/main.py", "content": "VALUE = 1\n"}],
                verification_command=["python3", "-c", "import pathlib; assert pathlib.Path('app/main.py').exists()"],
                use_docker=False,
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["trace"], ["111", "001", "000", "总"])
            self.assertTrue((Path(tmp) / "app" / "main.py").exists())
            manifest = Path(tmp) / ".yizijue" / "manifest.json"
            self.assertTrue(manifest.exists())
            manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertIn("app/main.py", manifest_data["sha256_map"])
            self.assertIn("summary", result)

    def test_path_escape_halts_and_soft_rewrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_build_mode_task(
                "创建一个文件",
                workspace=tmp,
                writes=[{"path": "../escape.py", "content": "bad\n"}],
                verification_command=["python3", "-c", "print('must not run')"],
                use_docker=False,
            )

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["trace"], ["111", "100", "110"])
            self.assertEqual(result["feedback"]["http_status"], 200)
            self.assertEqual(result["feedback"]["stderr"], "")
            self.assertFalse((Path(tmp).parent / "escape.py").exists())

    def test_verification_failure_goes_to_correct_and_inspect(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_build_mode_task(
                "创建一个文件并运行失败测试",
                workspace=tmp,
                writes=[{"path": "app/main.py", "content": "VALUE = 1\n"}],
                verification_command=["python3", "-c", "raise SystemExit(1)"],
                use_docker=False,
            )

            self.assertEqual(result["status"], "needs_fix")
            self.assertEqual(result["trace"], ["111", "001", "110", "101"])
            self.assertEqual(result["feedback"]["http_status"], 200)
            self.assertIn("repo_card", result)

    def test_build_mode_runner_main_prints_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_buffer = StringIO()
            args = [
                "build-mode-runner",
                "创建文件并验证",
                "--workspace",
                tmp,
                "--write",
                "app/main.py=VALUE = 1",
                "--verify",
                "python3 -c \"import pathlib; assert pathlib.Path('app/main.py').exists()\"",
            ]
            with patch("sys.argv", args), redirect_stdout(output_buffer):
                output = build_mode_runner.main()
            payload = json.loads(output)
            self.assertEqual(payload["status"], "completed")
            self.assertEqual(payload["trace"], ["111", "001", "000", "总"])


if __name__ == "__main__":
    unittest.main()
