from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from onecode.kernel.checkpoint import skill_selection_sha256
from onecode.kernel.hexagram import IchingKernel


SKILL_NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}\Z")
VALID_RISKS = {"low", "medium", "high"}
VALID_MODES = {"method_only", "reference_only"}
MAX_SKILL_MANIFEST_BYTES = 64 * 1024
MAX_SKILL_CAPABILITIES = 32
MAX_SKILL_FIELD_CHARS = 128
MAX_SELECTED_SKILLS = 8
TOKEN_ALIASES = {
    "tests": "test",
    "testing": "test",
    "tested": "test",
    "reviews": "review",
    "reviewing": "review",
    "reviewed": "review",
    "audits": "audit",
    "auditing": "audit",
    "audited": "audit",
    "verify": "verification",
    "verifies": "verification",
    "verified": "verification",
    "verifying": "verification",
}


@dataclass(frozen=True)
class SkillManifest:
    name: str
    version: str
    source: str
    risk: str
    mode: str
    capabilities: tuple[str, ...]
    content_sha256: str

    def to_summary(self) -> dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "source": self.source,
            "risk": self.risk,
            "mode": self.mode,
            "capability_count": len(self.capabilities),
            "capabilities": list(self.capabilities),
            "content_sha256": self.content_sha256,
        }


def discover_skill_context(workspace: Path) -> dict[str, Any]:
    root = Path(workspace).resolve()
    skills: list[SkillManifest] = []
    invalid_skills: list[dict[str, str]] = []
    seen_names: set[str] = set()

    onecode_dir = root / ".onecode"
    directory = onecode_dir / "skills"
    if onecode_dir.is_symlink():
        candidate_paths = []
        invalid_skills.append({"path": ".onecode", "reason": "outside_project"})
    elif directory.is_symlink():
        candidate_paths = []
        invalid_skills.append({"path": ".onecode/skills", "reason": "outside_project"})
    else:
        try:
            candidate_paths = _candidate_skill_files(root)
        except OSError as exc:
            candidate_paths = []
            invalid_skills.append({"path": ".onecode/skills", "reason": "list_error", "detail": str(exc)})

    for path in candidate_paths:
        try:
            manifest = _read_skill_manifest(root, path)
        except ValueError as exc:
            invalid_skills.append(_invalid_skill(root, path, str(exc)))
            continue
        if manifest.name in seen_names:
            invalid_skills.append(_invalid_skill(root, path, "duplicate_name"))
            continue
        seen_names.add(manifest.name)
        skills.append(manifest)

    if invalid_skills:
        status = "warning"
        reason = _classification_reason(invalid_skills)
    elif skills:
        status = "ok"
        reason = None
    else:
        status = "missing"
        reason = "no_skills"

    status_code = IchingKernel.classify_skill_context(status, reason)
    transition = IchingKernel.transition(status_code)
    method_only_count = sum(1 for skill in skills if skill.mode == "method_only")
    reference_only_count = sum(1 for skill in skills if skill.mode == "reference_only")

    return {
        "status": status,
        "skills": [skill.to_summary() for skill in skills],
        "invalid_skills": invalid_skills,
        "summary": {
            "skill_count": len(skills),
            "invalid_count": len(invalid_skills),
            "method_only_count": method_only_count,
            "reference_only_count": reference_only_count,
            "element": IchingKernel.TRIGRAM_ELEMENTS[IchingKernel.KAN],
            "yin_yang_pressure": "warning" if invalid_skills else "stable",
        },
        "iching_status_code": status_code,
        "iching_transition_action": transition.action,
        "iching_transition_reason": transition.reason,
        "dispatch_decision": IchingKernel.dispatch_decision(transition),
    }


def public_skill_context(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload.get("status"),
        "summary": payload.get("summary") if isinstance(payload.get("summary"), dict) else {},
        "iching_status_code": payload.get("iching_status_code"),
        "iching_transition_action": payload.get("iching_transition_action"),
        "iching_transition_reason": payload.get("iching_transition_reason"),
        "dispatch_decision": payload.get("dispatch_decision"),
    }


