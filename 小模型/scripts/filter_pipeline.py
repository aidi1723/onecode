#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

from onecode.kernel.deepseek_distillation import filter_raw_distillation_samples


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Filter DeepSeek teacher rows through OneCode/YiZiJue adjudication.")
    parser.add_argument("--raw", default="data/training/distillation/raw_deepseek_data.jsonl")
    parser.add_argument("--accepted", default="data/training/distillation/accepted.jsonl")
    parser.add_argument("--corrected", default="data/training/distillation/corrected.jsonl")
    parser.add_argument("--rejected", default="data/training/distillation/rejected.jsonl")
    parser.add_argument("--train", default="data/train_data.jsonl")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = filter_raw_distillation_samples(
            Path(args.raw),
            accepted_path=Path(args.accepted),
            corrected_path=Path(args.corrected),
            rejected_path=Path(args.rejected),
            train_path=Path(args.train),
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
