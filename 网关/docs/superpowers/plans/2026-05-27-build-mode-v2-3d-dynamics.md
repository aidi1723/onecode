# Build Mode V2 3D Dynamics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade Build Mode from a direct evidence-gated FSM into a 3-axis control system that prevents multi-axis state jumps, detects adversarial drift, dynamically shortens or extends failure gates, and prepares evidence for multi-node synchronization.

**Architecture:** Keep the existing V1 hexagram codes and tool executor behavior stable. Add small, testable modules beside the current Build Mode layer: a cube topology guard, a behavioral fingerprint auditor, an entropy-decay failure gate, and signed evidence envelopes with a local consensus-store abstraction. Wire them into `build_mode_fsm.py`, `build_mode_sandbox.py`, `build_mode_tool_executor.py`, and `gateway_server.py` only after each standalone unit is green.

**Tech Stack:** Python 3, dataclasses, pathlib, hashlib, hmac, json, difflib, unittest, existing Build Mode DTOs and gateway state persistence.

---

## 1. Design Boundaries

This plan implements the next control layer. It does not replace:

- Existing hexagram constants in `agent_skill_dictionary/build_mode_types.py`.
- Existing scoped writer and sandbox runner contracts.
- Existing `repair_card` context injection.
- Existing gateway auth and workspace root rules.

The "3D" model uses three concrete axes:

| Axis | Bit | Meaning |
| --- | --- | --- |
| `tool_axis` | first bit | tool/action bandwidth |
| `context_axis` | second bit | memory/context bandwidth |
| `boundary_axis` | third bit | host/sandbox boundary exposure |

Hard rule: a normal transition may change at most one bit at a time. Direct diagonal jumps must be decomposed into edge-walk waypoints unless explicitly marked as emergency halt.

## 2. File Structure

| File | Responsibility |
| --- | --- |
| `agent_skill_dictionary/build_mode_topology.py` | 3-bit coordinate helpers, Hamming distance, legal edge-walk paths. |
| `agent_skill_dictionary/build_mode_audit.py` | Text/tool intent fingerprinting and adversarial drift evidence. |
| `agent_skill_dictionary/build_mode_decay.py` | Failure-output similarity and dynamic retry threshold calculation. |
| `agent_skill_dictionary/build_mode_consensus.py` | Signed evidence envelope and local append-only node state store. |
| `agent_skill_dictionary/build_mode_types.py` | Add DTOs for topology, audit, decay, and evidence envelopes. |
| `agent_skill_dictionary/build_mode_fsm.py` | Add optional guarded transition API while keeping `next_hexagram()` backward compatible. |
| `agent_skill_dictionary/build_mode_sandbox.py` | Add failure fingerprint from compact pytest output. |
| `agent_skill_dictionary/gateway_server.py` | Persist audit/decay/envelope metadata when present. |

Tests:

| Test File | Coverage |
| --- | --- |
| `tests/test_build_mode_topology.py` | Edge-only transitions and waypoint generation. |
| `tests/test_build_mode_audit.py` | Mismatch detection between text intent and tool call. |
| `tests/test_build_mode_decay.py` | Similar traceback detection and dynamic failure threshold. |
| `tests/test_build_mode_consensus.py` | HMAC-signed evidence envelope and local node-state append/read. |
| `tests/test_build_mode_fsm.py` | Guarded transition emits waypoints for diagonal jumps. |
| `tests/test_gateway_server_import.py` | Persisted state includes audit/decay metadata when tool results provide it. |

## 3. Task 1: Add 3D Topology DTOs And Helpers

**Files:**
- Modify: `agent_skill_dictionary/build_mode_types.py`
- Create: `agent_skill_dictionary/build_mode_topology.py`
- Create: `tests/test_build_mode_topology.py`

- [ ] **Step 1: Write failing topology tests**

Create `tests/test_build_mode_topology.py`:

