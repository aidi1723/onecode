# OneCode LibreChat v0.8.7 Upgrade and Runtime Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the OneCode Web shell to LibreChat `v0.8.7`, eliminate retry-amplified model timeouts, persist local shell state, and preserve every current OneCode shell workflow with deterministic evidence and rollback.

**Architecture:** Keep OneCode and LibreChat in separate isolated worktrees. Normalize model failures inside OneCode, return structured Web errors, configure the OneCode LibreChat endpoint with zero outer retries, and port existing shell features onto the `v0.8.7` extension points in bounded backend, data, and UI slices.

**Tech Stack:** Python 3.11 stdlib HTTP/unittest, OneCode evidence kernel, LibreChat v0.8.7, Node >=20.19 (verified with 24.14.1), npm 11.13.0 through Corepack, TypeScript/React, Jest, Vite, Playwright.

---

## Worktree Map

- OneCode implementation worktree: `/Users/aidi/大字典/one code/.worktrees/onecode-shell-v087-hardening/one code`
- Original LibreChat customization worktree: `/Users/aidi/大字典/onecode-librechat`
- LibreChat upgrade worktree to create: `/Users/aidi/大字典/one code/.worktrees/librechat-v087`
- LibreChat checkpoint branch to create: `checkpoint/onecode-shell-pre-v087-20260715`
- LibreChat upgrade branch to create: `feature/onecode-shell-v087-hardening`
- Community baseline tag: `v0.8.7` (`9e74cc0e5`)

## File Map

### OneCode

- Modify `src/onecode/kernel/model_provider.py`: typed provider timeout.
- Modify `src/onecode/kernel/model_loop.py`: terminal failed trace and halted evidence.
- Modify `src/onecode/web/api.py`: 504/502 structured shell results.
- Create `src/onecode/shell_state.py`: atomic private persistent shell state.
- Modify `src/onecode/shell_launcher.py`: preflight checks, persistent secrets,
  Mongo path, bounded logs, process records, and provenance.
- Modify `src/onecode/cli_commands/local_interfaces.py`: `--state-dir` public CLI option.
- Modify `tests/test_model_provider_contract.py`, `tests/test_model_loop.py`,
  `tests/test_web_api.py`, and `tests/test_shell_launcher.py`.
- Create `tests/test_shell_state.py`, `tests/test_shell_timeout_integration.py`,
  and `tests/fixtures/delayed_model_server.py`.

### LibreChat v0.8.7

- Create `DESIGN.md` and `ONECODE_SHELL.md` from the checkpoint with updated provenance.
- Create `packages/api/src/endpoints/custom/onecode.ts` and its spec.
- Modify `packages/api/src/endpoints/custom/initialize.ts` and its spec.
- Modify `api/server/services/Endpoints/agents/build.js` and add/port its spec.
- Create/port `api/server/routes/onecode.js` and its spec.
- Create/port `api/server/services/OneCode/projectPicker.js` and its spec.
- Modify `api/server/index.js` and `api/server/routes/index.js` only at route registration boundaries.
- Modify `packages/api/src/types/http.ts`.
- Modify `packages/data-provider/src/api-endpoints.ts`, `data-service.ts`, and `types.ts`.
- Create/port `client/src/onecode/console.ts`, `project.ts`, and `project.test.ts`.
- Create/port `client/src/onecode/brand.ts` and `brand.test.ts` without changing
  the existing exported property names.
- Create/port `client/src/components/OneCode/*` and
  `client/src/components/Chat/Input/OneCodeProjectButton*`.
- Modify `client/src/components/Chat/Input/ChatForm.tsx`,
  `client/src/components/SidePanel/SidePanelGroup.tsx`,
  `client/src/hooks/Chat/useChatFunctions.ts`, and
  `client/src/hooks/Nav/useSideNavLinks.ts` at narrow integration points.
- Modify `client/src/locales/en/translation.json`; preserve the existing local
  Chinese translations in `zh-Hans` without bulk locale churn.
- Modify `librechat.yaml`, `.env.example`, `package.json`, and
  `scripts/onecode-smoke.mjs`.

## Task 1: Preserve LibreChat and Establish the v0.8.7 Baseline

**Files:**
- Checkpoint existing tracked and OneCode-owned untracked files in `/Users/aidi/大字典/onecode-librechat`
- Create worktree `/Users/aidi/大字典/one code/.worktrees/librechat-v087`

- [ ] **Step 1: Create the checkpoint branch without cleaning the worktree**

Run:

```bash
cd '/Users/aidi/大字典/onecode-librechat'
git switch -c checkpoint/onecode-shell-pre-v087-20260715
git add -u
git add DESIGN.md \
  api/server/routes/onecode.js api/server/routes/onecode.spec.js \
  api/server/services/Endpoints/agents/build.spec.js \
  api/server/services/OneCode \
  client/src/components/Chat/Input/OneCodeProjectButton.tsx \
  client/src/components/Chat/Input/OneCodeProjectButton.test.tsx \
  client/src/components/OneCode \
  client/src/components/SidePanel/SidePanelGroup.test.tsx \
  client/src/onecode \
  packages/api/src/endpoints/custom/onecode.ts \
  packages/api/src/endpoints/custom/onecode.spec.ts
```

Expected: `.env`, `node_modules`, `logs`, `.playwright-cli`, and `.superpowers` are not staged.

- [ ] **Step 2: Verify checkpoint scope and secrets**

Run:

```bash
git diff --cached --check
git diff --cached --name-only
if git diff --cached | rg --pcre2 -n \
  'sk-(?!test(?:[-_]|$))[A-Za-z0-9_-]{12,}|BEGIN (RSA |OPENSSH )?PRIVATE KEY|api[_-]?key\s*[:=]\s*[^$<{]'; then
  exit 1
fi
git diff --cached | rg -n 'sk-|api[_-]?key' || true
```

Expected: whitespace check passes; the secret scan returns no real credential.
`${...}` examples and test-only `sk-test-*` fixtures are reviewed explicitly.

- [ ] **Step 3: Commit the preserved customization state**

```bash
git commit -m "chore: checkpoint OneCode shell before v0.8.7"
git status --short
```

Expected: only excluded runtime artifacts remain untracked.

- [ ] **Step 4: Create the clean LibreChat worktree from the exact tag**

```bash
git worktree add '/Users/aidi/大字典/one code/.worktrees/librechat-v087' \
  -b feature/onecode-shell-v087-hardening v0.8.7
cd '/Users/aidi/大字典/one code/.worktrees/librechat-v087'
git rev-parse HEAD
git describe --tags --exact-match
```

Expected: commit `9e74cc0e5...` and tag `v0.8.7`.

- [ ] **Step 5: Record community provenance and supply-chain boundaries**

Run from the clean worktree:

```bash
test "$(git remote get-url origin)" = 'https://github.com/danny-avila/LibreChat.git'
test "$(git rev-parse 'v0.8.7^{commit}')" = '9e74cc0e57b395926122bd4062c1fcedc48ed465'
git show v0.8.7:LICENSE | sed -n '1,20p'
git show v0.8.7:package.json | sed -n '1,125p'
git diff --name-only v0.8.7^..v0.8.7 -- package.json package-lock.json '*/package.json'
```

Expected: origin is the official `danny-avila/LibreChat` repository, the tag
resolves to the pinned commit, and the repository license is MIT. Record that
`v0.8.7` is a lightweight unsigned tag and that the root package manifest says
ISC while the repository `LICENSE` says MIT; preserve both upstream records in
the closure report instead of silently normalizing them.

- [ ] **Step 6: Create the customization migration inventory**

```bash
git diff --name-status a16f08a42..checkpoint/onecode-shell-pre-v087-20260715 > \
  /private/tmp/onecode-v087-migration-inventory.txt
wc -l /private/tmp/onecode-v087-migration-inventory.txt
sed -n '1,240p' /private/tmp/onecode-v087-migration-inventory.txt
```

Expected: every tracked customization and every OneCode-owned file appears.
Task 12 must classify each row as `ported`, `superseded-by-v0.8.7`, or
`approved-removal`; no row may disappear without a closure-record entry.

