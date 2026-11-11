import unittest
import urllib.request

from onecode.kernel.http_safety import StripAuthRedirectHandler, should_strip_redirect_auth


class ShouldStripRedirectAuthTests(unittest.TestCase):
    def test_same_host_https_to_http_strips(self) -> None:
        self.assertTrue(
            should_strip_redirect_auth(
                old_url="https://api.example.test/v1",
                new_url="http://api.example.test/v1",
            )
        )

    def test_different_host_strips(self) -> None:
        self.assertTrue(
            should_strip_redirect_auth(
                old_url="https://api.example.test/v1",
                new_url="https://evil.example.test/v1",
            )
        )

    def test_same_host_https_to_https_keeps(self) -> None:
        self.assertFalse(
            should_strip_redirect_auth(
                old_url="https://api.example.test/v1",
                new_url="https://api.example.test/v2",
            )
        )


class StripAuthRedirectHandlerTests(unittest.TestCase):
    def test_same_host_downgrade_drops_authorization_and_api_key(self) -> None:
        request = urllib.request.Request(
            "https://api.example.test/v1",
            method="GET",
            headers={"Authorization": "Bearer secret", "api-key": "secret-key"},
        )

        redirected = StripAuthRedirectHandler().redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "http://api.example.test/v1",
        )

        self.assertIsNotNone(redirected)
        header_names = {name.lower() for name in redirected.headers}
        self.assertNotIn("authorization", header_names)
        self.assertNotIn("api-key", header_names)


if __name__ == "__main__":
    unittest.main()
