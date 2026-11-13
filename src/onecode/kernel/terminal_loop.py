"""Open-ended multi-step terminal loop for SWE-bench exploration and interactive problem solving.

This module implements a stateful terminal agent session:
1. Multi-turn interactive execution: the model observes shell output, reads files,
   applies surgical patches, runs exploration commands, and re-tests.
2. Anti-tamper protection: strict isolation of immutable preset test paths.
3. Stagnation and loop governance: detects repeated identical failures (Lyapunov Stagnation Guard)
   and forces strategy pivoting.
4. Fault localization coupling: integrates SymbolLocator to direct exploration
   directly to true implementation modules.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import posixpath
import re
import shlex
import shutil
import subprocess
import time
from typing import Any, Callable

from onecode.kernel.execution_scope import (
    ExecutionScope,
    ToolCapabilityPolicy,
)
from onecode.kernel.execution_tools import ToolRegistry, default_tool_registry
from onecode.kernel.path_guard import PathGuard, PathGuardError
from onecode.kernel.symbol_locator import SymbolLocator, WorkspaceSymbolIndex, is_any_test_path
from onecode.kernel.workspace_snapshot import WorkspaceSnapshot

_TEST_PATH_PAT = r"(?:tests?/|test/|__tests__/|spec/|[^\s]*_test\.[a-z0-9]+|[^\s]*\.(?:test|spec)\.[a-z0-9]+|[^\s]*tests\.rs\b|[^\s]*test_\w+\.(?:py|pyw|rb)\b)"

_FORBIDDEN_TEST_CMD_PATTERNS = (
    re.compile(rf"\b(?:rm|unlink|truncate|shred)\s+.*{_TEST_PATH_PAT}", re.IGNORECASE),
    re.compile(rf"\bsed\s+.*(?:-i|--in-place).*{_TEST_PATH_PAT}", re.IGNORECASE),
    re.compile(rf"\bsed\s+.*{_TEST_PATH_PAT}.*(?:-i|--in-place)", re.IGNORECASE),
    re.compile(rf">\s*{_TEST_PATH_PAT}", re.IGNORECASE),
    re.compile(rf">>\s*{_TEST_PATH_PAT}", re.IGNORECASE),
    re.compile(rf"\btee\s+.*{_TEST_PATH_PAT}", re.IGNORECASE),
    re.compile(rf"\b(?:cp|mv)\s+.*{_TEST_PATH_PAT}\s*$", re.IGNORECASE),
)

_DESTRUCTIVE_CMDS = frozenset({"rm", "unlink", "truncate", "shred", "tee"})
_PATH_FRAGMENT = re.compile(r"[A-Za-z0-9_.@+-]+(?:[/\\][A-Za-z0-9_.@+-]+)+|[A-Za-z0-9_.@+-]+\.(?:py|pyw|rb|go|js|ts|rs)")
_TEST_DIR_NAMES = frozenset({"tests", "test", "spec", "__tests__"})
_CONCAT_GAP = re.compile(r"\s*(?:\+|~|\.)\s*")
_PATH_CALL = re.compile(r"(?:open|Path|join|joinpath|writeFileSync|writeFile)\s*\(\s*$")
_MUTATING_CALL = re.compile(
    r"write_text|write_bytes|writelines|writeFileSync|writeFile|\.write\s*\(|"
    r"\bunlink\b|\brmtree\b|\bmkdir\b|\bmakedirs\b|\brename\s*\(|\btruncate\b|\bremove\s*\("
)
_OPEN_CALL = re.compile(r"\bopen\s*\(")
_OPEN_MODE = re.compile(r"['\"]([rwaxtb+U]+)['\"]")
_VARIABLE_SPLICE = re.compile(r"\s*(?:\+|~|\.)\s*[A-Za-z_$]")
_OBFUSCATED_TEST_PREFIX = re.compile(r"(?:^|[/\\])(?:ests|sts|pec|tests__)(?:[/\\]|$)")
_WRITE_CALL = re.compile(r"(?:open|writeFileSync|writeFile|Path)\s*\(")


def _string_literals(script: str) -> list[tuple[int, int, str]]:
    """Return each quoted literal as (start, end, decoded text)."""
    found: list[tuple[int, int, str]] = []
    index = 0
    length = len(script)
    while index < length:
        if script.startswith(("'''", '"""'), index):
            quote = script[index:index + 3]
            end = script.find(quote, index + 3)
            if end < 0:
                break
            found.append((index, end + 3, script[index + 3:end]))
            index = end + 3
            continue
        if script[index] not in {"'", '"'}:
            index += 1
            continue
        quote = script[index]
        cursor = index + 1
        chars: list[str] = []
        while cursor < length:
            if script[cursor] == "\\" and cursor + 1 < length:
                chars.append(script[cursor + 1])
                cursor += 2
                continue
            if script[cursor] == quote:
                break
            chars.append(script[cursor])
            cursor += 1
        if cursor >= length or script[cursor] != quote:
            break
        found.append((index, cursor + 1, "".join(chars)))
        index = cursor + 1
    return found


def _script_mutates_files(script: str) -> bool:
    if _MUTATING_CALL.search(script):
        return True
    for match in _OPEN_CALL.finditer(script):
        window = script[match.end():match.end() + 160]
        if any(any(char in mode for char in "wax+") for mode in _OPEN_MODE.findall(window)):
            return True
    return False


def _test_root_prefix(text: str) -> bool:
    cleaned = text.strip().strip("/\\")
    if not cleaned:
        return False
    return re.split(r"[/\\]", cleaned, maxsplit=1)[0] in _TEST_DIR_NAMES


def _literal_used_as_path(script: str, start: int, end: int, text: str) -> bool:
    if not (is_any_test_path(text) or _test_root_prefix(text)):
        return False
    before = script[max(0, start - 48):start]
    after = script[end:end + 24]
    if _PATH_CALL.search(before):
        return True
    if re.match(r"\s*(?:\+|~|/)", after):
        return True
    return re.search(r"(?:\+|~|/)\s*$", before) is not None


