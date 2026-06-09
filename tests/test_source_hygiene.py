from pathlib import Path
import subprocess
import tempfile
import unittest


class SourceHygieneTests(unittest.TestCase):
    def test_contributing_forbids_leaked_sources(self):
        text = Path("CONTRIBUTING.md").read_text(encoding="utf-8")

        self.assertIn("Leaked, mirrored, or DMCA-risk Claude Code source repositories are forbidden", text)
        self.assertIn("Every OneCode source file must be independently authored", text)

    def test_privacy_scan_ignores_worktree_git_pointer_file(self):
        script = Path("scripts/privacy-scan.sh").resolve()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            private_path = "/" + "Users" + "/" + "local-user" + "/private/worktree"
            (root / ".git").write_text(f"gitdir: {private_path}\n", encoding="utf-8")
            (root / "README.md").write_text("# public\n", encoding="utf-8")

            completed = subprocess.run(
                ["bash", str(script)],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
