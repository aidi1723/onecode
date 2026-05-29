# Gateway Folder Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the existing gateway product assets under `/Users/aidi/大字典/网关` while keeping OneCode independent.

**Architecture:** Treat `网关/` as the product root for the existing Claude Code / Codex gateway. Move gateway source, tests, scripts, deployment files, docs, and runtime support files together, then fix import and path assumptions so tests can run from the new product root. Leave `one code/` untouched.

**Tech Stack:** Python 3, unittest/pytest-compatible tests, FastAPI gateway modules, shell deployment scripts, git.

---

### Task 1: Move Gateway Product Assets

**Files:**
- Move: `/Users/aidi/大字典/agent_skill_dictionary` -> `/Users/aidi/大字典/网关/agent_skill_dictionary`
- Move: `/Users/aidi/大字典/tests` -> `/Users/aidi/大字典/网关/tests`
- Move: `/Users/aidi/大字典/scripts` -> `/Users/aidi/大字典/网关/scripts`
- Move: `/Users/aidi/大字典/deploy` -> `/Users/aidi/大字典/网关/deploy`
- Move: `/Users/aidi/大字典/bin` -> `/Users/aidi/大字典/网关/bin`
- Move: `/Users/aidi/大字典/docs` -> `/Users/aidi/大字典/网关/docs`
- Move: `/Users/aidi/大字典/Dockerfile.gateway` -> `/Users/aidi/大字典/网关/Dockerfile.gateway`
- Move: `/Users/aidi/大字典/requirements-gateway.txt` -> `/Users/aidi/大字典/网关/requirements-gateway.txt`
- Move: `/Users/aidi/大字典/pytest.ini` -> `/Users/aidi/大字典/网关/pytest.ini`
- Move if present and gateway-specific: `/Users/aidi/大字典/.env.example`, `/Users/aidi/大字典/PRIVATE_BETA_QUICKSTART.md`, `/Users/aidi/大字典/README.md`, `/Users/aidi/大字典/Makefile`

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
- Modify: `/Users/aidi/大字典/网关/pytest.ini`
- Review: `/Users/aidi/大字典/网关/scripts/*.py`
- Review: `/Users/aidi/大字典/网关/deploy/*.sh`
- Review: `/Users/aidi/大字典/网关/Makefile`

- [ ] **Step 1: Search old root-relative paths**

Run:

```bash
rg -n "agent_skill_dictionary/|docs/|tests/|requirements-gateway|Dockerfile.gateway|/Users/aidi/大字典" 网关
```

Expected: only legitimate product-root relative references remain.

- [ ] **Step 2: Update scripts that assume the old root**

Use product-root relative paths from `网关/`, such as:

```text
agent_skill_dictionary/programming-agent-skill-dictionary.json
requirements-gateway.txt
docs/yizijue-gateway-quickstart.md
```

Expected: running commands from `/Users/aidi/大字典/网关` works without depending on the old repository root.

### Task 3: Verify Gateway From New Root

**Files:**
- Test: `/Users/aidi/大字典/网关/tests`

- [ ] **Step 1: Run focused gateway tests**

Run from `/Users/aidi/大字典/网关`:

```bash
python3 -m unittest tests.test_gateway_core tests.test_gateway_plan tests.test_gateway_auth tests.test_minimal_gateway_mvp tests.test_build_mode_gateway_integration -v
```

Expected: tests pass or reveal path assumptions to fix.

- [ ] **Step 2: Run broader build-mode smoke tests if focused tests pass**

Run from `/Users/aidi/大字典/网关`:

```bash
python3 -m unittest discover -s tests -p 'test_gateway*.py' -v
python3 -m unittest discover -s tests -p 'test_build_mode*.py' -v
```

Expected: gateway/build-mode tests pass from the new product root.

### Task 4: Commit Migration Boundary

**Files:**
- Add/Move: `/Users/aidi/大字典/网关/**`
- Preserve: `/Users/aidi/大字典/one code/**`

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