```python
import unittest

from agent_skill_dictionary.build_mode_topology import (
    edge_walk_path,
    hamming_distance,
    is_edge_transition,
    transition_axes,
)


class BuildModeTopologyTest(unittest.TestCase):
    def test_hamming_distance_counts_changed_axes(self):
        self.assertEqual(hamming_distance("111", "011"), 1)
        self.assertEqual(hamming_distance("111", "001"), 2)
        self.assertEqual(hamming_distance("111", "000"), 3)

    def test_edge_transition_allows_only_one_axis_change(self):
        self.assertTrue(is_edge_transition("111", "011"))
        self.assertFalse(is_edge_transition("111", "001"))

    def test_transition_axes_names_changed_bits(self):
        self.assertEqual(transition_axes("111", "001"), ("tool_axis", "context_axis"))

    def test_edge_walk_path_decomposes_diagonal_jump(self):
        self.assertEqual(edge_walk_path("111", "001"), ("111", "011", "001"))
        self.assertEqual(edge_walk_path("111", "000"), ("111", "011", "001", "000"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
python3 -m unittest tests.test_build_mode_topology
```

Expected: import error for `agent_skill_dictionary.build_mode_topology`.

- [ ] **Step 3: Implement topology module**

Create `agent_skill_dictionary/build_mode_topology.py`:

```python
from __future__ import annotations


AXIS_NAMES = ("tool_axis", "context_axis", "boundary_axis")


def _validate_hexagram(value: str) -> str:
    if len(value) != 3 or any(char not in {"0", "1"} for char in value):
        raise ValueError(f"invalid 3-bit hexagram: {value!r}")
    return value


def hamming_distance(source: str, target: str) -> int:
    source = _validate_hexagram(source)
    target = _validate_hexagram(target)
    return sum(1 for left, right in zip(source, target) if left != right)


def is_edge_transition(source: str, target: str) -> bool:
    return hamming_distance(source, target) <= 1


def transition_axes(source: str, target: str) -> tuple[str, ...]:
    source = _validate_hexagram(source)
    target = _validate_hexagram(target)
    return tuple(name for name, left, right in zip(AXIS_NAMES, source, target) if left != right)


def edge_walk_path(source: str, target: str) -> tuple[str, ...]:
    source = _validate_hexagram(source)
    target = _validate_hexagram(target)
    current = list(source)
    path = [source]
    for index, desired in enumerate(target):
        if current[index] == desired:
            continue
        current[index] = desired
        path.append("".join(current))
    return tuple(path)
```

- [ ] **Step 4: Run and verify pass**

Run:

```bash
python3 -m unittest tests.test_build_mode_topology
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add agent_skill_dictionary/build_mode_topology.py tests/test_build_mode_topology.py
git commit -m "feat: add build mode topology guard helpers"
```

## 4. Task 2: Add Guarded FSM Edge-Walk API

**Files:**
- Modify: `agent_skill_dictionary/build_mode_types.py`
- Modify: `agent_skill_dictionary/build_mode_fsm.py`
- Modify: `tests/test_build_mode_fsm.py`

- [ ] **Step 1: Write failing FSM tests**

Append to `tests/test_build_mode_fsm.py`:

```python
from agent_skill_dictionary.build_mode_fsm import guarded_next_hexagram
from agent_skill_dictionary.build_mode_types import TransitionPlanEvidence


class BuildModeGuardedFsmTest(unittest.TestCase):
    def test_guarded_transition_records_edge_walk_for_diagonal_jump(self):
        evidence = WriteEvidence(True, ("app/main.py",), "/w", "a" * 64)
        plan = guarded_next_hexagram("111", "001", evidence)

        self.assertIsInstance(plan, TransitionPlanEvidence)
        self.assertEqual(plan.source_hexagram, "111")
        self.assertEqual(plan.target_hexagram, "001")
        self.assertEqual(plan.edge_path, ("111", "011", "001"))
        self.assertFalse(plan.emergency_override)

    def test_guarded_transition_allows_emergency_violation_to_halt(self):
        violation = ViolationEvidence("rm -rf /", "dangerous_command", "path_sentinel")
        plan = guarded_next_hexagram("111", "100", violation, emergency_override=True)

        self.assertEqual(plan.target_hexagram, "100")
        self.assertEqual(plan.edge_path, ("111", "100"))
        self.assertTrue(plan.emergency_override)
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
python3 -m unittest tests.test_build_mode_fsm.BuildModeGuardedFsmTest
```

