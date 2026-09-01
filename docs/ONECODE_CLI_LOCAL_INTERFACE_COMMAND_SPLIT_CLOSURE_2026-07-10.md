# OneCode CLI Local Interface Command Split Closure

Date: 2026-07-10

## Objective

Extract the local service and UI command family from the central CLI while
preserving parser, lazy-import, side-effect, error, and exit-code behavior.

## Extracted Commands

`onecode.cli_commands.local_interfaces` owns exactly:

- `serve`;
- `shell`;
- `shell-status`;
- `tui`.

No command, option, provider, default, or alias was added or removed.

## Parser Compatibility

Tests freeze descriptions, option strings, destinations, required flags,
defaults, choices, nargs, action classes, types, and parser-level defaults. The
shell root default continues to evaluate `Path.cwd()` during parser construction.

## Lazy Import and Side-Effect Boundary

The adapter has stdlib-only top-level imports. `onecode.web.api`,
`onecode.tui.app`, and `onecode.shell_launcher` are imported only inside their
selected dispatch branches.

Direct dispatch tests inject fake modules through `sys.modules`. They verify
server arguments, unauthenticated environment mutation, launcher configuration,
launcher exit-code passthrough, parser error conversion, shell-status JSON,
TUI workspace conversion, and model/provider arguments without starting real
services, processes, sockets, browsers, MongoDB, LibreChat, or Textual.

## Structural Result

- `onecode.cli.main()`: 500 lines before this phase, 472 after extraction.
- `onecode.cli.build_parser()`: 214 lines after parser extraction.

Both remain compatibility entry points. Existing source-quality allowlist
entries remain because the functions are still above the global 160-line limit.

## Dependency Boundary

Tests reject top-level OneCode imports in the adapter and reverse imports from
Web, TUI, shell launcher, or kernel modules. The adapter does not own runner,
model, training, benchmark, verifier, sandbox, or evidence persistence paths.

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

LogosGate, PathGuard, approvals, verifier, sandbox, evidence writes, physical
evidence, and historical artifacts remain unchanged.

## Verification Record

Fresh verification after implementation and documentation completion:

```text
Parser and direct interface regression: 48 passed, 1 skipped
Focused interface/Web/runner regression: 168 passed, 1 skipped
Lazy-import proof: Web, TUI, and shell-launcher modules absent after adapter import
Source quality: ok
cli.main line count: 472
build_parser line count: 214
Forbidden formula diff scan: no matches
git diff --check: passed
Full verification: 807 tests passed, 10 skipped
Doctor: ok
Release audit: wheel assets ok
Publish action: not performed
```
