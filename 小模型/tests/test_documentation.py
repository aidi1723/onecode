import unittest
from pathlib import Path


class DocumentationTest(unittest.TestCase):
    def test_workspace_readme_documents_verify_script(self):
        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("scripts/verify.sh", readme)
        self.assertIn("一键验证", readme)

    def test_workspace_readme_verify_scope_matches_script(self):
        readme = Path("README.md").read_text(encoding="utf-8")
        verify_script = Path("scripts/verify.sh").read_text(encoding="utf-8")

        expected_pairs = (
            ("主测试", "python3 -m unittest discover -s tests"),
            ("release 测试", "cd release/yizijue-lm-public"),
            ("脚本语法检查", "compile(path.read_text"),
            ("评估 gate 正反例", "yizijue-review-full-report-should-fail"),
            ("release checksum", "scripts/check_release_checksums.py"),
        )
        for readme_text, script_text in expected_pairs:
            self.assertIn(readme_text, readme)
            self.assertIn(script_text, verify_script)

    def test_release_readme_documents_self_verify_script(self):
        readme = Path("release/yizijue-lm-public/README.md").read_text(encoding="utf-8")

        self.assertIn("scripts/verify_release.sh", readme)
        self.assertIn("release self-check", readme)

    def test_release_readme_verify_scope_matches_script(self):
        readme = Path("release/yizijue-lm-public/README.md").read_text(encoding="utf-8")
        verify_script = Path("release/yizijue-lm-public/scripts/verify_release.sh").read_text(encoding="utf-8")

        expected_pairs = (
            ("release tests", "python3 -m unittest discover -s tests"),
            ("script syntax check", "compile(path.read_text"),
            ("release checksum", "scripts/check_release_checksums.py"),
        )
        for readme_text, script_text in expected_pairs:
            self.assertIn(readme_text, readme)
            self.assertIn(script_text, verify_script)

    def test_docs_do_not_reference_platform_specific_checksum_tools(self):
        docs = [
            Path("CHANGELOG.md"),
            Path("README.md"),
            Path("release/yizijue-lm-public/CHANGELOG.md"),
            Path("release/yizijue-lm-public/README.md"),
        ]

        offenders = [str(path) for path in docs if "shasum" in path.read_text(encoding="utf-8")]

        self.assertEqual(offenders, [])

    def test_verify_scripts_use_python_checksum_validation(self):
        scripts = [
            Path("scripts/verify.sh"),
            Path("release/yizijue-lm-public/scripts/verify_release.sh"),
        ]

        for path in scripts:
            text = path.read_text(encoding="utf-8")
            self.assertIn("scripts/check_release_checksums.py", text)
            self.assertNotIn("shasum", text)


if __name__ == "__main__":
    unittest.main()