def _joined_literals(script: str, literals: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    joined: list[tuple[int, int, str]] = []
    index = 0
    while index < len(literals):
        start, end, text = literals[index]
        nxt = index
        while nxt + 1 < len(literals):
            gap = script[end:literals[nxt + 1][0]]
            if _CONCAT_GAP.fullmatch(gap) is None:
                break
            text += literals[nxt + 1][2]
            end = literals[nxt + 1][1]
            nxt += 1
        joined.append((start, end, text))
        index = nxt + 1
    return joined


def _call_arguments(script: str, open_paren: int) -> tuple[list[str], int] | None:
    """Return call arguments and the index just after the closing parenthesis."""
    depth = 1
    bracket = 0
    brace = 0
    start = open_paren + 1
    index = start
    quote = ""
    arguments: list[str] = []
    while index < len(script):
        char = script[index]
        if quote:
            if char == "\\" and index + 1 < len(script):
                index += 2
                continue
            if char == quote:
                quote = ""
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            index += 1
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                arguments.append(script[start:index])
                return arguments, index + 1
        elif char == "[":
            bracket += 1
        elif char == "]":
            bracket = max(0, bracket - 1)
        elif char == "{":
            brace += 1
        elif char == "}":
            brace = max(0, brace - 1)
        elif char == "," and depth == 1 and bracket == 0 and brace == 0:
            arguments.append(script[start:index])
            start = index + 1
        index += 1
    return None


def _first_call_argument(script: str, open_paren: int) -> str | None:
    """Return the text of the first argument, without crossing nested calls."""
    parsed = _call_arguments(script, open_paren)
    if not parsed or not parsed[0]:
        return None
    return parsed[0][0]


def _collect_target_ids(target: ast.AST, out: set[str]) -> None:
    if isinstance(target, ast.Name):
        out.add(target.id)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            _collect_target_ids(elt, out)


def _resolved_constant_str_bindings(script: str) -> dict[str, list[str]]:
    """Return unambiguous top-level constant string assignments mapped by variable name."""
    try:
        tree = ast.parse(script)
    except SyntaxError:
        return {}
    candidates: dict[str, list[str]] = {}
    safe_nodes: set[int] = set()
    unsafe_names: set[str] = set()
    for stmt in tree.body:
        if (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
        ):
            name = stmt.targets[0].id
            candidates.setdefault(name, []).append(stmt.value.value)
            safe_nodes.add(id(stmt))
    for node in ast.walk(tree):
        if id(node) in safe_nodes:
            continue
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                _collect_target_ids(tgt, unsafe_names)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            _collect_target_ids(node.target, unsafe_names)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            _collect_target_ids(node.target, unsafe_names)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars is not None:
                    _collect_target_ids(item.optional_vars, unsafe_names)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            unsafe_names.add(node.name)
        elif isinstance(node, ast.NamedExpr):
            unsafe_names.add(node.target.id)
        elif isinstance(node, ast.Delete):
            for tgt in node.targets:
                _collect_target_ids(tgt, unsafe_names)
        elif isinstance(node, ast.comprehension):
            _collect_target_ids(node.target, unsafe_names)
        elif isinstance(node, ast.arg):
            unsafe_names.add(node.arg)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            unsafe_names.update(node.names)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                unsafe_names.add(alias.asname or alias.name.split(".", 1)[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            unsafe_names.add(node.name)
    return {k: v for k, v in candidates.items() if k not in unsafe_names}


def _unproven_write_target(script: str) -> str:
    """Block a mutating interpreter script whose destination is not a static literal path."""
    if not script or not _script_mutates_files(script):
        return ""
    const_bindings: dict[str, list[str]] | None = None
    for match in _WRITE_CALL.finditer(script):
        argument = _first_call_argument(script, match.end() - 1)
        if argument is None:
            continue
        stripped = argument.strip()
        if stripped.startswith(("'''", '"""', "'", '"')):
            continue
        if stripped.isidentifier():
            if const_bindings is None:
                const_bindings = _resolved_constant_str_bindings(script)
            bound_vals = const_bindings.get(stripped)
            if bound_vals:
                unsafe_target = ""
                for val in bound_vals:
                    if is_any_test_path(val) or _test_root_prefix(val) or _OBFUSCATED_TEST_PREFIX.search(val):
                        return val
                    if _path_escapes_workspace(val):
                        unsafe_target = "a computed path"
                        break
                if not unsafe_target:
                    continue
        return "a computed path"
    return ""


def _spliced_test_target(script: str, depth: int = 0) -> str:
    """Return a test path assembled inside an interpreter script, or an empty string."""
    if not script or not _script_mutates_files(script):
        return ""
    if depth == 0:
        computed = _unproven_write_target(script)
        if computed:
            return computed
    literals = _string_literals(script)
    if "chr(" in script:
        for _start, _end, text in literals:
            if _OBFUSCATED_TEST_PREFIX.search(text):
                return text
    for start, end, text in _joined_literals(script, literals):
        if _literal_used_as_path(script, start, end, text):
            return text
        if _VARIABLE_SPLICE.match(script[end:]) and _test_root_prefix(text):
            return text
    return ""


def _module_names(source: str) -> list[str]:
    """Return imported module names, ignoring names pulled in by ``from module import name``."""
    names: list[str] = []
    without_from = re.sub(r"(?<![\w.])from\s+[A-Za-z_][\w.]*\s+import\b[^\n;]*", " ", source)
    for match in re.finditer(
        r"(?<![\w.])import\s+([A-Za-z_][\w.]*(?:\s*,\s*[A-Za-z_][\w.]*)*)",
        without_from,
    ):
        names.extend(part.strip() for part in match.group(1).split(",") if part.strip())
    names.extend(re.findall(r"(?<![\w.])from\s+([A-Za-z_][\w.]*)\s+import\b", source))
    names.extend(re.findall(r"""(?:__import__|import_module)\(\s*['"]([A-Za-z_][\w.]*)['"]""", source))
    return names


def _local_module_file(workspace: Path, module: str) -> Path | None:
    parts = module.split(".")
    if any(part in {"", ".", ".."} for part in parts):
        return None
    root = workspace.resolve()
    candidates = (root.joinpath(*parts).with_suffix(".py"), root.joinpath(*parts, "__init__.py"))
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.is_file() and resolved.is_relative_to(root):
            return resolved
    return None


def _source_write_target(
    workspace: Path,
    source: str,
    seen: set[Path],
    depth: int = 0,
    is_test_context: bool = True,
) -> str:
    """Return a test write hidden in this source or in a workspace module it imports."""
    if depth > 6:
        return "a computed execution" if (is_test_context and depth == 0) else ""
    found = _spliced_test_target(source, depth)
    if found:
        return found
    executed = _dynamic_execution_target(workspace, source, seen, depth, is_test_context=is_test_context)
    if executed:
        return executed
    if is_test_context and depth == 0:
        dynamic = _unproven_dynamic_import(source)
        if dynamic:
            return dynamic
    for module in _module_names(source):
        path = _local_module_file(workspace, module)
        if path is None or path in seen:
            continue
        seen.add(path)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return path.name
        rel_path = str(path.relative_to(workspace)) if path.is_relative_to(workspace) else str(path)
        in_test = is_any_test_path(rel_path)
        nested = _source_write_target(workspace, text, seen, depth + 1, is_test_context=in_test)
        if nested:
            return nested
    return ""


def _python_module_flag(cmd_tokens: tuple[str, ...]) -> str:
    for index, token in enumerate(cmd_tokens):
        if token == "-m" and index + 1 < len(cmd_tokens):
            return cmd_tokens[index + 1]
    return ""


def _unproven_dynamic_import(script: str) -> str:
    """Block an interpreter script that imports a module through a non-literal expression."""
    for match in re.finditer(r"(?:__import__|import_module)\s*\(", script):
        argument = _first_call_argument(script, match.end() - 1)
        if argument is None or not argument.strip().startswith(("'''", '"""', "'", '"')):
            return "a computed import"
    return ""


def _module_flag_write_target(workspace: Path, module: str) -> str:
    path = _local_module_file(workspace, module)
    if path is None:
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return module
    rel_path = str(path.relative_to(workspace)) if path.is_relative_to(workspace) else str(path)
    return _source_write_target(workspace, text, {path}, depth=1, is_test_context=is_any_test_path(rel_path))


_EXECUTION_CALLS = (
    ("exec", 0),
    ("run_module", 0),
    ("run_path", 0),
    ("spec_from_file_location", 1),
    ("SourceFileLoader", 1),
)
_FILE_EXECUTION_CALLS = frozenset({"run_path", "spec_from_file_location", "SourceFileLoader"})


def _sole_string_literal(argument: str) -> str | None:
    stripped = argument.strip()
    literals = _string_literals(stripped)
    if len(literals) != 1:
        return None
    start, end, text = literals[0]
    if stripped[start:end] != stripped:
        return None
    return text


def _path_escapes_workspace(relative: str) -> bool:
    if not relative or relative.startswith(("/", "\\")):
        return True
    return ".." in Path(relative).parts


def _workspace_source_file(workspace: Path, relative: str) -> Path | None:
    if _path_escapes_workspace(relative):
        return None
    root = workspace.resolve()
    try:
        candidate = (root / relative).resolve()
    except OSError:
        return None
    if candidate.is_file() and candidate.is_relative_to(root):
        return candidate
    return None


def _file_write_target(workspace: Path, relative: str, seen: set[Path] | None = None, depth: int = 0) -> str:
    if _path_escapes_workspace(relative):
        return relative
    path = _workspace_source_file(workspace, relative)
    if path is None:
        return ""
    seen = set() if seen is None else seen
    if path in seen:
        return ""
    seen.add(path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return relative
    return _source_write_target(workspace, text, seen, depth=depth + 1, is_test_context=is_any_test_path(relative))


def _execution_argument_target(
    workspace: Path,
    call: str,
    argument: str,
    seen: set[Path] | None = None,
    depth: int = 0,
    is_test_context: bool = True,
) -> str:
    literal = _sole_string_literal(argument)
    if literal is not None:
        if call == "run_module":
            return _module_flag_write_target(workspace, literal)
        if call in _FILE_EXECUTION_CALLS:
            return _file_write_target(workspace, literal, seen, depth)
        return _source_write_target(workspace, literal, set() if seen is None else seen, depth, is_test_context=is_test_context)
    paths = [text for _start, _end, text in _string_literals(argument) if text.endswith(".py")]
    if not paths:
        return "a computed execution" if is_test_context else ""
    for relative in paths:
        found = _file_write_target(workspace, relative, seen, depth)
        if found:
            return found
    return ""


def _static_literal_text(argument: str) -> str | None:
    """Return one literal, including adjacent pieces joined by ``+``."""
    stripped = argument.strip()
    literals = _string_literals(stripped)
    if not literals:
        return None
    joined = _joined_literals(stripped, literals)
    if len(joined) != 1:
        return None
    start, end, text = joined[0]
    if stripped[start:end] != stripped:
        return None
    return text


def _getattr_execution_target(
    workspace: Path,
    script: str,
    seen: set[Path] | None = None,
    depth: int = 0,
    is_test_context: bool = True,
) -> str:
    """Block a loader reached through getattr, including a name joined from pieces."""
    for match in re.finditer(r"(?<![\w])getattr\s*\(", script):
        parsed = _call_arguments(script, match.end() - 1)
        if parsed is None or len(parsed[0]) < 2:
            if is_test_context:
                return "a computed execution"
            continue
        arguments, end = parsed
        name = _static_literal_text(arguments[1])
        rest = script[end:].lstrip()
        if name is None:
            if is_test_context and rest.startswith("("):
                return "a computed execution"
            continue
        arg_index = dict(_EXECUTION_CALLS).get(name)
        if arg_index is None or not rest.startswith("("):
            continue
        open_paren = end + (len(script[end:]) - len(rest))
        invoked = _call_arguments(script, open_paren)
        if invoked is None or arg_index >= len(invoked[0]):
            if is_test_context:
                return "a computed execution"
            continue
        found = _execution_argument_target(workspace, name, invoked[0][arg_index], seen, depth, is_test_context=is_test_context)
        if found:
            return found
    return ""


_PROCESS_CALL = re.compile(
    r"(?<![\w])(?:subprocess\.(?:run|call|check_call|check_output|Popen)|os\.(?:system|popen)|os\.execv(?:p|pe)?)\s*\("
)


def _command_tokens(argument: str) -> list[str] | None:
    """Return argv when it is a literal string or a list of literal strings."""
    stripped = argument.strip()
    literal = _sole_string_literal(stripped)
    if literal is not None:
        try:
            return shlex.split(literal)
        except ValueError:
            return None
    if not (stripped.startswith("[") and stripped.endswith("]")):
        return None
    parsed = _call_arguments("(" + stripped[1:-1] + ")", 0)
    if parsed is None:
        return None
    tokens: list[str] = []
    for part in parsed[0]:
        if not part.strip():
            continue
        text = _static_literal_text(part)
        if text is None:
            return None
        tokens.append(text)
    return tokens


_SHELLS = frozenset({"bash", "sh", "zsh", "dash", "ash"})
_SHELL_SCAN_BYTES = 65_536


def _is_shell_command(argv: tuple[str, ...]) -> bool:
    return bool(argv) and posixpath.basename(argv[0]).lower() in _SHELLS


def _is_shell_c_flag(token: str) -> bool:
    return token.startswith("-") and not token.startswith("--") and "c" in token


def _shell_command_text(argv: tuple[str, ...]) -> str:
    if not _is_shell_command(argv):
        return ""
    for index, token in enumerate(argv):
        if _is_shell_c_flag(token) and index + 1 < len(argv):
            return argv[index + 1]
    return ""


def _shell_script_argument(argv: tuple[str, ...]) -> str:
    """Return the script path for ``bash helper.sh``, ignoring ``bash -c``."""
    if not _is_shell_command(argv) or any(_is_shell_c_flag(token) for token in argv):
        return ""
    for token in argv[1:]:
        if token == "--" or token.startswith("-"):
            continue
        return token
    return ""


def _workspace_shell_text(workspace: Path, relative: str, seen: set[Path]) -> str | None:
    """Return a workspace shell script, or None when its contents cannot be proven safe."""
    if not relative or "$" in relative or "`" in relative or relative.startswith(("/", "\\")) or ".." in Path(relative).parts:
        return None
    root = workspace.resolve()
    try:
        candidate = (root / relative).resolve()
    except OSError:
        return None
    if not candidate.is_file() or not candidate.is_relative_to(root):
        return ""
    if candidate in seen:
        return ""
    try:
        if candidate.stat().st_size > _SHELL_SCAN_BYTES:
            return None
        seen.add(candidate)
        return candidate.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def _forbidden_shell_target(segment: str) -> str:
    if any(pattern.search(segment) for pattern in _FORBIDDEN_TEST_CMD_PATTERNS):
        for fragment in _PATH_FRAGMENT.findall(segment):
            if is_any_test_path(fragment):
                return fragment
        return "a preset test path"
    try:
        tokens = shlex.split(segment)
    except ValueError:
        return ""
    first_cmd = posixpath.basename(tokens[0].lower())
    if first_cmd in _DESTRUCTIVE_CMDS:
        for token in tokens[1:]:
            if not token.startswith("-") and is_any_test_path(token):
                return token
    if first_cmd == "sed":
        has_inplace = any(tok.startswith("-i") or tok.startswith("--in-place") for tok in tokens[1:])
        if has_inplace:
            for token in tokens[1:]:
                if not token.startswith("-") and is_any_test_path(token):
                    return token
    return ""


def _shell_file_write_target(workspace: Path, argv: tuple[str, ...], seen: set[Path] | None, depth: int) -> str:
    """Block a shell script file that would modify a test path."""
    if depth > 6:
        return "a computed execution"
    relative = _shell_script_argument(argv)
    if not relative:
        return ""
    seen = set() if seen is None else seen
    text = _workspace_shell_text(workspace, relative, seen)
    if text is None:
        return "a computed execution"
    if not text:
        return ""
    return _scan_shell_script(workspace, text, seen, depth + 1)


def _split_shell_segments(script: str) -> list[str]:
    segments: list[str] = []
    current: list[str] = []
    quote = ""
    index = 0
    while index < len(script):
        char = script[index]
        if quote:
            if char == "\\" and index + 1 < len(script):
                current.append(char)
                current.append(script[index + 1])
                index += 2
                continue
            if char == quote:
                quote = ""
            current.append(char)
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            current.append(char)
            index += 1
            continue
        if char == "\\" and index + 1 < len(script):
            current.append(char)
            current.append(script[index + 1])
            index += 2
            continue
        if char in {";", "\n"}:
            seg = "".join(current).strip()
            if seg:
                segments.append(seg)
            current = []
            index += 1
            continue
        if script.startswith(("&&", "||"), index):
            seg = "".join(current).strip()
            if seg:
                segments.append(seg)
            current = []
            index += 2
            continue
        if char == "&":
            seg = "".join(current).strip()
            if seg:
                segments.append(seg)
            current = []
            index += 1
            continue
        current.append(char)
        index += 1
    seg = "".join(current).strip()
    if seg:
        segments.append(seg)
    return segments


def _scan_shell_script(workspace: Path, script: str, seen: set[Path] | None, depth: int) -> str:
    """Block a shell script that launches a Python writer or edits a test path."""
    if depth > 6:
        return "a computed execution"
    seen = set() if seen is None else seen
    for segment in _split_shell_segments(script):
        if not segment or segment.startswith("#"):
            continue
        blocked = _forbidden_shell_target(segment)
        if blocked:
            return blocked
        try:
            tokens = shlex.split(segment)
        except ValueError:
            return "a computed execution"
        if not tokens:
            continue
        if _is_python_command(tuple(tokens)):
            if any("$" in token or "`" in token for token in tokens):
                return "a computed execution"
            found = _workspace_python_write_target(workspace, tuple(tokens), seen, depth + 1)
            if found:
                return found
            continue
        head = posixpath.basename(tokens[0])
        if head in {"eval", "source", "."}:
            if any("$" in token or "`" in token for token in tokens[1:]):
                return "a computed execution"
            if head == "eval":
                nested_text = " ".join(tokens[1:]).strip()
                if not nested_text:
                    return "a computed execution"
                found = _scan_shell_script(workspace, nested_text, seen, depth + 1)
            else:
                script_text = _workspace_shell_text(workspace, tokens[1], seen) if len(tokens) > 1 else None
                if script_text is None:
                    return "a computed execution"
                found = _scan_shell_script(workspace, script_text, seen, depth + 1) if script_text else ""
            if found:
                return found
            continue
        nested = _shell_command_text(tuple(tokens))
        if nested:
            found = _scan_shell_script(workspace, nested, seen, depth + 1)
            if found:
                return found
            continue
        found = _shell_file_write_target(workspace, tuple(tokens), seen, depth)
        if found:
            return found
    return ""


def _subprocess_write_target(
    workspace: Path,
    script: str,
    seen: set[Path] | None,
    depth: int,
    is_test_context: bool = True,
) -> str:
    """Block an interpreter launched through subprocess or os.system."""
    if depth > 6:
        return "a computed execution" if (is_test_context and depth == 0) else ""
    for match in _PROCESS_CALL.finditer(script):
        parsed = _call_arguments(script, match.end() - 1)
        if parsed is None or not parsed[0] or not parsed[0][0].strip():
            if depth == 0 and is_test_context:
                return "a computed execution"
            continue
        argv = _command_tokens(parsed[0][0])
        if argv is None:
            if depth == 0 and is_test_context:
                return "a computed execution"
            continue
        if not argv:
            continue
        if _is_python_command(tuple(argv)):
            found = _workspace_python_write_target(workspace, tuple(argv), seen, depth + 1)
        else:
            shell_text = _shell_command_text(tuple(argv))
            if shell_text:
                found = _scan_shell_script(workspace, shell_text, seen, depth + 1)
            else:
                found = _shell_file_write_target(workspace, tuple(argv), seen, depth + 1)
        if found:
            return found
    return ""


def _dynamic_execution_target(
    workspace: Path,
    script: str,
    seen: set[Path] | None = None,
    depth: int = 0,
    is_test_context: bool = True,
) -> str:
    """Block exec, runpy, and file loaders whose target can write a test file."""
    for name, arg_index in _EXECUTION_CALLS:
        pattern = rf"(?<![\w]){name}\s*\("
        for match in re.finditer(pattern, script):
            parsed = _call_arguments(script, match.end() - 1)
            if parsed is None or arg_index >= len(parsed[0]):
                if is_test_context:
                    return "a computed execution"
                continue
            found = _execution_argument_target(workspace, name, parsed[0][arg_index], seen, depth, is_test_context=is_test_context)
            if found:
                return found
    launched = _subprocess_write_target(workspace, script, seen, depth, is_test_context=is_test_context)
    if launched:
        return launched
    return _getattr_execution_target(workspace, script, seen, depth, is_test_context=is_test_context)


def _is_python_command(cmd_tokens: tuple[str, ...]) -> bool:
    if not cmd_tokens:
        return False
    exe = posixpath.basename(cmd_tokens[0]).lower().removesuffix(".exe")
    return exe in {"python", "python3", "pypy", "pypy3"} or re.fullmatch(r"python3?\.\d+", exe) is not None


def _workspace_python_write_target(
    workspace: Path,
    cmd_tokens: tuple[str, ...],
    seen: set[Path] | None = None,
    depth: int = 0,
) -> str:
    """Block a Python command whose workspace module would write a test file."""
    if depth > 6 or not _is_python_command(cmd_tokens):
        return "a computed execution" if depth > 6 else ""
    seen = set() if seen is None else seen
    script = _eval_script_text(cmd_tokens)
    if script:
        dynamic = _unproven_dynamic_import(script)
        if dynamic:
            return dynamic
        executed = _dynamic_execution_target(workspace, script, seen, depth)
        if executed:
            return executed
        return _source_write_target(workspace, script, seen, depth)
    module = _python_module_flag(cmd_tokens)
    if module:
        return _module_flag_write_target(workspace, module)
    if len(cmd_tokens) < 2 or cmd_tokens[1].startswith("-"):
        return ""
    try:
        candidate = (workspace / cmd_tokens[1]).resolve()
        root = workspace.resolve()
        if not candidate.is_file() or not candidate.is_relative_to(root):
            return ""
        if candidate in seen:
            return ""
        seen.add(candidate)
        text = candidate.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError):
        return cmd_tokens[1]
    rel_path = str(candidate.relative_to(root)) if candidate.is_relative_to(root) else str(candidate)
    return _source_write_target(workspace, text, seen, depth=depth + 1, is_test_context=is_any_test_path(rel_path))


def _eval_script_text(cmd_tokens: tuple[str, ...]) -> str:
    for index, token in enumerate(cmd_tokens):
        if token in {"-c", "-e", "-E", "--eval", "-r"} and index + 1 < len(cmd_tokens):
            return cmd_tokens[index + 1]
        if token.startswith("--eval="):
            return token.split("=", 1)[1]
    return ""


def _interpreter_test_target(cmd_tokens: tuple[str, ...]) -> str:
    """Return the test path named by an interpreter one-liner, or an empty string."""
    exe = posixpath.basename(cmd_tokens[0]).lower().removesuffix(".exe")
    flags = cmd_tokens[1:]
    is_eval = False
    if exe in {"python", "python3", "pypy", "pypy3"} or re.fullmatch(r"python3?\.\d+", exe):
        is_eval = "-c" in flags
    elif exe == "perl":
        is_eval = any(tok in {"-e", "-E"} or (tok.startswith("-") and "i" in tok) for tok in flags)
    elif exe in {"node", "nodejs"}:
        is_eval = "-e" in flags or "--eval" in flags
    elif exe in {"ruby", "php"}:
        is_eval = any(tok in {"-e", "-r"} or (tok.startswith("-") and ("i" in tok or "p" in tok)) for tok in flags)
    if not is_eval:
        return ""
    for fragment in _PATH_FRAGMENT.findall(" ".join(cmd_tokens)):
        if is_any_test_path(fragment):
            return fragment
    for tok in cmd_tokens:
        cleaned = tok.strip("\"'")
        if is_any_test_path(cleaned):
            return cleaned
    return _spliced_test_target(_eval_script_text(cmd_tokens))


@dataclass(frozen=True)
class TerminalAction:
    """An action emitted by the agent model during a terminal turn."""
    action_type: str  # "command", "patch", "read_file", "write_file", "finish"
    command: tuple[str, ...] = field(default_factory=tuple)
    path: str = ""
    search_block: str = ""
    replace_block: str = ""
    content: str = ""
    start_line: int | None = None
    end_line: int | None = None
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"action_type": self.action_type}
        if self.command:
            data["command"] = list(self.command)
        if self.path:
            data["path"] = self.path
        if self.search_block:
            data["search_block"] = self.search_block
        if self.replace_block:
            data["replace_block"] = self.replace_block
        if self.content:
            data["content"] = self.content
        if self.start_line is not None:
            data["start_line"] = self.start_line
        if self.end_line is not None:
            data["end_line"] = self.end_line
        if self.explanation:
            data["explanation"] = self.explanation
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TerminalAction:
        action_type = str(data.get("action_type") or data.get("action") or "finish").strip().lower()
        if action_type in {"write_file", "write_text", "create_file"}:
            action_type = "write_file"
        cmd = data.get("command") or data.get("cmd") or data.get("argv") or []
        if isinstance(cmd, str):
            cmd = cmd.split()
        elif not isinstance(cmd, (list, tuple)):
            cmd = []

        content = str(data.get("content") or data.get("text") or "")
        return cls(
            action_type=action_type,
            command=tuple(str(x) for x in cmd),
            path=str(data.get("path") or "").strip(),
            search_block=str(data.get("search_block") or ""),
            replace_block=str(data.get("replace_block") or ""),
            content=content,
            start_line=int(data["start_line"]) if "start_line" in data and str(data["start_line"]).isdigit() else None,
            end_line=int(data["end_line"]) if "end_line" in data and str(data["end_line"]).isdigit() else None,
            explanation=str(data.get("explanation") or data.get("reason") or "").strip(),
        )


@dataclass(frozen=True)
class TerminalObservation:
    """The result of executing an action in the environment."""
    action_type: str
    status: str  # "ok", "error", "blocked", "halted"
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    output: str = ""
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "status": self.status,
            "exit_code": self.exit_code,
            "stdout": self.stdout[:4000],
            "stderr": self.stderr[:4000],
            "output": self.output[:4000],
            "reason": self.reason,
        }


@dataclass(frozen=True)
class TerminalStep:
    """A full step recording action, observation, and hexagram assessment."""
    turn_index: int
    action: TerminalAction
    observation: TerminalObservation
    hexagram_code: int = 63  # 63: 乾为天, 39: 山天大畜, 40: 火地晋
    timestamp_ns: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_index": self.turn_index,
            "action": self.action.to_dict(),
            "observation": self.observation.to_dict(),
            "hexagram_code": self.hexagram_code,
            "timestamp_ns": self.timestamp_ns,
        }


