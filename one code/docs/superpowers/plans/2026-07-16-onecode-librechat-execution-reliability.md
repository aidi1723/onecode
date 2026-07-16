# OneCode LibreChat Execution Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make OneCode task routing, workspace selection, approval, resume, Console state, and error handling reliable across the OneCode and LibreChat repositories.

**Architecture:** Keep deterministic classification and the existing guarded execution engine, but enforce workspace and approval policy before planning or execution. Add a bounded pending-plan API and shell projection v5, then consume those contracts through LibreChat's existing data-provider, local API proxy, React Console, and input-bar project control. Ship the two repositories together only after contract, build, browser, and live-shell gates pass.

**Tech Stack:** Python 3.11+ and `unittest` in OneCode; TypeScript, React, Jest, Testing Library, Express, and Playwright in LibreChat; existing LibreChat tokens and components; no new runtime dependencies.

---

## Repository Map

- OneCode code root: `one code/` (package root inside the monorepo)
- OneCode Git root: monorepo parent that contains `one code/`
- LibreChat Git root: separate local shell repository (not published by this plan)
- Approved design: `one code/docs/superpowers/specs/2026-07-16-onecode-librechat-execution-reliability-design.md`

Run OneCode Python commands from `one code/`. Run LibreChat commands from the
LibreChat checkout named in each task. Commit OneCode paths only in the
OneCode monorepo and LibreChat paths only in the LibreChat repository. Do not
combine paths from both repositories in one Git commit.

## File Structure

### OneCode

- `src/onecode/kernel/task_classification.py`: deterministic mode and reason classification.
- `src/onecode/web/workspace.py`: explicit-workspace policy and allowed-root validation.
- `src/onecode/kernel/approval_summary.py`: redacted action and pending-plan summaries.
- `src/onecode/kernel/approval_plans.py`: pending-plan persistence, validation, listing, claim, and archive lifecycle.
- `src/onecode/web/api.py`: OpenAI-compatible routing and OneCode plan endpoints.
- `src/onecode/kernel/shell_projection.py`: shell projection v5 and approval state.
- `src/onecode/contracts/shell_projection_v5_schema.json`: public v5 schema.
- `src/onecode/contracts/shell_projection_v5_cases.json`: exact v5 behavior fixtures.
- `src/onecode/shell_launcher.py`: strict shell environment, title configuration, and preflight diagnostics.

### LibreChat

- `packages/api/src/endpoints/custom/onecode.ts`: OneCode metadata forwarding and retry policy.
- `packages/data-provider/src/types.ts`: shared OneCode response contracts.
- `packages/data-provider/src/api-endpoints.ts`: browser-to-LibreChat OneCode URLs.
- `packages/data-provider/src/data-service.ts`: typed plan and approval calls.
- `api/server/services/OneCode/projectPicker.js`: local authenticated proxy to OneCode.
- `api/server/routes/onecode.js`: browser-facing plan routes.
- `client/src/onecode/project.ts`: workspace, mode, plan, and error helpers.
- `client/src/components/Chat/Input/OneCodeModeControl.tsx`: compact mode segmented control.
- `client/src/components/OneCode/ApprovalTab.tsx`: pending-plan decision UI.
- `client/src/components/OneCode/OneCodeConsolePanel.tsx`: Console orchestration.
- `client/src/components/OneCode/ProjectTab.tsx`: Git and skill-state semantics.
- `e2e/specs/onecode-console.spec.ts`: desktop/mobile approval workflow checks.

### Task 1: Add Deterministic Classification Reasons And Phrase Coverage

**Repository:** OneCode

**Files:**
- Modify: `src/onecode/kernel/task_classification.py`
- Modify: `tests/test_task_classification.py`

- [ ] **Step 1: Write failing positive and negative classification tests**

Add table-driven tests that preserve both the mode and a stable reason:

```python
def test_common_project_requests_are_classified_with_reasons(self):
    from onecode.kernel.task_classification import classify_task_with_reason

    cases = {
        "写一个 hello.txt": ("change_task", "mutation_action_with_path"),
        "写文件 hello.txt 内容是 hi": ("change_task", "mutation_action_with_path"),
        "在项目根目录写个文件": ("change_task", "mutation_action_with_project_object"),
        "fix bug in main.py": ("change_task", "mutation_action_with_path"),
        "把这个 bug 修一下": ("change_task", "mutation_action_with_project_object"),
        "运行一下测试": ("change_task", "mutation_action_with_project_object"),
        "帮我看看这个仓库": ("read_task", "read_action_with_project_object"),
        "看看 src": ("read_task", "read_action_with_project_object"),
        "分析一下代码": ("read_task", "read_action_with_project_object"),
    }
    for text, expected in cases.items():
        with self.subTest(text=text):
            result = classify_task_with_reason(text)
            self.assertEqual((result.mode, result.reason), expected)


def test_ambiguous_explanations_remain_chat(self):
    from onecode.kernel.task_classification import classify_task_with_reason

    for text in ("什么是文件系统", "解释一下 fix 这个词", "Write a brief explanation of tests"):
        with self.subTest(text=text):
            result = classify_task_with_reason(text)
            self.assertEqual((result.mode, result.reason), ("chat", "default_chat"))
```

- [ ] **Step 2: Run the targeted tests and confirm the old behavior fails**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_task_classification -v
```

Expected: FAIL because `classify_task_with_reason` does not exist and the known phrases still fall through to chat.

- [ ] **Step 3: Implement a typed detailed classifier and keep the existing wrapper**

Use a frozen record and action-object composition instead of adding generic nouns to global substring lists:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class TaskClassification:
    mode: TaskMode
    reason: str


MUTATION_ACTIONS = (
    "修改", "创建", "写入", "写一个", "写个", "写文件", "修复", "修一下",
    "运行一下", "跑一下", "fix ", "create ", "write ", "edit ", "run tests", "run command",
)
READ_ACTIONS = ("检查", "查看", "看看", "审查", "分析", "诊断", "inspect", "review", "check", "read")
PROJECT_OBJECTS = (
    "项目", "仓库", "代码", "测试", "命令", "文件", "bug", "src", "repo", "project", "code", "test",
)


def classify_task_with_reason(text: str, *, explicit_mode: str | None = None) -> TaskClassification:
    if explicit_mode is not None:
        if explicit_mode not in VALID_TASK_MODES:
            raise ValueError("metadata.onecode_mode must be chat, read_task, or change_task")
        return TaskClassification(cast(TaskMode, explicit_mode), "explicit_mode")
    if not isinstance(text, str) or not text.strip():
        return TaskClassification("chat", "default_chat")
    stripped = text.strip()
    lowered = stripped.lower()
    has_path = any(signal in lowered for signal in PATH_SIGNALS)
    has_object = has_path or any(noun in lowered for noun in PROJECT_OBJECTS)
    if stripped.startswith(CHANGE_PREFIXES):
        return TaskClassification("change_task", "explicit_change_prefix")
    if any(action in lowered for action in MUTATION_ACTIONS) and has_object:
        reason = "mutation_action_with_path" if has_path else "mutation_action_with_project_object"
        return TaskClassification("change_task", reason)
    if stripped.startswith(READ_PREFIXES):
        return TaskClassification("read_task", "explicit_read_prefix")
    if any(action in lowered for action in READ_ACTIONS) and has_object:
        reason = "read_action_with_path" if has_path else "read_action_with_project_object"
        return TaskClassification("read_task", reason)
    return TaskClassification("chat", "default_chat")


def classify_task(text: str, *, explicit_mode: str | None = None) -> TaskMode:
    return classify_task_with_reason(text, explicit_mode=explicit_mode).mode
```