Expected: import error for `guarded_next_hexagram` or `TransitionPlanEvidence`.

- [ ] **Step 3: Add DTO**

Add to `agent_skill_dictionary/build_mode_types.py`:

```python
@dataclass(frozen=True)
class TransitionPlanEvidence:
    source_hexagram: str
    target_hexagram: str
    edge_path: tuple[str, ...]
    changed_axes: tuple[str, ...]
    emergency_override: bool = False
```

- [ ] **Step 4: Add guarded FSM API**

Modify `agent_skill_dictionary/build_mode_fsm.py`:

```python
from .build_mode_topology import edge_walk_path, is_edge_transition, transition_axes
from .build_mode_types import TransitionPlanEvidence


def guarded_next_hexagram(
    current_hexagram: str,
    target_hexagram: str,
    evidence: Any,
    *,
    emergency_override: bool = False,
) -> TransitionPlanEvidence:
    if emergency_override or is_edge_transition(current_hexagram, target_hexagram):
        path = (current_hexagram, target_hexagram) if current_hexagram != target_hexagram else (current_hexagram,)
    else:
        path = edge_walk_path(current_hexagram, target_hexagram)
    return TransitionPlanEvidence(
        source_hexagram=current_hexagram,
        target_hexagram=target_hexagram,
        edge_path=path,
        changed_axes=transition_axes(current_hexagram, target_hexagram),
        emergency_override=emergency_override,
    )
```

Keep the existing `next_hexagram()` unchanged in this task.

- [ ] **Step 5: Run and verify pass**

Run:

```bash
python3 -m unittest tests.test_build_mode_fsm.BuildModeGuardedFsmTest tests.test_build_mode_topology
```

Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add agent_skill_dictionary/build_mode_types.py agent_skill_dictionary/build_mode_fsm.py tests/test_build_mode_fsm.py
git commit -m "feat: add guarded build mode transition plans"
```

## 5. Task 3: Add Behavioral Fingerprint Audit

**Files:**
- Create: `agent_skill_dictionary/build_mode_audit.py`
- Modify: `agent_skill_dictionary/build_mode_types.py`
- Create: `tests/test_build_mode_audit.py`

- [ ] **Step 1: Write failing audit tests**

Create `tests/test_build_mode_audit.py`:

```python
import unittest

from agent_skill_dictionary.build_mode_audit import audit_behavior_fingerprint


class BuildModeAuditTest(unittest.TestCase):
    def test_flags_text_tool_mismatch_for_destructive_instruction(self):
        evidence = audit_behavior_fingerprint(
            assistant_text="Before testing, remove ~/SENTINEL.txt with rm -rf.",
            tool_name="write_file",
            arguments={"path": "README.md", "content": "safe"},
        )

        self.assertTrue(evidence.suspicious)
        self.assertEqual(evidence.recommended_hexagram, "100")
        self.assertIn("destructive_text_intent", evidence.reasons)

    def test_allows_scoped_write_without_dangerous_text(self):
        evidence = audit_behavior_fingerprint(
            assistant_text="Writing the FastAPI server.",
            tool_name="write_file",
            arguments={"path": "api/server.py", "content": "app = None\n"},
        )

        self.assertFalse(evidence.suspicious)
        self.assertEqual(evidence.recommended_hexagram, "111")
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
python3 -m unittest tests.test_build_mode_audit
```

Expected: import error.

- [ ] **Step 3: Add DTO**

Add to `agent_skill_dictionary/build_mode_types.py`:

```python
@dataclass(frozen=True)
class BehaviorFingerprintEvidence:
    suspicious: bool
    text_sha256: str
    tool_name: str
    tool_intent: str
    text_intent: str
    reasons: tuple[str, ...]
    recommended_hexagram: str
```

- [ ] **Step 4: Implement audit module**

Create `agent_skill_dictionary/build_mode_audit.py`:

```python
from __future__ import annotations

import hashlib
from typing import Any

from .build_mode_types import BehaviorFingerprintEvidence, HEX_CREATE, HEX_HALT


DESTRUCTIVE_TEXT_PATTERNS = ("rm -rf", "delete sentinel", "remove ~/sentinel", "~/.ssh", "/etc/passwd")


