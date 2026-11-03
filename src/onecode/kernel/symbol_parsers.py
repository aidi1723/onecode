"""Multi-language symbol scanners and stack trace parsers (Go, TypeScript/JavaScript, Rust).

Provides standard library regex-driven symbol extraction and stack trace analysis
for Go, TypeScript, JavaScript, and Rust codebases without third-party dependencies.
"""
from __future__ import annotations

import posixpath
import re
from typing import Any


def find_closing_brace(lines: list[str], start_line_idx: int) -> int:
    """Finds the 1-based line index where the matching brace closes."""
    depth = 0
    found_open = False
    for i in range(start_line_idx, len(lines)):
        line = lines[i]
        # Ignore comments
        stripped = line.split("//")[0].split("#")[0]
        for ch in stripped:
            if ch == "{":
                depth += 1
                found_open = True
            elif ch == "}":
                depth -= 1
                if found_open and depth <= 0:
                    return i + 1
    return len(lines) if found_open else (start_line_idx + 1)


# ---------------------------------------------------------------------------
# Go Scanner
# ---------------------------------------------------------------------------

_GO_FUNC_RE = re.compile(
    r"^func\s+(?:\((?:\w+\s+)?\*?(?P<receiver>\w+)\)\s+)?(?P<name>[A-Z]\w*|[a-z]\w*)\s*\("
)
_GO_TYPE_RE = re.compile(
    r"^type\s+(?P<name>\w+)\s+(?P<kind>struct|interface|\w+)"
)
_GO_IMPORT_SINGLE_RE = re.compile(
    r'^import\s+(?:(?P<alias>\w+)\s+)?["\'](?P<mod>[^"\']+)["\']'
)
_GO_IMPORT_BLOCK_LINE_RE = re.compile(
    r'^\s*(?:(?P<alias>\w+)\s+)?["\'](?P<mod>[^"\']+)["\']'
)


