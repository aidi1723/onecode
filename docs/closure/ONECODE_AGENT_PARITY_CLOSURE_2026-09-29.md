# OneCode Agent Parity Handbook Closure

Date: 2026-09-29
Status: Published to `origin/main` with this commit
Branch: `main`
Base before this closeout: `b18f442`
Version: v0.8.0 local kernel
Source: `docs/superpowers/plans/2026-09-29-agent-parity-handbook.md`

## Outcome

The handbook tasks are implemented. OneCode remains a local kernel. This
closeout does not claim parity with general coding agents.
`claims_mainstream_parity` stays false in both evaluation records.

The I Ching layer still only consumes tool outcomes. No new hexagram was
added. Single-shot `dispatch_decision` is unchanged: `halt`, `checkpoint`,
and `discover` still dispatch `stop`. The multi-turn shell reads the same
transition through `agent_cycle_decision`.

## What the handbook added

| Phase | Behavior |
| --- | --- |
| 1. Cycle | `model_continue`, `read_only_continue`, `verify`, and `stop`. A turn allows at most two tools. The default cap is 8 turns, then `resource_budget_exceeded` |
| 2. Edit | Literal search stays the default. Optional regex rejects nested repeats. `glob_files` and Python `outline` report `search_miss` when empty. A non-unique patch returns `patch_mismatch` and does not write. Patch results include a unified diff and can be restored from the checkpoint sha256 |
| 3. Memory | History over the character budget keeps the task, a one-line summary, and the last two turns. `.onecode/memory.jsonl` is appended only after an explicit confirm and only when the cycle is not `stop` |
| 4. Terminal and git | `run_command` can stream through `on_output`. A timeout returns `http_timeout`. One Docker container is reused per workspace when the daemon is up; `auto` still falls back to the host allowlist. `git_diff` is read-only. `git_commit` is mutating and stays on the approval list |
| 5. Extensions | MCP tools register as `mcp.<server>.<tool>`, require approval, and return `action_exception` when the process cannot be reached. At most three read-only subagents run. Each has a turn budget and `.onecode/subagents/<id>/result.json`. The parent status code comes from `IchingKernel.aggregate_status` |
| 6. Interface | Chat streaming writes a `tool_turn` event when a step finishes, then the final answer and `data: [DONE]`. `write_text`, `patch_text`, and `git_commit` approval summaries include a unified diff. The file is unchanged until the existing approval plan is approved. The TUI shows that diff and accepts `/approve` and `/reject` |
| 7. Evaluation | Thirty local tasks live in `benchmarks/tasks/agent/`. Five SWE-bench Lite instance ids are pinned in `benchmarks/swebench-lite/subset.jsonl` |

## Workflow run

On 2026-09-29 a temporary workspace was driven through the real tool registry,
approval plan store, and execution engine. The language model was not called.
A fixed plan stood in for the planner. Observed results:

| Design point | Observed |
| --- | --- |
| `search_miss` | Cycle `read_only_continue`. Transition `discover`. Dispatch remains `stop` |
| Read-only write | `permission_denied`. The target file was not created |
| Following turn | The second proposal saw the first tool result. `outline` returned `Greeter` and `greet` |
| Success | `cooldown` with cycle `model_continue` |
| Memory | A stopped turn was not stored. A completed turn was stored |
| Turn cap | `resource_budget_exceeded` |
| Bad patch | `patch_mismatch`. File stayed `return "old"` |
| Approval | Diff showed `return "old"` to `return "new"` before any write. After approval the file contained `return "new"` and a `patch_text` turn event was emitted |
| Git | `git_diff` was read-only. `git_commit` required approval and committed only `src/app.py` |
| Command | Output arrived through `on_output`. Timeout reason was `http_timeout` |
| MCP | The echo tool required approval and returned `ping`. A missing binary returned `action_exception` |
| Subagents | Four agents stopped with `resource_budget_exceeded` and wrote no evidence. A write inside a read-only child was refused. The parent code matched `aggregate_status` |
| Chat stream | `stream_chat_completion` without a configured model returned HTTP 502 and emitted no `tool_turn` |

The host path meets the handbook once a plan exists. The chat entry does not
reach that path until a model is configured.

## Records

`benchmarks/reports/agent-local-pass-rate.json`

| Field | Value |
| --- | --- |
| Runner | `scripted_oracle` |
| Tasks | 30 |
| Passed | 30 |
| Pass rate | 1.0 |
| Mainstream claim | false |

Stop reasons in that record are empty for a finished script, plus
`resource_budget_exceeded`, `permission_denied`, and `sovereignty_breach` for
the three tasks that are specified to stop. The pass rate means the scripted
steps matched their assertions. It is not a model solve rate.

`benchmarks/reports/swebench-lite-subset.json`

| Field | Value |
| --- | --- |
| Runner | `official_gold_patch` |
| Loaded | 5 |
| Executed | 4 |
| Passed | 4 |
| Blocked | 1 (`astropy__astropy-12907`, `install_failed`) |
| Pass rate | 1.0 of the four that ran |
| Mainstream claim | false |

The four passing instances are `django__django-11099`,
`sympy__sympy-20590`, `pytest-dev__pytest-5692`, and
`sphinx-doc__sphinx-10325`. Each failed its `FAIL_TO_PASS` tests before the
published patch and passed after it. OneCode did not write those patches.

## Verification that was run

Targeted unit tests for the touched modules passed while the phases were
built. The workflow above was run once against a temporary workspace. The
full `scripts/verify.sh` suite was not re-run after the combined tree.

## Still open

- No model was called, so chat streaming from a live planning turn is unmeasured.
- The thirty-task pass rate is an oracle record.
- Astropy 4.3 did not compile in this environment, so that public instance has no test result.
- `production_ready` remains false without a Docker daemon and `ONECODE_API_TOKEN`.
- Whole-tree mypy is not enabled.
- v0.8.0 is still a local kernel, not a general coding-agent product.
