import json
import unittest
from contextlib import redirect_stdout
from io import StringIO

from scripts import smoke_test


class SmokeScriptTest(unittest.TestCase):
    def test_smoke_script_returns_delivery_readiness_summary(self):
        output_buffer = StringIO()
        with redirect_stdout(output_buffer):
            result = smoke_test.main()

        payload = json.loads(output_buffer.getvalue())
        self.assertEqual(result, payload)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["checks"]["doctor"], "pass")
        self.assertEqual(payload["checks"]["preflight_blocks_write"], "pass")
        self.assertEqual(payload["checks"]["normal_run"], "pass")
        self.assertEqual(payload["checks"]["security_halt"], "pass")
        self.assertEqual(payload["checks"]["audit_chain"], "pass")


if __name__ == "__main__":
    unittest.main()
