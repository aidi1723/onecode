# OneCode LibreChat B Mapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Productize the main OneCode agent loop inside the LibreChat shell with project status, run evidence, resume, verifier initialization, and workspace safety.

**Architecture:** OneCode core remains the execution and evidence source of truth, adding native JSON endpoints under `/v1/onecode/*`. LibreChat backend exposes authenticated local-only `/api/onecode/*` routes that call OneCode and manage local folder/MCP operations. LibreChat client keeps the existing compact project button beside attachments and expands it into a status/actions popover.

**Tech Stack:** Python stdlib HTTP server and unittest for OneCode; Express, Jest, TypeScript, React, Ariakit, lucide-react, and LibreChat data-provider patterns for the shell.

---

## File Map

OneCode core:

- Modify `src/onecode/web/api.py`: add workspace guard helpers, project status/init handlers, runs/inspect/resume handlers, and route dispatch.
- Modify `src/onecode/shell_launcher.py`: pass `ONECODE_ALLOWED_WORKSPACE_ROOTS` into both OneCode and LibreChat local environments.
- Modify `tests/test_web_api.py`: add endpoint and workspace guard coverage.
- Modify `tests/test_shell_launcher.py`: assert allowed workspace roots env is propagated.

LibreChat shell backend/data:

- Modify `api/server/services/OneCode/projectPicker.js`: add allowed-root helpers, project initialization, OneCode API proxy helpers, and safer create flow.
- Modify `api/server/services/OneCode/projectPicker.spec.js`: cover allowed-root checks, init, and proxy helper behavior.
- Modify `api/server/routes/onecode.js`: add project status/init/runs/inspect/resume routes.
- Modify `api/server/routes/onecode.spec.js`: cover route forwarding and rejection behavior.
- Modify `packages/data-provider/src/api-endpoints.ts`: add endpoint builders for status, init, runs, inspect, resume.
- Modify `packages/data-provider/src/data-service.ts`: add typed request functions.
- Modify `packages/data-provider/src/types.ts`: add OneCode status, run, inspect, and resume response types.

LibreChat shell client:

- Modify `client/src/onecode/project.ts`: add status/init/runs/inspect/resume client helpers and compact status derivation helpers.
- Modify `client/src/onecode/project.test.ts`: cover new helpers.
- Modify `client/src/components/Chat/Input/OneCodeProjectButton.tsx`: expand popover to show status badges and run actions.
- Add `client/src/components/Chat/Input/OneCodeProjectButton.test.tsx`: render and action tests using mocked data helpers.

Verification:

- Run OneCode targeted tests and `bash scripts/verify.sh`.
- Run LibreChat targeted Jest tests with coverage disabled or writable coverage output where sandbox allows.
- Manually smoke current local services with a selected workspace.

---

### Task 1: OneCode Workspace Guard And Native Project API

**Files:**
- Modify: `src/onecode/web/api.py`
- Modify: `tests/test_web_api.py`

- [ ] **Step 1: Add failing tests for allowed workspace roots**

Add these tests to `tests/test_web_api.py`:

```python
    def test_workspace_from_request_rejects_workspace_outside_allowed_roots(self):
        from onecode.web.api import workspace_from_request

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

    def test_workspace_from_request_accepts_workspace_inside_allowed_root(self):
        from onecode.web.api import workspace_from_request

        with tempfile.TemporaryDirectory() as allowed:
            child = Path(allowed) / "child"
            child.mkdir()
            with patch.dict(
                "os.environ",
                {
                    "ONECODE_WORKSPACE_ROOT": allowed,
                    "ONECODE_ALLOWED_WORKSPACE_ROOTS": allowed,
                },
                clear=True,
            ):
                workspace = workspace_from_request({"metadata": {"workspace": str(child)}})

        self.assertEqual(workspace, child.resolve())
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_web_api.OneCodeWebApiTests.test_workspace_from_request_rejects_workspace_outside_allowed_roots \
  tests.test_web_api.OneCodeWebApiTests.test_workspace_from_request_accepts_workspace_inside_allowed_root
```

Expected: outside-root rejection test fails because `workspace_from_request` does not yet enforce allowed roots.

- [ ] **Step 3: Implement allowed-root helpers**

In `src/onecode/web/api.py`, add helpers near `workspace_from_request`:

