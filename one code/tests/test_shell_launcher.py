import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from onecode.shell_launcher import (
    DEFAULT_LIBRECHAT_PORT,
    DEFAULT_LOCAL_EMAIL,
    DEFAULT_LOCAL_PASSWORD,
    DEFAULT_MONGO_PORT,
    DEFAULT_ONECODE_PORT,
    ShellLaunchConfig,
    build_librechat_env,
    build_runtime_config,
    check_tcp,
    check_url,
    config_from_args,
    default_librechat_dir,
    process_is_running,
    shell_status,
)


class ShellLauncherConfigTests(unittest.TestCase):
    def test_shell_defaults_workspace_to_onecode_root_and_separates_runtime_state(self):
        class Args:
            onecode_root = "/tmp/example-onecode"
            librechat_dir = "/tmp/example-librechat"
            workspace = None
            onecode_host = "127.0.0.1"
            librechat_host = "127.0.0.1"
            api_token = "token"
            open_browser = False
            show_credentials = False

        config = config_from_args(Args())

        self.assertEqual(config.workspace_root, Path("/tmp/example-onecode").resolve())
        self.assertNotEqual(config.runtime_state_root, config.workspace_root)
        self.assertEqual(config.runtime_state_root, Path(tempfile.gettempdir()) / "onecode-librechat-live")

    def test_runtime_config_uses_explicit_state_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = ShellLaunchConfig(
                onecode_root=Path(tmp) / "one code",
                librechat_dir=Path(tmp) / "onecode-librechat",
                onecode_host="127.0.0.1",
                onecode_port=18080,
                librechat_host="127.0.0.1",
                librechat_port=13080,
                mongo_port=37017,
                api_token="test-token",
                workspace_root=Path(tmp) / "workspace",
                runtime_state_root=Path(tmp) / "state",
            )

            path = build_runtime_config(config)

            self.assertEqual(path.parent, Path(tmp) / "state")
            self.assertFalse((Path(tmp) / "workspace" / "librechat.onecode.yaml").exists())

    def test_default_librechat_dir_points_to_adjacent_onecode_shell(self):
        project_root = Path("/private/var/tmp/example-root/one code")

        self.assertEqual(default_librechat_dir(project_root), Path("/private/var/tmp/example-root/onecode-librechat"))

    def test_build_librechat_env_is_onecode_only_and_allows_registration(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = ShellLaunchConfig(
                onecode_root=Path(tmp) / "one code",
                librechat_dir=Path(tmp) / "onecode-librechat",
                onecode_host="127.0.0.1",
                onecode_port=18080,
                librechat_host="127.0.0.1",
                librechat_port=13080,
                mongo_port=37017,
                api_token="test-token",
                workspace_root=Path(tmp) / "workspace",
                email="agent@example.test",
                password="Secret123!",
            )

            env = build_librechat_env(config, os.environ | {"ONEWORD_API_BASE_URL": "http://bad"})

            self.assertEqual(env["APP_TITLE"], "one code")
            self.assertEqual(env["CUSTOM_FOOTER"], "one code")
            self.assertEqual(env["ENDPOINTS"], "custom")
            self.assertEqual(env["ONECODE_API_BASE_URL"], "http://127.0.0.1:18080/v1")
            self.assertEqual(env["ONECODE_API_TOKEN"], "test-token")
            self.assertEqual(env["MONGO_URI"], "mongodb://127.0.0.1:37017/LibreChat")
            self.assertEqual(env["ALLOW_REGISTRATION"], "true")
            self.assertEqual(env["ALLOW_EMAIL_LOGIN"], "true")
            self.assertEqual(env["ALLOW_UNVERIFIED_EMAIL_LOGIN"], "true")
            self.assertEqual(env["LOGIN_WINDOW"], "1")
            self.assertEqual(env["LOGIN_MAX"], "100")
            self.assertNotIn("ONEWORD_API_BASE_URL", env)

    def test_build_librechat_env_sets_required_auth_secrets_for_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = ShellLaunchConfig(
                onecode_root=Path(tmp) / "one code",
                librechat_dir=Path(tmp) / "onecode-librechat",
                onecode_host="127.0.0.1",
                onecode_port=18080,
                librechat_host="127.0.0.1",
                librechat_port=13080,
                mongo_port=37017,
                api_token="test-token",
                workspace_root=Path(tmp) / "workspace",
            )

            env = build_librechat_env(config, {})

        self.assertGreaterEqual(len(env["JWT_SECRET"]), 32)
        self.assertGreaterEqual(len(env["JWT_REFRESH_SECRET"]), 32)
        self.assertRegex(env["CREDS_KEY"], r"^[0-9a-f]{64}$")
        self.assertRegex(env["CREDS_IV"], r"^[0-9a-f]{32}$")
        self.assertEqual(env["MEILI_NO_SYNC"], "true")

    def test_build_librechat_env_generates_fresh_auth_secrets_for_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = ShellLaunchConfig(
                onecode_root=Path(tmp) / "one code",
                librechat_dir=Path(tmp) / "onecode-librechat",
                onecode_host="127.0.0.1",
                onecode_port=18080,
                librechat_host="127.0.0.1",
                librechat_port=13080,
                mongo_port=37017,
                api_token="test-token",
                workspace_root=Path(tmp) / "workspace",
            )

            first = build_librechat_env(config, {})
            second = build_librechat_env(config, {})

        self.assertNotEqual(first["JWT_SECRET"], second["JWT_SECRET"])
        self.assertNotEqual(first["JWT_REFRESH_SECRET"], second["JWT_REFRESH_SECRET"])
        self.assertNotEqual(first["CREDS_KEY"], second["CREDS_KEY"])
        self.assertNotEqual(first["CREDS_IV"], second["CREDS_IV"])

    def test_build_librechat_env_does_not_inherit_openai_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = ShellLaunchConfig(
                onecode_root=Path(tmp) / "one code",
                librechat_dir=Path(tmp) / "onecode-librechat",
                onecode_host="127.0.0.1",
                onecode_port=18080,
                librechat_host="127.0.0.1",
                librechat_port=13080,
                mongo_port=37017,
                api_token="test-token",
                workspace_root=Path(tmp) / "workspace",
            )

            env = build_librechat_env(
                config,
                {
                    "OPENAI_API_KEY": "host-key",
                    "OPENAI_BASE_URL": "http://host-openai.test/v1",
                    "OPENAI_MODEL": "gpt-5.5",
                },
            )

            self.assertNotIn("OPENAI_API_KEY", env)
            self.assertNotIn("OPENAI_BASE_URL", env)
            self.assertNotIn("OPENAI_MODEL", env)

    def test_onecode_env_uses_openai_base_url_and_model_when_present(self):
        from onecode.shell_launcher import build_onecode_env

        with tempfile.TemporaryDirectory() as tmp:
            config = ShellLaunchConfig(
                onecode_root=Path(tmp) / "one code",
                librechat_dir=Path(tmp) / "onecode-librechat",
                onecode_host="127.0.0.1",
                onecode_port=18080,
                librechat_host="127.0.0.1",
                librechat_port=13080,
                mongo_port=37017,
                api_token="test-token",
                workspace_root=Path(tmp) / "workspace",
            )

            env = build_onecode_env(
                config,
                {
                    "OPENAI_API_KEY": "test-key",
                    "OPENAI_BASE_URL": "http://127.0.0.1:6780/v1",
                    "OPENAI_MODEL": "gpt-5.5",
                },
            )

        self.assertEqual(env["ONECODE_MODEL_PROVIDER"], "chat")
        self.assertEqual(env["ONECODE_MODEL_ENDPOINT"], "http://127.0.0.1:6780/v1")
        self.assertEqual(env["ONECODE_MODEL"], "gpt-5.5")
        self.assertEqual(env["OPENAI_API_KEY"], "test-key")

    def test_shell_env_exports_allowed_workspace_roots(self):
        from onecode.shell_launcher import build_onecode_env

        with tempfile.TemporaryDirectory() as tmp:
            workspace_root = Path(tmp) / "workspace"
            config = ShellLaunchConfig(
                onecode_root=Path(tmp) / "one code",
                librechat_dir=Path(tmp) / "onecode-librechat",
                onecode_host="127.0.0.1",
                onecode_port=18080,
                librechat_host="127.0.0.1",
                librechat_port=13080,
                mongo_port=37017,
                api_token="test-token",
                workspace_root=workspace_root,
            )

            self.assertEqual(build_onecode_env(config, {})["ONECODE_ALLOWED_WORKSPACE_ROOTS"], str(workspace_root))
            self.assertEqual(build_librechat_env(config, {})["ONECODE_ALLOWED_WORKSPACE_ROOTS"], str(workspace_root))

    def test_default_local_credentials_are_explicit_for_preview(self):
        self.assertEqual(DEFAULT_LOCAL_EMAIL, "onecode@local.test")
        self.assertEqual(DEFAULT_LOCAL_PASSWORD, "OneCode123!")

    def test_default_shell_ports_match_local_onecode_mapping(self):
        self.assertEqual(DEFAULT_ONECODE_PORT, 19080)
        self.assertEqual(DEFAULT_LIBRECHAT_PORT, 14080)
        self.assertEqual(DEFAULT_MONGO_PORT, 39017)

        class Args:
            onecode_root = "/tmp/one code"
            librechat_dir = "/tmp/onecode-librechat"
            workspace = "/tmp/onecode-workspace"
            onecode_host = "127.0.0.1"
            librechat_host = "127.0.0.1"
            api_token = "dev-local-token"
            email = DEFAULT_LOCAL_EMAIL
            password = DEFAULT_LOCAL_PASSWORD
            open_browser = False
            show_credentials = False

        config = config_from_args(Args())

        self.assertEqual(config.onecode_port, 19080)
        self.assertEqual(config.librechat_port, 14080)
        self.assertEqual(config.mongo_port, 39017)

    def test_runtime_config_allows_selected_onecode_port(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = ShellLaunchConfig(
                onecode_root=Path(tmp) / "one code",
                librechat_dir=Path(tmp) / "onecode-librechat",
                onecode_host="127.0.0.1",
                onecode_port=18080,
                librechat_host="127.0.0.1",
                librechat_port=13080,
                mongo_port=37017,
                api_token="test-token",
                workspace_root=Path(tmp) / "workspace",
            )
            path = build_runtime_config(config)
            text = path.read_text(encoding="utf-8")

            self.assertIn("127.0.0.1:18080", text)
            self.assertIn("localhost:18080", text)
            self.assertIn("baseURL: '${ONECODE_API_BASE_URL}'", text)

    def test_shell_status_reports_down_when_services_are_unreachable(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = ShellLaunchConfig(
                onecode_root=Path(tmp) / "one code",
                librechat_dir=Path(tmp) / "onecode-librechat",
                onecode_host="127.0.0.1",
                onecode_port=9,
                librechat_host="127.0.0.1",
                librechat_port=9,
                mongo_port=9,
                api_token="test-token",
                workspace_root=Path(tmp) / "workspace",
            )

            result = shell_status(config)

        self.assertEqual(result["status"], "down")
        self.assertFalse(result["checks"]["onecode_api"]["ok"])
        self.assertFalse(result["checks"]["librechat_shell"]["ok"])
        self.assertFalse(result["checks"]["mongo"]["ok"])
        self.assertIn("onecode shell", result["hint"])

    def test_check_url_reports_unreachable_loopback_without_raising(self):
        result = check_url("http://127.0.0.1:9/health", timeout_seconds=0.2)

        self.assertFalse(result["ok"])
        self.assertEqual(result["url"], "http://127.0.0.1:9/health")

    def test_check_tcp_reports_unreachable_port_without_raising(self):
        result = check_tcp("127.0.0.1", 9, timeout_seconds=0.2)

        self.assertFalse(result["ok"])
        self.assertEqual(result["host"], "127.0.0.1")
        self.assertEqual(result["port"], 9)


class ProcessRunningTests(unittest.TestCase):
    def test_process_is_running_rejects_exited_process(self):
        class ExitedProcess:
            def poll(self):
                return 1

        self.assertFalse(process_is_running(ExitedProcess()))

    def test_process_is_running_accepts_live_process(self):
        class LiveProcess:
            def poll(self):
                return None

        self.assertTrue(process_is_running(LiveProcess()))


class ShellLauncherCliTests(unittest.TestCase):
    def test_shell_subcommand_is_registered(self):
        from onecode.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["shell", "--librechat-dir", "/tmp/shell", "--no-browser"])

        self.assertEqual(args.subcommand, "shell")
        self.assertEqual(args.librechat_dir, "/tmp/shell")
        self.assertFalse(args.open_browser)
        self.assertFalse(args.show_credentials)

    def test_shell_subcommand_can_explicitly_show_credentials(self):
        from onecode.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["shell", "--librechat-dir", "/tmp/shell", "--show-credentials"])

        self.assertTrue(args.show_credentials)

    def test_shell_subcommand_defaults_to_local_onecode_mapping(self):
        from onecode.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["shell", "--librechat-dir", "/tmp/shell", "--no-browser"])

        self.assertEqual(args.onecode_port, 19080)
        self.assertEqual(args.librechat_port, 14080)
        self.assertEqual(args.mongo_port, 39017)

    def test_serve_subcommand_defaults_to_shell_api_port(self):
        from onecode.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["serve"])

        self.assertEqual(args.port, 19080)

    def test_shell_status_subcommand_defaults_to_local_onecode_mapping(self):
        from onecode.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["shell-status"])

        self.assertEqual(args.subcommand, "shell-status")
        self.assertEqual(args.onecode_port, 19080)
        self.assertEqual(args.librechat_port, 14080)
        self.assertEqual(args.mongo_port, 39017)
        self.assertFalse(args.open_browser)
        self.assertTrue(args.show_credentials)

    def test_shell_subcommand_dispatches_to_launcher(self):
        from onecode.cli import main

        with patch("onecode.shell_launcher.launch_shell", return_value=0) as launcher:
            exit_code = main(["shell", "--librechat-dir", "/tmp/shell", "--no-browser"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(launcher.call_count, 1)
        self.assertEqual(launcher.call_args.args[0].librechat_dir, Path("/tmp/shell").resolve())
        self.assertFalse(launcher.call_args.args[0].open_browser)
        self.assertFalse(launcher.call_args.args[0].show_credentials)


if __name__ == "__main__":
    unittest.main()
