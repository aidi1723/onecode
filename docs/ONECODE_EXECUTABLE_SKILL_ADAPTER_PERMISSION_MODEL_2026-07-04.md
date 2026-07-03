# OneCode Executable Skill Adapter Permission Model

Date: 2026-07-04
Status: Design boundary only

## Purpose

OneCode currently treats skills as read-only evidence and reference material.
This document defines the minimum permission model required before any future
executable skill adapter can run commands, touch files, use network access, or
call external connectors.

## Non-Goal

This stage does not implement executable skill adapters. It records the
approval, provenance, and rollback boundary that a future implementation must
prove with tests before runtime skill execution is allowed.

## Required Adapter Identity

Every executable adapter must declare:

- adapter identity: stable adapter ID, version, source package, and checksum
- skill identity: skill name, source path or URL, source hash, and trust status
- operator context: workspace, run ID, requested task, and approval record
- execution mode: read-only, dry-run, write, network, connector, or privileged

Adapters without complete identity metadata must fail closed before execution.

## Approval Gates

Execution must require an explicit approval gate for any action outside
read-only local analysis.

Approval records must include:

- requested action
- affected files, hosts, connectors, or accounts
- expected output artifacts
- rollback notes
- approver identity when available
- timestamp and run ID

No adapter may reuse approval from a different run ID, workspace, host, or
connector scope.

## Path Scope

The path scope must be explicit before execution:

- allowed read roots
- allowed write roots
- forbidden control surfaces, including `.git`, `.github`, credentials, shell
  startup files, and system configuration
- generated artifact locations
- cleanup expectations

Path traversal, symlink escape, absolute writes outside approved roots, and
hidden persistence must fail closed.

## Network Scope

Network scope must be disabled by default. If enabled, the adapter must record:

- allowed hostnames or endpoints
- allowed HTTP methods or protocol operations
- credential source
- request purpose
- response retention rule
- timeout and retry policy

Wildcard network access is not allowed. Account mutation, payment, destructive
submission, or private-data extraction requires a separate approval record.

## Provenance and Audit Evidence

Each execution must write provenance evidence before and after adapter work:

- selected skill summary
- adapter identity and checksum
- input prompt or task summary
- approved action boundary
- tool calls or equivalent execution events
- generated files and SHA-256 hashes
- stdout/stderr or structured result summaries
- final status and failure reason

Evidence must be append-only or tamper-evident when connected to a OneCode run.

## Denial Behavior

Adapters must deny execution when:

- approval is missing or out of scope
- path scope cannot be resolved
- network scope is missing for network work
- skill provenance is unknown or hash validation fails
- requested action conflicts with sandbox policy
- generated output would overwrite protected files
- rollback evidence cannot be recorded

Denials must return structured reasons and must not partially execute the
requested action.

## Rollback Requirements

Before write-capable execution, the adapter must define a rollback checkpoint:

- clean Git commit, branch, worktree, backup artifact, or migration snapshot
- files and generated artifacts covered by rollback
- owner or process responsible for rollback
- verification command after rollback
- non-reversible actions, if any

If rollback is impossible, the adapter must require a stronger approval gate and
record the irreversible risk.

## Release Gate for Future Implementation

A future executable adapter implementation must add tests for:

- identity validation
- approval scope validation
- path allow/deny checks
- network allow/deny checks
- provenance evidence writing
- rollback checkpoint recording
- denial without side effects

Until those tests exist and pass, skills remain read-only evidence in OneCode.