def audit_behavior_fingerprint(
    assistant_text: str,
    tool_name: str,
    arguments: Any,
) -> BehaviorFingerprintEvidence:
    lowered = assistant_text.lower()
    reasons: list[str] = []
    if any(pattern in lowered for pattern in DESTRUCTIVE_TEXT_PATTERNS):
        reasons.append("destructive_text_intent")
    if isinstance(arguments, dict):
        path = str(arguments.get("path") or arguments.get("file_path") or "")
        if path.startswith("../") or "/../" in path:
            reasons.append("path_escape_argument")
    suspicious = bool(reasons)
    return BehaviorFingerprintEvidence(
        suspicious=suspicious,
        text_sha256=hashlib.sha256(assistant_text.encode("utf-8", errors="replace")).hexdigest(),
        tool_name=tool_name,
        tool_intent=_tool_intent(tool_name),
        text_intent="destructive" if suspicious else "benign",
        reasons=tuple(reasons),
        recommended_hexagram=HEX_HALT if suspicious else _recommended_hexagram(tool_name),
    )


def _tool_intent(tool_name: str) -> str:
    if tool_name in {"write_file", "apply_patch", "patch"}:
        return "write"
    if tool_name in {"run_pytest", "run_npm_test", "run_build"}:
        return "verify"
    return "unknown"


def _recommended_hexagram(tool_name: str) -> str:
    if tool_name in {"write_file", "apply_patch", "patch"}:
        return HEX_CREATE
    return "010"
```

- [ ] **Step 5: Run and verify pass**

Run:

```bash
python3 -m unittest tests.test_build_mode_audit
```

Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add agent_skill_dictionary/build_mode_audit.py agent_skill_dictionary/build_mode_types.py tests/test_build_mode_audit.py
git commit -m "feat: add build mode behavior fingerprint audit"
```

## 6. Task 4: Add Entropy Decay Failure Gate

**Files:**
- Create: `agent_skill_dictionary/build_mode_decay.py`
- Modify: `agent_skill_dictionary/build_mode_types.py`
- Create: `tests/test_build_mode_decay.py`

- [ ] **Step 1: Write failing decay tests**

Create `tests/test_build_mode_decay.py`:

```python
import unittest

from agent_skill_dictionary.build_mode_decay import compute_decay_gate


class BuildModeDecayTest(unittest.TestCase):
    def test_repeated_tracebacks_lower_threshold_to_one(self):
        previous = "FAILED tests/test_mesh.py::test_duplicate - TypeError: bad arg\n6 failed"
        current = "FAILED tests/test_mesh.py::test_duplicate - TypeError: bad arg\n6 failed"

        evidence = compute_decay_gate(previous, current, base_threshold=3)

        self.assertGreaterEqual(evidence.similarity_ratio, 0.95)
        self.assertEqual(evidence.dynamic_threshold, 1)
        self.assertTrue(evidence.deadlock_suspected)

    def test_different_failure_keeps_base_threshold(self):
        previous = "FAILED tests/test_a.py::test_a - AssertionError: alpha"
        current = "FAILED tests/test_b.py::test_b - ImportError: beta"

        evidence = compute_decay_gate(previous, current, base_threshold=3)

        self.assertEqual(evidence.dynamic_threshold, 3)
        self.assertFalse(evidence.deadlock_suspected)
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
python3 -m unittest tests.test_build_mode_decay
```

Expected: import error.

- [ ] **Step 3: Add DTO**

Add to `agent_skill_dictionary/build_mode_types.py`:

```python
@dataclass(frozen=True)
class EntropyDecayEvidence:
    previous_sha256: str
    current_sha256: str
    similarity_ratio: float
    base_threshold: int
    dynamic_threshold: int
    deadlock_suspected: bool
```

- [ ] **Step 4: Implement decay module**

Create `agent_skill_dictionary/build_mode_decay.py`:

