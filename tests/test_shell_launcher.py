import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from onecode.shell_launcher import (
    DEFAULT_LOCAL_EMAIL,
    DEFAULT_LOCAL_PASSWORD,
    ShellLaunchConfig,
    build_librechat_env,
    build_runtime_config,
    default_librechat_dir,
    process_is_running,
)


class ShellLauncherConfigTests(unittest.TestCase):
    def test_default_librechat_dir_points_to_adjacent_onecode_shell(self):
        project_root = Path("/Users/example/root/one code")

        self.assertEqual(default_librechat_dir(project_root), Path("/Users/example/root/onecode-librechat"))

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
                    "OPENAI_BASE_URL": "http://10.0.0.184:6780/v1",
                    "OPENAI_MODEL": "gpt-5.5",
                },
            )

        self.assertEqual(env["ONECODE_MODEL_PROVIDER"], "chat")
        self.assertEqual(env["ONECODE_MODEL_ENDPOINT"], "http://10.0.0.184:6780/v1")
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
