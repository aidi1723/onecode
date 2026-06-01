import json
import tempfile
import unittest
from unittest.mock import patch


class ModelConfigCliTests(unittest.TestCase):
    def test_cli_config_set_model_writes_masked_config(self):
        from onecode.cli import main

        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"ONECODE_HOME": tmp}, clear=True), patch(
            "builtins.print"
        ) as print_mock:
            exit_code = main(
                [
                    "config",
                    "set-model",
                    "--endpoint",
                    "http://127.0.0.1:6780/v1",
                    "--api-key",
                    "sk-test-secret",
                ]
            )
            payload = json.loads(print_mock.call_args.args[0])

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["configured"])
        self.assertEqual(payload["model"], "gpt-5.5")
        self.assertNotIn("api_key", payload)

    def test_cli_config_show_prints_current_masked_config(self):
        from onecode.cli import main
        from onecode.kernel.model_config import write_model_config

        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"ONECODE_HOME": tmp}, clear=True):
            write_model_config(endpoint="http://127.0.0.1:6780/v1", api_key="secret-key", model="gpt-4.1")
            with patch("builtins.print") as print_mock:
                exit_code = main(["config", "show"])
            payload = json.loads(print_mock.call_args.args[0])

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["model"], "gpt-4.1")
        self.assertTrue(payload["api_key_configured"])
        self.assertNotIn("api_key", payload)


if __name__ == "__main__":
    unittest.main()
