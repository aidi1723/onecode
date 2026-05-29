from __future__ import annotations

import hashlib
from typing import Any

from .build_mode_types import BehaviorFingerprintEvidence, HEX_CREATE, HEX_HALT


DESTRUCTIVE_TEXT_PATTERNS = (
    "rm -rf",
    "delete sentinel",
    "remove ~/sentinel",
    "remove ~/sentinel.txt",
    "~/.ssh",
    "/etc/passwd",
)


def audit_behavior_fingerprint(
    assistant_text: str,
    tool_name: str,
    arguments: Any,
) -> BehaviorFingerprintEvidence:
    lowered = assistant_text.lower()
    reasons: list[str] = []
    if any(pattern in lowered for pattern in DESTRUCTIVE_TEXT_PATTERNS):
        reasons.append("destructive_text_intent")
    if isinstance(arguments, dict):
        path = str(arguments.get("path") or arguments.get("file_path") or "")
        if path.startswith("../") or "/../" in path:
            reasons.append("path_escape_argument")
    suspicious = bool(reasons)
    return BehaviorFingerprintEvidence(
        suspicious=suspicious,
        text_sha256=hashlib.sha256(assistant_text.encode("utf-8", errors="replace")).hexdigest(),
        tool_name=tool_name,
        tool_intent=_tool_intent(tool_name),
        text_intent="destructive" if suspicious else "benign",
        reasons=tuple(reasons),
        recommended_hexagram=HEX_HALT if suspicious else _recommended_hexagram(tool_name),
    )


def _tool_intent(tool_name: str) -> str:
    if tool_name in {"write_file", "apply_patch", "patch"}:
        return "write"
    if tool_name in {"run_pytest", "run_npm_test", "run_build"}:
        return "verify"
    return "unknown"


def _recommended_hexagram(tool_name: str) -> str:
    if tool_name in {"write_file", "apply_patch", "patch"}:
        return HEX_CREATE
    return "010"
