# OneCode Maintenance Log - 2026-08-24

## Scope

Resume and complete an I Ching rule-vocabulary refactor in
`src/onecode/kernel/hexagram.py` and `src/onecode/kernel/recovery_policy.py`
that was left partially applied when the previous session was interrupted
by a power outage.

## Background

A new module `src/onecode/kernel/rule_constants.py` introduces `StrEnum`
types (`TransitionAction`, `TransitionReason`, `ElementModulation`) plus
`ELEMENT_DYNAMICS_MODULATION_TABLE`, centralizing rule-engine vocabulary
that was previously hardcoded as bare string literals scattered across
`hexagram.py`. `StrEnum` members compare equal to their plain string
value, so this is a pure refactor: no externally observed behavior change.

## Work Resumed

On picking up the interrupted session, most of `hexagram.py` and
`recovery_policy.py` had already been converted to use the new enums, but
four call sites were missed:

- `RUNTIME_CONTROL_MODULATION_POLICY` dict keys (`hexagram.py:149-154`) —
  converted from string literals (`"hard_control"`, `"quench"`, `"prune"`,
  `"dam"`, `"break_ground"`, `"normal"`) to `ElementModulation` members.
- The corresponding lookup default at `hexagram.py:632`
  (`RUNTIME_CONTROL_MODULATION_POLICY["normal"]` →
  `RUNTIME_CONTROL_MODULATION_POLICY[ElementModulation.NORMAL]`).
- `action_penalties` dict keys inside `lyapunov_energy`
  (`hexagram.py:1098-1108`) — converted to `TransitionAction` members.
- A comparison in `cross_cutting_profile`
  (`hexagram.py:1157`): `dynamics["modulation"] == "recovery_seed" and
  transition.action == "checkpoint"` → now compares against
  `ElementModulation.RECOVERY_SEED` and `TransitionAction.CHECKPOINT`.

`TRIGRAM_VIRTUES` (`hexagram.py:40-49`) was intentionally left untouched —
its second-position strings (`"activate"`, `"checkpoint"`, etc.) describe
trigram *virtues*, a different vocabulary that happens to share two string
values with `TransitionAction`. Converting it would conflate two distinct
concepts, so it stays as plain strings.

## Verification

- `grep` swept `hexagram.py` and `recovery_policy.py` for every remaining
  rule-vocabulary string literal (action/reason/modulation names) — only
  the intentional `TRIGRAM_VIRTUES` entries remain.
- `.venv/bin/python -m unittest discover -s tests`: 907 tests passed,
  1 environment-only skip (unchanged from before the fix).
- `scripts/verify-core.sh`: 234 core tests passed, `onecode doctor`
  returned `status: ok` across all checks (write_text, resume_skip,
  sovereignty_breach, http_timeout, project_context, runtime_config,
  skill_context, recovery_policy).
- `scripts/check_source_quality.py src`: `source quality ok`.

No behavior changed — `StrEnum` members are interchangeable with their
string values in comparisons, dict keys, and JSON serialization (confirmed
by `doctor`'s JSON output still showing plain strings like
`"iching_transition_action": "cooldown"`).

## Status

Refactor complete. `hexagram.py` and `recovery_policy.py` now consistently
reference `TransitionAction` / `TransitionReason` / `ElementModulation`
from `rule_constants.py` instead of ad hoc string literals, with the one
intentional exception noted above. Ready to commit.
