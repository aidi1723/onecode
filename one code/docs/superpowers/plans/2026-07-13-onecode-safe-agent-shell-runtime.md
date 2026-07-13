# OneCode Safe-Agent Shell Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route shell tasks through the latest verified Safe-Agent Router, execute bounded reads, require approval for side effects, and reject empty plans.

**Architecture:** Add focused kernel adapters for routing, classification, effective model configuration, tools, and approval persistence. Keep Web API code as orchestration glue and preserve PathGuard, runner, evidence, and shell-projection boundaries.

**Tech Stack:** Python 3.11, stdlib subprocess/JSON/HTTP server, unittest, existing OneCode kernel and LibreChat launcher.

---

## File Map

- Create `kernel/safe_agent_router.py`, `task_classification.py`, `effective_model_config.py`, and `approval_plans.py`.
- Extend `execution_tools.py`, `execution_engine.py`, `model_provider.py`, and `model_loop.py`.
- Update `web/api.py` and `shell_launcher.py` without moving existing public entry points.
- Add one focused test module per new boundary and extend current integration tests.

### Task 1: Latest Safe-Agent Router Adapter

**Files:**
- Create: `src/onecode/kernel/safe_agent_router.py`
- Create: `tests/test_safe_agent_router.py`

- [ ] **Step 1: Write failing adapter tests**

```python
class SafeAgentRouterTests(unittest.TestCase):
    def test_routes_schema_v2_trusted_task_pack(self):
        completed = subprocess.CompletedProcess([], 0, json.dumps(valid_task_pack()), "")
        route = route_safe_agent_task("检查项目", runner=lambda *a, **k: completed)
        self.assertEqual(route.status, "ok")
        self.assertEqual(route.schema_version, 2)
        self.assertEqual(route.selected_skills, ("code-test-regression",))
        self.assertNotIn("safe_workflow", route.to_planning_context())

    def test_rejects_tampered_registry(self):
        pack = valid_task_pack()
        pack["registry_verification"]["tampered_count"] = 1
        route = route_safe_agent_task("检查项目", runner=completed_runner(pack))
        self.assertEqual((route.status, route.reason), ("invalid", "registry_verification_failed"))

    def test_missing_router_is_explicit(self):
        route = route_safe_agent_task("检查项目", runner=missing_runner)
        self.assertEqual((route.status, route.reason), ("unavailable", "router_command_not_found"))
```

- [ ] **Step 2: Run RED**

Run: `.venv/bin/python -m unittest tests.test_safe_agent_router -v`

Expected: import failure for `onecode.kernel.safe_agent_router`.

- [ ] **Step 3: Implement the adapter**

Create `SafeAgentRoute` with status, reason, schema version, route ID, selected scenarios, trusted skill names, execution order, verifier expectations, and registry summary. `route_safe_agent_task()` runs `safe-agent-router-task-pack TASK --format json` with a timeout and output limit. Validation requires Schema v2, complete routing, clean registry verification, zero tampering, and trusted selected skills. Planning context uses an explicit field allowlist and `method_only` safety boundary.

- [ ] **Step 4: Run GREEN**

Run: `.venv/bin/python -m unittest tests.test_safe_agent_router -v`

Expected: all adapter tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/onecode/kernel/safe_agent_router.py tests/test_safe_agent_router.py
git commit -m "feat: add verified safe-agent router adapter"
```

### Task 2: Task Classification and Effective Model Configuration

**Files:**
- Create: `src/onecode/kernel/task_classification.py`
- Create: `src/onecode/kernel/effective_model_config.py`
- Create: `tests/test_task_classification.py`
- Create: `tests/test_effective_model_config.py`
- Modify: `src/onecode/web/api.py`

- [ ] **Step 1: Write failing classification tests**

```python
def test_natural_project_check_is_read_task():
    assert classify_task("检查当前项目是否集成了 safe-agent-skills") == "read_task"

def test_question_requesting_inspection_is_read_task():
    assert classify_task("你能检查一下 src/onecode 吗？") == "read_task"

def test_mutation_and_install_are_change_tasks():
    assert classify_task("修改 README.md") == "change_task"
    assert classify_task("安装项目依赖") == "change_task"

def test_explanatory_question_is_chat():
    assert classify_task("什么是 Safe-Agent-Skills？") == "chat"