```python
from __future__ import annotations

import difflib
import hashlib

from .build_mode_types import EntropyDecayEvidence


def compute_decay_gate(
    previous_failure_summary: str,
    current_failure_summary: str,
    *,
    base_threshold: int = 3,
    deadlock_similarity: float = 0.95,
) -> EntropyDecayEvidence:
    ratio = difflib.SequenceMatcher(None, previous_failure_summary, current_failure_summary).ratio()
    deadlock = bool(previous_failure_summary and current_failure_summary and ratio >= deadlock_similarity)
    dynamic_threshold = 1 if deadlock else base_threshold
    return EntropyDecayEvidence(
        previous_sha256=_sha256(previous_failure_summary),
        current_sha256=_sha256(current_failure_summary),
        similarity_ratio=ratio,
        base_threshold=base_threshold,
        dynamic_threshold=dynamic_threshold,
        deadlock_suspected=deadlock,
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()
```

- [ ] **Step 5: Run and verify pass**

Run:

```bash
python3 -m unittest tests.test_build_mode_decay
```

Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add agent_skill_dictionary/build_mode_decay.py agent_skill_dictionary/build_mode_types.py tests/test_build_mode_decay.py
git commit -m "feat: add dynamic entropy decay gate"
```

## 7. Task 5: Add Signed Evidence Envelopes

**Files:**
- Create: `agent_skill_dictionary/build_mode_consensus.py`
- Modify: `agent_skill_dictionary/build_mode_types.py`
- Create: `tests/test_build_mode_consensus.py`

- [ ] **Step 1: Write failing consensus tests**

Create `tests/test_build_mode_consensus.py`:

```python
import tempfile
import unittest
from pathlib import Path

from agent_skill_dictionary.build_mode_consensus import (
    append_node_event,
    sign_evidence_envelope,
    verify_evidence_envelope,
)


class BuildModeConsensusTest(unittest.TestCase):
    def test_signed_envelope_verifies_with_same_secret(self):
        envelope = sign_evidence_envelope(
            node_id="n100",
            hexagram="111",
            evidence={"changed_files": ["core/crypto.py"]},
            secret=b"test-secret",
            timestamp_ms=123,
        )

        self.assertTrue(verify_evidence_envelope(envelope, b"test-secret"))
        self.assertFalse(verify_evidence_envelope(envelope, b"wrong-secret"))

    def test_append_node_event_writes_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "node-state.jsonl"
            envelope = sign_evidence_envelope("n100", "001", {"exit_code": 1}, b"s", timestamp_ms=1)
            append_node_event(path, envelope)

            text = path.read_text(encoding="utf-8")
            self.assertIn('"node_id": "n100"', text)
            self.assertIn('"hexagram": "001"', text)
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
python3 -m unittest tests.test_build_mode_consensus
```

Expected: import error.

- [ ] **Step 3: Add DTO**

Add to `agent_skill_dictionary/build_mode_types.py`:

```python
@dataclass(frozen=True)
class EvidenceEnvelope:
    node_id: str
    hexagram: str
    evidence: dict[str, Any]
    timestamp_ms: int
    evidence_sha256: str
    signature: str
```

- [ ] **Step 4: Implement consensus module**

Create `agent_skill_dictionary/build_mode_consensus.py`:

```python
from __future__ import annotations

import hmac
import hashlib
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .build_mode_types import EvidenceEnvelope


def sign_evidence_envelope(
    node_id: str,
    hexagram: str,
    evidence: dict[str, Any],
    secret: bytes,
    timestamp_ms: int | None = None,
) -> EvidenceEnvelope:
    timestamp = int(time.time() * 1000) if timestamp_ms is None else timestamp_ms
    evidence_json = json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    evidence_sha256 = hashlib.sha256(evidence_json.encode("utf-8")).hexdigest()
    payload = f"{node_id}|{hexagram}|{timestamp}|{evidence_sha256}".encode("utf-8")
    signature = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return EvidenceEnvelope(
        node_id=node_id,
        hexagram=hexagram,
        evidence=evidence,
        timestamp_ms=timestamp,
        evidence_sha256=evidence_sha256,
        signature=signature,
    )


def verify_evidence_envelope(envelope: EvidenceEnvelope, secret: bytes) -> bool:
    expected = sign_evidence_envelope(
        envelope.node_id,
        envelope.hexagram,
        envelope.evidence,
        secret,
        timestamp_ms=envelope.timestamp_ms,
    )
    return hmac.compare_digest(expected.signature, envelope.signature)


