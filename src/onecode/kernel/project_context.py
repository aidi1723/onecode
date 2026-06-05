from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re

from onecode.kernel.hexagram import IchingKernel


_RULE_SUFFIXES = {".md", ".txt", ".mdc"}
_ROOT_RULE_FILES = (
    ("AGENTS.md", "project_root", "project"),
    ("CLAUDE.md", "project_root", "project"),
    ("CLAW.md", "project_root", "project"),
    (".onecode/instructions.md", "onecode_instructions", "project"),
)
_FRAMEWORK_ROOT_FILES = {
    "cursor": ((".cursorrules", "cursor_rules"),),
    "copilot": ((".github/copilot-instructions.md", "copilot_instructions"),),
    "windsurf": ((".windsurfrules", "windsurf_rules"),),
    "plandex": ((".plandex/instructions.md", "plandex_instructions"),),
}
_FRAMEWORK_RULE_DIRS = {
    "cursor": ((".cursor/rules", "cursor_rules"),),
}


@dataclass(frozen=True)
class RulesImport:
    _mode: str
    _frameworks: frozenset[str] = frozenset()

    @classmethod
    def auto(cls) -> "RulesImport":
        return cls("auto")

    @classmethod
    def none(cls) -> "RulesImport":
        return cls("none")

    @classmethod
    def list(cls, frameworks: list[str]) -> "RulesImport":
        return cls("list", frozenset(_normalize_framework(name) for name in frameworks))

    def should_import(self, framework: str) -> bool:
        normalized = _normalize_framework(framework)
        if self._mode == "none":
            return False
        if self._mode == "list":
            return normalized in self._frameworks
        return True


def discover_project_context(workspace: Path, *, rules_import: RulesImport | None = None) -> dict:
    root = Path(workspace)
    import_policy = rules_import or RulesImport.auto()
    invalid_files: list[dict[str, str]] = []
    seen_normalized_hashes: set[str] = set()
    memory_files: list[dict[str, object]] = []
    deduped_count = 0

    for path, source, origin in _candidate_files(root, import_policy):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            invalid_files.append(_invalid_file(root, path, "utf8_decode_error", str(exc)))
            continue
        except OSError as exc:
            invalid_files.append(_invalid_file(root, path, "read_error", str(exc)))
            continue

        normalized_hash = _normalized_content_sha256(text)
        if normalized_hash in seen_normalized_hashes:
            deduped_count += 1
            continue
        seen_normalized_hashes.add(normalized_hash)

        relative_path = _relative_path(root, path)
        memory_files.append(
            {
                "path": relative_path,
                "scope_path": root.resolve().as_posix(),
                "outside_project": False,
                "source": source,
                "origin": origin,
                "chars": len(text),
                "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "contributes": True,
            }
        )

    status = "warning" if invalid_files else "ok"
    status_code = _status_code_for(status)
    transition = IchingKernel.transition(status_code)

    return {
        "status": status,
        "memory_files": memory_files,
        "invalid_files": invalid_files,
        "summary": {
            "file_count": len(memory_files),
            "deduped_count": deduped_count,
            "invalid_count": len(invalid_files),
            "element": IchingKernel.TRIGRAM_ELEMENTS[IchingKernel.XUN],
            "yin_yang_pressure": "warning" if invalid_files else "stable",
        },
        "iching_status_code": status_code,
        "iching_transition_action": transition.action,
        "iching_transition_reason": transition.reason,
        "dispatch_decision": IchingKernel.dispatch_decision(transition),
    }


def _candidate_files(root: Path, rules_import: RulesImport) -> list[tuple[Path, str, str]]:
    candidates: list[tuple[Path, str, str]] = []

    for relative, source, origin in _ROOT_RULE_FILES:
        path = root / relative
        if path.is_file():
            candidates.append((path, source, origin))

    candidates.extend((path, "onecode_rules", "project") for path in _sorted_rule_files(root / ".onecode" / "rules"))
    candidates.extend((path, "onecode_rules_local", "local") for path in _sorted_rule_files(root / ".onecode" / "rules.local"))

    for framework in ("cursor", "copilot", "windsurf", "plandex"):
        if not rules_import.should_import(framework):
            continue
        for relative, source in _FRAMEWORK_ROOT_FILES.get(framework, ()):
            path = root / relative
            if path.is_file():
                candidates.append((path, source, framework))
        for relative, source in _FRAMEWORK_RULE_DIRS.get(framework, ()):
            candidates.extend((path, source, framework) for path in _sorted_files(root / relative))

    return candidates


def _sorted_rule_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        (path for path in directory.iterdir() if path.is_file() and path.suffix.lower() in _RULE_SUFFIXES),
        key=lambda path: path.name,
    )


def _sorted_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted((path for path in directory.iterdir() if path.is_file()), key=lambda path: path.name)


def _normalize_content(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    collapsed: list[str] = []
    previous_blank = False
    for line in lines:
        is_blank = line == ""
        if is_blank and previous_blank:
            continue
        collapsed.append(line)
        previous_blank = is_blank
    return "\n".join(collapsed).strip()


def _normalized_content_sha256(text: str) -> str:
    return hashlib.sha256(_normalize_content(text).encode("utf-8")).hexdigest()


def _invalid_file(root: Path, path: Path, reason: str, detail: str) -> dict[str, str]:
    return {
        "path": _relative_path(root, path),
        "reason": reason,
        "detail": detail,
    }


def _relative_path(root: Path, path: Path) -> str:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return path.as_posix()
    return relative.as_posix()


def _normalize_framework(name: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", name.strip().lower()).strip("_")


def _status_code_for(status: str) -> int:
    if status == "warning":
        return IchingKernel.compute_status(IchingKernel.XUN, IchingKernel.KAN)
    return IchingKernel.compute_status(IchingKernel.XUN, IchingKernel.ZHEN)
