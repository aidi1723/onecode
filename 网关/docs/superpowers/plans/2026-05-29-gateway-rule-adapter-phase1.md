# Gateway Rule Adapter Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a non-invasive `gateway_rule` evidence envelope to the gateway so existing Claude Code / Codex-compatible flows are mapped into the approved Yin-Yang, Four Symbols, Eight Trigrams, Five Elements, and 64-hexagram rule surface.

**Architecture:** Create a pure `gateway_rule_adapter.py` that converts existing gateway metadata, preflight/build-mode evidence, or status summaries into a 6-bit rule envelope. Attach this envelope to existing metadata and compact result surfaces without changing tool filtering, dispatch, request forwarding, Build Mode execution, or persistence semantics.

**Tech Stack:** Python 3 standard library, `unittest`, existing `agent_skill_dictionary` modules.

---

## File Structure

- Create `agent_skill_dictionary/gateway_rule_adapter.py`
  - Owns 6-bit bit derivation, transition mapping, element relation, entropy/polarity aggregation, and envelope construction.
  - Has no model calls, file writes, network calls, or tool execution.
- Create `tests/test_gateway_rule_adapter.py`
  - Covers the adapter directly with deterministic rule cases.
- Modify `agent_skill_dictionary/gateway_core.py`
  - Attach `gateway_rule` to `rewrite_chat_completion_request()` and `rewrite_anthropic_messages_request()` metadata.
- Modify `agent_skill_dictionary/gateway_plan.py`
  - Attach `gateway_rule` to `resolve_execution_plan()` output.
- Modify `agent_skill_dictionary/gateway_server.py`
  - Refresh `gateway_rule` after Build Mode metadata gates have been applied.
  - Attach per-result `gateway_rule` in `_compact_build_mode_results()`.
- Modify focused gateway tests only where new metadata is asserted.

## Task 1: Pure Gateway Rule Adapter

**Files:**
- Create: `agent_skill_dictionary/gateway_rule_adapter.py`
- Test: `tests/test_gateway_rule_adapter.py`

- [ ] **Step 1: Write failing adapter tests**

Add `tests/test_gateway_rule_adapter.py`:

```python
import unittest

from agent_skill_dictionary.gateway_rule_adapter import (
    aggregate_gateway_statuses,
    build_gateway_rule,
)


class GatewayRuleAdapterTest(unittest.TestCase):
    def test_all_true_evidence_maps_to_pure_yang_continue(self):
        rule = build_gateway_rule(
            {
                "sovereignty": True,
                "upstream": True,
                "policy": True,
                "artifact": True,
                "execution": True,
                "time": True,
            }
        )

        self.assertEqual(rule["gateway_status_code"], 63)
        self.assertEqual(rule["gateway_status_binary"], "111111")
        self.assertEqual(rule["outer_trigram"], "111")
        self.assertEqual(rule["inner_trigram"], "111")
        self.assertEqual(rule["polarity_index"], 1.0)
        self.assertEqual(rule["transition_action"], "cooldown")
        self.assertEqual(rule["transition_reason"], "yang_overload_cooldown")
        self.assertEqual(rule["dispatch_decision"], "continue")

    def test_sovereignty_breach_maps_to_fire_halt_stop(self):
        rule = build_gateway_rule({"event": "sovereignty_breach"})

        self.assertEqual(rule["gateway_status_code"], 48)
        self.assertEqual(rule["gateway_status_binary"], "110000")
        self.assertEqual(rule["outer_trigram_name"], "LI")
        self.assertEqual(rule["inner_trigram_name"], "KUN")
        self.assertEqual(rule["transition_action"], "halt")
        self.assertEqual(rule["transition_reason"], "sovereignty_fire_boundary")
        self.assertEqual(rule["dispatch_decision"], "stop")

    def test_upstream_timeout_maps_to_checkpoint_stop(self):
        rule = build_gateway_rule({"event": "upstream_timeout"})

        self.assertEqual(rule["gateway_status_code"], 17)
        self.assertEqual(rule["gateway_status_binary"], "010001")
        self.assertEqual(rule["outer_trigram_name"], "KAN")
        self.assertEqual(rule["inner_trigram_name"], "ZHEN")
        self.assertEqual(rule["transition_action"], "checkpoint")
        self.assertEqual(rule["transition_reason"], "network_water_preserves_resume_seed")
        self.assertEqual(rule["dispatch_decision"], "stop")

    def test_policy_gap_maps_to_discover_stop(self):
        rule = build_gateway_rule({"event": "policy_gap"})

        self.assertEqual(rule["gateway_status_code"], 0)
        self.assertEqual(rule["transition_action"], "discover")
        self.assertEqual(rule["transition_reason"], "rule_gap_discovery")
        self.assertEqual(rule["dispatch_decision"], "stop")

    def test_entropy_aggregation_is_polarity_aware(self):
        success = aggregate_gateway_statuses([63, 63])
        failure = aggregate_gateway_statuses([0, 0])

        self.assertEqual(success["decision"], "accept_positive_polarity")
        self.assertEqual(success["gateway_status_code"], 63)
        self.assertEqual(success["dispatch_decision"], "continue")
        self.assertEqual(failure["decision"], "rollback_negative_polarity")
        self.assertEqual(failure["gateway_status_code"], 17)
        self.assertEqual(failure["reason"], "entropy_negative_polarity_rollback")
        self.assertEqual(failure["dispatch_decision"], "stop")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_gateway_rule_adapter -v
```