_IGNORED_SNAPSHOT_DIRS = frozenset({
    ".git",
    ".onecode",
    "__pycache__",
    ".venv",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".worktrees",
})


def _snapshot_non_test_hashes(workspace: Path) -> dict[str, str]:
    """Capture SHA-256 digests of non-test workspace files for command write auditing."""
    hashes: dict[str, str] = {}
    if not workspace.is_dir():
        return hashes
    root = workspace.resolve()
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        try:
            rel_parts = p.relative_to(root).parts
        except ValueError:
            continue
        if any(part in _IGNORED_SNAPSHOT_DIRS for part in rel_parts):
            continue
        if p.suffix in {".pyc", ".pyo"}:
            continue
        rel = "/".join(rel_parts)
        if is_any_test_path(rel):
            continue
        try:
            hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
        except OSError:
            continue
    return hashes


def _resolved_line_range(target: Path, start_line: int | None, end_line: int | None) -> tuple[int, int, int]:
    lines = target.read_text(encoding="utf-8").splitlines()
    total_lines = len(lines)
    start = max(1, start_line or 1)
    end = min(total_lines, end_line or (start + 200))
    return start, end, total_lines


def _is_valid_read_pagination(
    seen_lines: set[int],
    start: int,
    end: int,
    total_lines: int,
    consecutive_reads: int,
) -> bool:
    """Allow meaningful non-overlapping pagination while guarding against tiny sliding loops."""
    if total_lines <= 0 or start > end or end > total_lines or consecutive_reads >= 8:
        return False
    requested = set(range(start, end + 1))
    new_lines = len(requested - seen_lines)
    if new_lines == 0:
        return False
    overlap_ratio = len(requested & seen_lines) / len(requested)
    if overlap_ratio >= 0.5:
        return False
    if new_lines >= 15:
        return True
    return end == total_lines and len(seen_lines) >= 15 and start > max(seen_lines, default=0)


