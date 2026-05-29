import unittest

from agent_skill_dictionary.gateway_core import rewrite_chat_completion_request
from agent_skill_dictionary.loader import load_dictionary
from agent_skill_dictionary.workflow_loader import load_workflow_registry, lookup_workflow


DICTIONARY_PATH = "agent_skill_dictionary/programming-agent-skill-dictionary.json"
REGISTRY_PATH = "agent_skill_dictionary/workflow_registry.json"


class WorkflowLoaderTest(unittest.TestCase):
    def setUp(self):
        self.dictionary = load_dictionary(DICTIONARY_PATH)
        self.registry = load_workflow_registry(REGISTRY_PATH)

    def test_registry_contains_eight_root_workflows(self):
        expected = {"查", "修", "测", "卫", "停", "问", "记", "总"}
        self.assertTrue(expected.issubset(set(self.registry["workflows"])))

    def test_lookup_workflow_loads_markdown_for_root_opcode(self):
        workflow = lookup_workflow(self.registry, "修")
        self.assertEqual(workflow.code, "修")
        self.assertIn("修 Opcode Workflow", workflow.title)
        self.assertIn("最小复现", workflow.content)

    def test_every_root_workflow_declares_quality_contract(self):
        for code in {"查", "修", "测", "卫", "停", "问", "记", "总"}:
            with self.subTest(code=code):
                workflow = lookup_workflow(self.registry, code)
                self.assertIn("Prompt Engineering Sources", workflow.content)
                self.assertIn("Efficiency Controls", workflow.content)
                self.assertIn("Precision Controls", workflow.content)
                self.assertIn("Stability Controls", workflow.content)
                self.assertIn("Evidence", workflow.content)

    def test_lookup_workflow_rejects_unknown_root_opcode(self):
        with self.assertRaises(KeyError):
            lookup_workflow(self.registry, "造")

    def test_gateway_injects_loaded_workflow_excerpt(self):
        body = {
            "model": "gpt-test",
            "messages": [{"role": "user", "content": "这个 bug 修一下，然后跑测试确认。"}],
        }
        rewritten, metadata = rewrite_chat_completion_request(body, self.dictionary)
        system_message = rewritten["messages"][0]["content"]
        self.assertEqual(metadata["root_opcode"], "修")
        self.assertIn("根字 Workflow 摘要", system_message)
        self.assertIn("修 Opcode Workflow", system_message)
        self.assertIn("最小复现", system_message)


if __name__ == "__main__":
    unittest.main()
