from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from onecode.kernel.path_guard import PathGuard, PathGuardError


class PatchRejected(ValueError):
    pass


@dataclass(frozen=True)
class PatchIntent:
    path: str
    search_block: str
    replace_block: str
    action: Literal["patch"] = "patch"

    def __post_init__(self) -> None:
        if self.action != "patch":
            raise ValueError("PatchIntent action must be patch")
        if not isinstance(self.path, str) or self.path == "":
            raise ValueError("patch path must be a non-empty string")
        if not isinstance(self.search_block, str) or self.search_block == "":
            raise ValueError("patch search_block must be a non-empty string")
        if not isinstance(self.replace_block, str):
            raise ValueError("patch replace_block must be a string")


@dataclass(frozen=True)
class PatchPreview:
    path: str
    content: str
    status: Literal["ready"] = "ready"


def apply_patch_preview(workspace_root: Path, intent: PatchIntent) -> PatchPreview:
    target = PathGuard.resolve_target(workspace_root, intent.path)
    try:
        original = target.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PatchRejected("patch_target_not_found") from exc

    match_count = original.count(intent.search_block)
    if match_count == 0:
        raise PatchRejected("patch_search_not_found")
    if match_count > 1:
        raise PatchRejected("patch_search_ambiguous")

    content = original.replace(intent.search_block, intent.replace_block, 1)
    return PatchPreview(path=intent.path, content=content)


def compile_patch_preview(preview: PatchPreview) -> None:
    if not preview.path.endswith(".py"):
        return
    try:
        compile(preview.content, preview.path, "exec")
    except SyntaxError as exc:
        raise PatchRejected("patch_compile_error") from exc


def commit_patch(workspace_root: Path, intent: PatchIntent) -> dict[str, str | bool | None]:
    try:
        preview = apply_patch_preview(workspace_root, intent)
        compile_patch_preview(preview)
        written = PathGuard.write_text(workspace_root, intent.path, preview.content)
    except PathGuardError:
        return {
            "status": "halted",
            "partial": True,
            "reason": "sovereignty_breach",
        }
    except PatchRejected as exc:
        return {
            "status": "halted",
            "partial": True,
            "reason": str(exc),
        }

    return {
        "status": "completed",
        "partial": False,
        "reason": None,
        **written,
    }
