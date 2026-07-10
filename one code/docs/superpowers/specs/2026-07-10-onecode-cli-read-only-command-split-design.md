# OneCode CLI Read-Only Command Split Design

Date: 2026-07-10

## Goal

Reduce the structural risk of `src/onecode/cli.py` by extracting the existing
read-only command family while preserving every public CLI argument, JSON
payload, exit code, execution decision, and I Ching authority boundary.

## Confirmed Scope

The phase extracts exactly five existing commands:

- `inspect`;
- `list-runs`;
- `doctor`;
- `math-audit`;
- `shell-schema`.

`project-status` is not a current CLI command and is not added. `audit-self`,
verifier policy commands, shell launch commands, server commands, runner
commands, training commands, model commands, benchmark commands, and all
write-capable paths remain in `src/onecode/cli.py`.

## Module Boundary

Create:

```text
src/onecode/cli_commands/
  __init__.py
  read_only.py
```

`read_only.py` exposes:

```python
READ_ONLY_COMMANDS: frozenset[str]
register_read_only_commands(subparsers: argparse._SubParsersAction) -> None
dispatch_read_only_command(args: argparse.Namespace) -> int | None
math_audit_payload() -> dict[str, object]
```

`register_read_only_commands()` registers the same parsers and arguments that
currently live in `build_parser()`:

```text
inspect --workspace . --run-id REQUIRED
list-runs --workspace .
doctor
math-audit
shell-schema
```

`dispatch_read_only_command()` returns `None` for commands outside the set and
returns the existing integer exit code after printing the same sorted UTF-8
JSON for handled commands.

## One-Way Dependencies

The allowed direction is:

```text
onecode.cli
-> onecode.cli_commands.read_only
-> kernel diagnostics / run inspection / shell projection / Iching certificates
```

`onecode.cli_commands` must not import:

- `onecode.cli`;
- `onecode.kernel.runner`;
- model-loop or model-provider execution modules;
- training-data or benchmark modules;
- sandbox or verifier execution modules;
- `onecode.web` or `onecode.tui`.

The package is a CLI adapter only. Kernel and Web layers must not import it.

## Parser Integration

`build_parser()` continues to be the public parser factory used by CLI tests,
self-audit, and shell-launcher tests. It creates the root parser and subparser
collection as before, then delegates only the five read-only registrations to
`register_read_only_commands()`.

The parser contract is checked structurally. For each extracted command the
tests freeze:

- command presence;
- option strings;
- destination names;
- required flags;
- defaults;
- choices;
- nargs;
- action class.

No command aliases, help text changes, new defaults, or argument normalization
are introduced.

## Dispatch Integration

Immediately after `parse_args()`, `main()` calls:

```python
read_only_exit_code = dispatch_read_only_command(args)
if read_only_exit_code is not None:
    return read_only_exit_code
```

The five original inline branches are then removed. Remaining branch order and
behavior stay unchanged.

The `None` sentinel is safe because every handled command returns an integer,
including successful exit code `0` and failure exit code `1`.

## Math Audit Preservation

The existing math-audit construction moves verbatim into
`math_audit_payload()`. It continues to call only the existing
`IchingKernel` certificate and energy helpers. Key names, list order, state
count, transition count, accepted mappings, and reference-only mappings remain
unchanged.

The extraction must not cache or precompute certificate output, alter
calculation order in a way that changes results, or introduce fixture-driven
authority.

## Output and Exit-Code Compatibility

- `inspect`: preserves inspection exit code and Shell v4 attachment.
- `list-runs`: preserves exit code `0` and per-run Shell v4 attachment.
- `doctor`: preserves `0` for `status == "ok"`, otherwise `1`.
- `math-audit`: preserves exit code `0` and exact JSON object.
- `shell-schema`: preserves exit code `0` and exact Shell v4 schema fixture.

All output continues to use:

```python
json.dumps(payload, ensure_ascii=False, sort_keys=True)
```

## Bottom-Theory and Safety Boundary

This phase changes only the CLI shell structure. It does not modify or bypass:

```text
yin/yang line bits
-> trigrams
-> five-element generation/control
-> yin/yang pressure and dynamic balance
-> transition
-> dispatch
```

It does not modify runner behavior, LogosGate, PathGuard, approvals, verifier,
sandbox, evidence writes, physical-evidence authority, or historical evidence.

## Testing Strategy

1. Add failing import and parser-contract tests before creating the package.
2. Move parser registration minimally and verify all parser consumers.
3. Add failing direct-dispatch tests before moving command branches.
4. Move one command group without changing output construction.
5. Re-run existing doctor, inspect, list-runs, runner CLI, shell launcher, and
   self-audit tests.
6. Verify import boundaries and source-quality line counts.
7. Run full verification, Doctor, release audit, whitespace checks, and the
   forbidden formula diff scan.

## Acceptance Criteria

1. The five command parser contracts are identical after extraction.
2. Existing stdout JSON and exit-code tests remain unchanged and pass.
3. Unknown commands return `None` from the read-only dispatcher.
4. `main()` no longer contains branches for the five extracted commands and is
   at least 70 lines shorter without expanding into other command families.
5. `onecode.cli_commands` has no forbidden execution or reverse dependencies.
6. No Yin/Yang, trigram, five-element, balance, transition, or dispatch formula
   changes appear in the diff.
7. Focused and full verification, Doctor, release audit, and wheel checks pass.
