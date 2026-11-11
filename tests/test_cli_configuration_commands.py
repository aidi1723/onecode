import argparse
import ast
import io
import inspect
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from onecode.cli import build_parser
from onecode.cli_commands.configuration import (
    CONFIGURATION_COMMANDS,
    dispatch_configuration_command,
    register_configuration_commands,
)


EXPECTED_PARSER_CONTRACT = {
    "list-verifier-presets": [],
    "init-verifier-policy": [
        {
            "option_strings": ["--workspace"],
            "dest": "workspace",
            "required": False,
            "default": ".",
            "choices": None,
            "nargs": None,
            "action_class": "_StoreAction",
            "type": None,
        },
        {
            "option_strings": ["--output"],
            "dest": "output",
            "required": False,
            "default": ".onecode/verifier-policy.json",
            "choices": None,
            "nargs": None,
            "action_class": "_StoreAction",
            "type": None,
        },
        {
            "option_strings": ["--preset"],
            "dest": "preset",
            "required": False,
            "default": None,
            "choices": None,
            "nargs": None,
            "action_class": "_AppendAction",
            "type": None,
        },
        {
            "option_strings": ["--force"],
            "dest": "force",
            "required": False,
            "default": False,
            "choices": None,
            "nargs": 0,
            "action_class": "_StoreTrueAction",
            "type": None,
        },
    ],
    "config": [
        {
            "option_strings": [],
            "dest": "config_action",
            "required": True,
            "default": None,
            "choices": ["set-model", "show", "discover-models"],
            "nargs": "A...",
            "action_class": "_SubParsersAction",
            "type": None,
            "subparser_dest": "config_action",
            "subparser_required": True,
        }
    ],
    "config_actions": {
        "set-model": [
            {
                "option_strings": ["--endpoint"],
                "dest": "endpoint",
                "required": True,
                "default": None,
                "choices": None,
                "nargs": None,
                "action_class": "_StoreAction",
                "type": None,
            },
            {
                "option_strings": ["--api-key"],
                "dest": "api_key",
                "required": True,
                "default": None,
                "choices": None,
                "nargs": None,
                "action_class": "_StoreAction",
                "type": None,
            },
            {
                "option_strings": ["--model"],
                "dest": "model",
                "required": False,
                "default": None,
                "choices": None,
                "nargs": None,
                "action_class": "_StoreAction",
                "type": None,
            },
            {
                "option_strings": ["--provider"],
                "dest": "provider",
                "required": False,
                "default": "openai-compatible",
                "choices": None,
                "nargs": None,
                "action_class": "_StoreAction",
                "type": None,
            },
        ],
        "show": [],
        "discover-models": [
            {
                "option_strings": ["--endpoint"],
                "dest": "endpoint",
                "required": True,
                "default": None,
                "choices": None,
                "nargs": None,
                "action_class": "_StoreAction",
                "type": None,
            },
            {
                "option_strings": ["--api-key"],
                "dest": "api_key",
                "required": True,
                "default": None,
                "choices": None,
                "nargs": None,
                "action_class": "_StoreAction",
                "type": None,
            },
        ],
    },
}


def _actions_contract(parser):
    contract = []
    for action in parser._actions:
        if isinstance(action, argparse._HelpAction):
            continue
        item = {
            "option_strings": list(action.option_strings),
            "dest": action.dest,
            "required": action.required,
            "default": action.default,
            "choices": list(action.choices) if action.choices is not None else None,
            "nargs": action.nargs,
            "action_class": type(action).__name__,
            "type": None if action.type is None else action.type.__name__,
        }
        if isinstance(action, argparse._SubParsersAction):
            item["subparser_dest"] = action.dest
            item["subparser_required"] = action.required
        contract.append(item)
    return contract


