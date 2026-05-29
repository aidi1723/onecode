import tempfile
import unittest
from pathlib import Path

from agent_skill_dictionary.build_mode_repair import build_repair_card, summarize_pytest_output


PYTEST_OUTPUT = """FAILED tests/test_mesh.py::test_duplicate - TypeError: SecureMeshServer.__init__() got an unexpected keyword argument 'receiver_private_key'
FAILED tests/test_mesh.py::test_export_public_key_shape - ValueError: Valid PEM but no BEGIN/END delimiters for a private key found
=========================== short test summary info ============================
FAILED tests/test_mesh.py::test_duplicate - TypeError: SecureMeshServer.__init__() got an unexpected keyword argument 'receiver_private_key'
FAILED tests/test_mesh.py::test_export_public_key_shape - ValueError: Valid PEM but no BEGIN/END delimiters for a private key found
6 failed, 4 passed in 16.38s
"""


class BuildModeRepairCardTest(unittest.TestCase):
    def test_summarize_pytest_output_extracts_failures_without_full_log(self):
        summary = summarize_pytest_output(PYTEST_OUTPUT, max_chars=360)

        self.assertIn("test_duplicate", summary)
        self.assertIn("TypeError", summary)
        self.assertIn("test_export_public_key_shape", summary)
        self.assertLessEqual(len(summary), 360)

    def test_build_repair_card_combines_failure_summary_and_interface_signatures(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "api").mkdir()
            (root / "core").mkdir()
            (root / "tests").mkdir()
            (root / "api" / "server.py").write_text(
                "class SecureMeshServer:\n"
                "    def __init__(self, private_key, ledger_path='mesh.jsonl'):\n"
                "        pass\n"
                "async def receive_encrypted_message(envelope):\n"
                "    return {}\n",
                encoding="utf-8",
            )
            (root / "core" / "crypto.py").write_text(
                "def generate_keypair():\n"
                "    return b'private', b'public'\n"
                "def export_public_key(private_key_pem):\n"
                "    return b'public'\n",
                encoding="utf-8",
            )
            (root / "tests" / "test_mesh.py").write_text(
                "def test_duplicate():\n"
                "    pass\n",
                encoding="utf-8",
            )

            card = build_repair_card(root, PYTEST_OUTPUT, max_chars=1000)

        self.assertIn("Build Mode Repair Card", card)
        self.assertIn("test_duplicate", card)
        self.assertIn("SecureMeshServer.__init__", card)
        self.assertIn("api/server.py", card)
        self.assertIn("core/crypto.py", card)
        self.assertLessEqual(len(card), 1000)


if __name__ == "__main__":
    unittest.main()
