# OneCode CLI Read-Only Command Split Closure

Date: 2026-07-10

## Objective

Reduce the structural risk of the OneCode CLI shell by extracting existing
read-only parser registration and dispatch without changing public behavior or
the Agent execution kernel.

## Extracted Commands

The focused `onecode.cli_commands.read_only` adapter owns exactly:

- `inspect`;
- `list-runs`;
- `doctor`;
- `math-audit`;
- `shell-schema`.

No new command was added. `project-status` remains a Web API surface and was not
introduced into the CLI.

## Compatibility Boundary

`onecode.cli.build_parser()` remains the parser entry point used by the CLI,
self-audit, and shell-launcher consumers. `onecode.cli.main()` remains the
console entry point. Existing kernel service imports remain available from
`onecode.cli` for compatibility.

The extracted parser contract freezes command names, option strings,
destinations, required flags, defaults, choices, nargs, and action classes.
Output remains sorted UTF-8 JSON with the original exit-code rules.

## One-Way Dependency Boundary

The new adapter depends only on:

- diagnostics;
- run inspection;
- Shell projection;
- existing I Ching certificate helpers used by `math-audit`.

Tests reject reverse or execution dependencies on CLI, Web, TUI, runner,
models, training, benchmark, sandbox, or verifier modules.

## Structural Result

`onecode.cli.main()` decreased from 581 lines to 500 lines. The original
430-line estimate was not enforced because the approved five-command scope
contains 81 removable lines; reaching 430 would require extracting additional
command families. The regression boundary requires fewer than 510 lines and at
least a 70-line reduction.

## Bottom-Theory and Safety Preservation

This phase changes the CLI shell only. It does not modify:

```text
yin/yang line bits
-> trigrams
-> five-element generation/control
-> yin/yang pressure and dynamic balance
-> transition
-> dispatch
```

Runner behavior, LogosGate, PathGuard, approvals, verifier, sandbox, evidence
writes, physical evidence, and historical evidence remain unchanged.

## Verification Record

Fresh verification after implementation and documentation completion:

```text
Parser and initial command regression: 55 passed
Focused CLI, shell-launcher, and self-audit regression: 130 passed
Source quality: ok
cli.main line count: 500 (previously 581)
Forbidden formula diff scan: no matches
git diff --check: passed
Full verification: 794 tests passed, 1 skipped
Doctor: ok
Release audit: wheel assets ok
Publish action: not performed
```

The initial focused command referenced the nonexistent module
`tests.test_self_audit`; the documented command was corrected to the existing
`tests.test_self_audit_cli` module. This was a plan-command defect, not a code
or runtime failure.
