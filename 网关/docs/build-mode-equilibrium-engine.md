# Build Mode Equilibrium Engine

`agent_skill_dictionary.build_mode_equilibrium` owns the generic Build Mode balance rules. The gateway must treat it as the single decision layer for long-task lifecycle routing.

## Inputs

- `ArtifactGap`: physical workspace evidence for required project assets.
- persisted Build Mode state: latest tool result, failure counter, repair card, and failure summary.
- optional repair target hint inferred from state text and current files.

## Outputs

`EquilibriumDecision` returns the only values the gateway should apply to the next request:

- `hexagram`: next control state.
- `source`: metadata source marker.
- `shadow_action`: physical execution posture.
- `instruction`: system instruction injected into the model context.
- `tool_name`: canonical tool to expose, or none for archive lock.
- `target_path`: optional path enum for scoped write repair.
- `metadata_key` and `metadata`: stable report/debug metadata.
- `force_empty_tools`: true only for archive/lockdown posture.
- `balance`: the measured and corrected yin/yang state for the turn.

`BalanceSnapshot` makes the control law observable:

- `total_gaps`: missing required artifacts, the primary yin resistance input.
- `allowed_tool_names`: exposed yang channels after or before correction.
- `yin_resistance`: normalized gap/safety resistance.
- `yang_bandwidth`: normalized tool freedom.
- `mode`: observed, incremental create, canonical verify, repair, archive, or failure lockdown.
- `violations`: detected imbalance signatures, such as missing write channel or overexposed tools.

## Universal Rules

1. **Incremental Create Gate**

   If required artifacts are missing, the decision is always `111` with a single `write_file` tool. The target path is the first missing artifact. Historical `001` verify state cannot override a nonzero gap.

2. **Canonical Verify Gate**

   If all required artifacts exist and the latest state is not a failed verification and not a successful return, the decision is `001` with a single `run_pytest` tool. If the client omitted that schema, the gateway injects it.

3. **Repair Gate**

   If all artifacts exist and the latest verification result failed, the decision is `111` with a single `write_file` tool. If a repair target is known, the tool schema restricts `path` to that file. After a successful repair write, the next decision returns to verify instead of looping on repair.

4. **Archive Gate**

   If the latest verification passed, the decision is `000`, tools are removed, and the model may only summarize the locked asset state. Final manifest/archive work remains handled by the existing tool executor path.

5. **Failure Lockdown**

   If the failure counter trips, gateway metadata must still report a `build_mode_equilibrium` snapshot. The state is `100`, tool bandwidth is zero, and the violation reason is `consecutive_failures_exceeded`. The gateway also emits `build_mode_expert_handoff` evidence for human-approved expert intervention. This keeps emergency exit behavior under the same balance law as ordinary turns without pretending the task has archived successfully.

6. **Expert Handoff**

   After `100`, automated model writes remain revoked. A human-approved expert seed may run only through the explicit handoff path with `ONEWORD_EXPERT_HANDOFF_TOKEN`. The seed still writes through the scoped writer, must stay inside the `RequiredArtifactPlan`, and must pass guarded runtime verification before `000` archive finalization.

## Gateway Contract

Every Build Mode request rewrite should expose one `build_mode_equilibrium` metadata object with:

- chosen `hexagram`
- decision `source`
- `shadow_action`
- chosen `tool_name`
- optional `target_path`
- `balance`

Downstream reports and A/B harnesses should prefer this metadata over ad hoc gateway fields when explaining why a turn wrote, tested, repaired, halted, or archived.

## Non-Goals

- This module does not execute tools.
- This module does not parse model output.
- This module does not score code quality.
- This module does not contain project-specific generation logic.

The gateway remains responsible for request protocol conversion, schema injection, state persistence, and response execution. The executor remains responsible for physical evidence.