def append_node_event(path: str | Path, envelope: EvidenceEnvelope) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(envelope), ensure_ascii=False, sort_keys=True) + "\n")
```

- [ ] **Step 5: Run and verify pass**

Run:

```bash
python3 -m unittest tests.test_build_mode_consensus
```

Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add agent_skill_dictionary/build_mode_consensus.py agent_skill_dictionary/build_mode_types.py tests/test_build_mode_consensus.py
git commit -m "feat: add signed build mode evidence envelopes"
```

## 8. Task 6: Persist Audit And Decay Metadata

**Files:**
- Modify: `agent_skill_dictionary/gateway_server.py`
- Modify: `tests/test_gateway_server_import.py`

- [ ] **Step 1: Write failing persistence test**

Append to `tests/test_gateway_server_import.py`:

```python
    def test_build_mode_state_persists_audit_and_decay_metadata(self):
        import json
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            gateway_server._persist_build_mode_state(
                str(workspace),
                [
                    {
                        "status": "needs_fix",
                        "hexagram": "001",
                        "next_hexagram": "101",
                        "audit": {"suspicious": True, "recommended_hexagram": "100"},
                        "decay": {"dynamic_threshold": 1, "deadlock_suspected": True},
                    }
                ],
                {},
            )

            state = json.loads((workspace / ".yizijue" / "build-mode-state.json").read_text(encoding="utf-8"))

        self.assertEqual(state["results"][0]["audit"]["recommended_hexagram"], "100")
        self.assertEqual(state["results"][0]["decay"]["dynamic_threshold"], 1)
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
python3 -m unittest tests.test_gateway_server_import.GatewayServerImportTest.test_build_mode_state_persists_audit_and_decay_metadata
```

Expected: failure because compact state drops `audit` and `decay`.

- [ ] **Step 3: Persist compact metadata**

Modify `_compact_build_mode_results()` in `agent_skill_dictionary/gateway_server.py` so each compact result includes safe dict values:

```python
                "audit": result.get("audit") if isinstance(result.get("audit"), dict) else None,
                "decay": result.get("decay") if isinstance(result.get("decay"), dict) else None,
```

- [ ] **Step 4: Run and verify pass**

Run:

```bash
python3 -m unittest tests.test_gateway_server_import.GatewayServerImportTest.test_build_mode_state_persists_audit_and_decay_metadata
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add agent_skill_dictionary/gateway_server.py tests/test_gateway_server_import.py
git commit -m "feat: persist build mode audit and decay metadata"
```

## 9. Task 7: Add Sandbox Decay Evidence

**Files:**
- Modify: `agent_skill_dictionary/build_mode_sandbox.py`
- Modify: `agent_skill_dictionary/build_mode_tool_executor.py`
- Modify: `tests/test_build_mode_tool_executor.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_build_mode_tool_executor.py`:

```python
    def test_repeated_failure_summary_adds_decay_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous = "FAILED tests/test_mesh.py::test_duplicate - TypeError: bad arg"
            result = execute_build_mode_tool(
                workspace=tmp,
                tool_name="run_pytest",
                arguments={"command": "python3 -c \"print('FAILED tests/test_mesh.py::test_duplicate - TypeError: bad arg'); raise SystemExit(1)\""},
                use_docker=False,
                previous_failure_summary=previous,
            )

            self.assertIn("decay", result)
            self.assertEqual(result["decay"]["dynamic_threshold"], 1)
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
python3 -m unittest tests.test_build_mode_tool_executor.BuildModeToolExecutorTest.test_repeated_failure_summary_adds_decay_metadata
```

Expected: `execute_build_mode_tool()` does not accept `previous_failure_summary`.

- [ ] **Step 3: Extend executor signature**

Modify `execute_build_mode_tool()` signature:

```python
def execute_build_mode_tool(
    workspace: str | Path,
    tool_name: str,
    arguments: Any,
    use_docker: bool = False,
    timeout_seconds: int = 15,
    lockdown: bool = False,
    previous_failure_summary: str = "",
) -> dict[str, Any]:
```

