from __future__ import annotations

from importlib import resources
from typing import Any


LOGICAL_SKILLS_ROOT = "integrations/skills"


def _skills_root() -> Any:
    return resources.files("onecode").joinpath("integrations", "skills")


def _skill_resource(name: str) -> Any:
    return _skills_root().joinpath(name, "SKILL.md")


def _logical_skill_path(name: str) -> str:
    return f"{LOGICAL_SKILLS_ROOT}/{name}/SKILL.md"


def _read_frontmatter(path: Any) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"skill missing frontmatter: {path}")
    values: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def list_builtin_skills() -> list[dict[str, Any]]:
    skills = []
    root = _skills_root()
    if not root.exists():
        return skills
    for skill_dir in sorted((path for path in root.iterdir() if path.is_dir()), key=lambda path: path.name):
        path = skill_dir.joinpath("SKILL.md")
        if not path.exists():
            continue
        metadata = _read_frontmatter(path)
        name = metadata.get("name", skill_dir.name)
        skills.append(
            {
                "name": name,
                "description": metadata.get("description", ""),
                "kind": "router" if name == "safe-agent-router" else "skill",
                "path": _logical_skill_path(name),
                "authority": "advisory_only",
            }
        )
    return skills


def get_builtin_skill(name: str) -> dict[str, Any]:
    for skill in list_builtin_skills():
        if skill["name"] == name:
            return {**skill, "content": _skill_resource(name).read_text(encoding="utf-8")}
    raise KeyError(f"unknown built-in skill: {name}")


def _task_profile(task: str) -> dict[str, Any]:
    lowered = task.lower()
    capabilities = []
    if any(term in lowered for term in ["test", "verify", "lint", "build", "doctor"]):
        capabilities.append("verification")
    if any(term in lowered for term in ["doc", "readme", "release", "checklist"]):
        capabilities.append("documentation")
    if any(term in lowered for term in ["code", "fix", "implement", "add", "update"]):
        capabilities.append("implementation")
    if not capabilities:
        capabilities.append("general_reasoning")
    return {
        "task_length": len(task),
        "capabilities": capabilities,
        "non_trivial": len(task.strip()) > 20 or len(capabilities) > 1,
    }


def build_skill_task_pack(task: str) -> dict[str, Any]:
    normalized_task = task.strip()
    if not normalized_task:
        raise ValueError("task must not be empty")
    profile = _task_profile(normalized_task)
    execution_plan = [
        "Classify the task and select only trusted built-in or host-approved skills.",
        "Read the selected skill guidance before planning implementation details.",
        "Apply guidance within existing host permissions and OneCode kernel policy.",
        "Run verifier expectations before reporting completion.",
    ]
    if "documentation" in profile["capabilities"]:
        execution_plan.insert(2, "Check public wording, privacy boundaries, and release documentation consistency.")
    if "implementation" in profile["capabilities"]:
        execution_plan.insert(2, "Keep edits scoped and preserve path, evidence, and runtime safety checks.")
    return {
        "skill": "safe-agent-router",
        "authority": "advisory_only",
        "task": normalized_task,
        "task_profile": profile,
        "selected_scenario": "trusted-local-task-routing",
        "selected_skills": ["safe-agent-router"],
        "capability_coverage": profile["capabilities"],
        "execution_plan": execution_plan,
        "verifier_expectations": [
            "Run focused tests for changed behavior.",
            "Run privacy scan for public release or documentation changes.",
            "Run the project verification gate when core behavior changes.",
        ],
        "safety_boundary": [
            "No filesystem, shell, network, browser, connector, account, credential, deployment, or production permission is granted by skill routing.",
            "Host runtime policy, OneCode path guards, evidence checks, and verifier results remain authoritative.",
        ],
    }
