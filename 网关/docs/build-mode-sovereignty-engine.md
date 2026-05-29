# Build Mode Sovereignty Engine

`agent_skill_dictionary.build_mode_sovereignty` extends the Build Mode equilibrium rules from provider-side tool control to local runtime evidence. Its job is to prevent a split-brain state where the model is constrained by the gateway, but the local CLI freely creates fake dependency shims or other unplanned files.

## Control Law

The Build Mode gateway treats cloud intent and local workspace state as one sovereignty surface:

- If required physical dependencies are missing, the build must not start under the fiction that local shims are acceptable.
- If the workspace contains files outside the `RequiredArtifactPlan` and support-file allowlist, the next turn must halt before more tools are exposed.

This maps to the yin/yang balance rule:

- missing real packages are insufficient local yang capacity, so the system enters `100` stop posture until a real environment is selected;
- unplanned local files are uncontrolled yang leakage, so the system removes tools and forces cleanup before continuing.

## Environment Gate

Set `ONEWORD_BUILD_MODE_REQUIRE_REAL_DEPS=1` to make dependency availability a hard preflight gate.

The gateway probes `ONEWORD_BUILD_MODE_PYTHON` when set, otherwise the current Python executable. The probe runs in the target interpreter and checks the packages required by the recognized artifact plan:

- `secure-rpc-mesh`: `fastapi`, `pytest_asyncio`, `cryptography`
- `cluster-state-sync`: `fastapi`, `sqlmodel`, `pytest_asyncio`, `redis`

If packages are missing, metadata reports:

- `oneword_build_mode.hexagram = "100"`
- `oneword_build_mode.source = "sovereignty_environment_gate"`
- `build_mode_sovereignty.environment_gate`

The payload tools are removed and the instruction explicitly forbids creating fake dependency modules such as `fastapi/`, `sqlmodel/`, or `pytest.py`.

## Workspace Gate

For recognized artifact plans, the gateway audits the workspace before creating support files or computing artifact gaps.

Allowed paths are:

- plan artifacts
- package support files such as `api/__init__.py`, `sync/__init__.py`, `core/__init__.py`, and `tests/__init__.py`
- gateway metadata under `.yizijue/`
- Python cache files under `__pycache__/`

Any other file is treated as unplanned local creation. The gateway enters `100` stop posture, removes tools, and reports:

- `oneword_build_mode.source = "sovereignty_workspace_gate"`
- `build_mode_sovereignty.workspace_gate.unplanned_paths`

This catches dependency shims on the next request turn and prevents them from being normalized into the Build Mode flow.

## Tool Execution Gate

When the gateway executes a Build Mode tool with a bound artifact plan, `execute_build_mode_tool` applies the same allowlist before `write_file` or `apply_patch` touches disk.

This prevents provider-side tool calls from creating unplanned local artifacts even if a caller bypasses the request rewrite layer and calls the tool execution endpoint directly.

The bound plan can come from:

- an explicit `artifact_plan` object inside the local runtime call;
- `request_text` / `original_request`;
- `metadata.oneword_build_mode.project_name` or `artifact_project`.

If the model attempts to write `fastapi/__init__.py`, `sqlmodel/__init__.py`, `pytest.py`, or any other path outside the plan, the executor returns `ViolationEvidence` with `reason = "unplanned_artifact_path"` and does not create the file.

## PATH Runtime Gate

The local PATH sentinels in `bin/` also participate in Build Mode sovereignty checks.

When these environment variables are present:

- `ONEWORD_BUILD_MODE=1`
- `ONEWORD_BUILD_MODE_WORKSPACE` or `ONEWORD_WORKSPACE_ROOT`
- `ONEWORD_BUILD_MODE_REQUEST_TEXT` or `ONEWORD_BUILD_MODE_PROJECT`

`agent_skill_dictionary.path_sentinel` resolves the artifact plan and runs the sovereignty checks before ordinary command preflight.

If the workspace already contains unplanned artifacts, or `ONEWORD_BUILD_MODE_REQUIRE_REAL_DEPS=1` finds missing packages in `ONEWORD_BUILD_MODE_PYTHON`, the sentinel exits `126` and prints `oneword build mode sovereignty denied` to stderr. The real binary is not executed.