```python
def configured_allowed_workspace_roots() -> list[Path]:
    raw_roots = os.getenv("ONECODE_ALLOWED_WORKSPACE_ROOTS", "")
    roots = [part for part in raw_roots.split(os.pathsep) if part.strip()]
    if not roots:
        default_root = os.getenv("ONECODE_WORKSPACE_ROOT", os.getcwd())
        roots = [default_root]
    return [Path(root).expanduser().resolve() for root in roots]


def path_inside_root(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def workspace_allowed(workspace: Path, roots: list[Path] | None = None) -> bool:
    allowed_roots = roots if roots is not None else configured_allowed_workspace_roots()
    return any(path_inside_root(workspace.resolve(), root) for root in allowed_roots)


def require_allowed_workspace(workspace: Path) -> Path:
    resolved = workspace.resolve()
    if not workspace_allowed(resolved):
        raise ValueError(f"workspace outside allowed workspace roots: {resolved}")
    return resolved
```

Update `workspace_from_request` so after the exists/is_dir check it calls:

```python
    return require_allowed_workspace(workspace)
```

- [ ] **Step 4: Run tests to verify they pass**

Run the same command from Step 2.

Expected: both tests pass.

- [ ] **Step 5: Add failing tests for project status/init endpoints**

Add to `tests/test_web_api.py`:

```python
    def test_project_status_reports_git_and_verifier_policy(self):
        from onecode.web.api import handle_onecode_project_status

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ):
            workspace = Path(tmp)
            (workspace / ".git").mkdir()
            (workspace / ".onecode").mkdir()
            (workspace / ".onecode" / "verifier-policy.json").write_text(
                json.dumps({"verifiers": []}),
                encoding="utf-8",
            )

            payload, status = handle_onecode_project_status({"workspace": tmp})

        self.assertEqual(status, 200)
        self.assertTrue(payload["allowed"])
        self.assertTrue(payload["exists"])
        self.assertTrue(payload["git"]["present"])
        self.assertTrue(payload["verifier_policy"]["present"])

    def test_project_init_creates_git_and_default_verifier_policy(self):
        from onecode.web.api import handle_onecode_project_init

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ):
            workspace = Path(tmp) / "demo"
            workspace.mkdir()

            payload, status = handle_onecode_project_init(
                {"workspace": str(workspace), "git": True, "verifierPolicy": True}
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload["workspace"], str(workspace.resolve()))
        self.assertTrue((workspace / ".git").exists())
        self.assertTrue((workspace / ".onecode" / "verifier-policy.json").exists())
        self.assertTrue(payload["git"]["present"])
        self.assertTrue(payload["verifier_policy"]["present"])
```

- [ ] **Step 6: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_web_api.OneCodeWebApiTests.test_project_status_reports_git_and_verifier_policy \
  tests.test_web_api.OneCodeWebApiTests.test_project_init_creates_git_and_default_verifier_policy
```

Expected: import errors for missing handlers.

- [ ] **Step 7: Implement project status/init handlers**

In `src/onecode/web/api.py`, import:

```python
import subprocess
from onecode.kernel.verifier import DEFAULT_VERIFIER_POLICY_PATH, write_verifier_policy
from onecode.cli import inspect_run, list_runs
```

Add:

```python
def query_workspace_param(query: str) -> str | None:
    from urllib.parse import parse_qs

    values = parse_qs(query).get("workspace")
    return values[0] if values else None


def workspace_from_value(value: str | None) -> Path:
    workspace = Path(
        value if isinstance(value, str) and value.strip() else os.getenv("ONECODE_WORKSPACE_ROOT", os.getcwd())
    ).expanduser().resolve()
    if not workspace.exists() or not workspace.is_dir():
        raise ValueError(f"workspace does not exist or is not a directory: {workspace}")
    return require_allowed_workspace(workspace)


def project_status_payload(workspace: Path) -> dict[str, Any]:
    resolved = require_allowed_workspace(workspace)
    policy_path = resolved / DEFAULT_VERIFIER_POLICY_PATH
    runs = list_runs(resolved)["runs"]
    latest_run = runs[-1] if runs else None
    return {
        "workspace": str(resolved),
        "exists": resolved.exists() and resolved.is_dir(),
        "allowed": workspace_allowed(resolved),
        "allowed_roots": [str(root) for root in configured_allowed_workspace_roots()],
        "git": {"present": (resolved / ".git").exists()},
        "verifier_policy": {"present": policy_path.exists(), "path": str(policy_path)},
        "latest_run": latest_run,
    }


