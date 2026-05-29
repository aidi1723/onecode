"""OneWord TUI conversational interface."""

from __future__ import annotations

import os
import json
import re
import urllib.request
import urllib.error
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Input, Static
from textual.binding import Binding
from textual.worker import Worker, WorkerState

from onecode.kernel.runner import run_task
from onecode.kernel.model_loop import run_model_task
from onecode.kernel.model_provider import api_key_from_env, build_provider_config


# --- Config ---

APP_VERSION = "0.1.0-alpha"
DEFAULT_MODEL = "gpt-5.5"
DEFAULT_WORKSPACE = Path("/private/tmp/oneword-tui-live")
DEFAULT_ENDPOINT = "http://10.0.0.184:6780/v1/chat/completions"
API_KEY_WARNING = "提示: 未检测到 OPENAI_API_KEY。AI 对话功能已禁用，但本地接入命令仍可正常执行。"

TASK_MARKERS = (
    "create", "generate", "implement", "fix", "write", "build",
    "test", "add", "remove", "delete", "update", "refactor",
)
PATH_MARKERS = ("src/", "tests/", ".py", ".md", ".json")
RICH_TAG_PATTERN = re.compile(r"\[/?[a-zA-Z][^\]]*\]")


def resolve_api_key(provider_kind: str = "chat") -> str | None:
    key = api_key_from_env(provider_kind=provider_kind)
    return key if key else None


def resolve_endpoint(provider_kind: str = "chat") -> str:
    endpoint = os.environ.get("ONECODE_ENDPOINT", "").strip()
    if endpoint:
        return endpoint
    if provider_kind == "chat":
        return DEFAULT_ENDPOINT
    return build_provider_config(provider_kind, endpoint=None, model=None).endpoint


def chat_completion(messages: list[dict], model: str, endpoint: str, api_key: str, timeout: float = 60) -> str:
    body = json.dumps({"model": model, "messages": messages}).encode("utf-8")
    req = urllib.request.Request(
        endpoint, data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"API {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Connection failed: {exc.reason}") from exc
    choices = payload.get("choices", [])
    if not choices:
        raise RuntimeError("Empty response from model")
    return choices[0].get("message", {}).get("content", "")


def classify_input(text: str) -> str:
    stripped = text.strip().lower()
    if stripped.startswith("/"):
        return "command"
    if any(m in stripped for m in TASK_MARKERS) and any(m in stripped for m in PATH_MARKERS):
        return "task"
    return "chat"


def plain_text(text: str) -> str:
    return RICH_TAG_PATTERN.sub("", text)


def format_execution_trace(trace: dict) -> str:
    success = bool(trace.get("success"))
    status = "[green]completed[/green]" if success else "[red]failed[/red]"
    lines = [f"Execution: {status}"]
    if trace.get("reason"):
        lines.append(f"reason: {trace['reason']}")

    for step in trace.get("step_results", []):
        step_line = f"  step {step.get('step_id', '?')}: {step.get('status', '?')}"
        if step.get("reason"):
            step_line += f" | {step['reason']}"
        lines.append(step_line)
        for tool in step.get("tool_results", []):
            tool_status = "ok" if tool.get("success") else "failed"
            tool_line = f"    tool {tool.get('tool_name', '?')}: {tool_status}"
            if tool.get("reason"):
                tool_line += f" | {tool['reason']}"
            lines.append(tool_line)

    runner_results = trace.get("runner_results", [])
    if runner_results:
        last = runner_results[-1]
        lines.append(f"  ledger: {last.get('run_id', '?')} {last.get('status', '?')}")
        completed = int(last.get("completed_count") or 0)
        skipped = int(last.get("skipped_count") or 0)
        failed = int(last.get("failed_count") or 0)
        if completed + skipped + failed > 0:
            lines.append(f"    completed:{completed} skipped:{skipped} failed:{failed}")
        if last.get("iching_transition_action"):
            lines.append(
                f"    action: {last.get('iching_transition_action')} | "
                f"reason: {last.get('iching_transition_reason')}"
            )
    return "\n".join(lines)


# --- Widgets ---

class UserMessage(Static):
    """User message - right-aligned with prompt indicator."""
    pass


class AssistantMessage(Static):
    """Assistant response - left-aligned with role label."""
    pass


class SystemMessage(Static):
    """System/status message - dimmed, centered."""
    pass


class Divider(Static):
    """Thin separator between message groups."""
    pass


