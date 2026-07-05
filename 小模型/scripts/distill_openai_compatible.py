#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


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
    parser = argparse.ArgumentParser(description="Generate teacher rows from any OpenAI-compatible chat endpoint.")
    parser.add_argument("--provider", default=os.environ.get("TEACHER_PROVIDER", "openai-compatible"))
    parser.add_argument("--output", default="data/training/distillation/raw_teacher_data.jsonl")
    parser.add_argument("--count", type=positive_int, default=20)
    parser.add_argument("--model", default=os.environ.get("TEACHER_MODEL", "deepseek-v4-flash"))
    parser.add_argument("--profile", choices=["security", "balanced"], default="balanced")
    parser.add_argument("--base-url", default=os.environ.get("TEACHER_BASE_URL"))
    parser.add_argument("--chat-path", default=os.environ.get("TEACHER_CHAT_COMPLETIONS_PATH", "/v1/chat/completions"))
    parser.add_argument("--api-key-env", default="TEACHER_API_KEY")
    parser.add_argument("--request-interval-seconds", type=nonnegative_float, default=0.5)
    parser.add_argument("--timeout-seconds", type=nonnegative_float, default=60.0)
    parser.add_argument("--max-tokens", type=positive_int, default=1024)
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--errors", default="data/training/distillation/errors_teacher.jsonl")
    return parser


def load_distillation_helpers():
    try:
        from onecode.kernel.deepseek_distillation import (
            DeepSeekChatClient,
            generate_raw_distillation_samples,
        )
    except ModuleNotFoundError as exc:
        if exc.name == "onecode":
            raise RuntimeError(
                "onecode package is required. Run from the OneCode repo with PYTHONPATH=src "
                "or install OneCode into this environment."
            ) from exc
        raise
    return DeepSeekChatClient, generate_raw_distillation_samples


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        DeepSeekChatClient, generate_raw_distillation_samples = load_distillation_helpers()
        api_key = os.environ.get(args.api_key_env, "")
        if not api_key:
            raise ValueError(f"{args.api_key_env} must be set")
        if not args.base_url:
            raise ValueError("base URL must be provided through --base-url or TEACHER_BASE_URL")
        client = DeepSeekChatClient(
            api_key=api_key,
            base_url=args.base_url,
            model=args.model,
            timeout_seconds=args.timeout_seconds,
            max_tokens=args.max_tokens,
            chat_completions_path=args.chat_path,
        )
        result = generate_raw_distillation_samples(
            Path(args.output),
            client=client,
            count=args.count,
            model=f"{args.provider}:{args.model}",
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