Expected: failure because `agent_skill_dictionary.gateway_rule_adapter` does not exist.

- [ ] **Step 3: Implement the pure adapter**

Create `agent_skill_dictionary/gateway_rule_adapter.py` with:

```python
from __future__ import annotations

from math import log2
from typing import Any


TRIGRAMS = {
    0: ("KUN", "earth"),
    1: ("ZHEN", "wood"),
    2: ("KAN", "water"),
    3: ("DUI", "metal"),
    4: ("GEN", "earth"),
    5: ("XUN", "wood"),
    6: ("LI", "fire"),
    7: ("QIAN", "metal"),
}

GENERATES = {
    "water": "wood",
    "wood": "fire",
    "fire": "earth",
    "earth": "metal",
    "metal": "water",
}
CONTROLS = {
    "water": "fire",
    "fire": "metal",
    "metal": "wood",
    "wood": "earth",
    "earth": "water",
}
STOP_ACTIONS = {"halt", "checkpoint", "discover"}
ROLLBACK_STATUS = 17


def build_gateway_rule(source: dict[str, Any] | None = None) -> dict[str, Any]:
    source = source or {}
    status_code = _status_code_from_source(source)
    outer = (status_code >> 3) & 0b111
    inner = status_code & 0b111
    action, reason = _transition(status_code, source)
    dispatch = "stop" if action in STOP_ACTIONS else "continue"
    return _envelope(
        status_code=status_code,
        action=action,
        reason=reason,
        dispatch_decision=dispatch,
        evidence_required=source.get("evidence_required") if isinstance(source.get("evidence_required"), list) else [],
        evidence_collected=source.get("evidence_collected") if isinstance(source.get("evidence_collected"), dict) else {},
        source=source,
        outer=outer,
        inner=inner,
    )


def aggregate_gateway_statuses(status_codes: list[int], entropy_threshold: float = 0.5) -> dict[str, Any]:
    if not status_codes:
        rule = build_gateway_rule({"event": "policy_gap"})
        return {
            "decision": "discover_empty_statuses",
            "gateway_status_code": rule["gateway_status_code"],
            "gateway_status_binary": rule["gateway_status_binary"],
            "entropy": 0.0,
            "polarity_index": rule["polarity_index"],
            "reason": rule["transition_reason"],
            "dispatch_decision": rule["dispatch_decision"],
        }
    entropy = _global_entropy(status_codes)
    average_polarity = sum(_polarity(code) for code in status_codes) / len(status_codes)
    if entropy < entropy_threshold and average_polarity < 0:
        rule = build_gateway_rule({"status_code": ROLLBACK_STATUS, "reason": "entropy_negative_polarity_rollback"})
        decision = "rollback_negative_polarity"
    elif entropy < entropy_threshold and average_polarity > 0:
        rule = build_gateway_rule({"status_code": max(status_codes), "reason": "accept_positive_polarity"})
        decision = "accept_positive_polarity"
    else:
        rule = build_gateway_rule({"status_code": _collapse_statuses(status_codes), "reason": "accept_entropy_balanced"})
        decision = "accept_entropy_balanced"
    return {
        "decision": decision,
        "gateway_status_code": rule["gateway_status_code"],
        "gateway_status_binary": rule["gateway_status_binary"],
        "entropy": entropy,
        "polarity_index": average_polarity,
        "reason": rule["transition_reason"],
        "dispatch_decision": rule["dispatch_decision"],
    }
```

