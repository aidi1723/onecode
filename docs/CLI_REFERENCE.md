# OneCode CLI Reference

This reference documents the supported OneCode command-line entrypoints (`onecode` or `python3 -m onecode`).

## 1. Core Execution Commands

### `onecode run-model`
Run the autonomous coding loop against a workspace using a configured model provider:

```bash
onecode run-model "Implement module foo and pass unit tests" \
  --workspace ./my-project \
  --run-id task-01 \
  --agent-mode terminal \
  --execution-scope full_terminal \
  --max-turns 20 \
  --verifier python-unittest \
  --approve
```

Key options:
- `--agent-mode {classic,terminal,phased_terminal}`: Select deterministic multi-turn terminal execution or two-phase read/patch orchestration (`--phased`).
- `--execution-scope {read_only,patch_guarded,full_terminal}`: Restrict what file writes and commands the runtime permits.
- `--verifier VERIFIER` / `--verifier-policy PATH`: Enforce isolated sandbox test validation before permitting `deliverable` completion.
- `--rollback-on-failure`: Automatically restore modified files to pre-run snapshot state if the session halts without completing.
- `--provider {responses,chat,openai-compatible,compatible,qwen,dashscope,deepseek,kimi,moonshot,zhipu,glm}`, `--model`, `--endpoint`, `--api-key`, `--http-timeout-seconds`.

### `onecode run`
Run bounded single-turn write/patch/command actions with checkpointing and resume support:

```bash
# Write one or multiple assets
onecode run "write asset" \
  --workspace ./my-project \
  --run-id demo-run \
  --write-path src/demo.py \
  --write-content "value = 1\n"

# Resume idempotently from an earlier checkpoint
onecode run "resume asset" \
  --workspace ./my-project \
  --run-id demo-resume \
  --resume-from demo-run \
  --write-path src/demo.py \
  --write-content "value = 1\n"
```

Key options: `--write-text PATH=CONTENT`, `--patch-path`, `--search-block`, `--replace-block`, `--intent-type`, `--command`, `--max-write-bytes`, `--max-actions`, `--completed-evidence-mode {full,wal}`, `--evidence-durability {strict,relaxed}`.

### `onecode run-plan` & `onecode run-execution-plan`
Execute declarative JSON asset/patch plans (`run-plan`) or approved command step plans (`run-execution-plan`):

```bash
onecode init-verifier-policy --workspace ./my-project --preset python-unittest
onecode run-plan \
  --workspace ./my-project \
  --run-id plan-01 \
  --plan ./plan.json \
  --verifier python-unittest
```

`run-plan` also supports automated repair retries via `--repair-model`, `--repair-provider`, `--repair-endpoint`, and `--max-repair-attempts`.

## 2. Audit, Diagnostics, and Evidence Inspection

Each run writes immutable evidence under `<workspace>/.onecode/runs/<run-id>/` (`manifest.json`, `ledger.json`, `ledger.jsonl`, `trace.jsonl`, `evidence-chain.jsonl`).

- `onecode inspect --workspace ./my-project --run-id <id>`: Inspect run status, ledger integrity, and SHA-256 evidence chain continuity.
- `onecode list-runs --workspace ./my-project`: List all recorded runs in a workspace.
- `onecode doctor [--production]`: Run built-in boundary checks (`write_text`, `resume_skip`, `sovereignty_breach`, `http_timeout`, `project_context`, `runtime_config`, `skill_context`, `recovery_policy`, `deployment_boundary`).
- `onecode math-audit`: Inspect the deterministic 64-state transition table (`56` self-loop fixed points, `8` energy-decreasing edges), Lyapunov invariants, and optional `symbolic_extension` attachment status.
- `onecode audit-self`: Run end-to-end self-audit across CLI/TUI/compile/unit checks.
- `onecode sandbox-smoke`: Verify isolated Docker container test execution (network disabled).
- `onecode list-verifier-presets`: List built-in verifier presets (`python-unittest`, etc.).

## 3. Configuration, Approvals, and Interactive Interfaces

- `onecode config {show,set-model,discover-models}`: View active configuration hierarchies or configure default model endpoints.
- `onecode approvals`: Manage pending human-in-the-loop approval requests.
- `onecode tui [--workspace PATH] [--model MODEL]`: Start the interactive terminal UI (`onecode-kernel[tui]`, installed locally via `pip install -e .[tui]`).
- `onecode serve [--host 127.0.0.1] [--port 19080]`: Serve an OpenAI-compatible HTTP API with `ONECODE_API_TOKEN` authentication (`/health`, `/v1/models`, `/v1/chat/completions`).
- `onecode shell` & `onecode shell-status`: Manage local web shell integration when `ONECODE_LIBRECHAT_DIR` or an adjacent shell checkout is configured.
- `onecode shell-schema`: Print the public structured `shell_projection` contract schema.
- `onecode mcp --config --target {claude,cursor,goose}`: Generate MCP client configuration snippets.

## 4. Key Environment Variables

| Variable | Purpose |
| :--- | :--- |
| `ONECODE_API_KEY` | Primary API key for `run-model` providers |
| `ONECODE_STREAM_CHAT=1` | Enable native SSE streaming to prevent upstream gateway origin timeouts (e.g. HTTP 524) |
| `ONECODE_API_TOKEN` | Bearer token required by `onecode serve` |
| `ONECODE_RUN_COMMAND_SANDBOX` | Sandbox policy for shell commands (`auto`, `docker`, `host`) |
| `ONECODE_LIBRECHAT_DIR` | Path override for the LibreChat web shell directory |
| `ONECODE_DISTILLED_DATASET_PATHS` | Optional colon-separated paths for local offline evaluation datasets |
