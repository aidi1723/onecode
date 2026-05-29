import unittest

from agent_skill_dictionary.upstream import parse_upstream_json, upstream_error_payload


class FakeResponse:
    status_code = 502
    text = "bad gateway"

    def json(self):
        raise ValueError("not json")


class UpstreamTest(unittest.TestCase):
    def test_parse_upstream_json_wraps_non_json_response(self):
        payload, status_code = parse_upstream_json(FakeResponse(), gateway_name="yizijue_gateway")

        self.assertEqual(status_code, 502)
        self.assertEqual(payload["error"]["type"], "upstream_invalid_json")
        self.assertEqual(payload["yizijue_gateway"]["upstream_status_code"], 502)

    def test_upstream_error_payload_is_stable_json(self):
        payload = upstream_error_payload(
            RuntimeError("connection failed"),
            gateway_name="oneword_gateway",
        )

        self.assertEqual(payload["error"]["type"], "upstream_request_failed")
        self.assertEqual(payload["oneword_gateway"]["upstream_error"], "RuntimeError")


if __name__ == "__main__":
    unittest.main()