- [ ] **Step 7: Install and verify the untouched community baseline**

```bash
node --version
corepack npm --version
corepack npm ci
npm run build:data-provider
npm run build:client
```

Expected: supported Node >=20.19, Corepack-selected npm `11.13.0`, clean dependency install, data-provider build, and client build all pass before OneCode files are ported.

- [ ] **Step 8: Record the baseline evidence outside source control**

```bash
git status --short
git log -1 --format='%H %cI %s'
```

Expected: source tree remains clean after baseline verification; `node_modules` and generated build output remain ignored.

## Task 2: Convert Raw Timeouts into a Typed Provider Error

**Files:**
- Modify: `src/onecode/kernel/model_provider.py`
- Modify: `tests/test_model_provider_contract.py`

- [ ] **Step 1: Write the failing provider timeout tests**

Add imports and tests:

```python
from unittest.mock import patch

from onecode.kernel.model_provider import ModelProviderTimeout


class ModelProviderTimeoutTests(unittest.TestCase):
    def test_responses_timeout_is_typed(self):
        provider = OpenAIResponsesProvider("key", endpoint="http://model.test/responses")
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            with self.assertRaisesRegex(ModelProviderTimeout, "model request timed out"):
                provider.create_plan("check", model="m", http_timeout_seconds=1)

    def test_chat_timeout_is_typed(self):
        provider = OpenAIChatCompletionsProvider("key", endpoint="http://model.test/chat/completions")
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            with self.assertRaisesRegex(ModelProviderTimeout, "model request timed out"):
                provider.create_plan("check", model="m", http_timeout_seconds=1)
```

- [ ] **Step 2: Run RED**

Run: `.venv/bin/python -m unittest tests.test_model_provider_contract -v`

Expected: import failure because `ModelProviderTimeout` does not exist.

- [ ] **Step 3: Implement the minimal typed error**

Add next to `ModelProviderError`:

```python
class ModelProviderTimeout(ModelProviderError):
    pass
```

Change both timeout handlers to:

```python
except TimeoutError as exc:
    raise ModelProviderTimeout("model request timed out") from exc
```

- [ ] **Step 4: Run GREEN**

Run: `.venv/bin/python -m unittest tests.test_model_provider_contract -v`

Expected: all provider contract tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/onecode/kernel/model_provider.py tests/test_model_provider_contract.py
git commit -m "fix: type model provider timeouts"
```

## Task 3: Persist Failed Model Calls as Terminal Evidence

**Files:**
- Modify: `src/onecode/kernel/model_loop.py`
- Modify: `tests/test_model_loop.py`

- [ ] **Step 1: Write failing terminal-evidence tests**

Add a provider and test:

```python
from onecode.kernel.model_provider import ModelProviderTimeout


class TimeoutProvider:
    def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
        raise ModelProviderTimeout("model request timed out")


class InvalidPlanProvider:
    def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
        raise ValueError("model response was not valid JSON")


class SequenceThenTimeoutProvider:
    def __init__(self, first_plan):
        self.first_plan = first_plan
        self.call_count = 0

    def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
        self.call_count += 1
        if self.call_count == 1:
            return self.first_plan
        raise ModelProviderTimeout("model request timed out")


def test_model_timeout_writes_failed_terminal_evidence(self):
    with tempfile.TemporaryDirectory() as tmp:
        result = run_model_task(
            "check project",
            workspace=Path(tmp),
            run_id="model-timeout",
            api_key="key",
            model="m",
            provider=TimeoutProvider(),
            task_mode="read_task",
            safe_agent_route=SafeAgentRoute("no_match", "no_matching_scenario", schema_version=2),
        )

        events = [json.loads(line) for line in Path(result["trace_path"]).read_text().splitlines()]
        model_events = [event["event_type"] for event in events if event["span_id"] == "model-call"]

        self.assertEqual((result["status"], result["reason"]), ("halted", "model_provider_timeout"))
        self.assertEqual(model_events, ["model_call_started", "model_call_failed"])
        self.assertTrue(Path(result["ledger_path"]).is_file())
        self.assertTrue(Path(result["manifest_path"]).is_file())
        self.assertNotIn("key", Path(result["ledger_path"]).read_text(encoding="utf-8"))


def test_invalid_model_plan_writes_failed_terminal_evidence(self):
    with tempfile.TemporaryDirectory() as tmp:
        result = run_model_task(
            "check project",
            workspace=Path(tmp),
            run_id="invalid-model-plan",
            api_key="key",
            model="m",
            provider=InvalidPlanProvider(),
        )
        events = [json.loads(line) for line in Path(result["trace_path"]).read_text().splitlines()]
        terminal = [
            event for event in events
            if event["span_id"] == "model-call"
            and event["event_type"] in {"model_call_completed", "model_call_failed"}
        ]
        self.assertEqual(result["reason"], "invalid_model_plan")
        self.assertEqual([event["event_type"] for event in terminal], ["model_call_failed"])
        self.assertTrue(Path(result["ledger_path"]).is_file())
        self.assertTrue(Path(result["manifest_path"]).is_file())


def test_repair_timeout_has_its_own_failed_terminal_event(self):
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        first_plan = ModelPlan(
            task="build broken module",
            execution_steps=[
                ModelExecutionStep(
                    id="write",
                    description="write invalid python",
                    tool_calls=[
                        ModelToolCall(
                            tool_name="write_text",
                            params={"path": "src/generated.py", "content": "def status():\n    return (\n"},
                        )
                    ],
                ),
                ModelExecutionStep(
                    id="patch",
                    description="compile-gated patch should fail",
                    depends_on=["write"],
                    tool_calls=[
                        ModelToolCall(
                            tool_name="patch_text",
                            params={
                                "path": "src/generated.py",
                                "search_block": "return (",
                                "replace_block": "return [",
                            },
                        )
                    ],
                ),
            ],
        )
        result = run_model_task(
            "build module with repair",
            workspace=workspace,
            run_id="repair-timeout",
            model="test-model",
            api_key="test-key",
            provider=SequenceThenTimeoutProvider(first_plan),
            max_repair_attempts=1,
        )
        events = [json.loads(line) for line in Path(result["trace_path"]).read_text().splitlines()]
        by_span = {
            span: [event["event_type"] for event in events if event["span_id"] == span]
            for span in ("model-call", "model-repair-1")
        }
        self.assertEqual(by_span["model-call"], ["model_call_started", "model_call_completed"])
        self.assertEqual(by_span["model-repair-1"], ["model_call_started", "model_call_failed"])
```

- [ ] **Step 2: Run RED**

Run: `.venv/bin/python -m unittest tests.test_model_loop -v`

Expected: timeout and invalid-plan errors escape or lack complete evidence;
the repair call has no independent terminal trace.

- [ ] **Step 3: Add one traced provider-call boundary**

Import `time`, `ModelProviderError`, `ModelProviderTimeout`, and
`halted_result`. Add a helper used by both the initial and repair calls:

```python
def traced_provider_plan(
    *,
    provider: Any,
    task: str,
    model_context: Any,
    trace_path: Path,
    provider_config: Any,
    resolved_model: str,
    http_timeout_seconds: float,
    planning_context: dict[str, Any],
    span_id: str,
) -> tuple[ModelPlan | None, dict[str, Any] | None]:
    started_at = time.monotonic()
    write_trace_event(
        trace_path,
        TraceEvent(
            trace_id=model_context.run_id,
            run_id=model_context.run_id,
            span_id=span_id,
            parent_span_id="run",
            event_type="model_call_started",
            status="started",
            payload={"provider": provider_config.provider_kind, "model": resolved_model},
        ),
    )
    try:
        plan = _create_provider_plan(
            provider,
            task,
            model=resolved_model,
            http_timeout_seconds=http_timeout_seconds,
            planning_context=planning_context,
        )
    except (ModelProviderError, ValueError) as exc:
        if isinstance(exc, ModelProviderTimeout):
            reason = "model_provider_timeout"
        elif isinstance(exc, ModelProviderError):
            reason = "model_provider_error"
        elif str(exc) == "plan must include at least one asset":
            reason = "no_actionable_plan"
        else:
            reason = "invalid_model_plan"
        elapsed_ms = max(0, int((time.monotonic() - started_at) * 1000))
        failure = {
            "provider": provider_config.provider_kind,
            "model": resolved_model,
            "failure_kind": reason,
            "elapsed_ms": elapsed_ms,
            "retryable": False,
            "safe_agent": planning_context["safe_agent"],
        }
        write_trace_event(
            trace_path,
            TraceEvent(
                trace_id=model_context.run_id,
                run_id=model_context.run_id,
                span_id=span_id,
                parent_span_id="run",
                event_type="model_call_failed",
                status="halted",
                duration_ms=elapsed_ms,
                payload=failure,
            ),
        )
        return None, failure
    elapsed_ms = max(0, int((time.monotonic() - started_at) * 1000))
    write_trace_event(
        trace_path,
        TraceEvent(
            trace_id=model_context.run_id,
            run_id=model_context.run_id,
            span_id=span_id,
            parent_span_id="run",
            event_type="model_call_completed",
            status="completed",
            duration_ms=elapsed_ms,
            payload={
                "provider": provider_config.provider_kind,
                "model": resolved_model,
                "asset_count": len(plan.assets),
                "patch_count": len(plan.patches),
                "execution_step_count": len(plan.execution_steps),
                "no_action": plan.no_action_reason is not None,
            },
        ),
    )
    return plan, None