Keep established exact mutation signals such as install, delete, patch, and commit in the mutation branch so existing tests continue to pass.

- [ ] **Step 4: Run classifier and web classification tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_task_classification tests.test_web_api.OneCodeWebApiTests.test_math_capability_question_is_classified_as_chat tests.test_web_api.OneCodeWebApiTests.test_natural_language_project_check_is_classified_as_task -v
```

Expected: PASS.

- [ ] **Step 5: Commit the classifier change**

```bash
git add 'one code/src/onecode/kernel/task_classification.py' 'one code/tests/test_task_classification.py'
git commit -m "fix: classify natural language project tasks"
```

### Task 2: Enforce Explicit Workspace And Resume Approval In Shell Mode

**Repository:** OneCode

**Files:**
- Modify: `src/onecode/web/workspace.py`
- Modify: `src/onecode/web/api.py`
- Modify: `src/onecode/shell_launcher.py`
- Modify: `tests/test_web_api.py`
- Modify: `tests/test_shell_launcher.py`

- [ ] **Step 1: Write failing strict-workspace and resume tests**

Add tests proving the policy runs before model or evidence creation:

```python
def test_strict_shell_task_requires_explicit_workspace_before_model_call(self):
    from onecode.web.api import handle_chat_completion

    with tempfile.TemporaryDirectory() as tmp, patch.dict(
        "os.environ",
        {
            "ONECODE_WORKSPACE_ROOT": tmp,
            "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp,
            "ONECODE_REQUIRE_EXPLICIT_TASK_WORKSPACE": "true",
        },
        clear=True,
    ), patch("onecode.web.api.run_model_task") as run_model:
        payload, status = handle_chat_completion({
            "model": "onecode-agent",
            "messages": [{"role": "user", "content": "写一个 hello.txt"}],
        })
        self.assertEqual((status, payload["error"]["type"]), (400, "workspace_required"))
        run_model.assert_not_called()
        self.assertFalse((Path(tmp) / ".onecode").exists())


