"""Open-ended multi-step terminal loop for SWE-bench exploration and interactive problem solving.

This module implements a stateful terminal agent session:
1. Multi-turn interactive execution: the model observes shell output, reads files,
   applies surgical patches, runs exploration commands, and re-tests.
2. Anti-tamper protection: strict isolation of immutable preset test paths.
3. Stagnation and loop governance: detects repeated command failures (陀罗暗滞)
   and forces strategy pivoting.
4. Fault localization coupling: integrates SymbolLocator to direct exploration
   directly to true implementation modules.
"""
from __future__ import annotations

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

from onecode.kernel.execution_tools import ToolRegistry, default_tool_registry
from onecode.kernel.path_guard import PathGuard
from onecode.kernel.symbol_locator import SymbolLocator, is_any_test_path

_TEST_PATH_PAT = r"(?:tests?/|test/|__tests__/|spec/|[^\s]*_test\.[a-z0-9]+|[^\s]*\.(?:test|spec)\.[a-z0-9]+|[^\s]*tests\.rs\b|[^\s]*test_\w+\.(?:py|pyw|rb)\b)"

_FORBIDDEN_TEST_CMD_PATTERNS = (
    re.compile(rf"\b(?:rm|unlink|truncate|shred)\s+.*{_TEST_PATH_PAT}", re.IGNORECASE),
    re.compile(rf"\bsed\s+.*-i.*{_TEST_PATH_PAT}", re.IGNORECASE),
    re.compile(rf">\s*{_TEST_PATH_PAT}", re.IGNORECASE),
    re.compile(rf">>\s*{_TEST_PATH_PAT}", re.IGNORECASE),
    re.compile(rf"\btee\s+.*{_TEST_PATH_PAT}", re.IGNORECASE),
    re.compile(rf"\b(?:cp|mv)\s+.*{_TEST_PATH_PAT}\s*$", re.IGNORECASE),
)

_DESTRUCTIVE_CMDS = frozenset({"rm", "unlink", "truncate", "shred", "sed", "tee"})
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


def _unproven_write_target(script: str) -> str:
    """Block a mutating interpreter script whose destination is not a static literal path."""
    if not script or not _script_mutates_files(script):
        return ""
    for match in _WRITE_CALL.finditer(script):
        argument = _first_call_argument(script, match.end() - 1)
        if argument is None:
            continue
        stripped = argument.strip()
        if stripped.startswith(("'''", '"""', "'", '"')):
            continue
        return "a computed path"
    return ""


def _spliced_test_target(script: str) -> str:
    """Return a test path assembled inside an interpreter script, or an empty string."""
    if not script or not _script_mutates_files(script):
        return ""
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


def _source_write_target(workspace: Path, source: str, seen: set[Path], depth: int = 0) -> str:
    """Return a test write hidden in this source or in a workspace module it imports."""
    if depth > 6:
        return "a computed execution"
    found = _spliced_test_target(source)
    if found:
        return found
    executed = _dynamic_execution_target(workspace, source, seen, depth)
    if executed:
        return executed
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
        nested = _source_write_target(workspace, text, seen, depth)
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
    return _source_write_target(workspace, text, {path})


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
    return _source_write_target(workspace, text, seen, depth)


def _execution_argument_target(
    workspace: Path,
    call: str,
    argument: str,
    seen: set[Path] | None = None,
    depth: int = 0,
) -> str:
    literal = _sole_string_literal(argument)
    if literal is not None:
        if call == "run_module":
            return _module_flag_write_target(workspace, literal)
        if call in _FILE_EXECUTION_CALLS:
            return _file_write_target(workspace, literal, seen, depth)
        return _source_write_target(workspace, literal, set() if seen is None else seen, depth)
    paths = [text for _start, _end, text in _string_literals(argument) if text.endswith(".py")]
    if not paths:
        return "a computed execution"
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
) -> str:
    """Block a loader reached through getattr, including a name joined from pieces."""
    for match in re.finditer(r"(?<![\w])getattr\s*\(", script):
        parsed = _call_arguments(script, match.end() - 1)
        if parsed is None or len(parsed[0]) < 2:
            return "a computed execution"
        arguments, end = parsed
        name = _static_literal_text(arguments[1])
        rest = script[end:].lstrip()
        if name is None:
            if rest.startswith("("):
                return "a computed execution"
            continue
        arg_index = dict(_EXECUTION_CALLS).get(name)
        if arg_index is None or not rest.startswith("("):
            continue
        open_paren = end + (len(script[end:]) - len(rest))
        invoked = _call_arguments(script, open_paren)
        if invoked is None or arg_index >= len(invoked[0]):
            return "a computed execution"
        found = _execution_argument_target(workspace, name, invoked[0][arg_index], seen, depth)
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