Then include the helper functions described by the tests:

```python
def _status_code_from_source(source: dict[str, Any]) -> int:
    if isinstance(source.get("status_code"), int):
        return int(source["status_code"]) & 0b111111
    event = str(source.get("event") or "")
    if event in {"sovereignty_breach", "preflight_breach", "tool_violation"}:
        return 48
    if event in {"upstream_timeout", "http_timeout", "stream_timeout"}:
        return 17
    if event in {"policy_gap", "unknown", "unmapped"}:
        return 0
    bits = [
        _bit(source, "sovereignty", True),
        _bit(source, "upstream", True),
        _bit(source, "policy", True),
        _bit(source, "artifact", True),
        _bit(source, "execution", True),
        _bit(source, "time", True),
    ]
    status = 0
    for bit in bits:
        status = (status << 1) | bit
    return status


def _bit(source: dict[str, Any], key: str, default: bool) -> int:
    value = source.get(key, default)
    return 1 if bool(value) else 0


def _transition(status_code: int, source: dict[str, Any]) -> tuple[str, str]:
    explicit_reason = source.get("reason")
    if explicit_reason == "entropy_negative_polarity_rollback":
        return "checkpoint", "entropy_negative_polarity_rollback"
    if explicit_reason == "accept_positive_polarity":
        return "cooldown", "accept_positive_polarity"
    if status_code == 0:
        return "discover", "rule_gap_discovery"
    outer = (status_code >> 3) & 0b111
    inner = status_code & 0b111
    if outer == 6:
        return "halt", "sovereignty_fire_boundary"
    if status_code == 17:
        return "checkpoint", "network_water_preserves_resume_seed"
    polarity = _polarity(status_code)
    if polarity >= 1.0:
        return "cooldown", "yang_overload_cooldown"
    if polarity <= -1.0:
        return "activate", "yin_stagnation_activate"
    relation = _element_relation(outer, inner)
    if relation == "generates":
        return "accelerate", "element_generation_accelerates"
    if relation == "controls":
        return "moderate", "element_control_moderates"
    return "continue", "balanced_continue"


def _envelope(
    *,
    status_code: int,
    action: str,
    reason: str,
    dispatch_decision: str,
    evidence_required: list[Any],
    evidence_collected: dict[str, Any],
    source: dict[str, Any],
    outer: int,
    inner: int,
) -> dict[str, Any]:
    outer_name, outer_element = TRIGRAMS[outer]
    inner_name, inner_element = TRIGRAMS[inner]
    binary = format(status_code, "06b")
    return {
        "gateway_status_code": status_code,
        "gateway_status_binary": binary,
        "outer_trigram": binary[:3],
        "inner_trigram": binary[3:],
        "outer_trigram_name": outer_name,
        "inner_trigram_name": inner_name,
        "outer_plane": "environment",
        "inner_plane": "asset",
        "polarity_index": _polarity(status_code),
        "four_symbols": [binary[0:2], binary[2:4], binary[4:6]],
        "element_relation": _element_relation(outer, inner),
        "outer_element": outer_element,
        "inner_element": inner_element,
        "transition_action": action,
        "transition_reason": reason,
        "dispatch_decision": dispatch_decision,
        "evidence_required": evidence_required,
        "evidence_collected": evidence_collected,
        "source": str(source.get("source") or "gateway_rule_adapter"),
    }


def _polarity(status_code: int) -> float:
    return (int(status_code).bit_count() - 3) / 3


def _element_relation(outer: int, inner: int) -> str:
    outer_element = TRIGRAMS[outer][1]
    inner_element = TRIGRAMS[inner][1]
    if outer_element == inner_element:
        return "same"
    if GENERATES.get(outer_element) == inner_element:
        return "generates"
    if CONTROLS.get(outer_element) == inner_element:
        return "controls"
    return "neutral"


def _global_entropy(status_codes: list[int]) -> float:
    total_bits = len(status_codes) * 6
    ones = sum((code & 0b111111).bit_count() for code in status_codes)
    p1 = ones / total_bits
    p0 = 1.0 - p1
    entropy = -sum(p * log2(p) for p in (p0, p1) if p > 0)
    return entropy + 0.0


def _collapse_statuses(status_codes: list[int]) -> int:
    status = 0
    for code in status_codes:
        status |= int(code) & 0b111111
    return status
```