def failed_model_result(model_context: Any, failure: dict[str, Any]) -> dict[str, Any]:
    return halted_result(
        model_context,
        reason=str(failure["failure_kind"]),
        payload=failure,
        trace_id=model_context.run_id,
        checkpoint_intent_type="model_plan",
        write_checkpoint_evidence=True,
    )
```

- [ ] **Step 4: Route every provider call through the helper**

Replace the existing initial start/call/completed block with:

```python
plan, failure = traced_provider_plan(
    provider=active_provider,
    task=task,
    model_context=model_context,
    trace_path=trace_path,
    provider_config=provider_config,
    resolved_model=resolved_model,
    http_timeout_seconds=http_timeout_seconds,
    planning_context=planning_context,
    span_id="model-call",
)
if failure is not None:
    return failed_model_result(model_context, failure)
assert plan is not None
```

Use the same helper for every repair call with
`span_id=f"model-repair-{attempt}"`. If a repair call fails, return
`failed_model_result(model_context, failure)` immediately. This guarantees
each actual provider call has exactly one started event and exactly one
completed-or-failed event with a unique span ID.

- [ ] **Step 5: Run GREEN and regression tests**

Run:

```bash
.venv/bin/python -m unittest \
  tests.test_model_provider_contract \
  tests.test_model_loop \
  tests.test_trace -v
```

Expected: timeout evidence test and existing completed-call trace tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/onecode/kernel/model_loop.py tests/test_model_loop.py
git commit -m "fix: finalize failed model planning evidence"
```

## Task 4: Return Stable Web Errors for Model Failures

**Files:**
- Modify: `src/onecode/web/api.py`
- Modify: `tests/test_web_api.py`

- [ ] **Step 1: Write failing Web result tests**

```python
def test_chat_completion_returns_504_for_timeout_result(self):
    timeout_result = {
        "run_id": "timeout-run",
        "status": "halted",
        "reason": "model_provider_timeout",
        "trace_path": "/tmp/trace.jsonl",
        "ledger_path": "/tmp/ledger.json",
        "manifest_path": "/tmp/manifest.json",
    }
    with tempfile.TemporaryDirectory() as tmp, patch.dict(
        "os.environ", {"ONECODE_HOME": str(Path(tmp) / "home")}, clear=True
    ), patch("onecode.web.api.run_model_task", return_value=timeout_result):
        payload, status_code = handle_chat_completion(
            {"model": "onecode-agent", "messages": [{"role": "user", "content": "检查项目"}]}
        )

    self.assertEqual(status_code, 504)
    self.assertEqual(payload["error"]["type"], "model_provider_timeout")
    self.assertEqual(payload["onecode"]["result"]["run_id"], "timeout-run")


def test_chat_completion_returns_502_for_provider_failure_result(self):
    provider_result = {"run_id": "failed-run", "status": "halted", "reason": "model_provider_error"}
    with tempfile.TemporaryDirectory() as tmp, patch.dict(
        "os.environ", {"ONECODE_HOME": str(Path(tmp) / "home")}, clear=True
    ), patch("onecode.web.api.run_model_task", return_value=provider_result):
        payload, status_code = handle_chat_completion(
            {"model": "onecode-agent", "messages": [{"role": "user", "content": "检查项目"}]}
        )
    self.assertEqual((status_code, payload["error"]["type"]), (502, "model_provider_error"))


def test_chat_completion_passes_configured_model_timeout(self):
    completed = {"run_id": "run", "status": "completed", "reason": "completed"}
    with tempfile.TemporaryDirectory() as tmp, patch.dict(
        "os.environ",
        {"ONECODE_HOME": str(Path(tmp) / "home"), "ONECODE_MODEL_TIMEOUT_SECONDS": "0.25"},
        clear=True,
    ), patch(
        "onecode.web.api.run_model_task", return_value=completed
    ) as run_model:
        handle_chat_completion(
            {"model": "onecode-agent", "messages": [{"role": "user", "content": "检查项目"}]}
        )
    self.assertEqual(run_model.call_args.kwargs["http_timeout_seconds"], 0.25)


def test_invalid_timeout_setting_is_rejected_without_a_model_call(self):
    with tempfile.TemporaryDirectory() as tmp, patch.dict(
        "os.environ",
        {"ONECODE_HOME": str(Path(tmp) / "home"), "ONECODE_MODEL_TIMEOUT_SECONDS": "0"},
        clear=True,
    ), patch(
        "onecode.web.api.run_model_task"
    ) as run_model:
        payload, status_code = handle_chat_completion(
            {"model": "onecode-agent", "messages": [{"role": "user", "content": "检查项目"}]}
        )
    self.assertEqual((status_code, payload["error"]["type"]), (503, "invalid_model_timeout"))
    run_model.assert_not_called()
```

- [ ] **Step 2: Run RED**

Run: `.venv/bin/python -m unittest tests.test_web_api.WebApiTests.test_chat_completion_returns_504_for_timeout_result -v`

Expected: current handler returns HTTP 200 model-mode output.

- [ ] **Step 3: Add the explicit bounded timeout setting**

Add next to the Web constants:

```python
DEFAULT_MODEL_TIMEOUT_SECONDS = 60.0
MAX_MODEL_TIMEOUT_SECONDS = 600.0


def model_timeout_seconds_from_env() -> float:
    raw = os.getenv("ONECODE_MODEL_TIMEOUT_SECONDS", str(DEFAULT_MODEL_TIMEOUT_SECONDS))
    try:
        value = float(raw)
    except ValueError:
        raise ValueError("ONECODE_MODEL_TIMEOUT_SECONDS must be a number") from None
    if not 0 < value <= MAX_MODEL_TIMEOUT_SECONDS:
        raise ValueError("ONECODE_MODEL_TIMEOUT_SECONDS must be greater than zero and at most 600")
    return value
```

Resolve the value before `run_model_task`, return HTTP 503
`invalid_model_timeout` on invalid configuration, and pass the value as
`http_timeout_seconds`. Do not silently fall back when the operator supplied
an invalid value.

- [ ] **Step 4: Add one result-to-error boundary**

After `run_model_task` returns, before choosing mode:

```python
failure_statuses = {
    "model_provider_timeout": 504,
    "model_provider_error": 502,
    "invalid_model_plan": 502,
}
failure_reason = result.get("reason")
if failure_reason in failure_statuses:
    payload = error_payload(failure_reason, "model planning failed before execution")
    payload["onecode"] = {"mode": "model", "result": result}
    return payload, failure_statuses[failure_reason]
```

Set mode to `no_action` when the structured result reason is
`no_actionable_plan`; otherwise preserve `approval_required` and `model`.
Keep the existing exception handlers for injected providers and backward
compatibility. Do not expose raw upstream exception text.

- [ ] **Step 5: Run GREEN and HTTP regression tests**

