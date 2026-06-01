# OneCode Release Notes

## Current Release Summary

This release stabilizes OneCode as a local-first agent kernel with a deterministic
state machine, guarded file writes, resumable execution, and low-overhead
append-only evidence.

## Highlights

- Apache License 2.0 project licensing.
- WAL-only relaxed evidence mode for normal completed runs.
- Hash-chain validation for WAL inspection and resume paths.
- Shell projection schema for stable CLI/Web/UI rendering.
- OpenAI-compatible local HTTP API for shell integration.
- Benchmark task set for safety, trace, approval, sandbox, and resume behavior.
- Core verification script and release audit script.

## Verification

Validated release gates:

```text
bash scripts/verify-core.sh
185 tests OK
doctor status: ok
```

```text
PYTHONPATH=src python3 -m unittest tests.test_web_api -v
48 tests OK
```

## Operational Notes

- The default completed-run evidence path is designed to minimize disk pressure.
- Denied and halted paths still preserve stronger evidence for auditability.
- The local API is intended for loopback or trusted bridge use unless placed
  behind production-grade gateway controls.
- Optional TUI dependencies are not required for the core kernel gate.

## Scope

This release pack intentionally uses engineering-neutral terminology. Internal
development files may contain historical research terms and compatibility field
names; those are not part of the public release narrative.

