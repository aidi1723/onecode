# OneCode Shell v4 Public Contract Design

Date: 2026-07-10

## Goal

Freeze the public OneCode shell projection version 4 contract with distributable
JSON fixtures and cross-entry-point contract tests while preserving all I Ching
kernel formulas and execution authority.

## Foundation Boundary

The existing direction remains authoritative:

```text
runtime evidence
-> project_run_to_shell()
-> shell v4 projection
-> public fixture comparison
```

Fixtures are output contracts only. Production code must not load a fixture to
calculate severity, next action, rule state, balance state, transition, or
dispatch. There is no reverse path from fixture data into runtime decisions.

The phase must not modify:

- Yin/Yang line-bit interpretation;
- trigram encoding or schema conversion;
- five-element generation, control, relation, or modulation;
- Yin/Yang pressure, balance mask, or dynamic balance;
- `IchingKernel.transition()`;
- `IchingKernel.dispatch_decision()`;
- LogosGate, PathGuard, approval, verifier, sandbox, or physical-evidence
  dominance.

## Public Contract Package

Create a small `onecode.contracts` package containing read-only JSON assets:

```text
src/onecode/contracts/
  __init__.py
  shell_projection_v4_schema.json
  shell_projection_v4_cases.json
```

Package data is declared explicitly in `pyproject.toml` so downstream adapters
can inspect the same fixtures from an installed wheel.

`shell_projection_v4_schema.json` is the canonical serialized output of
`shell_projection_schema()` for version 4. It freezes top-level field order,
nested field order, declared types, enum values, and descriptions.

`shell_projection_v4_cases.json` contains six named cases. Each case stores one
bounded input object and its exact expected projection:

1. `completed_full`;
2. `denied_full`;
3. `halted_resumable`;
4. `corrupt_evidence`;
5. `completed_wal_only`;
6. `legacy_missing_fields`.

Fixtures use deterministic relative evidence paths such as
`.onecode/runs/completed-full/ledger.json`; no temporary directories,
timestamps, random IDs, credentials, raw prompts, or mutable host paths are
allowed.

## Contract Loader

`onecode.contracts` exposes pure asset-loading helpers based on
`importlib.resources`:

```python
load_shell_projection_v4_schema() -> dict[str, object]
load_shell_projection_v4_cases() -> list[dict[str, object]]
```

The helpers return freshly decoded JSON values on every call so callers cannot
mutate shared module state. They validate only the fixture envelope needed by
tests and downstream readers: schema is an object; cases is a list of objects
with non-empty `name`, object `input`, and object `expected` fields.

Production shell projection modules do not import `onecode.contracts`.

## Cross-Entry-Point Contract

Contract tests compare:

- `shell_projection_schema()` with the schema fixture;
- `project_run_to_shell(case["input"])` with each expected fixture;
- CLI `onecode shell-schema` with the same schema fixture;
- direct Web `handle_onecode_shell_schema()` with the same schema fixture;
- HTTP `/v1/onecode/shell/schema` with the same schema fixture.

Exact equality is required. A field addition, removal, reorder, type change,
enum change, nested-key drift, null-rule drift, or message drift fails the
contract test. Intentional future changes require a new shell projection
version and new versioned fixture files rather than silently rewriting v4.

## Compatibility Cases

`legacy_missing_fields` proves that absent `rule_schema` remains interpreted as
`onecode-iching-v1`, absent mutation evidence projects null counts/statuses and
an empty changed-band list, and absent control/delivery/resume evidence remains
bounded rather than fabricated.

`completed_wal_only` proves the compact `rsv`, `bm`, `ssh`, `ssr`, and `ssc`
aliases project into the same public field names while preserving the compact
WAL evidence mode.

## Authority Isolation

Tests create paired inputs differing only in descriptive evidence fields:

- mutation summary or WAL mutation tuple;
- evidence paths and profile hash;
- skill-selection display evidence.

They assert that `severity`, `next_action`, transition action/reason, and
dispatch decision remain unchanged. The contract records existing output; it
does not authorize new control variables.

## Documentation and Closure

Update `README.md` with the location and purpose of the versioned public
fixtures. Add a closure report and changelog entry recording fixture coverage,
wheel inclusion, compatibility behavior, authority isolation, and fresh test
evidence.

Historical WAL, checkpoint, manifest, ledger, training, and prior contract
files are never rewritten.

## Acceptance Criteria

1. Six public v4 cases exactly match `project_run_to_shell()` output.
2. Python, CLI, direct Web, and HTTP schema outputs exactly match one fixture.
3. Fixtures are readable through `importlib.resources` from the built wheel.
4. Legacy missing fields and WAL-only aliases retain current semantics.
5. Descriptive evidence changes do not change shell or kernel authority.
6. No forbidden formula or authority function changes appear in the diff.
7. Focused tests, full verification, Doctor, release audit, and whitespace
   checks pass.
