import json
import os
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from types import SimpleNamespace
from unittest.mock import patch

from onecode.shell_launcher import (
    DEFAULT_LIBRECHAT_PORT,
    DEFAULT_LOCAL_EMAIL,
    DEFAULT_LOCAL_PASSWORD,
    DEFAULT_MONGO_PORT,
    DEFAULT_ONECODE_PORT,
    EXPECTED_LIBRECHAT_COMMIT,
    ManagedProcess,
    ShellLaunchConfig,
    append_bounded_log,
    build_librechat_env,
    build_onecode_env,
    build_runtime_config,
    check_tcp,
    check_url,
    config_from_args,
    default_librechat_dir,
    librechat_provenance,
    mongo_command,
    preflight_shell,
    process_is_running,
    shell_status,
)
from onecode.shell_state import write_runtime_status


def shell_args(**overrides):
    values = {
        "onecode_root": "/tmp/example-onecode",
        "librechat_dir": "/tmp/example-librechat",
        "workspace": None,
        "onecode_host": "127.0.0.1",
        "onecode_port": DEFAULT_ONECODE_PORT,
        "librechat_host": "127.0.0.1",
        "librechat_port": DEFAULT_LIBRECHAT_PORT,
        "mongo_port": DEFAULT_MONGO_PORT,
        "api_token": "token",
        "email": DEFAULT_LOCAL_EMAIL,
        "password": DEFAULT_LOCAL_PASSWORD,
        "state_dir": None,
        "model_timeout_seconds": 60.0,
        "open_browser": False,
        "show_credentials": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def shell_config(**overrides):
    values = {
        "onecode_root": Path("/tmp/example-onecode"),
        "librechat_dir": Path("/tmp/example-librechat"),
        "onecode_host": "127.0.0.1",
        "onecode_port": DEFAULT_ONECODE_PORT,
        "librechat_host": "127.0.0.1",
        "librechat_port": DEFAULT_LIBRECHAT_PORT,
        "mongo_port": DEFAULT_MONGO_PORT,
        "api_token": "token",
        "workspace_root": Path("/tmp/example-workspace"),
        "runtime_state_root": Path("/tmp/example-state"),
        "open_browser": False,
    }
    values.update(overrides)
    return ShellLaunchConfig(**values)


class ShellLauncherConfigTests(unittest.TestCase):
    def test_state_dir_defaults_under_onecode_home(self):
        with patch.dict(
            "os.environ", {"ONECODE_HOME": "/tmp/onecode-home"}, clear=False
        ):
            config = config_from_args(shell_args())

        self.assertEqual(
            config.runtime_state_root, Path("/tmp/onecode-home/shell")
        )

    def test_mongo_command_uses_persistent_db_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = shell_config(runtime_state_root=Path(tmp) / "state")
            command = mongo_command(config)

        self.assertIn(str(Path(tmp) / "state" / "mongo"), " ".join(command))

    def test_shell_status_never_returns_password(self):
        with patch("onecode.shell_launcher.check_url", return_value={"ok": False}), patch(
            "onecode.shell_launcher.check_tcp", return_value={"ok": False}
        ), patch(
            "onecode.shell_launcher.librechat_provenance",
            return_value={"version": "v0.8.7"},
        ), patch(
            "onecode.shell_launcher.read_model_config",
            return_value={"configured": False},
        ):
            result = shell_status(shell_config())

        self.assertNotIn("password", json.dumps(result).lower())

    def test_runtime_config_sets_onecode_retry_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = build_runtime_config(
                shell_config(runtime_state_root=Path(tmp) / "state")
            )

            self.assertIn("maxRetries: 0", path.read_text(encoding="utf-8"))

    def test_runtime_config_disables_onecode_title_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = build_runtime_config(
                shell_config(runtime_state_root=Path(tmp) / "state")
            )
            text = path.read_text(encoding="utf-8")

        self.assertIn("titleConvo: false", text)
        self.assertNotIn("titleModel:", text)

    def test_model_timeout_cli_reaches_onecode_environment(self):
        config = shell_config(model_timeout_seconds=12.5)

        env = build_onecode_env(config, {})

        self.assertEqual(env["ONECODE_MODEL_TIMEOUT_SECONDS"], "12.5")
        self.assertEqual(env["ONECODE_REQUIRE_EXPLICIT_TASK_WORKSPACE"], "true")

    def test_provenance_requires_v087_as_an_ancestor(self):
        with tempfile.TemporaryDirectory() as tmp:
            librechat_dir = Path(tmp) / "librechat"
            librechat_dir.mkdir()
            (librechat_dir / "package.json").write_text(
                json.dumps({"version": "v0.8.7"}), encoding="utf-8"
            )
            config = shell_config(librechat_dir=librechat_dir)
            with patch("onecode.shell_launcher.subprocess.run") as run:
                run.side_effect = [
                    CompletedProcess([], 0, "abc123\n", ""),
                    CompletedProcess([], 0, "", ""),
                ]
                result = librechat_provenance(config)

        self.assertEqual(result["community_base_commit"], EXPECTED_LIBRECHAT_COMMIT)
        self.assertEqual(result["head_commit"], "abc123")
        self.assertTrue(result["community_base_is_ancestor"])

    def test_preflight_rejects_an_occupied_port(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "onecode" / "src" / "onecode").mkdir(parents=True)
            librechat_dir = root / "librechat"
            librechat_dir.mkdir()
            (librechat_dir / "package.json").write_text(
                json.dumps({"version": "v0.8.7"}), encoding="utf-8"
            )
            config = shell_config(
                onecode_root=root / "onecode",
                librechat_dir=librechat_dir,
                runtime_state_root=root / "state",
            )
            with patch(
                "onecode.shell_launcher.shutil.which",
                side_effect=lambda name: f"/usr/bin/{name}",
            ), patch(
                "onecode.shell_launcher.subprocess.run"
            ) as run, patch(
                "onecode.shell_launcher.librechat_provenance",
                return_value={"version": "v0.8.7"},
            ), patch(
                "onecode.shell_launcher.read_model_config",
                return_value={"configured": False},
            ), patch(
                "onecode.shell_launcher.port_is_available", return_value=False
            ):
                run.side_effect = [
                    CompletedProcess([], 0, "v24.14.1\n", ""),
                    CompletedProcess([], 0, "11.13.0\n", ""),
                ]
                with self.assertRaisesRegex(
                    RuntimeError, "port .* is already in use"
                ):
                    preflight_shell(config)

    def test_preflight_missing_librechat_package_explains_resolved_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            onecode_root = Path(tmp) / "one code"
            (onecode_root / "src" / "onecode").mkdir(parents=True)
            librechat_dir = Path(tmp) / "missing-librechat"
            config = shell_config(
                onecode_root=onecode_root,
                librechat_dir=librechat_dir,
            )

            with self.assertRaises(FileNotFoundError) as raised:
                preflight_shell(config)

        message = str(raised.exception)
        self.assertIn(str(librechat_dir.resolve()), message)
        self.assertIn("--librechat-dir '<path>'", message)

    def test_bounded_service_log_redacts_and_caps_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "service.log"
            append_bounded_log(
                path,
                "Authorization: Bearer secret-token\n" + "x" * 5000,
                max_bytes=1024,
            )
            text = path.read_text(encoding="utf-8")

        self.assertLessEqual(len(text.encode("utf-8")), 1024)
        self.assertNotIn("secret-token", text)

    def test_shell_failure_redaction_removes_configured_secrets(self):
        from onecode.shell_launcher import redact_shell_failure

        config = shell_config(
            api_token="opaque-runtime-token", password="opaque-runtime-password"
        )

        redacted = redact_shell_failure(
            config, "failed opaque-runtime-token opaque-runtime-password"
        )

        self.assertNotIn("opaque-runtime-token", redacted)
        self.assertNotIn("opaque-runtime-password", redacted)

    def test_runtime_status_contains_only_service_names_and_pids(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_runtime_status(
                Path(tmp), status="running", services={"mongo": 123}
            )
            payload = json.loads(
                (Path(tmp) / "runtime-status.json").read_text(encoding="utf-8")
            )

        self.assertEqual(payload["services"], {"mongo": 123})
        self.assertNotIn("token", json.dumps(payload).lower())

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

        with patch.dict(
            "os.environ", {"ONECODE_HOME": "/tmp/onecode-home"}, clear=False
        ):
            config = config_from_args(Args())

        self.assertEqual(config.workspace_root, Path("/tmp/example-onecode").resolve())
        self.assertNotEqual(config.runtime_state_root, config.workspace_root)
        self.assertEqual(config.runtime_state_root, Path("/tmp/onecode-home/shell"))

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

            self.assertEqual(env["APP_TITLE"], "OneCode")
            self.assertEqual(env["CUSTOM_FOOTER"], "OneCode")
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

    def test_build_librechat_env_reuses_auth_secrets_for_same_state_root(self):
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

            first = build_librechat_env(config, {})
            second = build_librechat_env(config, {})

        self.assertEqual(first["JWT_SECRET"], second["JWT_SECRET"])
        self.assertEqual(first["JWT_REFRESH_SECRET"], second["JWT_REFRESH_SECRET"])
        self.assertEqual(first["CREDS_KEY"], second["CREDS_KEY"])
        self.assertEqual(first["CREDS_IV"], second["CREDS_IV"])

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

        managed = ManagedProcess(
            "test", ExitedProcess(), Path("/tmp/test.log"), None
        )

        self.assertFalse(process_is_running(managed))

    def test_process_is_running_accepts_live_process(self):
        class LiveProcess:
            def poll(self):
                return None

        managed = ManagedProcess("test", LiveProcess(), Path("/tmp/test.log"), None)

        self.assertTrue(process_is_running(managed))


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

    def test_shell_subcommand_accepts_state_dir_and_model_timeout(self):
        from onecode.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            [
                "shell",
                "--state-dir",
                "/tmp/onecode-state",
                "--model-timeout-seconds",
                "12.5",
                "--no-browser",
            ]
        )

        self.assertEqual(args.state_dir, "/tmp/onecode-state")
        self.assertEqual(args.model_timeout_seconds, 12.5)

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
