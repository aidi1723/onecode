# OneCode Update - 2026-06-09 Ubuntu And Docker Verification

## Summary

This update records the Ubuntu Linux validation pass for OneCode and the Docker
sandbox compatibility fix that came out of that validation.

OneCode now has verified local-core coverage on macOS and Ubuntu Linux. The
Ubuntu validation used Python 3.12 on Ubuntu 24.04 LTS and included the core
verification gate, doctor smoke checks, Docker sandbox smoke checks, and the
public privacy scan.

## What Changed

- Docker sandbox containers now run as the host UID/GID by default on Unix-like
  systems.
- The sandbox command keeps the existing defensive flags: network disabled by
  default, memory and CPU limits, process limit, dropped capabilities, read-only
  root filesystem where compatible, and bounded tmpfs.
- The default host-user mapping fixes Linux bind-mount write failures caused by
  running a capability-dropped container as root against a host-owned workspace.
- The privacy scan now ignores Git worktree pointer metadata while continuing
  to scan public project files.
- Regression tests cover both Docker command user mapping and privacy-scan
  worktree handling.

## Verified Gates

Validated on Ubuntu 24.04 LTS:

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

## Platform Status

- macOS: supported for local development and core kernel workflows.
- Ubuntu Linux: validated for core kernel workflows and Docker sandbox smoke.
- Other Linux distributions: expected to work when Python 3.11+ and standard
  Unix file locking are available, but should be validated per distribution.
- WSL2: likely compatible through the Linux path, but still needs an explicit
  validation pass before being listed as verified.
- Native Windows: not listed as supported yet because the evidence lock path
  still depends on Unix `fcntl.flock()`.

## Release Boundary

This update was prepared from the clean public publish worktree. Public docs
use generic placeholders for workspace paths and do not include local absolute
paths, private hostnames, temporary validation directories, or private file
names.
