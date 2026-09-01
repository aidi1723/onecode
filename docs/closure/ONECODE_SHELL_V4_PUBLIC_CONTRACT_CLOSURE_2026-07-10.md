# OneCode Shell v4 Public Contract Closure

Date: 2026-07-10

## Objective

Freeze the public Shell projection version 4 contract for downstream adapters
without changing the OneCode Agent execution kernel or its safety authority.

## Public Assets

The installable `onecode.contracts` package contains:

- `shell_projection_v4_schema.json`;
- `shell_projection_v4_cases.json`.

The public loaders use `importlib.resources`, decode fresh JSON values on each
call, and expose only versioned contract data. `pyproject.toml` declares both
JSON files as package data so the same assets are available from built wheels.

## Fixed Cases

The v4 case fixture covers exactly six named projections:

1. `completed_full`;
2. `denied_full`;
3. `halted_resumable`;
4. `corrupt_evidence`;
5. `completed_wal_only`;
6. `legacy_missing_fields`.

Inputs use deterministic run IDs and relative evidence paths. They contain no
timestamps, random IDs, credentials, host paths, or raw user prompts.

## Cross-Entry-Point Contract

One canonical schema fixture is compared by exact object equality with:

- `shell_projection_schema()`;
- CLI `onecode shell-schema`;
- direct Web `handle_onecode_shell_schema()`;
- HTTP `/v1/onecode/shell/schema`.

Each case expected object is compared exactly with
`project_run_to_shell(case["input"])`, including top-level and nested field
order, null behavior, compact message, and evidence mode.

## Compatibility

- Missing `rule_schema` continues to mean `onecode-iching-v1`.
- Missing mutation evidence produces null counts/statuses and an empty changed
  band list without fabricating facts.
- WAL-only `rsv`, `bm`, `ssr`, `ssc`, and `ssh` aliases retain their bounded
  named projection.
- Historical WAL, checkpoint, manifest, ledger, training, and earlier contract
  evidence is not rewritten.

## Bottom-Theory and Authority Preservation

The fixtures follow this one-way boundary:

```text
runtime evidence
-> project_run_to_shell()
-> Shell v4 public output
-> fixture comparison
```

Production shell code does not import `onecode.contracts`. Fixture values do
not calculate or override severity, next action, transition, dispatch, resume,
delivery, approval, verifier, sandbox, or physical-evidence authority.

No change is made to:

```text
yin/yang line bits
-> trigrams
-> five-element generation/control
-> yin/yang pressure and dynamic balance
-> transition
-> dispatch
```

## Verification Record

Fresh verification after implementation and documentation completion:

```text
Contract/shell focused tests: 23 passed
CLI/Web/inspect focused tests: 176 passed
Source quality: ok
Forbidden formula diff scan: no matches
git diff --check: passed
Full verification: 787 tests passed, 10 skipped
Doctor: ok
Release audit: wheel assets ok
Wheel direct listing: both Shell v4 JSON fixtures present
Publish action: not performed
```

The direct wheel listing reported:

```text
onecode/contracts/shell_projection_v4_cases.json
onecode/contracts/shell_projection_v4_schema.json
```
