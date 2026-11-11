"""Workspace file discovery that reports agent-cycle outcomes."""

from __future__ import annotations

import ast
import fnmatch
from pathlib import Path
from typing import Any

from onecode.kernel.path_guard import PathGuard


def glob_workspace(workspace: Path, pattern: str, *, start: Path, max_matches: int) -> dict[str, Any]:
    root = workspace.resolve()
    paths: list[str] = []
    scanned = 0
    truncated = False
    for candidate in start.rglob("*"):
        scanned += 1
        if scanned > 5_000:
            truncated = True
            break
        if candidate.is_symlink():
            continue
        try:
            relative = candidate.relative_to(root)
        except ValueError:
            continue
        if PathGuard.is_sensitive_read_path(relative):
            continue
        if not fnmatch.fnmatch(relative.as_posix(), pattern):
            continue
        if len(paths) >= max_matches:
            truncated = True
            break
        paths.append(relative.as_posix())
    result: dict[str, Any] = {"pattern": pattern, "paths": paths, "truncated": truncated}
    if not paths and not truncated:
        result["status"] = "completed"
        result["reason"] = "search_miss"
    return result


def outline_python(workspace: Path, relative_path: str) -> dict[str, Any]:
    target = PathGuard.resolve_read_target(workspace, relative_path)
    if not target.is_file():
        return {"path": relative_path, "symbols": [], "status": "completed", "reason": "search_miss"}
    try:
        tree = ast.parse(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return {"path": relative_path, "symbols": [], "status": "halted", "reason": "action_exception"}
    symbols = [
        {
            "kind": "class" if isinstance(node, ast.ClassDef) else "function",
            "name": node.name,
            "line": node.lineno,
        }
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    symbols.sort(key=lambda item: (item["line"], item["name"]))
    result: dict[str, Any] = {"path": relative_path, "symbols": symbols, "status": "completed"}
    if not symbols:
        result["reason"] = "search_miss"
    return result
