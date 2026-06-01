# OneCode Console Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose OneCode's advanced kernel capabilities inside the LibreChat shell as a right-side console panel.

**Architecture:** OneCode core remains authoritative for execution, verifier policy, doctor, self-audit, and evidence. LibreChat adds local-only authenticated bridge routes and a compact React console panel that calls typed data-provider helpers. The existing OneCode project button remains the lightweight entry point and opens the panel.

**Tech Stack:** Python stdlib HTTP server and unittest; Express/Jest bridge routes; LibreChat data-provider TypeScript API layer; React, Ariakit-style tabs/buttons, lucide-react icons, and existing LibreChat/Tailwind tokens.

---

## File Map

OneCode core:

- Modify `src/onecode/web/api.py`: add verifier policy handlers, doctor/self-audit handlers, evidence loader, and HTTP routes.
- Modify `tests/test_web_api.py`: add unit coverage for new handlers and route behavior.

LibreChat backend:

- Modify `api/server/services/OneCode/projectPicker.js`: add OneCode API bridge functions for verifier, diagnostics, and evidence.
- Modify `api/server/services/OneCode/projectPicker.spec.js`: test URL construction, workspace validation, and bridge calls.
- Modify `api/server/routes/onecode.js`: add console routes.
- Modify `api/server/routes/onecode.spec.js`: test route delegation and local/auth rejection.

LibreChat data provider:

- Modify `packages/data-provider/src/api-endpoints.ts`: add endpoint builders.
- Modify `packages/data-provider/src/types.ts`: add verifier, diagnostics, and evidence types.
- Modify `packages/data-provider/src/data-service.ts`: add typed service functions.

LibreChat client:

- Modify `client/src/onecode/project.ts`: add client helpers for new APIs.
- Create `client/src/onecode/console.ts`: tab constants and display helpers.
- Create `client/src/components/OneCode/OneCodeConsolePanel.tsx`: top-level console panel.
- Create `client/src/components/OneCode/ProjectTab.tsx`
- Create `client/src/components/OneCode/RunsTab.tsx`
- Create `client/src/components/OneCode/EvidenceTab.tsx`
- Create `client/src/components/OneCode/VerifierTab.tsx`
- Create `client/src/components/OneCode/DiagnosticsTab.tsx`
- Create tests for helper and panel behavior.
- Modify `client/src/components/Chat/Input/OneCodeProjectButton.tsx`: add `打开控制台`.
- Modify `client/src/components/SidePanel/SidePanelGroup.tsx`: mount OneCode console beside chat.

Verification:

- Run OneCode focused tests and `bash scripts/verify.sh`.
- Run LibreChat focused Jest tests.
- Run `npm run build:data-provider`.
- Smoke local shell and bridge endpoints.

---

### Task 1: OneCode Console API

**Files:**
- Modify: `src/onecode/web/api.py`
- Modify: `tests/test_web_api.py`

- [ ] **Step 1: Add failing tests for verifier preset and policy handlers**

Add tests to `tests/test_web_api.py`:

```python
    def test_onecode_verifier_presets_endpoint_returns_presets(self):
        from onecode.web.api import handle_onecode_verifier_presets

        payload, status = handle_onecode_verifier_presets()

        self.assertEqual(status, 200)
        self.assertIn("presets", payload)
        self.assertGreaterEqual(len(payload["presets"]), 1)

    def test_onecode_verifier_policy_reports_missing_policy(self):
        from onecode.web.api import handle_onecode_verifier_policy_get

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ):
            payload, status = handle_onecode_verifier_policy_get({"workspace": tmp})

        self.assertEqual(status, 200)
        self.assertFalse(payload["exists"])
        self.assertFalse(payload["valid"])

    def test_onecode_verifier_policy_writes_and_reads_policy(self):
        from onecode.web.api import handle_onecode_verifier_policy_get, handle_onecode_verifier_policy_write

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ):
            write_payload, write_status = handle_onecode_verifier_policy_write(
                {"workspace": tmp, "presetIds": ["python-unittest"], "force": False}
            )
            read_payload, read_status = handle_onecode_verifier_policy_get({"workspace": tmp})

        self.assertEqual(write_status, 200)
        self.assertEqual(read_status, 200)
        self.assertTrue(write_payload["exists"])
        self.assertTrue(read_payload["valid"])
        self.assertEqual(read_payload["policy"]["verifiers"][0]["id"], "python-unittest")

    def test_onecode_verifier_policy_rejects_overwrite_without_force(self):
        from onecode.web.api import handle_onecode_verifier_policy_write

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ):
            handle_onecode_verifier_policy_write({"workspace": tmp, "presetIds": ["python-unittest"]})
            payload, status = handle_onecode_verifier_policy_write(
                {"workspace": tmp, "presetIds": ["python-unittest"], "force": False}
            )

        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["type"], "invalid_verifier_policy")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_web_api.OneCodeWebApiTests.test_onecode_verifier_presets_endpoint_returns_presets \
  tests.test_web_api.OneCodeWebApiTests.test_onecode_verifier_policy_reports_missing_policy \
  tests.test_web_api.OneCodeWebApiTests.test_onecode_verifier_policy_writes_and_reads_policy \
  tests.test_web_api.OneCodeWebApiTests.test_onecode_verifier_policy_rejects_overwrite_without_force
```

