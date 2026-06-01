# OneCode

OneCode is a local-first agent kernel for guarded file changes, deterministic
state transitions, append-only run evidence, and resumable task execution.

The core kernel has no runtime third-party dependency. Optional shells and UI
layers can connect through the CLI or the local OpenAI-compatible HTTP API.

OneCode is licensed under the Apache License, Version 2.0.

## Core Capabilities

- Guarded workspace writes through a path and intent gate.
- Deterministic 6-bit state profile for every run outcome.
- Append-only WAL evidence with hash-chain validation.
- Stateful resume logic for completed, skipped, halted, and tampered runs.
- Shell projection contract for CLI, Web API, and UI adapters.
- Local doctor and release verification scripts.
- Benchmark harness for rule, safety, sandbox, approval, and trace coverage.

## Install

```bash
pip install -e .
```

Optional conversational TUI:

```bash
pip install -e .[tui]
```

## Verify

Fast core gate:

```bash
bash scripts/verify-core.sh
```

Full local gate:

```bash
bash scripts/verify.sh
```

## Run

Doctor smoke check:

```bash
PYTHONPATH=src python3 -m onecode doctor
```

Run a guarded file write:

```bash
PYTHONPATH=src python3 -m onecode run \
  --workspace . \
  --intent write_text \
  --path demo.txt \
  --content "hello onecode"
```

Start the local API:

```bash
PYTHONPATH=src ONECODE_API_TOKEN=dev-local-token \
  python3 -m onecode serve --host 127.0.0.1 --port 8080
```

Discover the shell projection schema:

```bash
PYTHONPATH=src python3 -m onecode shell-schema
```

## Safety Model

OneCode treats model output as a candidate, not an authority. File changes must
pass through the kernel's intent, path, evidence, and transition checks before
they are written.

Normal completed runs can use WAL-only relaxed evidence for low disk pressure.
Denied or halted paths retain stronger forensic evidence.

## Status

This release is suitable as a local development baseline and integration
prototype. Production deployment still requires an operator-owned gateway,
authentication, TLS, request-size limits, rate limiting, and environment-specific
secret management.

