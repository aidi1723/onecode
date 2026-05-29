# Gateway Rule State Persistence Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist the gateway rule envelope into Build Mode state files so resumed sessions can audit both per-step and global 6-bit rule state.

**Architecture:** Reuse the Phase 1 `gateway_rule_adapter` and keep all behavior non-invasive. `_compact_build_mode_results()` already records per-result `gateway_rule`; Phase 2 adds a top-level `gateway_rule` aggregation to `_persist_build_mode_state()` and `_persist_expert_handoff_state()` without changing routing, permissions, execution, or recovery decisions.

**Tech Stack:** Python 3 standard library, `unittest`, existing `gateway_server` state persistence helpers.

---

## File Structure

- Modify `agent_skill_dictionary/gateway_rule_adapter.py`
  - Expose an envelope-shaped aggregation helper for persisted state.
- Modify `agent_skill_dictionary/gateway_server.py`
  - Persist top-level `gateway_rule` in Build Mode state files.
  - Persist top-level `gateway_rule` in expert handoff state files.
- Modify `tests/test_gateway_server_import.py`
  - Add red/green tests for state-file-level rule evidence.

## Task 1: Persist Top-Level Build Mode State Rule

**Files:**
- Modify: `tests/test_gateway_server_import.py`
- Modify: `agent_skill_dictionary/gateway_rule_adapter.py`
- Modify: `agent_skill_dictionary/gateway_server.py`

- [ ] **Step 1: Write failing test**

Add assertions to `GatewayServerImportTest.test_build_tool_payload_persists_failed_verification_state`:

```python
self.assertEqual(state["gateway_rule"]["aggregation_decision"], "accept_entropy_balanced")
self.assertIn("gateway_status_code", state["gateway_rule"])
self.assertEqual(state["gateway_rule"]["source"], "build_mode_state")
```

Add assertions to `GatewayServerImportTest.test_build_tool_payload_timeout_triggers_secure_b2b_expert_handoff`:

```python
self.assertEqual(state["gateway_rule"]["gateway_status_code"], 63)
self.assertEqual(state["gateway_rule"]["source"], "expert_handoff_state")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest \
  tests.test_gateway_server_import.GatewayServerImportTest.test_build_tool_payload_persists_failed_verification_state \
  tests.test_gateway_server_import.GatewayServerImportTest.test_build_tool_payload_timeout_triggers_secure_b2b_expert_handoff \
  -v
```

Expected: failures for missing top-level `gateway_rule`.

- [ ] **Step 3: Add aggregation helper**

In `agent_skill_dictionary/gateway_rule_adapter.py`, add:

```python
def aggregate_gateway_rule_envelope(status_codes: list[int], source: str = "gateway_state") -> dict[str, Any]:
    summary = aggregate_gateway_statuses(status_codes)
    rule = build_gateway_rule(
        {
            "status_code": int(summary["gateway_status_code"]),
            "reason": str(summary["reason"]),
            "source": source,
        }
    )
    return {
        **rule,
        "source": source,
        "aggregation_decision": summary["decision"],
        "global_entropy": summary["entropy"],
        "global_polarity_index": summary["polarity_index"],
        "aggregation_reason": summary["reason"],
    }
```

- [ ] **Step 4: Persist state-level rule**

In `agent_skill_dictionary/gateway_server.py`, import `aggregate_gateway_rule_envelope` beside `build_gateway_rule`.

Add helper:

```python
def _gateway_rule_for_compact_results(results: list[dict[str, Any]], source: str) -> dict[str, Any]:
    status_codes = []
    for result in results:
        rule = result.get("gateway_rule") if isinstance(result.get("gateway_rule"), dict) else {}
        code = rule.get("gateway_status_code")
        if isinstance(code, int):
            status_codes.append(code)
    return aggregate_gateway_rule_envelope(status_codes, source)
```

In `_persist_build_mode_state()`, after `compact_results = _compact_build_mode_results(results)`, include:

```python
"gateway_rule": _gateway_rule_for_compact_results(compact_results, "build_mode_state"),
```

In `_persist_expert_handoff_state()`, add `gateway_rule` to `compact_result` with:

```python
"gateway_rule": build_gateway_rule({"source": "expert_handoff_result"}),
```

Then include:

```python
"gateway_rule": _gateway_rule_for_compact_results([*results, compact_result], "expert_handoff_state"),
```

- [ ] **Step 5: Run focused tests and verify they pass**

Run:

```bash
python3 -m unittest \
  tests.test_gateway_server_import.GatewayServerImportTest.test_build_tool_payload_persists_failed_verification_state \
  tests.test_gateway_server_import.GatewayServerImportTest.test_build_tool_payload_timeout_triggers_secure_b2b_expert_handoff \
  -v
```

Expected: `OK`.

## Task 2: Regression Sweep

**Files:**
- No extra files unless a regression requires a small fix.

- [ ] **Step 1: Run gateway suites**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_gateway*.py' -v
```

Expected: `OK`; route tests may skip when FastAPI TestClient is unavailable.

- [ ] **Step 2: Run Build Mode suites**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_build_mode*.py' -v
```

Expected: `OK`.

- [ ] **Step 3: Run diff check**

Run:

```bash
git diff --check
```

Expected: no output and exit code 0.

## Self-Review

- Scope: This phase only persists rule evidence; it does not change runtime dispatch.
- Coverage: Build Mode state and expert handoff state both get top-level rule evidence.
- Compatibility: Existing `results[*].gateway_rule` remains intact from Phase 1.
