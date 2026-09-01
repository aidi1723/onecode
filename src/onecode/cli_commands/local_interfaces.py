from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


LOCAL_INTERFACE_COMMANDS = frozenset({"serve", "shell", "shell-status", "tui"})


def register_local_interface_commands(subparsers: argparse._SubParsersAction) -> None:
    serve_parser = subparsers.add_parser("serve")
    serve_parser.description = "Serve OneCode as an OpenAI-compatible endpoint for LibreChat."
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=19080)
    serve_parser.add_argument("--allow-unauthenticated-local", action="store_true")

    shell_parser = subparsers.add_parser("shell")
    shell_parser.description = "Launch the local OneCode Agent shell with LibreChat."
    shell_parser.add_argument("--onecode-root", default=str(Path.cwd()))
    shell_parser.add_argument("--librechat-dir", default=None)
    shell_parser.add_argument("--workspace", default=None)
    shell_parser.add_argument("--state-dir", default=None)
    shell_parser.add_argument("--model-timeout-seconds", type=float, default=60.0)
    shell_parser.add_argument("--onecode-host", default="127.0.0.1")
    shell_parser.add_argument("--onecode-port", type=int, default=19080)
    shell_parser.add_argument("--librechat-host", default="127.0.0.1")
    shell_parser.add_argument("--librechat-port", type=int, default=14080)
    shell_parser.add_argument("--mongo-port", type=int, default=39017)
    shell_parser.add_argument("--api-token", default="dev-local-token")
    shell_parser.add_argument("--email", default="onecode@local.test")
    shell_parser.add_argument("--password", default="OneCode123!")
    shell_parser.add_argument("--show-credentials", action="store_true")
    shell_parser.add_argument("--no-browser", dest="open_browser", action="store_false")
    shell_parser.set_defaults(open_browser=True)

    shell_status_parser = subparsers.add_parser("shell-status")
    shell_status_parser.description = "Check whether the local OneCode Agent shell services are reachable."
    shell_status_parser.add_argument("--onecode-root", default=str(Path.cwd()))
    shell_status_parser.add_argument("--librechat-dir", default=None)
    shell_status_parser.add_argument("--workspace", default=None)
    shell_status_parser.add_argument("--state-dir", default=None)
    shell_status_parser.add_argument(
        "--model-timeout-seconds", type=float, default=60.0
    )
    shell_status_parser.add_argument("--onecode-host", default="127.0.0.1")
    shell_status_parser.add_argument("--onecode-port", type=int, default=19080)
    shell_status_parser.add_argument("--librechat-host", default="127.0.0.1")
    shell_status_parser.add_argument("--librechat-port", type=int, default=14080)
    shell_status_parser.add_argument("--mongo-port", type=int, default=39017)
    shell_status_parser.add_argument("--api-token", default="dev-local-token")
    shell_status_parser.add_argument("--email", default="onecode@local.test")
    shell_status_parser.add_argument("--password", default="OneCode123!")
    shell_status_parser.set_defaults(open_browser=False, show_credentials=True)

    tui_parser = subparsers.add_parser("tui")
    tui_parser.add_argument("--workspace", default=None)
    tui_parser.add_argument("--model", default=None)
    tui_parser.add_argument(
        "--provider",
        choices=[
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
        default=None,
    )


def dispatch_local_interface_command(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> int | None:
    if args.subcommand == "tui":
        from onecode.tui.app import run_tui

        run_tui(
            workspace=Path(args.workspace) if args.workspace is not None else None,
            model=args.model,
            provider_kind=args.provider,
        )
        return 0

    if args.subcommand == "serve":
        from onecode.web.api import run_server

        if args.allow_unauthenticated_local:
            os.environ["ONECODE_ALLOW_UNAUTHENTICATED"] = "true"
        run_server(host=args.host, port=args.port)
        return 0

    if args.subcommand == "shell":
        from onecode.shell_launcher import config_from_args, launch_shell

        try:
            return launch_shell(config_from_args(args))
        except (FileNotFoundError, RuntimeError) as exc:
            parser.error(str(exc))

    if args.subcommand == "shell-status":
        from onecode.shell_launcher import config_from_args, shell_status

        result = shell_status(config_from_args(args))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] == "ok" else 1

    return None
