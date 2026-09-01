import argparse
import ast
import io
import inspect
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from onecode.cli import build_parser
from onecode.contracts import load_shell_projection_v4_schema
from onecode.cli_commands.read_only import (
    READ_ONLY_COMMANDS,
    dispatch_read_only_command,
    register_read_only_commands,
)


EXPECTED_PARSER_CONTRACT = {
    "inspect": [
        {
            "option_strings": ["--workspace"],
            "dest": "workspace",
            "required": False,
            "default": ".",
            "choices": None,
            "nargs": None,
            "action_class": "_StoreAction",
        },
        {
            "option_strings": ["--run-id"],
            "dest": "run_id",
            "required": True,
            "default": None,
            "choices": None,
            "nargs": None,
            "action_class": "_StoreAction",
        },
    ],
    "list-runs": [
        {
            "option_strings": ["--workspace"],
            "dest": "workspace",
            "required": False,
            "default": ".",
            "choices": None,
            "nargs": None,
            "action_class": "_StoreAction",
        },
    ],
    "doctor": [],
    "math-audit": [],
    "shell-schema": [],
}


def parser_contract(parser):
    subparsers = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    contract = {}
    for command in EXPECTED_PARSER_CONTRACT:
        command_parser = subparsers.choices[command]
        contract[command] = [
            {
                "option_strings": list(action.option_strings),
                "dest": action.dest,
                "required": action.required,
                "default": action.default,
                "choices": list(action.choices) if action.choices is not None else None,
                "nargs": action.nargs,
                "action_class": type(action).__name__,
            }
            for action in command_parser._actions
            if not isinstance(action, argparse._HelpAction)
        ]
    return contract


class CliReadOnlyCommandTests(unittest.TestCase):
    def test_read_only_command_set_is_explicit(self):
        self.assertEqual(
            READ_ONLY_COMMANDS,
            frozenset({"inspect", "list-runs", "doctor", "math-audit", "shell-schema"}),
        )

    def test_existing_parser_contract_is_frozen(self):
        self.assertEqual(parser_contract(build_parser()), EXPECTED_PARSER_CONTRACT)

    def test_dispatch_returns_none_for_unhandled_command(self):
        args = argparse.Namespace(subcommand="run")

        self.assertIsNone(dispatch_read_only_command(args))

    def test_dispatch_shell_schema_prints_exact_public_contract(self):
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = dispatch_read_only_command(argparse.Namespace(subcommand="shell-schema"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), load_shell_projection_v4_schema())

    def test_read_only_adapter_has_no_execution_or_reverse_dependencies(self):
        source = Path("src/onecode/cli_commands/read_only.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_prefixes = (
            "onecode.cli",
            "onecode.web",
            "onecode.tui",
            "onecode.benchmark",
            "onecode.kernel.runner",
            "onecode.kernel.model_",
            "onecode.kernel.training_data",
            "onecode.kernel.sandbox",
            "onecode.kernel.verifier",
        )
        imported_modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules.append(node.module)

        self.assertFalse(
            [
                module
                for module in imported_modules
                if any(module == prefix or module.startswith(f"{prefix}.") for prefix in forbidden_prefixes)
            ]
        )

    def test_main_delegates_without_direct_read_only_command_branches(self):
        import onecode.cli

        source = inspect.getsource(onecode.cli.main)

        for command in READ_ONLY_COMMANDS:
            self.assertNotIn(f'args.subcommand == "{command}"', source)

    def test_main_is_materially_shorter_after_read_only_extraction(self):
        import onecode.cli

        line_count = len(inspect.getsource(onecode.cli.main).splitlines())

        self.assertLess(line_count, 510)
        self.assertGreaterEqual(581 - line_count, 70)


if __name__ == "__main__":
    unittest.main()
