import json
import unittest
from pathlib import Path
from unittest.mock import patch


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "contracts"


class ContractFixtureTests(unittest.TestCase):
    def test_shell_projection_schema_matches_public_fixture(self):
        from onecode.kernel.shell_projection import shell_projection_schema

        fixture = json.loads((FIXTURE_ROOT / "shell_projection_schema_v1.json").read_text(encoding="utf-8"))

        self.assertEqual(shell_projection_schema(), fixture)

    def test_chat_completion_payload_matches_public_fixture(self):
        from onecode.web.chat import chat_completion_payload

        with patch("onecode.web.chat.time.time", return_value=1234567890):
            payload = chat_completion_payload(
                "done",
                "onecode-agent",
                {
                    "run_id": "fixture-run",
                    "status": "completed",
                    "requested_count": 1,
                    "completed_count": 1,
                    "skipped_count": 0,
                    "failed_count": 0,
                    "ledger_path": "/tmp/onecode/ledger.json",
                },
                "model",
            )
        fixture = json.loads((FIXTURE_ROOT / "chat_completion_response.json").read_text(encoding="utf-8"))

        self.assertEqual(payload, fixture)
