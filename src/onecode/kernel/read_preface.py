from pathlib import Path

from onecode.kernel.agent_cycle import READ_ONLY_TOOLS
from onecode.kernel.path_guard import PathGuard


class ReadPrefaceError(ValueError):
    pass


def assert_read_only(tool_names: list[str]) -> None:
    refused = [name for name in tool_names if name not in READ_ONLY_TOOLS]
    if refused:
        raise ReadPrefaceError(f"preface tools must be read-only: {', '.join(refused)}")


def preface_text(files: dict[str, str]) -> str:
    blocks: list[str] = []
    for path in sorted(files):
        content = files[path]
        if content == "":
            continue
        blocks.append(f"## {path}\n{content[:4000]}")
    return "\n".join(blocks)


def with_preface(task: str, preface: str | None) -> str:
    if not preface:
        return task
    return f"{preface.rstrip()}\n\n{task}"


def collect_preface(workspace: Path, relative_paths: list[str]) -> str:
    files: dict[str, str] = {}
    for relative in relative_paths:
        target = PathGuard.resolve_read_target(workspace, relative)
        if target.is_file():
            files[relative.replace("\\", "/")] = target.read_text(encoding="utf-8")[:4000]
    return preface_text(files)
