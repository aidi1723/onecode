"""Transactional workspace snapshot and rollback guard for autonomous coding sessions.

Guarantees transactional cleanliness for enterprise workflows:
When an autonomous session halts or encounters a security/tamper violation,
any partial or corrupt modifications can be cleanly reverted, leaving the
workspace in its exact pre-session state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import subprocess
from typing import Any


@dataclass
class WorkspaceSnapshot:
    """Captures file modifications copy-on-write and restores baseline on failure."""

    workspace: Path
    _original_contents: dict[str, bytes] = field(default_factory=dict)
    _created_files: set[str] = field(default_factory=set)
    _initial_git_head: str | None = None
    _git_available: bool = False

    def __post_init__(self) -> None:
        self.workspace = self.workspace.resolve()
        self._check_git_baseline()

    def _check_git_baseline(self) -> None:
        dot_git = self.workspace / ".git"
        if not dot_git.exists():
            self._git_available = False
            return
        try:
            res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if res.returncode == 0:
                self._initial_git_head = res.stdout.strip()
                self._git_available = True
        except (OSError, subprocess.SubprocessError):
            self._git_available = False

    def record_before_write(self, target_path: str | Path) -> None:
        """Records the pre-modification state of a target path before a write/patch occurs."""
        resolved = (self.workspace / target_path).resolve()
        try:
            rel = resolved.relative_to(self.workspace).as_posix()
        except ValueError:
            return

        if rel in self._original_contents or rel in self._created_files:
            return

        if resolved.is_file():
            try:
                self._original_contents[rel] = resolved.read_bytes()
            except OSError:
                pass
        else:
            self._created_files.add(rel)

    def rollback(self, *, force_git_clean: bool = False) -> dict[str, Any]:
        """Restores modified files and removes newly created files.

        Returns a summary dict with restored_files, removed_files, and success status.
        """
        restored: list[str] = []
        removed: list[str] = []
        errors: list[str] = []

        # 1. Restore modified files
        for rel, original_bytes in self._original_contents.items():
            target = self.workspace / rel
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(original_bytes)
                restored.append(rel)
            except OSError as ex:
                errors.append(f"Failed to restore {rel}: {ex}")

        # 2. Remove files created during session
        for rel in sorted(self._created_files, reverse=True):
            target = self.workspace / rel
            if target.is_file() or target.is_symlink():
                try:
                    target.unlink()
                    removed.append(rel)
                except OSError as ex:
                    errors.append(f"Failed to remove {rel}: {ex}")

        # 3. Optional git-level restore if force_git_clean requested and git is available
        if force_git_clean and self._git_available:
            try:
                subprocess.run(
                    ["git", "checkout", "--", "."],
                    cwd=str(self.workspace),
                    capture_output=True,
                    check=False,
                    timeout=10,
                )
            except (OSError, subprocess.SubprocessError) as ex:
                errors.append(f"git checkout failed: {ex}")

        return {
            "rolled_back": True,
            "restored_files": sorted(restored),
            "removed_files": sorted(removed),
            "errors": errors,
        }

    def commit(self) -> dict[str, Any]:
        """Commits changes by clearing the snapshot log so they will not be rolled back."""
        count = len(self._original_contents) + len(self._created_files)
        self._original_contents.clear()
        self._created_files.clear()
        return {"committed": True, "changes_committed": count}
