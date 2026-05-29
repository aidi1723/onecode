from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .build_mode_decay import compute_decay_gate
from .build_mode_types import (
    HEX_CORRECT,
    HEX_CREATE,
    HEX_HALT,
    HEX_INSPECT,
    HEX_ISOLATE,
    HEX_PROMPT,
    HEX_RETURN,
    HEX_VERIFY,
)


@dataclass(frozen=True)
class ElementProfile:
    hexagram: str
    trigram_name: str
    element: str
    resource_role: str
    control_role: str


BAGUA_ELEMENT_MAP: dict[str, ElementProfile] = {
    HEX_RETURN: ElementProfile(HEX_RETURN, "坤", "土", "archive_lockdown", "asset_manifest"),
    HEX_VERIFY: ElementProfile(HEX_VERIFY, "震", "木", "active_test_motion", "verification_impulse"),
    HEX_ISOLATE: ElementProfile(HEX_ISOLATE, "坎", "水", "stream_relay", "network_buffer"),
    HEX_PROMPT: ElementProfile(HEX_PROMPT, "巽", "木", "derivative_watchdog", "decay_audit"),
    HEX_HALT: ElementProfile(HEX_HALT, "艮", "土", "hard_stop", "privilege_revocation"),
    HEX_INSPECT: ElementProfile(HEX_INSPECT, "离", "火", "failure_dehydration", "causal_fingerprint"),
    HEX_CORRECT: ElementProfile(HEX_CORRECT, "兑", "金", "soft_rewrite", "permission_correction"),
    HEX_CREATE: ElementProfile(HEX_CREATE, "乾", "金", "schema_injection", "scoped_privilege"),
}


@dataclass(frozen=True)
class FireDigest:
    text: str
    exception: str
    line_refs: tuple[str, ...]
    signatures: tuple[str, ...]


@dataclass(frozen=True)
class ElementDecision:
    hexagram: str
    action: str
    element: str
    metadata: dict[str, Any]


def element_profile(hexagram: str) -> ElementProfile:
    try:
        return BAGUA_ELEMENT_MAP[hexagram]
    except KeyError as exc:
        raise ValueError(f"unknown hexagram: {hexagram}") from exc


class FiveElementsDynamicBalancer:
    """V3 resource balancer layered on top of the Build Mode hexagram FSM."""

    def __init__(self, required_artifacts: list[str] | tuple[str, ...]):
        self.required_artifacts = tuple(required_artifacts)

    def align(
        self,
        payload: dict[str, Any],
        workspace: str | Path,
        current_hexagram: str,
        pytest_log: str,
        *,
        previous_failure_summary: str = "",
    ) -> ElementDecision:
        root = Path(workspace).resolve()
        missing = self.missing_artifacts(root)
        if pytest_log and "passed" not in pytest_log.lower():
            digest = self.fire_digest(root, pytest_log)
            if previous_failure_summary:
                current_failure = "\n".join(_failure_lines(pytest_log)) or digest.text
                decay = compute_decay_gate(previous_failure_summary, current_failure)
                if decay.deadlock_suspected:
                    return _decision(
                        hexagram=HEX_HALT,
                        action="expert_handoff",
                        element="木",
                        metadata={
                            "decay": {
                                "similarity_ratio": decay.similarity_ratio,
                                "dynamic_threshold": decay.dynamic_threshold,
                                "deadlock_suspected": decay.deadlock_suspected,
                            },
                            "fire_digest": digest.text,
                        },
                    )
            return _decision(
                hexagram=HEX_CREATE,
                action="scoped_repair_writer",
                element="火",
                metadata={"fire_digest": digest.text},
            )
        if missing:
            return _decision(
                hexagram=HEX_CREATE,
                action="scoped_writer",
                element="土",
                metadata={"missing_artifacts": list(missing)},
            )
        if current_hexagram != HEX_RETURN:
            return _decision(
                hexagram=HEX_VERIFY,
                action="canonical_tester",
                element="金",
                metadata={"missing_artifacts": []},
            )
        return _decision(
            hexagram=HEX_RETURN,
            action="archive_lockdown",
            element="土",
            metadata={"missing_artifacts": []},
        )

    def missing_artifacts(self, workspace: str | Path) -> tuple[str, ...]:
        root = Path(workspace)
        return tuple(path for path in self.required_artifacts if not (root / path).exists())

    def fire_digest(self, workspace: str | Path, raw_log: str, *, max_chars: int = 900) -> FireDigest:
        root = Path(workspace).resolve()
        exception = _exception_name(raw_log)
        line_refs = _line_refs(raw_log)
        signatures = _interface_signatures(root, line_refs)
        sections = [
            "V3 Fire Digest",
            f"Exception: {exception or '(unknown)'}",
            "Lines: " + (", ".join(line_refs) if line_refs else "(none)"),
            "Failures:",
            "\n".join(_failure_lines(raw_log)) or "(none)",
            "Interface Signatures:",
            "\n".join(signatures) if signatures else "(none)",
        ]
        return FireDigest(
            text=_clip("\n".join(sections), max_chars),
            exception=exception,
            line_refs=line_refs,
            signatures=signatures,
        )