def _read_file_excerpt(target: Path, path: str, start_line: int | None, end_line: int | None) -> str:
    lines = target.read_text(encoding="utf-8").splitlines()
    total_lines = len(lines)
    start = max(1, start_line or 1)
    end = min(total_lines, end_line or (start + 200))
    selected = lines[start - 1 : end]
    numbered = [f"{i + start:4d} | {line}" for i, line in enumerate(selected)]
    return f"## {path} (lines {start}-{end} of {total_lines})\n" + "\n".join(numbered)


def _repeated_read_observation(path: str, stalls: int, excerpt: str = "") -> TerminalObservation:
    if stalls >= 2:
        return TerminalObservation(
            action_type="read_file",
            status="halted",
            reason="stagnation_loop",
            stderr=(
                f"Stagnation warning (Lyapunov Stagnation Guard): Detected repeated redundant read of '{path}'. "
                "Do not repeat the same read; run verification tests with 'command' or submit 'finish'."
            ),
        )
    return TerminalObservation(
        action_type="read_file",
        status="error",
        reason="repeated_read",
        stderr=(
            f"Stagnation warning: You have already read this line range (or exceeded consecutive reads) of '{path}'. "
            "The lines you just requested are included below. "
            "Do not repeat redundant or sliding reads of the same file. "
            "The next redundant read of this file halts the session. "
            "Proceed to apply a patch with 'patch' or run a print-only reproduction with 'command'."
        ),
        output=excerpt,
    )


def _src_prefix_hint(workspace: Path, path: str) -> str | None:
    if path.startswith("/") or ".." in Path(path).parts:
        return None
    if (workspace / path).is_file():
        return None
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized.startswith("src/"):
        return None
    alternative = normalized[4:]
    if alternative == "" or alternative.startswith("/") or ".." in Path(alternative).parts:
        return None
    if not (workspace / alternative).is_file():
        return None
    return (
        f"File '{path}' does not exist, but '{alternative}' exists in the workspace. "
        f"Did you mean '{alternative}'? Do not add a 'src/' prefix."
    )


_COLLECTION_RETURN = re.compile(r"return\s+(?:\{|\[|set\(|list\()")
_SCALAR_RETURN = re.compile(r"""return\s+(?:'[^']*'|"[^"]*"|None|True|False|[A-Za-z_][A-Za-z0-9_]*)""")


def _patch_widens_return_to_collection(action: TerminalAction) -> bool:
    search = action.search_block
    replace = action.replace_block
    if not _COLLECTION_RETURN.search(replace) or _COLLECTION_RETURN.search(search):
        return False
    return _SCALAR_RETURN.search(search) is not None


def _patch_replaces_equality_with_membership(action: TerminalAction) -> bool:
    return "==" in action.search_block and " in " in action.replace_block


