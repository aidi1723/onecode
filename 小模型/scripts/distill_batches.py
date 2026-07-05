#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from onecode.kernel.deepseek_distillation import filter_raw_distillation_samples


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
    parser = argparse.ArgumentParser(description="Run resumable distillation batches and clean after every batch.")
    parser.add_argument("--batches", type=positive_int, default=1)
    parser.add_argument("--batch-size", type=positive_int, default=100)
    parser.add_argument("--profile", choices=["balanced", "security"], default="balanced")
    parser.add_argument("--raw", default="data/training/distillation/raw_deepseek_balanced.jsonl")
    parser.add_argument("--accepted", default="data/training/distillation/accepted_balanced.jsonl")
    parser.add_argument("--corrected", default="data/training/distillation/corrected_balanced.jsonl")
    parser.add_argument("--rejected", default="data/training/distillation/rejected_balanced.jsonl")
    parser.add_argument("--train", default="data/train_data_balanced.jsonl")
    parser.add_argument("--errors", default="data/training/distillation/errors_balanced.jsonl")
    parser.add_argument("--request-interval-seconds", type=nonnegative_float, default=0.05)
    parser.add_argument("--timeout-seconds", type=nonnegative_float, default=60.0)
    parser.add_argument("--max-tokens", type=positive_int, default=1024)
    return parser


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def approx_jsonl_tokens(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(len(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()) // 4


def run_generation(args: argparse.Namespace) -> None:
    command = [
        sys.executable,
        "scripts/distill_generator.py",
        "--count",
        str(args.batch_size),
        "--profile",
        args.profile,
        "--output",
        args.raw,
        "--request-interval-seconds",
        str(args.request_interval_seconds),
        "--timeout-seconds",
        str(args.timeout_seconds),
        "--max-tokens",
        str(args.max_tokens),
        "--continue-on-error",
        "--errors",
        args.errors,
    ]
    subprocess.run(command, check=True)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    raw = Path(args.raw)
    errors = Path(args.errors)
    train = Path(args.train)
    reports = []
    for batch_index in range(1, args.batches + 1):
        before_raw = count_lines(raw)
        before_errors = count_lines(errors)
        run_generation(args)
        clean_result = filter_raw_distillation_samples(
            raw,
            accepted_path=Path(args.accepted),
            corrected_path=Path(args.corrected),
            rejected_path=Path(args.rejected),
            train_path=train,
        )
        report = {
            "batch": batch_index,
            "raw_before": before_raw,
            "raw_after": count_lines(raw),
            "errors_before": before_errors,
            "errors_after": count_lines(errors),
            "train_count": clean_result["train_count"],
            "rejected_count": clean_result["rejected_count"],
            "approx_raw_tokens": approx_jsonl_tokens(raw),
            "approx_train_tokens": approx_jsonl_tokens(train),
        }
        reports.append(report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True), flush=True)
    print(json.dumps({"status": "completed", "batches": reports}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
