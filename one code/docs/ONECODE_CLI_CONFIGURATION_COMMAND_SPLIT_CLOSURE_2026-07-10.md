# OneCode CLI Configuration Command Split Closure

Date: 2026-07-10

## Objective

Extract verifier-policy and model-configuration commands from the central CLI
while preserving parser, path-safety, secret, persistence, network, error, and
exit-code behavior.

## Extracted Commands

`onecode.cli_commands.configuration` owns exactly:

- `list-verifier-presets`;
- `init-verifier-policy`;
- `config set-model`;
- `config show`;
- `config discover-models`.

No command, option, default, provider, nested action, or alias was added or
removed.

## Service Authority

The adapter delegates to the existing authorities only:

- `verifier_policy_presets_summary()`;
- `write_verifier_policy()`;
- `write_model_config()`;
- `read_model_config()`;
- `discover_models()`.

Workspace containment, preset validation, duplicate handling, overwrite
rules, config location, file permissions, API-key preservation and masking,
and model discovery networking remain in those services. The adapter does not
duplicate or override them.

## Parser and Error Compatibility

Tests freeze top-level and nested parser actions, including option strings,
destinations, required flags, defaults, choices, nargs, action classes, types,
subparser destination, and required status.

`write_verifier_policy()` value errors continue through `parser.error()` and
produce `SystemExit(2)`. Model-config service exceptions retain their previous
propagation behavior.

## Secret and Network Boundary

Direct dispatch tests mock model discovery, so they make no network request.
Integration tests use a temporary `ONECODE_HOME` and temporary workspaces.
Sentinel API keys are passed only to mocked or temporary local service calls;
captured public stdout contains masked service results and never contains the
raw secret. No raw API key is recorded in this closure document.

## Structural Result

- `onecode.cli.main()`: 472 lines before this phase, 442 after extraction.
- `onecode.cli.build_parser()`: 214 lines before this phase, 196 after extraction.

Both remain public compatibility entry points.

## Dependency Boundary

The adapter imports only stdlib plus `onecode.kernel.model_config` and
`onecode.kernel.verifier`. Tests reject reverse dependencies from Web, TUI,
other CLI adapters, and unrelated kernel modules. It does not own runner,
execution engine, model loop/provider execution, training, benchmark, sandbox,
evidence persistence, or `IchingKernel` paths.

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

## Verification Record

Fresh verification after implementation, root-cause repair, and documentation
completion:

```text
Initial RED: missing onecode.cli_commands.configuration
Dispatch RED: six handled-command tests failed before service integration
Configuration/source-quality regression: 22 passed
Focused CLI/config/Web/runner regression: 161 passed
Full verification: 823 tests passed, 1 skipped
Doctor: ok
Source quality: ok
git diff --check: passed
Forbidden formula diff scan: no matches
cli.main line count: 442
build_parser line count: 196
Release audit: wheel assets ok
Publish action: not performed
```

The first full verification exposed a shell compatibility regression:
`DEFAULT_VERIFIER_POLICY_PATH` had been removed from `onecode.cli` while
`run_plan_verifier_policy_path()` still used it. The import was restored, the
three failing run-plan/demo tests passed in isolation, and the complete suite
then passed. No kernel formula or execution-authority change was required.
