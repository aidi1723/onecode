#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.eval_mlx_predictions import action_from_assistant_content, assistant_content, user_content


WRITE_INTENT_MARKERS = (
    "写入",
    "写至",
    "创建文件",
    "内容更新",
    "内容设置",
    "内容改为",
    "内容为",
)

WORKSPACE_MARKERS = (
    "工作区",
    "workspace",
    "当前工作目录",
    "项目根目录",
    "项目目录",
    "./",
)

RELATIVE_PATH_PATTERN = re.compile(r"(?:^|[\s'\"`：:])(?:[a-zA-Z0-9_-]+/)+[a-zA-Z0-9_.-]+")


def assistant_reason(row: dict[str, Any]) -> str:
    obj = None
    content = assistant_content(row)
    decoder = json.JSONDecoder()
    for idx, char in enumerate(content):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(content[idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            obj = parsed
            break
    if not obj:
        return ""
    action = obj.get("action")
    if isinstance(action, dict):
        reason = action.get("reason")
        return reason if isinstance(reason, str) else ""
    return ""


def looks_like_explicit_workspace_write(row: dict[str, Any]) -> bool:
    text = user_content(row).lower()
    if not any(marker in text for marker in WRITE_INTENT_MARKERS):
        return False
    return any(marker.lower() in text for marker in WORKSPACE_MARKERS) or bool(RELATIVE_PATH_PATTERN.search(text))


def is_schema_denial(row: dict[str, Any]) -> bool:
    return action_from_assistant_content(assistant_content(row)) == "DENY_AND_LEDGER" and assistant_reason(row) == "schema_out_of_contract"


def audit_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    suspicious = [
        {
            "id": str(row.get("id", "")),
            "user": user_content(row),
            "gold_action": action_from_assistant_content(assistant_content(row)),
            "gold_reason": assistant_reason(row),
        }
        for row in rows
        if is_schema_denial(row) and looks_like_explicit_workspace_write(row)
    ]
    return {
        "sample_count": len(rows),
        "suspicious_schema_write_count": len(suspicious),
        "suspicious_schema_write_ids": [row["id"] for row in suspicious],
        "suspicious_schema_writes": suspicious,
    }


def clean_rows(rows: list[dict[str, Any]], report: dict[str, Any]) -> list[dict[str, Any]]:
    suspicious_ids = set(report["suspicious_schema_write_ids"])
    return [row for row in rows if str(row.get("id", "")) not in suspicious_ids]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit YiZiJue training labels for obvious schema/action conflicts.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--clean-output", help="Optional JSONL output with suspicious rows removed.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows = read_jsonl(Path(args.input))
    report = audit_rows(rows)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.clean_output:
        write_jsonl(Path(args.clean_output), clean_rows(rows, report))
    print(json.dumps({key: report[key] for key in ("sample_count", "suspicious_schema_write_count")}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
