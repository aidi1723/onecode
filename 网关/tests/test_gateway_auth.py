import unittest


class GatewayAuthTest(unittest.TestCase):
    def test_gateway_request_requires_token_when_configured(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        self.assertFalse(
            gateway_server.gateway_request_authorized(
                {},
                required_token="secret-token",
            )
        )
        self.assertTrue(
            gateway_server.gateway_request_authorized(
                {"authorization": "Bearer secret-token"},
                required_token="secret-token",
            )
        )
        self.assertTrue(
            gateway_server.gateway_request_authorized(
                {"x-oneword-token": "secret-token"},
                required_token="secret-token",
            )
        )
        self.assertTrue(
            gateway_server.gateway_request_authorized(
                {"x-api-key": "secret-token"},
                required_token="secret-token",
            )
        )

    def test_upstream_authorization_does_not_satisfy_gateway_token(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        self.assertFalse(
            gateway_server.gateway_request_authorized(
                {"authorization": "Bearer upstream-model-key"},
                required_token="gateway-token",
            )
        )

    def test_gateway_request_fails_closed_without_configured_token(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        self.assertFalse(gateway_server.gateway_request_authorized({}))

    def test_gateway_request_uses_constant_time_token_compare(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        calls: list[tuple[str, str]] = []

        def fake_compare(left: str, right: str) -> bool:
            calls.append((left, right))
            return left == right

        with unittest.mock.patch("agent_skill_dictionary.gateway_server.hmac.compare_digest", side_effect=fake_compare):
            self.assertTrue(
                gateway_server.gateway_request_authorized(
                    {"authorization": "Bearer gateway-token"},
                    required_token="gateway-token",
                )
            )

        self.assertIn(("gateway-token", "gateway-token"), calls)

    def test_chat_proxy_requires_gateway_token_when_configured(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        response = gateway_server.gateway_unauthorized_response()

        self.assertEqual(response["status"], "rejected")
        self.assertEqual(response["error"]["type"], "unauthorized")

    def test_upstream_headers_do_not_forward_gateway_token(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        headers = gateway_server._upstream_headers(
            {"authorization": "Bearer gateway-token"},
            upstream_api_key=None,
        )

        self.assertNotIn("authorization", headers)

    def test_upstream_headers_use_only_configured_upstream_key(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        headers = gateway_server._upstream_headers(
            {"authorization": "Bearer gateway-token"},
            upstream_api_key="real-upstream-key",
        )

        self.assertEqual(headers["authorization"], "Bearer real-upstream-key")

    def test_missing_upstream_key_response_is_actionable(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        response, status_code = gateway_server.missing_upstream_key_response()

        self.assertEqual(status_code, 503)
        self.assertEqual(response["error"]["type"], "upstream_api_key_missing")
        self.assertTrue(response["yizijue_gateway"]["blocked"])

    def test_control_plane_run_does_not_require_upstream_key(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        self.assertFalse(gateway_server.control_plane_requires_upstream_key("/v1/yizijue/run"))
        self.assertFalse(gateway_server.control_plane_requires_upstream_key("/v1/yizijue/submit-evidence"))
        self.assertTrue(gateway_server.control_plane_requires_upstream_key("/v1/chat/completions"))
        self.assertTrue(gateway_server.control_plane_requires_upstream_key("/v1/messages"))

    def test_anthropic_headers_use_configured_key_without_gateway_token(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        headers = gateway_server._anthropic_upstream_headers(
            {"authorization": "Bearer gateway-token", "x-api-key": "gateway-token"},
            upstream_api_key="anthropic-key",
        )

        self.assertEqual(headers["x-api-key"], "anthropic-key")
        self.assertNotIn("authorization", headers)
        self.assertEqual(headers["anthropic-version"], "2023-06-01")

    def test_preflight_auth_can_be_required_by_configuration(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with self.assertRaises(gateway_server.GatewayAuthRequired):
            gateway_server.authorize_preflight_request(
                {},
                required_token="gateway-token",
                protect_preflight=True,
            )

        gateway_server.authorize_preflight_request(
            {"authorization": "Bearer gateway-token"},
            required_token="gateway-token",
            protect_preflight=True,
        )

    def test_preflight_auth_is_required_by_default(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with self.assertRaises(gateway_server.GatewayAuthRequired):
            gateway_server.authorize_preflight_request({}, required_token="gateway-token")


if __name__ == "__main__":
    unittest.main()
