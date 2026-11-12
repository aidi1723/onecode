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
    "kill", "pkill", "killall", "truncate",
})

_DESTRUCTIVE_SCRIPT_PATTERNS = re.compile(
    r"\b(shutil\.rmtree|os\.remove|os\.unlink|pathlib.*\.unlink|unlink|rmdir|rmSync|unlinkSync|rmdirSync)\b"
)


def _extract_command_string(command: Sequence[str] | None) -> str:
    if not command:
        return ""
    parts = list(command)
    if len(parts) >= 3 and parts[0] in {"bash", "sh", "/bin/bash", "/bin/sh"} and parts[1] in {"-c", "-lc", "-cl"}:
        return parts[2]
    return " ".join(parts)


def is_catastrophic_command(command: Sequence[str] | None) -> bool:
    """Detect catastrophic commands that wipe root, home, or workspace, zero disks, or trigger forkbombs."""
    cmd_str = _extract_command_string(command)
    if not cmd_str:
        return False
    cmd_lower = cmd_str.lower()

    if re.search(r":\(\)\s*\{\s*:\|:&\s*\};:", cmd_str) or re.search(r":\s*\{\s*:\|:&\s*\};:", cmd_str):
        return True
    if re.search(r"\b(mkfs(\.[a-z0-9]+)?|fdisk|parted)\b", cmd_lower):
        return True
    if re.search(r"\bdd\s+if=/dev/(zero|urandom|null)\s+of=/dev/", cmd_lower):
        return True
    if re.search(r"\b(shutdown|reboot|poweroff|init\s+0|init\s+6)\b", cmd_lower):
        return True
    # Total workspace or system tree wiping: rm -rf /, rm -rf ., rm -rf *, rm -rf src
    if re.search(r"\brm\s+(-[a-z]*r[a-z]*f?|-[a-z]*f[a-z]*r?)\s+(/|/\*|~|\$home|\.|\*|src|src/)([\s/;&|]|$)", cmd_lower):
        return True
    if re.search(r"\bfind\b.*(?<!\w)-delete\b", cmd_lower):
        return True
    if re.search(r"\bpython[0-9]*\s+-c\s+.*shutil\.rmtree\(['\"](\.|\*|src)['\"]\)", cmd_lower):
        return True
    if re.search(r"\bchmod\s+(-[a-z]*r[a-z]*\s+)?000\s+(/|\.)", cmd_lower):
        return True
    if re.search(r"\bps\s+.*(\$ppid|\bppid\b)", cmd_lower) or re.search(r"/proc/(\$ppid|[0-9]+)/environ", cmd_lower):
        return True
    return False


def is_destructive_command(command: Sequence[str] | None) -> bool:
    """Detect destructive shell commands that could wipe workspaces, reset git state, or kill system processes."""
    cmd_str = _extract_command_string(command)
    if not cmd_str:
        return False

    if is_catastrophic_command(command):
        return True

    # Check for shell redirection clobber / truncation: : > file
    if re.search(r"(^|[;&|])\s*:\s*>\s*\S+", cmd_str):
        return True

    sub_cmds = re.split(r"[;&|\n]+", cmd_str)
    for sub in sub_cmds:
        tokens = [t.lower() for t in re.findall(r"[^\s;|<>&\"']+", sub)]
        if not tokens:
            continue

        first = posixpath.basename(tokens[0])
        if first in _DESTRUCTIVE_COMMANDS:
            return True

        if first == "xargs" and any(tok in {"rm", "unlink", "shred"} for tok in tokens[1:]):
            return True

        if first == "find":
            if "-delete" in tokens or ("-exec" in tokens and any(tok in {"rm", "unlink"} for tok in tokens)):
                return True

        if first in {"rsync"} and any("--delete" in tok for tok in tokens[1:]):
            return True

        if first in {"tar"} and "--remove-files" in tokens[1:]:
            return True

        if first == "chmod" and any("-r" in tok for tok in tokens[1:]) and any("000" in tok for tok in tokens[1:]):
            return True

        # Destructive inline interpreter execution
        if first in {"python", "python3", "perl", "node", "ruby"}:
            if any(flag in tokens[1:] for flag in {"-c", "-e"}):
                if _DESTRUCTIVE_SCRIPT_PATTERNS.search(sub):
                    return True

        # Git destructive operations
        if first == "git" and len(tokens) > 1:
            git_sub = tokens[1]
            if git_sub == "reset" and any(arg in {"--hard", "hard", "--merge"} for arg in tokens[2:]):
                return True
            if git_sub == "clean" and any("-f" in arg for arg in tokens[2:]):
                return True
            if git_sub == "checkout" and any(arg in {".", "-f", "--force"} for arg in tokens[2:]):
                return True
            if git_sub == "restore" and any(arg in {".", "--worktree", "--staged"} for arg in tokens[2:]):
                return True
            if git_sub == "stash" and any(arg in {"drop", "clear"} for arg in tokens[2:]):
                return True
            if git_sub == "branch" and any(arg in {"-d", "-d"} for arg in tokens[2:]):
                return True
            if git_sub == "push":
                if any(arg in {"--force", "-f", "--force-with-lease"} or arg.startswith("+") for arg in tokens[2:]):
                    return True

        if "rm" in tokens and any(arg in {"-rf", "-fr", "-r", "-f"} or arg == "rm" for arg in tokens):
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

        # FULL_TERMINAL: all standard dev tools permitted; catastrophic host or workspace destruction is blocked
        if action_type == "command" and is_catastrophic_command(command):
            cmd_summary = " ".join(command or ())
            return ExecutionScopeDecision(
                allowed=False,
                reason="catastrophic_command_denied",
                stderr=f"Catastrophic host or workspace destruction command is strictly forbidden: {cmd_summary}.",
                hexagram_code=40,
            )
        return ExecutionScopeDecision(allowed=True, reason=None, stderr="", hexagram_code=63)