In the failed verify branch:

```python
from .build_mode_decay import compute_decay_gate

if previous_failure_summary and sandbox.failure_summary:
    decay = compute_decay_gate(previous_failure_summary, sandbox.failure_summary)
    payload["decay"] = dto_to_dict(decay)
```

- [ ] **Step 4: Run and verify pass**

Run:

```bash
python3 -m unittest tests.test_build_mode_tool_executor.BuildModeToolExecutorTest.test_repeated_failure_summary_adds_decay_metadata
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add agent_skill_dictionary/build_mode_tool_executor.py tests/test_build_mode_tool_executor.py
git commit -m "feat: add decay metadata to repeated sandbox failures"
```

## 10. Task 8: Regression Suite And Documentation

**Files:**
- Modify: `docs/hexagram-rules.md`
- Create: `docs/build-mode-v2-3d-dynamics.md`

- [ ] **Step 1: Add V2 docs**

Create `docs/build-mode-v2-3d-dynamics.md`:

```markdown
# Build Mode V2 3D Dynamics

Build Mode V2 models each 3-bit hexagram as a coordinate in a cube:

- bit 1: tool/action bandwidth
- bit 2: context/memory bandwidth
- bit 3: boundary/sandbox exposure

Normal state transitions must move along cube edges. A transition that changes multiple bits is decomposed into a `TransitionPlanEvidence.edge_path`. Emergency halt transitions may bypass edge walking only when backed by `ViolationEvidence` or `BehaviorFingerprintEvidence`.

V2 also adds:

- behavioral fingerprint audit for text/tool mismatch and destructive hidden intent
- entropy decay gates for repeated pytest failures
- signed evidence envelopes for future multi-node state synchronization
```

- [ ] **Step 2: Run focused regression**

Run:

```bash
python3 -m unittest \
  tests.test_build_mode_topology \
  tests.test_build_mode_audit \
  tests.test_build_mode_decay \
  tests.test_build_mode_consensus \
  tests.test_build_mode_fsm \
  tests.test_build_mode_tool_executor \
  tests.test_gateway_server_import
```

Expected: `OK`.

- [ ] **Step 3: Run compile check**

Run:

```bash
python3 -m compileall -q agent_skill_dictionary scripts tests
```

Expected: no output, exit code `0`.

- [ ] **Step 4: Record known unrelated full-suite issue if still present**

Run:

```bash
python3 -m unittest discover
```

Expected before separate contract cleanup: one unrelated `查` allowlist mismatch may still fail because `kernel_policy.py` includes `native_inspect_card` while `oneword_dict.json` does not. Do not fix that in this V2 dynamics branch unless the user explicitly approves changing the root dictionary contract.

- [ ] **Step 5: Commit**

```bash
git add docs/hexagram-rules.md docs/build-mode-v2-3d-dynamics.md
git commit -m "docs: document build mode v2 dynamics controls"
```

## 11. Self-Review

Spec coverage:

- 对抗维度: Task 3 implements `BehaviorFingerprintEvidence` and mismatch detection.
- 时间维度: Task 4 and Task 7 implement repeated-failure similarity and dynamic threshold metadata.
- 空间维度: Task 5 implements signed evidence envelopes and a local append-only state store as the first consensus boundary.
- 三维棱边: Task 1 and Task 2 implement topology helpers and guarded transition planning.

Placeholder scan:

- No `TBD`, `TODO`, or "implement later" placeholders are present.
- Each task has exact files, test code, implementation code, commands, and expected outcomes.

Type consistency:

- `TransitionPlanEvidence`, `BehaviorFingerprintEvidence`, `EntropyDecayEvidence`, and `EvidenceEnvelope` are all defined in `build_mode_types.py` before use.
- Existing `next_hexagram()` remains backward compatible.
- New metadata keys are `audit` and `decay` consistently across executor and gateway state persistence.

## 12. Execution Options

Plan complete and saved to `docs/superpowers/plans/2026-05-27-build-mode-v2-3d-dynamics.md`.

1. **Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fastest for isolated modules.
2. **Inline Execution** - execute tasks in this session using executing-plans, batch execution with checkpoints.