class WelcomePanel(Static):
    """Startup welcome panel with OneWord runtime context."""

    def __init__(self, app: "OneCodeApp") -> None:
        self.renderable = self._build_renderable(app)
        super().__init__(self.renderable)

    @staticmethod
    def _build_renderable(app: "OneCodeApp") -> str:
        api_status = "已配置 API 密钥" if app.api_key else "未配置 API 密钥"
        return (
            f"一字诀 OneWord v{APP_VERSION}\n\n"
            f"    [red]▄████▄[/]       接入大模型: {app.model}  •  状态: {api_status}\n"
            f"  [yellow]▄█▀[/]    [green]▀█▄[/]     运行路径: {app.workspace}\n"
            "  [magenta]█[/]   [cyan]○[/]    [blue]█[/]\n"
            "  [green]▀█▄[/]    [yellow]▄█▀[/]     ▍ 快速开始\n"
            "    [red]▀████▀[/]         输入 /help 查看一字诀指令与接入工具集\n\n"
            "                 ▍ 最近活动\n"
            "                   暂无最近活动记录"
        )


# --- Main App ---

class OneCodeApp(App):
    """OneCode - conversational kernel interface."""

    CSS_PATH = "styles.tcss"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Exit", priority=True),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("escape", "quit", "Exit"),
    ]

    def __init__(
        self,
        workspace: Path | None = None,
        model: str | None = None,
        provider_kind: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.workspace = (workspace or DEFAULT_WORKSPACE).resolve()
        self.provider_kind = provider_kind or os.environ.get("ONECODE_PROVIDER", "").strip() or "chat"
        provider_model = None if self.provider_kind == "chat" else build_provider_config(
            self.provider_kind,
            endpoint=None,
            model=None,
        ).model
        self.model = model or os.environ.get("ONECODE_MODEL", "").strip() or provider_model or DEFAULT_MODEL
        self.endpoint = resolve_endpoint(self.provider_kind)
        self.api_key = resolve_api_key(self.provider_kind)
        self.transcript_path = self.workspace / ".onecode" / "tui-transcript.txt"
        self.last_output_path = self.workspace / ".onecode" / "tui-last-output.txt"
        self.messages: list[dict] = [
            {"role": "system", "content": (
                "You are OneCode assistant. Help users with code tasks concisely. "
                "When users describe file operations, suggest /task commands."
            )}
        ]

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="chat-log")
        yield Input(placeholder="> ", id="input")
        yield Footer()

    def on_mount(self) -> None:
        self._startup()
        if not self.api_key:
            self._system(f"[yellow]{API_KEY_WARNING}[/yellow]")
        self.query_one("#input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""
        self._user(text)
        self._handle(text)

    def action_clear(self) -> None:
        self.query_one("#chat-log", VerticalScroll).remove_children()
        self.messages = [self.messages[0]]
        self._startup()
        self._system("Cleared.")

    # --- Display helpers ---

    def _startup(self) -> None:
        log = self.query_one("#chat-log", VerticalScroll)
        log.mount(WelcomePanel(self))
        log.scroll_end(animate=False)

    def _user(self, text: str) -> None:
        log = self.query_one("#chat-log", VerticalScroll)
        log.mount(UserMessage(f"[b]> {text}[/b]"))
        self._record_transcript("user", text, update_last=False)
        log.scroll_end(animate=False)

    def _assistant(self, text: str) -> None:
        log = self.query_one("#chat-log", VerticalScroll)
        log.mount(AssistantMessage(text))
        self._record_transcript("assistant", text)
        log.scroll_end(animate=False)

    def _system(self, text: str) -> None:
        log = self.query_one("#chat-log", VerticalScroll)
        log.mount(SystemMessage(text))
        self._record_transcript("system", text)
        log.scroll_end(animate=False)

    def _error(self, text: str) -> None:
        log = self.query_one("#chat-log", VerticalScroll)
        log.mount(SystemMessage(f"[red]{text}[/red]"))
        self._record_transcript("error", text)
        log.scroll_end(animate=False)

    def _divider(self) -> None:
        log = self.query_one("#chat-log", VerticalScroll)
        log.mount(Divider("─" * 60))
        log.scroll_end(animate=False)

    def _record_transcript(self, role: str, text: str, update_last: bool = True) -> None:
        clean = plain_text(text).strip()
        self.transcript_path.parent.mkdir(parents=True, exist_ok=True)
        line = f"[{role}] {clean}\n"
        with self.transcript_path.open("a", encoding="utf-8") as handle:
            handle.write(line)
        if update_last:
            self.last_output_path.write_text(line, encoding="utf-8")

    # --- Input routing ---

    def _handle(self, text: str) -> None:
        low = text.strip().lower()

        if low == "/help":
            self._show_help()
        elif low == "/doctor":
            self._run_doctor()
        elif low == "/status":
            self._show_status()
        elif low == "/clear":
            self.action_clear()
        elif low in ("/runs", "/list-runs"):
            self._run_list_runs()
        elif low == "/export":
            self._system(f"Transcript: {self.transcript_path}")
        elif low in ("/export-last", "/last-output"):
            self._system(f"Last output: {self.last_output_path}")
        elif low.startswith("/inspect "):
            self._run_inspect(text.split(maxsplit=1)[1])
        elif low.startswith("/task ") or low.startswith("/run "):
            self._run_kernel_task(text.split(maxsplit=1)[1])
        elif low.startswith("/write "):
            self._run_write(text[7:].strip())
        elif low.startswith("/plan "):
            self._run_plan(text[6:].strip())
        elif low.startswith("/exec-plan "):
            self._run_execution_plan(text[11:].strip())
        elif low.startswith("/model"):
            arg = text[6:].strip()
            if arg:
                self.model = arg
                self._system(f"Model: {self.model}")
            else:
                self._system(f"Current model: {self.model}")
        elif low in ("/exit", "/quit"):
            self.exit()
        elif low.startswith("/"):
            self._error(f"Unknown command: {text.split()[0]}. Try /help")
        else:
            route = classify_input(text)
            if route == "task":
                self._run_kernel_task(text)
            else:
                self._run_chat(text)

    def _show_help(self) -> None:
        self._assistant(
            "[b]Commands[/b]\n"
            "  /task <desc>       Run through OneCode kernel\n"
            "  /write path=content  Write a file\n"
            "  /plan file.json    Execute task plan\n"
            "  /exec-plan file.json Execute multi-step plan\n"
            "  /inspect <run-id>  Inspect run evidence\n"
            "  /runs              List all runs\n"
            "  /export            Show transcript file path\n"
            "  /export-last       Show last output file path\n"
            "  /doctor            Smoke checks\n"
            "  /model [name]      Show/switch model\n"
            "  /status            Show config\n"
            "  /clear             Clear history\n"
            "  /exit              Quit\n\n"
            "Or just type naturally to chat.\n"
            "Code/file requests auto-route to kernel."
        )

    def _show_status(self) -> None:
        key_s = "[green]set[/green]" if self.api_key else "[red]missing[/red]"
        self._assistant(
            f"Workspace: {self.workspace}\n"
            f"Model: {self.model}\n"
            f"Endpoint: {self.endpoint}\n"
            f"API Key: {key_s}"
        )

    # --- Chat ---

    def _run_chat(self, text: str) -> None:
        if not self.api_key:
            self._error("No API key. Set OPENAI_API_KEY or use /task for kernel ops.")
            return
        self.messages.append({"role": "user", "content": text})
        self.run_worker(self._chat_worker, name="chat", thread=True)

    def _chat_worker(self) -> str:
        return chat_completion(
            self.messages, self.model, self.endpoint, self.api_key, timeout=60
        )

    # --- Kernel operations ---

    def _run_kernel_task(self, task: str) -> None:
        if not task:
            self._error("Usage: /task <description>")
            return
        self._system("[dim]Planning and running task...[/dim]")
        self.run_worker(lambda: self._task_worker(task), name="task", thread=True)

    def _task_worker(self, task: str) -> dict:
        return run_model_task(
            task,
            workspace=self.workspace,
            model=self.model,
            api_key=self.api_key,
            provider_kind=self.provider_kind,
            endpoint=self.endpoint,
        )

    def _run_write(self, arg: str) -> None:
        if "=" not in arg or not arg.split("=", 1)[0].strip():
            self._error("Usage: /write path=content")
            return
        path, content = arg.split("=", 1)
        self._system(f"[dim]Writing {path.strip()}...[/dim]")
        self.run_worker(lambda: self._write_worker(path.strip(), content), name="task", thread=True)

    def _write_worker(self, path: str, content: str) -> dict:
        return run_task(
            f"write {path}", workspace=self.workspace,
            write_path=path, write_content=content,
        )

    def _run_plan(self, path: str) -> None:
        if not path:
            self._error("Usage: /plan <file.json>")
            return
        p = Path(path) if Path(path).is_absolute() else self.workspace / path
        if not p.exists():
            self._error(f"Not found: {p}")
            return
        self._system("[dim]Executing plan...[/dim]")
        self.run_worker(lambda: self._plan_worker(p), name="task", thread=True)

    def _plan_worker(self, plan_file: Path) -> dict:
        from onecode.kernel.task_plan import load_task_plan
        task, write_texts, evidence = load_task_plan(plan_file)
        return run_task(task, workspace=self.workspace, write_texts=write_texts, run_metadata=evidence)

    def _run_execution_plan(self, path: str) -> None:
        if not path:
            self._error("Usage: /exec-plan <file.json>")
            return
        p = Path(path) if Path(path).is_absolute() else self.workspace / path
        if not p.exists():
            self._error(f"Not found: {p}")
            return
        self._system("[dim]Executing multi-step plan...[/dim]")
        self.run_worker(lambda: self._execution_plan_worker(p), name="execution-plan", thread=True)

    def _execution_plan_worker(self, plan_file: Path) -> dict:
        from onecode.kernel.execution_engine import execute_plan
        from onecode.kernel.execution_plan_loader import execution_trace_to_dict, load_execution_plan

        plan = load_execution_plan(plan_file)
        trace = execute_plan(plan, workspace=self.workspace)
        return execution_trace_to_dict(trace)

    def _run_doctor(self) -> None:
        self._system("[dim]Running doctor...[/dim]")
        self.run_worker(self._doctor_worker, name="doctor", thread=True)

    def _doctor_worker(self) -> dict:
        from onecode.cli import run_doctor
        return run_doctor()

    def _run_inspect(self, run_id: str) -> None:
        self.run_worker(lambda: self._inspect_worker(run_id.strip()), name="inspect", thread=True)

    def _inspect_worker(self, run_id: str) -> dict:
        from onecode.cli import inspect_run
        _, result = inspect_run(self.workspace, run_id)
        return result

    def _run_list_runs(self) -> None:
        self.run_worker(self._list_runs_worker, name="list-runs", thread=True)

    def _list_runs_worker(self) -> dict:
        from onecode.cli import list_runs
        return list_runs(self.workspace)

    # --- Result handlers ---

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.SUCCESS:
            result = event.worker.result
            if result is None:
                return
            name = event.worker.name
            if name == "chat":
                self._handle_chat_reply(result)
            elif name == "doctor":
                self._handle_doctor(result)
            elif name == "inspect":
                self._handle_inspect(result)
            elif name == "list-runs":
                self._handle_list_runs(result)
            elif name == "execution-plan":
                self._handle_execution_trace(result)
            else:
                self._handle_task(result)
        elif event.state == WorkerState.ERROR:
            self._error(str(event.worker.error))

    def _handle_chat_reply(self, reply: str) -> None:
        self.messages.append({"role": "assistant", "content": reply})
        self._assistant(reply)

    def _handle_doctor(self, result: dict) -> None:
        status = result.get("status", "?")
        checks = result.get("checks", [])
        lines = []
        for c in checks:
            icon = "[green]pass[/green]" if c["passed"] else "[red]FAIL[/red]"
            lines.append(f"  {icon} {c['name']}")
        color = "green" if status == "ok" else "red"
        self._assistant(f"Doctor: [{color}]{status}[/{color}]\n" + "\n".join(lines))

    def _handle_task(self, result: dict) -> None:
        if isinstance(result.get("execution_trace"), dict):
            self._handle_execution_trace(result["execution_trace"])
            return
        st = result.get("status", "?")
        rid = result.get("run_id", "?")
        action = result.get("iching_transition_action", "")
        reason = result.get("iching_transition_reason", "")
        c = result.get("completed_count", 0)
        s = result.get("skipped_count", 0)
        f = result.get("failed_count", 0)
        color = "green" if st == "completed" else "red" if st in ("denied", "halted") else "cyan"
        lines = [f"[{color}]{st}[/{color}] run:{rid}"]
        if action:
            lines.append(f"  action: {action} | reason: {reason}")
        if c + s + f > 0:
            lines.append(f"  completed:{c} skipped:{s} failed:{f}")
        if result.get("repaired"):
            lines.append(
                "  repair: "
                f"attempts={result.get('repair_attempt_count', 0)} "
                f"initial={result.get('initial_status')} | {result.get('initial_reason')}"
            )
        self._assistant("\n".join(lines))

    def _handle_execution_trace(self, result: dict) -> None:
        self._assistant(format_execution_trace(result))

    def _handle_inspect(self, result: dict) -> None:
        lines = [f"[b]{result.get('run_id','?')}[/b] ({result.get('status','?')})"]
        if result.get("reason"):
            lines.append(f"  reason: {result['reason']}")
        assets = result.get("assets", [])
        if assets:
            for a in assets[:6]:
                lines.append(f"  {a.get('status','?')}: {a.get('path','?')}")
            if len(assets) > 6:
                lines.append(f"  ...+{len(assets)-6} more")
        self._assistant("\n".join(lines))

    def _handle_list_runs(self, result: dict) -> None:
        runs = result.get("runs", [])
        if not runs:
            self._assistant("No runs found.")
            return
        lines = [f"[b]{len(runs)} runs:[/b]"]
        for r in runs[-10:]:
            st = r.get("status", "?")
            color = "green" if st == "completed" else "red" if st in ("denied","halted") else "dim"
            lines.append(f"  [{color}]{st:10}[/{color}] {r.get('run_id','?')}")
        self._assistant("\n".join(lines))


def run_tui(
    workspace: Path | None = None,
    model: str | None = None,
    provider_kind: str | None = None,
) -> None:
    """Launch the OneCode TUI."""
    app = OneCodeApp(workspace=workspace, model=model, provider_kind=provider_kind)
    app.run()