def _command_reports_missing_test(observation: TerminalObservation) -> bool:
    if observation.exit_code == 4:
        return True
    text = f"{observation.stdout}\n{observation.stderr}".lower()
    return "no tests ran" in text


def _session_has_modifications(workspace: Path, steps: list[TerminalStep]) -> bool:
    if any(s.action.action_type in {"patch", "write_file"} and s.observation.status == "ok" for s in steps):
        return True
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                target_rel = line[3:].strip()
                if line.strip() and not is_any_test_path(target_rel):
                    return True
    except Exception:
        pass
    return False


_INSPECTION_UTILITIES = frozenset({
    "ls", "dir", "find", "cat", "grep", "egrep", "fgrep", "rg", "ag",
    "sed", "awk", "head", "tail", "less", "more", "wc", "file", "nl",
    "pwd", "tree", "echo", "which", "whereis", "sort", "uniq", "stat",
    "cut", "tr", "true", "xargs",
})

_VERIFICATION_INDICATORS = frozenset({
    "pytest", "python", "python3", "tox", "unittest", "runtests",
    "cargo", "go", "npm", "node", "jest", "mocha", "vitest",
    "make", "ctest", "ruby", "rake",
})


def _is_inspection_command(command: tuple[str, ...] | list[str] | None) -> bool:
    if not command:
        return False
    parts = list(command)
    if len(parts) >= 3 and parts[0] in {"bash", "sh", "/bin/bash", "/bin/sh"} and parts[1] in {"-c", "-lc", "-cl"}:
        script_text = parts[2]
    else:
        script_text = " ".join(parts)
    tokens = [t.lower() for t in re.findall(r"[A-Za-z0-9_.-]+", script_text)]
    if not tokens:
        return False
    if any(tok in _VERIFICATION_INDICATORS for tok in tokens):
        return False
    sub_cmds = re.split(r"[;&|]+", script_text)
    for sub in sub_cmds:
        sub_tokens = [t.lower() for t in re.findall(r"[A-Za-z0-9_.-]+", sub)]
        if not sub_tokens:
            continue
        first = sub_tokens[0]
        if first == "git":
            if len(sub_tokens) <= 1 or sub_tokens[1] not in {"diff", "status", "log", "show", "branch"}:
                return False
        elif first not in _INSPECTION_UTILITIES:
            return False
    return True


def _status_directive(
    steps: list[TerminalStep],
    workspace: Path | None = None,
    max_turns: int | None = None,
    *,
    command_modified_files: list[str] | None = None,
    last_command_mod_turn: int | None = None,
) -> str:
    pending_membership = False
    applied_patch = False
    last_mod_idx = -1
    for i, step in enumerate(steps):
        action = step.action
        if action.action_type not in {"patch", "write_file"} or step.observation.status != "ok":
            continue
        applied_patch = True
        last_mod_idx = i
        if _patch_widens_return_to_collection(action):
            pending_membership = True
        if _patch_replaces_equality_with_membership(action):
            pending_membership = False
    if not applied_patch and workspace is not None:
        if command_modified_files or _session_has_modifications(workspace, steps):
            applied_patch = True
            for i, step in enumerate(steps):
                if last_command_mod_turn is not None and step.turn_index == last_command_mod_turn:
                    last_mod_idx = max(last_mod_idx, i)
                elif last_command_mod_turn is None and step.action.action_type == "command" and step.observation.status == "ok":
                    last_mod_idx = max(last_mod_idx, i)
    latest = steps[-1] if steps else None
    if latest is not None and latest.action.action_type == "command" and _command_reports_missing_test(latest.observation):
        return (
            "Status Directive: That command reported a missing test. "
            "Do not retry it and do not search the checkout for that test function. "
            "A missing result is exit code 4, 'not found', or 'no tests ran'. "
            "If a patch changed a return value from a string or scalar into a set or list, "
            "update every downstream equality check ('==') of that value to a membership check ('in') "
            "before running another command."
        )
    if pending_membership:
        return (
            "Status Directive: A patch changed a return value from a string or scalar into a set or list. "
            "Before running tests or finish, inspect consumers and change equality checks ('==') "
            "of that returned value into membership checks ('in')."
        )
    if applied_patch:
        if max_turns is not None and len(steps) + 1 >= max_turns:
            return (
                f"Status Directive: CRITICAL FINAL TURN (Turn {len(steps) + 1} of {max_turns}). "
                "Implementation files have been modified. Do not execute further inspection or test commands. "
                "Submit 'finish' NOW with an explanation of your changes to complete the task."
            )
        steps_after = steps[last_mod_idx + 1 :] if last_mod_idx >= 0 else []
        cmds_after = [s for s in steps_after if s.action.action_type == "command"]
        if cmds_after:
            latest_cmd = cmds_after[-1]
            if latest_cmd.observation.exit_code == 0 and not _command_reports_missing_test(latest_cmd.observation):
                if _is_inspection_command(latest_cmd.action.command):
                    return (
                        "Status Directive: Inspection command completed (exit code 0). "
                        "If you need to make further adjustments, apply them with 'patch' or 'write_file'. "
                        "Once changes are complete, run a verification test or reproduction command "
                        "(e.g. pytest, python -c) to verify your fix before submitting 'finish'."
                    )
                return (
                    "Status Directive: Verification succeeded (exit code 0) after your changes. "
                    "Verification is satisfied. Do not run further redundant inspection or read commands. "
                    "Submit 'finish' now with an explanation of your fix to complete the task."
                )
            if latest_cmd.observation.exit_code is not None and latest_cmd.observation.exit_code != 0:
                return (
                    f"Status Directive: Your latest command exited with code {latest_cmd.observation.exit_code}. "
                    "Inspect the failure output, adjust the implementation with 'patch' for targeted fixes. "
                    "Do not rewrite the entire file with 'write_file' if only a small targeted fix is needed. "
                    "Then run verification tests to confirm your fix."
                )
        return (
            "Status Directive: You have already applied a code change. "
            "Avoid redundant re-reading of the same file. "
            "Proceed to run verification tests with 'command' or submit 'finish' to complete the task."
        )
    if not applied_patch:
        inspect_count = sum(1 for s in steps if s.action.action_type in {"read_file", "command"})
        if inspect_count >= 2:
            return (
                "Status Directive: Initial reconnaissance completed. "
                "Proceed to implement the necessary code changes using 'write_file' or 'patch'. "
                "Avoid further redundant reads or inspection commands."
            )
    return ""


def _command_tamper_target(workspace: Path, cmd_tokens: tuple[str, ...]) -> str:
    """Return the test path a command would modify, before the command runs."""
    if not cmd_tokens:
        return ""
    cmd_str = " ".join(cmd_tokens)
    if any(pat.search(cmd_str) for pat in _FORBIDDEN_TEST_CMD_PATTERNS):
        for fragment in _PATH_FRAGMENT.findall(cmd_str):
            if is_any_test_path(fragment):
                return fragment
        return "a preset test path"
    first_cmd = posixpath.basename(cmd_tokens[0].lower())
    if first_cmd in _DESTRUCTIVE_CMDS:
        for tok in cmd_tokens[1:]:
            if not tok.startswith("-") and is_any_test_path(tok):
                return tok
    if first_cmd == "sed":
        has_inplace = any(tok.startswith("-i") or tok.startswith("--in-place") for tok in cmd_tokens[1:])
        if has_inplace:
            for tok in cmd_tokens[1:]:
                if not tok.startswith("-") and is_any_test_path(tok):
                    return tok
    found = _interpreter_test_target(cmd_tokens)
    if found:
        return found
    found = _workspace_python_write_target(workspace, cmd_tokens)
    if found:
        return found
    shell_text = _shell_command_text(cmd_tokens)
    if shell_text:
        return _scan_shell_script(workspace, shell_text, set(), 0)
    return _shell_file_write_target(workspace, cmd_tokens, set(), 0)


def _detect_test_file_tamper(workspace: Path, initial_test_hashes: dict[str, str]) -> str:
    """Return tamper description if any test file was modified, deleted, or created."""
    for rel, orig_hash in initial_test_hashes.items():
        target = workspace / rel
        if not target.is_file():
            return f"Test file '{rel}' was deleted"
        try:
            current_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        except OSError as ex:
            return f"Test file '{rel}' could not be read: {ex}"
        if current_hash != orig_hash:
            return f"Test file '{rel}' was modified (SHA-256 hash mismatch)"
    for path in workspace.rglob("*"):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(workspace).as_posix()
        except ValueError:
            continue
        if rel not in initial_test_hashes and is_any_test_path(rel):
            return f"New test file '{rel}' was created"
    return ""


def _restore_workspace_test_files(
    workspace: Path,
    initial_test_bytes: dict[str, bytes],
    initial_test_hashes: dict[str, str],
) -> list[str]:
    """Restore snapshotted test files and remove test files created during the session."""
    restored: list[str] = []
    for rel, payload in initial_test_bytes.items():
        target = workspace / rel
        try:
            current = target.read_bytes() if target.is_file() else None
        except OSError:
            current = None
        if current == payload:
            continue
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        elif target.exists() or target.is_symlink():
            target.unlink()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        restored.append(rel)
    for path in list(workspace.rglob("*")):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(workspace).as_posix()
        except ValueError:
            continue
        if rel in initial_test_hashes or not is_any_test_path(rel):
            continue
        path.unlink()
        restored.append(rel)
    return restored


