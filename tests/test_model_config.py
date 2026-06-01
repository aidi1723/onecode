import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class ModelConfigTests(unittest.TestCase):
    def test_write_and_read_user_model_config_masks_api_key(self):
        from onecode.kernel.model_config import read_model_config, write_model_config

        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"ONECODE_HOME": tmp}, clear=True):
            written = write_model_config(
                endpoint="http://127.0.0.1:6780/v1",
                api_key="sk-test-secret",
                model="gpt-5.5",
            )
            read_back = read_model_config()
            raw = json.loads((Path(tmp) / "config.json").read_text(encoding="utf-8"))

        self.assertEqual(written["endpoint"], "http://127.0.0.1:6780/v1")
        self.assertEqual(read_back["model"], "gpt-5.5")
        self.assertEqual(read_back["api_key_configured"], True)
        self.assertEqual(read_back["api_key_preview"], "sk-t...cret")
        self.assertNotIn("api_key", read_back)
        self.assertEqual(raw["api_key"], "sk-test-secret")

    def test_write_model_config_adds_http_scheme_for_host_port_endpoint(self):
        from onecode.kernel.model_config import read_model_config, write_model_config

        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"ONECODE_HOME": tmp}, clear=True):
            written = write_model_config(
                endpoint="10.0.0.184:6780/v1",
                api_key="sk-test-secret",
                model="gpt-5.5",
            )
            read_back = read_model_config()

        self.assertEqual(written["endpoint"], "http://10.0.0.184:6780/v1")
        self.assertEqual(read_back["endpoint"], "http://10.0.0.184:6780/v1")

    def test_model_config_defaults_model_and_provider(self):
        from onecode.kernel.model_config import read_model_config, write_model_config

        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"ONECODE_HOME": tmp}, clear=True):
            write_model_config(
                endpoint="http://127.0.0.1:6780/v1/chat/completions",
                api_key="secret",
            )
            read_back = read_model_config(include_secret=True)

        self.assertEqual(read_back["provider"], "openai-compatible")
        self.assertEqual(read_back["model"], "gpt-5.5")
        self.assertEqual(read_back["endpoint"], "http://127.0.0.1:6780/v1/chat/completions")
        self.assertEqual(read_back["api_key"], "secret")

    def test_write_model_config_can_preserve_existing_api_key(self):
        from onecode.kernel.model_config import read_model_config, write_model_config

        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"ONECODE_HOME": tmp}, clear=True):
            write_model_config(
                endpoint="http://127.0.0.1:6780/v1",
                api_key="sk-test-secret",
                model="gpt-5.5",
            )
            write_model_config(
                endpoint="http://127.0.0.1:6780/v1/chat/completions",
                api_key="",
                model="gpt-4.1",
                preserve_existing_secret=True,
            )
            read_back = read_model_config(include_secret=True)

        self.assertEqual(read_back["api_key"], "sk-test-secret")
        self.assertEqual(read_back["model"], "gpt-4.1")
        self.assertEqual(read_back["endpoint"], "http://127.0.0.1:6780/v1/chat/completions")

    def test_discover_models_uses_openai_compatible_models_endpoint(self):
        from onecode.kernel.model_config import discover_models

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(
                    {
                        "data": [
                            {"id": "gpt-5.5"},
                            {"id": "gpt-4.1"},
                        ]
                    }
                ).encode("utf-8")

        with patch("onecode.kernel.model_config.urllib.request.urlopen", return_value=Response()) as urlopen:
            payload = discover_models("http://127.0.0.1:6780/v1/chat/completions", "sk-test")

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:6780/v1/models")
        self.assertEqual(request.headers["Authorization"], "Bearer sk-test")
        self.assertEqual(payload["models"], ["gpt-5.5", "gpt-4.1"])
        self.assertEqual(payload["source"], "remote")

    def test_discover_models_adds_http_scheme_for_host_port_endpoint(self):
        from onecode.kernel.model_config import discover_models

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps({"data": [{"id": "gpt-5.5"}]}).encode("utf-8")

        with patch("onecode.kernel.model_config.urllib.request.urlopen", return_value=Response()) as urlopen:
            payload = discover_models("10.0.0.184:6780/v1", "sk-test")

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://10.0.0.184:6780/v1/models")
        self.assertEqual(payload["source"], "remote")

    def test_discover_models_falls_back_when_remote_fails(self):
        from onecode.kernel.model_config import discover_models

        with patch("onecode.kernel.model_config.urllib.request.urlopen", side_effect=OSError("offline")):
            payload = discover_models("http://127.0.0.1:6780/v1", "sk-test")

        self.assertEqual(payload["source"], "fallback")
        self.assertIn("gpt-5.5", payload["models"])


if __name__ == "__main__":
    unittest.main()
