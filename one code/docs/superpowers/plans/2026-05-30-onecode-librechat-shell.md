# OneCode LibreChat Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose OneCode as a standalone OpenAI-compatible endpoint that LibreChat can use as its Web shell.

**Architecture:** Add a small stdlib HTTP server in `src/onecode/web` that adapts LibreChat/OpenAI Chat Completions requests to OneCode core runs. Configure the LibreChat fork with a `OneCode` custom endpoint and keep OneWord gateway dependencies out of this line.

**Tech Stack:** Python stdlib HTTP server, OneCode kernel, unittest, LibreChat custom endpoint configuration.

---

### Task 1: OneCode OpenAI-Compatible API

**Files:**
- Create: `src/onecode/web/__init__.py`
- Create: `src/onecode/web/api.py`
- Modify: `src/onecode/cli.py`
- Test: `tests/test_web_api.py`

- [ ] Add tests for health, models, bearer auth, and chat completion fallback.
- [ ] Implement request parsing and OpenAI-compatible JSON response helpers.
- [ ] Add `onecode serve` CLI command.
- [ ] Verify targeted tests pass.

### Task 2: LibreChat Endpoint Rename

**Files:**
- Modify in sibling LibreChat fork: `.env.example`, `librechat.yaml`, `ONEWORD_SHELL.md` or replacement docs.
- Test: static searches for `OneCode`, `ONECODE_API_BASE_URL`, and absence of OneWord gateway defaults in active config.

- [ ] Rename the endpoint from `OneWord` to `OneCode`.
- [ ] Replace OneWord env vars with OneCode env vars.
- [ ] Keep allowed local addresses for LibreChat SSRF protection.
- [ ] Verify the fork worktree is clean after commit.

### Task 3: End-to-End Smoke

**Files:**
- Create or modify: `scripts/onecode-librechat-smoke.py`
- Test: invoke OneCode API directly against `/v1/chat/completions`.

- [ ] Start OneCode API on localhost.
- [ ] Call `/v1/models`.
- [ ] Call `/v1/chat/completions` with a LibreChat-compatible payload.
- [ ] Confirm the response contains an assistant message and OneCode metadata.