```

- [ ] **Step 2: Write failing effective-config test**

```python
def test_environment_precedence_is_public_and_redacted():
    result = resolve_effective_model_config(
        {"ONECODE_MODEL_PROVIDER": "chat", "ONECODE_MODEL": "m1", "OPENAI_API_KEY": "secret"},
        {"provider": "openai-compatible", "endpoint": "http://stored/v1", "model": "stored"},
    )
    assert result.public["provider_source"] == "environment"
    assert result.public["endpoint_source"] == "stored"
    assert result.public["api_key_configured"] is True
    assert "secret" not in repr(result.public)
```

- [ ] **Step 3: Run RED**

Run: `.venv/bin/python -m unittest tests.test_task_classification tests.test_effective_model_config -v`

Expected: both modules are missing.

- [ ] **Step 4: Implement three-way classification**

Expose `classify_task(text, explicit_mode=None) -> Literal["chat", "read_task", "change_task"]`. Change signals take precedence over read signals; explicit validated modes take precedence over inference. Question punctuation alone cannot demote an imperative request.

- [ ] **Step 5: Implement effective configuration**

Expose an immutable result containing provider, endpoint, model, API key, and a redacted `public` mapping. Resolve environment, then stored values, then defaults. Record a source label for each public value and never include secret text in public output.

- [ ] **Step 6: Wire Web routing and diagnostics**

Validate optional `metadata.onecode_mode`, use direct chat only for `chat`, pass the task mode to model planning, and expose the redacted effective config in project status.

- [ ] **Step 7: Run GREEN and commit**

Run: `.venv/bin/python -m unittest tests.test_task_classification tests.test_effective_model_config tests.test_web_api -v`

```bash
git add src/onecode/kernel/task_classification.py src/onecode/kernel/effective_model_config.py src/onecode/web/api.py tests/test_task_classification.py tests/test_effective_model_config.py tests/test_web_api.py
git commit -m "fix: classify shell tasks and expose effective model config"
```

### Task 3: Workspace-Bounded Tools and Approval Decisions

**Files:**
- Modify: `src/onecode/kernel/execution_tools.py`
- Modify: `src/onecode/kernel/execution_engine.py`
- Create: `tests/test_execution_tools.py`
- Modify: `tests/test_execution_engine.py`

- [ ] **Step 1: Write failing tool tests**

```python
def test_default_registry_exposes_read_and_guarded_tools():
    registry = default_tool_registry()
    assert registry.names() == ["git_status", "list_files", "patch_text", "read_text", "run_command", "search_text", "write_text"]
    assert registry.get("read_text").requires_approval is False
    assert registry.get("run_command").requires_approval is True

def test_read_text_rejects_workspace_escape(tmp_path):
    with pytest.raises(PathGuardError):
        ReadTextTool().execute({"path": "../secret"}, workspace=tmp_path)

def test_run_command_requires_argv(tmp_path):
    with pytest.raises(ValueError, match="argv"):
        RunCommandTool().plan_action({"command": "pwd && rm file"})
```

- [ ] **Step 2: Write failing approval test**

```python
def test_guarded_step_requires_approval_without_execution(tmp_path):
    trace = execute_plan(guarded_write_plan(), workspace=tmp_path)
    assert (trace.success, trace.reason) == (False, "approval_required")
    assert not (tmp_path / "out.txt").exists()
```

- [ ] **Step 3: Run RED**

Run: `.venv/bin/python -m unittest tests.test_execution_tools tests.test_execution_engine -v`

Expected: new tools are absent and the guarded write currently executes.

- [ ] **Step 4: Implement tools**

Add `list_files`, `read_text`, `search_text`, and `git_status` with path resolution, symlink escape protection, byte/line/match limits, and JSON-safe output. Add `run_command` using only a bounded `argv: list[str]`, `shell=False`, selected-workspace cwd, timeout, and bounded stdout/stderr. Keep write/patch routed through `run_task`.

- [ ] **Step 5: Enforce approval**

When a guarded tool has no approval callback, return `approval_required` without execution. Execute only when a callback exists and returns true. Rejection returns `approval_rejected`.

- [ ] **Step 6: Run GREEN and commit**

Run: `.venv/bin/python -m unittest tests.test_execution_tools tests.test_execution_engine -v`

```bash
git add src/onecode/kernel/execution_tools.py src/onecode/kernel/execution_engine.py tests/test_execution_tools.py tests/test_execution_engine.py
git commit -m "feat: add guarded shell inspection tools"
```

### Task 4: Canonical Planning Contract and No-Action Result

**Files:**
- Modify: `src/onecode/kernel/model_provider.py`
- Modify: `src/onecode/kernel/model_loop.py`
- Create: `tests/test_model_provider_contract.py`
- Modify: `tests/test_model_loop.py`

- [ ] **Step 1: Write failing contract tests**

```python
def test_both_providers_receive_the_same_tools_and_safe_agent_context():
    context = planning_context(task_mode="read_task", safe_agent={"schema_version": 2})
    responses = OpenAIResponsesProvider("key").request_payload("check", model="m", planning_context=context)
    chat = OpenAIChatCompletionsProvider("key").request_payload("check", model="m", planning_context=context)
    assert contract_from(responses) == contract_from(chat)
    assert "read_text" in json.dumps(responses)
    assert "safe_agent" in json.dumps(chat)