def handle_onecode_project_status(params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    return project_status_payload(workspace), 200


def handle_onecode_project_init(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(body.get("workspace") if isinstance(body.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    if body.get("git") is True and not (workspace / ".git").exists():
        subprocess.run(["git", "init"], cwd=str(workspace), check=True, capture_output=True, text=True)
    if body.get("verifierPolicy") is True and not (workspace / DEFAULT_VERIFIER_POLICY_PATH).exists():
        write_verifier_policy(workspace, output=DEFAULT_VERIFIER_POLICY_PATH)
    return project_status_payload(workspace), 200
```

- [ ] **Step 8: Route project status/init in `OneCodeRequestHandler`**

In `do_GET`, after `/v1/models`, add:

```python
        if path == "/v1/onecode/project/status":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            parsed = urlparse(self.path)
            payload, status_code = handle_onecode_project_status({"workspace": query_workspace_param(parsed.query)})
            self._send_json(payload, status_code=status_code)
            return
```

In `do_POST`, before the chat completion path check, add:

```python
        if path == "/v1/onecode/project/init":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json()
            if body is None:
                self._send_json(error_payload("invalid_json", "request body must be valid JSON"), status_code=400)
                return
            payload, status_code = handle_onecode_project_init(body)
            self._send_json(payload, status_code=status_code)
            return
```

- [ ] **Step 9: Run project tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_web_api.OneCodeWebApiTests.test_project_status_reports_git_and_verifier_policy tests.test_web_api.OneCodeWebApiTests.test_project_init_creates_git_and_default_verifier_policy
```

Expected: pass.

---

### Task 2: OneCode Runs, Inspect, And Resume API

**Files:**
- Modify: `src/onecode/web/api.py`
- Modify: `tests/test_web_api.py`

- [ ] **Step 1: Add failing tests for runs and inspect handlers**

Add to `tests/test_web_api.py`:

```python
    def test_onecode_runs_endpoint_lists_existing_run_summaries(self):
        from onecode.kernel.runner import run_task
        from onecode.web.api import handle_onecode_runs_list

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ):
            run_task("seed", workspace=Path(tmp), run_id="api-run", write_path="seed.txt", content="ok\n")
            payload, status = handle_onecode_runs_list({"workspace": tmp, "limit": "10"})

        self.assertEqual(status, 200)
        self.assertEqual(payload["runs"][0]["run_id"], "api-run")
        self.assertIn("ledger_path", payload["runs"][0])

    def test_onecode_inspect_endpoint_returns_cli_inspect_summary(self):
        from onecode.kernel.runner import run_task
        from onecode.web.api import handle_onecode_run_inspect

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ):
            run_task("seed", workspace=Path(tmp), run_id="inspect-api", write_path="seed.txt", content="ok\n")
            payload, status = handle_onecode_run_inspect("inspect-api", {"workspace": tmp})

        self.assertEqual(status, 200)
        self.assertEqual(payload["run_id"], "inspect-api")
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["delivery_status"], "deliverable")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_web_api.OneCodeWebApiTests.test_onecode_runs_endpoint_lists_existing_run_summaries \
  tests.test_web_api.OneCodeWebApiTests.test_onecode_inspect_endpoint_returns_cli_inspect_summary
```

Expected: import errors for missing handlers.

- [ ] **Step 3: Implement runs and inspect handlers**

Add to `src/onecode/web/api.py`:

```python
def parse_limit(value: Any, default: int = 20, maximum: int = 100) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(parsed, maximum))


def handle_onecode_runs_list(params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    payload = list_runs(workspace)
    limit = parse_limit(params.get("limit"))
    payload["runs"] = payload["runs"][-limit:]
    return payload, 200


def handle_onecode_run_inspect(run_id: str, params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    exit_code, payload = inspect_run(workspace, run_id)
    return payload, 200 if exit_code == 0 else 404
```

- [ ] **Step 4: Add GET routing for runs and inspect**

In `do_GET`, after project status routing, add:

```python
        if path == "/v1/onecode/runs":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            parsed = urlparse(self.path)
            from urllib.parse import parse_qs

            query = parse_qs(parsed.query)
            payload, status_code = handle_onecode_runs_list(
                {
                    "workspace": query.get("workspace", [None])[0],
                    "limit": query.get("limit", [None])[0],
                }
            )
            self._send_json(payload, status_code=status_code)
            return
        if path.startswith("/v1/onecode/runs/") and path.endswith("/inspect"):
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            run_id = path.removeprefix("/v1/onecode/runs/").removesuffix("/inspect").strip("/")
            parsed = urlparse(self.path)
            payload, status_code = handle_onecode_run_inspect(run_id, {"workspace": query_workspace_param(parsed.query)})
            self._send_json(payload, status_code=status_code)
            return
```

- [ ] **Step 5: Run tests to verify runs and inspect pass**

Run the command from Step 2.

Expected: pass.

- [ ] **Step 6: Add failing test for resume handler**

Add:

```python
    def test_onecode_resume_endpoint_runs_model_with_resume_from_run_id(self):
        from onecode.web.api import handle_onecode_run_resume

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ), patch("onecode.web.api.run_model_task") as run_model:
            run_model.return_value = {"run_id": "resumed-api", "status": "completed"}
            payload, status = handle_onecode_run_resume(
                "source-api",
                {"workspace": tmp, "message": "继续完成"},
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload["run_id"], "resumed-api")
        self.assertEqual(run_model.call_args.kwargs["resume_from_run_id"], "source-api")
        self.assertEqual(run_model.call_args.kwargs["workspace"], Path(tmp).resolve())
```

- [ ] **Step 7: Run resume test to verify it fails**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_web_api.OneCodeWebApiTests.test_onecode_resume_endpoint_runs_model_with_resume_from_run_id
```

Expected: import error for missing handler.

- [ ] **Step 8: Implement resume handler and route**

Add:

```python
def handle_onecode_run_resume(run_id: str, body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(body.get("workspace") if isinstance(body.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    message = body.get("message")
    task = message if isinstance(message, str) and message.strip() else f"继续运行 {run_id}"
    try:
        result = run_model_task(
            task,
            workspace=workspace,
            run_id=None,
            resume_from_run_id=run_id,
            model=os.getenv("ONECODE_MODEL") or os.getenv("OPENAI_MODEL") or None,
            provider_kind=os.getenv("ONECODE_MODEL_PROVIDER", "responses"),
            endpoint=os.getenv("ONECODE_MODEL_ENDPOINT") or None,
        )
    except MissingModelApiKey:
        result = run_task(task, workspace=workspace, resume_from_run_id=run_id)
    except ModelProviderError as exc:
        return error_payload("model_provider_error", str(exc)), 502
    return result, 200
```

In `do_POST`, before chat route check, add:

```python
        if path.startswith("/v1/onecode/runs/") and path.endswith("/resume"):
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json()
            if body is None:
                self._send_json(error_payload("invalid_json", "request body must be valid JSON"), status_code=400)
                return
            run_id = path.removeprefix("/v1/onecode/runs/").removesuffix("/resume").strip("/")
            payload, status_code = handle_onecode_run_resume(run_id, body)
            self._send_json(payload, status_code=status_code)
            return
```

- [ ] **Step 9: Run resume test**

Run command from Step 7.

Expected: pass.

---

### Task 3: Shell Launcher Environment And LibreChat Backend Proxy

**Files:**
- Modify: `src/onecode/shell_launcher.py`
- Modify: `tests/test_shell_launcher.py`
- Modify: `api/server/services/OneCode/projectPicker.js`
- Modify: `api/server/services/OneCode/projectPicker.spec.js`
- Modify: `api/server/routes/onecode.js`
- Modify: `api/server/routes/onecode.spec.js`

- [ ] **Step 1: Add failing shell launcher test for allowed roots env**

In `tests/test_shell_launcher.py`, add:

```python
    def test_shell_env_exports_allowed_workspace_roots(self):
        from onecode.shell_launcher import ShellLaunchConfig, build_librechat_env, build_onecode_env

        config = ShellLaunchConfig(
            onecode_root=Path("/tmp/onecode"),
            librechat_dir=Path("/tmp/librechat"),
            onecode_host="127.0.0.1",
            onecode_port=8080,
            librechat_host="127.0.0.1",
            librechat_port=3080,
            mongo_port=27017,
            api_token="token",
            workspace_root=Path("/tmp/workspaces"),
        )

        self.assertEqual(build_onecode_env(config, {})["ONECODE_ALLOWED_WORKSPACE_ROOTS"], "/tmp/workspaces")
        self.assertEqual(build_librechat_env(config, {})["ONECODE_ALLOWED_WORKSPACE_ROOTS"], "/tmp/workspaces")
```

- [ ] **Step 2: Run shell launcher test to verify it fails**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_shell_launcher.ShellLauncherConfigTests.test_shell_env_exports_allowed_workspace_roots
```

Expected: missing env key.

- [ ] **Step 3: Implement env propagation**

In `build_librechat_env`, add:

```python
"ONECODE_ALLOWED_WORKSPACE_ROOTS": str(config.workspace_root),
```

In `build_onecode_env`, add:

```python
env["ONECODE_ALLOWED_WORKSPACE_ROOTS"] = str(config.workspace_root)
```

- [ ] **Step 4: Run shell launcher test**

Run Step 2 command.

Expected: pass.

- [ ] **Step 5: Add backend service tests**

In `api/server/services/OneCode/projectPicker.spec.js`, add tests:

```javascript
it('rejects workspaces outside allowed roots', () => {
  const { workspaceInsideAllowedRoots } = require('./projectPicker');
  expect(workspaceInsideAllowedRoots('/tmp/root/project', ['/tmp/root'])).toBe(true);
  expect(workspaceInsideAllowedRoots('/tmp/other/project', ['/tmp/root'])).toBe(false);
});

it('builds OneCode API URLs from ONECODE_API_BASE_URL', () => {
  const { oneCodeApiUrl } = require('./projectPicker');
  expect(oneCodeApiUrl('/onecode/project/status')).toBe('http://localhost:8080/v1/onecode/project/status');
});
```

- [ ] **Step 6: Run backend service tests to verify they fail**

Run from `/Users/aidi/大字典/onecode-librechat/api`:

```bash
npx jest server/services/OneCode/projectPicker.spec.js --coverage=false --runInBand
```

Expected: missing exported helpers.

- [ ] **Step 7: Implement backend service helpers**

In `api/server/services/OneCode/projectPicker.js`, add:

```javascript
function allowedWorkspaceRoots() {
  return String(process.env.ONECODE_ALLOWED_WORKSPACE_ROOTS || process.env.ONECODE_WORKSPACE_ROOT || '')
    .split(path.delimiter)
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => path.resolve(item));
}

function workspaceInsideAllowedRoots(workspace, roots = allowedWorkspaceRoots()) {
  const resolved = path.resolve(String(workspace || ''));
  return roots.some((root) => resolved === root || resolved.startsWith(root + path.sep));
}

function requireAllowedWorkspace(workspace) {
  const resolved = path.resolve(String(workspace || ''));
  if (!workspaceInsideAllowedRoots(resolved)) {
    throw new Error(`workspace outside allowed roots: ${resolved}`);
  }
  return resolved;
}

function oneCodeApiUrl(pathname) {
  const base = (process.env.ONECODE_API_BASE_URL || 'http://localhost:8080/v1').replace(/\/$/, '');
  return `${base}${pathname}`;
}

async function oneCodeFetch(pathname, options = {}) {
  const response = await fetch(oneCodeApiUrl(pathname), {
    ...options,
    headers: {
      authorization: `Bearer ${process.env.ONECODE_API_TOKEN || 'dev-local-token'}`,
      'content-type': 'application/json',
      ...(options.headers || {}),
    },
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload?.error?.message || `OneCode request failed: ${response.status}`);
  }
  return payload;
}
```

Update `createOneCodeProject` to call `requireAllowedWorkspace(picked.workspace)` before joining the child, and call `requireAllowedWorkspace(workspace)` before `fs.mkdir`.

Export the helpers.

- [ ] **Step 8: Add proxy service functions**

In same file add and export:

```javascript
async function getOneCodeProjectStatus(workspace) {
  const resolved = requireAllowedWorkspace(workspace);
  return oneCodeFetch(`/onecode/project/status?workspace=${encodeURIComponent(resolved)}`);
}

async function initOneCodeProject(workspace) {
  const resolved = requireAllowedWorkspace(workspace);
  return oneCodeFetch('/onecode/project/init', {
    method: 'POST',
    body: JSON.stringify({ workspace: resolved, git: true, verifierPolicy: true }),
  });
}

async function listOneCodeRuns(workspace, limit = 20) {
  const resolved = requireAllowedWorkspace(workspace);
  return oneCodeFetch(`/onecode/runs?workspace=${encodeURIComponent(resolved)}&limit=${encodeURIComponent(limit)}`);
}

async function inspectOneCodeRun(workspace, runId) {
  const resolved = requireAllowedWorkspace(workspace);
  return oneCodeFetch(`/onecode/runs/${encodeURIComponent(runId)}/inspect?workspace=${encodeURIComponent(resolved)}`);
}

async function resumeOneCodeRun(workspace, runId, message) {
  const resolved = requireAllowedWorkspace(workspace);
  return oneCodeFetch(`/onecode/runs/${encodeURIComponent(runId)}/resume`, {
    method: 'POST',
    body: JSON.stringify({ workspace: resolved, message }),
  });
}
```

- [ ] **Step 9: Update routes**

In `api/server/routes/onecode.js`, import the new service functions and add:

```javascript
router.get('/projects/status', async (req, res) => {
  try {
    res.json(await getOneCodeProjectStatus(req.query?.workspace));
  } catch (error) {
    res.status(400).json({ error: error.message || 'failed to get OneCode project status' });
  }
});

router.post('/projects/init', async (req, res) => {
  try {
    res.json(await initOneCodeProject(req.body?.workspace));
  } catch (error) {
    res.status(400).json({ error: error.message || 'failed to initialize OneCode project' });
  }
});

router.get('/runs', async (req, res) => {
  try {
    res.json(await listOneCodeRuns(req.query?.workspace, req.query?.limit));
  } catch (error) {
    res.status(400).json({ error: error.message || 'failed to list OneCode runs' });
  }
});

router.get('/runs/:runId/inspect', async (req, res) => {
  try {
    res.json(await inspectOneCodeRun(req.query?.workspace, req.params.runId));
  } catch (error) {
    res.status(400).json({ error: error.message || 'failed to inspect OneCode run' });
  }
});

router.post('/runs/:runId/resume', async (req, res) => {
  try {
    res.json(await resumeOneCodeRun(req.body?.workspace, req.params.runId, req.body?.message));
  } catch (error) {
    res.status(400).json({ error: error.message || 'failed to resume OneCode run' });
  }
});
```

- [ ] **Step 10: Run backend service tests**

Run:

```bash
npx jest server/services/OneCode/projectPicker.spec.js --coverage=false --runInBand
```

Expected: pass.

Note: `server/routes/onecode.spec.js` may fail in this sandbox because `supertest` opens a listener. If it does, record the EPERM limitation and rely on service tests plus manual route smoke.

---

### Task 4: Data Provider And Client Project Popover

**Files:**
- Modify: `packages/data-provider/src/api-endpoints.ts`
- Modify: `packages/data-provider/src/data-service.ts`
- Modify: `packages/data-provider/src/types.ts`
- Modify: `client/src/onecode/project.ts`
- Modify: `client/src/onecode/project.test.ts`
- Modify: `client/src/components/Chat/Input/OneCodeProjectButton.tsx`

- [ ] **Step 1: Add data-provider endpoint builders**

In `packages/data-provider/src/api-endpoints.ts`, after existing OneCode endpoints add:

```typescript
export const oneCodeProjectStatus = (workspace: string) =>
  `${BASE_URL}/api/onecode/projects/status${buildQuery({ workspace })}`;
export const oneCodeProjectInit = () => `${BASE_URL}/api/onecode/projects/init`;
export const oneCodeRuns = (workspace: string, limit?: number) =>
  `${BASE_URL}/api/onecode/runs${buildQuery({ workspace, limit })}`;
export const oneCodeRunInspect = (runId: string, workspace: string) =>
  `${BASE_URL}/api/onecode/runs/${encodeURIComponent(runId)}/inspect${buildQuery({ workspace })}`;
export const oneCodeRunResume = (runId: string) =>
  `${BASE_URL}/api/onecode/runs/${encodeURIComponent(runId)}/resume`;
```

- [ ] **Step 2: Add types**

In `packages/data-provider/src/types.ts`, add:

```typescript
export type TOneCodeRunSummary = {
  run_id: string;
  status: string;
  reason?: string | null;
  delivery_status?: string;
  next_action?: string;
  ledger_path?: string;
  manifest_path?: string;
  checkpoint_count?: number;
};

export type TOneCodeProjectStatusResponse = {
  workspace: string;
  exists: boolean;
  allowed: boolean;
  allowed_roots?: string[];
  git?: { present: boolean };
  verifier_policy?: { present: boolean; path?: string };
  latest_run?: TOneCodeRunSummary | null;
};

export type TOneCodeRunsResponse = {
  workspace: string;
  runs: TOneCodeRunSummary[];
};

export type TOneCodeInspectResponse = TOneCodeRunSummary & {
  partial?: boolean;
  resumed_from?: string | null;
};

export type TOneCodeResumeResponse = Record<string, unknown>;
```

- [ ] **Step 3: Add data-service functions**

In `packages/data-provider/src/data-service.ts`, add:

```typescript
export const getOneCodeProjectStatus = (
  workspace: string,
): Promise<t.TOneCodeProjectStatusResponse> => {
  return request.get(endpoints.oneCodeProjectStatus(workspace));
};

export const initOneCodeProject = (
  workspace: string,
): Promise<t.TOneCodeProjectStatusResponse> => {
  return request.post(endpoints.oneCodeProjectInit(), { workspace });
};

export const listOneCodeRuns = (
  workspace: string,
  limit = 20,
): Promise<t.TOneCodeRunsResponse> => {
  return request.get(endpoints.oneCodeRuns(workspace, limit));
};

export const inspectOneCodeRun = (
  workspace: string,
  runId: string,
): Promise<t.TOneCodeInspectResponse> => {
  return request.get(endpoints.oneCodeRunInspect(runId, workspace));
};

export const resumeOneCodeRun = (
  workspace: string,
  runId: string,
  message?: string,
): Promise<t.TOneCodeResumeResponse> => {
  return request.post(endpoints.oneCodeRunResume(runId), { workspace, message });
};
```

- [ ] **Step 4: Add client helper tests**

In `client/src/onecode/project.test.ts`, add:

```typescript
  it('fetches OneCode project status through the data service', async () => {
    const getter = jest.fn().mockResolvedValue({ workspace: '/tmp/project-a', exists: true, allowed: true });
    await expect(getOneCodeProjectStatus('/tmp/project-a', getter)).resolves.toEqual({
      workspace: '/tmp/project-a',
      exists: true,
      allowed: true,
    });
    expect(getter).toHaveBeenCalledWith('/tmp/project-a');
  });

  it('derives compact project status labels', () => {
    expect(projectStatusBadges({ exists: true, allowed: true, git: { present: true }, verifier_policy: { present: false } })).toEqual([
      { kind: 'ok', label: '已允许' },
      { kind: 'ok', label: 'Git' },
      { kind: 'warn', label: '缺少验证策略' },
    ]);
  });
```

- [ ] **Step 5: Implement client helpers**

In `client/src/onecode/project.ts`, add types and functions:

```typescript
export type OneCodeProjectStatus = {
  workspace: string;
  exists: boolean;
  allowed: boolean;
  git?: { present: boolean };
  verifier_policy?: { present: boolean; path?: string };
  latest_run?: { run_id: string; status: string; next_action?: string } | null;
};

export type OneCodeStatusBadge = { kind: 'ok' | 'warn' | 'error'; label: string };

export function projectStatusBadges(status: Partial<OneCodeProjectStatus> | undefined): OneCodeStatusBadge[] {
  if (!status) return [];
  return [
    status.allowed ? { kind: 'ok', label: '已允许' } : { kind: 'error', label: '路径受限' },
    status.git?.present ? { kind: 'ok', label: 'Git' } : { kind: 'warn', label: '未初始化 Git' },
    status.verifier_policy?.present
      ? { kind: 'ok', label: '验证策略' }
      : { kind: 'warn', label: '缺少验证策略' },
  ];
}

export async function getOneCodeProjectStatus(
  workspace: string,
  getter: (workspace: string) => Promise<OneCodeProjectStatus> = dataService.getOneCodeProjectStatus,
): Promise<OneCodeProjectStatus | undefined> {
  const normalized = normalizeOneCodeWorkspace(workspace);
  return normalized ? getter(normalized) : undefined;
}

export async function initOneCodeProject(
  workspace: string,
  initializer: (workspace: string) => Promise<OneCodeProjectStatus> = dataService.initOneCodeProject,
): Promise<OneCodeProjectStatus | undefined> {
  const normalized = normalizeOneCodeWorkspace(workspace);
  return normalized ? initializer(normalized) : undefined;
}
```

Also export wrappers for `listOneCodeRuns`, `inspectOneCodeRun`, and `resumeOneCodeRun` using the same normalized workspace pattern.

- [ ] **Step 6: Run client helper tests**

Run from `client`:

```bash
npx jest src/onecode/project.test.ts --coverage=false --runInBand
```

Expected: pass.

- [ ] **Step 7: Expand project popover state**

In `OneCodeProjectButton.tsx`:

- Import new helpers and icons: `ShieldCheck`, `RotateCw`, `ListChecks`, `Play`.
- Add state:

```typescript
const [projectStatus, setProjectStatus] = useState<OneCodeProjectStatus | undefined>();
const [runs, setRuns] = useState<OneCodeRunSummary[]>([]);
const [statusError, setStatusError] = useState('');
```

- Add a `refreshProjectStatus` callback that calls `getOneCodeProjectStatus(workspace)` and `listOneCodeRuns(workspace, 5)`.
- Call `refreshProjectStatus` after selecting workspace, after MCP sync, and after project init.
- Add dropdown items:
  - Initialize verifier policy / project metadata: calls `initOneCodeProject(workspace)`.
  - View recent runs: refreshes runs.
  - Inspect latest run: calls `inspectOneCodeRun(workspace, latest.run_id)` and stores/display minimal summary.
  - Continue latest resumable run: calls `resumeOneCodeRun(workspace, latest.run_id, '继续完成上次运行')`.

Keep all actions inside the existing compact dropdown. Do not introduce a new page.

- [ ] **Step 8: Add minimal render test for popover helper if component test is too heavy**

If importing the full `OneCodeProjectButton` causes provider setup issues, add a pure helper in `client/src/onecode/project.ts`:

```typescript
export function latestRunActionLabel(run?: { next_action?: string } | null): string {
  return run?.next_action === 'resume' ? '继续最新运行' : '查看最新运行';
}
```

Test it in `client/src/onecode/project.test.ts`. This keeps behavior covered without overfitting to LibreChat providers.

---

### Task 5: Final Verification And Manual Smoke

**Files:**
- No required source edits unless verification reveals defects.

- [ ] **Step 1: Run OneCode targeted tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_web_api tests.test_shell_launcher
```

Expected: pass.

- [ ] **Step 2: Run OneCode full verification**

Run:

```bash
bash scripts/verify.sh
```

Expected: install, compileall, unittest `OK`, doctor `status: ok`.

- [ ] **Step 3: Run LibreChat targeted tests without coverage writes**

Run:

```bash
cd /Users/aidi/大字典/onecode-librechat/client
npx jest src/onecode/project.test.ts --coverage=false --runInBand
```

Run:

```bash
cd /Users/aidi/大字典/onecode-librechat/packages/api
npx jest src/endpoints/custom/onecode.spec.ts src/endpoints/custom/initialize.spec.ts --coverage=false --runInBand
```

Run:

```bash
cd /Users/aidi/大字典/onecode-librechat/api
npx jest server/services/OneCode/projectPicker.spec.js --coverage=false --runInBand
```

Expected: pass. If route tests using `supertest` are attempted and fail with `listen EPERM`, document sandbox limitation.

- [ ] **Step 4: Manual API smoke**

With local OneCode API running, run:

```bash
mkdir -p /private/tmp/onecode-b-mapping-smoke
curl -sS -H 'authorization: Bearer dev-local-token' \
  'http://127.0.0.1:8080/v1/onecode/project/status?workspace=/private/tmp/onecode-b-mapping-smoke'
curl -sS -H 'authorization: Bearer dev-local-token' -H 'content-type: application/json' \
  http://127.0.0.1:8080/v1/onecode/project/init \
  --data '{"workspace":"/private/tmp/onecode-b-mapping-smoke","git":true,"verifierPolicy":true}'
```

Expected: status response shows `allowed: true`; init response shows `git.present: true` and `verifier_policy.present: true`.

- [ ] **Step 5: Manual shell smoke**

Start or reuse the local shell at `http://127.0.0.1:3080`:

1. Log in locally.
2. Select or create a project with the folder button beside attachment.
3. Confirm badges show allowed workspace, Git, verifier policy, and MCP state.
4. Send a OneCode write task.
5. Open recent runs from the same popover.
6. Inspect the latest run.
7. Confirm the evidence ledger path points inside the selected workspace.

Expected: all operations complete without using any gateway service.

---

## Self-Review

- Spec coverage: all goals from `2026-05-30-onecode-librechat-b-mapping-design.md` map to tasks: workspace guards and OneCode native API in Tasks 1-2, shell env/backend in Task 3, client status/run UX in Task 4, verification in Task 5.
- Placeholder scan: no `TBD` or `TODO`; each task has concrete files, code snippets, commands, and expected results.
- Type consistency: OneCode response fields use snake_case from Python; TypeScript response types preserve those names to avoid lossy mapping.
- Scope check: plan stays in option B and explicitly avoids IDE features and gateway integration.
