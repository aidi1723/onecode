# OneCode v0.8.0 Final Closure

Date: 2026-07-10

## Release Scope

OneCode v0.8.0 closes the canonical I Ching runtime/evidence migration and the
current CLI shell decomposition. This document is the index for the approved
July 10 implementation phases.

The GitHub update targets the existing
`feature/gateway-iching-rule-sync` branch. It does not merge `main`, create a
GitHub Release, publish a package, or deploy a production service.

## Foundational Authority

The release preserves the established authority chain:

```text
yin/yang line bits
-> trigrams
-> five-element generation/control
-> yin/yang pressure and dynamic balance
-> transition
-> dispatch
```

The following remain unchanged as execution authorities:

- `IchingKernel.transition()`;
- `IchingKernel.dispatch_decision()`;
- `apply_balanced_event()`;
- `balance_mask()`;
- yin/yang calculations;
- five-element generation, control, relation, and modulation;
- LogosGate, PathGuard, approvals, verifier, sandbox, and physical evidence.

No confidence, priority, mood, retry score, or parallel external-policy state
was added as an execution authority.

## Completed Phases

1. **Canonical I Ching v2 encoding**
   - Added immutable v1/v2 schemas and corrected canonical Li/Xun encoding for
     new v2 facts.
   - Preserved missing-schema evidence as v1 without rewriting history.
   - Record: `docs/ONECODE_ICHING_V2_CANONICALIZATION_CLOSURE_2026-07-10.md`.
2. **Training and benchmark schema projection**
   - Added record-level `rule_schema` while preserving strict action fields and
     historical v1 semantics.
   - Record: `docs/ONECODE_TRAINING_BENCHMARK_RULE_SCHEMA_CLOSURE_2026-07-10.md`.
3. **Runtime balance mutation evidence**
   - Added descriptive raw-to-balanced mutation certificates and bounded
     persistence summaries without feeding evidence back into decisions.
   - Record: `docs/ONECODE_RUNTIME_BALANCE_MUTATION_EVIDENCE_CLOSURE_2026-07-10.md`.
4. **Mutation integrity and Shell v4**
   - Added strict evidence validation, WAL recovery, and read-only
     `balance_state` projection.
   - Record: `docs/ONECODE_MUTATION_EVIDENCE_INTEGRITY_SHELL_V4_CLOSURE_2026-07-10.md`.
5. **Shell v4 public contract**
   - Added exact schema/case fixtures for Python, CLI, Web, and HTTP consumers.
   - Record: `docs/ONECODE_SHELL_V4_PUBLIC_CONTRACT_CLOSURE_2026-07-10.md`.
6. **CLI command-family decomposition**
   - Split read-only, local-interface, and configuration/policy command families
     into focused adapters while retaining `onecode.cli` compatibility.
   - Records:
     - `docs/ONECODE_CLI_READ_ONLY_COMMAND_SPLIT_CLOSURE_2026-07-10.md`;
     - `docs/ONECODE_CLI_LOCAL_INTERFACE_COMMAND_SPLIT_CLOSURE_2026-07-10.md`;
     - `docs/ONECODE_CLI_CONFIGURATION_COMMAND_SPLIT_CLOSURE_2026-07-10.md`.

## Public Version Contract

The following public identifiers are aligned to `0.8.0`:

- package metadata in `pyproject.toml`;
- `onecode.__version__`;
- TUI `APP_VERSION`;
- HTTP server identifier `OneCodeHTTP/0.8`.

An automated version consistency test prevents future drift.

## Verification Baseline

Final local verification for the versioned source tree:

```text
Focused configuration/Web/runner regression: 161 passed
Full verification: 824 passed, 1 skipped
Doctor: ok
Source quality: ok
git diff --check: passed
Forbidden core-formula diff scan: no matches
Wheel: onecode-0.8.0-py3-none-any.whl
Wheel assets: ok
Publish action: not performed
```

The single skipped test requires the optional `ONECODE_GLOBAL_COMMAND`
environment configuration and does not represent a source failure.

The GitHub commit and push identifiers are appended only after those actions
complete successfully.

## Residual Maintenance

The remaining work is non-blocking maintenance:

- continue reducing `onecode.cli.main()` and `build_parser()` by command family;
- split runner orchestration only with execution-order and evidence-authority
  regression tests;
- treat `IchingKernel` formula refactoring as a separate proof-heavy project,
  not routine cleanup;
- configure and run the optional global-command entrypoint test when validating
  a machine-wide installation.
