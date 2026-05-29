from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


DEFAULT_WORKFLOW_REGISTRY = Path(__file__).with_name("workflow_registry.json")


@dataclass(frozen=True)
class Workflow:
    code: str
    title: str
    path: Path
    content: str


def load_workflow_registry(path: str | Path = DEFAULT_WORKFLOW_REGISTRY) -> dict[str, Any]:
    registry_path = Path(path)
    with registry_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Workflow registry root must be an object")
    workflows = data.get("workflows")
    if not isinstance(workflows, dict) or not workflows:
        raise ValueError("Workflow registry must contain a non-empty workflows object")
    data["_base_dir"] = str(registry_path.parent)
    return data


def lookup_workflow(registry: dict[str, Any], code: str) -> Workflow:
    workflows = registry.get("workflows", {})
    if code not in workflows:
        raise KeyError(f"Unknown workflow code: {code}")

    base_dir = Path(registry.get("_base_dir", "."))
    workflow_path = base_dir / workflows[code]
    content = workflow_path.read_text(encoding="utf-8")
    return Workflow(
        code=code,
        title=_extract_title(content, workflow_path),
        path=workflow_path,
        content=content,
    )


def load_workflow_excerpt(code: str, max_chars: int = 1400) -> str:
    registry = load_workflow_registry()
    workflow = lookup_workflow(registry, code)
    content = workflow.content.strip()
    if len(content) <= max_chars:
        return content
    return content[:max_chars].rstrip() + "\n..."


def _extract_title(content: str, path: Path) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return path.stem
