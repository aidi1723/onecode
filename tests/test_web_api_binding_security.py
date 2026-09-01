import os
import unittest
from unittest.mock import patch

from onecode.web.api import run_server


class WebApiBindingSecurityTests(unittest.TestCase):
    def test_run_server_allows_loopback_without_token(self):
        """Loopback addresses should work without token even with allow_unauthenticated."""
        with patch("onecode.web.api.ThreadingHTTPServer") as mock_server:
            with patch.dict(os.environ, {"ONECODE_ALLOW_UNAUTHENTICATED": "true"}, clear=False):
                mock_instance = mock_server.return_value
                mock_instance.serve_forever.side_effect = KeyboardInterrupt

                try:
                    run_server(host="127.0.0.1", port=19080)
                except KeyboardInterrupt:
                    pass

                mock_server.assert_called_once_with(("127.0.0.1", 19080), unittest.mock.ANY)

    def test_run_server_allows_localhost_without_token(self):
        """localhost should work without token even with allow_unauthenticated."""
        with patch("onecode.web.api.ThreadingHTTPServer") as mock_server:
            with patch.dict(os.environ, {"ONECODE_ALLOW_UNAUTHENTICATED": "true"}, clear=False):
                mock_instance = mock_server.return_value
                mock_instance.serve_forever.side_effect = KeyboardInterrupt

                try:
                    run_server(host="localhost", port=19080)
                except KeyboardInterrupt:
                    pass

                mock_server.assert_called_once_with(("localhost", 19080), unittest.mock.ANY)

    def test_run_server_rejects_non_loopback_without_token(self):
        """Non-loopback addresses with allow_unauthenticated but no token should be rejected."""
        with patch.dict(os.environ, {"ONECODE_ALLOW_UNAUTHENTICATED": "true", "ONECODE_API_TOKEN": ""}, clear=True):
            with self.assertRaises(ValueError) as cm:
                run_server(host="0.0.0.0", port=19080)

            self.assertIn("Security error", str(cm.exception))
            self.assertIn("0.0.0.0", str(cm.exception))
            self.assertIn("non-loopback", str(cm.exception))

    def test_run_server_allows_non_loopback_with_token(self):
        """Non-loopback addresses should work when a token is configured."""
        with patch("onecode.web.api.ThreadingHTTPServer") as mock_server:
            with patch.dict(os.environ, {"ONECODE_ALLOW_UNAUTHENTICATED": "true", "ONECODE_API_TOKEN": "test-token"}, clear=True):
                mock_instance = mock_server.return_value
                mock_instance.serve_forever.side_effect = KeyboardInterrupt

                try:
                    run_server(host="0.0.0.0", port=19080)
                except KeyboardInterrupt:
                    pass

                mock_server.assert_called_once_with(("0.0.0.0", 19080), unittest.mock.ANY)

    def test_run_server_allows_non_loopback_without_unauthenticated_flag(self):
        """Non-loopback addresses should work when allow_unauthenticated is false (default)."""
        with patch("onecode.web.api.ThreadingHTTPServer") as mock_server:
            with patch.dict(os.environ, {}, clear=True):
                mock_instance = mock_server.return_value
                mock_instance.serve_forever.side_effect = KeyboardInterrupt

                try:
                    run_server(host="0.0.0.0", port=19080)
                except KeyboardInterrupt:
                    pass

                mock_server.assert_called_once_with(("0.0.0.0", 19080), unittest.mock.ANY)


if __name__ == "__main__":
    unittest.main()