def test_model_plan_accepts_explicit_no_action():
    plan = validate_model_plan({"task": "explain", "no_action": {"reason": "no workspace action"}})
    assert plan.no_action_reason == "no workspace action"
```

- [ ] **Step 2: Write failing model-loop router test**

```python
def test_model_task_passes_verified_route_to_provider(tmp_path):
    provider = CapturingProvider(read_plan())
    route = SafeAgentRoute(status="ok", reason=None, schema_version=2, selected_skills=("code-test-regression",))
    run_model_task("check", tmp_path, api_key="key", provider=provider, safe_agent_route=route, task_mode="read_task")
    assert provider.planning_context["safe_agent"]["schema_version"] == 2
```

- [ ] **Step 3: Run RED**

Run: `.venv/bin/python -m unittest tests.test_model_provider_contract tests.test_model_loop -v`

Expected: missing planning-context parameters and no-action field.

- [ ] **Step 4: Implement canonical contract**

Extend `ModelPlan` and `MODEL_PLAN_SCHEMA` with `no_action.reason`. Require exactly one of actionable assets/patches/execution steps or no-action. Generate one canonical system contract containing task mode, exact tool parameter schemas, approval policy, and allowlisted Safe-Agent planning context; use it for both providers.

- [ ] **Step 5: Integrate router and no-action result**

`run_model_task` accepts task mode and an optional injected route. It calls the latest router by default. Invalid integrity output halts before model planning; unavailable/no-scenario routes remain explicit but may continue. No-action returns `halted/no_actionable_plan` and never calls lightweight `noop` execution.

- [ ] **Step 6: Run GREEN and commit**

Run: `.venv/bin/python -m unittest tests.test_model_provider_contract tests.test_model_loop tests.test_model_config -v`

```bash
git add src/onecode/kernel/model_provider.py src/onecode/kernel/model_loop.py tests/test_model_provider_contract.py tests/test_model_loop.py tests/test_model_config.py
git commit -m "feat: route model plans through safe-agent context"
```

### Task 5: Persisted Guarded Plans and Web Approval

**Files:**
- Create: `src/onecode/kernel/approval_plans.py`
- Create: `tests/test_approval_plans.py`
- Modify: `src/onecode/web/api.py`
- Modify: `tests/test_web_api.py`

- [ ] **Step 1: Write failing plan-store tests**

```python
def test_plan_round_trip_checks_digest_and_workspace(tmp_path):
    stored = persist_approval_plan(tmp_path, guarded_plan(), model_metadata={"model": "m"})
    loaded = load_approval_plan(tmp_path, stored.plan_id)
    assert loaded.plan_sha256 == stored.plan_sha256
    assert loaded.workspace == str(tmp_path.resolve())

def test_tampered_plan_is_rejected(tmp_path):
    stored = persist_approval_plan(tmp_path, guarded_plan(), model_metadata={})
    stored.path.write_text(stored.path.read_text().replace("README.md", "outside.txt"))
    with pytest.raises(ValueError, match="approval_plan_mismatch"):
        load_approval_plan(tmp_path, stored.plan_id)
```

- [ ] **Step 2: Write failing Web tests**

```python
def test_change_task_returns_approval_required_without_mutation(self):
    payload, status = handle_chat_completion(change_task_body())
    self.assertEqual(status, 200)
    self.assertEqual(payload["onecode"]["result"]["reason"], "approval_required")
    self.assertFalse((workspace / "README.md").exists())

def test_approved_endpoint_executes_revalidated_plan(self):
    payload, status = handle_onecode_plan_approval({"workspace": str(workspace), "plan_id": plan_id, "approved": True})
    self.assertEqual((status, payload["status"]), (200, "completed"))
