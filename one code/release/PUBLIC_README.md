# one code

one code is a trusted industrial AI kernel for enterprise-grade local agent
workflows. It is designed to reduce model error propagation by turning model
outputs into candidates that must pass deterministic state, safety, evidence,
and recovery checks before they can affect project files.

one code is not a general-purpose autonomous assistant. It is a controllable
execution kernel for guarded file changes, deterministic state transitions,
append-only run evidence, and resumable task execution.

The core kernel has no runtime third-party dependency. Optional shells and UI
layers can connect through the CLI or the local OpenAI-compatible HTTP API.

one code is licensed under the Apache License, Version 2.0.

## Core Capabilities

- Guarded workspace writes through a path and intent gate.
- Deterministic 6-bit state profile for every run outcome.
- Append-only WAL evidence with hash-chain validation.
- Stateful resume logic for completed, skipped, halted, and tampered runs.
- Shell projection contract for CLI, Web API, and UI adapters.
- Local doctor and release verification scripts.
- Benchmark harness for rule, safety, sandbox, approval, and trace coverage.
- Model-independent control layer for OpenAI-compatible, local, or third-party
  candidate generators.
- Low-disk-pressure evidence mode for normal completed runs.

## Why It Matters

Large models can propose useful edits, but they can also hallucinate tools,
paths, schemas, permissions, and completion status. one code inserts a
deterministic control layer between the model and the workspace.

The target benefits measured by the benchmark harness are:

- lower invalid-action propagation
- higher verified task completion
- fewer unsafe writes
- less repeated repair work
- lower token use from fewer failed retries
- lower disk I/O from compact append-only evidence
- better task quality through verifier and evidence checks

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
  --content "hello one code"
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

one code treats model output as a candidate, not an authority. File changes must
pass through the kernel's intent, path, evidence, and transition checks before
they are written.

Normal completed runs can use WAL-only relaxed evidence for low disk pressure.
Denied or halted paths retain stronger forensic evidence.

## Status

This release is suitable as a local development baseline, integration prototype,
and enterprise evaluation baseline for trusted industrial AI workflows.
Production deployment still requires an operator-owned gateway, authentication,
TLS, request-size limits, rate limiting, and environment-specific secret
management.
