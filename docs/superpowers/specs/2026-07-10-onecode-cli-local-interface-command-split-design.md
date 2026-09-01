# OneCode CLI Local Interface Command Split Design

Date: 2026-07-10

## Goal

Extract the existing local interface command family from `onecode.cli` while
preserving parser contracts, lazy imports, environment mutation timing,
launcher behavior, error handling, and all kernel and safety authority.

## Confirmed Scope

The phase extracts exactly four existing commands:

- `serve`;
- `shell`;
- `shell-status`;
- `tui`.

The phase does not start a server, browser, MongoDB, LibreChat, or TUI during
tests. It does not change shell-launcher implementation, Web API implementation,
TUI implementation, runner behavior, model behavior, or command availability.

## Module Boundary

Create:

```text
src/onecode/cli_commands/local_interfaces.py
```

The module exposes:

```python
LOCAL_INTERFACE_COMMANDS: frozenset[str]
register_local_interface_commands(subparsers: argparse._SubParsersAction) -> None
dispatch_local_interface_command(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> int | None
```

The dispatcher returns `None` for unhandled commands and the original integer
exit code for handled commands.

## Parser Contract

`register_local_interface_commands()` moves the existing parser construction
without changing registration order, descriptions, option strings,
destinations, types, defaults, choices, actions, or `set_defaults()` values.

### `serve`

```text
--host                         default 127.0.0.1
--port                         type int, default 19080
--allow-unauthenticated-local  store_true
```

The existing description is preserved.

### `shell`

The existing options and defaults remain unchanged, including:

- `--onecode-root` using `str(Path.cwd())` at parser construction time;
- local OneCode/LibreChat/Mongo port defaults;
- local API token and preview credentials;
- `--show-credentials` as `store_true`;
- `--no-browser` writing `open_browser=False`;
- parser default `open_browser=True`.

### `shell-status`

The shared shell configuration options remain unchanged. Parser defaults remain
`open_browser=False` and `show_credentials=True`.

### `tui`

`workspace`, `model`, and the full provider choice list remain unchanged. No
new provider alias or default is introduced.

## Lazy Import Boundary

The module must not import `onecode.web.api`, `onecode.tui.app`, or
`onecode.shell_launcher` at module import time. These imports remain inside the
matching dispatch branch so importing `onecode.cli` does not load optional UI
dependencies or initialize service code.

Tests inspect `sys.modules` after importing the adapter and use AST checks to
reject top-level imports of those modules.

## Dispatch Compatibility

### `serve`

The branch lazily imports `run_server`. When
`allow_unauthenticated_local` is true, it sets:

```text
ONECODE_ALLOW_UNAUTHENTICATED=true
```

immediately before calling `run_server(host=args.host, port=args.port)`. It
returns `0` after the call. When the flag is false, it does not create or delete
the environment variable.

### `shell`

The branch lazily imports `config_from_args` and `launch_shell`, passes the
resulting configuration exactly once, and returns the launcher's integer result.
`FileNotFoundError` and `RuntimeError` continue to call `parser.error(str(exc))`,
which preserves argparse stderr and `SystemExit(2)` behavior.

### `shell-status`

The branch lazily imports `config_from_args` and `shell_status`, prints sorted
UTF-8 JSON, and returns `0` only when `result["status"] == "ok"`; all other
statuses return `1`.

### `tui`

The branch lazily imports `run_tui`, converts a non-null workspace string to
`Path`, passes model and provider as before, and returns `0`.

## Mock and Side-Effect Safety

Direct dispatcher tests replace lazy-loaded modules in `sys.modules` with
bounded fake modules. Tests prove call arguments, environment behavior, output,
exit codes, and error conversion without opening sockets, spawning processes,
opening browsers, reading credentials, or initializing Textual.

The existing shell-launcher, venv entrypoint, Web API, and TUI tests remain part
of focused regression.

## One-Way Dependency Boundary

The adapter may use only stdlib modules at top level. It must not import runner,
model execution, training, benchmark, verifier, sandbox, evidence persistence,
kernel formulas, Web, TUI, or shell-launcher modules at top level.

Web, TUI, shell-launcher, and kernel modules must not import
`onecode.cli_commands.local_interfaces`.

## Structural Target

The approved four-command extraction should remove the direct branches from
`main()` and the matching parser block from `build_parser()`. Structural tests
record the actual reduction rather than forcing extraction of unrelated command
families. Existing source-quality allowlist entries remain until functions fall
below global thresholds.

## Bottom-Theory and Safety Preservation

This phase changes only CLI adapter structure. It does not modify:

```text
yin/yang line bits
-> trigrams
-> five-element generation/control
-> yin/yang pressure and dynamic balance
-> transition
-> dispatch
```

It does not alter LogosGate, PathGuard, approvals, verifier, sandbox, evidence
writes, physical-evidence authority, or historical artifacts.

## Acceptance Criteria

1. All four parser contracts remain identical.
2. Imports remain lazy and tests perform no real local-interface startup.
3. Environment mutation, calls, JSON, errors, and exit codes remain unchanged.
4. Unknown commands return `None` from the dispatcher.
5. `main()` and `build_parser()` contain no direct branches/registrations for
   the four commands and are materially shorter.
6. No forbidden dependency or core formula change appears in the diff.
7. Focused and full verification, Doctor, release audit, and wheel checks pass.
