from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from .audit import append_audit_record, build_evidence_record


SKIP_DIRS = {
    "__pycache__",
    ".git",
    ".mypy_cache",
    ".oneword",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".venv-gateway",
    "build",
    "dist",
    "node_modules",
    "site-packages",
}
TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".json",
    ".txt",
    ".yaml",
    ".yml",
    ".toml",
    ".csv",
    ".ini",
}
RISK_MARKERS = (
    "while True",
    "rm -rf",
    "subprocess",
    "eval(",
    "exec(",
    "shell=True",
    "requests.get",
    "httpx.",
    "os.system",
)


def inspect_workspace(
    workspace_root: str | Path,
    audit_log_path: str | Path | None = None,
    max_files: int = 200,
    snippet_chars: int = 400,
) -> dict[str, Any]:
    root = Path(workspace_root).resolve()
    files = _list_text_files(root, max_files)
    snippets = _read_snippets(root, files, snippet_chars)
    native_card = build_native_inspect_card(root)
    stdout = "\n".join(files)
    evidence = build_evidence_record(
        command=f"inspect_workspace {root}",
        exit_code=0,
        stdout=stdout,
        stderr="",
    )
    if audit_log_path is not None:
        evidence = append_audit_record(audit_log_path, evidence)
    return {
        "ok": True,
        "root": str(root),
        "file_count": len(files),
        "files": files,
        "snippets": snippets,
        "native_card": native_card,
        "native_card_text": native_card["text"],
        "evidence": evidence,
    }


def build_native_inspect_card(
    workspace_root: str | Path,
    target: str | None = None,
    max_files: int = 30,
    max_symbols: int = 24,
    max_imports: int = 16,
    max_risks: int = 12,
    max_chars: int = 1200,
) -> dict[str, Any]:
    root = Path(workspace_root).resolve()
    files = _target_files(root, target, max_files)
    symbols: list[str] = []
    imports: list[str] = []
    risks: list[str] = []
    for relative in files:
        path = root / relative
        if path.suffix == ".py":
            extracted = _extract_python_map(root, path)
            symbols.extend(extracted["symbols"])
            imports.extend(extracted["imports"])
        risks.extend(_extract_risks(root, path))
    card = {
        "state": "101-INSPECT",
        "target": target or "*",
        "files": files[:max_files],
        "symbols": symbols[:max_symbols],
        "imports": imports[:max_imports],
        "risks": risks[:max_risks],
    }
    text = _format_native_card(card, max_chars=max_chars)
    return {**card, "text": text}


def _list_text_files(root: Path, max_files: int) -> list[str]:
    result: list[str] = []
    for path in sorted(root.rglob("*")):
        if len(result) >= max_files:
            break
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            result.append(path.relative_to(root).as_posix())
    return result


def _target_files(root: Path, target: str | None, max_files: int) -> list[str]:
    if target:
        target_path = _resolve_relative(root, target)
        if target_path.is_file() and target_path.suffix.lower() in TEXT_SUFFIXES:
            return [target_path.relative_to(root).as_posix()]
        if target_path.is_dir():
            return _list_text_files(target_path, max_files)
    return _list_text_files(root, max_files)


def _resolve_relative(root: Path, value: str) -> Path:
    target = (root / value).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes workspace: {value}") from exc
    return target


def _extract_python_map(root: Path, path: Path) -> dict[str, list[str]]:
    relative = path.relative_to(root).as_posix()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return {"symbols": [], "imports": []}
    symbols: list[str] = []
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            kind = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            if isinstance(node, ast.ClassDef):
                kind = "class"
            symbols.append(f"{relative}:{node.lineno}:{kind} {node.name}")
        elif isinstance(node, ast.Import):
            names = ", ".join(alias.name for alias in node.names)
            imports.append(f"{relative}:{node.lineno}:import {names}")
        elif isinstance(node, ast.ImportFrom):
            names = ", ".join(alias.name for alias in node.names)
            module = node.module or ""
            imports.append(f"{relative}:{node.lineno}:from {module} import {names}")
    return {"symbols": sorted(symbols), "imports": sorted(imports)}


def _extract_risks(root: Path, path: Path) -> list[str]:
    relative = path.relative_to(root).as_posix()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return []
    risks: list[str] = []
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if any(marker in stripped for marker in RISK_MARKERS):
            risks.append(f"{relative}:{line_number}:{_compact_risk_line(stripped)}")
    return risks


def _format_native_card(card: dict[str, Any], max_chars: int) -> str:
    item_budget = max(80, max_chars // 5)
    sections = [
        f"[State]: {card['state']} | [Target]: {card['target']}",
        "[Files]: " + _join_with_budget(card["files"], item_budget, ", "),
        "[Symbols]: " + _join_with_budget(card["symbols"], item_budget, " | "),
        "[Imports]: " + _join_with_budget(card["imports"], item_budget, " | "),
        "[Risks]: " + (_join_with_budget(card["risks"], item_budget, " | ") if card["risks"] else "none"),
    ]
    text = "\n".join(section for section in sections if not section.endswith(": "))
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 18)].rstrip() + "\n[Truncated]: true"


def _compact_risk_line(line: str) -> str:
    return line.rstrip(":")[:120]


def _join_with_budget(items: list[str], max_chars: int, separator: str) -> str:
    output = ""
    for index, item in enumerate(items):
        candidate = item if not output else output + separator + item
        if len(candidate) > max_chars:
            remaining = len(items) - index
            suffix = f"{separator}+{remaining} more"
            return (output + suffix) if output else item[: max(0, max_chars - len(suffix))] + suffix
        output = candidate
    return output


def _read_snippets(root: Path, files: list[str], snippet_chars: int) -> dict[str, str]:
    snippets: dict[str, str] = {}
    for relative in files[:20]:
        path = root / relative
        try:
            snippets[relative] = path.read_text(encoding="utf-8")[:snippet_chars]
        except UnicodeDecodeError:
            continue
    return snippets
