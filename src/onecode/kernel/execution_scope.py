"""Execution scope and tool capability policy for bounded autonomous agents.

Provides capability profiling across:
- READ_ONLY: Safe exploratory/planning phase (read_file, inspection commands only, no writes).
- PATCH_GUARDED: Controlled surgical patching (read_file, patch, non-destructive commands).
- FULL_TERMINAL: Standard autonomous engineering session (full tool suite under PathGuard & anti-tamper).
"""
from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Sequence


class ExecutionScope(StrEnum):
    """Scoped tool capabilities for enterprise-grade autonomous execution."""
    READ_ONLY = "read_only"
    PATCH_GUARDED = "patch_guarded"
    FULL_TERMINAL = "full_terminal"


_DESTRUCTIVE_COMMANDS = frozenset({
    "rm", "unlink", "shred", "dd", "mkfs", "format",
    "shutdown", "reboot", "poweroff", "init",
    "kill", "pkill", "killall",
})


def is_destructive_command(command: Sequence[str] | None) -> bool:
    """Detect destructive shell commands that could wipe workspaces or kill system processes."""
    if not command:
        return False
    parts = list(command)
    if len(parts) >= 3 and parts[0] in {"bash", "sh", "/bin/bash", "/bin/sh"} and parts[1] in {"-c", "-lc", "-cl"}:
        cmd_str = parts[2]
    else:
        cmd_str = " ".join(parts)

    tokens = [t.lower() for t in re.findall(r"[A-Za-z0-9_.-]+", cmd_str)]
    if not tokens:
        return False

    first = posixpath.basename(tokens[0])
    if first in _DESTRUCTIVE_COMMANDS:
        return True

    # Check git destructive operations
    if first == "git" and len(tokens) > 1:
        git_sub = tokens[1]
        if git_sub == "reset" and any(arg in {"--hard", "hard"} for arg in tokens[2:]):
            return True
        if git_sub == "clean" and any("-f" in arg for arg in tokens[2:]):
            return True
        if git_sub == "push" and any(arg in {"--force", "-f", "+"} for arg in tokens[2:]):
            return True

    # Check destructive rm variants
    if "rm" in tokens and any(arg in {"-rf", "-fr", "-r", "-f"} for arg in tokens):
        return True

    return False


@dataclass(frozen=True)
class ExecutionScopeDecision:
    """Result of evaluating an action against an ExecutionScope policy."""
    allowed: bool
    reason: str | None
    stderr: str
    hexagram_code: int = 39

    def to_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "stderr": self.stderr,
            "hexagram_code": self.hexagram_code,
        }


class ToolCapabilityPolicy:
    """Enforces capability boundaries based on active ExecutionScope."""

    @staticmethod
    def evaluate(
        scope: ExecutionScope | str,
        action_type: str,
        command: Sequence[str] | None = None,
        *,
        is_inspection: bool = False,
    ) -> ExecutionScopeDecision:
        """Evaluates whether an action is permitted within the given execution scope."""
        try:
            active_scope = ExecutionScope(scope) if isinstance(scope, str) else scope
        except ValueError:
            active_scope = ExecutionScope.FULL_TERMINAL

        if active_scope == ExecutionScope.READ_ONLY:
            if action_type in {"read_file", "finish"}:
                return ExecutionScopeDecision(allowed=True, reason=None, stderr="", hexagram_code=63)
            if action_type == "command":
                if is_inspection:
                    return ExecutionScopeDecision(allowed=True, reason=None, stderr="", hexagram_code=63)
                return ExecutionScopeDecision(
                    allowed=False,
                    reason="scope_violation",
                    stderr=(
                        "Command execution with side effects is forbidden in READ_ONLY execution scope. "
                        "Only read-only inspection commands (ls, grep, find, cat, etc.) are permitted."
                    ),
                    hexagram_code=39,
                )
            if action_type == "patch":
                return ExecutionScopeDecision(
                    allowed=False,
                    reason="scope_violation",
                    stderr=(
                        "Action 'patch' is forbidden in READ_ONLY execution scope. "
                        "This session is restricted to read-only analysis and inspection (Phase 1 planning)."
                    ),
                    hexagram_code=39,
                )
            return ExecutionScopeDecision(
                allowed=False,
                reason="scope_violation",
                stderr=f"Action '{action_type}' is forbidden in READ_ONLY execution scope.",
                hexagram_code=39,
            )

        if active_scope == ExecutionScope.PATCH_GUARDED:
            if action_type in {"read_file", "patch", "write_file", "finish"}:
                return ExecutionScopeDecision(allowed=True, reason=None, stderr="", hexagram_code=63)
            if action_type == "command":
                if is_destructive_command(command):
                    cmd_summary = " ".join(command or ())
                    return ExecutionScopeDecision(
                        allowed=False,
                        reason="destructive_command_denied",
                        stderr=f"Destructive shell command is forbidden in PATCH_GUARDED execution scope: {cmd_summary}.",
                        hexagram_code=39,
                    )
                return ExecutionScopeDecision(allowed=True, reason=None, stderr="", hexagram_code=63)

        # FULL_TERMINAL: all actions permitted subject to downstream anti-tamper and approval gates
        return ExecutionScopeDecision(allowed=True, reason=None, stderr="", hexagram_code=63)
