import unittest

from agent_skill_dictionary.gateway_core import rewrite_chat_completion_request
from agent_skill_dictionary.loader import load_dictionary
from agent_skill_dictionary.skill_mount_loader import (
    load_skill_mount_registry,
    lookup_skill_mount,
    lookup_skill_mount_or_root,
)


DICTIONARY_PATH = "agent_skill_dictionary/programming-agent-skill-dictionary.json"
REGISTRY_PATH = "agent_skill_dictionary/skill_mount_registry.json"


class SkillMountRegistryTest(unittest.TestCase):
    def setUp(self):
        self.dictionary = load_dictionary(DICTIONARY_PATH)
        self.registry = load_skill_mount_registry(REGISTRY_PATH)

    def test_registry_contains_eight_root_mounts(self):
        expected = {"查", "修", "测", "卫", "停", "问", "记", "总"}
        self.assertTrue(expected.issubset(set(self.registry["mounts"])))

    def test_each_root_mount_has_sources_gates_and_evidence(self):
        for code in {"查", "修", "测", "卫", "停", "问", "记", "总"}:
            with self.subTest(code=code):
                mount = lookup_skill_mount(self.registry, code)
                self.assertGreaterEqual(len(mount.community_sources), 1)
                self.assertGreaterEqual(len(mount.hard_gates), 2)
                self.assertGreaterEqual(len(mount.evidence), 1)

    def test_inspect_mount_references_repo_map_and_swe_agent(self):
        mount = lookup_skill_mount(self.registry, "查")
        source_names = {source["name"] for source in mount.community_sources}
        self.assertIn("Aider Repository Map", source_names)
        self.assertIn("SWE-agent Agent-Computer Interface", source_names)

    def test_guard_mount_references_security_scanners(self):
        mount = lookup_skill_mount(self.registry, "卫")
        source_names = {source["name"] for source in mount.community_sources}
        self.assertIn("Semgrep CLI", source_names)
        self.assertIn("OSV-Scanner", source_names)

    def test_build_is_a_derived_mount_not_root_mount(self):
        self.assertNotIn("造", self.registry["mounts"])
        build_mount = lookup_skill_mount(self.registry, "造")
        self.assertEqual(build_mount.inherits_root, "修")

    def test_unknown_child_mount_falls_back_to_root_mount(self):
        explain_mount = lookup_skill_mount_or_root(self.registry, "解", "查")

        self.assertEqual(explain_mount.code, "解")
        self.assertEqual(explain_mount.inherits_root, "查")
        self.assertEqual(explain_mount.mount_name, "inspect_repo_map_mount")

    def test_gateway_injects_skill_mount_excerpt(self):
        body = {
            "model": "gpt-test",
            "messages": [{"role": "user", "content": "这个 bug 修一下，然后跑测试确认。"}],
        }
        rewritten, metadata = rewrite_chat_completion_request(body, self.dictionary)
        system_message = rewritten["messages"][0]["content"]

        self.assertEqual(metadata["root_opcode"], "修")
        self.assertIn("根字 Skill Mount 摘要", system_message)
        self.assertIn("surgical_fix_mount", system_message)
        self.assertIn("外科手术式修改", system_message)


if __name__ == "__main__":
    unittest.main()
