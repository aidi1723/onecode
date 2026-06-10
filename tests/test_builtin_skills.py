import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


class BuiltinSkillsTests(unittest.TestCase):
    def test_safe_agent_router_skill_file_is_bundled(self):
        skill_path = Path("integrations/skills/safe-agent-router/SKILL.md")
        package_skill_path = Path("src/onecode/integrations/skills/safe-agent-router/SKILL.md")

        self.assertTrue(skill_path.exists())
        self.assertTrue(package_skill_path.exists())
        text = skill_path.read_text(encoding="utf-8")
        self.assertEqual(package_skill_path.read_text(encoding="utf-8"), text)
        self.assertIn("name: safe-agent-router", text)
        self.assertIn("method guidance only", text)
        self.assertIn("never grants filesystem", text)

    def test_builtin_skill_catalog_lists_safe_agent_router(self):
        from onecode.kernel.builtin_skills import list_builtin_skills

        skills = list_builtin_skills()

        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0]["name"], "safe-agent-router")
        self.assertEqual(skills[0]["kind"], "router")
        self.assertEqual(skills[0]["path"], "integrations/skills/safe-agent-router/SKILL.md")
        self.assertFalse(Path(skills[0]["path"]).is_absolute())

    def test_builtin_skill_task_pack_keeps_router_advisory_only(self):
        from onecode.kernel.builtin_skills import build_skill_task_pack

        pack = build_skill_task_pack("update docs and run tests")

        self.assertEqual(pack["skill"], "safe-agent-router")
        self.assertEqual(pack["authority"], "advisory_only")
        self.assertIn("verification", pack["capability_coverage"])
        self.assertIn("No filesystem", pack["safety_boundary"][0])
        self.assertIn("run verifier", " ".join(pack["execution_plan"]).lower())

    def test_cli_skills_list_and_route_are_json(self):
        env = {**os.environ, "PYTHONPATH": "src"}
        listed = subprocess.run(
            [sys.executable, "-m", "onecode", "skills", "list"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        routed = subprocess.run(
            [sys.executable, "-m", "onecode", "skills", "route", "update docs and run tests"],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertEqual(routed.returncode, 0, routed.stderr)
        list_payload = json.loads(listed.stdout)
        self.assertEqual(list_payload["skills"][0]["name"], "safe-agent-router")
        self.assertEqual(list_payload["skills"][0]["path"], "integrations/skills/safe-agent-router/SKILL.md")
        self.assertEqual(json.loads(routed.stdout)["skill"], "safe-agent-router")


if __name__ == "__main__":
    unittest.main()