Expected: import errors for missing handlers.

- [ ] **Step 3: Implement verifier handlers**

In `src/onecode/web/api.py`, extend verifier imports:

```python
from onecode.kernel.verifier import (
    DEFAULT_VERIFIER_POLICY_PATH,
    load_verifier_policy,
    verifier_policy_presets_summary,
    write_verifier_policy,
)
```

Add helpers:

```python
def handle_onecode_verifier_presets() -> tuple[dict[str, Any], int]:
    return verifier_policy_presets_summary(), 200


def verifier_policy_payload(workspace: Path) -> dict[str, Any]:
    resolved = require_allowed_workspace(workspace)
    policy_path = resolved / DEFAULT_VERIFIER_POLICY_PATH
    payload: dict[str, Any] = {
        "workspace": str(resolved),
        "path": str(policy_path),
        "exists": policy_path.exists(),
        "valid": False,
        "policy": None,
    }
    if not policy_path.exists():
        return payload
    try:
        policy = load_verifier_policy(policy_path)
        payload["policy"] = {
            "verifiers": [
                {
                    "id": spec.id,
                    "command": spec.command,
                    "cwd": spec.cwd,
                    "timeout_ms": spec.timeout_ms,
                }
                for spec in policy.specs.values()
            ]
        }
        payload["valid"] = True
    except ValueError as exc:
        payload["error"] = str(exc)
    return payload


def handle_onecode_verifier_policy_get(params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    return verifier_policy_payload(workspace), 200


def handle_onecode_verifier_policy_write(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(body.get("workspace") if isinstance(body.get("workspace"), str) else None)
        preset_ids = body.get("presetIds")
        if preset_ids is not None and not all(isinstance(item, str) for item in preset_ids):
            return error_payload("invalid_verifier_policy", "presetIds must be a list of strings"), 400
        write_verifier_policy(
            workspace=workspace,
            output=DEFAULT_VERIFIER_POLICY_PATH,
            preset_ids=preset_ids if isinstance(preset_ids, list) else None,
            force=body.get("force") is True,
        )
    except ValueError as exc:
        return error_payload("invalid_verifier_policy", str(exc)), 400
    return verifier_policy_payload(workspace), 200
```

- [ ] **Step 4: Run verifier tests to verify they pass**

Run the same command from Step 2.

- [ ] **Step 5: Add failing tests for doctor, self-audit, and evidence**

Add:

```python
    def test_onecode_doctor_endpoint_returns_doctor_result(self):
        from onecode.web.api import handle_onecode_doctor

        with patch("onecode.web.api.run_doctor", return_value={"status": "ok", "checks": []}) as doctor:
            payload, status = handle_onecode_doctor()

        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(doctor.call_count, 1)

    def test_onecode_audit_self_endpoint_returns_audit_result(self):
        from onecode.web.api import handle_onecode_audit_self

        with patch("onecode.web.api.audit_self", return_value={"status": "ok", "checks": []}) as audit:
            payload, status = handle_onecode_audit_self()

        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(audit.call_count, 1)

    def test_onecode_run_evidence_returns_raw_ledger_manifest_and_checkpoints(self):
        from onecode.kernel.runner import run_task
        from onecode.web.api import handle_onecode_run_evidence

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ):
            run_task("seed", workspace=Path(tmp), run_id="evidence-api", write_path="seed.txt", write_content="ok\n")
            payload, status = handle_onecode_run_evidence("evidence-api", {"workspace": tmp})

        self.assertEqual(status, 200)
        self.assertEqual(payload["summary"]["run_id"], "evidence-api")
        self.assertEqual(payload["ledger"]["run_id"], "evidence-api")
        self.assertEqual(payload["manifest"]["run_id"], "evidence-api")
        self.assertEqual(len(payload["checkpoints"]), 1)
        self.assertIn("document", payload["checkpoints"][0])
```

- [ ] **Step 6: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_web_api.OneCodeWebApiTests.test_onecode_doctor_endpoint_returns_doctor_result \
  tests.test_web_api.OneCodeWebApiTests.test_onecode_audit_self_endpoint_returns_audit_result \
  tests.test_web_api.OneCodeWebApiTests.test_onecode_run_evidence_returns_raw_ledger_manifest_and_checkpoints
