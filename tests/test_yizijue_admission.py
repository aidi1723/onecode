import unittest

from onecode.kernel.agent_cycle import run_agent_cycle


def refuse_tools(visible, allowed):
    raise AssertionError("tools must not be proposed")


def refuse_execute(name, params):
    raise AssertionError("tools must not run")


class AgentAdmissionTests(unittest.TestCase):
    def test_observe_and_kun_stop_before_tools(self):
        observe = run_agent_cycle(
            propose=refuse_tools,
            execute=refuse_execute,
            admission={
                "yizijue_state": "010010",
                "action": "DENY_AND_LEDGER",
                "reason": "entropy_observe",
            },
        )
        kun = run_agent_cycle(
            propose=refuse_tools,
            execute=refuse_execute,
            admission={
                "yizijue_state": "000000",
                "action": "DENY_AND_LEDGER",
                "reason": "kun_deny_ledger",
            },
        )
        self.assertEqual(observe["status"], "halted")
        self.assertEqual(observe["reason"], "entropy_observe")
        self.assertEqual(observe["yizijue_state"], "010010")
        self.assertEqual(kun["reason"], "kun_deny_ledger")
        self.assertEqual(kun["yizijue_state"], "000000")

    def test_allow_and_verifier_do_not_enter_the_tool_loop(self):
        allowed = run_agent_cycle(
            propose=refuse_tools,
            execute=refuse_execute,
            admission={
                "yizijue_state": "111111",
                "action": "ALLOW_ATOMIC_WRITE",
                "reason": "hexagram_recast",
            },
        )
        verifier = run_agent_cycle(
            propose=refuse_tools,
            execute=refuse_execute,
            admission={
                "yizijue_state": "010010",
                "action": "RUN_VERIFIER_IN_SANDBOX",
                "reason": "verifier_requires_sandbox",
            },
        )
        self.assertEqual(allowed["status"], "halted")
        self.assertEqual(allowed["yizijue_action"], "ALLOW_ATOMIC_WRITE")
        self.assertEqual(verifier["reason"], "verifier_requires_sandbox")
        self.assertEqual(verifier["turns"], [])

    def test_bad_admission_stops_before_tools(self):
        result = run_agent_cycle(
            propose=refuse_tools,
            execute=refuse_execute,
            admission={"yizijue_state": "999", "action": "DENY_AND_LEDGER", "reason": "entropy_observe"},
        )
        self.assertEqual(result["reason"], "yizijue_admission_rejected")

    def test_forged_decision_kind_is_rejected_and_recorded(self):
        import json
        import tempfile

        def writer(workspace, relative_path, content):
            raise AssertionError("a forged decision must not write")

        with tempfile.TemporaryDirectory() as directory:
            workspace = __import__("pathlib").Path(directory)
            service_ledger = workspace / "service.jsonl"
            previous = __import__("os").environ.get("YIZIJUE_LEDGER")
            __import__("os").environ["YIZIJUE_LEDGER"] = str(service_ledger)
            try:
                result = run_agent_cycle(
                    propose=refuse_tools,
                    execute=refuse_execute,
                    workspace=workspace,
                    write_runner=writer,
                    write_content="三条笔记",
                    admission={
                        "kind": "yizijue_decision",
                        "yizijue_state": "999",
                        "action": "ALLOW_ATOMIC_WRITE",
                        "reason": "hexagram_recast",
                        "executed": True,
                    },
                )
            finally:
                if previous is None:
                    __import__("os").environ.pop("YIZIJUE_LEDGER", None)
                else:
                    __import__("os").environ["YIZIJUE_LEDGER"] = previous
            recorded = json.loads((workspace / ".onecode" / "yizijue-ledger.jsonl").read_text(encoding="utf-8"))
            copied = json.loads(service_ledger.read_text(encoding="utf-8"))
        self.assertEqual(result["reason"], "yizijue_admission_rejected")
        self.assertEqual(copied, recorded)
        self.assertEqual(recorded["reason"], "yizijue_admission_rejected")
        self.assertEqual(recorded["action"], "ALLOW_ATOMIC_WRITE")
        self.assertFalse(recorded["executed"])

    def test_valid_cycle_decision_is_copied_to_the_service_ledger(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            workspace = __import__("pathlib").Path(directory)
            service_ledger = workspace / "service.jsonl"
            previous = __import__("os").environ.get("YIZIJUE_LEDGER")
            __import__("os").environ["YIZIJUE_LEDGER"] = str(service_ledger)
            try:
                result = run_agent_cycle(
                    propose=refuse_tools,
                    execute=refuse_execute,
                    workspace=workspace,
                    admission={
                        "yizijue_state": "010010",
                        "action": "DENY_AND_LEDGER",
                        "reason": "entropy_observe",
                    },
                )
            finally:
                if previous is None:
                    __import__("os").environ.pop("YIZIJUE_LEDGER", None)
                else:
                    __import__("os").environ["YIZIJUE_LEDGER"] = previous
            recorded = json.loads((workspace / ".onecode" / "yizijue-ledger.jsonl").read_text(encoding="utf-8"))
            copied = json.loads(service_ledger.read_text(encoding="utf-8"))
        self.assertEqual(result["reason"], "entropy_observe")
        self.assertEqual(copied, recorded)
        self.assertFalse(recorded["executed"])

    def test_copied_ledger_line_does_not_run_again(self):
        import json
        import tempfile

        from onecode.kernel.checkpoint import sha256_text

        calls = []

        def writer(workspace, relative_path, content):
            calls.append(content)
            target = workspace / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return {"path": relative_path}

        content = "三条笔记"
        facts = {
            "intent_type": "write_text",
            "path_scope": "workspace_relative",
            "sandbox_state": "not_required",
            "evidence_state": "present",
        }
        evidence = {"path": "notes/today.txt", "sha256": sha256_text(content)}
        with tempfile.TemporaryDirectory() as directory:
            workspace = __import__("pathlib").Path(directory)
            run_agent_cycle(
                propose=refuse_tools,
                execute=refuse_execute,
                workspace=workspace,
                write_runner=writer,
                write_content=content,
                admission={
                    "yizijue_state": "111111",
                    "action": "ALLOW_ATOMIC_WRITE",
                    "reason": "hexagram_recast",
                    "facts": facts,
                    "evidence": evidence,
                },
            )
            recorded = json.loads((workspace / ".onecode" / "yizijue-ledger.jsonl").read_text(encoding="utf-8").splitlines()[0])
            replay = run_agent_cycle(
                propose=refuse_tools,
                execute=refuse_execute,
                workspace=workspace,
                write_runner=writer,
                write_content=content,
                admission={**recorded, "facts": facts, "evidence": evidence, "executed": True},
            )
            effect = run_agent_cycle(
                propose=refuse_tools,
                execute=refuse_execute,
                workspace=workspace,
                write_runner=writer,
                write_content=content,
                admission={
                    "kind": "yizijue_effect",
                    "effect": "write",
                    "yizijue_state": "111111",
                    "action": "ALLOW_ATOMIC_WRITE",
                    "reason": "hexagram_recast",
                    "executed": True,
                    "facts": facts,
                    "evidence": evidence,
                    "path": "notes/today.txt",
                    "sha256": sha256_text(content),
                },
            )
        self.assertEqual(calls, [content])
        self.assertEqual(replay["reason"], "yizijue_admission_rejected")
        self.assertNotIn("write", replay)
        self.assertEqual(effect["reason"], "yizijue_admission_rejected")
        self.assertNotIn("write", effect)

    def test_verifier_and_write_use_their_gates_instead_of_tools(self):
        import tempfile

        from onecode.kernel.checkpoint import sha256_text

        calls = []

        def verifier(workspace, command):
            calls.append(("verifier", command))
            return {"status": "passed", "command": list(command)}

        def writer(workspace, relative_path, content):
            calls.append(("write", relative_path, content))
            target = workspace / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return {"path": relative_path}

        with tempfile.TemporaryDirectory() as directory:
            workspace = __import__("pathlib").Path(directory)
            verified = run_agent_cycle(
                propose=refuse_tools,
                execute=refuse_execute,
                workspace=workspace,
                verifier_runner=verifier,
                admission={
                    "yizijue_state": "010010",
                    "action": "RUN_VERIFIER_IN_SANDBOX",
                    "reason": "verifier_requires_sandbox",
                    "facts": {
                        "intent_type": "execute_pytest",
                        "path_scope": "no_path",
                        "sandbox_state": "required",
                        "evidence_state": "required",
                    },
                },
            )
            observed = run_agent_cycle(
                propose=refuse_tools,
                execute=refuse_execute,
                workspace=workspace,
                verifier_runner=verifier,
                admission={
                    "yizijue_state": "010010",
                    "action": "DENY_AND_LEDGER",
                    "reason": "entropy_observe",
                },
            )
            content = "三条笔记"
            written = run_agent_cycle(
                propose=refuse_tools,
                execute=refuse_execute,
                workspace=workspace,
                write_runner=writer,
                write_content=content,
                admission={
                    "yizijue_state": "111111",
                    "action": "ALLOW_ATOMIC_WRITE",
                    "reason": "hexagram_recast",
                    "facts": {
                        "intent_type": "write_text",
                        "path_scope": "workspace_relative",
                        "sandbox_state": "not_required",
                        "evidence_state": "present",
                    },
                    "evidence": {"path": "notes/today.txt", "sha256": sha256_text(content)},
                },
            )
            self.assertTrue(verified["verifier"]["ran"])
            self.assertEqual(verified["reason"], "verifier_requires_sandbox")
            from onecode.experimental.yizijue_verifier import pinned_verifier_command

            self.assertEqual(verified["verifier"]["command"], pinned_verifier_command())
            self.assertEqual(calls[0][0], "verifier")
            self.assertFalse(observed["verifier"]["ran"])
            self.assertEqual(observed["verifier"]["reason"], "withheld")
            self.assertNotIn("command", observed["verifier"])
            self.assertTrue(written["write"]["ran"])
            self.assertEqual(written["reason"], "hexagram_recast")
            self.assertEqual(written["write"]["path"], "notes/today.txt")
            self.assertEqual(written["write"]["sha256"], sha256_text(content))
            self.assertEqual(calls[1], ("write", "notes/today.txt", content))
            lines = (workspace / ".onecode" / "yizijue-ledger.jsonl").read_text(encoding="utf-8").splitlines()
        import json

        kinds = [json.loads(line)["kind"] for line in lines]
        self.assertEqual(
            kinds,
            [
                "yizijue_decision",
                "yizijue_effect",
                "yizijue_decision",
                "yizijue_effect",
                "yizijue_decision",
                "yizijue_effect",
            ],
        )
        effects = [json.loads(line) for line in lines if json.loads(line)["kind"] == "yizijue_effect"]
        self.assertEqual([item["effect"] for item in effects], ["verifier", "verifier", "write"])
        self.assertEqual([item["executed"] for item in effects], [True, False, True])
        self.assertEqual(effects[0]["command"], verified["verifier"]["command"])
        self.assertEqual(effects[2]["sha256"], written["write"]["sha256"])
        self.assertEqual(effects[2]["path"], written["write"]["path"])

    def test_blocked_reason_does_not_run(self):
        import tempfile

        def verifier(workspace, command):
            raise AssertionError("a blocked decision must not run")

        with tempfile.TemporaryDirectory() as directory:
            result = run_agent_cycle(
                propose=refuse_tools,
                execute=refuse_execute,
                workspace=__import__("pathlib").Path(directory),
                verifier_runner=verifier,
                admission={
                    "yizijue_state": "010010",
                    "action": "RUN_VERIFIER_IN_SANDBOX",
                    "reason": "verifier_unconfirmed",
                    "facts": {
                        "intent_type": "execute_pytest",
                        "path_scope": "no_path",
                        "sandbox_state": "required",
                        "evidence_state": "required",
                    },
                },
            )
        self.assertFalse(result["verifier"]["executed"])
        self.assertEqual(result["verifier"]["reason"], "withheld")
        self.assertEqual(result["reason"], "withheld")
        self.assertNotIn("command", result["verifier"])

    def test_failed_write_replaces_the_allow_reason(self):
        import tempfile

        from onecode.kernel.checkpoint import sha256_text

        def writer(workspace, relative_path, content):
            raise AssertionError("a hash mismatch must not write")

        content = "三条笔记"
        with tempfile.TemporaryDirectory() as directory:
            result = run_agent_cycle(
                propose=refuse_tools,
                execute=refuse_execute,
                workspace=__import__("pathlib").Path(directory),
                write_runner=writer,
                write_content="别的内容",
                admission={
                    "yizijue_state": "111111",
                    "action": "ALLOW_ATOMIC_WRITE",
                    "reason": "hexagram_recast",
                    "facts": {
                        "intent_type": "write_text",
                        "path_scope": "workspace_relative",
                        "sandbox_state": "not_required",
                        "evidence_state": "present",
                    },
                    "evidence": {"path": "notes/today.txt", "sha256": sha256_text(content)},
                },
            )
        self.assertFalse(result["write"]["executed"])
        self.assertEqual(result["write"]["reason"], "sha_mismatch")
        self.assertEqual(result["reason"], "sha_mismatch")


if __name__ == "__main__":
    unittest.main()