def parser_contract(parser):
    subparsers = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    contract = {
        command: _actions_contract(subparsers.choices[command])
        for command in ("list-verifier-presets", "init-verifier-policy", "config")
    }
    config_subparsers = next(
        action
        for action in subparsers.choices["config"]._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    contract["config_actions"] = {
        action: _actions_contract(config_subparsers.choices[action])
        for action in ("set-model", "show", "discover-models")
    }
    return contract


class CliConfigurationCommandTests(unittest.TestCase):
    def test_configuration_command_set_is_explicit(self):
        self.assertEqual(
            CONFIGURATION_COMMANDS,
            frozenset({"list-verifier-presets", "init-verifier-policy", "config"}),
        )

    def test_existing_parser_contract_is_frozen(self):
        self.assertEqual(parser_contract(build_parser()), EXPECTED_PARSER_CONTRACT)

    def test_registration_function_builds_frozen_contract(self):
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="subcommand", required=True)

        register_configuration_commands(subparsers)

        self.assertEqual(parser_contract(parser), EXPECTED_PARSER_CONTRACT)

    def test_dispatch_returns_none_for_unhandled_command(self):
        self.assertIsNone(
            dispatch_configuration_command(
                argparse.Namespace(subcommand="run"),
                argparse.ArgumentParser(),
            )
        )

    def test_dispatch_lists_verifier_presets_as_sorted_json(self):
        stdout = io.StringIO()
        payload = {"zeta": 2, "alpha": 1}

        with patch(
            "onecode.cli_commands.configuration.verifier_policy_presets_summary",
            return_value=payload,
        ), redirect_stdout(stdout):
            exit_code = dispatch_configuration_command(
                argparse.Namespace(subcommand="list-verifier-presets"),
                argparse.ArgumentParser(),
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), '{"alpha": 1, "zeta": 2}\n')

    def test_dispatch_writes_verifier_policy_with_exact_arguments(self):
        stdout = io.StringIO()
        payload = {"written": True, "verifier_ids": ["python-unittest"]}

        with patch(
            "onecode.cli_commands.configuration.write_verifier_policy",
            return_value=payload,
        ) as write_policy, redirect_stdout(stdout):
            exit_code = dispatch_configuration_command(
                argparse.Namespace(
                    subcommand="init-verifier-policy",
                    workspace="/tmp/workspace",
                    output=".onecode/custom-policy.json",
                    preset=["python-unittest"],
                    force=True,
                ),
                argparse.ArgumentParser(),
            )

        self.assertEqual(exit_code, 0)
        write_policy.assert_called_once_with(
            workspace=Path("/tmp/workspace"),
            output=".onecode/custom-policy.json",
            preset_ids=["python-unittest"],
            force=True,
        )
        self.assertEqual(json.loads(stdout.getvalue()), payload)

    def test_dispatch_routes_verifier_policy_value_error_through_parser_error(self):
        stderr = io.StringIO()
        parser = argparse.ArgumentParser(prog="onecode")

        with patch(
            "onecode.cli_commands.configuration.write_verifier_policy",
            side_effect=ValueError("unsafe output"),
        ), redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            dispatch_configuration_command(
                argparse.Namespace(
                    subcommand="init-verifier-policy",
                    workspace=".",
                    output="../policy.json",
                    preset=None,
                    force=False,
                ),
                parser,
            )

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("onecode: error: unsafe output", stderr.getvalue())

    def test_dispatch_sets_model_without_printing_raw_api_key(self):
        stdout = io.StringIO()
        secret = "sk-never-print-this"
        payload = {
            "configured": True,
            "endpoint": "http://127.0.0.1:6780/v1",
            "model": "gpt-5.5",
        }

        with patch(
            "onecode.cli_commands.configuration.write_model_config",
            return_value=payload,
        ) as write_config, redirect_stdout(stdout):
            exit_code = dispatch_configuration_command(
                argparse.Namespace(
                    subcommand="config",
                    config_action="set-model",
                    endpoint="http://127.0.0.1:6780/v1",
                    api_key=secret,
                    model=None,
                    provider="openai-compatible",
                ),
                argparse.ArgumentParser(),
            )

        self.assertEqual(exit_code, 0)
        write_config.assert_called_once_with(
            endpoint="http://127.0.0.1:6780/v1",
            api_key=secret,
            model=None,
            provider="openai-compatible",
        )
        self.assertEqual(json.loads(stdout.getvalue()), payload)
        self.assertNotIn(secret, stdout.getvalue())

    def test_dispatch_shows_masked_model_config(self):
        stdout = io.StringIO()
        payload = {"model": "gpt-4.1", "api_key_configured": True}

        with patch(
            "onecode.cli_commands.configuration.read_model_config",
            return_value=payload,
        ) as read_config, redirect_stdout(stdout):
            exit_code = dispatch_configuration_command(
                argparse.Namespace(subcommand="config", config_action="show"),
                argparse.ArgumentParser(),
            )

        self.assertEqual(exit_code, 0)
        read_config.assert_called_once_with()
        self.assertEqual(json.loads(stdout.getvalue()), payload)

    def test_dispatch_discovers_models_via_service_without_real_network(self):
        stdout = io.StringIO()
        secret = "sk-discovery-secret"
        payload = {"models": ["gpt-5.5"], "source": "remote"}

        with patch(
            "onecode.cli_commands.configuration.discover_models",
            return_value=payload,
        ) as discover, redirect_stdout(stdout):
            exit_code = dispatch_configuration_command(
                argparse.Namespace(
                    subcommand="config",
                    config_action="discover-models",
                    endpoint="http://127.0.0.1:6780/v1",
                    api_key=secret,
                ),
                argparse.ArgumentParser(),
            )

        self.assertEqual(exit_code, 0)
        discover.assert_called_once_with("http://127.0.0.1:6780/v1", secret)
        self.assertEqual(json.loads(stdout.getvalue()), payload)
        self.assertNotIn(secret, stdout.getvalue())

    def test_dispatch_returns_none_for_impossible_unknown_config_action(self):
        self.assertIsNone(
            dispatch_configuration_command(
                argparse.Namespace(subcommand="config", config_action="unknown"),
                argparse.ArgumentParser(),
            )
        )

    def test_adapter_imports_only_approved_configuration_services(self):
        path = Path("src/onecode/cli_commands/configuration.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        allowed_onecode_modules = {
            "onecode.kernel.model_config",
            "onecode.kernel.verifier",
        }
        imported_onecode_modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_onecode_modules.extend(
                    alias.name for alias in node.names if alias.name.startswith("onecode.")
                )
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module is not None
                and node.module.startswith("onecode.")
            ):
                imported_onecode_modules.append(node.module)

        self.assertEqual(set(imported_onecode_modules), allowed_onecode_modules)

    def test_runtime_layers_do_not_reverse_depend_on_configuration_adapter(self):
        excluded_kernel_modules = {"model_config.py", "verifier.py"}
        paths = [
            Path("src/onecode/web/api.py"),
            Path("src/onecode/tui/app.py"),
            Path("src/onecode/cli_commands/read_only.py"),
            Path("src/onecode/cli_commands/local_interfaces.py"),
            *[
                path
                for path in Path("src/onecode/kernel").glob("*.py")
                if path.name not in excluded_kernel_modules
            ],
        ]

        for path in paths:
            with self.subTest(path=path):
                self.assertNotIn(
                    "onecode.cli_commands.configuration",
                    path.read_text(encoding="utf-8"),
                )

    def test_cli_set_and_show_never_print_raw_api_key(self):
        from onecode.cli import main

        secret = "sk-configuration-boundary-sentinel"
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"ONECODE_HOME": tmp},
            clear=True,
        ), redirect_stdout(stdout):
            set_exit_code = main(
                [
                    "config",
                    "set-model",
                    "--endpoint",
                    "http://127.0.0.1:6780/v1",
                    "--api-key",
                    secret,
                ]
            )
            show_exit_code = main(["config", "show"])

        self.assertEqual((set_exit_code, show_exit_code), (0, 0))
        self.assertNotIn(secret, stdout.getvalue())
        payloads = [json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertNotIn("api_key", payloads[0])
        self.assertNotIn("api_key", payloads[1])

    def test_cli_delegates_without_direct_configuration_branches(self):
        import onecode.cli

        main_source = inspect.getsource(onecode.cli.main)
        parser_source = inspect.getsource(onecode.cli.build_parser)
        for command in CONFIGURATION_COMMANDS:
            self.assertNotIn(f'args.subcommand == "{command}"', main_source)
            self.assertNotIn(f'add_parser("{command}")', parser_source)
        self.assertNotIn("args.config_action", main_source)

    def test_cli_functions_are_materially_shorter_after_configuration_extraction(self):
        import onecode.cli

        main_lines = len(inspect.getsource(onecode.cli.main).splitlines())
        parser_lines = len(inspect.getsource(onecode.cli.build_parser).splitlines())

        self.assertLess(main_lines, 450)
        self.assertGreaterEqual(472 - main_lines, 20)
        self.assertLess(parser_lines, 200)
        self.assertGreaterEqual(214 - parser_lines, 10)


if __name__ == "__main__":
    unittest.main()