def select_skill_evidence(workspace: Path, task: str, *, max_selected: int = MAX_SELECTED_SKILLS) -> dict[str, Any]:
    skill_context = discover_skill_context(workspace)
    task_tokens = _task_tokens(task)
    selected = []
    for skill in skill_context.get("skills", []):
        if not isinstance(skill, dict):
            continue
        capabilities = skill.get("capabilities")
        if not isinstance(capabilities, list):
            continue
        matched = [
            capability
            for capability in capabilities
            if isinstance(capability, str) and _capability_matches(capability, task_tokens)
        ]
        if not matched:
            continue
        selected.append(
            {
                "name": skill.get("name"),
                "mode": skill.get("mode"),
                "risk": skill.get("risk"),
                "matched_capabilities": matched,
                "content_sha256": skill.get("content_sha256"),
            }
        )
    selected = sorted(
        selected,
        key=lambda item: (
            0 if item.get("mode") == "method_only" else 1,
            str(item.get("name") or ""),
        ),
    )[: max(0, max_selected)]

    if selected:
        selection_reason = "capability_match"
    elif skill_context.get("status") == "missing":
        selection_reason = "skill_context_unavailable"
    else:
        selection_reason = "no_matching_capability"

    evidence = {
        "status": skill_context.get("status"),
        "selection_reason": selection_reason,
        "selected_skills": selected,
        "selected_count": len(selected),
        "skill_context_summary": public_skill_context(skill_context).get("summary", {}),
        "iching_status_code": skill_context.get("iching_status_code"),
        "iching_transition_action": skill_context.get("iching_transition_action"),
        "iching_transition_reason": skill_context.get("iching_transition_reason"),
        "dispatch_decision": skill_context.get("dispatch_decision"),
    }
    evidence["selection_sha256"] = skill_selection_sha256(evidence)
    return evidence


def _candidate_skill_files(root: Path) -> list[Path]:
    directory = root / ".onecode" / "skills"
    if not directory.is_dir():
        return []
    return sorted(
        (path for path in directory.iterdir() if path.is_file() and path.suffix == ".json"),
        key=lambda path: path.name,
    )


def _classification_reason(invalid_skills: list[dict[str, str]]) -> str:
    reasons = {item.get("reason") for item in invalid_skills}
    if "outside_project" in reasons:
        return "outside_project"
    if "duplicate_name" in reasons:
        return "duplicate_name"
    return "invalid_manifest"


def _read_skill_manifest(root: Path, path: Path) -> SkillManifest:
    try:
        resolved = path.resolve()
    except OSError as exc:
        raise ValueError("resolve_error") from exc
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("outside_project") from exc
    try:
        if resolved.stat().st_size > MAX_SKILL_MANIFEST_BYTES:
            raise ValueError("manifest_too_large")
    except ValueError:
        raise
    except OSError as exc:
        raise ValueError("stat_error") from exc

    try:
        text = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("utf8_decode_error") from exc
    except OSError as exc:
        raise ValueError("read_error") from exc

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid_json") from exc
    if not isinstance(payload, dict):
        raise ValueError("non_object_json")

    name = payload.get("name")
    if not isinstance(name, str) or SKILL_NAME_PATTERN.fullmatch(name) is None:
        raise ValueError("invalid_name")

    version = payload.get("version")
    if not isinstance(version, str) or not version.strip() or len(version.strip()) > MAX_SKILL_FIELD_CHARS:
        raise ValueError("invalid_version")

    risk = payload.get("risk")
    if not isinstance(risk, str) or risk not in VALID_RISKS:
        raise ValueError("invalid_risk")

    mode = payload.get("mode")
    if not isinstance(mode, str) or mode not in VALID_MODES:
        raise ValueError("invalid_mode")

    capabilities_raw = payload.get("capabilities")
    if not isinstance(capabilities_raw, list):
        raise ValueError("invalid_capabilities")
    if len(capabilities_raw) > MAX_SKILL_CAPABILITIES:
        raise ValueError("invalid_capabilities")
    if not all(
        isinstance(item, str) and item.strip() and len(item.strip()) <= MAX_SKILL_FIELD_CHARS
        for item in capabilities_raw
    ):
        raise ValueError("invalid_capabilities")
    capabilities = tuple(dict.fromkeys(_safe_token(item) for item in capabilities_raw))
    if not capabilities or not all(capabilities):
        raise ValueError("invalid_capabilities")

    return SkillManifest(
        name=name,
        version=version.strip(),
        source="project",
        risk=risk,
        mode=mode,
        capabilities=capabilities,
        content_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


def _safe_token(value: str) -> str:
    return re.sub(r"[^a-z0-9_:-]+", "_", value.strip().lower().replace("-", "_")).strip("_")


def _task_tokens(value: str) -> set[str]:
    if not isinstance(value, str):
        return set()
    tokens: set[str] = set()
    for item in re.split(r"[^A-Za-z0-9]+", value):
        token = _safe_token(item)
        if not token:
            continue
        tokens.add(token)
        alias = TOKEN_ALIASES.get(token)
        if alias:
            tokens.add(alias)
        if token.endswith("s") and not token.endswith("ss") and len(token) > 3:
            tokens.add(token[:-1])
    return tokens


def _capability_matches(capability: str, task_tokens: set[str]) -> bool:
    if capability in task_tokens:
        return True
    parts = [part for part in re.split(r"[_:-]+", capability) if part]
    return len(parts) > 1 and all(part in task_tokens for part in parts)


def _invalid_skill(root: Path, path: Path, reason: str) -> dict[str, str]:
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        relative = path.as_posix()
    return {"path": relative, "reason": reason}
