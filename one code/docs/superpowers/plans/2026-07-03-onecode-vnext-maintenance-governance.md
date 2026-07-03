# OneCode vNext Maintenance Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the GitHub update path reviewable and begin conservative `web/api.py` decomposition without changing Web API behavior.

**Architecture:** Treat P0 release-line governance as a documented Git audit with no destructive operations. Treat P1a as helper extraction: new focused modules own request-body parsing, response helpers, auth checks, and workspace guards while `src/onecode/web/api.py` remains the route coordinator and re-exports compatibility names.

**Tech Stack:** Python stdlib, `unittest`, Git/GitHub CLI, existing OneCode verification scripts.

---

## File Structure

- Create: `docs/ONECODE_VNEXT_RELEASE_LINE_AUDIT_2026-07-03.md`
  - Records `main`, `origin/main`, current branch ancestry, PR limitation, and the selected non-destructive review path.
- Create: `src/onecode/web/request_body.py`
  - Owns `DEFAULT_MAX_REQUEST_BYTES`, `JsonRequestBody`, `max_request_bytes()`, and `read_json_request_body()`.
- Create: `src/onecode/web/responses.py`
  - Owns `error_payload()` and `encode_json_payload()`.
- Create: `src/onecode/web/auth.py`
  - Owns `LOOPBACK_HOSTS` and `request_authorized()`.
- Create: `src/onecode/web/workspace.py`
  - Owns workspace-root environment parsing and workspace path validation.
- Modify: `src/onecode/web/api.py`
  - Imports extracted helpers and keeps top-level compatibility exports.
- Modify: `tests/test_web_api.py`
  - Adds focused module import tests before each extraction.
- Modify: `CHANGELOG.md`
  - Records the vNext maintenance-governance update after implementation.

## Task 1: P0 Release-Line Audit

**Files:**
- Create: `docs/ONECODE_VNEXT_RELEASE_LINE_AUDIT_2026-07-03.md`

- [ ] **Step 1: Run read-only ancestry audit**

Run:

```bash
git fetch origin
git branch -vv
git merge-base main feature/gateway-iching-rule-sync
git merge-base origin/main feature/gateway-iching-rule-sync
git log --oneline --decorate --graph --max-count=20 --all
```

Expected: commands complete without modifying tracked project files. Record whether `origin/main` and `feature/gateway-iching-rule-sync` share a merge base.

- [ ] **Step 2: Check PR state without creating a PR**

Run:

```bash
gh pr list --head feature/gateway-iching-rule-sync --repo aidi1723/onecode --json number,title,url,state,headRefName,baseRefName
```

Expected: output is either an existing PR JSON list or `[]`. Record the result.

- [ ] **Step 3: Write the audit document**

Create `docs/ONECODE_VNEXT_RELEASE_LINE_AUDIT_2026-07-03.md` with this structure:

```markdown
# OneCode vNext Release-Line Audit

Date: 2026-07-03
Branch: `feature/gateway-iching-rule-sync`
Remote: `origin https://github.com/aidi1723/onecode.git`

## Audit Commands

- `git fetch origin`
- `git branch -vv`
- `git merge-base main feature/gateway-iching-rule-sync`
- `git merge-base origin/main feature/gateway-iching-rule-sync`
- `gh pr list --head feature/gateway-iching-rule-sync --repo aidi1723/onecode --json number,title,url,state,headRefName,baseRefName`

## Findings

- Local branch and upstream tracking status: write the exact `git branch -vv`
  line for `feature/gateway-iching-rule-sync`.
- Local `main` merge-base with feature branch: write the exact commit hash
  printed by `git merge-base main feature/gateway-iching-rule-sync`, or write
  `none` if the command exits non-zero.
- `origin/main` merge-base with feature branch: write the exact commit hash
  printed by `git merge-base origin/main feature/gateway-iching-rule-sync`, or
  write `none` if the command exits non-zero.
- Current PR state: write the exact JSON returned by `gh pr list`.

## Decision

Use a non-destructive sync branch if GitHub still rejects PR creation from
`feature/gateway-iching-rule-sync` to `main`. Do not force-push or rewrite
history. Preserve the current feature branch as the milestone record.

## Follow-Up

