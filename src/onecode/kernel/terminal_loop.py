"""Open-ended multi-step terminal loop for SWE-bench exploration and interactive problem solving.

This module implements a stateful terminal agent session:
1. Multi-turn interactive execution: the model observes shell output, reads files,
   applies surgical patches, runs exploration commands, and re-tests.
2. Anti-tamper protection: strict isolation of immutable preset test paths.
3. Stagnation and loop governance: detects repeated command failures (陀罗暗滞)
   and forces strategy pivoting.
4. Fault localization coupling: integrates SymbolLocator to direct exploration
   directly to true implementation modules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import time
from typing import Any, Callable

from onecode.kernel.execution_tools import ToolRegistry, default_tool_registry
from onecode.kernel.path_guard import PathGuard
from onecode.kernel.preset_tests import is_preset_test_path
from onecode.kernel.symbol_locator import SymbolLocator

_FORBIDDEN_TEST_CMD_PATTERNS = (
    re.compile(r"\brm\s+.*tests?/", re.IGNORECASE),
    re.compile(r"\bsed\s+.*-i.*tests?/", re.IGNORECASE),
    re.compile(r"\b>\s*tests?/", re.IGNORECASE),
    re.compile(r"\b>>\s*tests?/", re.IGNORECASE),
    re.compile(r"\btee\s+.*tests?/", re.IGNORECASE),
)


@dataclass(frozen=True)
class TerminalAction:
    """An action emitted by the agent model during a terminal turn."""
    action_type: str  # "command", "patch", "read_file", "finish"
    command: tuple[str, ...] = field(default_factory=tuple)
    path: str = ""
    search_block: str = ""
    replace_block: str = ""
    start_line: int | None = None
    end_line: int | None = None
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"action_type": self.action_type}
        if self.command:
            data["command"] = list(self.command)
        if self.path:
            data["path"] = self.path
        if self.search_block:
            data["search_block"] = self.search_block
        if self.replace_block:
            data["replace_block"] = self.replace_block
        if self.start_line is not None:
            data["start_line"] = self.start_line
        if self.end_line is not None:
            data["end_line"] = self.end_line
        if self.explanation:
            data["explanation"] = self.explanation
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TerminalAction:
        action_type = str(data.get("action_type") or data.get("action") or "finish").strip().lower()
        cmd = data.get("command") or data.get("cmd") or data.get("argv") or []
        if isinstance(cmd, str):
            cmd = cmd.split()
        elif not isinstance(cmd, (list, tuple)):
            cmd = []

        return cls(
            action_type=action_type,
            command=tuple(str(x) for x in cmd),
            path=str(data.get("path") or "").strip(),
            search_block=str(data.get("search_block") or ""),
            replace_block=str(data.get("replace_block") or ""),
            start_line=int(data["start_line"]) if "start_line" in data and str(data["start_line"]).isdigit() else None,
            end_line=int(data["end_line"]) if "end_line" in data and str(data["end_line"]).isdigit() else None,
            explanation=str(data.get("explanation") or data.get("reason") or "").strip(),
        )


@dataclass(frozen=True)
class TerminalObservation:
    """The result of executing an action in the environment."""
    action_type: str
    status: str  # "ok", "error", "blocked", "halted"
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    output: str = ""
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "status": self.status,
            "exit_code": self.exit_code,
            "stdout": self.stdout[:4000],
            "stderr": self.stderr[:4000],
            "output": self.output[:4000],
            "reason": self.reason,
        }


@dataclass(frozen=True)
class TerminalStep:
    """A full step recording action, observation, and hexagram assessment."""
    turn_index: int
    action: TerminalAction
    observation: TerminalObservation
    hexagram_code: int = 63  # 63: 乾为天, 39: 山天大畜, 40: 火地晋
    timestamp_ns: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_index": self.turn_index,
            "action": self.action.to_dict(),
            "observation": self.observation.to_dict(),
            "hexagram_code": self.hexagram_code,
            "timestamp_ns": self.timestamp_ns,
        }


class TerminalSession:
    """Manages multi-turn stateful terminal interaction in the workspace sandbox."""

    def __init__(
        self,
        workspace: Path,
        task: str,
        *,
        max_turns: int = 15,
        tool_registry: ToolRegistry | None = None,
        require_modification: bool = True,
    ) -> None:
        self.workspace = workspace.resolve()
        self.task = task
        self.max_turns = max_turns
        self.tool_registry = tool_registry or default_tool_registry()
        self.require_modification = require_modification
        self.steps: list[TerminalStep] = []
        self.is_finished = False
        self.finish_explanation = ""
        self.last_command_signature = ""
        self.consecutive_stalls = 0
        self.last_read_signature = ""
        self.consecutive_read_stalls = 0

    def is_command_tampering(self, cmd_tokens: tuple[str, ...]) -> bool:
        cmd_str = " ".join(cmd_tokens)
        return any(pat.search(cmd_str) for pat in _FORBIDDEN_TEST_CMD_PATTERNS)

    def execute_action(self, action: TerminalAction) -> TerminalObservation:
        """Executes an action under sandbox security policies and records the observation."""
        if action.action_type == "finish":
            has_modified = any(s.action.action_type == "patch" and s.observation.status == "ok" for s in self.steps)
            if self.require_modification and not has_modified:
                obs = TerminalObservation(
                    action_type="finish",
                    status="error",
                    reason="unmodified_workspace",
                    stderr="Cannot finish: no implementation files have been modified or patched yet. First inspect files, apply patches, and verify.",
                )
                self._record_step(action, obs, hexagram_code=39)
                return obs
            self.is_finished = True
            self.finish_explanation = action.explanation or "Task completed by agent."
            obs = TerminalObservation(
                action_type="finish",
                status="ok",
                output=self.finish_explanation,
            )
            self._record_step(action, obs, hexagram_code=63)
            return obs

        if action.action_type == "patch":
            self.last_command_signature = ""
            self.consecutive_stalls = 0
            self.last_read_signature = ""
            self.consecutive_read_stalls = 0
            obs = self._handle_patch(action)
            hex_code = 63 if obs.status == "ok" else 39
            self._record_step(action, obs, hexagram_code=hex_code)
            return obs

        if action.action_type == "read_file":
            self.last_command_signature = ""
            self.consecutive_stalls = 0
            obs = self._handle_read_file(action)
            hex_code = 63 if obs.status == "ok" else (40 if obs.status in {"blocked", "halted"} else 39)
            self._record_step(action, obs, hexagram_code=hex_code)
            return obs

        if action.action_type == "command":
            self.last_read_signature = ""
            self.consecutive_read_stalls = 0
            obs = self._handle_command(action)
            hex_code = 63 if obs.status == "ok" else (40 if obs.status == "blocked" else 39)
            self._record_step(action, obs, hexagram_code=hex_code)
            return obs

        obs = TerminalObservation(
            action_type=action.action_type,
            status="error",
            reason="unknown_action_type",
            stderr=f"Unknown action_type '{action.action_type}'. Valid types: command, patch, read_file, finish.",
        )
        self._record_step(action, obs, hexagram_code=39)
        return obs

    def _handle_patch(self, action: TerminalAction) -> TerminalObservation:
        if not action.path:
            return TerminalObservation(action_type="patch", status="error", reason="empty_path", stderr="Path cannot be empty.")
        if is_preset_test_path(action.path):
            return TerminalObservation(
                action_type="patch",
                status="blocked",
                reason="preset_test_immutable",
                stderr="Anti-tamper protection active: Modification of test files under tests/ is strictly prohibited. Patch implementation files instead.",
            )
        tool = self.tool_registry.get("patch_text")
        if tool is None:
            return TerminalObservation(action_type="patch", status="error", reason="tool_not_found", stderr="patch_text tool is missing.")
        try:
            res = tool.execute(
                {"path": action.path, "search_block": action.search_block, "replace_block": action.replace_block},
                self.workspace,
            )
            status = "ok" if res.get("status") in {"ok", "completed"} else "error"
            return TerminalObservation(
                action_type="patch",
                status=status,
                output=res.get("summary") or f"Successfully patched {action.path}",
                stderr=res.get("reason") or "",
            )
        except Exception as ex:
            return TerminalObservation(action_type="patch", status="error", reason="patch_failed", stderr=str(ex))

    def _handle_read_file(self, action: TerminalAction) -> TerminalObservation:
        if not action.path:
            return TerminalObservation(action_type="read_file", status="error", reason="empty_path", stderr="Path cannot be empty.")
        if PathGuard.is_sensitive_read_path(Path(action.path)):
            return TerminalObservation(action_type="read_file", status="blocked", reason="sensitive_read_denied", stderr="Access to sensitive path denied.")
        target = self.workspace / action.path
        if not target.is_file():
            return TerminalObservation(action_type="read_file", status="error", reason="file_not_found", stderr=f"File '{action.path}' does not exist.")
        read_sig = f"{action.path}:{action.start_line or 1}:{action.end_line or 0}"
        if read_sig == self.last_read_signature:
            self.consecutive_read_stalls += 1
            if self.consecutive_read_stalls >= 2:
                return TerminalObservation(
                    action_type="read_file",
                    status="halted",
                    reason="stagnation_loop",
                    stderr=f"Stagnation warning (陀罗暗滞·化权破滞): Detected identical repeated read of '{action.path}'. Do not repeat the same read; run verification tests with 'command' or submit 'finish'.",
                )
        else:
            self.last_read_signature = read_sig
            self.consecutive_read_stalls = 0
        try:
            lines = target.read_text(encoding="utf-8").splitlines()
            total_lines = len(lines)
            start = max(1, action.start_line or 1)
            end = min(total_lines, action.end_line or (start + 200))
            selected = lines[start - 1 : end]
            numbered = [f"{i + start:4d} | {line}" for i, line in enumerate(selected)]
            out = f"## {action.path} (lines {start}-{end} of {total_lines})\n" + "\n".join(numbered)
            return TerminalObservation(action_type="read_file", status="ok", output=out)
        except Exception as ex:
            return TerminalObservation(action_type="read_file", status="error", reason="read_error", stderr=str(ex))

    def _handle_command(self, action: TerminalAction) -> TerminalObservation:
        if not action.command:
            return TerminalObservation(action_type="command", status="error", reason="empty_command", stderr="Command cannot be empty.")
        if self.is_command_tampering(action.command):
            return TerminalObservation(
                action_type="command",
                status="blocked",
                reason="preset_test_immutable",
                stderr="Anti-tamper protection active: Shell commands modifying tests/ are forbidden.",
            )

        cmd_sig = " ".join(action.command)
        if cmd_sig == self.last_command_signature and self.steps and self.steps[-1].observation.status == "error":
            self.consecutive_stalls += 1
            if self.consecutive_stalls >= 2:
                return TerminalObservation(
                    action_type="command",
                    status="halted",
                    reason="stagnation_loop",
                    stderr="Stagnation warning (陀罗暗滞·化权破滞): Detected identical repeated failing command. Do not repeat the same command; inspect diagnostics and pivot your approach.",
                )
        else:
            self.last_command_signature = cmd_sig
            self.consecutive_stalls = 0

        tool = self.tool_registry.get("run_command")
        if tool is None:
            return TerminalObservation(action_type="command", status="error", reason="tool_not_found", stderr="run_command tool is missing.")
        try:
            res = tool.execute({"argv": list(action.command), "timeout_seconds": 60}, self.workspace)
            code = res.get("returncode")
            status = "ok" if code == 0 else "error"
            return TerminalObservation(
                action_type="command",
                status=status,
                exit_code=code,
                stdout=res.get("stdout") or "",
                stderr=res.get("stderr") or "",
            )
        except Exception as ex:
            return TerminalObservation(action_type="command", status="error", reason="command_execution_error", stderr=str(ex))

    def _record_step(self, action: TerminalAction, observation: TerminalObservation, hexagram_code: int) -> None:
        step = TerminalStep(
            turn_index=len(self.steps) + 1,
            action=action,
            observation=observation,
            hexagram_code=hexagram_code,
            timestamp_ns=time.time_ns(),
        )
        self.steps.append(step)

    def render_turn_prompt(self, *, include_fault_hints: bool = True) -> str:
        """Formats the prompt for the next turn, providing history, observations, and symbols."""
        sections: list[str] = [
            "You are the OneCode Autonomous Terminal Agent in an active exploration loop.",
            f"User Task: {self.task}",
            f"Current Turn: {len(self.steps) + 1} of {self.max_turns}",
            "",
            "Available Actions (return strict JSON object with 'action_type'):",
            "1. Command: {\"action_type\":\"command\", \"command\":[\"pytest\", \"-k\", \"...\"], \"explanation\":\"...\"}",
            "2. Read File: {\"action_type\":\"read_file\", \"path\":\"src/...\", \"start_line\":1, \"end_line\":100, \"explanation\":\"...\"}",
            "3. Patch: {\"action_type\":\"patch\", \"path\":\"src/...\", \"search_block\":\"<exact>\", \"replace_block\":\"<fixed>\", \"explanation\":\"...\"}",
            "4. Finish: {\"action_type\":\"finish\", \"explanation\":\"Verification passed and all criteria satisfied.\"}",
            "",
            "Rules & Policies:",
            "- Anti-tamper: All paths under tests/ are strictly immutable. Only patch non-test implementation source files.",
            "- Verification: Use 'command' to run existing tests to verify your hypotheses before and after patching.",
            "- Focus: When confident that the tests pass and the solution is complete, submit 'finish'.",
        ]

        if include_fault_hints:
            recent_errs = "\n".join(
                s.observation.stderr + "\n" + s.observation.stdout
                for s in self.steps[-3:]
            )
            if recent_errs:
                locator = SymbolLocator(self.workspace)
                locs = locator.locate_fault(recent_errs, max_candidates=3)
                if locs:
                    sections.append("")
                    sections.append("Fault Localization Hints (天相印绶·符号溯源定位):")
                    for loc in locs:
                        if not loc.is_test_file:
                            sections.append(
                                f"- Recommended target: '{loc.file_path}', symbol '{loc.symbol_name}' "
                                f"(lines {loc.line_start}-{loc.line_end}, confidence {loc.confidence:.2f}). Reason: {loc.reason}"
                            )

        has_applied_patch = any(s.action.action_type == "patch" and s.observation.status == "ok" for s in self.steps)
        if has_applied_patch:
            sections.append("")
            sections.append("Status Directive: You have already applied a code patch. Avoid redundant re-reading of the same file. Proceed to run verification tests with 'command' or submit 'finish' to complete the task.")

        if self.steps:
            sections.append("")
            sections.append("Execution History:")
            for i, s in enumerate(self.steps[-6:]):
                is_latest = (i == len(self.steps[-6:]) - 1)
                act = s.action
                obs = s.observation
                sections.append(f"Turn {s.turn_index}: Action={act.action_type} Status={obs.status}")
                if act.action_type == "command":
                    sections.append(f"  Command: {' '.join(act.command)} (exit_code={obs.exit_code})")
                    if obs.stdout:
                        sections.append(f"  Stdout tail: {obs.stdout[-1200:].strip()}")
                    if obs.stderr:
                        sections.append(f"  Stderr tail: {obs.stderr[-1200:].strip()}")
                elif act.action_type == "patch":
                    sections.append(f"  Patch path={act.path} result={obs.output or obs.stderr}")
                elif act.action_type == "read_file":
                    sections.append(f"  Read {act.path}")
                    if obs.output:
                        preview_limit = 4000 if is_latest else 400
                        sections.append(f"  Content:\n{obs.output[:preview_limit]}")

        sections.append("")
        sections.append("Respond with a single JSON object containing your next action.")
        return "\n".join(sections)


def run_terminal_session(
    task: str,
    workspace: Path,
    provider: Any,
    *,
    max_turns: int = 15,
    require_modification: bool = True,
    on_step: Callable[[TerminalStep], None] | None = None,
) -> dict[str, Any]:
    """Runs a multi-turn open-ended terminal exploration loop until finish or turn exhaustion."""
    session = TerminalSession(workspace, task, max_turns=max_turns, require_modification=require_modification)

    for turn in range(max_turns):
        prompt = session.render_turn_prompt()
        response_text: str | None = None
        last_provider_error: Exception | None = None
        for attempt in range(2):
            try:
                response_text = provider.complete(prompt) if hasattr(provider, "complete") else str(provider(prompt))
                break
            except Exception as ex:
                last_provider_error = ex
                if attempt == 0:
                    time.sleep(1.0)
        if response_text is None:
            return {
                "status": "halted",
                "reason": "provider_error",
                "error": str(last_provider_error),
                "turns_completed": len(session.steps),
                "steps": [s.to_dict() for s in session.steps],
            }

        # Parse JSON action from response
        action = _parse_model_action(response_text)
        obs = session.execute_action(action)
        if on_step is not None and session.steps:
            on_step(session.steps[-1])

        if session.is_finished:
            return {
                "status": "completed",
                "reason": "agent_finished",
                "explanation": session.finish_explanation,
                "turns_completed": len(session.steps),
                "steps": [s.to_dict() for s in session.steps],
            }

        if obs.status == "halted":
            return {
                "status": "halted",
                "reason": obs.reason or "stagnation_halt",
                "turns_completed": len(session.steps),
                "steps": [s.to_dict() for s in session.steps],
            }

    return {
        "status": "halted",
        "reason": "turn_limit_exhausted",
        "turns_completed": len(session.steps),
        "steps": [s.to_dict() for s in session.steps],
    }


def _parse_model_action(text: str) -> TerminalAction:
    """Robustly extracts JSON action from raw model text."""
    decoder = json.JSONDecoder()
    clean_text = text.strip()
    match = re.search(r"\{[\s\S]*\}", clean_text)
    if match:
        idx = match.start()
        try:
            parsed, _ = decoder.raw_decode(clean_text[idx:])
            if isinstance(parsed, dict):
                return TerminalAction.from_dict(parsed)
        except json.JSONDecodeError:
            pass

    return TerminalAction(
        action_type="command",
        command=("git", "status"),
        explanation="Default fallback command after JSON parse error.",
    )