```bash
.venv/bin/python -m unittest tests.test_web_api -v
```

Expected: direct handler and local HTTP server tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/onecode/web/api.py tests/test_web_api.py
git commit -m "fix: surface model planning failures over HTTP"
```

## Task 5: Add Atomic Persistent Shell State

**Files:**
- Create: `src/onecode/shell_state.py`
- Create: `tests/test_shell_state.py`
- Modify: `src/onecode/shell_launcher.py`
- Modify: `tests/test_shell_launcher.py`

- [ ] **Step 1: Write failing state tests**

Import `stat` and `ThreadPoolExecutor` from `concurrent.futures`, then add:

```python
class ShellStateTests(unittest.TestCase):
    def test_auth_secrets_are_reused_for_the_same_state_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "state"
            first = load_or_create_shell_secrets(root)
            second = load_or_create_shell_secrets(root)
        self.assertEqual(first, second)

    def test_state_permissions_are_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "state"
            load_or_create_shell_secrets(root)
            self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE((root / "auth-secrets.json").stat().st_mode), 0o600)

    def test_corrupt_secret_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "state"
            root.mkdir(mode=0o700)
            (root / "auth-secrets.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid shell secret state"):
                load_or_create_shell_secrets(root)

    def test_concurrent_initialization_returns_one_secret_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "state"
            with ThreadPoolExecutor(max_workers=8) as pool:
                values = list(pool.map(lambda _: load_or_create_shell_secrets(root), range(16)))
        self.assertEqual(len(set(values)), 1)
```

- [ ] **Step 2: Run RED**

Run: `.venv/bin/python -m unittest tests.test_shell_state -v`

Expected: module import failure.

- [ ] **Step 3: Implement the private state module**

Create an immutable `ShellSecrets` dataclass with `jwt_secret`,
`jwt_refresh_secret`, `creds_key`, and `creds_iv`. Implement
`load_or_create_shell_secrets(root)` with:

```python
root.mkdir(parents=True, exist_ok=True, mode=0o700)
root.chmod(0o700)
path = root / "auth-secrets.json"
if path.exists():
    return validate_shell_secrets(json.loads(path.read_text(encoding="utf-8")))
payload = ShellSecrets(
    jwt_secret=secrets.token_hex(32),
    jwt_refresh_secret=secrets.token_hex(32),
    creds_key=secrets.token_hex(32),
    creds_iv=secrets.token_hex(16),
)
write_private_text(path, json.dumps(asdict(payload), sort_keys=True) + "\n")
return payload
```

Use the existing `write_private_text` atomic-write pattern from
`kernel/model_config.py`. Hold `file_lock(root / ".auth-secrets.lock")` from
`kernel/checkpoint.py` across the existence check, read, validation, and first
write so concurrent launchers cannot return different generated values.
Validate exact key names and hex lengths when reading; a corrupt or
partially-written file fails closed instead of rotating authentication.

- [ ] **Step 4: Integrate secrets into the LibreChat environment**

Change `build_librechat_env()` to call the state loader when explicit secrets
are absent from `base_env`. Preserve explicit operator-provided values. Remove
the test that requires fresh secrets and replace it with a test that two calls
using the same `runtime_state_root` return identical values.

- [ ] **Step 5: Run GREEN**

```bash
.venv/bin/python -m unittest tests.test_shell_state tests.test_shell_launcher -v
```

Expected: state and launcher tests pass, and no real `~/.onecode` files are touched.

- [ ] **Step 6: Commit**

```bash
git add src/onecode/shell_state.py src/onecode/shell_launcher.py tests/test_shell_state.py tests/test_shell_launcher.py
git commit -m "feat: persist private shell authentication state"
```

## Task 6: Persist Mongo State and Improve Shell Diagnostics

**Files:**
- Modify: `src/onecode/shell_launcher.py`
- Modify: `src/onecode/shell_state.py`
- Modify: `src/onecode/cli_commands/local_interfaces.py`
- Modify: `tests/test_shell_launcher.py`
- Modify: `tests/test_shell_state.py`

- [ ] **Step 1: Write failing launcher configuration tests**

Import `json`, `CompletedProcess`, and the new launcher/state helpers, then add:

```python
def test_state_dir_defaults_under_onecode_home(self):
    with patch.dict("os.environ", {"ONECODE_HOME": "/tmp/onecode-home"}, clear=False):
        config = config_from_args(shell_args())
    self.assertEqual(config.runtime_state_root, Path("/tmp/onecode-home/shell"))

def test_mongo_command_uses_persistent_db_path(self):
    config = shell_config(runtime_state_root=Path("/tmp/state"))
    command = mongo_command(config)
    self.assertIn("/tmp/state/mongo", " ".join(command))

def test_shell_status_never_returns_password(self):
    result = shell_status(shell_config())
    self.assertNotIn("password", json.dumps(result).lower())

def test_runtime_config_sets_onecode_retry_limit(self):
    path = build_runtime_config(shell_config())
    self.assertIn("maxRetries: 0", path.read_text(encoding="utf-8"))

def test_model_timeout_cli_reaches_onecode_environment(self):
    config = shell_config(model_timeout_seconds=12.5)
    self.assertEqual(build_onecode_env(config, {})["ONECODE_MODEL_TIMEOUT_SECONDS"], "12.5")

def test_provenance_requires_v087_as_an_ancestor(self):
    config = shell_config()
    with patch("onecode.shell_launcher.subprocess.run") as run:
        run.side_effect = [
            CompletedProcess([], 0, "abc123\n", ""),
            CompletedProcess([], 0, "", ""),
        ]
        result = librechat_provenance(config)
    self.assertEqual(result["community_base_commit"], EXPECTED_LIBRECHAT_COMMIT)
    self.assertEqual(result["head_commit"], "abc123")
    self.assertTrue(result["community_base_is_ancestor"])

def test_preflight_rejects_an_occupied_port(self):
    with patch("onecode.shell_launcher.port_is_available", return_value=False):
        with self.assertRaisesRegex(RuntimeError, "port .* is already in use"):
            preflight_shell(shell_config())

def test_bounded_service_log_redacts_and_caps_output(self):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "service.log"
        append_bounded_log(path, "Authorization: Bearer secret-token\n" + "x" * 5000, max_bytes=1024)
        text = path.read_text(encoding="utf-8")
    self.assertLessEqual(len(text.encode("utf-8")), 1024)
    self.assertNotIn("secret-token", text)

def test_runtime_status_contains_only_service_names_and_pids(self):
    with tempfile.TemporaryDirectory() as tmp:
        write_runtime_status(Path(tmp), status="running", services={"mongo": 123})
        payload = json.loads((Path(tmp) / "runtime-status.json").read_text())
    self.assertEqual(payload["services"], {"mongo": 123})
    self.assertNotIn("token", json.dumps(payload).lower())
