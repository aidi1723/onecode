#!/usr/bin/env python3
import argparse
import contextlib
import io
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_hardened_mlx_dataset import STRICT_SYSTEM_PROMPT


DEFAULT_SYSTEM = "You are YiZiJue-LM. Translate natural language into simple replies or strict OneCode/YiZiJue JSON. Output JSON only when an action is needed."


def greedy_sampler(logprobs, mx_module=None):
    if mx_module is None:
        import mlx.core as mx

        mx_module = mx
    return mx_module.argmax(logprobs, axis=-1)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}: line {line_number} is invalid JSON: {exc.msg}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}: line {line_number} must be a JSON object")
        raw_sample_id = row.get("id", "")
        if not isinstance(raw_sample_id, str):
            raise ValueError("input id must be a string")
        if not raw_sample_id:
            raise ValueError("input id is required")
        if raw_sample_id in seen_ids:
            raise ValueError(f"duplicate input id: {raw_sample_id}")
        messages = row.get("messages", [])
        if not isinstance(messages, list) or any(not isinstance(message, dict) for message in messages):
            raise ValueError(f"messages must be a list of objects for id: {raw_sample_id}")
        if not any(message.get("role") == "user" for message in messages):
            raise ValueError(f"input user message is required for id: {raw_sample_id}")
        seen_ids.add(raw_sample_id)
        rows.append(row)
    if not rows:
        raise ValueError("input rows are required")
    return rows


def user_content(row: dict[str, Any]) -> str:
    for message in row.get("messages", []):
        if message.get("role") == "user":
            return str(message.get("content", ""))
    return ""


def prompt_for_row(row: dict[str, Any], *, strict_system_prompt: bool = False) -> str:
    messages = row.get("messages", [])
    system = (
        STRICT_SYSTEM_PROMPT
        if strict_system_prompt
        else next((str(m.get("content", "")) for m in messages if m.get("role") == "system"), DEFAULT_SYSTEM)
    )
    return f"{system}\n\nUser: {user_content(row)}\nAssistant:"


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate MLX YiZiJue-LM predictions for messages JSONL rows.")
    parser.add_argument("--model", default="Qwen/Qwen3-0.6b")
    parser.add_argument("--adapter-path", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=positive_int, default=40)
    parser.add_argument("--max-tokens", type=positive_int, default=220)
    parser.add_argument("--strict-system-prompt", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        rows = read_jsonl(Path(args.input))[: args.limit]
    except ValueError as exc:
        build_parser().error(str(exc))
    from mlx_lm import generate, load

    model, tokenizer = load(args.model, adapter_path=args.adapter_path)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for idx, row in enumerate(rows, start=1):
            with contextlib.redirect_stdout(io.StringIO()):
                prediction = generate(
                    model,
                    tokenizer,
                    prompt=prompt_for_row(row, strict_system_prompt=args.strict_system_prompt),
                    max_tokens=args.max_tokens,
                    sampler=greedy_sampler,
                    verbose=False,
                )
            handle.write(
                json.dumps(
                    {
                        "id": row.get("id"),
                        "prediction": prediction,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )
            print(json.dumps({"generated": idx, "id": row.get("id")}, ensure_ascii=False, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