This gives external CLI processes a local runtime guard as long as they execute through the repo-provided PATH wrappers such as `bin/python`, `bin/python3`, `bin/bash`, `bin/sh`, or `bin/rm`.

## Guarded Runtime Runner

For harnesses that need to execute untrusted local commands, use the controlled runner instead of launching the process directly:

```bash
python3 -m agent_skill_dictionary.cli build-mode-guarded-run \
  --workspace /path/to/workspace \
  --request-text "实现 cluster-state-sync" \
  -- /usr/bin/python3 -m pytest -q
```

The runner performs:

1. pre-run workspace sovereignty audit;
2. local command execution with repo `bin/` wrappers prepended to `PATH`;
3. post-run workspace sovereignty audit;
4. quarantine of newly created unplanned artifacts under `.yizijue/quarantine/`;
5. `exit_code = 126` and `status = "blocked"` when sovereignty is violated.

This closes the common absolute-binary bypass for controlled A/B harnesses: even if a subprocess calls `/usr/bin/python3` directly and creates `fastapi/__init__.py`, the runner detects the post-run violation and removes the fake module from the active workspace.

When `run_pytest` is executed through Build Mode with a bound artifact plan and local execution is selected, the tool executor uses this guarded runner automatically. A test command that exits `0` but leaves `fastapi/`, `sqlmodel/`, `pytest.py`, or other unplanned files behind is downgraded to `needs_fix`, the files are quarantined, and archive finalization is skipped.

## Expert Handoff

After two failed verification cycles, Build Mode enters `100` and emits `build_mode_expert_handoff`. Model write privileges remain revoked. A human-approved expert seed can be applied only through the explicit token-gated path:

```bash
export ONEWORD_EXPERT_HANDOFF_TOKEN="local-human-approved-token"

python3 -m agent_skill_dictionary.cli build-mode-expert-handoff \
  --workspace /path/to/workspace \
  --session-id session-a \
  --request-text "实现 cluster-state-sync" \
  --token "$ONEWORD_EXPERT_HANDOFF_TOKEN" \
  --changes-json '{"sync/models.py":"...full file contents..."}' \
  --verify-command-json '["/usr/bin/python3","-m","pytest","-q"]'
```

The handoff path enforces:

- token must match `ONEWORD_EXPERT_HANDOFF_TOKEN`;
- workspace state must show the failure gate is active;
- every changed path must be inside the `RequiredArtifactPlan`;
- verification runs through the guarded runtime runner;
- archive finalization happens only after guarded verification succeeds.
- successful handoff resets `consecutive_failures` to `0` and records an `expert_handoff` state result so the next turn is not trapped in `100`.
- completed and blocked handoff attempts append tamper-evident records to `.yizijue/audit.jsonl` with `source = "expert_handoff"`.

It is therefore not an automatic bypass and cannot create fake dependency shims.

The same path is available through the gateway control plane:

```http
POST /v1/yizijue/expert-handoff
Authorization: Bearer <ONEWORD_GATEWAY_TOKEN>
Content-Type: application/json

{
  "workspace": "/path/to/workspace",
  "session_id": "session-a",
  "request_text": "实现 cluster-state-sync",
  "token": "<ONEWORD_EXPERT_HANDOFF_TOKEN>",
  "changes": {"sync/models.py": "...full file contents..."},
  "verify_command": ["/usr/bin/python3", "-m", "pytest", "-q"]
}
```

Gateway workspace allowlisting applies before the expert token is evaluated.

When `session_id`, `conversation_id`, or `thread_id` is provided, handoff reads and resets the matching session-scoped state file such as `.yizijue/build-mode-state-session-a.json`.

## Current Boundary

This implementation is a gateway/runtime audit gate, a guarded tool-execution write gate, a PATH-wrapper runtime gate, and a guarded runner with post-run quarantine. It still does not intercept filesystem syscalls at the instant a process writes bytes. True write-drop enforcement would require a filesystem monitor, sandbox mount, or kernel-level mechanism. Until that layer exists, the system can detect unauthorized local artifacts at turn boundaries, block guarded tool writes before disk mutation, stop wrapped commands before execution, quarantine unplanned artifacts after controlled process execution, halt model forwarding, and force cleanup before continuing.
