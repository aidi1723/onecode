# OneCode Ubuntu Docker Verification Closure

Date: 2026-06-09

## Scope

This closure records the Ubuntu Linux validation pass for the OneCode public
release line. It covers the core kernel, doctor checks, Docker sandbox smoke,
and public privacy scan. It does not cover native Windows, multi-host
distributed execution, or production gateway hardening.

## Result

OneCode core passed the Ubuntu validation gate.

Validated environment class:

- Ubuntu 24.04 LTS
- Python 3.12
- Docker Engine available

Validated commands:

```text
bash scripts/verify-core.sh
188 tests OK
doctor status: ok
```

```text
PYTHONPATH=src python3 -m unittest tests.test_sandbox tests.test_source_hygiene -v
11 tests OK
```

```text
PYTHONPATH=src python3 -m onecode sandbox-smoke
sandbox status: completed
exit_code: 0
```

```text
bash scripts/privacy-scan.sh
no findings
```

## Issue Found

The first Docker sandbox smoke attempt on Ubuntu exposed a bind-mount write
permission failure. The container was running as root with all capabilities
dropped. On a host-owned workspace directory, capability-dropped container root
could not write the mounted workspace file.

## Fix

`SandboxConfig` now resolves a default Docker `--user` value from the host
UID/GID on Unix-like systems. This makes sandboxed commands write workspace
files as the same host user that owns the bind mount while preserving the
existing isolation flags.

The fix is intentionally narrow:

- no broadening of filesystem scope;
- no network relaxation;
- no removal of resource limits;
- no extra authority for model-generated actions;
- no change to the kernel's intent, path, evidence, or transition rules.

## Privacy Closure

The public privacy scan now excludes Git worktree pointer metadata, because it
is local Git state and is not part of the publishable project tree. Public
source files remain scanned for local path, private host, private email, API key,
and temporary workspace markers.

The test fixture for this behavior uses generic placeholder path components.
It does not contain a real local path, private hostname, temporary validation
directory, or private file name.

## Rule Alignment

The change remains inside OneCode's existing rule model:

- Yin-yang boundary: execution authority is not expanded; the sandbox only
  receives the minimum host identity needed to write its own mounted workspace.
- Five-element balance: Docker remains a containment layer, not a new authority
  source. Evidence and transition logic stay in the kernel.
- Bagua/state discipline: the change preserves deterministic command
  construction and converts the observed Linux failure into a reproducible
  regression test.

## Residual Risks

- Native Windows still requires a portable lock abstraction before it can be
  listed as supported.
- Other Linux distributions should run the same verification gates before being
  listed as validated.
- Production deployments still need operator-owned gateway, authentication,
  TLS, request-size limits, rate limiting, backup, and secret management.

## Closure

Ubuntu Linux is now validated for the OneCode local-core path and Docker
sandbox smoke path. The public release line includes regression coverage for
the Linux bind-mount fix and the privacy-scan worktree boundary.
