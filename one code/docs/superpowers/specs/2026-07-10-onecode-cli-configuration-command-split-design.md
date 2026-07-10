# OneCode CLI Configuration Command Split Design

Date: 2026-07-10

## Goal

Extract verifier-policy and model-configuration CLI commands into a focused
adapter while preserving path safety, secret handling, parser behavior, JSON
output, errors, exit codes, and all execution-kernel authority.

## Confirmed Scope

The phase extracts exactly:

- `list-verifier-presets`;
- `init-verifier-policy`;
- `config set-model`;
- `config show`;
- `config discover-models`.

The phase does not change verifier execution, model-loop execution, provider
selection for runs, Web configuration endpoints, training, benchmark, sandbox,
runner, evidence persistence, or I Ching formulas.

## Module Boundary

Create:

```text
src/onecode/cli_commands/configuration.py
```

The module exposes:

```python
CONFIGURATION_COMMANDS: frozenset[str]
register_configuration_commands(subparsers: argparse._SubParsersAction) -> None
dispatch_configuration_command(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> int | None
```

`CONFIGURATION_COMMANDS` contains the top-level commands
`list-verifier-presets`, `init-verifier-policy`, and `config`. Nested config
actions remain parser-owned values of `args.config_action`.

## Parser Contract

The registration function moves current parser construction verbatim and
preserves registration order.

### Verifier Policy

```text
list-verifier-presets

init-verifier-policy
  --workspace  default .
  --output     default .onecode/verifier-policy.json
  --preset     append, default None
  --force      store_true
```

### Model Configuration

```text
config set-model
  --endpoint  required
  --api-key   required
  --model     default None
  --provider  default openai-compatible

config show

config discover-models
  --endpoint  required
  --api-key   required
```

Tests freeze top-level and nested subparser names, destinations, required flags,
defaults, choices, nargs, action classes, and types.

## Service Authority

The adapter does not reimplement validation or persistence. It calls only:

- `verifier_policy_presets_summary()`;
- `write_verifier_policy()`;
- `write_model_config()`;
- `read_model_config()`;
- `discover_models()`.

The service layer remains the only authority for:

- verifier preset validity and duplicate handling;
- policy output containment within workspace;
- overwrite/force behavior;
- model config file location and permissions;
- API-key storage, masking, and preservation;
- discovery network request and response validation.

## Dispatch Compatibility

### `list-verifier-presets`

Print sorted UTF-8 JSON from `verifier_policy_presets_summary()` and return `0`.
No file is created.

### `init-verifier-policy`

Pass `Path(args.workspace)`, output, repeated preset list, and force flag to
`write_verifier_policy()`. Convert `ValueError` to `parser.error(str(exc))`,
preserving argparse stderr and `SystemExit(2)`. On success print sorted UTF-8
JSON and return `0`.

### `config set-model`

Pass endpoint, API key, model, and provider exactly once to
`write_model_config()`. Print only the returned public/masked payload and return
`0`.

### `config show`

Print the public/masked result of `read_model_config()` and return `0`.

### `config discover-models`

Pass endpoint and API key to `discover_models()`, print the result, and return
`0`. The adapter adds no retry, timeout, fallback, secret logging, or network
behavior.

Unknown top-level commands return `None`. An impossible unknown `config_action`
also returns `None`; argparse prevents this through the required nested parser.

## Secret and Filesystem Safety

Tests use temporary `ONECODE_HOME` and temporary workspaces. They assert public
stdout does not contain the raw API key. Direct-dispatch tests mock service
functions and inspect arguments without writing user configuration or making
network requests.

Path traversal, existing output, unknown preset, duplicate preset, and force
behavior continue to be covered by existing verifier policy CLI tests against
the service authority.

## Dependency Boundary

The adapter may import only stdlib, `onecode.kernel.model_config`, and the
verifier policy summary/write helpers. It must not import:

- `onecode.cli`;
- runner or execution engine;
- model loop or model provider execution;
- training or benchmark;
- sandbox;
- Web or TUI;
- checkpoint, WAL, trace, ledger, or evidence persistence;
- `IchingKernel`.

Kernel, Web, and TUI layers must not reverse-import the adapter.

## Structural Target

`build_parser()` and `main()` delegate the configuration family after the
existing read-only and local-interface adapters. Structural tests record actual
line-count reductions without broadening scope. Existing public compatibility
exports from `onecode.cli` remain available.

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

LogosGate, PathGuard, approvals, verifier execution, sandbox, evidence writes,
physical evidence, and historical artifacts remain unchanged.

## Acceptance Criteria

1. Top-level and nested parser contracts remain identical.
2. Existing path, force, preset, masking, and config tests pass unchanged.
3. Direct tests prove no real network request or user config write occurs.
4. Raw API keys do not appear in public stdout or recorded closure evidence.
5. `main()` and `build_parser()` no longer contain direct configuration
   branches/registrations and are materially shorter.
6. Dependency and forbidden formula scans pass.
7. Focused/full verification, Doctor, release audit, and wheel checks pass.
