import unittest

from agent_skill_dictionary.loader import load_dictionary, lookup_entry


DICTIONARY_PATH = "agent_skill_dictionary/programming-agent-skill-dictionary.json"


class ReferencePatternsTest(unittest.TestCase):
    def setUp(self):
        self.dictionary = load_dictionary(DICTIONARY_PATH)

    def test_every_entry_has_reference_workflow_patterns(self):
        for entry in self.dictionary["entries"]:
            with self.subTest(code=entry["code"]):
                patterns = entry.get("reference_workflow_patterns")
                self.assertIsInstance(patterns, list)
                self.assertGreaterEqual(len(patterns), 1)

    def test_every_entry_has_professional_protocol(self):
        for entry in self.dictionary["entries"]:
            with self.subTest(code=entry["code"]):
                protocol = entry.get("professional_protocol", {})
                self.assertGreaterEqual(len(protocol.get("source_projects", [])), 1)
                self.assertGreaterEqual(len(protocol.get("operating_logic", [])), 3)
                self.assertGreaterEqual(len(protocol.get("hard_gates", [])), 2)

    def test_fix_references_debugging_tdd_and_verification(self):
        fix = lookup_entry(self.dictionary, "修").raw
        patterns = set(fix["reference_workflow_patterns"])
        self.assertIn("superpowers:systematic-debugging", patterns)
        self.assertIn("superpowers:test-driven-development", patterns)
        self.assertIn("superpowers:verification-before-completion", patterns)

    def test_design_references_design_md_workflow(self):
        design = lookup_entry(self.dictionary, "设").raw
        self.assertIn("design-md-ui", design["reference_workflow_patterns"])

    def test_guard_and_isolate_reference_security_patterns(self):
        guard = lookup_entry(self.dictionary, "卫").raw
        isolate = lookup_entry(self.dictionary, "隔").raw
        self.assertIn("security:permission-whitelist", guard["reference_workflow_patterns"])
        self.assertIn("multi-agent:reader-orchestrator-writer", isolate["reference_workflow_patterns"])

    def test_control_codes_reference_human_and_context_workflows(self):
        clarify = lookup_entry(self.dictionary, "问").raw
        halt = lookup_entry(self.dictionary, "停").raw
        memory = lookup_entry(self.dictionary, "记").raw
        evaluate = lookup_entry(self.dictionary, "评").raw
        summarize = lookup_entry(self.dictionary, "总").raw

        self.assertIn("langgraph:human-in-the-loop", clarify["reference_workflow_patterns"])
        self.assertIn("hooks:permission-request", halt["reference_workflow_patterns"])
        self.assertIn("claude-code:memory", memory["reference_workflow_patterns"])
        self.assertIn("openai-agents:guardrail-evaluation", evaluate["reference_workflow_patterns"])
        self.assertIn("claude-code:context-management", summarize["reference_workflow_patterns"])


if __name__ == "__main__":
    unittest.main()