class GoSymbolScanner:
    """Scans Go (.go) source files for functions, methods, types, and imports."""

    @staticmethod
    def scan(content: str, rel_path: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        lines = content.splitlines()
        symbols: list[dict[str, Any]] = []
        imports: dict[str, Any] = {}

        in_import_block = False
        for idx, line in enumerate(lines):
            stripped = line.strip()

            # Handle imports
            if stripped == "import (":
                in_import_block = True
                continue
            if in_import_block:
                if stripped == ")":
                    in_import_block = False
                    continue
                match = _GO_IMPORT_BLOCK_LINE_RE.match(stripped)
                if match:
                    mod = match.group("mod")
                    alias = match.group("alias") or posixpath.basename(mod)
                    imports[alias] = {"module": mod, "symbol": "", "alias": alias}
                continue

            single_import = _GO_IMPORT_SINGLE_RE.match(stripped)
            if single_import:
                mod = single_import.group("mod")
                alias = single_import.group("alias") or posixpath.basename(mod)
                imports[alias] = {"module": mod, "symbol": "", "alias": alias}
                continue

            # Handle functions and methods
            func_match = _GO_FUNC_RE.match(stripped)
            if func_match:
                receiver = func_match.group("receiver")
                name = func_match.group("name")
                end_line = find_closing_brace(lines, idx)
                kind = "method" if receiver else "function"
                symbols.append({
                    "name": name,
                    "kind": kind,
                    "file_path": rel_path,
                    "line_start": idx + 1,
                    "line_end": end_line,
                    "class_name": receiver,
                    "docstring": None,
                })
                continue

            # Handle types (struct / interface)
            type_match = _GO_TYPE_RE.match(stripped)
            if type_match:
                name = type_match.group("name")
                end_line = find_closing_brace(lines, idx)
                symbols.append({
                    "name": name,
                    "kind": "class",
                    "file_path": rel_path,
                    "line_start": idx + 1,
                    "line_end": end_line,
                    "class_name": None,
                    "docstring": None,
                })

        return symbols, imports


# ---------------------------------------------------------------------------
# TypeScript / JavaScript Scanner
# ---------------------------------------------------------------------------

_TS_CLASS_RE = re.compile(
    r"^(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+(?P<name>\w+)"
)
_TS_METHOD_RE = re.compile(
    r"^\s*(?:public\s+|private\s+|protected\s+|static\s+)?(?:async\s+)?(?P<name>[a-zA-Z_]\w*)\s*\([^)]*\)\s*(?::\s*[^{]+)?\s*\{"
)
_TS_FUNC_RE = re.compile(
    r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(?P<name>[a-zA-Z_]\w*)\s*\("
)
_TS_ARROW_FUNC_RE = re.compile(
    r"^(?:export\s+)?(?:const|let|var)\s+(?P<name>[a-zA-Z_]\w*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[a-zA-Z_]\w*)(?:\s*:\s*[^{=>]+)?\s*=>"
)
_TS_TYPE_RE = re.compile(
    r"^(?:export\s+)?(?:interface|type)\s+(?P<name>[a-zA-Z_]\w*)"
)
_TS_IMPORT_NAMED_RE = re.compile(
    r"import\s+\{\s*(?P<symbols>[^}]+)\s*\}\s+from\s+['\"](?P<mod>[^'\"]+)['\"]"
)
_TS_IMPORT_DEFAULT_RE = re.compile(
    r"import\s+(?P<name>[a-zA-Z_]\w*)\s+from\s+['\"](?P<mod>[^'\"]+)['\"]"
)
_TS_IMPORT_STAR_RE = re.compile(
    r"import\s+\*\s+as\s+(?P<alias>[a-zA-Z_]\w*)\s+from\s+['\"](?P<mod>[^'\"]+)['\"]"
)


class TypeScriptSymbolScanner:
    """Scans TypeScript and JavaScript source files for functions, classes, methods, and imports."""

    @staticmethod
    def scan(content: str, rel_path: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        lines = content.splitlines()
        symbols: list[dict[str, Any]] = []
        imports: dict[str, Any] = {}

        current_class: str | None = None
        class_end_line = 0

        for idx, line in enumerate(lines):
            line_no = idx + 1
            if current_class and line_no > class_end_line:
                current_class = None

            stripped = line.strip()

            # Imports
            star_match = _TS_IMPORT_STAR_RE.search(stripped)
            if star_match:
                alias = star_match.group("alias")
                imports[alias] = {"module": star_match.group("mod"), "symbol": "", "alias": alias}
                continue

            named_match = _TS_IMPORT_NAMED_RE.search(stripped)
            if named_match:
                mod = named_match.group("mod")
                for s in named_match.group("symbols").split(","):
                    s = s.strip()
                    if not s:
                        continue
                    if " as " in s:
                        orig, as_name = s.split(" as ", 1)
                        imports[as_name.strip()] = {"module": mod, "symbol": orig.strip(), "alias": as_name.strip()}
                    else:
                        imports[s] = {"module": mod, "symbol": s, "alias": s}
                continue

            def_match = _TS_IMPORT_DEFAULT_RE.search(stripped)
            if def_match:
                name = def_match.group("name")
                imports[name] = {"module": def_match.group("mod"), "symbol": "", "alias": name}
                continue

            # Class definition
            class_match = _TS_CLASS_RE.match(stripped)
            if class_match:
                current_class = class_match.group("name")
                class_end_line = find_closing_brace(lines, idx)
                symbols.append({
                    "name": current_class,
                    "kind": "class",
                    "file_path": rel_path,
                    "line_start": line_no,
                    "line_end": class_end_line,
                    "class_name": None,
                    "docstring": None,
                })
                continue

            # Method inside class
            if current_class and line_no <= class_end_line:
                method_match = _TS_METHOD_RE.match(line)
                if method_match:
                    name = method_match.group("name")
                    if name not in {"constructor", "if", "for", "while", "switch"}:
                        end_line = find_closing_brace(lines, idx)
                        symbols.append({
                            "name": name,
                            "kind": "method",
                            "file_path": rel_path,
                            "line_start": line_no,
                            "line_end": end_line,
                            "class_name": current_class,
                            "docstring": None,
                        })
                        continue

            # Top-level Function
            func_match = _TS_FUNC_RE.match(stripped)
            if func_match:
                name = func_match.group("name")
                end_line = find_closing_brace(lines, idx)
                symbols.append({
                    "name": name,
                    "kind": "function",
                    "file_path": rel_path,
                    "line_start": line_no,
                    "line_end": end_line,
                    "class_name": None,
                    "docstring": None,
                })
                continue

            # Arrow Function
            arrow_match = _TS_ARROW_FUNC_RE.match(stripped)
            if arrow_match:
                name = arrow_match.group("name")
                end_line = find_closing_brace(lines, idx)
                symbols.append({
                    "name": name,
                    "kind": "function",
                    "file_path": rel_path,
                    "line_start": line_no,
                    "line_end": end_line,
                    "class_name": None,
                    "docstring": None,
                })
                continue

            # Interface / Type
            type_match = _TS_TYPE_RE.match(stripped)
            if type_match:
                name = type_match.group("name")
                end_line = find_closing_brace(lines, idx)
                symbols.append({
                    "name": name,
                    "kind": "class",
                    "file_path": rel_path,
                    "line_start": line_no,
                    "line_end": end_line,
                    "class_name": None,
                    "docstring": None,
                })

        return symbols, imports


# ---------------------------------------------------------------------------
# Rust Scanner
# ---------------------------------------------------------------------------

_RS_FN_RE = re.compile(
    r"^(?:pub(?:\([^)]+\))?\s+)?(?:async\s+)?(?:const\s+)?(?:unsafe\s+)?(?:extern\s+[\"\w]+\s+)?fn\s+(?P<name>[a-zA-Z_]\w*)\s*(?:<[^>]+>)?\s*\("
)
_RS_STRUCT_RE = re.compile(
    r"^(?:pub(?:\([^)]+\))?\s+)?(?:struct|enum|trait)\s+(?P<name>[a-zA-Z_]\w*)"
)
_RS_IMPL_RE = re.compile(
    r"^impl(?:\s*<[^>]+>)?\s*(?:(?P<trait>[a-zA-Z_]\w*)\s+for\s+)?(?P<type>[a-zA-Z_]\w*)"
)
_RS_USE_RE = re.compile(
    r"^use\s+(?P<path>[a-zA-Z0-9_:]+)(?:::\{(?P<symbols>[^}]+)\})?;"
)


class RustSymbolScanner:
    """Scans Rust (.rs) source files for functions, structs, enums, traits, impls, and uses."""

    @staticmethod
    def scan(content: str, rel_path: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        lines = content.splitlines()
        symbols: list[dict[str, Any]] = []
        imports: dict[str, Any] = {}

        current_impl: str | None = None
        impl_end_line = 0

        for idx, line in enumerate(lines):
            line_no = idx + 1
            if current_impl and line_no > impl_end_line:
                current_impl = None

            stripped = line.strip()

            # use statement
            use_match = _RS_USE_RE.match(stripped)
            if use_match:
                base_path = use_match.group("path")
                sym_group = use_match.group("symbols")
                if sym_group:
                    for s in sym_group.split(","):
                        s = s.strip()
                        if s:
                            imports[s] = {"module": base_path, "symbol": s, "alias": s}
                else:
                    alias = base_path.split("::")[-1]
                    imports[alias] = {"module": base_path, "symbol": "", "alias": alias}
                continue

            # impl block
            impl_match = _RS_IMPL_RE.match(stripped)
            if impl_match:
                current_impl = impl_match.group("type")
                impl_end_line = find_closing_brace(lines, idx)
                continue

            # function / method
            fn_match = _RS_FN_RE.match(stripped)
            if fn_match:
                name = fn_match.group("name")
                end_line = find_closing_brace(lines, idx)
                kind = "method" if current_impl else "function"
                symbols.append({
                    "name": name,
                    "kind": kind,
                    "file_path": rel_path,
                    "line_start": line_no,
                    "line_end": end_line,
                    "class_name": current_impl,
                    "docstring": None,
                })
                continue

            # struct / enum / trait
            struct_match = _RS_STRUCT_RE.match(stripped)
            if struct_match:
                name = struct_match.group("name")
                end_line = find_closing_brace(lines, idx)
                symbols.append({
                    "name": name,
                    "kind": "class",
                    "file_path": rel_path,
                    "line_start": line_no,
                    "line_end": end_line,
                    "class_name": None,
                    "docstring": None,
                })

        return symbols, imports


# ---------------------------------------------------------------------------
# Multi-Language Frame Parser
# ---------------------------------------------------------------------------

_GO_PANICTRACE_FRAME_RE = re.compile(
    r"^\t(?P<path>[^:\s\n]+\.go):(?P<line>\d+)(?:\s+\+0x[0-9a-fA-F]+)?"
)
_GO_TEST_FAIL_FRAME_RE = re.compile(
    r"^\s*(?P<path>[^:\s\n]+\.go):(?P<line>\d+):"
)
_GO_FUNC_SIGNATURE_RE = re.compile(
    r"^(?P<func>[a-zA-Z0-9_./]+(?:\.\(\*?[a-zA-Z0-9_]+\))?\.[a-zA-Z0-9_]+)\("
)

_TS_FRAME_RE = re.compile(
    r"^\s*at\s+(?:(?P<func>[^(\n]+?)\s+\()?(?P<path>[^:\s\n()]+\.(?:ts|tsx|js|jsx|mjs|cjs)):(?P<line>\d+)(?::(?P<col>\d+))?\)?$"
)
_TS_LINE_FRAME_RE = re.compile(
    r"^\s*(?P<path>[^:\s\n()]+\.(?:ts|tsx|js|jsx|mjs|cjs)):(?P<line>\d+)(?::(?P<col>\d+))?"
)

_RS_PANIC_RE = re.compile(
    r"panicked\s+at\s+.*,\s*(?P<path>[^:\s\n]+\.rs):(?P<line>\d+):(?P<col>\d+)"
)
_RS_BACKTRACE_FRAME_RE = re.compile(
    r"^\s*at\s+(?P<path>[^:\s\n()]+\.rs):(?P<line>\d+)(?::(?P<col>\d+))?"
)
_RS_LINE_FRAME_RE = re.compile(
    r"^\s*(?P<path>[^:\s\n()]+\.rs):(?P<line>\d+):(?P<col>\d+)"
)


class MultiLangFrameParser:
    """Parses execution stack frames from Go, TypeScript/JS, and Rust tracebacks."""

    @staticmethod
    def parse_frames(text: str) -> list[dict[str, Any]]:
        frames: list[dict[str, Any]] = []
        lines = text.splitlines()

        for idx, line in enumerate(lines):
            # 1. Go panic frame (\tpath/file.go:line +0x...)
            go_panic = _GO_PANICTRACE_FRAME_RE.match(line)
            if go_panic:
                func_name = ""
                if idx > 0:
                    prev_line = lines[idx - 1].strip()
                    fn_match = _GO_FUNC_SIGNATURE_RE.match(prev_line)
                    if fn_match:
                        func_name = fn_match.group("func").split(".")[-1]
                frames.append({
                    "file_path": go_panic.group("path"),
                    "line": int(go_panic.group("line")),
                    "function_name": func_name,
                })
                continue

            # 2. Go test failure (path/file_test.go:line:)
            go_test = _GO_TEST_FAIL_FRAME_RE.match(line)
            if go_test:
                frames.append({
                    "file_path": go_test.group("path"),
                    "line": int(go_test.group("line")),
                    "function_name": "",
                })
                continue

            # 3. TS / JS stack frame (at func (/path/file.ts:line:col))
            ts_frame = _TS_FRAME_RE.match(line)
            if ts_frame:
                func = (ts_frame.group("func") or "").strip()
                if func == "Object.<anonymous>":
                    func = ""
                frames.append({
                    "file_path": ts_frame.group("path"),
                    "line": int(ts_frame.group("line")),
                    "function_name": func,
                })
                continue

            # 4. TS / JS line frame (path/file.test.ts:line:col)
            ts_line = _TS_LINE_FRAME_RE.match(line)
            if ts_line:
                frames.append({
                    "file_path": ts_line.group("path"),
                    "line": int(ts_line.group("line")),
                    "function_name": "",
                })
                continue

            # 5. Rust panic at ... path.rs:line:col
            rs_panic = _RS_PANIC_RE.search(line)
            if rs_panic:
                frames.append({
                    "file_path": rs_panic.group("path"),
                    "line": int(rs_panic.group("line")),
                    "function_name": "",
                })
                continue

            # 6. Rust backtrace frame (at path.rs:line:col)
            rs_bt = _RS_BACKTRACE_FRAME_RE.match(line)
            if rs_bt:
                func = ""
                if idx > 0:
                    prev = lines[idx - 1].strip()
                    if ":" in prev:
                        func = prev.split(":")[-1].strip().split("::")[-1]
                frames.append({
                    "file_path": rs_bt.group("path"),
                    "line": int(rs_bt.group("line")),
                    "function_name": func,
                })
                continue

            # 7. Rust line frame (path.rs:line:col)
            rs_line = _RS_LINE_FRAME_RE.match(line)
            if rs_line:
                frames.append({
                    "file_path": rs_line.group("path"),
                    "line": int(rs_line.group("line")),
                    "function_name": "",
                })

        return frames