If a PR is required, create a branch from `origin/main` in an isolated worktree
and replay only project-root changes under `one code/`.
```

- [ ] **Step 4: Verify the audit document**

Run:

```bash
rg -n "none if|write the exact" docs/ONECODE_VNEXT_RELEASE_LINE_AUDIT_2026-07-03.md
git diff --check -- docs/ONECODE_VNEXT_RELEASE_LINE_AUDIT_2026-07-03.md
```

Expected: `rg` exits with no matches; `git diff --check` exits 0.

- [ ] **Step 5: Commit P0 audit**

Run:

```bash
git add docs/ONECODE_VNEXT_RELEASE_LINE_AUDIT_2026-07-03.md
git commit -m "docs: audit vnext release line"
```

Expected: commit succeeds and contains only the audit document.

## Task 2: Extract Request Body Helpers

**Files:**
- Create: `src/onecode/web/request_body.py`
- Modify: `src/onecode/web/api.py`
- Modify: `tests/test_web_api.py`

- [ ] **Step 1: Write failing module import test**

Append this test near the existing JSON-body tests in `tests/test_web_api.py`:

```python
    def test_request_body_module_reports_invalid_content_length(self):
        from io import BytesIO
        from onecode.web.request_body import read_json_request_body

        result = read_json_request_body({"content-length": "not-a-number"}, BytesIO(b"{}"))

        self.assertIsNone(result.payload)
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.error_type, "invalid_request_body")
        self.assertIn("content-length", result.error_message)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_web_api.OneCodeWebApiTests.test_request_body_module_reports_invalid_content_length -v
```

Expected: FAIL or ERROR with `ModuleNotFoundError: No module named 'onecode.web.request_body'`.

- [ ] **Step 3: Create `request_body.py`**

Create `src/onecode/web/request_body.py`:

```python
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, BinaryIO, Mapping


DEFAULT_MAX_REQUEST_BYTES = 1_000_000


@dataclass(frozen=True)
class JsonRequestBody:
    payload: dict[str, Any] | None
    status_code: int = 200
    error_type: str | None = None
    error_message: str | None = None


def max_request_bytes() -> int:
    try:
        value = int(os.getenv("ONECODE_MAX_REQUEST_BYTES", str(DEFAULT_MAX_REQUEST_BYTES)))
    except ValueError:
        return DEFAULT_MAX_REQUEST_BYTES
    return value if value > 0 else DEFAULT_MAX_REQUEST_BYTES


def read_json_request_body(headers: Mapping[str, str], rfile: BinaryIO) -> JsonRequestBody:
    raw_length = headers.get("content-length") or headers.get("Content-Length") or "0"
    try:
        length = int(raw_length or "0")
    except ValueError:
        return JsonRequestBody(
            payload=None,
            status_code=400,
            error_type="invalid_request_body",
            error_message="content-length must be an integer",
        )
    if length < 0:
        return JsonRequestBody(
            payload=None,
            status_code=400,
            error_type="invalid_request_body",
            error_message="content-length must not be negative",
        )
    limit = max_request_bytes()
    if length > limit:
        return JsonRequestBody(
            payload=None,
            status_code=413,
            error_type="request_too_large",
            error_message=f"request body exceeds maximum size of {limit} bytes",
        )
    raw = rfile.read(length)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonRequestBody(
            payload=None,
            status_code=400,
            error_type="invalid_json",
            error_message="request body must be valid JSON",
        )
    if not isinstance(value, dict):
        return JsonRequestBody(
            payload=None,
            status_code=400,
            error_type="invalid_json",
            error_message="request body must be a JSON object",
        )
    return JsonRequestBody(payload=value)
```

- [ ] **Step 4: Wire `api.py` compatibility imports**

In `src/onecode/web/api.py`, remove the local `JsonRequestBody`, `DEFAULT_MAX_REQUEST_BYTES`, `max_request_bytes()`, and `read_json_request_body()` definitions. Add this import near the other imports:

```python
from .request_body import JsonRequestBody, max_request_bytes, read_json_request_body
```

Keep `JsonRequestBody`, `max_request_bytes`, and `read_json_request_body` imported at module top level so existing `from onecode.web.api import read_json_request_body` callers keep working.

- [ ] **Step 5: Run request-body focused tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_web_api.OneCodeWebApiTests.test_request_body_module_reports_invalid_content_length \
  tests.test_web_api.OneCodeWebApiTests.test_read_json_result_reports_invalid_content_length \
  tests.test_web_api.OneCodeWebApiTests.test_read_json_result_reports_oversized_request_body \
  tests.test_web_api.OneCodeWebApiTests.test_read_json_rejects_oversized_request_body -v
```

