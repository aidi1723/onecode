#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

from onecode.kernel.deepseek_distillation import (
    DEFAULT_DEEPSEEK_MODEL,
    build_client_from_env,
    generate_raw_distillation_samples,
)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def nonnegative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate raw DeepSeek teacher rows for YiZiJue distillation.")
    parser.add_argument("--output", default="data/training/distillation/raw_deepseek_data.jsonl")
    parser.add_argument("--count", type=positive_int, default=20)
    parser.add_argument("--model", default=DEFAULT_DEEPSEEK_MODEL)
    parser.add_argument("--profile", choices=["security", "balanced"], default="balanced")
    parser.add_argument("--request-interval-seconds", type=nonnegative_float, default=0.5)
    parser.add_argument("--timeout-seconds", type=nonnegative_float, default=20.0)
    parser.add_argument("--max-tokens", type=positive_int, default=512)
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--errors", default="data/training/distillation/errors.jsonl")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        client = build_client_from_env(timeout_seconds=args.timeout_seconds, max_tokens=args.max_tokens)
        result = generate_raw_distillation_samples(
            Path(args.output),
            client=client,
            count=args.count,
            model=args.model,
            profile=args.profile,
            request_interval_seconds=args.request_interval_seconds,
            continue_on_error=args.continue_on_error,
            error_path=Path(args.errors),
        )
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
