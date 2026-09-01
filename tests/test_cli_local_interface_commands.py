import argparse
import ast
import io
import inspect
import json
import os
import subprocess
import sys
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from onecode.cli import build_parser
from onecode.cli_commands.local_interfaces import (
    LOCAL_INTERFACE_COMMANDS,
    dispatch_local_interface_command,
    register_local_interface_commands,
)


TARGET_COMMANDS = ("serve", "shell", "shell-status", "tui")


def parser_contract(parser):
    subparsers = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    contract = {}
    for command in TARGET_COMMANDS:
        command_parser = subparsers.choices[command]
        contract[command] = {
            "description": command_parser.description,
            "defaults": dict(command_parser._defaults),
            "actions": [
                {
                    "option_strings": list(action.option_strings),
                    "dest": action.dest,
                    "required": action.required,
                    "default": action.default,
                    "choices": list(action.choices) if action.choices is not None else None,
                    "nargs": action.nargs,
                    "action_class": type(action).__name__,
                    "type_name": getattr(action.type, "__name__", None),
                }
                for action in command_parser._actions
                if not isinstance(action, argparse._HelpAction)
            ],
        }
    return contract


class CliLocalInterfaceCommandTests(unittest.TestCase):
    def test_local_interface_command_set_is_explicit(self):
        self.assertEqual(
            LOCAL_INTERFACE_COMMANDS,
            frozenset({"serve", "shell", "shell-status", "tui"}),
        )

    def test_existing_local_interface_parser_contract_is_frozen(self):
        contract = parser_contract(build_parser())

        self.assertEqual(contract["serve"]["description"], "Serve OneCode as an OpenAI-compatible endpoint for LibreChat.")
        self.assertEqual(contract["serve"]["defaults"], {})
        self.assertEqual(contract["serve"]["actions"][0]["default"], "127.0.0.1")
        self.assertEqual(contract["serve"]["actions"][1]["default"], 19080)
        self.assertEqual(contract["serve"]["actions"][1]["type_name"], "int")
        self.assertEqual(contract["serve"]["actions"][2]["action_class"], "_StoreTrueAction")

        self.assertEqual(contract["shell"]["description"], "Launch the local OneCode Agent shell with LibreChat.")
        self.assertEqual(contract["shell"]["defaults"], {"open_browser": True})
        self.assertEqual(contract["shell"]["actions"][-2]["action_class"], "_StoreTrueAction")
        self.assertEqual(contract["shell"]["actions"][-1]["dest"], "open_browser")
        self.assertEqual(contract["shell"]["actions"][-1]["action_class"], "_StoreFalseAction")

        self.assertEqual(
            contract["shell-status"]["description"],
            "Check whether the local OneCode Agent shell services are reachable.",
        )
        self.assertEqual(
            contract["shell-status"]["defaults"],
            {"open_browser": False, "show_credentials": True},
        )

        self.assertEqual(contract["tui"]["description"], None)
        self.assertEqual(contract["tui"]["defaults"], {})
        self.assertEqual(
            contract["tui"]["actions"][2]["choices"],
            [
                "chat",
                "openai-compatible",
                "compatible",
                "qwen",
                "dashscope",
                "deepseek",
                "kimi",
                "moonshot",
                "zhipu",
                "glm",
            ],
        )

    def test_dispatch_returns_none_for_unhandled_command(self):
        parser = argparse.ArgumentParser()

        self.assertIsNone(
            dispatch_local_interface_command(argparse.Namespace(subcommand="run"), parser)
        )

    def test_serve_dispatch_preserves_environment_and_call_contract(self):
        calls = []
        web_api = types.ModuleType("onecode.web.api")

        def run_server(*, host, port):
            calls.append((host, port, os.environ.get("ONECODE_ALLOW_UNAUTHENTICATED")))

        web_api.run_server = run_server
        args = argparse.Namespace(
            subcommand="serve",
            host="127.0.0.2",
            port=19081,
            allow_unauthenticated_local=True,
        )
        with patch.dict(sys.modules, {"onecode.web.api": web_api}), patch.dict(
            os.environ, {}, clear=True
        ):
            exit_code = dispatch_local_interface_command(args, argparse.ArgumentParser())

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, [("127.0.0.2", 19081, "true")])

    def test_shell_dispatch_passes_config_and_launcher_exit_code(self):
        launcher = types.ModuleType("onecode.shell_launcher")
        calls = []
        launcher.config_from_args = lambda args: {"workspace": args.workspace}

        def launch_shell(config):
            calls.append(config)
            return 7

        launcher.launch_shell = launch_shell
        args = argparse.Namespace(subcommand="shell", workspace="/tmp/work")
        with patch.dict(sys.modules, {"onecode.shell_launcher": launcher}):
            exit_code = dispatch_local_interface_command(args, argparse.ArgumentParser())

        self.assertEqual(exit_code, 7)
        self.assertEqual(calls, [{"workspace": "/tmp/work"}])

    def test_shell_dispatch_converts_launcher_error_to_parser_error(self):
        launcher = types.ModuleType("onecode.shell_launcher")
        launcher.config_from_args = lambda args: {"workspace": args.workspace}

        def launch_shell(_config):
            raise FileNotFoundError("missing shell")

        launcher.launch_shell = launch_shell
        stderr = io.StringIO()
        with patch.dict(sys.modules, {"onecode.shell_launcher": launcher}), redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as raised:
                dispatch_local_interface_command(
                    argparse.Namespace(subcommand="shell", workspace="/tmp/work"),
                    argparse.ArgumentParser(prog="onecode"),
                )

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("missing shell", stderr.getvalue())

    def test_shell_status_dispatch_prints_json_and_maps_exit_code(self):
        launcher = types.ModuleType("onecode.shell_launcher")
        launcher.config_from_args = lambda args: {"workspace": args.workspace}
        launcher.shell_status = lambda config: {"status": "down", "config": config}
        stdout = io.StringIO()
        with patch.dict(sys.modules, {"onecode.shell_launcher": launcher}), redirect_stdout(stdout):
            exit_code = dispatch_local_interface_command(
                argparse.Namespace(subcommand="shell-status", workspace="/tmp/work"),
                argparse.ArgumentParser(),
            )

        self.assertEqual(exit_code, 1)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {"status": "down", "config": {"workspace": "/tmp/work"}},
        )

    def test_tui_dispatch_converts_workspace_and_preserves_arguments(self):
        tui_package = types.ModuleType("onecode.tui")
        tui_package.__path__ = []
        tui_app = types.ModuleType("onecode.tui.app")
        calls = []

        def run_tui(*, workspace, model, provider_kind):
            calls.append((workspace, model, provider_kind))

        tui_app.run_tui = run_tui
        args = argparse.Namespace(
            subcommand="tui",
            workspace="/tmp/work",
            model="local-model",
            provider="qwen",
        )
        with patch.dict(sys.modules, {"onecode.tui": tui_package, "onecode.tui.app": tui_app}):
            exit_code = dispatch_local_interface_command(args, argparse.ArgumentParser())

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, [(Path("/tmp/work"), "local-model", "qwen")])

    def test_adapter_import_does_not_eagerly_load_interface_modules(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import json,sys; "
                    "import onecode.cli_commands.local_interfaces; "
                    "print(json.dumps([name for name in "
                    "('onecode.web.api','onecode.tui.app','onecode.shell_launcher') "
                    "if name in sys.modules]))"
                ),
            ],
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": "src"},
        )

        self.assertEqual(json.loads(completed.stdout), [])

    def test_adapter_has_stdlib_only_top_level_imports(self):
        path = Path("src/onecode/cli_commands/local_interfaces.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported_modules = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules.append(node.module)

        self.assertFalse([module for module in imported_modules if module.startswith("onecode.")])

    def test_runtime_layers_do_not_reverse_depend_on_local_interface_adapter(self):
        paths = [
            Path("src/onecode/web/api.py"),
            Path("src/onecode/tui/app.py"),
            Path("src/onecode/shell_launcher.py"),
            *Path("src/onecode/kernel").glob("*.py"),
        ]

        for path in paths:
            with self.subTest(path=path):
                self.assertNotIn(
                    "onecode.cli_commands.local_interfaces",
                    path.read_text(encoding="utf-8"),
                )

    def test_cli_delegates_without_direct_local_interface_branches(self):
        import onecode.cli

        main_source = inspect.getsource(onecode.cli.main)
        parser_source = inspect.getsource(onecode.cli.build_parser)
        for command in LOCAL_INTERFACE_COMMANDS:
            self.assertNotIn(f'args.subcommand == "{command}"', main_source)
            self.assertNotIn(f'add_parser("{command}")', parser_source)

    def test_cli_functions_are_materially_shorter_after_interface_extraction(self):
        import onecode.cli

        main_lines = len(inspect.getsource(onecode.cli.main).splitlines())
        parser_lines = len(inspect.getsource(onecode.cli.build_parser).splitlines())

        self.assertLess(main_lines, 480)
        self.assertGreaterEqual(500 - main_lines, 20)
        self.assertLess(parser_lines, 220)


if __name__ == "__main__":
    unittest.main()