class YinYangFiveElementsEngine:
    """Compatibility facade for V3 callers that need payload, hexagram, action."""

    def __init__(self, required_artifacts: list[str] | tuple[str, ...], failure_threshold: int = 2):
        self.balancer = FiveElementsDynamicBalancer(required_artifacts)
        self.failure_threshold = failure_threshold

    def enforce_balance_flow(
        self,
        payload: dict[str, Any],
        workspace: str | Path,
        current_hexagram: str,
        last_pytest_output: str,
        *,
        previous_failure_summary: str = "",
    ) -> tuple[dict[str, Any], str, str]:
        decision = self.balancer.align(
            payload,
            workspace,
            current_hexagram,
            last_pytest_output,
            previous_failure_summary=previous_failure_summary,
        )
        return payload, decision.hexagram, decision.action


def _exception_name(text: str) -> str:
    matches = re.findall(r"\b([A-Za-z_][\w.]*?(?:Error|Exception|Timeout))\b", text)
    return matches[-1] if matches else ""


def _decision(hexagram: str, action: str, element: str, metadata: dict[str, Any]) -> ElementDecision:
    enriched = dict(metadata)
    enriched["cosmology"] = _cosmology_dict(hexagram)
    return ElementDecision(hexagram=hexagram, action=action, element=element, metadata=enriched)


def _cosmology_dict(hexagram: str) -> dict[str, str]:
    profile = element_profile(hexagram)
    scope = _scope_for_hexagram(hexagram)
    return {
        "hexagram": hexagram,
        "trigram_name": profile.trigram_name,
        "force": _force_for_hexagram(hexagram),
        "scope": scope,
        "scope_name": _scope_name(scope),
        "element": profile.element,
        "resource_role": profile.resource_role,
        "permission_role": profile.control_role,
    }


def _force_for_hexagram(hexagram: str) -> str:
    return "yang" if hexagram in {HEX_PROMPT, HEX_CORRECT, HEX_CREATE} else "yin"


def _scope_for_hexagram(hexagram: str) -> str:
    if hexagram == HEX_RETURN:
        return "00"
    if hexagram == HEX_PROMPT:
        return "01"
    if hexagram in {HEX_VERIFY, HEX_ISOLATE, HEX_HALT, HEX_INSPECT}:
        return "10"
    return "11"


def _scope_name(scope: str) -> str:
    return {"00": "太阴", "01": "少阳", "10": "少阴", "11": "太阳"}[scope]


def _line_refs(text: str) -> tuple[str, ...]:
    refs: list[str] = []
    seen: set[str] = set()
    pattern = re.compile(r'File "([^"]+)", line (\d+)')
    compact_pattern = re.compile(r"\b([\w.-]+\.py):(\d+)(?:\s+in\s+[\w_]+)?")
    matches = [(Path(path).name, line) for path, line in pattern.findall(text)]
    matches.extend(compact_pattern.findall(text))
    for path, line in matches:
        ref = f"{Path(path).name}:{line}"
        if ref not in seen:
            seen.add(ref)
            refs.append(ref)
    return tuple(refs[:8])


def _failure_lines(text: str) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("FAILED "):
            continue
        normalized = re.sub(r"\s+", " ", line)
        if normalized not in seen:
            seen.add(normalized)
            lines.append(normalized)
    return lines[:6]


def _interface_signatures(root: Path, line_refs: tuple[str, ...]) -> tuple[str, ...]:
    target_names = {ref.split(":", 1)[0] for ref in line_refs}
    signatures: list[str] = []
    for target in sorted(target_names):
        for path in root.rglob(target):
            if path.is_file() and path.suffix == ".py":
                signatures.extend(_signatures_for_file(root, path))
                break
    return tuple(signatures[:16])


def _signatures_for_file(root: Path, path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return []
    relative = path.relative_to(root)
    signatures: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            signatures.append(f"{relative}:{node.lineno} {prefix} {node.name}{_args_signature(node.args)}")
        elif isinstance(node, ast.ClassDef):
            signatures.append(f"{relative}:{node.lineno} class {node.name}")
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    signatures.append(
                        f"{relative}:{child.lineno} {node.name}.{child.name}{_args_signature(child.args)}"
                    )
    return signatures


def _args_signature(args: ast.arguments) -> str:
    parts = [arg.arg for arg in [*args.posonlyargs, *args.args]]
    if args.vararg:
        parts.append(f"*{args.vararg.arg}")
    parts.extend(arg.arg for arg in args.kwonlyargs)
    if args.kwarg:
        parts.append(f"**{args.kwarg.arg}")
    return "(" + ", ".join(parts) + ")"


def _clip(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    if max_chars <= 12:
        return text[:max_chars]
    return text[: max_chars - 12].rstrip() + "\n...[clipped]"
