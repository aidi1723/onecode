from __future__ import annotations

import ast
import re
from pathlib import Path


DEFAULT_REPAIR_FILES = (
    "core/crypto.py",
    "api/server.py",
    "tests/test_mesh.py",
)


def summarize_pytest_output(output: str, max_chars: int = 800) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    failure_lines: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if not line.startswith("FAILED "):
            continue
        normalized = re.sub(r"\s+", " ", line)
        if normalized in seen:
            continue
        seen.add(normalized)
        failure_lines.append(normalized)

    summary_lines = failure_lines[:8]
    for line_ref in _traceback_line_refs(lines):
        if line_ref not in summary_lines:
            summary_lines.append(line_ref)
    final_summary = _last_pytest_count_line(lines)
    if final_summary and final_summary not in summary_lines:
        summary_lines.append(final_summary)
    if not summary_lines:
        summary_lines = _last_interesting_lines(lines)
    return _clip("\n".join(summary_lines), max_chars)


def build_repair_card(
    workspace_root: str | Path,
    pytest_output: str,
    max_chars: int = 1200,
) -> str:
    root = Path(workspace_root).resolve()
    failure_summary = summarize_pytest_output(pytest_output, max_chars=max(200, max_chars // 2))
    signatures = _interface_signatures(root)
    sections = [
        "Build Mode Repair Card",
        "Failure Summary:",
        failure_summary or "(no compact pytest failure lines captured)",
        "Interface Signatures:",
        "\n".join(signatures) if signatures else "(no Python interface signatures captured)",
        (
            "Repair Rule: align tests and implementation to these signatures; "
            "do not rewrite unrelated files; run pytest after the fix."
        ),
    ]
    return _clip("\n".join(sections), max_chars)


def _interface_signatures(root: Path) -> list[str]:
    signatures: list[str] = []
    for relative in DEFAULT_REPAIR_FILES:
        path = root / relative
        if not path.is_file():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (OSError, SyntaxError, UnicodeDecodeError) as exc:
            signatures.append(f"{relative}: parse_error={type(exc).__name__}")
            continue
        signatures.extend(_signatures_for_tree(relative, tree))
    return signatures[:40]


def _signatures_for_tree(relative: str, tree: ast.AST) -> list[str]:
    signatures: list[str] = []
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.ClassDef):
            signatures.append(f"{relative}:{node.lineno} class {node.name}")
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    signatures.append(
                        f"{relative}:{child.lineno} {node.name}.{child.name}{_args_signature(child.args)}"
                    )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            signatures.append(f"{relative}:{node.lineno} {prefix} {node.name}{_args_signature(node.args)}")
    return signatures


def _args_signature(args: ast.arguments) -> str:
    parts: list[str] = []
    positional = [*args.posonlyargs, *args.args]
    defaults_offset = len(positional) - len(args.defaults)
    for index, arg in enumerate(positional):
        value = arg.arg
        if index >= defaults_offset:
            value += "="
        parts.append(value)
    if args.vararg:
        parts.append(f"*{args.vararg.arg}")
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        value = arg.arg
        if default is not None:
            value += "="
        parts.append(value)
    if args.kwarg:
        parts.append(f"**{args.kwarg.arg}")
    return "(" + ", ".join(parts) + ")"


def _last_pytest_count_line(lines: list[str]) -> str:
    pattern = re.compile(r"(\d+\s+(failed|passed|error|errors|skipped|xfailed|xpassed))", re.I)
    for line in reversed(lines):
        if pattern.search(line) and " in " in line:
            return line
    return ""


def _traceback_line_refs(lines: list[str]) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    pattern = re.compile(r'File "([^"]+)", line (\d+)(?:, in ([\w_]+))?')
    for line in lines:
        match = pattern.search(line)
        if not match:
            continue
        filename = Path(match.group(1)).name
        func = match.group(3) or ""
        ref = f"{filename}:{match.group(2)}" + (f" in {func}" if func else "")
        if ref in seen:
            continue
        seen.add(ref)
        refs.append(ref)
    return refs[:6]


def _last_interesting_lines(lines: list[str]) -> list[str]:
    interesting = [
        line
        for line in lines
        if "Error" in line or "Exception" in line or "failed" in line.lower() or "Traceback" in line
    ]
    return interesting[-8:]


def _clip(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    if max_chars <= 12:
        return text[:max_chars]
    return text[: max_chars - 12].rstrip() + "\n...[clipped]"