def _shell_command_text(argv: tuple[str, ...]) -> str:
    if not argv or posixpath.basename(argv[0]).lower() not in _SHELLS:
        return ""
    for index, token in enumerate(argv):
        if token == "-c" and index + 1 < len(argv):
            return argv[index + 1]
    return ""


def _scan_shell_script(workspace: Path, script: str, seen: set[Path] | None, depth: int) -> str:
    """Block a shell -c script that launches a Python writer."""
    if depth > 6:
        return "a computed execution"
    for segment in (part.strip() for part in re.split(r"(?:&&|\|\||;|\n)", script)):
        if not segment:
            continue
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
        nested = _shell_command_text(tuple(tokens))
        if nested:
            found = _scan_shell_script(workspace, nested, seen, depth + 1)
            if found:
                return found
    return ""


def _subprocess_write_target(
    workspace: Path,
    script: str,
    seen: set[Path] | None,
    depth: int,
) -> str:
    """Block an interpreter launched through subprocess or os.system."""
    if depth > 6:
        return "a computed execution"
    for match in _PROCESS_CALL.finditer(script):
        parsed = _call_arguments(script, match.end() - 1)
        if parsed is None or not parsed[0] or not parsed[0][0].strip():
            return "a computed execution"
        argv = _command_tokens(parsed[0][0])
        if argv is None:
            return "a computed execution"
        if not argv:
            continue
        if _is_python_command(tuple(argv)):
            found = _workspace_python_write_target(workspace, tuple(argv), seen, depth + 1)
        else:
            shell_text = _shell_command_text(tuple(argv))
            found = _scan_shell_script(workspace, shell_text, seen, depth + 1) if shell_text else ""
        if found:
            return found
    return ""