- [ ] **Step 4: Run adapter tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_gateway_rule_adapter -v
```

Expected: `OK`.

## Task 2: Attach Rule Envelope To Gateway Metadata

**Files:**
- Modify: `agent_skill_dictionary/gateway_core.py`
- Modify: `agent_skill_dictionary/gateway_plan.py`
- Test: `tests/test_gateway_core.py`
- Test: `tests/test_gateway_plan.py`

- [ ] **Step 1: Write failing metadata tests**

Add assertions to `GatewayCoreTest.test_rewrite_chat_request_injects_active_rule_and_locks_temperature`:

```python
self.assertEqual(metadata["gateway_rule"]["gateway_status_code"], 63)
self.assertEqual(metadata["gateway_rule"]["transition_action"], "cooldown")
self.assertEqual(metadata["gateway_rule"]["dispatch_decision"], "continue")
```

Add assertions to `GatewayCoreTest.test_rewrite_anthropic_messages_filters_tools_and_injects_system`:

```python
self.assertEqual(metadata["gateway_rule"]["gateway_status_binary"], "111111")
self.assertEqual(metadata["gateway_rule"]["outer_plane"], "environment")
self.assertEqual(metadata["gateway_rule"]["inner_plane"], "asset")
```

Add assertions to `GatewayPlanTest.test_resolve_execution_plan_for_fix_and_test`:

```python
self.assertEqual(plan["gateway_rule"]["gateway_status_code"], 63)
self.assertEqual(plan["gateway_rule"]["dispatch_decision"], "continue")
```

- [ ] **Step 2: Run focused tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_gateway_core tests.test_gateway_plan -v
```

Expected: failures for missing `gateway_rule`.

- [ ] **Step 3: Attach `gateway_rule` in core and plan**

In `agent_skill_dictionary/gateway_core.py`, import:

```python
from .gateway_rule_adapter import build_gateway_rule
```

Add `"gateway_rule": build_gateway_rule({"source": "gateway_core", "evidence_required": []})` to both metadata dictionaries built by `rewrite_chat_completion_request()` and `rewrite_anthropic_messages_request()`.

In `agent_skill_dictionary/gateway_plan.py`, import:

```python
from .gateway_rule_adapter import build_gateway_rule
```

Add `"gateway_rule": build_gateway_rule({"source": "gateway_plan", "evidence_required": raw["verification"].get("evidence", []) if isinstance(raw.get("verification"), dict) else []})` to the returned plan.

- [ ] **Step 4: Run focused tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_gateway_core tests.test_gateway_plan -v
```

Expected: `OK`.

## Task 3: Attach Rule Envelope After Build Mode Gates And Compact Results

**Files:**
- Modify: `agent_skill_dictionary/gateway_server.py`
- Test: `tests/test_gateway_server_import.py`

- [ ] **Step 1: Write failing server metadata tests**

Add assertions to an existing `chat_completions_payload` metadata test:

```python
self.assertIn("gateway_rule", result["metadata"])
self.assertIn("gateway_status_code", result["metadata"]["gateway_rule"])
self.assertEqual(result["metadata"]["gateway_rule"]["outer_plane"], "environment")
```

Add a focused test for compact Build Mode results:

```python
def test_compact_build_mode_results_adds_gateway_rule(self):
    compacted = gateway_server._compact_build_mode_results(
        [
            {
                "status": "completed",
                "hexagram": "111",
                "next_hexagram": "000",
                "evidence": {"changed_files": ["mesh.py"], "exit_code": 0},
            }
        ]
    )

    self.assertEqual(compacted[0]["gateway_rule"]["gateway_status_code"], 63)
    self.assertEqual(compacted[0]["gateway_rule"]["dispatch_decision"], "continue")
