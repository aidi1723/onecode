#!/usr/bin/env python3
from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path


MAX_FUNCTION_LINES = 160
MAX_CLASS_LINES = 500

ALLOWED_LONG_FUNCTIONS = {
    "src/onecode/cli.py:build_parser",
    "src/onecode/cli.py:main",
    "src/onecode/kernel/runner.py:_run_task_with_context",
    "src/onecode/kernel/training_data.py:expanded_training_samples",
    "src/onecode/web/api.py:gateway_console_html",
}

ALLOWED_LONG_CLASSES = {
    "src/onecode/kernel/hexagram.py:IchingKernel",
}


@dataclass(frozen=True)
class Finding:
    kind: str
    key: str
    line_count: int
    limit: int

    def render(self) -> str:
        return f"{self.kind} too long: {self.key} has {self.line_count} lines, limit {self.limit}"


def source_files(root: Path) -> list[Path]:
    if root.is_file() and root.suffix == ".py":
        return [root]
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def node_line_count(node: ast.AST) -> int:
    end_lineno = getattr(node, "end_lineno", None)
    lineno = getattr(node, "lineno", None)
    if not isinstance(lineno, int) or not isinstance(end_lineno, int):
        return 0
    return end_lineno - lineno + 1


def display_key(path: Path, node_name: str) -> str:
    return f"{path.as_posix()}:{node_name}"


def findings_for_file(path: Path) -> list[Finding]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            line_count = node_line_count(node)
            key = display_key(path, node.name)
            if line_count > MAX_FUNCTION_LINES and key not in ALLOWED_LONG_FUNCTIONS:
                findings.append(Finding("function", key, line_count, MAX_FUNCTION_LINES))
        elif isinstance(node, ast.ClassDef):
            line_count = node_line_count(node)
            key = display_key(path, node.name)
            if line_count > MAX_CLASS_LINES and key not in ALLOWED_LONG_CLASSES:
                findings.append(Finding("class", key, line_count, MAX_CLASS_LINES))
    return findings


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    roots = [Path(arg) for arg in args] if args else [Path("src")]
    findings: list[Finding] = []
    for root in roots:
        for path in source_files(root):
            findings.extend(findings_for_file(path))
    if findings:
        for finding in findings:
            print(finding.render(), file=sys.stderr)
        return 1
    print("source quality ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
