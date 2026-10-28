import tempfile
import unittest
from pathlib import Path

from onecode.kernel.path_guard import PathGuardError


class ReadPrefaceTests(unittest.TestCase):
    def test_survey_prompt_asks_for_a_tools_array_without_a_sample_call(self):
        from onecode.kernel.read_preface import _survey_prompt

        prompt = _survey_prompt("fix the parser", [], frozenset({"read_text", "outline"}))
        self.assertIn("tools array", prompt)
        self.assertIn("read_text", prompt)
        self.assertNotIn('"tool_name"', prompt)
        from onecode.kernel.read_preface import ReadPrefaceError, assert_read_only

        with self.assertRaises(ReadPrefaceError):
            assert_read_only(["read_text", "write_text"])

    def test_preface_keeps_source_excerpt(self):
        from onecode.kernel.read_preface import preface_text

        text = preface_text({"src/fares.py": "def fare_cents(distance_km, minutes):\n    return 0\n"})
        self.assertIn("src/fares.py", text)
        self.assertIn("def fare_cents", text)

    def test_survey_queue_reads_a_ranked_file_outside_src(self):
        from onecode.kernel.read_preface import _survey_queue

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("a.py", "b.py", "c.py"):
                (root / name).write_text("A = 1\n", encoding="utf-8")
            (root / "pkg").mkdir()
            (root / "pkg" / "query_utils.py").write_text("class FilteredRelation:\n    pass\n", encoding="utf-8")
            queue = _survey_queue(root, "FilteredRelation 放进查询后会崩")
        self.assertEqual(queue[0]["params"]["path"], "pkg/query_utils.py")

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

    def test_survey_reads_a_file_through_the_agent_cycle(self):
        from onecode.kernel.read_preface import survey_reads

        def propose(history, allowed):
            del allowed
            if history:
                return []
            return [{"tool_name": "read_text", "params": {"path": "src/fares.py"}}]

        def execute(tool_name, params):
            self.assertEqual(tool_name, "read_text")
            return {
                "status": "completed",
                "reason": None,
                "path": params["path"],
                "content": "def fare_cents():\n    return 0\n",
            }

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = survey_reads(workspace, "Fix src/fares.py", propose, execute)
            self.assertFalse((workspace / ".onecode" / "memory.jsonl").exists())
        self.assertEqual(result["status"], "completed")
        self.assertIn("def fare_cents", result["preface"])

    def test_survey_drops_a_write_tool(self):
        from onecode.kernel.read_preface import survey_reads

        def propose(history, allowed):
            del history, allowed
            return [{"tool_name": "write_text", "params": {"path": "src/fares.py", "content": "VALUE = 1\n"}}]

        def execute(tool_name, params):
            del tool_name, params
            raise AssertionError("a write tool must not run during the read survey")

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = survey_reads(workspace, "Fix src/fares.py", propose, execute)
            self.assertFalse((workspace / "src" / "fares.py").exists())
        self.assertEqual(result["status"], "halted")
        self.assertEqual(result["reason"], "no_progress")

    def test_default_survey_reads_source_and_the_matching_test(self):
        from onecode.kernel.read_preface import default_read_proposer, read_only_registry_execute, survey_reads

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "src").mkdir()
            (workspace / "tests").mkdir()
            (workspace / "src" / "fares.py").write_text("def fare_cents():\n    return 0\n", encoding="utf-8")
            (workspace / "tests" / "test_fares.py").write_text(
                "import unittest\n\nclass FareTests(unittest.TestCase):\n    def test_zero(self):\n        self.assertEqual(1, 0)\n",
                encoding="utf-8",
            )
            result = survey_reads(
                workspace,
                "Fix src/fares.py",
                default_read_proposer(workspace, "Fix src/fares.py"),
                read_only_registry_execute(workspace),
            )
        self.assertEqual(result["status"], "completed")
        self.assertIn("def fare_cents", result["preface"])
        self.assertIn("assertEqual", result["preface"])
        self.assertNotIn("tests/test_fares.py", result["preface"])
        self.assertIn("tests / test_fares.py", result["preface"])

    def test_survey_reports_a_path_escape_as_sovereignty_breach(self):
        from onecode.kernel.read_preface import read_only_registry_execute, survey_reads

        def propose(history, allowed):
            del allowed
            if history:
                return []
            return [{"tool_name": "read_text", "params": {"path": "../outside.py"}}]

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = survey_reads(workspace, "Read the notes", propose, read_only_registry_execute(workspace))
        self.assertEqual(result["status"], "halted")
        self.assertEqual(result["reason"], "sovereignty_breach")

    def test_survey_continues_after_a_glob_without_a_pattern(self):
        from onecode.kernel.read_preface import read_only_registry_execute, survey_model_reads

        calls = {"count": 0}

        def complete(prompt: str) -> str:
            calls["count"] += 1
            if calls["count"] == 1:
                return '{"tools":[{"tool_name":"glob_files","params":{"path":"tests/test_wharf.py"}}]}'
            if calls["count"] == 2:
                return '{"tools":[{"tool_name":"read_text","params":{"path":"tests/test_wharf.py"}}]}'
            return '{"tools":[]}'

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "tests").mkdir()
            (workspace / "tests" / "test_wharf.py").write_text(
                "def test_day():\n    assert True\n",
                encoding="utf-8",
            )
            result = survey_model_reads(
                workspace,
                "Write src/tide.py and src/berth.py.",
                complete,
                read_only_registry_execute(workspace),
            )
        self.assertEqual(result["status"], "completed")
        self.assertGreaterEqual(calls["count"], 2)
        self.assertIn("test_day", result["preface"])

    def test_model_survey_reads_a_file_the_task_did_not_name(self):
        from onecode.kernel.read_preface import read_only_registry_execute, survey_model_reads

        prompts: list[str] = []

        def complete(prompt: str) -> str:
            prompts.append(prompt)
            if len(prompts) == 1:
                return (
                    '{"tools":['
                    '{"tool_name":"read_text","params":{"path":"src/rates.py"}},'
                    '{"tool_name":"write_text","params":{"path":"src/hack.py","content":"nope"}}'
                    "]}"
                )
            return '{"tools":[]}'

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "src").mkdir()
            (workspace / "src" / "rates.py").write_text("FARE = 9\n", encoding="utf-8")
            result = survey_model_reads(
                workspace,
                "where is the fare constant",
                complete,
                read_only_registry_execute(workspace),
            )
            self.assertFalse((workspace / "src" / "hack.py").exists())
        self.assertEqual(result["status"], "completed")
        self.assertIn("read_text", prompts[0])
        self.assertIn("FARE = 9", result["preface"])

    def test_model_survey_retries_invalid_json_once_then_reads_the_named_file(self):
        from onecode.kernel.read_preface import read_only_registry_execute, survey_model_reads

        calls = {"count": 0}

        def complete(prompt: str) -> str:
            del prompt
            calls["count"] += 1
            return "not json"

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "src").mkdir()
            (workspace / "src" / "fares.py").write_text("def fare_cents():\n    return 0\n", encoding="utf-8")
            result = survey_model_reads(
                workspace,
                "Fix src/fares.py",
                complete,
                read_only_registry_execute(workspace),
            )
        self.assertEqual(calls["count"], 2)
        self.assertEqual(result["status"], "completed")
        self.assertIn("def fare_cents", result["preface"])

    def test_model_survey_timeout_stops_the_read_cycle(self):
        from onecode.kernel.model_provider import ModelProviderTimeout
        from onecode.kernel.read_preface import read_only_registry_execute, survey_model_reads

        def complete(prompt: str) -> str:
            del prompt
            raise ModelProviderTimeout("model request timed out")

        with tempfile.TemporaryDirectory() as tmp:
            result = survey_model_reads(
                Path(tmp),
                "where is the fare constant",
                complete,
                read_only_registry_execute(Path(tmp)),
            )
        self.assertEqual(result["status"], "halted")
        self.assertEqual(result["reason"], "model_provider_timeout")

    def test_model_survey_stops_when_the_first_call_fails(self):
        from onecode.kernel.model_provider import ModelProviderError
        from onecode.kernel.read_preface import read_only_registry_execute, survey_model_reads

        def complete(prompt: str) -> str:
            del prompt
            raise ModelProviderError("origin")

        with tempfile.TemporaryDirectory() as tmp:
            result = survey_model_reads(
                Path(tmp),
                "where is the fare constant",
                complete,
                read_only_registry_execute(Path(tmp)),
            )
        self.assertEqual(result["status"], "halted")
        self.assertEqual(result["reason"], "model_provider_error")

    def test_model_survey_keeps_an_earlier_read_when_a_later_call_fails(self):
        from onecode.kernel.model_provider import ModelProviderError
        from onecode.kernel.read_preface import read_only_registry_execute, survey_model_reads

        calls = {"count": 0}

        def complete(prompt: str) -> str:
            del prompt
            calls["count"] += 1
            if calls["count"] == 1:
                return '{"tools":[{"tool_name":"read_text","params":{"path":"src/fares.py"}}]}'
            raise ModelProviderError("origin")

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "src").mkdir()
            (workspace / "src" / "fares.py").write_text("FARE = 9\n", encoding="utf-8")
            result = survey_model_reads(
                workspace,
                "Fix src/fares.py",
                complete,
                read_only_registry_execute(workspace),
            )
        self.assertNotEqual(result.get("reason"), "model_provider_error")
        self.assertIn("FARE = 9", result["preface"])
