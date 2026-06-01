import unittest
from pathlib import Path


class ReadmeTests(unittest.TestCase):
    def test_readme_documents_core_cli_and_verification_paths(self):
        readme = Path("README.md")

        self.assertTrue(readme.exists())
        text = readme.read_text(encoding="utf-8")

        for snippet in [
            "bash scripts/verify.sh",
            "bash scripts/demo_v07.sh",
            "python3 -m onecode doctor",
            "python3 -m onecode.cli doctor",
            "python3 -m onecode run",
            "python3 -m onecode shell",
            "cd shell/onecode-librechat",
            "npm install",
            "http://127.0.0.1:14080/c/new",
            "python3 -m onecode run-plan",
            "python3 -m onecode init-verifier-policy",
            "python3 -m onecode list-verifier-presets",
            "python3 -m onecode inspect",
            "python3 -m onecode list-runs",
            "onecode audit-self",
            "onecode tui",
            "pip install -e .[tui]",
            "The core kernel has no runtime third-party dependency.",
            "Textual is an optional TUI dependency.",
            ".onecode/tui-transcript.txt",
            "/export-last",
            "--resume-from",
            "--write-text",
            "--max-write-bytes",
            "--max-trace-bytes",
            "--max-run-seconds",
            "resource_budget_exceeded",
            "run_completed",
            "evidence-chain.jsonl",
            "--cap-drop ALL",
            "onecode math-audit",
            "transition graph",
            "--verifier-policy",
            "--verifier python-unittest",
            "After initialization, `run-plan --verifier` reads the workspace default policy",
        ]:
            self.assertIn(snippet, text)


if __name__ == "__main__":
    unittest.main()