Expected: all listed tests pass.

- [ ] **Step 6: Commit request-body extraction**

Run:

```bash
git add src/onecode/web/request_body.py src/onecode/web/api.py tests/test_web_api.py
git commit -m "refactor: extract web request body helpers"
```

Expected: commit succeeds and `api.py` line count decreases.

## Task 3: Extract Response Helpers

**Files:**
- Create: `src/onecode/web/responses.py`
- Modify: `src/onecode/web/api.py`
- Modify: `tests/test_web_api.py`

- [ ] **Step 1: Write failing response module test**

Append this test near `test_error_payload_uses_openai_style_error`:

```python
    def test_responses_module_encodes_json_payload(self):
        from onecode.web.responses import encode_json_payload, error_payload

        payload = error_payload("invalid_request", "bad request")
        encoded = encode_json_payload(payload)

        self.assertEqual(payload, {"error": {"type": "invalid_request", "message": "bad request"}})
        self.assertEqual(encoded, b'{"error": {"type": "invalid_request", "message": "bad request"}}')
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_web_api.OneCodeWebApiTests.test_responses_module_encodes_json_payload -v
```

Expected: FAIL or ERROR with `ModuleNotFoundError: No module named 'onecode.web.responses'`.

- [ ] **Step 3: Create `responses.py`**

Create `src/onecode/web/responses.py`:

```python
from __future__ import annotations

import json
from typing import Any


def error_payload(error_type: str, message: str) -> dict[str, Any]:
    return {"error": {"type": error_type, "message": message}}


def encode_json_payload(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")
```

- [ ] **Step 4: Wire `api.py` response imports**

In `src/onecode/web/api.py`, remove the local `error_payload()` definition and add:

```python
from .responses import encode_json_payload, error_payload
```

Update `OneCodeRequestHandler._send_json()` to use:

```python
        encoded = encode_json_payload(payload)
```

Leave all status codes and headers unchanged.

- [ ] **Step 5: Run response focused tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_web_api.OneCodeWebApiTests.test_responses_module_encodes_json_payload \
  tests.test_web_api.OneCodeWebApiTests.test_error_payload_uses_openai_style_error \
  tests.test_web_api.OneCodeWebApiTests.test_error_payload_uses_openai_style_error -v
```

Expected: all listed tests pass.

- [ ] **Step 6: Commit response extraction**

Run:

```bash
git add src/onecode/web/responses.py src/onecode/web/api.py tests/test_web_api.py
git commit -m "refactor: extract web response helpers"
```

Expected: commit succeeds and existing `onecode.web.api.error_payload` import compatibility is preserved through the imported name.

## Task 4: Extract Auth Helpers

**Files:**
- Create: `src/onecode/web/auth.py`
- Modify: `src/onecode/web/api.py`
- Modify: `tests/test_web_api.py`

- [ ] **Step 1: Write failing auth module test**

Append this test near the existing bearer auth tests:

```python
    def test_auth_module_allows_loopback_without_token_when_explicit(self):
        from onecode.web.auth import request_authorized

        self.assertTrue(request_authorized({}, None, allow_unauthenticated=True, host="::1"))
        self.assertFalse(request_authorized({}, None, allow_unauthenticated=True, host="0.0.0.0"))
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_web_api.OneCodeWebApiTests.test_auth_module_allows_loopback_without_token_when_explicit -v
```

Expected: FAIL or ERROR with `ModuleNotFoundError: No module named 'onecode.web.auth'`.

- [ ] **Step 3: Create `auth.py`**

Create `src/onecode/web/auth.py`:

```python
from __future__ import annotations

import secrets


LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def request_authorized(
    headers: dict[str, str],
    token: str | None,
    *,
    allow_unauthenticated: bool = False,
    host: str = "127.0.0.1",
) -> bool:
    if token is None or token.strip() == "":
        return allow_unauthenticated and host in LOOPBACK_HOSTS
    authorization = headers.get("authorization") or headers.get("Authorization") or ""
    return secrets.compare_digest(authorization, f"Bearer {token}")
```

- [ ] **Step 4: Wire `api.py` auth imports**

In `src/onecode/web/api.py`, remove local `LOOPBACK_HOSTS` and `request_authorized()`. Add:

```python
from .auth import LOOPBACK_HOSTS, request_authorized
```

Remove `import secrets` from `api.py` if it is no longer used outside auth.

- [ ] **Step 5: Preserve constant-time compare test**

Update `test_bearer_auth_uses_constant_time_compare` to patch the new module:

```python
        with patch("onecode.web.auth.secrets.compare_digest", return_value=True) as compare_digest:
            authorized = request_authorized({"authorization": "Bearer secret-token"}, "secret-token")
