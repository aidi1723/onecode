#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Merge adjudicated YiZiJue distillation rows and export Qwen messages.")
    parser.add_argument("--balanced", default="data/train_data_balanced.jsonl")
    parser.add_argument("--security", default="data/train_data_security.jsonl")
    parser.add_argument("--merged", default="data/train_data_distilled.jsonl")
    parser.add_argument("--messages", default="data/train_messages_distilled.jsonl")
    return parser


def load_training_data_helpers():
    try:
        from onecode.kernel.training_data import (
            distilled_state_rows_to_qwen_messages,
            validate_yizijue_lm_state_sample,
        )
    except ModuleNotFoundError as exc:
        if exc.name == "onecode":
            raise RuntimeError(
                "onecode package is required. Run from the OneCode repo with PYTHONPATH=src "
                "or install OneCode into this environment."
            ) from exc
        raise
    return distilled_state_rows_to_qwen_messages, validate_yizijue_lm_state_sample


def read_rows(path: Path, *, prefix: str, validate_sample) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = validate_sample(json.loads(line))
        rows.append(validate_sample({**row, "id": f"{prefix}-{row['id']}"}))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def approx_tokens(path: Path) -> int:
    return sum(len(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()) // 4


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        distilled_state_rows_to_qwen_messages, validate_sample = load_training_data_helpers()
    except RuntimeError as exc:
        parser.error(str(exc))
    balanced_rows = read_rows(Path(args.balanced), prefix="balanced", validate_sample=validate_sample)
    security_rows = read_rows(Path(args.security), prefix="security", validate_sample=validate_sample)
    merged_rows = balanced_rows + security_rows
    ids = [row["id"] for row in merged_rows]
    if len(ids) != len(set(ids)):
        raise ValueError("merged training rows contain duplicate ids")
    merged_path = Path(args.merged)
    messages_path = Path(args.messages)
    write_jsonl(merged_path, merged_rows)
    write_jsonl(messages_path, distilled_state_rows_to_qwen_messages(merged_rows))
    result = {
        "status": "completed",
        "balanced_count": len(balanced_rows),
        "security_count": len(security_rows),
        "merged_count": len(merged_rows),
        "merged_path": str(merged_path),
        "messages_path": str(messages_path),
        "approx_merged_tokens": approx_tokens(merged_path),
        "approx_messages_tokens": approx_tokens(messages_path),
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