```

- [ ] **Step 3: Run RED**

Run: `.venv/bin/python -m unittest tests.test_approval_plans tests.test_web_api -v`

Expected: approval store and handler are missing.

- [ ] **Step 4: Implement atomic plan store**

Store canonical allowlisted JSON under `.onecode/pending-plans/<plan-id>.json` with SHA256 and atomic replace. Validate plan ID, workspace, digest, age, tools, and parameters on load. Exclude credentials and raw skill bodies.

- [ ] **Step 5: Implement Web approval flow**

Persist guarded plans and return `approval_required` with a bounded summary. Add authenticated `POST /v1/onecode/plans/<plan-id>/approval` accepting `approved: bool`. Revalidate approved plans before execution; record rejection without executing. Remove the empty-plan `chat_fallback` that creates a successful `noop`.

- [ ] **Step 6: Run GREEN and commit**

Run: `.venv/bin/python -m unittest tests.test_approval_plans tests.test_web_api -v`

```bash
git add src/onecode/kernel/approval_plans.py src/onecode/web/api.py tests/test_approval_plans.py tests/test_web_api.py
git commit -m "feat: require approval for guarded shell plans"
```

### Task 6: Shell Workspace and Runtime-State Separation

**Files:**
- Modify: `src/onecode/shell_launcher.py`
- Modify: `tests/test_shell_launcher.py`
- Modify: `tests/test_cli_local_interface_commands.py`

- [ ] **Step 1: Write failing launcher tests**

```python
def test_shell_defaults_workspace_to_onecode_root():
    config = config_from_args(namespace(onecode_root="/project", workspace=None))
    assert config.workspace_root == Path("/project").resolve()
    assert config.runtime_state_root != config.workspace_root

def test_runtime_config_is_outside_workspace(tmp_path):
    config = shell_config(workspace_root=tmp_path / "project", runtime_state_root=tmp_path / "state")
    assert build_runtime_config(config).parent == tmp_path / "state"
```

- [ ] **Step 2: Run RED**

Run: `.venv/bin/python -m unittest tests.test_shell_launcher tests.test_cli_local_interface_commands -v`

Expected: current workspace default is temporary and no state-root field exists.

- [ ] **Step 3: Implement separate roots**

Add `runtime_state_root` to `ShellLaunchConfig`. Default workspace to `onecode_root`; default state root to `tempfile.gettempdir()/onecode-librechat-live`. Write LibreChat YAML under state root while keeping OneCode workspace and allowed roots on the selected project.

- [ ] **Step 4: Run GREEN and commit**

Run: `.venv/bin/python -m unittest tests.test_shell_launcher tests.test_cli_local_interface_commands -v`

```bash
git add src/onecode/shell_launcher.py tests/test_shell_launcher.py tests/test_cli_local_interface_commands.py
git commit -m "fix: bind shell tasks to selected project workspace"
```

### Task 7: Documentation and End-to-End Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/ONECODE_SAFE_AGENT_SHELL_INTEGRATION_ISSUE_2026-07-13.md`
- Modify: `docs/superpowers/plans/2026-07-13-onecode-safe-agent-shell-runtime.md`

- [ ] **Step 1: Run focused regression suite**

Run all new test modules plus `test_execution_engine`, `test_model_loop`, `test_shell_launcher`, `test_cli_local_interface_commands`, and `test_web_api` with unittest verbose mode.

Expected: all non-socket tests pass; socket tests skip only when sandbox binding is unavailable.

- [ ] **Step 2: Run project verification**

Run: `bash scripts/verify.sh`

Expected: exit code 0 and all required gates pass.

- [ ] **Step 3: Update README and issue status**

Document dynamic latest-router use, selected workspace, automatic reads, approval flow, no-action behavior, and redacted configuration. Mark the issue `Resolved` with exact verification results.

- [ ] **Step 4: Restart live shell**

Run `.venv/bin/python -m onecode shell --workspace "/Users/aidi/大字典/one code" --show-credentials --no-browser` after stopping the old foreground launcher.

Expected: MongoDB, OneCode API, and LibreChat pass readiness checks on ports 39017, 19080, and 14080.

- [ ] **Step 5: Run live read and guarded smoke checks**

Submit `检查当前项目状态`; verify a read execution trace and Safe-Agent Schema v2 summary. Submit `修改 README.md`; verify `approval_required` and unchanged README, then reject the plan. Verify an injected no-action response returns `halted/no_actionable_plan` without a successful noop WAL entry.

- [ ] **Step 6: Review and commit documentation**

Run `git diff --check` and `git status --short`, stage only README, issue record, and this plan, then commit with `docs: close safe-agent shell integration issue`.