```

- [ ] **Step 6: Run auth focused tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_web_api.OneCodeWebApiTests.test_auth_module_allows_loopback_without_token_when_explicit \
  tests.test_web_api.OneCodeWebApiTests.test_bearer_auth_rejects_missing_token_when_configured \
  tests.test_web_api.OneCodeWebApiTests.test_bearer_auth_rejects_missing_token_by_default \
  tests.test_web_api.OneCodeWebApiTests.test_bearer_auth_allows_explicit_unauthenticated_loopback \
  tests.test_web_api.OneCodeWebApiTests.test_bearer_auth_rejects_explicit_unauthenticated_non_loopback \
  tests.test_web_api.OneCodeWebApiTests.test_bearer_auth_accepts_matching_token \
  tests.test_web_api.OneCodeWebApiTests.test_bearer_auth_uses_constant_time_compare -v
```

Expected: all listed tests pass.

- [ ] **Step 7: Commit auth extraction**

Run:

```bash
git add src/onecode/web/auth.py src/onecode/web/api.py tests/test_web_api.py
git commit -m "refactor: extract web auth helpers"
```

Expected: commit succeeds.

## Task 5: Extract Workspace Helpers

**Files:**
- Create: `src/onecode/web/workspace.py`
- Modify: `src/onecode/web/api.py`
- Modify: `tests/test_web_api.py`

- [ ] **Step 1: Write failing workspace module test**

Append this test near the existing workspace tests:

```python
    def test_workspace_module_rejects_path_outside_allowed_roots(self):
        from onecode.web.workspace import workspace_from_request

        with tempfile.TemporaryDirectory() as allowed, tempfile.TemporaryDirectory() as outside, patch.dict(
            "os.environ",
            {
                "ONECODE_WORKSPACE_ROOT": allowed,
                "ONECODE_ALLOWED_WORKSPACE_ROOTS": allowed,
            },
            clear=True,
        ):
            with self.assertRaises(ValueError) as raised:
                workspace_from_request({"metadata": {"workspace": outside}})

        self.assertIn("outside allowed workspace roots", str(raised.exception))
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_web_api.OneCodeWebApiTests.test_workspace_module_rejects_path_outside_allowed_roots -v
```

Expected: FAIL or ERROR with `ModuleNotFoundError: No module named 'onecode.web.workspace'`.

- [ ] **Step 3: Create `workspace.py`**

Create `src/onecode/web/workspace.py`:

```python
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def configured_allowed_workspace_roots() -> list[Path]:
    raw_roots = os.getenv("ONECODE_ALLOWED_WORKSPACE_ROOTS", "")
    roots = [part for part in raw_roots.split(os.pathsep) if part.strip()]
    if not roots:
        roots = [os.getenv("ONECODE_WORKSPACE_ROOT", os.getcwd())]
    return [Path(root).expanduser().resolve() for root in roots]


def path_inside_root(path: Path, root: Path) -> bool:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    return resolved_path == resolved_root or resolved_root in resolved_path.parents


def workspace_allowed(workspace: Path, roots: list[Path] | None = None) -> bool:
    allowed_roots = roots if roots is not None else configured_allowed_workspace_roots()
    return any(path_inside_root(workspace, root) for root in allowed_roots)


def require_allowed_workspace(workspace: Path) -> Path:
    resolved = workspace.resolve()
    if not workspace_allowed(resolved):
        raise ValueError(f"workspace outside allowed workspace roots: {resolved}")
    return resolved


def workspace_from_value(value: str | None) -> Path:
    workspace = Path(
        value if isinstance(value, str) and value.strip() else os.getenv("ONECODE_WORKSPACE_ROOT", os.getcwd())
    ).expanduser().resolve()
    if not workspace.exists() or not workspace.is_dir():
        raise ValueError(f"workspace does not exist or is not a directory: {workspace}")
    return require_allowed_workspace(workspace)


def workspace_from_request(body: dict[str, Any]) -> Path:
    metadata = body.get("metadata")
    workspace_value = metadata.get("workspace") if isinstance(metadata, dict) else None
    return workspace_from_value(workspace_value if isinstance(workspace_value, str) else None)
```

