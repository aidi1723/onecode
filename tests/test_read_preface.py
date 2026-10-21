import tempfile
import unittest
from pathlib import Path

from onecode.kernel.path_guard import PathGuardError


class ReadPrefaceTests(unittest.TestCase):
    def test_preface_rejects_a_write_tool(self):
        from onecode.kernel.read_preface import ReadPrefaceError, assert_read_only

        with self.assertRaises(ReadPrefaceError):
            assert_read_only(["read_text", "write_text"])

    def test_preface_keeps_source_excerpt(self):
        from onecode.kernel.read_preface import preface_text

        text = preface_text({"src/fares.py": "def fare_cents(distance_km, minutes):\n    return 0\n"})
        self.assertIn("src/fares.py", text)
        self.assertIn("def fare_cents", text)

    def test_collect_preface_reads_workspace_files(self):
        from onecode.kernel.read_preface import collect_preface

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "src").mkdir()
            (workspace / "src" / "fares.py").write_text("VALUE = 1\n", encoding="utf-8")
            text = collect_preface(workspace, ["src/fares.py"])
        self.assertIn("VALUE = 1", text)

    def test_collect_preface_rejects_escape(self):
        from onecode.kernel.read_preface import collect_preface

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PathGuardError):
                collect_preface(Path(tmp), ["../outside.py"])

    def test_model_task_receives_the_preface(self):
        from onecode.kernel.model_loop import run_model_task
        from onecode.kernel.model_provider import validate_model_plan

        class SeeingProvider:
            def __init__(self) -> None:
                self.seen = ""

            def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
                self.seen = task
                return validate_model_plan(
                    {"task": "write", "assets": [{"path": "src/one.py", "content": "VALUE = 1\n"}]}
                )

        provider = SeeingProvider()
        with tempfile.TemporaryDirectory() as tmp:
            run_model_task(
                "fix the fare",
                workspace=Path(tmp),
                run_id="preface",
                api_key="key",
                model="m",
                provider=provider,
                execution_approval=lambda step: True,
                preface="src/fares.py\ndef fare_cents():\n    return 0\n",
            )
        self.assertIn("def fare_cents", provider.seen)
        self.assertIn("fix the fare", provider.seen)
