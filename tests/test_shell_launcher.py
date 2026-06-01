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
    LIBRECHAT_LOCAL_SECRETS,
    ShellLaunchConfig,
    build_librechat_env,
    build_runtime_config,
    check_tcp,
    check_url,
    config_from_args,
    default_librechat_dir,
    ensure_librechat_runtime_dirs,
    process_is_running,
    shell_status,
)


class ShellLauncherConfigTests(unittest.TestCase):
    def test_default_librechat_dir_prefers_bundled_custom_shell(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "onecode"
            bundled_shell = project_root / "shell" / "onecode-librechat"
            bundled_shell.mkdir(parents=True)

            self.assertEqual(default_librechat_dir(project_root), bundled_shell.resolve())

    def test_default_librechat_dir_falls_back_to_adjacent_development_shell(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "one code"
            adjacent_shell = Path(tmp) / "onecode-librechat"
            adjacent_shell.mkdir(parents=True)

            self.assertEqual(default_librechat_dir(project_root), adjacent_shell.resolve())

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
            for key, value in LIBRECHAT_LOCAL_SECRETS.items():
                self.assertEqual(env[key], value)
            self.assertNotIn("ONEWORD_API_BASE_URL", env)

    def test_build_librechat_env_preserves_operator_secrets(self):
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

            env = build_librechat_env(config, {"JWT_SECRET": "operator-secret"})

        self.assertEqual(env["JWT_SECRET"], "operator-secret")

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

    def test_default_shell_ports_match_local_onecode_mapping(self):
        self.assertEqual(DEFAULT_ONECODE_PORT, 19080)
        self.assertEqual(DEFAULT_LIBRECHAT_PORT, 14080)
        self.assertEqual(DEFAULT_MONGO_PORT, 39017)

        class Args:
            onecode_root = "/tmp/onecode"
            librechat_dir = "/tmp/onecode/shell/onecode-librechat"
            workspace = "/tmp/onecode-workspace"
            onecode_host = "127.0.0.1"
            librechat_host = "127.0.0.1"
            api_token = "dev-local-token"
            email = DEFAULT_LOCAL_EMAIL
            password = DEFAULT_LOCAL_PASSWORD
            shell_mode = "librechat"
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

    def test_librechat_runtime_dirs_are_created_without_runtime_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            shell = Path(tmp) / "onecode-librechat"
            shell.mkdir()

            ensure_librechat_runtime_dirs(shell)

            self.assertTrue((shell / "data").is_dir())
            self.assertEqual(list((shell / "data").iterdir()), [])

    def test_bundled_shell_defaults_map_to_onecode_api_port(self):
        project_root = Path(__file__).resolve().parents[1]
        shell = project_root / "shell" / "onecode-librechat"

        files = [
            shell / "librechat.yaml",
            shell / "api" / "server" / "services" / "OneCode" / "projectPicker.js",
            shell / "scripts" / "onecode-smoke.mjs",
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in files)

        self.assertIn("127.0.0.1:19080", combined)
        self.assertIn("localhost:19080", combined)
        self.assertNotIn("127.0.0.1:8080", combined)
        self.assertNotIn("localhost:8080/v1", combined)

    def test_shell_status_reports_down_when_librechat_services_are_unreachable(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = ShellLaunchConfig(
                onecode_root=Path(tmp) / "onecode",
                librechat_dir=Path(tmp) / "onecode" / "shell" / "onecode-librechat",
                onecode_host="127.0.0.1",
                onecode_port=9,
                librechat_host="127.0.0.1",
                librechat_port=9,
                mongo_port=9,
                api_token="test-token",
                workspace_root=Path(tmp) / "workspace",
                shell_mode="librechat",
            )

            result = shell_status(config)

        self.assertEqual(result["status"], "down")
        self.assertEqual(result["shell_mode"], "librechat")
        self.assertFalse(result["checks"]["onecode_api"]["ok"])
        self.assertFalse(result["checks"]["librechat_shell"]["ok"])
        self.assertFalse(result["checks"]["mongo"]["ok"])
        self.assertIn("onecode shell", result["hint"])

    def test_shell_status_reports_down_when_integrated_shell_is_unreachable(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = ShellLaunchConfig(
                onecode_root=Path(tmp) / "onecode",
                librechat_dir=Path(tmp) / "unused",
                onecode_host="127.0.0.1",
                onecode_port=9,
                librechat_host="127.0.0.1",
                librechat_port=14080,
                mongo_port=39017,
                api_token="test-token",
                workspace_root=Path(tmp) / "workspace",
                shell_mode="integrated",
            )

            result = shell_status(config)

        self.assertEqual(result["status"], "down")
        self.assertEqual(result["shell_mode"], "integrated")
        self.assertFalse(result["checks"]["onecode_api"]["ok"])
        self.assertFalse(result["checks"]["integrated_shell"]["ok"])
        self.assertNotIn("mongo", result["checks"])

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
        args = parser.parse_args(["shell", "--no-browser"])

        self.assertEqual(args.subcommand, "shell")
        self.assertEqual(args.shell_mode, "librechat")
        self.assertEqual(args.onecode_port, 19080)
        self.assertEqual(args.librechat_port, 14080)
        self.assertEqual(args.mongo_port, 39017)
        self.assertIsNone(args.librechat_dir)
        self.assertFalse(args.open_browser)
        self.assertFalse(args.show_credentials)

    def test_shell_subcommand_supports_explicit_librechat_mode(self):
        from onecode.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["shell", "--shell-mode", "librechat", "--librechat-dir", "/tmp/shell"])

        self.assertEqual(args.shell_mode, "librechat")
        self.assertEqual(args.librechat_dir, "/tmp/shell")
        self.assertEqual(args.librechat_port, 14080)

    def test_shell_subcommand_can_explicitly_show_credentials(self):
        from onecode.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["shell", "--librechat-dir", "/tmp/shell", "--show-credentials"])

        self.assertTrue(args.show_credentials)

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
        self.assertEqual(args.shell_mode, "librechat")
        self.assertEqual(args.onecode_port, 19080)
        self.assertEqual(args.librechat_port, 14080)
        self.assertEqual(args.mongo_port, 39017)
        self.assertFalse(args.open_browser)
        self.assertTrue(args.show_credentials)

    def test_shell_subcommand_dispatches_to_launcher(self):
        from onecode.cli import main

        with patch("onecode.shell_launcher.launch_shell", return_value=0) as launcher:
            exit_code = main(["shell", "--no-browser"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(launcher.call_count, 1)
        self.assertEqual(launcher.call_args.args[0].shell_mode, "librechat")
        self.assertEqual(launcher.call_args.args[0].onecode_port, 19080)
        self.assertEqual(launcher.call_args.args[0].librechat_port, 14080)
        self.assertEqual(launcher.call_args.args[0].mongo_port, 39017)
        self.assertFalse(launcher.call_args.args[0].open_browser)
        self.assertFalse(launcher.call_args.args[0].show_credentials)

    def test_librechat_shell_reports_missing_node_dependencies_clearly(self):
        from onecode.shell_launcher import launch_shell

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "onecode"
            shell = root / "shell" / "onecode-librechat"
            (root / "src" / "onecode").mkdir(parents=True)
            shell.mkdir(parents=True)
            (shell / "package.json").write_text("{}", encoding="utf-8")
            config = ShellLaunchConfig(
                onecode_root=root,
                librechat_dir=shell,
                onecode_host="127.0.0.1",
                onecode_port=19080,
                librechat_host="127.0.0.1",
                librechat_port=14080,
                mongo_port=39017,
                api_token="test-token",
                workspace_root=Path(tmp) / "workspace",
                shell_mode="librechat",
            )

            with self.assertRaises(FileNotFoundError) as raised:
                launch_shell(config)

        self.assertIn("Run `npm install`", str(raised.exception))

    def test_integrated_shell_does_not_require_source_tree_package_path(self):
        from onecode.shell_launcher import launch_shell

        with tempfile.TemporaryDirectory() as tmp, patch("onecode.shell_launcher.launch_integrated_shell", return_value=0):
            config = ShellLaunchConfig(
                onecode_root=Path(tmp) / "installed-workdir",
                librechat_dir=Path(tmp) / "unused-librechat",
                onecode_host="127.0.0.1",
                onecode_port=14080,
                librechat_host="127.0.0.1",
                librechat_port=3080,
                mongo_port=27017,
                api_token="test-token",
                workspace_root=Path(tmp) / "workspace",
                shell_mode="integrated",
            )

            self.assertEqual(launch_shell(config), 0)

    def test_integrated_shell_detects_process_exit_during_startup(self):
        from onecode.shell_launcher import launch_integrated_shell

        class ExitedProcess:
            def poll(self):
                return 1

            def terminate(self):
                raise AssertionError("exited process should not be terminated")

            def kill(self):
                raise AssertionError("exited process should not be killed")

        with tempfile.TemporaryDirectory() as tmp, patch("onecode.shell_launcher.start_process", return_value=ExitedProcess()), patch(
            "onecode.shell_launcher.wait_for_url",
            return_value=True,
        ):
            config = ShellLaunchConfig(
                onecode_root=Path(tmp),
                librechat_dir=Path(tmp) / "unused-librechat",
                onecode_host="127.0.0.1",
                onecode_port=14080,
                librechat_host="127.0.0.1",
                librechat_port=3080,
                mongo_port=27017,
                api_token="test-token",
                workspace_root=Path(tmp) / "workspace",
                shell_mode="integrated",
            )

            with self.assertRaises(RuntimeError) as raised:
                launch_integrated_shell(config)

        self.assertIn("exited during startup", str(raised.exception))

    def test_integrated_shell_creates_workspace_before_starting_api(self):
        from onecode.shell_launcher import launch_integrated_shell

        class ExitedAfterHealthProcess:
            def poll(self):
                return 1

            def terminate(self):
                raise AssertionError("exited process should not be terminated")

            def kill(self):
                raise AssertionError("exited process should not be killed")

        with tempfile.TemporaryDirectory() as tmp, patch("onecode.shell_launcher.start_process", return_value=ExitedAfterHealthProcess()), patch(
            "onecode.shell_launcher.wait_for_url",
            return_value=True,
        ):
            workspace = Path(tmp) / "workspace"
            config = ShellLaunchConfig(
                onecode_root=Path(tmp),
                librechat_dir=Path(tmp) / "unused-librechat",
                onecode_host="127.0.0.1",
                onecode_port=14080,
                librechat_host="127.0.0.1",
                librechat_port=3080,
                mongo_port=27017,
                api_token="test-token",
                workspace_root=workspace,
                shell_mode="integrated",
            )

            with self.assertRaises(RuntimeError):
                launch_integrated_shell(config)

            self.assertTrue(workspace.is_dir())

    def test_librechat_shell_still_requires_source_tree_and_librechat_package(self):
        from onecode.shell_launcher import launch_shell

        with tempfile.TemporaryDirectory() as tmp:
            config = ShellLaunchConfig(
                onecode_root=Path(tmp) / "missing-onecode-root",
                librechat_dir=Path(tmp) / "missing-librechat",
                onecode_host="127.0.0.1",
                onecode_port=14080,
                librechat_host="127.0.0.1",
                librechat_port=3080,
                mongo_port=27017,
                api_token="test-token",
                workspace_root=Path(tmp) / "workspace",
                shell_mode="librechat",
            )

            with self.assertRaises(FileNotFoundError):
                launch_shell(config)


if __name__ == "__main__":
    unittest.main()