def test_resume_requires_approval_for_new_mutating_plan(self):
    from onecode.web.api import handle_onecode_run_resume

    with tempfile.TemporaryDirectory() as tmp, patch.dict(
        "os.environ",
        {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
        clear=True,
    ), patch("onecode.web.api.run_model_task", return_value={"status": "halted"}) as run_model:
        handle_onecode_run_resume("source-run", {"workspace": tmp, "message": "继续完成"})
    self.assertTrue(run_model.call_args.kwargs["require_explicit_approval"])
```

Also add a direct-chat test showing strict mode does not require a workspace.

- [ ] **Step 2: Run the targeted tests and confirm failure**

```bash
PYTHONPATH=src python3 -m unittest tests.test_web_api.OneCodeWebApiTests.test_strict_shell_task_requires_explicit_workspace_before_model_call tests.test_web_api.OneCodeWebApiTests.test_resume_requires_approval_for_new_mutating_plan -v
```

Expected: FAIL because missing workspace still resolves to the default and resume omits the flag.

- [ ] **Step 3: Add explicit-workspace helpers**

Add these functions to `src/onecode/web/workspace.py`:

```python
def explicit_task_workspace_required() -> bool:
    return os.getenv("ONECODE_REQUIRE_EXPLICIT_TASK_WORKSPACE", "").lower() in {"1", "true", "yes", "on"}


def request_workspace_value(body: dict[str, Any]) -> str | None:
    metadata = body.get("metadata")
    value = metadata.get("workspace") if isinstance(metadata, dict) else None
    return value.strip() if isinstance(value, str) and value.strip() else None


def workspace_from_request(body: dict[str, Any], *, require_explicit: bool = False) -> Path:
    value = request_workspace_value(body)
    if require_explicit and value is None:
        raise ValueError("workspace_required")
    return workspace_from_value(value)
```

- [ ] **Step 4: Reorder chat routing and enable approval on resume**

In `handle_chat_completion`, classify before resolving a project workspace. Resolve with `require_explicit=True` for approval messages in strict mode and for non-chat tasks in strict mode. Map `workspace_required` to its own error type:

```python
def _workspace_error(exc: ValueError) -> tuple[dict[str, Any], int]:
    if str(exc) == "workspace_required":
        return error_payload("workspace_required", "请先选择项目"), 400
    return error_payload("invalid_workspace", str(exc)), 400
```

Pass the missing resume flag explicitly:

```python
result = run_model_task(
    task,
    workspace=workspace,
    run_id=None,
    resume_from_run_id=run_id,
    model=effective_model.model,
    api_key=effective_model.api_key,
    provider_kind=effective_model.provider,
    endpoint=effective_model.endpoint,
    require_explicit_approval=True,
)
```

- [ ] **Step 5: Enable strict mode from the shell launcher**

Add the environment entry in `build_onecode_env`:

```python
env["ONECODE_REQUIRE_EXPLICIT_TASK_WORKSPACE"] = "true"
```

Assert the exact value in `tests/test_shell_launcher.py`.

- [ ] **Step 6: Run the focused safety suite**

```bash
PYTHONPATH=src python3 -m unittest tests.test_web_api tests.test_shell_launcher -v
```

Expected: PASS, including existing default-workspace tests when strict mode is absent.

- [ ] **Step 7: Commit the safety boundary**

```bash
git add 'one code/src/onecode/web/workspace.py' 'one code/src/onecode/web/api.py' 'one code/src/onecode/shell_launcher.py' 'one code/tests/test_web_api.py' 'one code/tests/test_shell_launcher.py'
git commit -m "fix: enforce shell workspace and resume approval"
```

### Task 3: Add Redacted Pending-Plan Listing And Flexible Exact Approval Commands

**Repository:** OneCode

**Files:**
- Create: `src/onecode/kernel/approval_summary.py`
- Modify: `src/onecode/kernel/approval_plans.py`
- Modify: `src/onecode/kernel/model_loop.py`
- Modify: `src/onecode/web/api.py`
- Modify: `tests/test_approval_plans.py`
- Modify: `tests/test_web_api.py`

- [ ] **Step 1: Write failing plan-listing, redaction, parser, and route tests**

Add tests for valid pending plans, workspace isolation, invalid files, and exact parser variants:

```python
def test_approval_parser_accepts_safe_variants_and_rejects_surrounding_prose(self):
    from onecode.web.api import parse_approval_message

    plan_id = "abcdef0123456789abcdef0123456789"
    accepted = (
        f"批准计划 {plan_id}",
        f"请批准计划 `{plan_id.upper()}`",
        f"确认 计划 {plan_id}",
        f"拒绝计划 {plan_id}",
    )
    for message in accepted:
        with self.subTest(message=message):
            self.assertIsNotNone(parse_approval_message(message))
    self.assertIsNone(parse_approval_message(f"我想批准计划 {plan_id} 但先等等"))


def test_pending_plan_list_returns_redacted_bounded_actions(self):
    from onecode.kernel.approval_plans import persist_approval_plan
    from onecode.kernel.model_provider import ModelPlan, ModelPlanAsset
    from onecode.web.api import handle_onecode_plans_list

    with tempfile.TemporaryDirectory() as tmp, patch.dict(
        "os.environ",
        {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
        clear=True,
    ):
        plan = ModelPlan(task="write result", assets=[ModelPlanAsset(path="docs/result.md", content="done\n")])
        stored = persist_approval_plan(Path(tmp), plan, model_metadata={"model": "m"})
        payload, status = handle_onecode_plans_list({"workspace": tmp})
    self.assertEqual(status, 200)
    self.assertEqual(payload["plans"][0]["plan_id"], stored.plan_id)
    self.assertNotIn("done\n", json.dumps(payload, ensure_ascii=False))
```

- [ ] **Step 2: Run the tests and confirm failure**

```bash
PYTHONPATH=src python3 -m unittest tests.test_approval_plans tests.test_web_api.OneCodeWebApiTests.test_approval_parser_accepts_safe_variants_and_rejects_surrounding_prose tests.test_web_api.OneCodeWebApiTests.test_pending_plan_list_returns_redacted_bounded_actions -v
```

Expected: FAIL because the listing handler and safe parser variants do not exist.

- [ ] **Step 3: Move approval summaries into a non-circular module**

Create `approval_summary.py` with public functions:

```python
from __future__ import annotations

from typing import Any

from onecode.kernel.approval_plans import StoredApprovalPlan
from onecode.kernel.execution_plan_loader import execution_plan_from_model_plan
from onecode.kernel.execution_tools import redact_sensitive_text


def approval_action_summaries(plan: Any) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for step in execution_plan_from_model_plan(plan).steps:
        for call in step.tool_calls:
            if call.tool_name == "run_command":
                argv = call.params.get("argv")
                actions.append({
                    "tool": "run_command",
                    "argv": [redact_sensitive_text(item) for item in argv] if isinstance(argv, list) else [],
                    "timeout_seconds": call.params.get("timeout_seconds", 60),
                })
            else:
                actions.append({
                    "tool": call.tool_name,
                    "path": call.params.get("path"),
                })
    return actions


def pending_plan_summary(stored: StoredApprovalPlan) -> dict[str, Any]:
    actions = approval_action_summaries(stored.plan)
    return {
        "plan_id": stored.plan_id,
        "plan_sha256": stored.plan_sha256,
        "created_at": stored.created_at,
        "workspace": stored.workspace,
        "task": stored.plan.task,
        "status": "pending",
        "action_count": len(actions),
        "tool_names": sorted({str(action.get("tool")) for action in actions}),
        "actions": actions,
    }
```

Move the existing richer write/patch redaction helpers from `model_loop.py` into this module rather than reducing their current redaction quality. Import `approval_action_summaries` back into `model_loop.py`.

- [ ] **Step 4: Add bounded pending-plan enumeration**

Add to `approval_plans.py`:

```python
def list_pending_approval_plans(workspace: Path, *, limit: int = 100) -> tuple[list[StoredApprovalPlan], int]:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    root = Path(workspace).resolve()
    directory = root / ".onecode" / "pending-plans"
    if not directory.is_dir():
        return [], 0
    plans: list[StoredApprovalPlan] = []
    skipped = 0
    for path in sorted(directory.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        if len(plans) >= limit:
            break
        try:
            plans.append(load_approval_plan(root, path.stem))
        except ValueError:
            skipped += 1
    return plans, skipped
```

- [ ] **Step 5: Add plan-list API handling and the exact parser**

Use this anchored pattern and lowercase normalization:

```python
APPROVAL_MESSAGE_PATTERN = re.compile(
    r"^(?:请\s*)?(批准|确认|拒绝)\s*计划\s+`?([A-Fa-f0-9]{32})`?\s*$"
)


def parse_approval_message(user_message: str) -> tuple[str, bool] | None:
    match = APPROVAL_MESSAGE_PATTERN.fullmatch(user_message.strip())
    if match is None:
        return None
    return match.group(2).lower(), match.group(1) != "拒绝"
```

Add `handle_onecode_plans_list`, authorize `GET /v1/onecode/plans`, require its workspace, and return `{workspace, plans, skipped_count}`. Update approval prose to include the exact line `请回复：批准计划 <plan_id>`.

- [ ] **Step 6: Run plan storage and API tests**

```bash
PYTHONPATH=src python3 -m unittest tests.test_approval_plans tests.test_web_api -v
```

Expected: PASS.

- [ ] **Step 7: Commit the structured approval API**

```bash
git add 'one code/src/onecode/kernel/approval_summary.py' 'one code/src/onecode/kernel/approval_plans.py' 'one code/src/onecode/kernel/model_loop.py' 'one code/src/onecode/web/api.py' 'one code/tests/test_approval_plans.py' 'one code/tests/test_web_api.py'
git commit -m "feat: expose redacted pending approval plans"
```

### Task 4: Publish Shell Projection V5 With Approval State

**Repository:** OneCode

**Files:**
- Modify: `src/onecode/kernel/shell_projection.py`
- Modify: `src/onecode/contracts/__init__.py`
- Create: `src/onecode/contracts/shell_projection_v5_schema.json`
- Create: `src/onecode/contracts/shell_projection_v5_cases.json`
- Modify: `tests/test_shell_projection.py`
- Modify: `tests/test_shell_contracts.py`
- Modify: `tests/test_web_api.py`
- Modify: `tests/test_runner_cli.py`
- Modify: `tests/test_cli_read_only_commands.py`
- Modify: `tests/test_inspect_cli.py`

- [ ] **Step 1: Write failing v5 projection tests**

Add an exact pending approval test:

```python
def test_pending_approval_projects_structured_approval_action(self):
    from onecode.kernel.shell_projection import project_run_to_shell

    plan_id = "a" * 32
    projection = project_run_to_shell({
        "run_id": "pending-run",
        "status": "halted",
        "reason": "approval_required",
        "plan_id": plan_id,
    })
    self.assertEqual(projection["version"], 5)
    self.assertEqual(projection["severity"], "blocked")
    self.assertEqual(projection["next_action"], "approve")
    self.assertEqual(projection["approval_state"], {
        "required": True,
        "plan_id": plan_id,
        "status": "pending",
    })
```

Add a completed-result test expecting `{required: False, plan_id: None, status: None}`.

- [ ] **Step 2: Run projection tests and confirm failure**

```bash
PYTHONPATH=src python3 -m unittest tests.test_shell_projection tests.test_shell_contracts -v
```

Expected: FAIL on version 4, missing `approval_state`, and `next_action=inspect`.

- [ ] **Step 3: Implement the v5 projection field**

Update the constants and projection:

```python
SHELL_PROJECTION_VERSION = 5
APPROVAL_STATE_FIELDS = ("required", "plan_id", "status")
SHELL_PROJECTION_FIELDS = (
    "version", "run_id", "status_label", "severity", "next_action", "compact_message",
    "rule_state", "control_state", "balance_state", "delivery_state", "evidence_ref",
    "resume_state", "approval_state",
)


def _approval_state(run: dict[str, Any]) -> dict[str, Any]:
    required = run.get("reason") == "approval_required"
    return {
        "required": required,
        "plan_id": _string(run.get("plan_id")) if required else None,
        "status": "pending" if required else None,
    }


def _next_action(run: dict[str, Any], severity: str) -> str:
    explicit = _string(run.get("next_action"))
    if explicit is not None:
        return explicit
    if run.get("reason") == "approval_required" and _string(run.get("plan_id")) is not None:
        return "approve"
    if severity in {"corrupt", "missing", "blocked"}:
        return "inspect"
    if severity == "warning":
        return "verify"
    return "idle"
```

Add `approval_state` to the schema and returned projection without changing severity semantics.

- [ ] **Step 4: Add v5 contract loaders and fixtures**

Add `load_shell_projection_v5_schema()` and `load_shell_projection_v5_cases()` using the same validation pattern as v4. Keep both v4 assets and loaders unchanged. The v5 schema must list `approval_state` in `fields` and `nested_fields` with exactly `required`, `plan_id`, and `status`. Include seven cases: the six current v4 inputs projected through v5 plus `pending_approval`.

- [ ] **Step 5: Update current-contract consumers from v4 to v5**

Change current schema assertions and CLI/API tests to import `load_shell_projection_v5_schema`. Keep explicit historical-resource tests for v4. Update all exact version assertions found by:

```bash
rg -n 'shell_projection.*version|\["version"\].*4|version.*4' tests
```

Expected after editing: only intentionally historical v4 fixture assertions remain.

- [ ] **Step 6: Run all projection consumers**

```bash
PYTHONPATH=src python3 -m unittest tests.test_shell_projection tests.test_shell_contracts tests.test_web_api tests.test_runner_cli tests.test_cli_read_only_commands tests.test_inspect_cli -v
```

Expected: PASS.

- [ ] **Step 7: Commit projection v5**

```bash
git add 'one code/src/onecode/kernel/shell_projection.py' 'one code/src/onecode/contracts' 'one code/tests/test_shell_projection.py' 'one code/tests/test_shell_contracts.py' 'one code/tests/test_web_api.py' 'one code/tests/test_runner_cli.py' 'one code/tests/test_cli_read_only_commands.py' 'one code/tests/test_inspect_cli.py'
git commit -m "feat: publish shell projection v5 approval state"
```

### Task 5: Align OneCode Timeout, Title, Git, Skill, And Startup Semantics

**Repository:** OneCode

**Files:**
- Modify: `src/onecode/web/api.py`
- Modify: `src/onecode/shell_launcher.py`
- Modify: `tests/test_web_api.py`
- Modify: `tests/test_shell_launcher.py`

- [ ] **Step 1: Write failing consistency tests**

Cover direct-chat timeout forwarding, parent Git detection, runtime title configuration, and path diagnostics:

```python
def test_direct_chat_uses_configured_timeout(self):
    from onecode.web.api import handle_chat_completion

    with patch.dict("os.environ", {"ONECODE_MODEL_TIMEOUT_SECONDS": "0.25"}, clear=True), patch(
        "onecode.web.api.direct_chat_completion", return_value="ok"
    ) as direct_chat, patch("onecode.web.api.read_model_config", return_value={}):
        handle_chat_completion({"messages": [{"role": "user", "content": "2+2"}]})
    self.assertEqual(direct_chat.call_args.kwargs["timeout_seconds"], 0.25)


def test_runtime_config_disables_onecode_title_generation(self):
    with tempfile.TemporaryDirectory() as tmp:
        path = build_runtime_config(shell_config(runtime_state_root=Path(tmp) / "state"))
    self.assertIn("titleConvo: false", path.read_text(encoding="utf-8"))
```

For Git, create a parent `.git` directory and assert `{present: True, relation: "parent"}` for a child workspace.

- [ ] **Step 2: Run tests and confirm failure**

```bash
PYTHONPATH=src python3 -m unittest tests.test_web_api tests.test_shell_launcher -v
```

Expected: FAIL on the new assertions.

- [ ] **Step 3: Apply the consistency changes**

- Parse `ONECODE_MODEL_TIMEOUT_SECONDS` before the chat/task split.
- Pass it as `timeout_seconds` to `direct_chat_completion`.
- Map `TimeoutError` to HTTP 504 `model_provider_timeout`.
- Remove the unreachable `chat_fallback` branch from `format_run_result`.
- Generate `titleConvo: false` and remove `titleModel` from shell runtime YAML.
- Add a bounded `git_status(workspace)` helper returning `present`, `relation`, and `root` from `git -C <workspace> rev-parse --show-toplevel`; return `relation="workspace"` when roots match and `relation="parent"` otherwise.
- Change the missing LibreChat package error to include the resolved directory and exact `--librechat-dir '<path>'` correction syntax.
- Keep `skill_context` data unchanged; add a compact `skill_sources` object with `project_manifest_status=<skill_context.status>` and `runtime_router_status="per_run"` so clients do not infer global router availability from project manifests.

- [ ] **Step 4: Run the consistency suite**

```bash
PYTHONPATH=src python3 -m unittest tests.test_web_api tests.test_shell_launcher tests.test_shell_timeout_integration -v
```

Expected: PASS.

- [ ] **Step 5: Commit secondary OneCode consistency**

```bash
git add 'one code/src/onecode/web/api.py' 'one code/src/onecode/shell_launcher.py' 'one code/tests/test_web_api.py' 'one code/tests/test_shell_launcher.py'
git commit -m "fix: align OneCode shell status semantics"
```

### Task 6: Add LibreChat OneCode Mode Persistence And Metadata

**Repository:** LibreChat

**Files:**
- Modify: `client/src/onecode/project.ts`
- Modify: `client/src/onecode/project.test.ts`
- Modify: `client/src/hooks/Chat/useChatFunctions.ts`
- Create: `client/src/components/Chat/Input/OneCodeModeControl.tsx`
- Create: `client/src/components/Chat/Input/OneCodeModeControl.test.tsx`
- Modify: `client/src/components/Chat/Input/OneCodeProjectButton.tsx`
- Modify: `client/src/components/Chat/Input/OneCodeProjectButton.test.tsx`

- [ ] **Step 1: Write failing metadata and mode persistence tests**

Add:

```typescript
it('builds workspace and explicit mode metadata while omitting automatic mode', () => {
  expect(buildOneCodeMetadata('/tmp/project', 'read_task')).toEqual({
    workspace: '/tmp/project',
    onecode_mode: 'read_task',
  });
  expect(buildOneCodeMetadata('/tmp/project', 'auto')).toEqual({ workspace: '/tmp/project' });
  expect(buildOneCodeMetadata('', 'chat')).toEqual({ onecode_mode: 'chat' });
});
```

Add storage round-trip tests for `auto`, `chat`, `read_task`, and `change_task`, rejecting unknown stored values back to `auto`.

- [ ] **Step 2: Run the project helper tests and confirm failure**

From `client`:

```bash
npx jest src/onecode/project.test.ts --runInBand
```

Expected: FAIL because mode helpers and the expanded metadata signature do not exist.

- [ ] **Step 3: Implement the mode contract**

Add to `client/src/onecode/project.ts`:

```typescript
export const ONECODE_MODE_STORAGE_KEY = 'onecode.mode';
export type OneCodeMode = 'auto' | 'chat' | 'read_task' | 'change_task';
export type OneCodeMetadata = {
  workspace?: string;
  onecode_mode?: Exclude<OneCodeMode, 'auto'>;
};

export function getStoredOneCodeMode(storage: Storage = window.localStorage): OneCodeMode {
  const value = storage.getItem(ONECODE_MODE_STORAGE_KEY);
  return value === 'chat' || value === 'read_task' || value === 'change_task' ? value : 'auto';
}

export function setStoredOneCodeMode(mode: OneCodeMode, storage: Storage = window.localStorage): void {
  if (mode === 'auto') {
    storage.removeItem(ONECODE_MODE_STORAGE_KEY);
    return;
  }
  storage.setItem(ONECODE_MODE_STORAGE_KEY, mode);
}

export function buildOneCodeMetadata(workspace: string, mode: OneCodeMode): OneCodeMetadata | undefined {
  const normalized = normalizeOneCodeWorkspace(workspace);
  const metadata: OneCodeMetadata = {
    ...(normalized ? { workspace: normalized } : {}),
    ...(mode === 'auto' ? {} : { onecode_mode: mode }),
  };
  return Object.keys(metadata).length > 0 ? metadata : undefined;
}
```

Update `useChatFunctions` to call both storage getters.

- [ ] **Step 4: Create the segmented mode control**

Implement `OneCodeModeControl.tsx` as a four-button `role="group"` control using the existing surface, border, focus-ring, and text tokens. Export labels `自动`, `问答`, `读取`, and `变更`. Each button uses `aria-pressed`, a stable 32px height, and no viewport-scaled typography.

Render it through a custom item near the top of the project popover. Persist selection immediately and keep workspace as the dominant header line.

- [ ] **Step 5: Run helper, hook, and input control tests**

From `client`:

```bash
npx jest src/onecode/project.test.ts src/components/Chat/Input/OneCodeModeControl.test.tsx src/components/Chat/Input/OneCodeProjectButton.test.tsx --runInBand
```

Expected: PASS.

- [ ] **Step 6: Commit LibreChat mode metadata**

```bash
git add client/src/onecode/project.ts client/src/onecode/project.test.ts client/src/hooks/Chat/useChatFunctions.ts client/src/components/Chat/Input/OneCodeModeControl.tsx client/src/components/Chat/Input/OneCodeModeControl.test.tsx client/src/components/Chat/Input/OneCodeProjectButton.tsx client/src/components/Chat/Input/OneCodeProjectButton.test.tsx
git commit -m "feat: add explicit OneCode task modes"
```

### Task 7: Forward Mode Metadata Through The LibreChat OneCode Adapter

**Repository:** LibreChat

**Files:**
- Modify: `packages/api/src/endpoints/custom/onecode.ts`
- Modify: `packages/api/src/endpoints/custom/onecode.spec.ts`
- Modify: `packages/api/src/endpoints/custom/initialize.spec.ts`

- [ ] **Step 1: Write a failing adapter test**

```typescript
it('forwards workspace and a validated OneCode mode', () => {
  expect(
    buildOneCodeModelKwargs(undefined, {
      workspace: ' /tmp/project ',
      onecode_mode: 'change_task',
    }),
  ).toEqual({ metadata: { workspace: '/tmp/project', onecode_mode: 'change_task' } });
});
```

Also test that `auto` and unknown strings are not forwarded.

- [ ] **Step 2: Run the adapter tests and confirm failure**

From `packages/api`:

```bash
npx jest src/endpoints/custom/onecode.spec.ts src/endpoints/custom/initialize.spec.ts --coverage=false --runInBand
```

Expected: FAIL because `OneCodeMetadata` contains only workspace.

- [ ] **Step 3: Extend the adapter metadata type and builder**

```typescript
export type OneCodeMetadata = {
  workspace?: string;
  onecode_mode?: 'chat' | 'read_task' | 'change_task';
};

const mode =
  metadata?.onecode_mode === 'chat' ||
  metadata?.onecode_mode === 'read_task' ||
  metadata?.onecode_mode === 'change_task'
    ? metadata.onecode_mode
    : undefined;
const nextMetadata = {
  ...currentMetadata,
  ...(workspace ? { workspace } : {}),
  ...(mode ? { onecode_mode: mode } : {}),
};
```

Return original `modelKwargs` only when neither workspace nor mode is present. Preserve `maxRetries: 0`.

- [ ] **Step 4: Run adapter unit and 504 integration tests**

```bash
npx jest src/endpoints/custom/onecode.spec.ts src/endpoints/custom/initialize.spec.ts src/endpoints/custom/onecode.integration.spec.ts --coverage=false --runInBand
```

Expected: PASS with one request in the 504 integration case.

- [ ] **Step 5: Commit adapter metadata forwarding**

```bash
git add packages/api/src/endpoints/custom/onecode.ts packages/api/src/endpoints/custom/onecode.spec.ts packages/api/src/endpoints/custom/initialize.spec.ts
git commit -m "feat: forward OneCode task mode metadata"
```

### Task 8: Add Typed Pending-Plan And Approval APIs To LibreChat

**Repository:** LibreChat

**Files:**
- Modify: `packages/data-provider/src/types.ts`
- Modify: `packages/data-provider/src/api-endpoints.ts`
- Modify: `packages/data-provider/src/data-service.ts`
- Modify: `api/server/services/OneCode/projectPicker.js`
- Modify: `api/server/services/OneCode/projectPicker.spec.js`
- Modify: `api/server/routes/onecode.js`
- Modify: `api/server/routes/onecode.spec.js`
- Modify: `client/src/onecode/project.ts`
- Modify: `client/src/onecode/project.test.ts`

- [ ] **Step 1: Write failing proxy and client helper tests**

Test these browser routes:

```javascript
const listResponse = await request(app).get('/api/onecode/plans?workspace=/tmp/project');
expect(listResponse.status).toBe(200);
expect(picker.listOneCodePlans).toHaveBeenCalledWith('/tmp/project');

const approvalResponse = await request(app)
  .post('/api/onecode/plans/abcdef0123456789abcdef0123456789/approval')
  .send({ workspace: '/tmp/project', approved: true });
expect(approvalResponse.status).toBe(200);
expect(picker.decideOneCodePlan).toHaveBeenCalledWith(
  '/tmp/project',
  'abcdef0123456789abcdef0123456789',
  true,
);
```

- [ ] **Step 2: Run API route tests and confirm failure**

From `api`:

```bash
npx jest server/routes/onecode.spec.js server/services/OneCode/projectPicker.spec.js --runInBand
```

Expected: FAIL because plan proxy functions and routes do not exist.

- [ ] **Step 3: Add shared plan types and endpoints**

Add exact types:

```typescript
export type TOneCodeApprovalAction = {
  tool: string;
  path?: string | null;
  argv?: string[];
  timeout_seconds?: number;
};

export type TOneCodePendingPlan = {
  plan_id: string;
  plan_sha256: string;
  created_at: number;
  workspace: string;
  task: string;
  status: 'pending';
  action_count: number;
  tool_names: string[];
  actions: TOneCodeApprovalAction[];
};

export type TOneCodePlansResponse = {
  workspace: string;
  plans: TOneCodePendingPlan[];
  skipped_count: number;
};

export type TOneCodePlanDecisionResponse = Record<string, unknown> & {
  status: string;
  reason?: string | null;
};
```

Add encoded endpoint functions, typed request methods, and exports following existing OneCode data-service patterns.

- [ ] **Step 4: Add local Express proxy functions and routes**

Use `requireAllowedWorkspace`, `encodeURIComponent(planId)`, and the existing authenticated `oneCodeFetch`. Require `approved` to be boolean before forwarding. Preserve the upstream error message. Add `listOneCodePlans` and `decideOneCodePlan` to module exports and route mocks.

- [ ] **Step 5: Add client normalization helpers**

Import `TOneCodePendingPlan` and `TOneCodePlanDecisionResponse` from `librechat-data-provider`, re-export them as local aliases, and do not duplicate their fields:

```typescript
export type OneCodePendingPlan = TOneCodePendingPlan;
export type OneCodePlanDecision = TOneCodePlanDecisionResponse;
```

Add typed `listOneCodePlans(workspace)` and `decideOneCodePlan(workspace, planId, approved)` helpers that return `undefined` for empty workspace or plan ID and otherwise call `dataService`.

- [ ] **Step 6: Run data-provider, API, and client helper tests**

```bash
cd packages/data-provider && npx jest --runInBand --coverage=false
cd ../../api && npx jest server/routes/onecode.spec.js server/services/OneCode/projectPicker.spec.js --runInBand
cd ../client && npx jest src/onecode/project.test.ts --runInBand
```

Expected: PASS.

- [ ] **Step 7: Commit the typed proxy layer**

```bash
git add packages/data-provider/src/types.ts packages/data-provider/src/api-endpoints.ts packages/data-provider/src/data-service.ts api/server/services/OneCode/projectPicker.js api/server/services/OneCode/projectPicker.spec.js api/server/routes/onecode.js api/server/routes/onecode.spec.js client/src/onecode/project.ts client/src/onecode/project.test.ts
git commit -m "feat: proxy OneCode approval plans"
```

### Task 9: Build The Console Approval Workflow

**Repository:** LibreChat

**Files:**
- Create: `client/src/components/OneCode/ApprovalTab.tsx`
- Create: `client/src/components/OneCode/ApprovalTab.test.tsx`
- Modify: `client/src/onecode/console.ts`
- Create: `client/src/onecode/console.test.ts`
- Modify: `client/src/components/OneCode/OneCodeConsolePanel.tsx`
- Modify: `client/src/components/OneCode/OneCodeConsolePanel.test.tsx`

- [ ] **Step 1: Write failing ApprovalTab interaction tests**

Test empty, pending, approve, reject, disabled, conflict, and wrapping states:

```typescript
it('approves a pending plan once and disables both decisions in flight', async () => {
  const decide = jest.fn(() => new Promise<Record<string, unknown>>(() => undefined));
  render(<ApprovalTab workspace="/tmp/project" plans={[pendingPlan]} onDecide={decide} />);
  fireEvent.click(screen.getByRole('button', { name: '批准计划' }));
  expect(decide).toHaveBeenCalledWith(pendingPlan, true);
  expect(screen.getByRole('button', { name: '批准计划' })).toBeDisabled();
  expect(screen.getByRole('button', { name: '拒绝计划' })).toBeDisabled();
});
```

- [ ] **Step 2: Run the component test and confirm failure**

From `client`:

```bash
npx jest src/components/OneCode/ApprovalTab.test.tsx --runInBand
```

Expected: FAIL because the component does not exist.

- [ ] **Step 3: Implement ApprovalTab**

Use `Check`, `X`, and `ChevronDown` from `lucide-react`. Render one bounded item per plan, never nested cards. Show workspace, task, monospaced plan ID, time, tool names, and redacted actions. Use native buttons with localized `aria-label`, visible text, existing `btn` variants, and an in-flight plan ID state. Render long values with `break-all` or `whitespace-pre-wrap`.

The component contract is:

```typescript
type ApprovalTabProps = {
  workspace: string;
  plans: OneCodePendingPlan[];
  loading?: boolean;
  error?: string;
  onRefresh: () => void;
  onDecide: (plan: OneCodePendingPlan, approved: boolean) => Promise<Record<string, unknown>>;
};
```

After a decision resolves, announce the result in an `aria-live="polite"` status and call `onRefresh`. On rejection, use the danger treatment. During approval, use neutral pending styling until the returned run status is known.

- [ ] **Step 4: Add the Console tab and orchestration**

Insert `approval` after `project` in `ONECODE_CONSOLE_TABS` with label `审批`. In `OneCodeConsolePanel`, add plans, loading, and approval error state; load plans when the tab opens; call `decideOneCodePlan`; refresh plans and runs after a decision. Clear plans when workspace is empty or changes.

Add `client/src/onecode/console.test.ts` asserting that `approval` is present exactly once, follows `project`, and maps to the `审批` label.

- [ ] **Step 5: Run Console tests**

```bash
npx jest src/components/OneCode/ApprovalTab.test.tsx src/components/OneCode/OneCodeConsolePanel.test.tsx src/onecode/console.test.ts --runInBand
```

Expected: PASS.

- [ ] **Step 6: Commit the approval UI**

```bash
git add client/src/components/OneCode/ApprovalTab.tsx client/src/components/OneCode/ApprovalTab.test.tsx client/src/onecode/console.ts client/src/onecode/console.test.ts client/src/components/OneCode/OneCodeConsolePanel.tsx client/src/components/OneCode/OneCodeConsolePanel.test.tsx
git commit -m "feat: add OneCode Console approvals"
```

### Task 10: Add Planning And Error Feedback Without Pretending To Stream

**Repository:** LibreChat

**Files:**
- Create: `client/src/onecode/errors.ts`
- Create: `client/src/onecode/errors.test.ts`
- Create: `client/src/components/Chat/Input/OneCodeActivityStatus.tsx`
- Create: `client/src/components/Chat/Input/OneCodeActivityStatus.test.tsx`
- Modify: `client/src/components/Chat/Input/ChatForm.tsx`
- Modify: `client/src/components/OneCode/OneCodeConsolePanel.tsx`
- Modify: `librechat.yaml`

- [ ] **Step 1: Write failing error mapping and activity-state tests**

```typescript
it.each([
  ['workspace_required', '请先选择项目'],
  ['model_provider_timeout', '规划超时，可手动重试'],
  ['model_configuration_missing', '请先配置 OneCode 模型'],
])('maps %s to an operational message', (type, message) => {
  expect(formatOneCodeError({ response: { data: { error: { type } } } })).toBe(message);
});

it('shows planning only for an active OneCode submission', () => {
  render(<OneCodeActivityStatus endpoint="OneCode" isSubmitting />);
  expect(screen.getByText('OneCode 正在规划')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests and confirm failure**

```bash
cd client && npx jest src/onecode/errors.test.ts src/components/Chat/Input/OneCodeActivityStatus.test.tsx --runInBand
```

Expected: FAIL because both modules are new.

- [ ] **Step 3: Implement bounded error normalization**

`formatOneCodeError(error: unknown)` must safely inspect Axios-style `response.data.error.type` and `message`, map 400/409/502/503/504 types to the approved Chinese operational messages, and fall back to an existing non-empty message or `OneCode 请求失败`. It must not stringify entire responses or expose secrets.

- [ ] **Step 4: Implement request-state feedback**

`OneCodeActivityStatus` renders nothing for other endpoints or idle state. It renders `OneCode 正在规划` while the current OneCode submission is active. ApprovalTab owns the structured `等待批准` state, while the assistant approval message remains the chat-surface record. Use text plus the existing muted color role and an `aria-live="polite"` region. Do not animate fake progress or split the existing one-chunk response.

Render the status near the OneCode project control in `ChatForm` using the existing endpoint and `isSubmitting` state. Reuse `formatOneCodeError` in Console promise catches.

- [ ] **Step 5: Disable OneCode title generation**

Change the checked-in `librechat.yaml` OneCode endpoint to:

```yaml
titleConvo: false
summarize: false
```

Remove `titleModel` for OneCode.

- [ ] **Step 6: Run feedback tests and config assertions**

```bash
cd client && npx jest src/onecode/errors.test.ts src/components/Chat/Input/OneCodeActivityStatus.test.tsx src/components/OneCode/OneCodeConsolePanel.test.tsx --runInBand
cd ../packages/api && npx jest src/endpoints/custom/onecode.spec.ts src/endpoints/custom/onecode.integration.spec.ts --coverage=false --runInBand
```

Expected: PASS.

- [ ] **Step 7: Commit status and error feedback**

```bash
git add client/src/onecode/errors.ts client/src/onecode/errors.test.ts client/src/components/Chat/Input/OneCodeActivityStatus.tsx client/src/components/Chat/Input/OneCodeActivityStatus.test.tsx client/src/components/Chat/Input/ChatForm.tsx client/src/components/OneCode/OneCodeConsolePanel.tsx librechat.yaml
git commit -m "fix: surface OneCode planning and errors"
```

### Task 11: Clarify Git And Skill Status In The Console

**Repository:** LibreChat

**Files:**
- Modify: `packages/data-provider/src/types.ts`
- Modify: `client/src/onecode/project.ts`
- Modify: `client/src/onecode/project.test.ts`
- Modify: `client/src/components/OneCode/ProjectTab.tsx`
- Create: `client/src/components/OneCode/ProjectTab.test.tsx`

- [ ] **Step 1: Write failing status semantics tests**

```typescript
it('distinguishes parent Git and project skill manifests from runtime routing', () => {
  render(<ProjectTab
    workspace="/tmp/repo/project"
    status={{
      workspace: '/tmp/repo/project',
      exists: true,
      allowed: true,
      git: { present: true, relation: 'parent', root: '/tmp/repo' },
      skill_context: { status: 'missing' },
      skill_sources: {
        project_manifest_status: 'missing',
        runtime_router_status: 'per_run',
      },
    }}
    onRefresh={jest.fn()}
    onInit={jest.fn()}
    onSyncMCP={jest.fn()}
  />);
  expect(screen.getByText('位于父级 Git 仓库')).toBeInTheDocument();
  expect(screen.getByText('项目技能清单: 未配置')).toBeInTheDocument();
  expect(screen.getByText('运行时路由: 按运行判定')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the status component tests and confirm failure**

```bash
cd client && npx jest src/components/OneCode/ProjectTab.test.tsx src/onecode/project.test.ts --runInBand
```

Expected: FAIL because the types and labels do not exist.

- [ ] **Step 3: Extend types and render explicit status rows**

Add Git `relation: 'workspace' | 'parent' | 'none'` and optional `root`, plus the compact `skill_sources` type defined by the OneCode project-status contract. Update `projectStatusBadges` so parent Git is not labelled uninitialized. Render flat status rows in `ProjectTab`; map `runtime_router_status="per_run"` to `按运行判定`. Do not add nested cards, claim runtime availability, or expose raw skill manifests.

- [ ] **Step 4: Run project and Console tests**

```bash
cd client && npx jest src/components/OneCode/ProjectTab.test.tsx src/components/OneCode/OneCodeConsolePanel.test.tsx src/onecode/project.test.ts --runInBand
```

Expected: PASS.

- [ ] **Step 5: Commit the semantic labels**

```bash
git add packages/data-provider/src/types.ts client/src/onecode/project.ts client/src/onecode/project.test.ts client/src/components/OneCode/ProjectTab.tsx client/src/components/OneCode/ProjectTab.test.tsx
git commit -m "fix: clarify OneCode project status labels"
```

### Task 12: Run Contract, Build, Browser, And Live-Shell Release Gates

**Repositories:** OneCode and LibreChat

**Files:**
- Create: `e2e/specs/onecode-console.spec.ts` in LibreChat
- Modify: `scripts/onecode-smoke.mjs` in LibreChat
- Create: `docs/ONECODE_LIBRECHAT_EXECUTION_RELIABILITY_CLOSURE_2026-07-16.md` in OneCode

- [ ] **Step 1: Add a Playwright Console workflow**

Create an authenticated local-shell spec that sets `onecode.workspace`, opens the OneCode control, opens Console, selects `审批`, and verifies empty and pending states. Intercept browser-facing `/api/onecode/plans` and approval routes with deterministic redacted payloads. Include desktop `1440x900` and mobile `390x844` projects or explicit viewport blocks. Assert keyboard focus, no horizontal overflow, disabled decision buttons during the request, and visible error details for a 409 response.

The pending fixture must use:

```typescript
const pendingPlan = {
  plan_id: 'abcdef0123456789abcdef0123456789',
  plan_sha256: 'f'.repeat(64),
  created_at: 1_752_640_000,
  workspace: '/tmp/project',
  task: '写入 docs/result.md',
  status: 'pending',
  action_count: 1,
  tool_names: ['write_text'],
  actions: [{ tool: 'write_text', path: 'docs/result.md' }],
};
```

- [ ] **Step 2: Expand the live smoke script**

Require `ONECODE_SMOKE_WORKSPACE` for project-scoped checks. Add requests for project status, pending plans, and a strict-workspace negative chat request. The script must assert status codes and types instead of logging only. Keep mutating model execution out of the automated smoke script because model output is nondeterministic; execute that flow in the manual live-shell matrix below.

- [ ] **Step 3: Run the full OneCode test suite**

From the OneCode code root:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
bash scripts/verify.sh
```

Expected: both commands exit 0 with no failures.

- [ ] **Step 4: Run LibreChat targeted tests and builds**

From the LibreChat root:

```bash
cd packages/api && npx jest src/endpoints/custom/onecode.spec.ts src/endpoints/custom/onecode.integration.spec.ts src/endpoints/custom/initialize.spec.ts --coverage=false --runInBand
cd ../../packages/data-provider && npm run build
cd ../../api && npx jest server/routes/onecode.spec.js server/services/OneCode/projectPicker.spec.js --runInBand
cd ../client && npx jest src/onecode/project.test.ts src/onecode/errors.test.ts src/components/OneCode src/components/Chat/Input/OneCodeModeControl.test.tsx src/components/Chat/Input/OneCodeActivityStatus.test.tsx --runInBand
cd .. && npm run build:api && npm run build:client
```

Expected: all tests and builds exit 0.

- [ ] **Step 5: Run Playwright desktop and mobile checks**

```bash
npx playwright test e2e/specs/onecode-console.spec.ts --config=e2e/playwright.config.local.ts --workers=1
```

Expected: desktop and mobile cases pass with no overflow or inaccessible decision controls. Capture screenshots for the pending, executing, error, and mobile states under the Playwright output directory.

- [ ] **Step 6: Run the real local-shell matrix**

Launch the shell using the actual LibreChat checkout and a disposable allowed workspace. Verify, in order:

1. `帮我看看这个仓库` reaches a read task.
2. `写一个 hello.txt` produces `approval_required` and no file.
3. Console rejection leaves no file.
4. A fresh plan approved in Console creates only the planned file.
5. A mutating resume produces another pending approval and does not mutate.
6. Clearing the selected project makes a project task return `workspace_required`.
7. A forced provider timeout produces one upstream request and a visible 504 state.
8. Replaying an approved plan returns 409.

Record run IDs, plan IDs, status codes, and artifact hashes in the closure document. Do not record API keys or full sensitive prompts.

- [ ] **Step 7: Write and verify the closure report**

The report must contain the exact commands above, pass/fail results, OneCode and LibreChat commits, projection version, screenshots, live run IDs, unresolved risks, and rollback points. Verify it contains no placeholder markers:

```bash
rg -n '[T]BD|[T]ODO|pending evidence|not run' docs/ONECODE_LIBRECHAT_EXECUTION_RELIABILITY_CLOSURE_2026-07-16.md
```

Expected: no output.

- [ ] **Step 8: Commit final verification artifacts separately in each repository**

LibreChat:

```bash
git add e2e/specs/onecode-console.spec.ts scripts/onecode-smoke.mjs
git commit -m "test: verify OneCode approval workflow"
```

OneCode parent repository:

```bash
git add 'one code/docs/ONECODE_LIBRECHAT_EXECUTION_RELIABILITY_CLOSURE_2026-07-16.md'
git commit -m "docs: close OneCode LibreChat reliability work"
```

## Release Gate

Do not enable the combined release until all conditions are true:

- OneCode strict workspace mode is exported by the shell launcher.
- LibreChat sends workspace and optional explicit mode metadata.
- OneCode serves shell projection v5.
- LibreChat types and Console consume approval state and pending plans.
- Resume uses explicit approval.
- OneCode full tests and LibreChat targeted tests/builds pass.
- Playwright desktop/mobile flows pass.
- The real shell matrix has recorded evidence for approve, reject, resume, missing workspace, timeout, and replay.

Rollback is repository-specific: revert the LibreChat UI/API commits first, then revert strict workspace and projection v5 in OneCode. Never leave strict workspace enabled with a LibreChat version that cannot send workspace metadata.