class TerminalSession:
    """Manages multi-turn stateful terminal interaction in the workspace sandbox."""

    def __init__(
        self,
        workspace: Path,
        task: str,
        *,
        max_turns: int = 15,
        tool_registry: ToolRegistry | None = None,
        require_modification: bool = True,
        approval_mode: str = "scoped_auto",
        execution_approval: Callable[[TerminalAction], bool] | None = None,
        auto_approved_for_eval: bool = False,
        execution_scope: ExecutionScope | str = ExecutionScope.FULL_TERMINAL,
        rollback_on_failure: bool = False,
    ) -> None:
        self.workspace = workspace.resolve()
        self.task = task
        self.max_turns = max_turns
        self.tool_registry = tool_registry or default_tool_registry()
        self.require_modification = require_modification
        self.approval_mode = approval_mode
        self.execution_approval = execution_approval
        self.auto_approved_for_eval = auto_approved_for_eval
        self.execution_scope = (
            ExecutionScope(execution_scope)
            if isinstance(execution_scope, str)
            else execution_scope
        )
        self.rollback_on_failure = rollback_on_failure
        self.snapshot = WorkspaceSnapshot(self.workspace)
        self.approved_actions_count = 0
        self.blocked_approvals_count = 0
        self.steps: list[TerminalStep] = []
        self.is_finished = False
        self.finish_explanation = ""
        self.last_command_signature = ""
        self.consecutive_stalls = 0
        self.last_read_signature = ""
        self.last_read_lines: set[int] = set()
        self.consecutive_file_reads = 0
        self.consecutive_read_stalls = 0
        self.command_modified_files: list[str] = []
        self.last_command_mod_turn: int | None = None
        self.initial_test_bytes: dict[str, bytes] = {}
        self._symbol_index: WorkspaceSymbolIndex | None = None
        self.test_integrity_broken = False
        self.initial_test_hashes = self._snapshot_test_files()

    def _snapshot_test_files(self) -> dict[str, str]:
        hashes: dict[str, str] = {}
        if not self.workspace.is_dir():
            return hashes
        for p in self.workspace.rglob("*"):
            if not p.is_file():
                continue
            try:
                rel = p.relative_to(self.workspace).as_posix()
            except ValueError:
                continue
            if not is_any_test_path(rel):
                continue
            try:
                payload = p.read_bytes()
            except OSError:
                continue
            self.initial_test_bytes[rel] = payload
            hashes[rel] = hashlib.sha256(payload).hexdigest()
        return hashes

    def _test_file_tamper_reason(self) -> str:
        return _detect_test_file_tamper(self.workspace, self.initial_test_hashes)

    def restore_test_files(self) -> list[str]:
        """Put every snapshotted test file back and remove test files created during the session."""
        return _restore_workspace_test_files(self.workspace, self.initial_test_bytes, self.initial_test_hashes)

    def rollback(self, *, force_git_clean: bool = False) -> dict[str, Any]:
        """Restores workspace implementation and test files to their pre-session state."""
        self.restore_test_files()
        return self.snapshot.rollback(force_git_clean=force_git_clean)

    def verify_test_files_integrity(self) -> tuple[bool, str]:
        """Compares workspace test files against the session snapshot and restores them on mismatch."""
        problem = self._test_file_tamper_reason()
        if not problem and not self.test_integrity_broken:
            return True, ""
        self.test_integrity_broken = True
        self.restore_test_files()
        return False, problem or "Test files were modified earlier in this session and have been restored"

    def command_tamper_target(self, cmd_tokens: tuple[str, ...]) -> str:
        """Return the test path a command would modify, before the command runs."""
        return _command_tamper_target(self.workspace, cmd_tokens)

    def is_command_tampering(self, cmd_tokens: tuple[str, ...]) -> bool:
        return bool(self.command_tamper_target(cmd_tokens))

    def _check_approval(self, action: TerminalAction) -> TerminalObservation | None:
        if self.approval_mode != "strict" or action.action_type not in {"patch", "command"}:
            return None
        if self.execution_approval is not None:
            if not self.execution_approval(action):
                self.blocked_approvals_count += 1
                return TerminalObservation(
                    action_type=action.action_type,
                    status="blocked",
                    reason="approval_denied",
                    stderr=f"Approval denied for {action.action_type}: rejected by execution_approval callback.",
                )
            self.approved_actions_count += 1
            return None
        if not self.auto_approved_for_eval:
            self.blocked_approvals_count += 1
            return TerminalObservation(
                action_type=action.action_type,
                status="blocked",
                reason="approval_required",
                stderr=f"Action '{action.action_type}' blocked: approval_mode is strict but no execution_approval callback provided.",
            )
        self.approved_actions_count += 1
        return None

    def _handle_finish(self, action: TerminalAction) -> TerminalObservation:
        intact, tamper_reason = self.verify_test_files_integrity()
        if not intact:
            return TerminalObservation(
                action_type="finish",
                status="blocked",
                reason="preset_test_immutable",
                stderr=f"Cannot finish: {tamper_reason}. Test files are strictly immutable across all languages.",
            )
        has_modified = bool(self.command_modified_files) or _session_has_modifications(self.workspace, self.steps)
        if self.require_modification and not has_modified:
            return TerminalObservation(
                action_type="finish",
                status="error",
                reason="unmodified_workspace",
                stderr="Cannot finish: no implementation files have been modified or patched yet. First inspect files, apply patches, and verify.",
            )
        self.is_finished = True
        self.finish_explanation = action.explanation or "Task completed by agent."
        return TerminalObservation(
            action_type="finish",
            status="ok",
            output=self.finish_explanation,
        )

    def execute_action(self, action: TerminalAction) -> TerminalObservation:
        """Executes an action under sandbox security policies and records the observation."""
        # Immutable security invariant: test anti-tamper is always enforced first
        if action.action_type in {"patch", "write_file"} and is_any_test_path(action.path):
            obs = TerminalObservation(
                action_type=action.action_type,
                status="blocked",
                reason="preset_test_immutable",
                stderr=(
                    f"Anti-tamper protection active: Modification of test files ({action.path}) is strictly prohibited "
                    "across all languages (Python, Go, TypeScript/JavaScript, Rust, Ruby). Patch implementation files instead."
                ),
            )
            self._record_step(action, obs, hexagram_code=40)
            return obs

        tamper_target = self.command_tamper_target(action.command) if action.action_type == "command" else ""
        if tamper_target:
            self.test_integrity_broken = True
            obs = TerminalObservation(
                action_type="command",
                status="blocked",
                reason="preset_test_immutable",
                stderr=(
                    f"Anti-tamper protection active: Shell commands modifying test files ({tamper_target}) "
                    "are forbidden across all languages."
                ),
            )
            self._record_step(action, obs, hexagram_code=40)
            return obs

        if action.action_type == "command":
            escape_reason = PathGuard.detect_command_workspace_escape(self.workspace, action.command)
            if escape_reason:
                obs = TerminalObservation(
                    action_type="command",
                    status="blocked",
                    reason="workspace_escape_denied",
                    stderr=f"Boundary protection active: {escape_reason}. Commands must remain confined to the workspace.",
                )
                self._record_step(action, obs, hexagram_code=40)
                return obs

        # Scope capability policy check (READ_ONLY, PATCH_GUARDED, FULL_TERMINAL)
        scope_decision = ToolCapabilityPolicy.evaluate(
            self.execution_scope,
            action.action_type,
            action.command,
            is_inspection=_is_inspection_command(action.command),
        )
        if not scope_decision.allowed:
            obs = TerminalObservation(
                action_type=action.action_type,
                status="blocked",
                reason=scope_decision.reason,
                stderr=scope_decision.stderr,
            )
            self._record_step(action, obs, hexagram_code=scope_decision.hexagram_code)
            return obs

        # Approval gate policy check
        approval_obs = self._check_approval(action)
        if approval_obs is not None:
            self._record_step(action, approval_obs, hexagram_code=39)
            return approval_obs

        if action.action_type == "finish":
            obs = self._handle_finish(action)
            hex_code = 63 if obs.status == "ok" else (40 if obs.reason == "preset_test_immutable" else 39)
            self._record_step(action, obs, hexagram_code=hex_code)
            return obs

        if action.action_type == "write_file":
            self.last_command_signature = ""
            self.consecutive_stalls = 0
            self.last_read_signature = ""
            self.last_read_lines.clear()
            self.consecutive_file_reads = 0
            self.consecutive_read_stalls = 0
            obs = self._handle_write_file(action)
            hex_code = 63 if obs.status == "ok" else 39
            self._record_step(action, obs, hexagram_code=hex_code)
            return obs

        if action.action_type == "patch":
            self.last_command_signature = ""
            self.consecutive_stalls = 0
            self.last_read_signature = ""
            self.last_read_lines.clear()
            self.consecutive_file_reads = 0
            self.consecutive_read_stalls = 0
            obs = self._handle_patch(action)
            hex_code = 63 if obs.status == "ok" else 39
            self._record_step(action, obs, hexagram_code=hex_code)
            return obs

        if action.action_type == "read_file":
            self.last_command_signature = ""
            self.consecutive_stalls = 0
            obs = self._handle_read_file(action)
            hex_code = 63 if obs.status == "ok" else (40 if obs.status in {"blocked", "halted"} else 39)
            self._record_step(action, obs, hexagram_code=hex_code)
            return obs

        if action.action_type == "command":
            self.last_read_signature = ""
            self.last_read_lines.clear()
            self.consecutive_file_reads = 0
            self.consecutive_read_stalls = 0
            obs = self._handle_command(action)
            hex_code = 63 if obs.status == "ok" else (40 if obs.status == "blocked" else 39)
            self._record_step(action, obs, hexagram_code=hex_code)
            return obs

        obs = TerminalObservation(
            action_type=action.action_type,
            status="error",
            reason="unknown_action_type",
            stderr=f"Unknown action_type '{action.action_type}'. Valid types: command, patch, write_file, read_file, finish.",
        )
        self._record_step(action, obs, hexagram_code=39)
        return obs

    def _handle_write_file(self, action: TerminalAction) -> TerminalObservation:
        if not action.path:
            return TerminalObservation(action_type="write_file", status="error", reason="empty_path", stderr="Path cannot be empty.")
        if is_any_test_path(action.path):
            return TerminalObservation(
                action_type="write_file",
                status="blocked",
                reason="preset_test_immutable",
                stderr=(
                    f"Anti-tamper protection active: Modification of test files ({action.path}) is strictly prohibited "
                    "across all languages (Python, Go, TypeScript/JavaScript, Rust). Patch implementation files instead."
                ),
            )
        tool = self.tool_registry.get("write_text")
        if tool is None:
            return TerminalObservation(action_type="write_file", status="error", reason="tool_not_found", stderr="write_text tool is missing.")
        self.snapshot.record_before_write(action.path)
        content = action.content or action.replace_block
        try:
            res = tool.execute({"path": action.path, "content": content}, self.workspace)
            status = "ok" if res.get("status") in {"ok", "completed"} else "error"
            return TerminalObservation(
                action_type="write_file",
                status=status,
                output=res.get("summary") or f"Successfully wrote {action.path}",
                stderr=res.get("reason") or "",
            )
        except (OSError, ValueError, RuntimeError, TypeError, KeyError, AttributeError) as ex:
            return TerminalObservation(
                action_type="write_file",
                status="error",
                reason="write_failed",
                stderr=str(ex) or type(ex).__name__,
            )

    def _handle_patch(self, action: TerminalAction) -> TerminalObservation:
        if not action.path:
            return TerminalObservation(action_type="patch", status="error", reason="empty_path", stderr="Path cannot be empty.")
        if is_any_test_path(action.path):
            return TerminalObservation(
                action_type="patch",
                status="blocked",
                reason="preset_test_immutable",
                stderr=(
                    f"Anti-tamper protection active: Modification of test files ({action.path}) is strictly prohibited "
                    "across all languages (Python, Go, TypeScript/JavaScript, Rust). Patch implementation files instead."
                ),
            )
        if not action.search_block and action.replace_block:
            return self._handle_write_file(
                TerminalAction(
                    action_type="write_file",
                    path=action.path,
                    content=action.replace_block,
                    explanation=action.explanation,
                )
            )
        hint = _src_prefix_hint(self.workspace, action.path)
        if hint is not None:
            return TerminalObservation(action_type="patch", status="error", reason="patch_target_not_found", stderr=hint)
        tool = self.tool_registry.get("patch_text")
        if tool is None:
            return TerminalObservation(action_type="patch", status="error", reason="tool_not_found", stderr="patch_text tool is missing.")
        self.snapshot.record_before_write(action.path)
        try:
            res = tool.execute(
                {"path": action.path, "search_block": action.search_block, "replace_block": action.replace_block},
                self.workspace,
            )
            status = "ok" if res.get("status") in {"ok", "completed"} else "error"
            return TerminalObservation(
                action_type="patch",
                status=status,
                output=res.get("summary") or f"Successfully patched {action.path}",
                stderr=res.get("reason") or "",
            )
        except (OSError, ValueError, RuntimeError, TypeError, KeyError, AttributeError) as ex:
            return TerminalObservation(action_type="patch", status="error", reason="patch_failed", stderr=str(ex))

    def _handle_read_file(self, action: TerminalAction) -> TerminalObservation:
        if not action.path:
            return TerminalObservation(action_type="read_file", status="error", reason="empty_path", stderr="Path cannot be empty.")
        try:
            target = PathGuard.resolve_read_target(self.workspace, action.path)
        except PathGuardError as ex:
            return TerminalObservation(action_type="read_file", status="blocked", reason="sensitive_read_denied", stderr=f"Access denied: {ex}.")
        if not target.is_file():
            return TerminalObservation(action_type="read_file", status="error", reason="file_not_found", stderr=f"File '{action.path}' does not exist.")
        try:
            start, end, total_lines = _resolved_line_range(target, action.start_line, action.end_line)
            excerpt = _read_file_excerpt(target, action.path, action.start_line, action.end_line)
        except (OSError, UnicodeError, ValueError) as ex:
            return TerminalObservation(action_type="read_file", status="error", reason="read_error", stderr=str(ex))

        if action.path == self.last_read_signature:
            if _is_valid_read_pagination(
                self.last_read_lines,
                start,
                end,
                total_lines,
                self.consecutive_file_reads,
            ):
                self.last_read_lines.update(range(start, end + 1))
                self.consecutive_file_reads += 1
                self.consecutive_read_stalls = 0
                return TerminalObservation(action_type="read_file", status="ok", output=excerpt)
            self.consecutive_read_stalls += 1
            return _repeated_read_observation(
                action.path,
                self.consecutive_read_stalls,
                excerpt if self.consecutive_read_stalls < 2 else "",
            )

        self.last_read_signature = action.path
        self.last_read_lines = set(range(start, end + 1)) if start <= end <= total_lines else set()
        self.consecutive_file_reads = 1
        self.consecutive_read_stalls = 0
        return TerminalObservation(action_type="read_file", status="ok", output=excerpt)

    def _handle_command(self, action: TerminalAction) -> TerminalObservation:
        if not action.command:
            return TerminalObservation(action_type="command", status="error", reason="empty_command", stderr="Command cannot be empty.")
        tamper_target = self.command_tamper_target(action.command)
        if tamper_target:
            self.test_integrity_broken = True
            return TerminalObservation(
                action_type="command",
                status="blocked",
                reason="preset_test_immutable",
                stderr=(
                    f"Anti-tamper protection active: Shell commands modifying test files ({tamper_target}) "
                    "are forbidden across all languages."
                ),
            )

        escape_reason = PathGuard.detect_command_workspace_escape(self.workspace, action.command)
        if escape_reason:
            return TerminalObservation(
                action_type="command",
                status="blocked",
                reason="workspace_escape_denied",
                stderr=f"Boundary protection active: {escape_reason}. Commands must remain confined to the workspace.",
            )

        cmd_sig = " ".join(action.command)
        if cmd_sig == self.last_command_signature and self.steps and self.steps[-1].observation.status == "error":
            self.consecutive_stalls += 1
            if self.consecutive_stalls >= 2:
                return TerminalObservation(
                    action_type="command",
                    status="halted",
                    reason="stagnation_loop",
                    stderr="Stagnation warning (Lyapunov Stagnation Guard): Detected identical repeated failing command. Do not repeat the same command; inspect diagnostics and pivot your approach.",
                )
        else:
            self.last_command_signature = cmd_sig
            self.consecutive_stalls = 0

        tool = self.tool_registry.get("run_command")
        if tool is None:
            return TerminalObservation(action_type="command", status="error", reason="tool_not_found", stderr="run_command tool is missing.")
        try:
            pre_hashes = _snapshot_non_test_hashes(self.workspace)
            res = tool.execute({"argv": list(action.command), "timeout_seconds": 60}, self.workspace)
            code = res.get("returncode")
            status = "ok" if code == 0 else "error"
            intact, tamper_reason = self.verify_test_files_integrity()
            if not intact:
                return TerminalObservation(
                    action_type="command",
                    status="blocked",
                    exit_code=code,
                    reason="preset_test_immutable",
                    stdout=res.get("stdout") or "",
                    stderr=(
                        f"Anti-tamper protection active: Command modified test files ({tamper_reason}). "
                        "Test files are strictly immutable across all languages."
                    ),
                )
            post_hashes = _snapshot_non_test_hashes(self.workspace)
            deleted = [rel for rel in pre_hashes if rel not in post_hashes]
            if deleted and any(rel.startswith("src/") or ("/" not in rel and rel.endswith(".py")) for rel in deleted):
                return TerminalObservation(
                    action_type="command",
                    status="blocked",
                    exit_code=code,
                    reason="workspace_destruction_detected",
                    stdout=res.get("stdout") or "",
                    stderr=f"Integrity protection active: Command deleted core workspace source files ({', '.join(deleted[:5])}).",
                )
            changed = [rel for rel, digest in post_hashes.items() if pre_hashes.get(rel) != digest]
            if changed:
                for rel in changed:
                    if rel not in self.command_modified_files:
                        self.command_modified_files.append(rel)
                self.last_command_mod_turn = len(self.steps) + 1
            return TerminalObservation(
                action_type="command",
                status=status,
                exit_code=code,
                stdout=res.get("stdout") or "",
                stderr=res.get("stderr") or "",
            )
        except (OSError, ValueError, RuntimeError, TypeError, KeyError, AttributeError, subprocess.SubprocessError) as ex:
            return TerminalObservation(action_type="command", status="error", reason="command_execution_error", stderr=str(ex))

    def _record_step(self, action: TerminalAction, observation: TerminalObservation, hexagram_code: int) -> None:
        step = TerminalStep(
            turn_index=len(self.steps) + 1,
            action=action,
            observation=observation,
            hexagram_code=hexagram_code,
            timestamp_ns=time.time_ns(),
        )
        self.steps.append(step)

    def render_turn_prompt(self, *, include_fault_hints: bool = True) -> str:
        """Formats the prompt for the next turn, providing history, observations, and symbols."""
        return _render_terminal_prompt(self, include_fault_hints=include_fault_hints)


