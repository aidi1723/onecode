# Gateway Folder Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the existing gateway product assets under `<gateway-repo>` while keeping OneCode independent.

**Architecture:** Treat `网关/` as the product root for the existing Claude Code / Codex gateway. Move gateway source, tests, scripts, deployment files, docs, and runtime support files together, then fix import and path assumptions so tests can run from the new product root. Leave `one code/` untouched.

**Tech Stack:** Python 3, unittest/pytest-compatible tests, FastAPI gateway modules, shell deployment scripts, git.

---

### Task 1: Move Gateway Product Assets

**Files:**
- Move: `<workspace-root>/agent_skill_dictionary` -> `<gateway-repo>/agent_skill_dictionary`
- Move: `<workspace-root>/tests` -> `<gateway-repo>/tests`
- Move: `<workspace-root>/scripts` -> `<gateway-repo>/scripts`
- Move: `<workspace-root>/deploy` -> `<gateway-repo>/deploy`
- Move: `<workspace-root>/bin` -> `<gateway-repo>/bin`
- Move: `<workspace-root>/docs` -> `<gateway-repo>/docs`
- Move: `<workspace-root>/Dockerfile.gateway` -> `<gateway-repo>/Dockerfile.gateway`
- Move: `<workspace-root>/requirements-gateway.txt` -> `<gateway-repo>/requirements-gateway.txt`
- Move: `<workspace-root>/pytest.ini` -> `<gateway-repo>/pytest.ini`
- Move if present and gateway-specific: `<workspace-root>/.env.example`, `<workspace-root>/PRIVATE_BETA_QUICKSTART.md`, `<workspace-root>/README.md`, `<workspace-root>/Makefile`

- [ ] **Step 1: Move directories and files**

Run:

```bash
mv agent_skill_dictionary tests scripts deploy bin docs Dockerfile.gateway requirements-gateway.txt pytest.ini .env.example PRIVATE_BETA_QUICKSTART.md README.md Makefile 网关/
```

Expected: gateway assets exist under `网关/`; OneCode remains at `one code/`.

- [ ] **Step 2: Inspect top-level leftovers**

Run:

```bash
find . -maxdepth 1 -mindepth 1 -print
```

Expected: non-gateway assets remain at the repository root, including `one code/`, images, reports, data, schemas, home, and `网关/`.

### Task 2: Fix Product-Root Path Assumptions

**Files:**
- Modify: `<gateway-repo>/pytest.ini`
- Review: `<gateway-repo>/scripts/*.py`
- Review: `<gateway-repo>/deploy/*.sh`
- Review: `<gateway-repo>/Makefile`

- [ ] **Step 1: Search old root-relative paths**

Run:

```bash
rg -n "agent_skill_dictionary/|docs/|tests/|requirements-gateway|Dockerfile.gateway|<workspace-root>" 网关
```

Expected: only legitimate product-root relative references remain.

- [ ] **Step 2: Update scripts that assume the old root**

Use product-root relative paths from `网关/`, such as:

```text
agent_skill_dictionary/programming-agent-skill-dictionary.json
requirements-gateway.txt
docs/yizijue-gateway-quickstart.md
```

Expected: running commands from `<gateway-repo>` works without depending on the old repository root.

### Task 3: Verify Gateway From New Root

**Files:**
- Test: `<gateway-repo>/tests`

- [ ] **Step 1: Run focused gateway tests**

Run from `<gateway-repo>`:

```bash
python3 -m unittest tests.test_gateway_core tests.test_gateway_plan tests.test_gateway_auth tests.test_minimal_gateway_mvp tests.test_build_mode_gateway_integration -v
```

Expected: tests pass or reveal path assumptions to fix.

- [ ] **Step 2: Run broader build-mode smoke tests if focused tests pass**

Run from `<gateway-repo>`:

```bash
python3 -m unittest discover -s tests -p 'test_gateway*.py' -v
python3 -m unittest discover -s tests -p 'test_build_mode*.py' -v
```

Expected: gateway/build-mode tests pass from the new product root.

### Task 4: Commit Migration Boundary

**Files:**
- Add/Move: `<gateway-repo>/**`
- Preserve: `<onecode-repo>/**`

- [ ] **Step 1: Check git status**

Run:

```bash
git status --short
```

Expected: gateway assets are under `网关/`; OneCode files are unchanged.

- [ ] **Step 2: Commit only migration-relevant files**

Run:

```bash
git add 网关
git commit -m "chore: consolidate gateway product under folder"
```

Expected: one migration commit on `feature/gateway-iching-rule-sync`.