```

- [ ] **Step 2: Run RED**

Run: `.venv/bin/python -m unittest tests.test_shell_launcher -v`

Expected: temporary state root, inline Mongo command, password output,
missing retry/timeout settings, absent provenance/preflight helpers, and absent
bounded runtime records fail the new assertions.

- [ ] **Step 3: Add explicit state configuration**

Add `--state-dir` and `--model-timeout-seconds` to both `shell` and
`shell-status`. Add `model_timeout_seconds: float = 60.0` to
`ShellLaunchConfig`. Resolve the state default as:

```python
onecode_home = Path(os.getenv("ONECODE_HOME", "~/.onecode")).expanduser()
runtime_state_root = Path(state_dir).expanduser().resolve() if state_dir else onecode_home / "shell"
```

Reject timeout values outside `(0, 600]` in `config_from_args`. In
`build_onecode_env`, set:

```python
env["ONECODE_MODEL_TIMEOUT_SECONDS"] = str(config.model_timeout_seconds)
```

Add `mongo_command(config)` that creates `runtime_state_root / "mongo"` with
mode `0700` and passes it as MongoMemoryServer `instance.dbPath`. The Node
snippet must retain the server object and handle `SIGINT`/`SIGTERM` with
`server.stop({ doCleanup: false })`; never call `cleanup({ force: true })` on
the operator's persistent path. Keep host, port, and `dbName` explicit.

- [ ] **Step 4: Add startup preflight and version provenance**

Add constants:

```python
EXPECTED_LIBRECHAT_VERSION = "v0.8.7"
EXPECTED_LIBRECHAT_COMMIT = "9e74cc0e57b395926122bd4062c1fcedc48ed465"
```

Implement `librechat_provenance(config)` by parsing `package.json`, then using
argument-vector subprocess calls (never `shell=True`) for:

```text
git -C <librechat_dir> rev-parse HEAD
git -C <librechat_dir> merge-base --is-ancestor <expected-base> HEAD
```

Return:

```python
{
    "version": "v0.8.7",
    "directory": str(config.librechat_dir),
    "community_base_commit": EXPECTED_LIBRECHAT_COMMIT,
    "head_commit": head_commit,
    "community_base_is_ancestor": True,
}
```

Implement `preflight_shell(config)` and call it before starting children. It
must verify Python >= 3.11, Node >= 20.19, npm major version 11, `node`/`npm`
resolved executable paths, the OneCode source package,
LibreChat version/base ancestry, private state directory creation, and all
three configured ports by attempting a local bind. A missing model config is a
bounded warning so the operator can configure it in the Console; report only
`configured`, provider, endpoint, model, and `api_key_configured`, never the
secret or full environment.

- [ ] **Step 5: Add redacted status and bounded process records**

Remove `login.password` from `shell_status`; return only the configured email.
Add state path, configured timeout, provenance, preflight warnings,
`runtime-status.json`, and per-service log paths.

In `shell_state.py`, implement `write_runtime_status(root, *, status,
services, last_failure=None)` using `write_private_text` and mode `0600`.
Allowed status values are `starting`, `running`, `stopping`, `stopped`, and
`failed`; service values are integer PIDs only. Persist `starting` before the
first child, update after each start, write `running` after health checks, and
write `stopped` or a bounded redacted `failed` summary in `finally`.

- [ ] **Step 6: Add bounded child logs**

Create `runtime_state_root / "logs"` with mode `0700`. Add
`append_bounded_log(path, text, max_bytes=2_000_000)` that redacts bearer
tokens, API-key assignments, and password assignments before writing; when a
write exceeds the cap, atomically retain only the newest complete UTF-8 tail.

Change `start_process` to use `stdout=subprocess.PIPE`,
`stderr=subprocess.STDOUT`, `text=True`, and one daemon pump thread per child.
Return a `ManagedProcess(name, process, log_path, pump_thread)` record, retain
all records until shutdown, and join pump threads after termination. On early
exit, raise `RuntimeError` with the service name, exit code, and final 20
already-redacted lines, not the entire file. Update `process_is_running` and
`terminate_processes` tests for the managed record rather than leaking pipe
handles.

- [ ] **Step 7: Generate the OneCode endpoint retry setting**

In the generated custom endpoint config include:

```yaml
      addParams:
        maxRetries: 0
```

The LibreChat adapter test in Task 7 remains authoritative; this YAML field is
also covered by the launcher test.

- [ ] **Step 8: Run GREEN and CLI tests**

```bash
.venv/bin/python -m unittest \
  tests.test_shell_launcher \
  tests.test_shell_state \
  tests.test_cli_local_interface_commands \
  tests.test_venv_entrypoint -v
```

Expected: launcher, CLI, and installed entry-point tests pass.

- [ ] **Step 9: Commit**

```bash
git add src/onecode/shell_launcher.py src/onecode/shell_state.py \
  src/onecode/cli_commands/local_interfaces.py tests/test_shell_launcher.py tests/test_shell_state.py
git commit -m "feat: persist shell runtime state and diagnostics"
```

## Task 7: Port the OneCode Custom Endpoint with Zero Outer Retries

**Files:**
- Create: `packages/api/src/endpoints/custom/onecode.ts`
- Create: `packages/api/src/endpoints/custom/onecode.spec.ts`
- Create: `packages/api/src/endpoints/custom/onecode.integration.spec.ts`
- Modify: `packages/api/src/endpoints/custom/initialize.ts`
- Modify: `packages/api/src/endpoints/custom/initialize.spec.ts`
- Modify: `api/server/services/Endpoints/agents/build.js`
- Create/port: `api/server/services/Endpoints/agents/build.spec.js`

- [ ] **Step 1: Restore only the checkpoint tests into the v0.8.7 worktree**

```bash
cd '/Users/aidi/大字典/one code/.worktrees/librechat-v087'
git restore --source checkpoint/onecode-shell-pre-v087-20260715 -- \
  packages/api/src/endpoints/custom/onecode.spec.ts \
  api/server/services/Endpoints/agents/build.spec.js
```

Extend the OneCode endpoint spec with:

```typescript
it('forces OneCode outer retries to zero', () => {
  expect(buildOneCodeLLMConfig({ model: 'onecode-agent', maxRetries: 6 }, undefined)).toMatchObject({
    model: 'onecode-agent',
    maxRetries: 0,
  });
});
```

Keep the existing `buildOneCodeModelKwargs` tests unchanged. Extend the
`initializeCustom` spec so mocked `getOpenAIConfig` returns `maxRetries: 6`,
then assert both workspace metadata and
`result.llmConfig.maxRetries === 0` for endpoint `OneCode`. Add a non-OneCode
case proving another custom endpoint keeps its supplied retry value.

Create `onecode.integration.spec.ts` to exercise LangChain's actual caller:

```typescript
import http from 'node:http';
import { once } from 'node:events';
import { ChatOpenAI } from '@langchain/openai';
import { buildOneCodeLLMConfig } from './onecode';

it('sends one HTTP request when OneCode returns a retryable 504', async () => {
  let requestCount = 0;
  const server = http.createServer((req, res) => {
    requestCount += 1;
    req.resume();
    res.writeHead(504, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ error: { type: 'model_provider_timeout', message: 'timed out' } }));
  });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const address = server.address();
  if (address == null || typeof address === 'string') {
    throw new Error('test server did not expose a TCP port');
  }
  try {
    const llmConfig = buildOneCodeLLMConfig(
      { apiKey: 'test-key', model: 'onecode-agent', streaming: false, maxRetries: 6 },
      undefined,
    );
    const model = new ChatOpenAI({
      ...(llmConfig as ConstructorParameters<typeof ChatOpenAI>[0]),
      configuration: { baseURL: `http://127.0.0.1:${address.port}/v1` },
    });
    await expect(model.invoke('inspect project')).rejects.toThrow();
    expect(requestCount).toBe(1);
  } finally {
    await new Promise<void>((resolve, reject) => {
      server.close((error) => (error == null ? resolve() : reject(error)));
    });
  }
});
```

- [ ] **Step 2: Run RED**

```bash
cd packages/api
npx jest src/endpoints/custom/onecode.spec.ts \
  src/endpoints/custom/onecode.integration.spec.ts \
  src/endpoints/custom/initialize.spec.ts --runInBand
```

Expected: missing `onecode.ts` and missing OneCode endpoint behavior.

- [ ] **Step 3: Implement one focused adapter**

Create:

```typescript
export type OneCodeMetadata = { workspace?: string };

export function buildOneCodeModelKwargs(
  modelKwargs: Record<string, unknown> | undefined,
  metadata: OneCodeMetadata | undefined,
): Record<string, unknown> | undefined {
  const workspace = typeof metadata?.workspace === 'string' ? metadata.workspace.trim() : '';
  if (!workspace) {
    return modelKwargs;
  }
  const currentMetadata =
    modelKwargs?.metadata != null && typeof modelKwargs.metadata === 'object'
      ? (modelKwargs.metadata as Record<string, unknown>)
      : {};
  return {
    ...(modelKwargs ?? {}),
    metadata: { ...currentMetadata, workspace },
  };
}