```

Expected: import errors.

- [ ] **Step 7: Implement doctor, self-audit, and evidence handlers**

In `src/onecode/web/api.py`, import:

```python
from onecode.cli import inspect_run, list_runs, run_doctor
from onecode.kernel.self_audit import audit_self
```

Add:

```python
def read_json_document(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "missing_file"
    except json.JSONDecodeError:
        return None, "invalid_json"
    if not isinstance(value, dict):
        return None, "not_object"
    return value, None


def handle_onecode_doctor() -> tuple[dict[str, Any], int]:
    return run_doctor(), 200


def handle_onecode_audit_self() -> tuple[dict[str, Any], int]:
    return audit_self(Path.cwd(), run_doctor, run_unittest=False), 200


def handle_onecode_run_evidence(run_id: str, params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    exit_code, summary = inspect_run(workspace, run_id)
    if exit_code != 0:
        return summary, 404
    ledger_path = Path(summary["ledger_path"])
    manifest_path = Path(summary["manifest_path"])
    ledger, ledger_error = read_json_document(ledger_path)
    manifest, manifest_error = read_json_document(manifest_path)
    checkpoints = []
    for record in (manifest or {}).get("checkpoints", []):
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            checkpoints.append({"record": record, "error": "invalid_checkpoint_record"})
            continue
        checkpoint_path = Path(record["path"])
        document, error = read_json_document(checkpoint_path)
        checkpoints.append(
            {
                "path": str(checkpoint_path),
                "record": record,
                "document": document,
                "error": error,
            }
        )
    return {
        "summary": summary,
        "ledger": ledger,
        "ledger_error": ledger_error,
        "manifest": manifest,
        "manifest_error": manifest_error,
        "checkpoints": checkpoints,
    }, 200
```

- [ ] **Step 8: Add HTTP routes**

Update `OneCodeRequestHandler.do_GET`:

```python
        if path == "/v1/onecode/verifier/presets":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            payload, status_code = handle_onecode_verifier_presets()
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/verifier/policy":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            parsed = urlparse(self.path)
            payload, status_code = handle_onecode_verifier_policy_get({"workspace": query_workspace_param(parsed.query)})
            self._send_json(payload, status_code=status_code)
            return
        if path.startswith("/v1/onecode/runs/") and path.endswith("/evidence"):
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            run_id = path.removeprefix("/v1/onecode/runs/").removesuffix("/evidence").strip("/")
            parsed = urlparse(self.path)
            payload, status_code = handle_onecode_run_evidence(run_id, {"workspace": query_workspace_param(parsed.query)})
            self._send_json(payload, status_code=status_code)
            return
```

Update `do_POST`:

```python
        if path == "/v1/onecode/verifier/policy":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json()
            if body is None:
                self._send_json(error_payload("invalid_json", "request body must be valid JSON"), status_code=400)
                return
            payload, status_code = handle_onecode_verifier_policy_write(body)
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/doctor":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            payload, status_code = handle_onecode_doctor()
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/audit-self":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            payload, status_code = handle_onecode_audit_self()
            self._send_json(payload, status_code=status_code)
            return
```

- [ ] **Step 9: Run OneCode focused tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_web_api
```

Expected: all web API tests pass.

---

### Task 2: LibreChat Bridge Routes

**Files:**
- Modify: `api/server/services/OneCode/projectPicker.js`
- Modify: `api/server/services/OneCode/projectPicker.spec.js`
- Modify: `api/server/routes/onecode.js`
- Modify: `api/server/routes/onecode.spec.js`

- [ ] **Step 1: Add service tests for new bridge calls**

In `api/server/services/OneCode/projectPicker.spec.js`, add tests that mock `global.fetch`:

```javascript
  it('fetches verifier presets from the OneCode API', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ presets: [] }),
    });
    const { getOneCodeVerifierPresets } = require('./projectPicker');

    await expect(getOneCodeVerifierPresets()).resolves.toEqual({ presets: [] });
    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8080/v1/onecode/verifier/presets',
      expect.objectContaining({ method: undefined }),
    );
  });

  it('forwards verifier policy writes for allowed workspaces', async () => {
    process.env.ONECODE_ALLOWED_WORKSPACE_ROOTS = '/tmp/onecode-root';
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ exists: true, valid: true }),
    });
    const { writeOneCodeVerifierPolicy } = require('./projectPicker');

    await expect(
      writeOneCodeVerifierPolicy('/tmp/onecode-root/project', ['python-unittest'], true),
    ).resolves.toEqual({ exists: true, valid: true });
  });
```

- [ ] **Step 2: Run service tests to verify they fail**

Run:

```bash
cd <local-user-path>
npx jest server/services/OneCode/projectPicker.spec.js --coverage=false --runInBand
```

Expected: missing exports.

- [ ] **Step 3: Implement bridge service functions**

Add to `projectPicker.js`:

```javascript
async function getOneCodeVerifierPresets() {
  return oneCodeFetch('/onecode/verifier/presets');
}

async function getOneCodeVerifierPolicy(workspace) {
  const resolved = requireAllowedWorkspace(workspace);
  return oneCodeFetch(`/onecode/verifier/policy?workspace=${encodeURIComponent(resolved)}`);
}

async function writeOneCodeVerifierPolicy(workspace, presetIds, force) {
  const resolved = requireAllowedWorkspace(workspace);
  return oneCodeFetch('/onecode/verifier/policy', {
    method: 'POST',
    body: JSON.stringify({ workspace: resolved, presetIds, force: force === true }),
  });
}

async function runOneCodeDoctor() {
  return oneCodeFetch('/onecode/doctor', { method: 'POST' });
}

async function runOneCodeSelfAudit() {
  return oneCodeFetch('/onecode/audit-self', { method: 'POST' });
}

async function getOneCodeRunEvidence(workspace, runId) {
  const resolved = requireAllowedWorkspace(workspace);
  return oneCodeFetch(
    `/onecode/runs/${encodeURIComponent(runId)}/evidence?workspace=${encodeURIComponent(resolved)}`,
  );
}
```

Export all six functions.

- [ ] **Step 4: Add routes**

In `api/server/routes/onecode.js`, import the new functions and add:

```javascript
router.get('/verifier/presets', async (_req, res) => {
  try {
    res.json(await getOneCodeVerifierPresets());
  } catch (error) {
    res.status(400).json({ error: error.message || 'failed to get OneCode verifier presets' });
  }
});

router.get('/verifier/policy', async (req, res) => {
  try {
    res.json(await getOneCodeVerifierPolicy(req.query?.workspace));
  } catch (error) {
    res.status(400).json({ error: error.message || 'failed to get OneCode verifier policy' });
  }
});

router.post('/verifier/policy', async (req, res) => {
  try {
    res.json(await writeOneCodeVerifierPolicy(req.body?.workspace, req.body?.presetIds, req.body?.force));
  } catch (error) {
    res.status(400).json({ error: error.message || 'failed to write OneCode verifier policy' });
  }
});

router.post('/doctor', async (_req, res) => {
  try {
    res.json(await runOneCodeDoctor());
  } catch (error) {
    res.status(400).json({ error: error.message || 'failed to run OneCode doctor' });
  }
});

router.post('/audit-self', async (_req, res) => {
  try {
    res.json(await runOneCodeSelfAudit());
  } catch (error) {
    res.status(400).json({ error: error.message || 'failed to run OneCode self audit' });
  }
});

router.get('/runs/:runId/evidence', async (req, res) => {
  try {
    res.json(await getOneCodeRunEvidence(req.query?.workspace, req.params.runId));
  } catch (error) {
    res.status(400).json({ error: error.message || 'failed to get OneCode run evidence' });
  }
});
```

- [ ] **Step 5: Add route tests**

In `api/server/routes/onecode.spec.js`, add tests following existing mocks:

```javascript
  it('forwards verifier presets requests', async () => {
    projectPicker.getOneCodeVerifierPresets.mockResolvedValue({ presets: [] });
    const response = await request(app)
      .get('/api/onecode/verifier/presets')
      .set('Authorization', 'Bearer test-token');
    expect(response.status).toBe(200);
    expect(response.body).toEqual({ presets: [] });
  });

  it('forwards run evidence requests', async () => {
    projectPicker.getOneCodeRunEvidence.mockResolvedValue({ summary: { run_id: 'run-1' } });
    const response = await request(app)
      .get('/api/onecode/runs/run-1/evidence?workspace=/tmp/project')
      .set('Authorization', 'Bearer test-token');
    expect(response.status).toBe(200);
    expect(projectPicker.getOneCodeRunEvidence).toHaveBeenCalledWith('/tmp/project', 'run-1');
  });
```

- [ ] **Step 6: Run bridge tests**

Run:

```bash
cd <local-user-path>
npx jest server/routes/onecode.spec.js server/services/OneCode/projectPicker.spec.js --coverage=false --runInBand
```

Expected: all tests pass.

---

### Task 3: Data Provider And Client Helpers

**Files:**
- Modify: `packages/data-provider/src/api-endpoints.ts`
- Modify: `packages/data-provider/src/types.ts`
- Modify: `packages/data-provider/src/data-service.ts`
- Modify: `client/src/onecode/project.ts`
- Modify: `client/src/onecode/project.test.ts`

- [ ] **Step 1: Add data-provider endpoint builders**

Add to `packages/data-provider/src/api-endpoints.ts`:

```typescript
export const oneCodeVerifierPresets = () => `${BASE_URL}/api/onecode/verifier/presets`;

export const oneCodeVerifierPolicy = (workspace: string) =>
  `${BASE_URL}/api/onecode/verifier/policy${buildQuery({ workspace })}`;

export const oneCodeVerifierPolicyWrite = () => `${BASE_URL}/api/onecode/verifier/policy`;

export const oneCodeDoctor = () => `${BASE_URL}/api/onecode/doctor`;

export const oneCodeSelfAudit = () => `${BASE_URL}/api/onecode/audit-self`;

export const oneCodeRunEvidence = (runId: string, workspace: string) =>
  `${BASE_URL}/api/onecode/runs/${encodeURIComponent(runId)}/evidence${buildQuery({ workspace })}`;
```

- [ ] **Step 2: Add data-provider types**

Add to `packages/data-provider/src/types.ts`:

```typescript
export type TOneCodeVerifierPreset = {
  id: string;
  command: string[];
  cwd: string;
  timeout_ms: number;
};

export type TOneCodeVerifierPresetsResponse = {
  presets: TOneCodeVerifierPreset[];
};

export type TOneCodeVerifierPolicyResponse = {
  workspace: string;
  path: string;
  exists: boolean;
  valid: boolean;
  policy?: { verifiers: TOneCodeVerifierPreset[] } | null;
  error?: string;
};

export type TOneCodeDiagnosticCheck = {
  name: string;
  passed: boolean;
  detail?: Record<string, unknown>;
};

export type TOneCodeDiagnosticResponse = {
  status: string;
  checks: TOneCodeDiagnosticCheck[];
  [key: string]: unknown;
};

export type TOneCodeRunEvidenceResponse = {
  summary: TOneCodeInspectResponse;
  ledger: Record<string, unknown> | null;
  ledger_error?: string | null;
  manifest: Record<string, unknown> | null;
  manifest_error?: string | null;
  checkpoints: Array<{
    path?: string;
    record?: Record<string, unknown>;
    document?: Record<string, unknown> | null;
    error?: string | null;
  }>;
};
```

- [ ] **Step 3: Add data-service functions**

Add to `packages/data-provider/src/data-service.ts`:

```typescript
export const getOneCodeVerifierPresets = (): Promise<t.TOneCodeVerifierPresetsResponse> => {
  return request.get(endpoints.oneCodeVerifierPresets());
};

export const getOneCodeVerifierPolicy = (
  workspace: string,
): Promise<t.TOneCodeVerifierPolicyResponse> => {
  return request.get(endpoints.oneCodeVerifierPolicy(workspace));
};

export const writeOneCodeVerifierPolicy = (
  workspace: string,
  presetIds?: string[],
  force?: boolean,
): Promise<t.TOneCodeVerifierPolicyResponse> => {
  return request.post(endpoints.oneCodeVerifierPolicyWrite(), { workspace, presetIds, force });
};

export const runOneCodeDoctor = (): Promise<t.TOneCodeDiagnosticResponse> => {
  return request.post(endpoints.oneCodeDoctor());
};

export const runOneCodeSelfAudit = (): Promise<t.TOneCodeDiagnosticResponse> => {
  return request.post(endpoints.oneCodeSelfAudit());
};

export const getOneCodeRunEvidence = (
  workspace: string,
  runId: string,
): Promise<t.TOneCodeRunEvidenceResponse> => {
  return request.get(endpoints.oneCodeRunEvidence(runId, workspace));
};
```

- [ ] **Step 4: Add client helper tests**

Add to `client/src/onecode/project.test.ts`:

```typescript
  it('fetches verifier policy only for selected workspaces', async () => {
    const getter = jest.fn().mockResolvedValue({ exists: true, valid: true });

    await expect(getOneCodeVerifierPolicy('/tmp/project-a', getter)).resolves.toEqual({
      exists: true,
      valid: true,
    });
    await expect(getOneCodeVerifierPolicy('', getter)).resolves.toBeUndefined();
    expect(getter).toHaveBeenCalledTimes(1);
  });

  it('fetches run evidence only when workspace and run id are present', async () => {
    const getter = jest.fn().mockResolvedValue({ summary: { run_id: 'run-1' }, checkpoints: [] });

    await expect(getOneCodeRunEvidence('/tmp/project-a', 'run-1', getter)).resolves.toEqual({
      summary: { run_id: 'run-1' },
      checkpoints: [],
    });
    await expect(getOneCodeRunEvidence('/tmp/project-a', '', getter)).resolves.toBeUndefined();
    expect(getter).toHaveBeenCalledTimes(1);
  });
```

Update imports in that test for the new helpers.

- [ ] **Step 5: Add client helper implementation**

In `client/src/onecode/project.ts`, add types and helpers:

```typescript
export type OneCodeVerifierPreset = {
  id: string;
  command: string[];
  cwd: string;
  timeout_ms: number;
};

export type OneCodeVerifierPolicy = {
  workspace: string;
  path: string;
  exists: boolean;
  valid: boolean;
  policy?: { verifiers: OneCodeVerifierPreset[] } | null;
  error?: string;
};

export type OneCodeDiagnostic = {
  status: string;
  checks: Array<{ name: string; passed: boolean; detail?: Record<string, unknown> }>;
  [key: string]: unknown;
};

export type OneCodeRunEvidence = {
  summary: OneCodeRunSummary;
  ledger: Record<string, unknown> | null;
  manifest: Record<string, unknown> | null;
  checkpoints: Array<Record<string, unknown>>;
};
```

Add functions:

```typescript
export async function getOneCodeVerifierPresets(
  getter: () => Promise<{ presets: OneCodeVerifierPreset[] }> =
    dataService.getOneCodeVerifierPresets,
): Promise<OneCodeVerifierPreset[]> {
  const payload = await getter();
  return Array.isArray(payload.presets) ? payload.presets : [];
}

export async function getOneCodeVerifierPolicy(
  workspace: string,
  getter: (workspace: string) => Promise<OneCodeVerifierPolicy> =
    dataService.getOneCodeVerifierPolicy,
): Promise<OneCodeVerifierPolicy | undefined> {
  const normalized = normalizeOneCodeWorkspace(workspace);
  return normalized ? getter(normalized) : undefined;
}

export async function writeOneCodeVerifierPolicy(
  workspace: string,
  presetIds?: string[],
  force?: boolean,
  writer: (workspace: string, presetIds?: string[], force?: boolean) => Promise<OneCodeVerifierPolicy> =
    dataService.writeOneCodeVerifierPolicy,
): Promise<OneCodeVerifierPolicy | undefined> {
  const normalized = normalizeOneCodeWorkspace(workspace);
  return normalized ? writer(normalized, presetIds, force) : undefined;
}

export async function runOneCodeDoctor(
  runner: () => Promise<OneCodeDiagnostic> = dataService.runOneCodeDoctor,
): Promise<OneCodeDiagnostic> {
  return runner();
}

export async function runOneCodeSelfAudit(
  runner: () => Promise<OneCodeDiagnostic> = dataService.runOneCodeSelfAudit,
): Promise<OneCodeDiagnostic> {
  return runner();
}

export async function getOneCodeRunEvidence(
  workspace: string,
  runId: string,
  getter: (workspace: string, runId: string) => Promise<OneCodeRunEvidence> =
    dataService.getOneCodeRunEvidence,
): Promise<OneCodeRunEvidence | undefined> {
  const normalized = normalizeOneCodeWorkspace(workspace);
  const normalizedRunId = normalizeOneCodeWorkspace(runId);
  return normalized && normalizedRunId ? getter(normalized, normalizedRunId) : undefined;
}
```

- [ ] **Step 6: Build data-provider and run client helper tests**

Run:

```bash
cd <local-user-path>
npm run build:data-provider
cd client
npx jest src/onecode/project.test.ts --coverage=false --runInBand --reporters=default
```

Expected: build succeeds and tests pass.

---

### Task 4: OneCode Console Panel UI

**Files:**
- Create: `client/src/onecode/console.ts`
- Create: `client/src/components/OneCode/OneCodeConsolePanel.tsx`
- Create: `client/src/components/OneCode/ProjectTab.tsx`
- Create: `client/src/components/OneCode/RunsTab.tsx`
- Create: `client/src/components/OneCode/EvidenceTab.tsx`
- Create: `client/src/components/OneCode/VerifierTab.tsx`
- Create: `client/src/components/OneCode/DiagnosticsTab.tsx`
- Create: `client/src/components/OneCode/OneCodeConsolePanel.test.tsx`

- [ ] **Step 1: Add console state helper**

Create `client/src/onecode/console.ts`:

```typescript
export const ONECODE_CONSOLE_TABS = ['project', 'runs', 'evidence', 'verifier', 'diagnostics'] as const;

export type OneCodeConsoleTab = (typeof ONECODE_CONSOLE_TABS)[number];

export const ONECODE_CONSOLE_TAB_LABELS: Record<OneCodeConsoleTab, string> = {
  project: '项目',
  runs: '运行',
  evidence: '证据',
  verifier: '验证',
  diagnostics: '诊断',
};

export function oneCodeStatusTone(status?: string | null): 'ok' | 'warn' | 'error' {
  if (status === 'completed' || status === 'ok' || status === 'deliverable') {
    return 'ok';
  }
  if (status === 'halted' || status === 'failed' || status === 'corrupt') {
    return 'error';
  }
  return 'warn';
}
```

- [ ] **Step 2: Add tab components**

Create tab components with props only; avoid internal fetching in the tab components. Example for `ProjectTab.tsx`:

```typescript
import { RotateCw, ShieldCheck, Link2 } from 'lucide-react';
import type { OneCodeProjectStatus } from '~/onecode/project';

export default function ProjectTab({
  workspace,
  status,
  message,
  onRefresh,
  onInit,
  onSyncMCP,
}: {
  workspace: string;
  status?: OneCodeProjectStatus;
  message?: string;
  onRefresh: () => void;
  onInit: () => void;
  onSyncMCP: () => void;
}) {
  return (
    <div className="space-y-3 p-3 text-sm text-text-primary">
      <div>
        <div className="text-xs font-medium text-text-secondary">Workspace</div>
        <div className="mt-1 break-all font-mono text-xs">{workspace || '未选择项目'}</div>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="rounded border border-border-light p-2">Git: {status?.git?.present ? '已初始化' : '未初始化'}</div>
        <div className="rounded border border-border-light p-2">验证: {status?.verifier_policy?.present ? '已配置' : '未配置'}</div>
      </div>
      {message && <div className="text-xs text-text-secondary">{message}</div>}
      <div className="flex flex-wrap gap-2">
        <button type="button" className="btn btn-neutral btn-sm" onClick={onRefresh}><RotateCw className="icon-sm" />刷新</button>
        <button type="button" className="btn btn-neutral btn-sm" onClick={onInit}><ShieldCheck className="icon-sm" />初始化</button>
        <button type="button" className="btn btn-neutral btn-sm" onClick={onSyncMCP}><Link2 className="icon-sm" />同步 MCP</button>
      </div>
    </div>
  );
}
```

Create `RunsTab`, `EvidenceTab`, `VerifierTab`, and `DiagnosticsTab` with the same compact pattern. Each gets typed props and renders simple buttons/lists/JSON `<pre>` blocks.

- [ ] **Step 3: Add console panel top-level component**

Create `OneCodeConsolePanel.tsx` that:

- Reads `workspace` from `getStoredOneCodeWorkspace()` on mount.
- Keeps state for selected tab, project status, runs, selected run ID, evidence, verifier policy/presets, doctor result, self-audit result, and message.
- Has `refreshProject`, `refreshRuns`, `loadEvidence`, `loadVerifier`, `runDoctor`, `runSelfAudit`.
- Renders tab buttons from `ONECODE_CONSOLE_TAB_LABELS`.

Use the helper functions from `~/onecode/project`.

- [ ] **Step 4: Add focused panel test**

Create `OneCodeConsolePanel.test.tsx` mocking `~/onecode/project`:

```typescript
it('renders project status and loads runs', async () => {
  mockProject.getStoredOneCodeWorkspace.mockReturnValue('/tmp/project');
  mockProject.getOneCodeProjectStatus.mockResolvedValue({
    workspace: '/tmp/project',
    exists: true,
    allowed: true,
    git: { present: true },
    verifier_policy: { present: true },
  });
  mockProject.listOneCodeRuns.mockResolvedValue([{ run_id: 'run-1', status: 'completed' }]);

  render(<OneCodeConsolePanel onClose={jest.fn()} />);

  expect(await screen.findByText('/tmp/project')).toBeInTheDocument();
  fireEvent.click(screen.getByText('运行'));
  expect(await screen.findByText('run-1')).toBeInTheDocument();
});
```

- [ ] **Step 5: Run console test**

Run:

```bash
cd <local-user-path>
npx jest src/components/OneCode/OneCodeConsolePanel.test.tsx --coverage=false --runInBand --reporters=default
```

Expected: pass.

---

### Task 5: Panel Mounting And Button Integration

**Files:**
- Modify: `client/src/components/SidePanel/SidePanelGroup.tsx`
- Modify: `client/src/components/Chat/Input/OneCodeProjectButton.tsx`
- Modify: `client/src/components/Chat/Input/OneCodeProjectButton.test.tsx`

- [ ] **Step 1: Add a lightweight browser event bridge**

In `client/src/onecode/console.ts`, add:

```typescript
export const ONECODE_CONSOLE_OPEN_EVENT = 'onecode:console-open';

export function openOneCodeConsole(): void {
  window.dispatchEvent(new CustomEvent(ONECODE_CONSOLE_OPEN_EVENT));
}
```

- [ ] **Step 2: Mount panel in `SidePanelGroup`**

Modify `SidePanelGroup.tsx`:

- Import `useEffect`.
- Import `OneCodeConsolePanel` and `ONECODE_CONSOLE_OPEN_EVENT`.
- Add state `const [showOneCodeConsole, setShowOneCodeConsole] = useState(false);`.
- Listen for the open event.
- Compute `const sideContent = showOneCodeConsole ? <OneCodeConsolePanel onClose={() => setShowOneCodeConsole(false)} /> : artifacts;`.
- Use `sideContent` wherever `artifacts` is currently used.
- Use panel IDs split when either artifacts or console exists.

- [ ] **Step 3: Add button action**

In `OneCodeProjectButton.tsx`, import `PanelRightOpen` and `openOneCodeConsole`.

Add menu item when workspace exists:

```typescript
items.push({
  id: 'onecode-open-console',
  label: '打开控制台',
  icon: <PanelRightOpen className="icon-md" />,
  onClick: openOneCodeConsole,
});
```

Place it before refresh/status actions.

- [ ] **Step 4: Extend button test**

In `OneCodeProjectButton.test.tsx`, mock `openOneCodeConsole` or listen for the event and assert clicking `打开控制台` emits it.

Example:

```typescript
it('opens the OneCode console from the project menu', () => {
  mockProjectState.workspace = '/tmp/onecode-demo';
  const listener = jest.fn();
  window.addEventListener('onecode:console-open', listener);

  render(<OneCodeProjectButton />);
  fireEvent.click(screen.getByRole('button', { name: 'OneCode 项目' }));
  fireEvent.click(screen.getByText('打开控制台'));

  expect(listener).toHaveBeenCalledTimes(1);
  window.removeEventListener('onecode:console-open', listener);
});
```

- [ ] **Step 5: Run client integration tests**

Run:

```bash
cd <local-user-path>
npx jest \
  src/onecode/project.test.ts \
  src/components/OneCode/OneCodeConsolePanel.test.tsx \
  src/components/Chat/Input/OneCodeProjectButton.test.tsx \
  --coverage=false --runInBand --reporters=default
```

Expected: pass.

---

### Task 6: Verification And Smoke

**Files:**
- No feature files unless fixing verification failures.

- [ ] **Step 1: Run OneCode full verification**

Run:

```bash
cd <local-user-path> code
bash scripts/verify.sh
```

Expected: unittest and doctor pass.

- [ ] **Step 2: Run LibreChat backend tests**

Run:

```bash
cd <local-user-path>
npx jest server/routes/onecode.spec.js server/services/OneCode/projectPicker.spec.js --coverage=false --runInBand
```

Expected: pass.

- [ ] **Step 3: Run packages API tests**

Run:

```bash
cd <local-user-path>
npx jest src/endpoints/custom/onecode.spec.ts src/endpoints/custom/initialize.spec.ts --coverage=false --runInBand
```

Expected: pass.

- [ ] **Step 4: Build data provider**

Run:

```bash
cd <local-user-path>
npm run build:data-provider
```

Expected: build succeeds.

- [ ] **Step 5: Run local smoke**

Start shell on non-conflicting ports:

```bash
cd <local-user-path> code
PYTHONPATH=src python3 -m onecode shell \
  --onecode-port 18080 \
  --librechat-port 13080 \
  --mongo-port 37017 \
  --workspace <private-temp-path> \
  --no-browser \
  --show-credentials
```

In another terminal, log in and call bridge endpoints:

```bash
TOKEN=$(curl -sS -H 'content-type: application/json' \
  -X POST http://127.0.0.1:13080/api/auth/login \
  --data '{"email":"onecode@local.test","password":"OneCode123!"}' \
  | node -pe 'JSON.parse(fs.readFileSync(0,"utf8")).token')

curl -sS -H "authorization: Bearer $TOKEN" \
  'http://127.0.0.1:13080/api/onecode/verifier/presets'

curl -sS -H "authorization: Bearer $TOKEN" -X POST \
  'http://127.0.0.1:13080/api/onecode/doctor'
```

Expected: verifier presets include at least one preset, doctor returns `status`.

---

## Self-Review

- Spec coverage: API additions, shell bridge routes, data-provider helpers, right-side panel, button entry, tests, smoke all have implementation tasks.
- Placeholder scan: no `TBD`, `TODO`, or unspecified implementation steps remain.
- Type consistency: OneCode naming uses `verifierPolicy`, `presetIds`, `runEvidence`, and existing `workspace` / `runId` conventions consistently.
