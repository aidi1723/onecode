import unittest


class EffectiveModelConfigTests(unittest.TestCase):
    def test_environment_precedence_is_public_and_redacted(self):
        from onecode.kernel.effective_model_config import resolve_effective_model_config

        result = resolve_effective_model_config(
            {
                "ONECODE_MODEL_PROVIDER": "chat",
                "ONECODE_MODEL": "m1",
                "OPENAI_API_KEY": "environment-secret",
            },
            {
                "provider": "openai-compatible",
                "endpoint": "http://stored.example/v1",
                "model": "stored",
                "api_key": "stored-secret",
            },
        )

        self.assertEqual(result.provider, "chat")
        self.assertEqual(result.model, "m1")
        self.assertEqual(result.endpoint, "http://stored.example/v1")
        self.assertEqual(result.public["provider_source"], "environment")
        self.assertEqual(result.public["endpoint_source"], "stored")
        self.assertEqual(result.public["api_key_source"], "environment")
        self.assertTrue(result.public["api_key_configured"])
        self.assertNotIn("environment-secret", repr(result.public))
        self.assertNotIn("stored-secret", repr(result.public))

    def test_stored_config_precedes_defaults(self):
        from onecode.kernel.effective_model_config import resolve_effective_model_config

        result = resolve_effective_model_config(
            {},
            {
                "provider": "openai-compatible",
                "endpoint": "http://stored.example/v1",
                "model": "stored-model",
                "api_key": "stored-secret",
            },
        )

        self.assertEqual(result.public["provider_source"], "stored")
        self.assertEqual(result.public["model_source"], "stored")
        self.assertEqual(result.public["endpoint_source"], "stored")
        self.assertEqual(result.public["api_key_source"], "stored")


if __name__ == "__main__":
    unittest.main()