def _render_terminal_prompt(session: TerminalSession, *, include_fault_hints: bool = True) -> str:
    sections: list[str] = [
        "You are the OneCode Autonomous Terminal Agent in an active exploration loop.",
        f"User Task: {session.task}",
        f"Current Turn: {len(session.steps) + 1} of {session.max_turns}",
        "",
        "Available Actions (return strict JSON object with 'action_type'):",
        "1. Command: {\"action_type\":\"command\", \"command\":[\"pytest\", \"-k\", \"...\"], \"explanation\":\"...\"}",
        "2. Read File: {\"action_type\":\"read_file\", \"path\":\"src/...\", \"start_line\":1, \"end_line\":100, \"explanation\":\"...\"}",
        "3. Write File: {\"action_type\":\"write_file\", \"path\":\"src/...\", \"content\":\"...\", \"explanation\":\"...\"}",
        "4. Patch: {\"action_type\":\"patch\", \"path\":\"src/...\", \"search_block\":\"<exact>\", \"replace_block\":\"<fixed>\", \"explanation\":\"...\"}",
        "5. Finish: {\"action_type\":\"finish\", \"explanation\":\"Verification passed and all criteria satisfied.\"}",
        "",
        "Rules & Policies:",
        "- Anti-tamper: All test files (tests/, *_test.go, *.test.ts, *.spec.js, etc.) are strictly immutable. Only patch non-test implementation source files.",
        "- Verification: Use 'command' to run existing tests to verify your hypotheses before and after patching.",
        "- Efficiency: Use 'write_file' to create new files. Once a file exists, use 'patch' for concise, targeted fixes rather than rewriting entire files.",
        "- Focus: When confident that the tests pass and the solution is complete, submit 'finish'.",
    ]

    if include_fault_hints:
        recent_errs = "\n".join(
            s.observation.stderr + "\n" + s.observation.stdout
            for s in session.steps[-3:]
        )
        if recent_errs:
            if session._symbol_index is None:
                session._symbol_index = WorkspaceSymbolIndex(session.workspace)
            else:
                session._symbol_index.refresh()
            locator = SymbolLocator(session.workspace, index=session._symbol_index)
            locs = locator.locate_fault(recent_errs, max_candidates=3)
            if locs:
                sections.append("")
                sections.append("Fault Localization Hints (AST Symbol Locator):")
                for loc in locs:
                    if not loc.is_test_file:
                        sections.append(
                            f"- Recommended target: '{loc.file_path}', symbol '{loc.symbol_name}' "
                            f"(lines {loc.line_start}-{loc.line_end}, confidence {loc.confidence:.2f}). Reason: {loc.reason}"
                        )

    directive = _status_directive(
        session.steps,
        session.workspace,
        max_turns=session.max_turns,
        command_modified_files=session.command_modified_files,
        last_command_mod_turn=session.last_command_mod_turn,
    )
    if directive:
        sections.append("")
        sections.append(directive)

    if session.steps:
        sections.append("")
        sections.append("Execution History:")
        for i, s in enumerate(session.steps[-6:]):
            is_latest = (i == len(session.steps[-6:]) - 1)
            act = s.action
            obs = s.observation
            sections.append(f"Turn {s.turn_index}: Action={act.action_type} Status={obs.status}")
            if act.action_type == "command":
                sections.append(f"  Command: {' '.join(act.command)} (exit_code={obs.exit_code})")
                if obs.stdout:
                    sections.append(f"  Stdout tail: {obs.stdout[-1200:].strip()}")
                if obs.stderr:
                    sections.append(f"  Stderr tail: {obs.stderr[-1200:].strip()}")
            elif act.action_type in {"patch", "write_file"}:
                sections.append(f"  {act.action_type.capitalize()} path={act.path} result={obs.output or obs.stderr}")
            elif act.action_type == "read_file":
                sections.append(f"  Read {act.path}")
                if obs.stderr:
                    sections.append(f"  Stderr: {obs.stderr[-1200:].strip()}")
                if obs.output:
                    preview_limit = 4000 if is_latest else 400
                    sections.append(f"  Content:\n{obs.output[:preview_limit]}")

    sections.append("")
    sections.append("Respond with a single JSON object containing your next action.")
    return "\n".join(sections)