export function buildOneCodeLLMConfig(
  llmConfig: Record<string, unknown>,
  metadata: OneCodeMetadata | undefined,
): Record<string, unknown> {
  const modelKwargs =
    llmConfig.modelKwargs != null && typeof llmConfig.modelKwargs === 'object'
      ? (llmConfig.modelKwargs as Record<string, unknown>)
      : undefined;
  const nextModelKwargs = buildOneCodeModelKwargs(modelKwargs, metadata);

  return {
    ...llmConfig,
    maxRetries: 0,
    ...(nextModelKwargs == null ? {} : { modelKwargs: nextModelKwargs }),
  };
}
```

In `initializeCustom`, apply `buildOneCodeLLMConfig` only when
`endpoint === 'OneCode'` after `getOpenAIConfig` returns. Preserve the current
`v0.8.7` native-Anthropic branch, tenant-scoped token cache, SSRF protection,
and header-forwarding guards; do not restore the old checkpoint version of
`initialize.ts` wholesale or affect other custom endpoints.

- [ ] **Step 4: Port request metadata through the v0.8.7 agent build boundary**

Keep the `v0.8.7` `chatProjectId` destructuring and return field intact. Add
`metadata: req.body?.metadata` only to the object returned by
`removeNullishValues`; `loadAgent` already receives `req`, so do not invent a
second unsupported metadata parameter. Update `build.spec.js` to assert both
`chatProjectId` and workspace metadata survive, while an unrelated request
body field is not copied to the endpoint option.

- [ ] **Step 5: Run GREEN and build the package**

```bash
cd packages/api
npx jest src/endpoints/custom/onecode.spec.ts \
  src/endpoints/custom/onecode.integration.spec.ts \
  src/endpoints/custom/initialize.spec.ts --runInBand
npm run build
cd ../../api
npx jest server/services/Endpoints/agents/build.spec.js --runInBand
```

Expected: OneCode retry and metadata tests pass; package build passes.

- [ ] **Step 6: Commit**

```bash
git add packages/api/src/endpoints/custom api/server/services/Endpoints/agents/build.js api/server/services/Endpoints/agents/build.spec.js
git commit -m "feat: port OneCode endpoint to LibreChat v0.8.7"
```

## Task 8: Port OneCode Local Routes and Shared Data Contracts

**Files:**
- Create/port: `api/server/routes/onecode.js`, `api/server/routes/onecode.spec.js`
- Create/port: `api/server/services/OneCode/projectPicker.js`, `projectPicker.spec.js`
- Modify: `api/server/index.js`, `api/server/routes/index.js`
- Modify: `packages/api/src/types/http.ts`
- Modify: `packages/data-provider/src/api-endpoints.ts`, `data-service.ts`, `types.ts`

- [ ] **Step 1: Restore route and service tests first**

```bash
git restore --source checkpoint/onecode-shell-pre-v087-20260715 -- \
  api/server/routes/onecode.spec.js \
  api/server/services/OneCode/projectPicker.spec.js
cd api
npx jest server/routes/onecode.spec.js server/services/OneCode/projectPicker.spec.js --runInBand
```

Expected: missing route/service modules.

- [ ] **Step 2: Restore the isolated route and service implementations**

```bash
cd '/Users/aidi/大字典/one code/.worktrees/librechat-v087'
git restore --source checkpoint/onecode-shell-pre-v087-20260715 -- \
  api/server/routes/onecode.js \
  api/server/services/OneCode/projectPicker.js
```

Adapt only imports and current `v0.8.7` request/user shapes. Preserve local-only
request enforcement, allowed workspace roots, `execFile` argv execution,
masked model config, bounded OneCode API responses, and the existing
`requireJwtAuth` then local-request middleware order. Add route cases for a
missing JWT and a non-loopback request; neither may reach a picker/service
mock.

- [ ] **Step 3: Register the route at the current v0.8.7 boundary**

Export `onecode` from `api/server/routes/index.js` and mount it at
`/api/onecode` in `api/server/index.js` next to other authenticated local API
routes. Do not replace either upstream file with its checkpoint version.

- [ ] **Step 4: Run API GREEN**

```bash
cd api
npx jest server/routes/onecode.spec.js server/services/OneCode/projectPicker.spec.js --runInBand
```

Expected: all local route, path-boundary, model-config, evidence, and MCP sync tests pass.

- [ ] **Step 5: Port shared types through additive sections**

Use the checkpoint diff as the behavior source:

```bash
git diff v0.8.7..checkpoint/onecode-shell-pre-v087-20260715 -- \
  packages/api/src/types/http.ts \
  packages/data-provider/src/api-endpoints.ts \
  packages/data-provider/src/data-service.ts \
  packages/data-provider/src/types.ts