```

- [ ] **Step 2: Run focused server tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_gateway_server_import -v
```

Expected: failures for missing `gateway_rule`.

- [ ] **Step 3: Add gateway server helpers**

In `agent_skill_dictionary/gateway_server.py`, import:

```python
from .gateway_rule_adapter import build_gateway_rule
```

Add helper:

```python
def _attach_gateway_rule_metadata(metadata: dict[str, Any], source: str = "gateway_server") -> dict[str, Any]:
    updated = dict(metadata)
    event = _gateway_rule_event_from_metadata(updated)
    updated["gateway_rule"] = build_gateway_rule(
        {
            "source": source,
            "event": event,
            "evidence_required": updated.get("gateway_rule", {}).get("evidence_required", []),
        }
    )
    return updated
```

Add helper:

```python
def _gateway_rule_event_from_metadata(metadata: dict[str, Any]) -> str | None:
    if metadata.get("build_mode_sovereignty"):
        return "sovereignty_breach"
    if metadata.get("oneword_build_mode", {}).get("failure_gate_locked"):
        return "policy_gap"
    return None
```

Call `_attach_gateway_rule_metadata(metadata, "...")` immediately before returning from:

- `chat_completions_payload()`
- `anthropic_messages_payload()`
- `openai_responses_payload()`

In `_compact_build_mode_results()`, add:

```python
"gateway_rule": build_gateway_rule(_gateway_rule_source_from_build_mode_result(result)),
```

Add helper:

```python
def _gateway_rule_source_from_build_mode_result(result: dict[str, Any]) -> dict[str, Any]:
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    if result.get("status") == "completed":
        return {
            "source": "build_mode_result",
            "sovereignty": True,
            "upstream": True,
            "policy": True,
            "artifact": True,
            "execution": True,
            "time": True,
            "evidence_collected": evidence,
        }
    if result.get("status") in {"blocked", "rejected"}:
        return {"source": "build_mode_result", "event": "sovereignty_breach", "evidence_collected": evidence}
    return {
        "source": "build_mode_result",
        "sovereignty": True,
        "upstream": True,
        "policy": True,
        "artifact": bool(evidence),
        "execution": False,
        "time": True,
        "evidence_collected": evidence,
    }
```

- [ ] **Step 4: Run focused server tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_gateway_server_import -v
```

Expected: `OK` or existing dependency skips only.

## Task 4: Regression Sweep

**Files:**
- No new files unless regressions require a targeted fix.

- [ ] **Step 1: Run gateway rule adapter and core suite**

Run:

```bash
python3 -m unittest tests.test_gateway_rule_adapter tests.test_gateway_core tests.test_gateway_plan tests.test_minimal_gateway_mvp -v
```

Expected: `OK`.

- [ ] **Step 2: Run migrated gateway suites**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_gateway*.py' -v
```

Expected: all runnable tests pass; FastAPI TestClient-dependent tests may skip if dependency is missing.

- [ ] **Step 3: Run Build Mode suites**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_build_mode*.py' -v
```

Expected: `OK`.

- [ ] **Step 4: Inspect diff**

Run:

```bash
git diff -- agent_skill_dictionary/gateway_rule_adapter.py agent_skill_dictionary/gateway_core.py agent_skill_dictionary/gateway_plan.py agent_skill_dictionary/gateway_server.py tests/test_gateway_rule_adapter.py tests/test_gateway_core.py tests/test_gateway_plan.py tests/test_gateway_server_import.py docs/superpowers/plans/2026-05-29-gateway-rule-adapter-phase1.md
```

Expected: only Phase 1 adapter, metadata, compact-result tests, and plan changes.

## Self-Review

- Spec coverage: Phase 1 design requirements are covered by Task 1 through Task 4.
- Scope: The plan adds evidence metadata only. It does not change request forwarding, policy filtering, execution behavior, model calls, persistence format, or OneCode kernel code.
- Type consistency: `gateway_rule` is always a dict envelope. Status fields use `gateway_status_*` names to avoid collision with existing `hexagram` and `oneword_build_mode` fields.