def _dynamic_execution_target(
    workspace: Path,
    script: str,
    seen: set[Path] | None = None,
    depth: int = 0,
) -> str:
    """Block exec, runpy, and file loaders whose target can write a test file."""
    for name, arg_index in _EXECUTION_CALLS:
        pattern = rf"(?<![\w]){name}\s*\("
        for match in re.finditer(pattern, script):
            parsed = _call_arguments(script, match.end() - 1)
            if parsed is None or arg_index >= len(parsed[0]):
                return "a computed execution"
            found = _execution_argument_target(workspace, name, parsed[0][arg_index], seen, depth)
            if found:
                return found
    launched = _subprocess_write_target(workspace, script, seen, depth)
    if launched:
        return launched
    return _getattr_execution_target(workspace, script, seen, depth)


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
    return _source_write_target(workspace, text, seen, depth)


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
    action_type: str  # "command", "patch", "read_file", "finish"
    command: tuple[str, ...] = field(default_factory=tuple)
    path: str = ""
    search_block: str = ""
    replace_block: str = ""
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
        cmd = data.get("command") or data.get("cmd") or data.get("argv") or []
        if isinstance(cmd, str):
            cmd = cmd.split()
        elif not isinstance(cmd, (list, tuple)):
            cmd = []

        return cls(
            action_type=action_type,
            command=tuple(str(x) for x in cmd),
            path=str(data.get("path") or "").strip(),
            search_block=str(data.get("search_block") or ""),
            replace_block=str(data.get("replace_block") or ""),
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
    ) -> None:
        self.workspace = workspace.resolve()
        self.task = task
        self.max_turns = max_turns
        self.tool_registry = tool_registry or default_tool_registry()
        self.require_modification = require_modification
        self.approval_mode = approval_mode
        self.execution_approval = execution_approval
        self.auto_approved_for_eval = auto_approved_for_eval
        self.approved_actions_count = 0
        self.blocked_approvals_count = 0
        self.steps: list[TerminalStep] = []
        self.is_finished = False
        self.finish_explanation = ""
        self.last_command_signature = ""
        self.consecutive_stalls = 0
        self.last_read_signature = ""
        self.consecutive_read_stalls = 0
        self.initial_test_bytes: dict[str, bytes] = {}
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
        for rel, orig_hash in self.initial_test_hashes.items():
            target = self.workspace / rel
            if not target.is_file():
                return f"Test file '{rel}' was deleted"
            try:
                current_hash = hashlib.sha256(target.read_bytes()).hexdigest()
            except OSError as ex:
                return f"Test file '{rel}' could not be read: {ex}"
            if current_hash != orig_hash:
                return f"Test file '{rel}' was modified (SHA-256 hash mismatch)"
        for path in self.workspace.rglob("*"):
            if not path.is_file():
                continue
            try:
                rel = path.relative_to(self.workspace).as_posix()
            except ValueError:
                continue
            if rel not in self.initial_test_hashes and is_any_test_path(rel):
                return f"New test file '{rel}' was created"
        return ""

    def restore_test_files(self) -> list[str]:
        """Put every snapshotted test file back and remove test files created during the session."""
        restored: list[str] = []
        for rel, payload in self.initial_test_bytes.items():
            target = self.workspace / rel
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
        for path in list(self.workspace.rglob("*")):
            if not path.is_file():
                continue
            try:
                rel = path.relative_to(self.workspace).as_posix()
            except ValueError:
                continue
            if rel in self.initial_test_hashes or not is_any_test_path(rel):
                continue
            path.unlink()
            restored.append(rel)
        return restored

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
        found = _interpreter_test_target(cmd_tokens)
        if found:
            return found
        found = _workspace_python_write_target(self.workspace, cmd_tokens)
        if found:
            return found
        shell_text = _shell_command_text(cmd_tokens)
        if shell_text:
            return _scan_shell_script(self.workspace, shell_text, set(), 0)
        return ""

    def is_command_tampering(self, cmd_tokens: tuple[str, ...]) -> bool:
        return bool(self.command_tamper_target(cmd_tokens))

    def execute_action(self, action: TerminalAction) -> TerminalObservation:
        """Executes an action under sandbox security policies and records the observation."""
        # Immutable security invariant: test anti-tamper is always enforced first
        if action.action_type == "patch" and is_any_test_path(action.path):
            obs = TerminalObservation(
                action_type="patch",
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

        # Approval gate policy check
        if self.approval_mode == "strict" and action.action_type in {"patch", "command"}:
            if self.execution_approval is not None:
                if not self.execution_approval(action):
                    self.blocked_approvals_count += 1
                    obs = TerminalObservation(
                        action_type=action.action_type,
                        status="blocked",
                        reason="approval_denied",
                        stderr=f"Approval denied for {action.action_type}: rejected by execution_approval callback.",
                    )
                    self._record_step(action, obs, hexagram_code=39)
                    return obs
                self.approved_actions_count += 1
            elif not self.auto_approved_for_eval:
                self.blocked_approvals_count += 1
                obs = TerminalObservation(
                    action_type=action.action_type,
                    status="blocked",
                    reason="approval_required",
                    stderr=f"Action '{action.action_type}' blocked: approval_mode is strict but no execution_approval callback provided.",
                )
                self._record_step(action, obs, hexagram_code=39)
                return obs
            else:
                self.approved_actions_count += 1

        if action.action_type == "finish":
            intact, tamper_reason = self.verify_test_files_integrity()
            if not intact:
                obs = TerminalObservation(
                    action_type="finish",
                    status="blocked",
                    reason="preset_test_immutable",
                    stderr=f"Cannot finish: {tamper_reason}. Test files are strictly immutable across all languages.",
                )
                self._record_step(action, obs, hexagram_code=40)
                return obs

            has_modified = any(s.action.action_type == "patch" and s.observation.status == "ok" for s in self.steps)
            if self.require_modification and not has_modified:
                obs = TerminalObservation(
                    action_type="finish",
                    status="error",
                    reason="unmodified_workspace",
                    stderr="Cannot finish: no implementation files have been modified or patched yet. First inspect files, apply patches, and verify.",
                )
                self._record_step(action, obs, hexagram_code=39)
                return obs
            self.is_finished = True
            self.finish_explanation = action.explanation or "Task completed by agent."
            obs = TerminalObservation(
                action_type="finish",
                status="ok",
                output=self.finish_explanation,
            )
            self._record_step(action, obs, hexagram_code=63)
            return obs

        if action.action_type == "patch":
            self.last_command_signature = ""
            self.consecutive_stalls = 0
            self.last_read_signature = ""
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
            self.consecutive_read_stalls = 0
            obs = self._handle_command(action)
            hex_code = 63 if obs.status == "ok" else (40 if obs.status == "blocked" else 39)
            self._record_step(action, obs, hexagram_code=hex_code)
            return obs

        obs = TerminalObservation(
            action_type=action.action_type,
            status="error",
            reason="unknown_action_type",
            stderr=f"Unknown action_type '{action.action_type}'. Valid types: command, patch, read_file, finish.",
        )
        self._record_step(action, obs, hexagram_code=39)
        return obs

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
        tool = self.tool_registry.get("patch_text")
        if tool is None:
            return TerminalObservation(action_type="patch", status="error", reason="tool_not_found", stderr="patch_text tool is missing.")
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
        if PathGuard.is_sensitive_read_path(Path(action.path)):
            return TerminalObservation(action_type="read_file", status="blocked", reason="sensitive_read_denied", stderr="Access to sensitive path denied.")
        target = self.workspace / action.path
        if not target.is_file():
            return TerminalObservation(action_type="read_file", status="error", reason="file_not_found", stderr=f"File '{action.path}' does not exist.")
        read_sig = f"{action.path}:{action.start_line or 1}:{action.end_line or 0}"
        if read_sig == self.last_read_signature:
            self.consecutive_read_stalls += 1
            if self.consecutive_read_stalls >= 2:
                return TerminalObservation(
                    action_type="read_file",
                    status="halted",
                    reason="stagnation_loop",
                    stderr=f"Stagnation warning (陀罗暗滞·化权破滞): Detected identical repeated read of '{action.path}'. Do not repeat the same read; run verification tests with 'command' or submit 'finish'.",
                )
        else:
            self.last_read_signature = read_sig
            self.consecutive_read_stalls = 0
        try:
            lines = target.read_text(encoding="utf-8").splitlines()
            total_lines = len(lines)
            start = max(1, action.start_line or 1)
            end = min(total_lines, action.end_line or (start + 200))
            selected = lines[start - 1 : end]
            numbered = [f"{i + start:4d} | {line}" for i, line in enumerate(selected)]
            out = f"## {action.path} (lines {start}-{end} of {total_lines})\n" + "\n".join(numbered)
            return TerminalObservation(action_type="read_file", status="ok", output=out)
        except (OSError, UnicodeError, ValueError) as ex:
            return TerminalObservation(action_type="read_file", status="error", reason="read_error", stderr=str(ex))

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

        cmd_sig = " ".join(action.command)
        if cmd_sig == self.last_command_signature and self.steps and self.steps[-1].observation.status == "error":
            self.consecutive_stalls += 1
            if self.consecutive_stalls >= 2:
                return TerminalObservation(
                    action_type="command",
                    status="halted",
                    reason="stagnation_loop",
                    stderr="Stagnation warning (陀罗暗滞·化权破滞): Detected identical repeated failing command. Do not repeat the same command; inspect diagnostics and pivot your approach.",
                )
        else:
            self.last_command_signature = cmd_sig
            self.consecutive_stalls = 0

        tool = self.tool_registry.get("run_command")
        if tool is None:
            return TerminalObservation(action_type="command", status="error", reason="tool_not_found", stderr="run_command tool is missing.")
        try:
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
        sections: list[str] = [
            "You are the OneCode Autonomous Terminal Agent in an active exploration loop.",
            f"User Task: {self.task}",
            f"Current Turn: {len(self.steps) + 1} of {self.max_turns}",
            "",
            "Available Actions (return strict JSON object with 'action_type'):",
            "1. Command: {\"action_type\":\"command\", \"command\":[\"pytest\", \"-k\", \"...\"], \"explanation\":\"...\"}",
            "2. Read File: {\"action_type\":\"read_file\", \"path\":\"src/...\", \"start_line\":1, \"end_line\":100, \"explanation\":\"...\"}",
            "3. Patch: {\"action_type\":\"patch\", \"path\":\"src/...\", \"search_block\":\"<exact>\", \"replace_block\":\"<fixed>\", \"explanation\":\"...\"}",
            "4. Finish: {\"action_type\":\"finish\", \"explanation\":\"Verification passed and all criteria satisfied.\"}",
            "",
            "Rules & Policies:",
            "- Anti-tamper: All test files (tests/, *_test.go, *.test.ts, *.spec.js, etc.) are strictly immutable. Only patch non-test implementation source files.",
            "- Verification: Use 'command' to run existing tests to verify your hypotheses before and after patching.",
            "- Focus: When confident that the tests pass and the solution is complete, submit 'finish'.",
        ]

        if include_fault_hints:
            recent_errs = "\n".join(
                s.observation.stderr + "\n" + s.observation.stdout
                for s in self.steps[-3:]
            )
            if recent_errs:
                locator = SymbolLocator(self.workspace)
                locs = locator.locate_fault(recent_errs, max_candidates=3)
                if locs:
                    sections.append("")
                    sections.append("Fault Localization Hints (天相印绶·符号溯源定位):")
                    for loc in locs:
                        if not loc.is_test_file:
                            sections.append(
                                f"- Recommended target: '{loc.file_path}', symbol '{loc.symbol_name}' "
                                f"(lines {loc.line_start}-{loc.line_end}, confidence {loc.confidence:.2f}). Reason: {loc.reason}"
                            )

        has_applied_patch = any(s.action.action_type == "patch" and s.observation.status == "ok" for s in self.steps)
        if has_applied_patch:
            sections.append("")
            sections.append("Status Directive: You have already applied a code patch. Avoid redundant re-reading of the same file. Proceed to run verification tests with 'command' or submit 'finish' to complete the task.")

        if self.steps:
            sections.append("")
            sections.append("Execution History:")
            for i, s in enumerate(self.steps[-6:]):
                is_latest = (i == len(self.steps[-6:]) - 1)
                act = s.action
                obs = s.observation
                sections.append(f"Turn {s.turn_index}: Action={act.action_type} Status={obs.status}")
                if act.action_type == "command":
                    sections.append(f"  Command: {' '.join(act.command)} (exit_code={obs.exit_code})")
                    if obs.stdout:
                        sections.append(f"  Stdout tail: {obs.stdout[-1200:].strip()}")
                    if obs.stderr:
                        sections.append(f"  Stderr tail: {obs.stderr[-1200:].strip()}")
                elif act.action_type == "patch":
                    sections.append(f"  Patch path={act.path} result={obs.output or obs.stderr}")
                elif act.action_type == "read_file":
                    sections.append(f"  Read {act.path}")
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
    )

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
            return {
                "status": "halted",
                "reason": "provider_error",
                "error": str(last_provider_error),
                "turns_completed": len(session.steps),
                "steps": [s.to_dict() for s in session.steps],
                "approval_mode": session.approval_mode,
                "auto_approved_for_eval": session.auto_approved_for_eval,
                "approved_actions_count": session.approved_actions_count,
                "blocked_approvals_count": session.blocked_approvals_count,
            }

        # Parse JSON action from response
        action = _parse_model_action(response_text)
        obs = session.execute_action(action)
        if on_step is not None and session.steps:
            on_step(session.steps[-1])

        if session.is_finished:
            return {
                "status": "completed",
                "reason": "agent_finished",
                "explanation": session.finish_explanation,
                "turns_completed": len(session.steps),
                "steps": [s.to_dict() for s in session.steps],
                "approval_mode": session.approval_mode,
                "auto_approved_for_eval": session.auto_approved_for_eval,
                "approved_actions_count": session.approved_actions_count,
                "blocked_approvals_count": session.blocked_approvals_count,
            }

        if obs.reason == "preset_test_immutable":
            return {
                "status": "halted",
                "reason": "preset_test_immutable",
                "turns_completed": len(session.steps),
                "steps": [s.to_dict() for s in session.steps],
                "approval_mode": session.approval_mode,
                "auto_approved_for_eval": session.auto_approved_for_eval,
                "approved_actions_count": session.approved_actions_count,
                "blocked_approvals_count": session.blocked_approvals_count,
            }

        if obs.status == "halted":
            return {
                "status": "halted",
                "reason": obs.reason or "stagnation_halt",
                "turns_completed": len(session.steps),
                "steps": [s.to_dict() for s in session.steps],
                "approval_mode": session.approval_mode,
                "auto_approved_for_eval": session.auto_approved_for_eval,
                "approved_actions_count": session.approved_actions_count,
                "blocked_approvals_count": session.blocked_approvals_count,
            }

    return {
        "status": "halted",
        "reason": "turn_limit_exhausted",
        "turns_completed": len(session.steps),
        "steps": [s.to_dict() for s in session.steps],
        "approval_mode": session.approval_mode,
        "auto_approved_for_eval": session.auto_approved_for_eval,
        "approved_actions_count": session.approved_actions_count,
        "blocked_approvals_count": session.blocked_approvals_count,
    }


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