```

Add the OneCode request/response types, endpoint builders, and data-service
methods to the `v0.8.7` files without reverting upstream tenant, skill, or
request changes. Keep every endpoint under `/api/onecode`. Preserve the exact
field names already consumed by `client/src/onecode/project.ts`; validate one
accepted masked-model response and one rejected missing-`workspace` request in
the restored route/data tests instead of weakening types with `any`.

- [ ] **Step 6: Build shared packages and run their focused tests**

```bash
npm run build:data-provider
cd packages/api
npm run build
```

Expected: TypeScript builds without `any`, duplicate exports, or upstream type regressions.

- [ ] **Step 7: Commit**

```bash
git add api/server/index.js api/server/routes api/server/services/OneCode packages/api/src/types/http.ts packages/data-provider/src
git commit -m "feat: port OneCode local shell APIs to v0.8.7"
```

## Task 9: Port the OneCode Console and Project UI

**Files:**
- Create/port: `client/src/onecode/*`
- Create/port: `client/src/components/OneCode/*`
- Create/port: `client/src/components/Chat/Input/OneCodeProjectButton*`
- Modify: `client/src/components/Chat/Input/ChatForm.tsx`
- Modify: `client/src/components/SidePanel/SidePanelGroup.tsx`
- Modify: `client/src/hooks/Chat/useChatFunctions.ts`
- Modify: `client/src/hooks/Nav/useSideNavLinks.ts`
- Modify: `client/src/locales/en/translation.json`, `zh-Hans/translation.json`
- Create/port: `DESIGN.md`

- [ ] **Step 1: Restore UI tests before components**

```bash
git restore --source checkpoint/onecode-shell-pre-v087-20260715 -- \
  client/src/onecode/project.test.ts \
  client/src/components/Chat/Input/OneCodeProjectButton.test.tsx \
  client/src/components/OneCode/OneCodeConsolePanel.test.tsx \
  client/src/components/SidePanel/SidePanelGroup.test.tsx
cd client
npx jest \
  src/onecode/project.test.ts \
  src/components/Chat/Input/OneCodeProjectButton.test.tsx \
  src/components/OneCode/OneCodeConsolePanel.test.tsx \
  src/components/SidePanel/SidePanelGroup.test.tsx --runInBand
```

Expected: missing component/module failures.

- [ ] **Step 2: Restore source-owned OneCode components**

```bash
cd '/Users/aidi/大字典/one code/.worktrees/librechat-v087'
git restore --source checkpoint/onecode-shell-pre-v087-20260715 -- \
  DESIGN.md \
  client/src/onecode/console.ts \
  client/src/onecode/project.ts \
  client/src/components/OneCode \
  client/src/components/Chat/Input/OneCodeProjectButton.tsx
```

Adapt imports to `v0.8.7` only. Preserve the right-side console on desktop and
full-screen overlay on narrow screens.

- [ ] **Step 3: Add narrow integration hooks against v0.8.7**

Apply the checkpoint behavior manually to current files:

- render `OneCodeProjectButton` beside attachment controls in `ChatForm`;
- forward selected workspace metadata only for endpoint `OneCode`;
- let `SidePanelGroup` choose between artifact content and OneCode Console;
- add the model-config navigation command using a Lucide icon and localized label.

Do not restore the checkpoint versions of these upstream-owned files wholesale.
Keep their current tenant, project-chat, and endpoint-type fields. After each
manual edit, inspect `git diff v0.8.7 -- <file>` and reject any unrelated
community-line removal before running tests.

- [ ] **Step 4: Apply the DESIGN.md rules**

Use LibreChat semantic tokens, compact tabs/status rows, existing focus rings,
and monospaced paths/run IDs. Do not add a component framework, nested cards,
gradients, hero content, or marketing copy. Fix shared panel/button behavior
before page-local classes.

- [ ] **Step 5: Run UI GREEN and type checks**

```bash
cd client
npx jest \
  src/onecode/project.test.ts \
  src/components/Chat/Input/OneCodeProjectButton.test.tsx \
  src/components/OneCode/OneCodeConsolePanel.test.tsx \
  src/components/SidePanel/SidePanelGroup.test.tsx --runInBand
npm run typecheck
npm run build
```

Expected: tests, TypeScript, and production client build pass.

- [ ] **Step 6: Run the UI consistency audit**

Check desktop and mobile for:

- visible title/action/content hierarchy;
- token-consistent surfaces and borders;
- compact typography and monospaced technical values;
- hover, focus, selected, disabled, loading, empty, and error states;
- path and run-ID wrapping/truncation;
- usable touch targets and visible keyboard focus;
- state communication that does not depend only on color.
- icon-only controls with accessible names and existing focus-ring behavior;
- semantic LibreChat tokens rather than new raw colors in OneCode components;
- concise raw kernel error details inside bounded, wrapping technical text;
- no repeated visual defect patched in three page-local locations when a
  shared OneCode component can own it.

Run:

```bash
rg -n --glob '*.tsx' --glob '*.css' '#[0-9A-Fa-f]{3,8}|rgb\(|hsl\(' client/src/components/OneCode client/src/components/Chat/Input/OneCodeProjectButton.tsx
```

Expected: no new raw color literal where a LibreChat semantic token exists;
each match is either removed or documented as an existing required upstream
value.

- [ ] **Step 7: Commit**

```bash
git add DESIGN.md client/src
git commit -m "feat: port OneCode Console UI to LibreChat v0.8.7"
```

## Task 10: Restore Branding, Runtime Config, and Upgrade Provenance

**Files:**
- Create/port: `ONECODE_SHELL.md`
- Create/port: `client/src/onecode/brand.ts`, `brand.test.ts`
- Modify: `.env.example`, `librechat.yaml`, `package.json`, `scripts/onecode-smoke.mjs`
- Modify: `client/index.html`, `client/src/components/Auth/AuthLayout.tsx`,
  `client/src/components/Chat/Landing.tsx`, `client/vite.config.ts`

- [ ] **Step 1: Write/port branding contract tests first**

Restore only the existing test first:

```bash
git restore --source checkpoint/onecode-shell-pre-v087-20260715 -- \
  client/src/onecode/brand.test.ts
```

Keep its operational assertions, which verify branding without deleting
required community assets:

```typescript
expect(ONECODE_BRAND.productName).toBe('OneCode');
expect(ONECODE_BRAND.endpointName).toBe('OneCode');
expect(ONECODE_BRAND.defaultModel).toBe('onecode-agent');
```

Run: `cd client && npx jest src/onecode/brand.test.ts --runInBand`

Expected: missing brand module or old product values.

- [ ] **Step 2: Port minimal branding and config**

Restore `ONECODE_SHELL.md`, `scripts/onecode-smoke.mjs`, and
`client/src/onecode/brand.ts` from the checkpoint. Use the checkpoint diff as
reference for tracked config files, but retain `v0.8.7` security and build
configuration. Add only `"onecode:smoke": "node scripts/onecode-smoke.mjs"`
to the root `package.json`; do not restore the old manifest wholesale. Set the
OneCode endpoint to port `19080`, keep `models.fetch` false, include
`addParams.maxRetries: 0`, and preserve the generated-runtime config contract
from OneCode.

Do not delete community assets solely to remove branding. Use OneCode-provided
tested replacements or neutral configuration where required.

- [ ] **Step 3: Update provenance documentation**

Create `ONECODE_SHELL.md` with:

```text
Community baseline: LibreChat v0.8.7
Community commit: 9e74cc0e5
OneCode upgrade branch: feature/onecode-shell-v087-hardening
OneCode remains the execution and approval authority.
```

Document state directory, ports, timeout behavior, zero outer retries, and
rollback branch without local credentials or absolute operator secrets.

- [ ] **Step 4: Run smoke/build checks**

```bash
npm run build:client
npm pkg get scripts.onecode:smoke
node --check scripts/onecode-smoke.mjs
git diff --check
```

Expected: build passes, the smoke command is registered, and its JavaScript
parses without requiring a live API. The live smoke runs only after Task 12
starts the isolated shell.

- [ ] **Step 5: Commit**

```bash
git add .env.example DESIGN.md ONECODE_SHELL.md librechat.yaml package.json \
  scripts/onecode-smoke.mjs client
git commit -m "docs: record LibreChat v0.8.7 OneCode shell baseline"
```

## Task 11: Add the Cross-Component Timeout Regression

**Files:**
- Create: `tests/test_shell_timeout_integration.py`
- Create: `tests/fixtures/delayed_model_server.py`

- [ ] **Step 1: Write the failing OneCode HTTP timeout integration test**

Create a local stub model server that counts POST requests and sleeps beyond a
`0.1` second OneCode timeout. Start `ThreadingHTTPServer(("127.0.0.1", 0),
OneCodeRequestHandler)` in a test thread with a temporary workspace and these
scoped environment values: `ONECODE_MODEL_PROVIDER=chat`,
`ONECODE_MODEL_ENDPOINT=<stub>/v1/chat/completions`,
`OPENAI_API_KEY=test-key`, `ONECODE_MODEL_TIMEOUT_SECONDS=0.1`, and
`ONECODE_ALLOW_UNAUTHENTICATED=true`. POST one non-streaming request to
`/v1/chat/completions`, then shut down and join both servers in `finally`.
Assert:

```python
self.assertEqual(response.status, 504)
self.assertEqual(payload["error"]["type"], "model_provider_timeout")
self.assertEqual(stub.request_count, 1)
self.assertEqual(model_event_types, ["model_call_started", "model_call_failed"])
self.assertTrue(Path(result["ledger_path"]).is_file())
self.assertTrue(Path(result["manifest_path"]).is_file())
```

- [ ] **Step 2: Run RED**

Run: `.venv/bin/python -m unittest tests.test_shell_timeout_integration -v`

Expected: the integration helper or final evidence contract fails until Tasks 2-6 are complete.

- [ ] **Step 3: Use the existing public HTTP integration boundaries**

Use the public environment timeout boundary added in Task 4 and the existing
`OneCodeRequestHandler`; do not add a second production-only timeout seam. If
the HTTP payload lacks a run ID or evidence references, correct the structured
Web mapping from Task 4 rather than parsing terminal text.

- [ ] **Step 4: Make the delayed model fixture reusable by browser verification**

Create a stdlib-only fixture with `/v1/models` and `/v1/chat/completions`.
`/v1/models` returns `stub-model`; chat increments a thread-safe request count,
sleeps for `--delay-seconds`, then returns a valid JSON completion if the
client has not timed out. Bind to `127.0.0.1`, require an explicit `--port`,
print only the ready URL, and stop cleanly on Ctrl+C. The integration test
imports the same handler/counter, while Task 12 runs the CLI fixture on port
`16780`; no credential or operator state enters the fixture.

- [ ] **Step 5: Run GREEN**

```bash
cd '/Users/aidi/大字典/one code/.worktrees/onecode-shell-v087-hardening/one code'
.venv/bin/python -m unittest tests.test_shell_timeout_integration -v
.venv/bin/python -m py_compile tests/fixtures/delayed_model_server.py
```

Expected: one request, bounded 504, one failed model event, complete evidence,
and a valid reusable fixture.

- [ ] **Step 6: Commit the cross-component OneCode regression**

OneCode:

```bash
git add tests/test_shell_timeout_integration.py tests/fixtures/delayed_model_server.py
git commit -m "test: cover shell model timeout end to end"
```

## Task 12: Full Verification, Browser Audit, and Closure Records

**Files:**
- Modify: `README.md`, `CHANGELOG.md`
- Modify: `docs/ONECODE_SAFE_AGENT_SHELL_INTEGRATION_ISSUE_2026-07-13.md`
- Create: `docs/ONECODE_LIBRECHAT_V087_HARDENING_CLOSURE_2026-07-15.md`
- Modify: LibreChat `ONECODE_SHELL.md`

- [ ] **Step 1: Run the OneCode focused suite**

```bash
cd '/Users/aidi/大字典/one code/.worktrees/onecode-shell-v087-hardening/one code'
PYTHONPATH=src .venv/bin/python -m unittest \
  tests.test_model_provider_contract \
  tests.test_model_loop \
  tests.test_web_api \
  tests.test_shell_state \
  tests.test_shell_launcher \
  tests.test_cli_local_interface_commands \
  tests.test_shell_timeout_integration -v
```

Expected: zero failures and zero errors.

- [ ] **Step 2: Run full OneCode verification**

```bash
PYTHONPATH=src bash scripts/verify.sh
git diff --check
```

Expected: complete suite, source-quality gates, and doctor pass.

- [ ] **Step 3: Run LibreChat focused and build verification**

```bash
cd '/Users/aidi/大字典/one code/.worktrees/librechat-v087'
cd packages/api && npx jest src/endpoints/custom/onecode.spec.ts src/endpoints/custom/onecode.integration.spec.ts src/endpoints/custom/initialize.spec.ts --runInBand
cd ../../api && npx jest server/routes/onecode.spec.js server/services/OneCode/projectPicker.spec.js server/services/Endpoints/agents/build.spec.js --runInBand
cd ../client && npx jest src/onecode/project.test.ts src/onecode/brand.test.ts src/components/OneCode/OneCodeConsolePanel.test.tsx src/components/Chat/Input/OneCodeProjectButton.test.tsx src/components/SidePanel/SidePanelGroup.test.tsx --runInBand
cd .. && npm run build:data-provider && npm run build:api && npm run build:client
git diff --check
```

Expected: all focused tests and builds pass.

- [ ] **Step 4: Start the local shell from isolated worktrees**

Run in a dedicated foreground terminal and retain the printed `STATE_DIR` for
the restart check:

```bash
cd '/Users/aidi/大字典/one code/.worktrees/onecode-shell-v087-hardening/one code'
STATE_DIR="$(mktemp -d /private/tmp/onecode-shell-v087-verification.XXXXXX)"
printf 'STATE_DIR=%s\n' "$STATE_DIR"
PYTHONPATH=src .venv/bin/python -m onecode shell \
  --librechat-dir '/Users/aidi/大字典/one code/.worktrees/librechat-v087' \
  --state-dir "$STATE_DIR" \
  --model-timeout-seconds 60 \
  --workspace '/Users/aidi/大字典/one code/.worktrees/onecode-shell-v087-hardening/one code' \
  --no-browser
```

Expected: Mongo, OneCode API, and LibreChat become healthy on ports
`39017`, `19080`, and `14080`.

- [ ] **Step 5: Run Playwright desktop and mobile smoke checks**

Use the bundled Playwright skill/wrapper against `http://127.0.0.1:14080`.
Verify login, project selection, Console tabs, a read-only task, approval-required
write behavior, keyboard focus, and responsive layout at desktop and mobile
viewports. Run `npm run onecode:smoke` against the live isolated OneCode API.
Capture screenshots under the temporary `STATE_DIR`, outside source
directories.

Expected: no overlapping text or controls; OneCode Console uses existing
LibreChat tokens; all target workflows reach the expected visible state.

- [ ] **Step 6: Verify restart persistence**

Start the reusable model fixture in a second terminal:

```bash
cd '/Users/aidi/大字典/one code/.worktrees/onecode-shell-v087-hardening/one code'
.venv/bin/python tests/fixtures/delayed_model_server.py --port 16780 --delay-seconds 2
```

Record the current run-directory set, run
`shasum -a 256 "$STATE_DIR/auth-secrets.json"`, and record the Mongo directory
listing. Do not change the operator's stored model configuration.

Stop the shell with Ctrl+C, confirm `runtime-status.json.status == "stopped"`,
then rerun the Step 4 launch command in the same terminal with the same
`STATE_DIR`, `--model-timeout-seconds 0.5`, and these process-scoped overrides:

```bash
ONECODE_MODEL_PROVIDER=chat \
ONECODE_MODEL_ENDPOINT=http://127.0.0.1:16780/v1/chat/completions \
ONECODE_MODEL=stub-model \
OPENAI_API_KEY=test-key \
PYTHONPATH=src .venv/bin/python -m onecode shell \
  --librechat-dir '/Users/aidi/大字典/one code/.worktrees/librechat-v087' \
  --state-dir "$STATE_DIR" \
  --model-timeout-seconds 0.5 \
  --workspace '/Users/aidi/大字典/one code/.worktrees/onecode-shell-v087-hardening/one code' \
  --no-browser
```

The overrides exist only for this child process and must not be written to
the operator's model config. Confirm the secret-file digest
is unchanged, the Mongo directory is reused, the local account remains, and
the prior session refresh succeeds without `invalid signature` log entries.
Submit one uniquely worded timeout task in the browser and prove: visible 504
timeout state, exactly one new run containing its digest, one failed terminal
model event, and readable ledger/manifest in the Console. Stop the delayed
fixture with Ctrl+C after this check. Do not print or copy secret-file contents.

- [ ] **Step 7: Write closure documentation**

Record exact commits, tag provenance, test counts, build results, screenshots,
timeout request count, restart evidence, remaining optional-service warnings,
and rollback commands. Reconcile every row in
`/private/tmp/onecode-v087-migration-inventory.txt` as `ported`,
`superseded-by-v0.8.7`, or `approved-removal`, with its test or decision record.
Update prior issue status without deleting historical evidence.

- [ ] **Step 8: Run final secret and diff audits**

In both worktrees:

```bash
git status --short
git diff --check
git diff --cached --check
if git grep -n -P 'sk-(?!test(?:[-_]|$))[A-Za-z0-9_-]{12,}|BEGIN (RSA |OPENSSH )?PRIVATE KEY'; then
  exit 1
fi
git grep -n -E 'sk-|api[_-]?key' -- . || true
```

Expected: only intended source/docs changes; no credentials, runtime state,
logs, screenshots, or dependencies tracked. Review every line from the broad
second scan; only explicit environment placeholders, masked values, and
test-only fixtures may remain.

- [ ] **Step 9: Commit closure records**

OneCode:

```bash
git add README.md CHANGELOG.md docs/ONECODE_SAFE_AGENT_SHELL_INTEGRATION_ISSUE_2026-07-13.md docs/ONECODE_LIBRECHAT_V087_HARDENING_CLOSURE_2026-07-15.md
git commit -m "docs: close LibreChat v0.8.7 shell hardening"
```

LibreChat:

```bash
git add ONECODE_SHELL.md
git commit -m "docs: record OneCode v0.8.7 verification"
```

- [ ] **Step 10: Stop before cutover or publication**

Report both branch heads, full verification evidence, rollback branches, and
remaining risks. Do not merge, push, tag, delete worktrees, or replace the
operator's current shell without a separate explicit decision.

## Acceptance Coverage Matrix

1. Exact `v0.8.7` provenance: Tasks 1, 6, 10, and 12.
2. No silently dropped customization: migration inventory in Tasks 1 and 12,
   plus focused ports in Tasks 7-10.
3. One upstream request instead of seven: LangChain HTTP integration in Task 7
   and UI run-directory count in Task 12.
4. Visible bounded 504: Tasks 4 and 11, then browser confirmation in Task 12.
5. Exactly one terminal event per model call: Task 3 covers initial, invalid,
   and repair calls; Task 11 covers the HTTP path.
6. Redacted trace, ledger, and manifest: Tasks 3, 4, 11, and final secret audit.
7. Secrets and session data survive restart: Tasks 5, 6, and Task 12 restart.
8. Read automation and guarded approval remain intact: ported tests in Tasks 8
   and 9, browser workflows in Task 12.
9. Safe-Agent no-match/unavailable semantics: Task 3 preserves route context;
   the OneCode focused/full suites in Task 12 retain existing router tests.
10. All tests, builds, shell health, and browser smoke: Task 12 Steps 1-6.
11. Original checkpoint and user worktree intact: Task 1 and the no-cutover gate
    in Task 12.
12. No runtime artifacts or secrets committed: Tasks 1, 5, 6, 10, and Task 12
    final tracked-file/secret audits.
