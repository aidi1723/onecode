from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


DEFAULT_SKILL_MOUNT_REGISTRY = Path(__file__).with_name("skill_mount_registry.json")


@dataclass(frozen=True)
class SkillMount:
    code: str
    mount_name: str
    purpose: str
    community_sources: list[dict[str, str]]
    optional_tools: list[str]
    context_mount: list[str]
    hard_gates: list[str]
    evidence: list[str]
    inherits_root: str | None = None


def load_skill_mount_registry(
    path: str | Path = DEFAULT_SKILL_MOUNT_REGISTRY,
) -> dict[str, Any]:
    registry_path = Path(path)
    with registry_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Skill mount registry root must be an object")
    mounts = data.get("mounts")
    if not isinstance(mounts, dict) or not mounts:
        raise ValueError("Skill mount registry must contain a non-empty mounts object")
    data["_base_dir"] = str(registry_path.parent)
    return data


def lookup_skill_mount(registry: dict[str, Any], code: str) -> SkillMount:
    mount_data = registry.get("mounts", {}).get(code)
    inherits_root: str | None = None
    if mount_data is None:
        mount_data = registry.get("derived_mounts", {}).get(code)
        if mount_data is not None:
            inherits_root = str(mount_data.get("inherits_root", ""))
    if mount_data is None:
        raise KeyError(f"Unknown skill mount code: {code}")
    return _build_mount(code, mount_data, inherits_root or None)


def lookup_skill_mount_or_root(
    registry: dict[str, Any],
    code: str,
    root_code: str,
) -> SkillMount:
    try:
        return lookup_skill_mount(registry, code)
    except KeyError:
        root_mount = lookup_skill_mount(registry, root_code)
        return SkillMount(
            code=code,
            mount_name=root_mount.mount_name,
            purpose=root_mount.purpose,
            community_sources=root_mount.community_sources,
            optional_tools=root_mount.optional_tools,
            context_mount=root_mount.context_mount,
            hard_gates=root_mount.hard_gates,
            evidence=root_mount.evidence,
            inherits_root=root_code,
        )


def load_skill_mount_excerpt(
    code: str,
    root_code: str | None = None,
    max_chars: int = 1800,
) -> str:
    registry = load_skill_mount_registry()
    if root_code:
        mount = lookup_skill_mount_or_root(registry, code, root_code)
    else:
        mount = lookup_skill_mount(registry, code)
    excerpt = format_skill_mount(mount)
    if len(excerpt) <= max_chars:
        return excerpt
    return excerpt[:max_chars].rstrip() + "\n..."


def format_skill_mount(mount: SkillMount) -> str:
    sources = "; ".join(
        f"{source['name']} ({source['pattern']})"
        for source in mount.community_sources
    )
    inherited = f"\n继承根字: {mount.inherits_root}" if mount.inherits_root else ""
    return "\n".join(
        [
            f"Skill Mount: {mount.mount_name}",
            f"挂载目标: {mount.purpose}",
            f"社区参考源: {sources}",
            f"可选工具: {', '.join(mount.optional_tools) if mount.optional_tools else 'none'}",
            f"上下文挂载: {', '.join(mount.context_mount)}",
            f"硬门规则: {'; '.join(mount.hard_gates)}",
            f"证据要求: {', '.join(mount.evidence)}{inherited}",
        ]
    )


def _build_mount(
    code: str,
    mount_data: dict[str, Any],
    inherits_root: str | None,
) -> SkillMount:
    return SkillMount(
        code=code,
        mount_name=str(mount_data["mount_name"]),
        purpose=str(mount_data["purpose"]),
        community_sources=list(mount_data.get("community_sources", [])),
        optional_tools=list(mount_data.get("optional_tools", [])),
        context_mount=list(mount_data.get("context_mount", [])),
        hard_gates=list(mount_data.get("hard_gates", [])),
        evidence=list(mount_data.get("evidence", [])),
        inherits_root=inherits_root,
    )