def run_terminal_session(
    task: str,
    workspace: Path,
    provider: Any,
    *,
    max_turns: int = 15,
    require_modification: bool = True,
    approval_mode: str = "strict",
    execution_approval: Callable[[TerminalAction], bool] | None = None,
    auto_approved_for_eval: bool = False,
    on_step: Callable[[TerminalStep], None] | None = None,
    execution_scope: ExecutionScope | str = ExecutionScope.FULL_TERMINAL,
    rollback_on_failure: bool = False,
) -> dict[str, Any]:
    """Runs a multi-turn open-ended terminal exploration loop until finish or turn exhaustion."""
    session = TerminalSession(
        workspace,
        task,
        max_turns=max_turns,
        require_modification=require_modification,
        approval_mode=approval_mode,
        execution_approval=execution_approval,
        auto_approved_for_eval=auto_approved_for_eval,
        execution_scope=execution_scope,
        rollback_on_failure=rollback_on_failure,
    )

    def _finalize(res: dict[str, Any]) -> dict[str, Any]:
        res["command_modified_files"] = list(session.command_modified_files)
        if rollback_on_failure and res.get("status") != "completed":
            res["rollback"] = session.rollback()
        return res

    for turn in range(max_turns):
        prompt = session.render_turn_prompt()
        response_text: str | None = None
        last_provider_error: Exception | None = None
        for attempt in range(2):
            try:
                response_text = provider.complete(prompt) if hasattr(provider, "complete") else str(provider(prompt))
                break
            except Exception as ex:
                last_provider_error = ex
                if attempt == 0:
                    time.sleep(1.0)
        if response_text is None:
            return _finalize({
                "status": "halted",
                "reason": "provider_error",
                "error": str(last_provider_error),
                "turns_completed": len(session.steps),
                "steps": [s.to_dict() for s in session.steps],
                "approval_mode": session.approval_mode,
                "auto_approved_for_eval": session.auto_approved_for_eval,
                "approved_actions_count": session.approved_actions_count,
                "blocked_approvals_count": session.blocked_approvals_count,
                "execution_scope": session.execution_scope.value,
            })

        # Parse JSON action from response
        action = _parse_model_action(response_text)
        obs = session.execute_action(action)
        if on_step is not None and session.steps:
            on_step(session.steps[-1])

        if session.is_finished:
            return _finalize({
                "status": "completed",
                "reason": "agent_finished",
                "explanation": session.finish_explanation,
                "turns_completed": len(session.steps),
                "steps": [s.to_dict() for s in session.steps],
                "approval_mode": session.approval_mode,
                "auto_approved_for_eval": session.auto_approved_for_eval,
                "approved_actions_count": session.approved_actions_count,
                "blocked_approvals_count": session.blocked_approvals_count,
                "execution_scope": session.execution_scope.value,
            })

        if obs.reason == "preset_test_immutable":
            return _finalize({
                "status": "halted",
                "reason": "preset_test_immutable",
                "turns_completed": len(session.steps),
                "steps": [s.to_dict() for s in session.steps],
                "approval_mode": session.approval_mode,
                "auto_approved_for_eval": session.auto_approved_for_eval,
                "approved_actions_count": session.approved_actions_count,
                "blocked_approvals_count": session.blocked_approvals_count,
                "execution_scope": session.execution_scope.value,
            })

        if obs.status == "halted":
            return _finalize({
                "status": "halted",
                "reason": obs.reason or "stagnation_halt",
                "turns_completed": len(session.steps),
                "steps": [s.to_dict() for s in session.steps],
                "approval_mode": session.approval_mode,
                "auto_approved_for_eval": session.auto_approved_for_eval,
                "approved_actions_count": session.approved_actions_count,
                "blocked_approvals_count": session.blocked_approvals_count,
                "execution_scope": session.execution_scope.value,
            })

    return _finalize({
        "status": "halted",
        "reason": "turn_limit_exhausted",
        "turns_completed": len(session.steps),
        "steps": [s.to_dict() for s in session.steps],
        "approval_mode": session.approval_mode,
        "auto_approved_for_eval": session.auto_approved_for_eval,
        "approved_actions_count": session.approved_actions_count,
        "blocked_approvals_count": session.blocked_approvals_count,
        "execution_scope": session.execution_scope.value,
    })


def _parse_model_action(text: str) -> TerminalAction:
    """Robustly extracts JSON action from raw model text."""
    decoder = json.JSONDecoder()
    clean_text = text.strip()
    match = re.search(r"\{[\s\S]*\}", clean_text)
    if match:
        idx = match.start()
        try:
            parsed, _ = decoder.raw_decode(clean_text[idx:])
            if isinstance(parsed, dict):
                return TerminalAction.from_dict(parsed)
        except json.JSONDecodeError:
            pass

    return TerminalAction(
        action_type="command",
        command=("git", "status"),
        explanation="Default fallback command after JSON parse error.",
    )


def run_phased_terminal_session(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Runs a two-phase terminal exploration loop (Plan -> Execute/Verify)."""
    from onecode.kernel.phased_terminal import run_phased_terminal_session as _impl

    return _impl(*args, **kwargs)

