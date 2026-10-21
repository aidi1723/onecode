# Long-task plan, 2026-10-21

This plan is not implemented. It does not change the kernel. `claims_mainstream_parity` stays false. Version stays 1.0.0. Tags stay where they are.

The current product can finish a bounded task: read the workspace, write one complete file, approve it, and run the sandbox check. A long mainstream task is a different job. The model keeps the same run open, reads the new test output, edits again, and repeats until the check passes or the budget ends. OneCode does not do that inside one run.

## What stays sealed until a later decision

- No new hexagram. `classify_outcome` is unchanged.
- One implementation repair inside a single run. A second failed check is `verifier_failed`, Li/Kun (40), delivery blocked.
- A patch that does not match stays `patch_search_not_found`. There is no fuzzy apply.
- The sandbox stays `--network none`.
- The agent cycle default stays 8 turns and 2 tools a turn. Read-only subagents stay at 3.
- LibreChat's own agents, code workspaces, programmatic tools, background tools, and scheduled chats stay off.
- User-Agent stays `onecode/0.8`.

## Reliable shape for a long task

The shell is the conductor. Each step is a new kernel entry, not a longer loop inside one entry.

1. A read-only survey lists the files the task needs. A bad tool parameter is a search miss. It does not cancel the task. A path escape still stops.
2. The shell asks for one complete asset for one missing or named file. The human approves that plan. The sandbox check runs when the named files for that step are present.
3. If the check fails, the existing one-patch repair is offered, with the implementation source and the verifier tail, and without a `tests/` path.
4. If that repair fails, or a patch does not match, the run stops at Li/Kun (40). The shell may then open a new entry whose plan is a complete asset for the same file. That is a new approval, not a second repair inside the stopped run.
5. When one file is done, the shell starts the next named file. An import of a module already on disk is accepted.
6. Dependencies are staged with `host_stage` only after approval. The sandbox does not gain a network.

This can carry a long task to completion as a sequence of short tasks. It still stops for approval at every write. It does not match an agent that edits unattended for dozens of steps.

## What this plan will not claim

A pass on the 30 scripted local tasks is not a mainstream score. A pass on a fee or schedule task with a preset test is not one either. Before anyone sets `claims_mainstream_parity` true, the operator has to name a public task set, run it on n100 through this shell path, and record each pass and each halt reason. That record is a later document. This plan does not authorize that flag.

## Rule changes that are out of scope

These would be required for an unattended long run. They are listed so the next decision is explicit. They are not approved by this document.

| Change | What it would touch |
| --- | --- |
| More than one repair inside one run | The second failure would no longer be an automatic Li/Kun (40) |
| Fuzzy or whole-file apply after `patch_search_not_found` | The exact-patch halt |
| Network inside the sandbox | `--network none` |
| A default turn cap above 8 | The cycle budget |
| Turning on LibreChat's own agent loop | Execution would leave the kernel |

Any one of those starts with a written decision, a failing test, and a fresh n100 run. None of them start from this close.
