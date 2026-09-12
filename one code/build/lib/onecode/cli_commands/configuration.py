import argparse
import json
from pathlib import Path

from onecode.kernel.model_config import discover_models, read_model_config, write_model_config
from onecode.kernel.verifier import (
    DEFAULT_VERIFIER_POLICY_PATH,
    verifier_policy_presets_summary,
    write_verifier_policy,
)


CONFIGURATION_COMMANDS = frozenset({"list-verifier-presets", "init-verifier-policy", "config"})


def register_configuration_commands(subparsers: argparse._SubParsersAction) -> None:
    subparsers.add_parser("list-verifier-presets")

    init_verifier_policy_parser = subparsers.add_parser("init-verifier-policy")
    init_verifier_policy_parser.add_argument("--workspace", default=".")
    init_verifier_policy_parser.add_argument("--output", default=DEFAULT_VERIFIER_POLICY_PATH)
    init_verifier_policy_parser.add_argument("--preset", action="append", default=None)
    init_verifier_policy_parser.add_argument("--force", action="store_true")

    config_parser = subparsers.add_parser("config")
    config_subparsers = config_parser.add_subparsers(dest="config_action", required=True)
    config_set_model_parser = config_subparsers.add_parser("set-model")
    config_set_model_parser.add_argument("--endpoint", required=True)
    config_set_model_parser.add_argument("--api-key", required=True)
    config_set_model_parser.add_argument("--model", default=None)
    config_set_model_parser.add_argument("--provider", default="openai-compatible")
    config_subparsers.add_parser("show")
    config_discover_parser = config_subparsers.add_parser("discover-models")
    config_discover_parser.add_argument("--endpoint", required=True)
    config_discover_parser.add_argument("--api-key", required=True)


def dispatch_configuration_command(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> int | None:
    if args.subcommand == "list-verifier-presets":
        print(json.dumps(verifier_policy_presets_summary(), ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "init-verifier-policy":
        try:
            result = write_verifier_policy(
                workspace=Path(args.workspace),
                output=args.output,
                preset_ids=args.preset,
                force=args.force,
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "config":
        if args.config_action == "set-model":
            result = write_model_config(
                endpoint=args.endpoint,
                api_key=args.api_key,
                model=args.model,
                provider=args.provider,
            )
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 0
        if args.config_action == "show":
            print(json.dumps(read_model_config(), ensure_ascii=False, sort_keys=True))
            return 0
        if args.config_action == "discover-models":
            print(json.dumps(discover_models(args.endpoint, args.api_key), ensure_ascii=False, sort_keys=True))
            return 0

    return None
