import unittest

from agent_skill_dictionary.gateway_compression_adapter import build_compression_record


class GatewayCompressionAdapterTest(unittest.TestCase):
    def test_compresses_internal_summary_and_preserves_paths_and_hashes(self):
        record = build_compression_record(
            "The system successfully wrote file app/main.py and preserved sha256 abcdef123456."
        )

        self.assertEqual(record["mode"], "internal_caveman")
        self.assertIn("app/main.py", record["compressed_summary"])
        self.assertIn("abcdef123456", record["compressed_summary"])
        self.assertLess(record["compressed_chars"], record["raw_chars"])
        self.assertGreater(record["compression_ratio"], 0.0)
        self.assertIn("app/main.py", record["preserved_tokens"])

    def test_empty_summary_returns_disabled_record(self):
        record = build_compression_record("")

        self.assertEqual(record["mode"], "off")
        self.assertEqual(record["compressed_summary"], "")
        self.assertEqual(record["compression_ratio"], 0.0)


if __name__ == "__main__":
    unittest.main()
