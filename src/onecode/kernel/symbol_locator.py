"""Large-repo symbol index and call-chain fault localization for SWE-bench workflows.

Given a failure trace, stack frames, or failing test assertion, this module:
1. Extracts failing symbol names and stack frames from traceback text;
2. Builds an AST-based symbol definition and import index of the workspace;
3. Traces the call chain from the failing test into the implementation codebase;
4. Identifies the true file(s) and line spans defining the target symbols;
5. Distinguishes immutable preset test paths from implementation source files.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
import os
from pathlib import Path
import posixpath
import re
from typing import Any

from onecode.kernel.path_guard import PathGuard
from onecode.kernel.preset_tests import is_preset_test_path
from onecode.kernel.symbol_parsers import (
    GoSymbolScanner,
    MultiLangFrameParser,
    RustSymbolScanner,
    TypeScriptSymbolScanner,
)

_PY_EXTENSIONS = {".py", ".pyw"}
_GO_EXTENSIONS = {".go"}
_TS_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
_RS_EXTENSIONS = {".rs"}
_LANG_EXTENSIONS = _PY_EXTENSIONS | _GO_EXTENSIONS | _TS_EXTENSIONS | _RS_EXTENSIONS

_IGNORE_DIRS = {
    ".git", ".venv", "venv", ".tox", ".nox", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "build", "dist",
    "egg-info", ".eggs", ".onecode", "node_modules", "target", "vendor",
}


_TEST_HARNESS_SYMBOLS = {
    "test", "describe", "it", "expect", "suite", "setup", "teardown",
    "before", "after", "beforeeach", "aftereach", "assert",
}


def _is_test_symbol(name: str) -> bool:
    low = name.casefold()
    if low in _TEST_HARNESS_SYMBOLS:
        return True
    if name.startswith("test_") or name.startswith("Test") or name.startswith("Benchmark") or name.startswith("Fuzz"):
        return True
    return False


def is_any_test_path(path: str) -> bool:
    """Identifies test files across Python, Go, TypeScript/JavaScript, and Rust."""
    if not isinstance(path, str) or not path.strip():
        return False
    if is_preset_test_path(path):
        return True
    norm = path.replace("\\", "/").casefold()
    if "/tests/" in norm or norm.startswith("tests/") or norm == "tests":
        return True
    if "/__tests__/" in norm or norm.startswith("__tests__/"):
        return True
    base = posixpath.basename(norm)
    if ".test." in base or ".spec." in base:
        return True
    if base.endswith(("_test.go", "_test.rs", "tests.rs", "_test.py", "_test.js", "_test.ts")):
        return True
    return False

_FRAME_RE = re.compile(
    r'File\s+["\'](?P<path>[^"\']+)["\'],\s+line\s+(?P<line>\d+)(?:,\s+in\s+(?P<func>[^\n]+))?'
)
_PYTEST_FRAME_RE = re.compile(
    r"^\s*(?P<path>[^:\s\n]+\.py):(?P<line>\d+):(?:\s+(?:in\s+)?(?P<func>[^\n]+))?"
)
_PYTEST_FAIL_RE = re.compile(
    r'(?:FAILED|ERROR)\s+(?P<path>[^:\s]+)(?:::)?(?P<test>[^\s]*)'
)
_ATTR_ERROR_RE = re.compile(
    r"AttributeError:\s+(?:type\s+object\s+)?['\"]?(?P<class>\w+)['\"]?\s+object\s+has\s+no\s+attribute\s+['\"](?P<attr>\w+)['\"]"
)
_TYPE_ERROR_RE = re.compile(
    r"TypeError:\s+(?P<func>\w+)\(\)\s+(?:missing|got|takes|takes\s+from)"
)
_NAME_ERROR_RE = re.compile(
    r"NameError:\s+name\s+['\"](?P<name>\w+)['\"]\s+is\s+not\s+defined"
)
_IMPORT_ERROR_RE = re.compile(
    r"(?:ImportError|ModuleNotFoundError):\s+(?:cannot\s+import\s+name\s+['\"](?P<symbol>\w+)['\"]|No\s+module\s+named\s+['\"](?P<mod>\w+)['\"])"
)


@dataclass(frozen=True)
class SymbolDef:
    """An AST-identified symbol definition in a workspace file."""
    name: str
    kind: str  # "function", "async_function", "class", "method"
    file_path: str  # relative POSIX path
    line_start: int
    line_end: int
    class_name: str | None = None
    docstring: str | None = None
    parameters: tuple[str, ...] = field(default_factory=tuple)

    @property
    def qualified_name(self) -> str:
        if self.class_name:
            return f"{self.class_name}.{self.name}"
        return self.name


@dataclass(frozen=True)
class ImportRef:
    """An imported module or symbol reference."""
    module: str
    symbol: str = ""
    alias: str = ""

    @property
    def target(self) -> str:
        if self.symbol:
            return f"{self.module}.{self.symbol}" if self.module else self.symbol
        return self.module

    def __str__(self) -> str:
        return self.target

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.target == other or self.module == other
        return super().__eq__(other)


@dataclass(frozen=True)
class StackFrame:
    """A single execution frame parsed from a traceback."""
    file_path: str
    line: int
    function_name: str
    code_snippet: str | None = None


@dataclass(frozen=True)
class FaultLocation:
    """A ranked candidate localization for patching."""
    file_path: str
    symbol_name: str
    symbol_kind: str
    line_start: int
    line_end: int
    confidence: float  # 0.0 to 1.0
    call_chain: tuple[str, ...]
    is_test_file: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "symbol_name": self.symbol_name,
            "symbol_kind": self.symbol_kind,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "confidence": round(self.confidence, 4),
            "call_chain": list(self.call_chain),
            "is_test_file": self.is_test_file,
            "reason": self.reason,
        }


class WorkspaceSymbolIndex:
    """AST-driven index of classes, functions, methods, and import relations."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self.symbols_by_name: dict[str, list[SymbolDef]] = {}
        self.symbols_by_file: dict[str, list[SymbolDef]] = {}
        self.imports_by_file: dict[str, dict[str, ImportRef]] = {}
        self.scanned_files_count = 0
        self._build_index()

    def _should_skip_dir(self, dir_name: str) -> bool:
        return dir_name in _IGNORE_DIRS or dir_name.endswith(".egg-info")

    def _collect_source_files(self) -> list[Path]:
        files: list[Path] = []
        for root, dirs, filenames in os.walk(self.workspace):
            dirs[:] = [d for d in dirs if not self._should_skip_dir(d)]
            for fn in filenames:
                ext = posixpath.splitext(fn)[1].casefold()
                if ext in _LANG_EXTENSIONS:
                    candidate = Path(root) / fn
                    if not candidate.is_symlink():
                        files.append(candidate)
        return files

    def _parse_file(self, file_path: Path) -> None:
        try:
            rel_path = file_path.relative_to(self.workspace).as_posix()
        except ValueError:
            return
        if PathGuard.is_sensitive_read_path(Path(rel_path)):
            return

        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return

        ext = posixpath.splitext(file_path.name)[1].casefold()
        if ext in _PY_EXTENSIONS:
            self._parse_python_content(content, rel_path)
        elif ext in _GO_EXTENSIONS:
            raw_symbols, raw_imports = GoSymbolScanner.scan(content, rel_path)
            self._register_scanned(raw_symbols, raw_imports, rel_path)
        elif ext in _TS_EXTENSIONS:
            raw_symbols, raw_imports = TypeScriptSymbolScanner.scan(content, rel_path)
            self._register_scanned(raw_symbols, raw_imports, rel_path)
        elif ext in _RS_EXTENSIONS:
            raw_symbols, raw_imports = RustSymbolScanner.scan(content, rel_path)
            self._register_scanned(raw_symbols, raw_imports, rel_path)

    def _parse_python_content(self, content: str, rel_path: str) -> None:
        try:
            tree = ast.parse(content, filename=rel_path)
        except (SyntaxError, ValueError):
            return

        self.scanned_files_count += 1
        file_symbols: list[SymbolDef] = []
        file_imports: dict[str, ImportRef] = {}

        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                self._index_import(node, file_imports, rel_path=rel_path)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                sym = self._make_func_symbol(node, rel_path)
                file_symbols.append(sym)
                self.symbols_by_name.setdefault(sym.name, []).append(sym)
            elif isinstance(node, ast.ClassDef):
                cls_sym = SymbolDef(
                    name=node.name,
                    kind="class",
                    file_path=rel_path,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    docstring=ast.get_docstring(node),
                )
                file_symbols.append(cls_sym)
                self.symbols_by_name.setdefault(cls_sym.name, []).append(cls_sym)

                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_sym = self._make_func_symbol(item, rel_path, class_name=node.name)
                        file_symbols.append(method_sym)
                        self.symbols_by_name.setdefault(method_sym.name, []).append(method_sym)
                        self.symbols_by_name.setdefault(f"{node.name}.{item.name}", []).append(method_sym)

        self.symbols_by_file[rel_path] = file_symbols
        self.imports_by_file[rel_path] = file_imports

    def _register_scanned(
        self,
        raw_symbols: list[dict[str, Any]],
        raw_imports: dict[str, Any],
        rel_path: str,
    ) -> None:
        self.scanned_files_count += 1
        file_symbols: list[SymbolDef] = []
        file_imports: dict[str, ImportRef] = {}
        for s in raw_symbols:
            sym = SymbolDef(
                name=s["name"],
                kind=s["kind"],
                file_path=s["file_path"],
                line_start=s["line_start"],
                line_end=s["line_end"],
                class_name=s.get("class_name"),
            )
            file_symbols.append(sym)
            self.symbols_by_name.setdefault(sym.name, []).append(sym)
            if sym.class_name:
                self.symbols_by_name.setdefault(f"{sym.class_name}.{sym.name}", []).append(sym)
        for alias, imp in raw_imports.items():
            file_imports[alias] = ImportRef(
                module=imp["module"],
                symbol=imp.get("symbol", ""),
                alias=imp.get("alias", alias),
            )
        self.symbols_by_file[rel_path] = file_symbols
        self.imports_by_file[rel_path] = file_imports

    def _index_import(
        self,
        node: ast.Import | ast.ImportFrom,
        target_dict: dict[str, ImportRef],
        rel_path: str = "",
    ) -> None:
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name
                target_dict[name] = ImportRef(module=alias.name, alias=name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level and node.level > 0 and rel_path:
                pkg_parts = Path(rel_path).parent.parts
                cut = node.level - 1
                base_parts = pkg_parts[: len(pkg_parts) - cut] if cut < len(pkg_parts) else ()
                prefix = ".".join(base_parts)
                mod = f"{prefix}.{mod}" if (prefix and mod) else (prefix or mod)
            for alias in node.names:
                name = alias.asname or alias.name
                target_dict[name] = ImportRef(module=mod, symbol=alias.name, alias=name)

    def _make_func_symbol(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        rel_path: str,
        class_name: str | None = None,
    ) -> SymbolDef:
        kind = "method" if class_name else ("async_function" if isinstance(node, ast.AsyncFunctionDef) else "function")
        params = tuple(arg.arg for arg in node.args.args)
        return SymbolDef(
            name=node.name,
            kind=kind,
            file_path=rel_path,
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", node.lineno),
            class_name=class_name,
            docstring=ast.get_docstring(node),
            parameters=params,
        )

    def resolve_import_file(
        self,
        imp: ImportRef,
        *,
        importing_file: str = "",
        max_depth: int = 3,
    ) -> str | None:
        """Resolves an ImportRef into a relative file path in the workspace."""
        candidates: list[str] = []
        mod = imp.module
        sym = imp.symbol

        # 1. Python candidates
        if sym:
            candidates.append(f"{mod}.{sym}".replace(".", "/") + ".py")
        candidates.append(mod.replace(".", "/") + ".py")
        if sym:
            candidates.append(f"{mod}.{sym}".replace(".", "/") + "/__init__.py")
        candidates.append(mod.replace(".", "/") + "/__init__.py")

        # 2. Go candidates
        mod_clean = mod.strip("/").strip('"')
        candidates.append(f"{mod_clean}.go")
        candidates.append(f"{mod_clean}/main.go")
        base_mod = posixpath.basename(mod_clean)

        # 3. TS / JS candidates
        if importing_file and mod.startswith("."):
            imp_dir = posixpath.dirname(importing_file)
            rel_target = posixpath.normpath(posixpath.join(imp_dir, mod))
            for ext in (".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.js"):
                candidates.append(rel_target + ext)
        for ext in (".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.js"):
            candidates.append(mod.lstrip("./") + ext)

        # 4. Rust candidates
        rs_mod = mod.replace("::", "/").lstrip("/")
        candidates.append(f"{rs_mod}.rs")
        candidates.append(f"{rs_mod}/mod.rs")

        # Also consider src/ prefix and stripping leading components
        expanded: list[str] = []
        for cand in candidates:
            expanded.append(cand)
            if not cand.startswith("src/"):
                expanded.append(f"src/{cand}")
            elif cand.startswith("src/"):
                expanded.append(cand[4:])

        found_path: str | None = None
        for cand in expanded:
            if cand in self.symbols_by_file:
                found_path = cand
                break

        # Fallback for Go: package folder match
        if not found_path and base_mod:
            for f in self.symbols_by_file:
                if f.endswith(".go") and (f"/{base_mod}/" in f"/{f}" or f.startswith(f"{base_mod}/")):
                    found_path = f
                    break

        if not found_path:
            return None

        # If found file does not define the symbol, check for re-exports
        if imp.symbol and max_depth > 0:
            sym_defs = [s.name for s in self.symbols_by_file.get(found_path, [])]
            if imp.symbol not in sym_defs and found_path in self.imports_by_file:
                reexport = self.imports_by_file[found_path].get(imp.symbol)
                if reexport:
                    deeper = self.resolve_import_file(reexport, importing_file=found_path, max_depth=max_depth - 1)
                    if deeper:
                        return deeper

        return found_path

    def _build_index(self) -> None:
        for src_file in self._collect_source_files():
            self._parse_file(src_file)


class SymbolLocator:
    """Parses failures, traverses symbols, and localizes fault implementation files."""

    def __init__(self, workspace: Path, index: WorkspaceSymbolIndex | None = None) -> None:
        self.workspace = workspace.resolve()
        self.index = index or WorkspaceSymbolIndex(self.workspace)

    def parse_stack_frames(self, text: str) -> list[StackFrame]:
        frames: list[StackFrame] = []
        seen: set[tuple[str, int]] = set()

        for ml_item in MultiLangFrameParser.parse_frames(text):
            norm = self._normalize_frame_path(ml_item["file_path"])
            key = (norm, ml_item["line"])
            if key not in seen:
                seen.add(key)
                frames.append(StackFrame(file_path=norm, line=ml_item["line"], function_name=ml_item["function_name"]))

        for line in text.splitlines():
            match = _FRAME_RE.search(line)
            if match:
                raw_path = match.group("path")
                line_no = int(match.group("line"))
                func = (match.group("func") or "").strip()
                norm = self._normalize_frame_path(raw_path)
                key = (norm, line_no)
                if key not in seen:
                    seen.add(key)
                    frames.append(StackFrame(file_path=norm, line=line_no, function_name=func))
            else:
                pytest_match = _PYTEST_FRAME_RE.search(line)
                if pytest_match:
                    raw_path = pytest_match.group("path")
                    line_no = int(pytest_match.group("line"))
                    raw_func = (pytest_match.group("func") or "").strip()
                    func = "" if (raw_func.endswith("Error") or raw_func.endswith("Exception")) else raw_func
                    norm = self._normalize_frame_path(raw_path)
                    key = (norm, line_no)
                    if key not in seen:
                        seen.add(key)
                        frames.append(StackFrame(file_path=norm, line=line_no, function_name=func))
        return frames

    def _normalize_frame_path(self, raw_path: str) -> str:
        p = raw_path.replace("\\", "/").strip()
        try:
            resolved = Path(p).resolve()
            return resolved.relative_to(self.workspace).as_posix()
        except Exception:
            for part in p.split("/"):
                if part in {"src", "lib", "tests", "app"}:
                    idx = p.find(part)
                    if idx >= 0:
                        return p[idx:]
            return posixpath.normpath(p)

    def extract_failing_symbols(self, text: str) -> list[str]:
        names: list[str] = []
        for match in _ATTR_ERROR_RE.finditer(text):
            names.append(match.group("attr"))
            names.append(f"{match.group('class')}.{match.group('attr')}")
            names.append(match.group("class"))
        for match in _TYPE_ERROR_RE.finditer(text):
            names.append(match.group("func"))
        for match in _NAME_ERROR_RE.finditer(text):
            names.append(match.group("name"))
        for match in _IMPORT_ERROR_RE.finditer(text):
            if match.group("symbol"):
                names.append(match.group("symbol"))
            if match.group("mod"):
                names.append(match.group("mod"))
        for match in _PYTEST_FAIL_RE.finditer(text):
            test_target = match.group("test")
            if test_target:
                for sub in test_target.split("::"):
                    if sub.startswith("test_") and len(sub) > 5:
                        names.append(sub[5:])
                    elif sub:
                        names.append(sub)

        # Frame function names
        for match in _FRAME_RE.finditer(text):
            func = (match.group("func") or "").strip()
            if func and func != "<module>" and not _is_test_symbol(func):
                names.append(func)

        # Quoted tokens
        quoted = re.findall(r"[`'\"]([a-zA-Z_]\w+(?:\.\w+)?)['\"`]", text)
        names.extend(quoted)

        # Any identifier in failure text matching a known workspace symbol
        tokens = set(re.findall(r"\b[a-zA-Z_]\w+\b", text))
        for token in tokens:
            if token in self.index.symbols_by_name and not _is_test_symbol(token):
                names.append(token)

        # Deduplicate preserving order
        seen: set[str] = set()
        result: list[str] = []
        for n in names:
            if n not in seen and len(n) > 1 and not _is_test_symbol(n):
                seen.add(n)
                result.append(n)
        return result

    def _extract_tokens_from_test_scope(self, frames: list[StackFrame]) -> list[str]:
        """Extract code tokens from the test function body containing the failure line."""
        tokens: list[str] = []
        for frame in frames:
            if not is_any_test_path(frame.file_path):
                continue
            test_file = self.workspace / frame.file_path
            if not test_file.is_file():
                continue
            enclosing = [
                s for s in self.index.symbols_by_file.get(frame.file_path, [])
                if s.line_start <= frame.line <= s.line_end
            ]
            if not enclosing:
                continue
            enclosing.sort(key=lambda s: s.line_end - s.line_start)
            target_sym = enclosing[0]
            try:
                lines = test_file.read_text(encoding="utf-8").splitlines()
                start = max(0, target_sym.line_start - 1)
                end = min(len(lines), target_sym.line_end)
                scope_text = "\n".join(lines[start:end])
                for word in re.findall(r"\b[a-zA-Z_]\w+\b", scope_text):
                    if word in self.index.symbols_by_name and not _is_test_symbol(word):
                        tokens.append(word)
            except OSError:
                pass
        return tokens

    def locate_fault(
        self,
        failure_text: str,
        *,
        max_candidates: int = 5,
        test_file_hint: str | None = None,
    ) -> list[FaultLocation]:
        frames = self.parse_stack_frames(failure_text)
        candidate_symbols = self.extract_failing_symbols(failure_text)
        for tok in self._extract_tokens_from_test_scope(frames):
            if tok not in candidate_symbols:
                candidate_symbols.append(tok)

        candidates: list[FaultLocation] = []
        seen_keys: set[tuple[str, str, int]] = set()

        # Step 1: Traverse stack frames from bottom (closest to failure) to top
        for frame_idx, frame in enumerate(reversed(frames)):
            is_test = is_any_test_path(frame.file_path)
            depth_weight = 1.0 - (frame_idx * 0.15)
            depth_weight = max(depth_weight, 0.4)

            # Look up symbols in frame file, sorted by specificity (narrowest span first)
            file_symbols = self.index.symbols_by_file.get(frame.file_path, [])
            matching = [s for s in file_symbols if s.line_start <= frame.line <= s.line_end]
            matching.sort(key=lambda s: (s.line_end - s.line_start, 0 if s.kind in {"method", "function"} else 1))

            for sym in matching:
                key = (sym.file_path, sym.name, sym.line_start)
                if key not in seen_keys:
                    seen_keys.add(key)
                    kind_bonus = 0.05 if sym.kind in {"method", "function", "async_function"} else 0.0
                    score = min(depth_weight * (0.3 if is_test else 1.0) + kind_bonus, 1.0)
                    candidates.append(
                        FaultLocation(
                            file_path=sym.file_path,
                            symbol_name=sym.qualified_name,
                            symbol_kind=sym.kind,
                            line_start=sym.line_start,
                            line_end=sym.line_end,
                            confidence=score,
                            call_chain=(frame.file_path, frame.function_name, sym.name),
                            is_test_file=is_test,
                            reason=f"Stack frame match at line {frame.line}",
                        )
                    )

        # Step 2: Call-chain import resolution from test file hint
        test_path = test_file_hint
        if not test_path and frames:
            for f in frames:
                if is_any_test_path(f.file_path):
                    test_path = f.file_path
                    break

        if not test_path:
            for match in _PYTEST_FAIL_RE.finditer(failure_text):
                p = match.group("path")
                if p and is_any_test_path(p):
                    test_path = p
                    break

        if test_path and test_path in self.index.imports_by_file:
            test_imports = self.index.imports_by_file[test_path]
            for local_alias, imp_ref in test_imports.items():
                target_file = self.index.resolve_import_file(imp_ref, importing_file=test_path)
                if not target_file:
                    continue

                for sym in self.index.symbols_by_file.get(target_file, []):
                    # Check if symbol matches failing candidates, imported symbol, or alias
                    matches_candidate = sym.name in candidate_symbols or sym.qualified_name in candidate_symbols
                    matches_import = sym.name == imp_ref.symbol or sym.name == local_alias
                    if matches_candidate or matches_import:
                        key = (sym.file_path, sym.name, sym.line_start)
                        if key not in seen_keys:
                            seen_keys.add(key)
                            conf = 0.92 if matches_candidate else 0.40
                            candidates.append(
                                FaultLocation(
                                    file_path=sym.file_path,
                                    symbol_name=sym.qualified_name,
                                    symbol_kind=sym.kind,
                                    line_start=sym.line_start,
                                    line_end=sym.line_end,
                                    confidence=conf,
                                    call_chain=(test_path, local_alias, target_file, sym.name),
                                    is_test_file=False,
                                    reason=f"Direct import reference from test '{test_path}'" + (" (symbol in failure context)" if matches_candidate else ""),
                                )
                            )

        # Step 3: AST lookup for explicitly failed symbols across workspace
        for sym_name in candidate_symbols:
            defs = self.index.symbols_by_name.get(sym_name, [])
            for sym in defs:
                is_test = is_any_test_path(sym.file_path)
                key = (sym.file_path, sym.name, sym.line_start)
                if key not in seen_keys:
                    seen_keys.add(key)
                    base_score = 0.25 if is_test else 0.85
                    candidates.append(
                        FaultLocation(
                            file_path=sym.file_path,
                            symbol_name=sym.qualified_name,
                            symbol_kind=sym.kind,
                            line_start=sym.line_start,
                            line_end=sym.line_end,
                            confidence=base_score,
                            call_chain=(sym_name, sym.qualified_name),
                            is_test_file=is_test,
                            reason=f"Explicit symbol definition match for '{sym_name}'",
                        )
                    )

        # Sort: Non-test files first, then by confidence descending
        candidates.sort(key=lambda loc: (loc.is_test_file, -loc.confidence))
        return candidates[:max_candidates]
