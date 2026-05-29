# Gateway Caveman Compression Layer Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an internal-only Caveman-style compression layer for persisted gateway state summaries while preserving raw evidence and user-facing output.

**Architecture:** Create a pure `gateway_compression_adapter.py` that compresses prose summaries into terse internal evidence. Wire it only into Build Mode state persistence as `compressed_summary` and `compression_rule`; do not compress code, JSON, paths, hashes, tool schemas, raw result evidence, or final user responses.

**Tech Stack:** Python 3 standard library, `unittest`, existing `gateway_server` state persistence.

---

## File Structure

- Create `agent_skill_dictionary/gateway_compression_adapter.py`
  - Pure deterministic compression helper.
  - No model calls, no file writes, no network, no execution.
- Create `tests/test_gateway_compression_adapter.py`
  - Direct tests for protected token preservation and ratio metadata.
- Modify `agent_skill_dictionary/gateway_server.py`
  - Add compressed summaries to Build Mode state files.
- Modify `tests/test_gateway_server_import.py`
  - Assert persisted state contains compressed internal summary while raw evidence remains.

## Task 1: Pure Compression Adapter

**Files:**
- Create: `agent_skill_dictionary/gateway_compression_adapter.py`
- Create: `tests/test_gateway_compression_adapter.py`

- [ ] **Step 1: Write failing adapter tests**

Add `tests/test_gateway_compression_adapter.py`:

```python
import unittest

from agent_skill_dictionary.gateway_compression_adapter import build_compression_record


class GatewayCompressionAdapterTest(unittest.TestCase):
    def test_compresses_internal_summary_and_preserves_paths_and_hashes(self):
        record = build_compression_record(
            "The system successfully wrote file app/main.py and preserved sha256 abcdef123456."
        )

        self.assertEqual(record["mode"], "internal_caveman")
        self.assertIn("app/main.py", record["compressed_summary"])
        self.assertIn("abcdef123456", record["compressed_summary"])
        self.assertLess(record["compressed_chars"], record["raw_chars"])
        self.assertGreater(record["compression_ratio"], 0.0)
        self.assertIn("app/main.py", record["preserved_tokens"])

    def test_empty_summary_returns_disabled_record(self):
        record = build_compression_record("")

        self.assertEqual(record["mode"], "off")
        self.assertEqual(record["compressed_summary"], "")
        self.assertEqual(record["compression_ratio"], 0.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_gateway_compression_adapter -v
```

Expected: import failure because the adapter does not exist.

- [ ] **Step 3: Implement adapter**

Create `agent_skill_dictionary/gateway_compression_adapter.py`:

```python
from __future__ import annotations

import re
from typing import Any


STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "please", "thank", "thanks", "you",
    "successfully", "system", "has", "have", "had", "is", "are", "was", "were",
    "to", "for", "with", "that", "this", "into", "from",
}
PROTECTED_RE = re.compile(r"([A-Za-z0-9_.\-/]+/[A-Za-z0-9_.\-/]+|[a-fA-F0-9]{12,}|[A-Za-z_][A-Za-z0-9_]*\([^)]*\))")


def build_compression_record(text: str, mode: str = "internal_caveman") -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {
            "mode": "off",
            "compressed_summary": "",
            "raw_chars": 0,
            "compressed_chars": 0,
            "compression_ratio": 0.0,
            "preserved_tokens": [],
            "compression_rule": "raw_empty_no_compression",
        }
    preserved = _preserved_tokens(raw)
    compressed = _compress(raw)
    return {
        "mode": mode,
        "compressed_summary": compressed,
        "raw_chars": len(raw),
        "compressed_chars": len(compressed),
        "compression_ratio": round(1 - (len(compressed) / len(raw)), 4) if raw else 0.0,
        "preserved_tokens": preserved,
        "compression_rule": "drop_stopwords_keep_paths_hashes_symbols",
    }
```

Then add:

```python
def _compress(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.strip())
    words = []
    for token in normalized.split(" "):
        stripped = token.strip()
        if not stripped:
            continue
        core = stripped.strip(".,;:!?()[]{}")
        if core.lower() in STOPWORDS:
            continue
        words.append(stripped)
    return " ".join(words)


def _preserved_tokens(text: str) -> list[str]:
    seen = []
    for match in PROTECTED_RE.findall(text):
        if match not in seen:
            seen.append(match)
    return seen
```

- [ ] **Step 4: Run adapter tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_gateway_compression_adapter -v
```

Expected: `OK`.

## Task 2: Persist Internal Compressed State Summary

**Files:**
- Modify: `agent_skill_dictionary/gateway_server.py`
- Modify: `tests/test_gateway_server_import.py`

- [ ] **Step 1: Write failing state persistence test**

Add assertions to `GatewayServerImportTest.test_build_tool_payload_persists_failed_verification_state`:

```python
self.assertIn("compressed_summary", state)
self.assertEqual(state["compression_rule"]["mode"], "internal_caveman")
self.assertIn("Build Mode Repair Card", state["repair_card"])
self.assertLessEqual(
    state["compression_rule"]["compressed_chars"],
    state["compression_rule"]["raw_chars"],
)
```

- [ ] **Step 2: Run focused test and verify it fails**

Run:

```bash
python3 -m unittest tests.test_gateway_server_import.GatewayServerImportTest.test_build_tool_payload_persists_failed_verification_state -v
```

Expected: missing `compressed_summary` or `compression_rule`.

- [ ] **Step 3: Persist compressed summary**

In `agent_skill_dictionary/gateway_server.py`, import:

```python
from .gateway_compression_adapter import build_compression_record
```

Add helper:

```python
def _build_state_compression_record(repair_card: str, compact_results: list[dict[str, Any]]) -> dict[str, Any]:
    if repair_card:
        return build_compression_record(repair_card)
    summaries = []
    for result in compact_results:
        value = result.get("failure_summary") or result.get("reason") or result.get("status")
        if isinstance(value, str) and value.strip():
            summaries.append(value.strip())
    return build_compression_record(" | ".join(summaries))
```

In `_persist_build_mode_state()`, after `repair_card = _latest_repair_card(...)`, compute:

```python
compression_record = _build_state_compression_record(repair_card, compact_results)
```

Add to `state`:

```python
"compressed_summary": compression_record["compressed_summary"],
"compression_rule": compression_record,
```

- [ ] **Step 4: Run focused test and verify it passes**

Run:

```bash
python3 -m unittest tests.test_gateway_server_import.GatewayServerImportTest.test_build_tool_payload_persists_failed_verification_state -v
```

Expected: `OK`.

## Task 3: Regression Sweep

- [ ] **Step 1: Run compression and gateway core tests**

Run:

```bash
python3 -m unittest tests.test_gateway_compression_adapter tests.test_gateway_rule_adapter tests.test_gateway_core tests.test_gateway_plan tests.test_minimal_gateway_mvp -v
```

Expected: `OK`.

- [ ] **Step 2: Run gateway suites**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_gateway*.py' -v
```

Expected: `OK`; route tests may skip when FastAPI TestClient is unavailable.

- [ ] **Step 3: Run Build Mode suites**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_build_mode*.py' -v
```

Expected: `OK`.

- [ ] **Step 4: Run diff check**

Run:

```bash
git diff --check
```

Expected: no output and exit code 0.

## Self-Review

- Scope: Compression is internal state evidence only.
- Safety: Raw evidence remains unchanged; compressed summary is additive.
- Product fit: Caveman is treated as Yin/Metal context pruning, not as user-facing brand voice.