- [ ] **Step 4: Wire `api.py` workspace imports**

In `src/onecode/web/api.py`, remove local definitions for:

- `configured_allowed_workspace_roots`
- `path_inside_root`
- `workspace_allowed`
- `require_allowed_workspace`
- `workspace_from_value`
- `workspace_from_request`

Add:

```python
from .workspace import (
    configured_allowed_workspace_roots,
    path_inside_root,
    require_allowed_workspace,
    workspace_allowed,
    workspace_from_request,
    workspace_from_value,
)
```

Keep all imported names available at `onecode.web.api` module level for compatibility.

- [ ] **Step 5: Run workspace focused tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_web_api.OneCodeWebApiTests.test_workspace_module_rejects_path_outside_allowed_roots \
  tests.test_web_api.OneCodeWebApiTests.test_workspace_from_request_rejects_workspace_outside_allowed_roots \
  tests.test_web_api.OneCodeWebApiTests.test_workspace_from_request_accepts_workspace_inside_allowed_root \
  tests.test_web_api.OneCodeWebApiTests.test_project_status_reports_git_and_verifier_policy -v
```

Expected: all listed tests pass.

- [ ] **Step 6: Commit workspace extraction**

Run:

```bash
git add src/onecode/web/workspace.py src/onecode/web/api.py tests/test_web_api.py
git commit -m "refactor: extract web workspace helpers"
```

Expected: commit succeeds.

## Task 6: Full Web API Verification and Documentation

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/ONECODE_MAINTENANCE_LOG_2026-07-03.md`

- [ ] **Step 1: Run Web API test suite**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_web_api -v
```

Expected: all Web API tests pass. If local socket bind permission causes skips, record the exact skipped count.

- [ ] **Step 2: Run diff hygiene**

Run:

```bash
git diff --check -- src tests docs README.md scripts CHANGELOG.md
```

Expected: exits 0 with no output.

- [ ] **Step 3: Run full verification**

Run:

```bash
bash scripts/verify.sh
```

Expected: exits 0 with full unittest discovery passing and doctor `status: ok`.

- [ ] **Step 4: Update `CHANGELOG.md`**

Add this section above the 2026-07-03 hardening entry:

```markdown
## 2026-07-03 - vNext Maintenance Governance

### Updated

- Added release-line audit documentation for the GitHub review path.
- Began conservative Web API decomposition by extracting request-body,
  response, auth, and workspace helpers from `src/onecode/web/api.py`.
- Preserved existing `onecode.web.api` compatibility imports and endpoint
  behavior while reducing route-coordinator responsibility.

### Verification

- `PYTHONPATH=src python3 -m unittest tests.test_web_api -v`
- `git diff --check -- src tests docs README.md scripts CHANGELOG.md`
- `bash scripts/verify.sh`
```

- [ ] **Step 5: Update maintenance log**

Append to `docs/ONECODE_MAINTENANCE_LOG_2026-07-03.md`:

```markdown
## vNext Maintenance Governance Update

- Audited the GitHub release-line state after PR creation reported unrelated
  branch history.
- Extracted stable Web API helpers into focused modules while preserving
  `onecode.web.api` compatibility imports.
- Verified Web API behavior and full project health after extraction.
```

- [ ] **Step 6: Commit documentation update**

Run:

```bash
git add CHANGELOG.md docs/ONECODE_MAINTENANCE_LOG_2026-07-03.md
git commit -m "docs: record vnext maintenance governance update"
```

Expected: commit succeeds.

## Task 7: Final Publish Check

**Files:**
- No source edits unless verification finds a defect.

- [ ] **Step 1: Confirm project-local clean status**

Run:

```bash
git status --short .
```

Expected: no output for the current project directory after commits.

- [ ] **Step 2: Push branch**

Run:

```bash
git push origin feature/gateway-iching-rule-sync
```

Expected: push succeeds.

- [ ] **Step 3: Confirm local and upstream commits match**

Run:

```bash
git rev-parse HEAD @{u}
```

Expected: both printed commit hashes are identical.

## Plan Self-Review

- Spec coverage: covers P0 release-line governance, P1a helper extraction, documentation, verification, and publish check.
- Completion token scan: Task 1 verifies that instruction-only audit phrases are not left in the final audit document.
- Type consistency: helper names match current `src/onecode/web/api.py` names and compatibility imports preserve current `tests/test_web_api.py` imports.
