# Build Mode MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Build Mode MVP so 一字诀 can complete scoped project-building tasks with deterministic state transitions, structured evidence, sandboxed verification, soft feedback, and manifest-based completion gates.

**Architecture:** Add a focused Build Mode layer beside the existing gateway and executor modules. The layer owns V2 hexagram state, evidence DTOs, shadow tool mapping, scoped writes, sandbox execution adapters, soft response payloads, and archive manifests while reusing existing `patch_executor.py`, `executor.py`, `tool_guard.py`, `path_sentinel.py`, and `gateway_server.py` where practical.

**Tech Stack:** Python 3, dataclasses, pathlib, hashlib, json, unittest, existing FastAPI gateway code, optional Docker through the existing command executor.

---

## 1. Design Inputs

This plan implements the rules from:

- `docs/build-mode-kernel-rules.md`
- `docs/hexagram-rules.md`

It does not run a new A/B benchmark. Testing in this plan is unit and integration-level only.

## 2. File Structure

Create these focused modules:

| File | Responsibility |
| --- | --- |
| `agent_skill_dictionary/build_mode_types.py` | Hexagram constants, scope constants, DTO dataclasses, evidence constructors |
| `agent_skill_dictionary/build_mode_intent.py` | Yin/Yang, quadrant, and initial hexagram resolver |
| `agent_skill_dictionary/build_mode_permissions.py` | Permission matrix and shadow tool mapping |
| `agent_skill_dictionary/build_mode_writer.py` | Scoped file creation/write/patch evidence wrapper |
| `agent_skill_dictionary/build_mode_sandbox.py` | Sandboxed test runner wrapper over existing `executor.execute_command` |
| `agent_skill_dictionary/build_mode_feedback.py` | Soft feedback DTO and OpenAI-compatible/SSE-compatible payload builders |
| `agent_skill_dictionary/build_mode_archive.py` | Manifest/SHA256 generation and optional lockdown |
| `agent_skill_dictionary/build_mode_fsm.py` | State transition table and evidence-gated transition function |

Modify these existing files only after the standalone modules are tested:

| File | Change |
| --- | --- |
| `agent_skill_dictionary/gateway_server.py` | Wire Build Mode resolver and permission filtering behind an env flag |
| `agent_skill_dictionary/tool_guard.py` | Add Build Mode tool categories if needed |
| `agent_skill_dictionary/runner.py` | Optional local Build Mode dry-run entry |

Add these tests:

| Test File | Coverage |
| --- | --- |
| `tests/test_build_mode_types.py` | DTO serialization, evidence gates, constants |
| `tests/test_build_mode_intent.py` | Intent routing to `111`, `011`, `101`, `100` |
| `tests/test_build_mode_permissions.py` | Tool filtering and shadow tool mapping |
| `tests/test_build_mode_writer.py` | Scoped write success, path escape halt evidence |
| `tests/test_build_mode_sandbox.py` | Exit-code evidence and timeout mapping |
| `tests/test_build_mode_feedback.py` | HTTP 200 soft payload, stderr-empty contract, SSE chunks |
| `tests/test_build_mode_archive.py` | Manifest hash generation and lockdown off by default |
| `tests/test_build_mode_fsm.py` | Full transition chain and blocked paths |

## 3. Core Data Structures

### 3.1 Hexagram Constants

Use these exact V2 primitive codes:

```python
HEX_RETURN = "000"   # 坤 / 归
HEX_VERIFY = "001"  # 震 / 测
HEX_ISOLATE = "010" # 坎 / 隔
HEX_PROMPT = "011"  # 巽 / 问
HEX_HALT = "100"    # 艮 / 停
HEX_INSPECT = "101" # 离 / 查
HEX_CORRECT = "110" # 兑 / 纠
HEX_CREATE = "111"  # 乾 / 造
```

### 3.2 `SystemStateContext`

```python
@dataclass(frozen=True)
class SystemStateContext:
    trace_id: str
    current_hexagram: str
    current_scope: str
    workspace_root: str
    last_exit_code: int | None = None
    consecutive_failures: int = 0
    evidence_gate_locked: bool = False
    lockdown: bool = False
```

### 3.3 Evidence DTOs

All state transitions must consume one of these DTOs. Natural-language model claims are not evidence.

```python
@dataclass(frozen=True)
class IntentEvidence:
    yin_yang: str
    quadrant: str
    hexagram: str
    confidence: float
    reasons: tuple[str, ...]

@dataclass(frozen=True)
class WriteEvidence:
    ok: bool
    changed_files: tuple[str, ...]
    path_scope: str
    patch_digest: str
    violation: str | None = None

@dataclass(frozen=True)
class SandboxEvidence:
    exit_code: int
    pytest_status: str
    stdout_sha256: str
    stderr_sha256: str
    duration_ms: int
    timed_out: bool = False
    oom: bool = False

@dataclass(frozen=True)
class ViolationEvidence:
    blocked_action: str
    reason: str
    source: str
    exit_code: int = 126

@dataclass(frozen=True)
class FeedbackEvidence:
    status: str
    source_hexagram: str
    next_hexagram: str
    summary: str
    line_refs: tuple[str, ...] = ()

@dataclass(frozen=True)
class ArchiveEvidence:
    manifest_path: str
    sha256_map: dict[str, str]
    readonly_status: str
    lockdown: bool
```

## 4. Shadow Tool Mapping Spec

`permission_matrix` must translate client-native tools into Build Mode primitives before the model sees or executes them.

| Native Client Tool / Pattern | Build Hexagram | Shadow Action | Notes |
| --- | --- | --- | --- |
| `view_file`, `read_file`, `grep`, `bash("cat ...")`, `bash("grep ...")`, `bash("rg ...")` | `101` 离/查 | Replace blind read with `native_inspect_card` / repo card; remove write and shell tools | Reduces prompt size and prevents read-loop drift |
| `write_file`, `edit_file`, `apply_patch`, `bash("mkdir ...")`, `bash("tee ...")` | `111` 乾/造 | Route through scoped writer; force workspace-root resolution | Allows creation only inside workspace |
| `run_terminal_command`, `bash("pytest ...")`, `bash("python -m pytest ...")`, `bash("npm test")` | `001` 震/测 | Route through sandbox runner; return digest and short summary | No host naked execution |
| `bash("rm -rf ...")`, `chmod`, `curl | sh`, secret-path access | `100` 艮/停 | Return violation evidence, then soft feedback | Never execute |
| No tool or pure question | `011` 巽/问 | Clear tools, use concise text response | Zero-tool fast path |
| Unknown I/O-heavy or ambiguous tool | `010` 坎/隔 | Route to shadow buffer or halt depending risk | No real disk write |

## 5. Implementation Tasks

### Task 1: Add Build Mode Types And Evidence Gates

**Files:**
- Create: `agent_skill_dictionary/build_mode_types.py`
- Test: `tests/test_build_mode_types.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_build_mode_types.py`:

```python
import unittest

from agent_skill_dictionary.build_mode_types import (
    HEX_CREATE,
    HEX_HALT,
    HEX_INSPECT,
    HEX_RETURN,
    HEX_VERIFY,
    ArchiveEvidence,
    SandboxEvidence,
    SystemStateContext,
    evidence_allows_completion,
)


class BuildModeTypesTest(unittest.TestCase):
    def test_hexagram_constants_are_unique(self):
        values = {HEX_RETURN, HEX_VERIFY, HEX_INSPECT, HEX_HALT, HEX_CREATE}
        self.assertEqual(len(values), 5)
        self.assertEqual(HEX_CREATE, "111")
        self.assertEqual(HEX_VERIFY, "001")

    def test_completion_requires_exit_zero_and_manifest(self):
        sandbox = SandboxEvidence(
            exit_code=0,
            pytest_status="passed",
            stdout_sha256="a" * 64,
            stderr_sha256="b" * 64,
            duration_ms=120,
        )
        archive = ArchiveEvidence(
            manifest_path=".yizijue/manifest.json",
            sha256_map={"app/main.py": "c" * 64},
            readonly_status="audit_only",
            lockdown=False,
        )
        self.assertTrue(evidence_allows_completion(sandbox, archive))

    def test_completion_rejects_model_only_claim(self):
        self.assertFalse(evidence_allows_completion("tests passed", None))

    def test_state_context_defaults_to_unlocked_gate(self):
        ctx = SystemStateContext(
            trace_id="trace-1",
            current_hexagram=HEX_CREATE,
            current_scope="11",
            workspace_root="/workspace/sandbox",
        )
        self.assertFalse(ctx.evidence_gate_locked)
        self.assertEqual(ctx.consecutive_failures, 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_build_mode_types -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'agent_skill_dictionary.build_mode_types'`.

- [ ] **Step 3: Implement types**

Create `agent_skill_dictionary/build_mode_types.py`:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

HEX_RETURN = "000"
HEX_VERIFY = "001"
HEX_ISOLATE = "010"
HEX_PROMPT = "011"
HEX_HALT = "100"
HEX_INSPECT = "101"
HEX_CORRECT = "110"
HEX_CREATE = "111"

SCOPE_TAIYANG = "11"
SCOPE_SHAOYIN = "10"
SCOPE_SHAOYANG = "01"
SCOPE_TAIYIN = "00"


@dataclass(frozen=True)
class SystemStateContext:
    trace_id: str
    current_hexagram: str
    current_scope: str
    workspace_root: str
    last_exit_code: int | None = None
    consecutive_failures: int = 0
    evidence_gate_locked: bool = False
    lockdown: bool = False


@dataclass(frozen=True)
class IntentEvidence:
    yin_yang: str
    quadrant: str
    hexagram: str
    confidence: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class WriteEvidence:
    ok: bool
    changed_files: tuple[str, ...]
    path_scope: str
    patch_digest: str
    violation: str | None = None


@dataclass(frozen=True)
class SandboxEvidence:
    exit_code: int
    pytest_status: str
    stdout_sha256: str
    stderr_sha256: str
    duration_ms: int
    timed_out: bool = False
    oom: bool = False


@dataclass(frozen=True)
class ViolationEvidence:
    blocked_action: str
    reason: str
    source: str
    exit_code: int = 126


@dataclass(frozen=True)
class FeedbackEvidence:
    status: str
    source_hexagram: str
    next_hexagram: str
    summary: str
    line_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ArchiveEvidence:
    manifest_path: str
    sha256_map: dict[str, str]
    readonly_status: str
    lockdown: bool


def dto_to_dict(value: Any) -> dict[str, Any]:
    if not hasattr(value, "__dataclass_fields__"):
        raise TypeError("expected dataclass DTO")
    return asdict(value)


def evidence_allows_completion(sandbox: Any, archive: Any) -> bool:
    if not isinstance(sandbox, SandboxEvidence):
        return False
    if not isinstance(archive, ArchiveEvidence):
        return False
    return (
        sandbox.exit_code == 0
        and sandbox.pytest_status == "passed"
        and bool(sandbox.stdout_sha256)
        and bool(archive.manifest_path)
        and bool(archive.sha256_map)
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python3 -m unittest tests.test_build_mode_types -v
```

Expected: PASS.

### Task 2: Add Intent Resolver

**Files:**
- Create: `agent_skill_dictionary/build_mode_intent.py`
- Test: `tests/test_build_mode_intent.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_build_mode_intent.py`:

```python
import unittest

from agent_skill_dictionary.build_mode_intent import resolve_intent
from agent_skill_dictionary.build_mode_types import HEX_CREATE, HEX_HALT, HEX_INSPECT, HEX_PROMPT


class BuildModeIntentTest(unittest.TestCase):
    def test_project_build_routes_to_create(self):
        evidence = resolve_intent({"messages": [{"role": "user", "content": "从零创建 FastAPI 项目，写测试并运行 pytest"}]})
        self.assertEqual(evidence.yin_yang, "yang")
        self.assertEqual(evidence.quadrant, "11")
        self.assertEqual(evidence.hexagram, HEX_CREATE)
        self.assertIn("requires_file_write", evidence.reasons)

    def test_pure_question_routes_to_prompt(self):
        evidence = resolve_intent({"messages": [{"role": "user", "content": "解释一下这个函数的设计思路"}]})
        self.assertEqual(evidence.yin_yang, "yin")
        self.assertEqual(evidence.hexagram, HEX_PROMPT)

    def test_readonly_repo_review_routes_to_inspect(self):
        evidence = resolve_intent({"messages": [{"role": "user", "content": "只读审查当前目录结构，不要修改文件"}]})
        self.assertEqual(evidence.hexagram, HEX_INSPECT)

    def test_dangerous_command_routes_to_halt(self):
        evidence = resolve_intent({"messages": [{"role": "user", "content": "执行 rm -rf /tmp/cache"}]})
        self.assertEqual(evidence.hexagram, HEX_HALT)
        self.assertIn("dangerous_command", evidence.reasons)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_build_mode_intent -v
```

Expected: FAIL with missing module.

- [ ] **Step 3: Implement resolver**

Create `agent_skill_dictionary/build_mode_intent.py`:

```python
from __future__ import annotations

from typing import Any

from .build_mode_types import (
    HEX_CREATE,
    HEX_HALT,
    HEX_INSPECT,
    HEX_PROMPT,
    IntentEvidence,
    SCOPE_SHAOYANG,
    SCOPE_TAIYANG,
    SCOPE_TAIYIN,
)

WRITE_MARKERS = ("创建", "新建", "写", "修改", "修复", "生成项目", "write", "patch", "mkdir")
TEST_MARKERS = ("pytest", "测试", "单测", "run test", "npm test")
READONLY_MARKERS = ("只读", "审查", "分析", "查看", "解释", "review", "inspect")
DANGEROUS_MARKERS = ("rm -rf", "curl | sh", "chmod -R", "/etc/passwd", "~/.ssh", "~/.codex", "~/.claude")


def resolve_intent(payload: dict[str, Any]) -> IntentEvidence:
    text = _payload_text(payload)
    lowered = text.lower()
    reasons: list[str] = []

    if any(marker in lowered for marker in DANGEROUS_MARKERS):
        return IntentEvidence("yin", SCOPE_TAIYIN, HEX_HALT, 1.0, ("dangerous_command",))

    if any(marker in lowered for marker in WRITE_MARKERS):
        reasons.append("requires_file_write")
    if any(marker in lowered for marker in TEST_MARKERS):
        reasons.append("requires_tests")

    if reasons:
        return IntentEvidence("yang", SCOPE_TAIYANG, HEX_CREATE, 0.9, tuple(reasons))

    if any(marker in lowered for marker in READONLY_MARKERS):
        if "只读" in lowered or "审查" in lowered or "review" in lowered or "inspect" in lowered:
            return IntentEvidence("yin", SCOPE_SHAOYANG, HEX_INSPECT, 0.82, ("readonly_inspect",))
        return IntentEvidence("yin", SCOPE_SHAOYANG, HEX_PROMPT, 0.78, ("pure_text",))

    return IntentEvidence("yin", SCOPE_SHAOYANG, HEX_PROMPT, 0.55, ("low_confidence_prompt",))


def _payload_text(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for message in payload.get("messages", []):
        content = message.get("content", "")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    parts.append(str(item.get("text", "")))
                else:
                    parts.append(str(item))
    return "\n".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python3 -m unittest tests.test_build_mode_intent -v
```

Expected: PASS.

### Task 3: Add Permission Matrix And Shadow Tool Mapping

**Files:**
- Create: `agent_skill_dictionary/build_mode_permissions.py`
- Test: `tests/test_build_mode_permissions.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_build_mode_permissions.py`:

```python
import unittest

from agent_skill_dictionary.build_mode_permissions import filter_tools_schema, map_shadow_tool
from agent_skill_dictionary.build_mode_types import HEX_CREATE, HEX_HALT, HEX_INSPECT, HEX_PROMPT, HEX_VERIFY


def tool(name):
    return {"type": "function", "function": {"name": name, "description": "long description"}}


class BuildModePermissionsTest(unittest.TestCase):
    def test_prompt_clears_tools(self):
        self.assertEqual(filter_tools_schema(HEX_PROMPT, [tool("write_file")]), [])

    def test_inspect_keeps_only_native_inspect_card(self):
        result = filter_tools_schema(HEX_INSPECT, [tool("grep"), tool("native_inspect_card"), tool("write_file")])
        self.assertEqual([t["function"]["name"] for t in result], ["native_inspect_card"])

    def test_create_keeps_write_tools_only(self):
        result = filter_tools_schema(HEX_CREATE, [tool("write_file"), tool("run_pytest"), tool("grep")])
        self.assertEqual([t["function"]["name"] for t in result], ["write_file"])

    def test_verify_keeps_test_tools_only(self):
        result = filter_tools_schema(HEX_VERIFY, [tool("write_file"), tool("run_pytest")])
        self.assertEqual([t["function"]["name"] for t in result], ["run_pytest"])

    def test_halt_clears_tools(self):
        self.assertEqual(filter_tools_schema(HEX_HALT, [tool("run_pytest")]), [])

    def test_shadow_maps_bash_pytest_to_verify(self):
        mapped = map_shadow_tool("bash", {"command": "python -m pytest -q"})
        self.assertEqual(mapped.hexagram, HEX_VERIFY)
        self.assertEqual(mapped.shadow_action, "sandbox_runner")

    def test_shadow_maps_rm_to_halt(self):
        mapped = map_shadow_tool("bash", {"command": "rm -rf /tmp/x"})
        self.assertEqual(mapped.hexagram, HEX_HALT)
        self.assertEqual(mapped.shadow_action, "halt")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_build_mode_permissions -v
```

Expected: FAIL with missing module.

- [ ] **Step 3: Implement permission matrix**

Create `agent_skill_dictionary/build_mode_permissions.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .build_mode_types import HEX_CREATE, HEX_HALT, HEX_INSPECT, HEX_ISOLATE, HEX_PROMPT, HEX_VERIFY

INSPECT_TOOLS = {"native_inspect_card"}
CREATE_TOOLS = {"make_dir", "write_file", "patch", "apply_patch", "edit_scoped_file", "create_new_file"}
VERIFY_TOOLS = {"run_pytest", "run_npm_test", "run_build"}
PROMPT_TOOLS: set[str] = set()
HALT_TOOLS: set[str] = set()
ISOLATE_TOOLS: set[str] = set()

READ_PATTERNS = ("cat ", "grep ", "rg ", "sed -n")
WRITE_PATTERNS = ("mkdir", "tee ", "cat >", "python - <<", "apply_patch")
TEST_PATTERNS = ("pytest", "npm test", "python -m pytest")
DANGEROUS_PATTERNS = ("rm -rf", "curl | sh", "chmod", "/etc/passwd", "~/.ssh", "~/.codex", "~/.claude")


@dataclass(frozen=True)
class ShadowToolMapping:
    original_tool: str
    hexagram: str
    shadow_action: str
    reason: str


def filter_tools_schema(hexagram: str, original_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    allowed = _allowed_tool_names(hexagram)
    if not allowed:
        return []
    filtered = []
    for item in original_tools:
        name = _tool_name(item)
        if name in allowed:
            filtered.append(_compact_tool(item))
    return filtered


def map_shadow_tool(tool_name: str, arguments: Any) -> ShadowToolMapping:
    command = _command_text(tool_name, arguments)
    lowered = command.lower()
    if any(pattern in lowered for pattern in DANGEROUS_PATTERNS):
        return ShadowToolMapping(tool_name, HEX_HALT, "halt", "dangerous_command")
    if tool_name in {"write_file", "edit_file", "apply_patch", "edit_scoped_file"}:
        return ShadowToolMapping(tool_name, HEX_CREATE, "scoped_writer", "native_write_tool")
    if any(pattern in lowered for pattern in TEST_PATTERNS):
        return ShadowToolMapping(tool_name, HEX_VERIFY, "sandbox_runner", "test_command")
    if any(pattern in lowered for pattern in WRITE_PATTERNS):
        return ShadowToolMapping(tool_name, HEX_CREATE, "scoped_writer", "write_command")
    if tool_name in {"view_file", "read_file", "grep", "native_inspect_card"} or any(pattern in lowered for pattern in READ_PATTERNS):
        return ShadowToolMapping(tool_name, HEX_INSPECT, "native_inspect_card", "read_command")
    if tool_name:
        return ShadowToolMapping(tool_name, HEX_ISOLATE, "shadow_buffer", "unknown_io")
    return ShadowToolMapping(tool_name, HEX_PROMPT, "zero_tool", "no_tool")


def _allowed_tool_names(hexagram: str) -> set[str]:
    if hexagram == HEX_INSPECT:
        return INSPECT_TOOLS
    if hexagram == HEX_CREATE:
        return CREATE_TOOLS
    if hexagram == HEX_VERIFY:
        return VERIFY_TOOLS
    if hexagram == HEX_PROMPT:
        return PROMPT_TOOLS
    if hexagram == HEX_HALT:
        return HALT_TOOLS
    if hexagram == HEX_ISOLATE:
        return ISOLATE_TOOLS
    return set()


def _tool_name(item: dict[str, Any]) -> str:
    if "function" in item and isinstance(item["function"], dict):
        return str(item["function"].get("name", ""))
    return str(item.get("name", ""))


def _compact_tool(item: dict[str, Any]) -> dict[str, Any]:
    name = _tool_name(item)
    if "function" in item:
        compact = dict(item)
        function = dict(compact["function"])
        function["description"] = f"Build Mode allowed tool: {name}"
        compact["function"] = function
        return compact
    compact = dict(item)
    compact["description"] = f"Build Mode allowed tool: {name}"
    return compact


def _command_text(tool_name: str, arguments: Any) -> str:
    if isinstance(arguments, dict):
        return str(arguments.get("command") or arguments.get("cmd") or arguments.get("path") or "")
    return str(arguments or tool_name)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python3 -m unittest tests.test_build_mode_permissions -v
```

Expected: PASS.

### Task 4: Add Scoped Writer

**Files:**
- Create: `agent_skill_dictionary/build_mode_writer.py`
- Test: `tests/test_build_mode_writer.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_build_mode_writer.py`:

```python
import tempfile
import unittest
from pathlib import Path

from agent_skill_dictionary.build_mode_types import ViolationEvidence
from agent_skill_dictionary.build_mode_writer import safe_write


class BuildModeWriterTest(unittest.TestCase):
    def test_safe_write_creates_file_inside_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = safe_write(tmp, "app/main.py", "print('ok')\n")
            self.assertTrue(evidence.ok)
            self.assertEqual(evidence.changed_files, ("app/main.py",))
            self.assertTrue((Path(tmp) / "app/main.py").exists())
            self.assertEqual(evidence.violation, None)

    def test_path_escape_returns_violation_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = safe_write(tmp, "../outside.py", "bad")
            self.assertIsInstance(evidence, ViolationEvidence)
            self.assertEqual(evidence.reason, "path_escape")
            self.assertEqual(evidence.exit_code, 126)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_build_mode_writer -v
```

Expected: FAIL with missing module.

- [ ] **Step 3: Implement scoped writer**

Create `agent_skill_dictionary/build_mode_writer.py`:

```python
from __future__ import annotations

import hashlib
from pathlib import Path

from .build_mode_types import ViolationEvidence, WriteEvidence


def safe_write(workspace_root: str | Path, relative_path: str, content: str) -> WriteEvidence | ViolationEvidence:
    root = Path(workspace_root).resolve()
    target = (root / relative_path).resolve()
    if target != root and root not in target.parents:
        return ViolationEvidence(
            blocked_action=f"write:{relative_path}",
            reason="path_escape",
            source="scoped_writer",
        )
    if _is_sensitive_path(target):
        return ViolationEvidence(
            blocked_action=f"write:{relative_path}",
            reason="sensitive_path",
            source="scoped_writer",
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    rel = target.relative_to(root).as_posix()
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return WriteEvidence(
        ok=True,
        changed_files=(rel,),
        path_scope=str(root),
        patch_digest=digest,
    )


def _is_sensitive_path(path: Path) -> bool:
    text = path.as_posix()
    return any(part in text for part in ("/.ssh/", "/.codex/", "/.claude/"))
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python3 -m unittest tests.test_build_mode_writer -v
```

Expected: PASS.

### Task 5: Add Sandbox Runner Wrapper

**Files:**
- Create: `agent_skill_dictionary/build_mode_sandbox.py`
- Test: `tests/test_build_mode_sandbox.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_build_mode_sandbox.py`:

```python
import tempfile
import unittest
from pathlib import Path

from agent_skill_dictionary.build_mode_sandbox import sandbox_evidence_from_result, run_isolated_test


class BuildModeSandboxTest(unittest.TestCase):
    def test_sandbox_evidence_maps_exit_zero_to_passed(self):
        evidence = sandbox_evidence_from_result({"exit_code": 0, "stdout": "ok", "stderr": ""}, 12)
        self.assertEqual(evidence.exit_code, 0)
        self.assertEqual(evidence.pytest_status, "passed")
        self.assertEqual(len(evidence.stdout_sha256), 64)

    def test_sandbox_evidence_maps_timeout(self):
        evidence = sandbox_evidence_from_result({"exit_code": 124, "stdout": "", "stderr": "TIMEOUT"}, 10000)
        self.assertTrue(evidence.timed_out)
        self.assertEqual(evidence.pytest_status, "timeout")

    def test_run_isolated_test_returns_evidence_for_simple_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
            evidence = run_isolated_test(["python3", "-m", "unittest", "discover"], tmp, use_docker=False, timeout_seconds=10)
            self.assertIsInstance(evidence.exit_code, int)
            self.assertEqual(len(evidence.stdout_sha256), 64)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_build_mode_sandbox -v
```

Expected: FAIL with missing module.

- [ ] **Step 3: Implement sandbox wrapper**

Create `agent_skill_dictionary/build_mode_sandbox.py`:

```python
from __future__ import annotations

import hashlib
import time
from pathlib import Path

from .build_mode_types import SandboxEvidence
from .executor import execute_command


def run_isolated_test(
    command: list[str],
    workspace_root: str | Path,
    use_docker: bool = True,
    timeout_seconds: int = 15,
) -> SandboxEvidence:
    start = time.monotonic()
    result = execute_command(
        command,
        cwd=workspace_root,
        workspace_root=workspace_root,
        timeout_seconds=timeout_seconds,
        use_docker=use_docker,
        require_docker=False,
    )
    duration_ms = int((time.monotonic() - start) * 1000)
    return sandbox_evidence_from_result(result, duration_ms)


def sandbox_evidence_from_result(result: dict[str, object], duration_ms: int) -> SandboxEvidence:
    exit_code = int(result.get("exit_code", 1))
    stdout = str(result.get("stdout", ""))
    stderr = str(result.get("stderr", ""))
    timed_out = exit_code == 124 or "TIMEOUT" in stderr
    oom = exit_code == 137
    if exit_code == 0:
        status = "passed"
    elif timed_out:
        status = "timeout"
    elif oom:
        status = "oom"
    else:
        status = "failed"
    return SandboxEvidence(
        exit_code=exit_code,
        pytest_status=status,
        stdout_sha256=_sha256(stdout),
        stderr_sha256=_sha256(stderr),
        duration_ms=duration_ms,
        timed_out=timed_out,
        oom=oom,
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python3 -m unittest tests.test_build_mode_sandbox -v
```

Expected: PASS.

### Task 6: Add Soft Feedback And Stream Tunnelling Payloads

**Files:**
- Create: `agent_skill_dictionary/build_mode_feedback.py`
- Test: `tests/test_build_mode_feedback.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_build_mode_feedback.py`:

```python
import json
import unittest

from agent_skill_dictionary.build_mode_feedback import build_sse_soft_chunks, rewrite_to_soft_payload
from agent_skill_dictionary.build_mode_types import HEX_CORRECT, HEX_HALT, HEX_INSPECT, ViolationEvidence


class BuildModeFeedbackTest(unittest.TestCase):
    def test_violation_rewrites_to_http_200_payload(self):
        evidence = ViolationEvidence(blocked_action="rm -rf /tmp/x", reason="dangerous_command", source="path_preflight")
        payload = rewrite_to_soft_payload(evidence)
        self.assertEqual(payload["http_status"], 200)
        self.assertEqual(payload["stderr"], "")
        self.assertEqual(payload["feedback"]["source_hexagram"], HEX_HALT)
        self.assertEqual(payload["feedback"]["next_hexagram"], HEX_INSPECT)

    def test_sse_chunks_are_data_events_and_done(self):
        evidence = ViolationEvidence(blocked_action="rm -rf /tmp/x", reason="dangerous_command", source="path_preflight")
        chunks = list(build_sse_soft_chunks(evidence))
        self.assertTrue(chunks[0].startswith("data: "))
        self.assertEqual(chunks[-1], "data: [DONE]\\n\\n")
        json.loads(chunks[0][len("data: "):])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_build_mode_feedback -v
```

Expected: FAIL with missing module.

- [ ] **Step 3: Implement feedback module**

Create `agent_skill_dictionary/build_mode_feedback.py`:

```python
from __future__ import annotations

import json
from typing import Iterator

from .build_mode_types import FeedbackEvidence, HEX_CORRECT, HEX_HALT, HEX_INSPECT, SandboxEvidence, ViolationEvidence, dto_to_dict


def rewrite_to_soft_payload(raw_error: SandboxEvidence | ViolationEvidence) -> dict[str, object]:
    feedback = _feedback_from_error(raw_error)
    return {
        "http_status": 200,
        "stderr": "",
        "response_mode": "soft_rewrite",
        "feedback": dto_to_dict(feedback),
        "message": _message_text(feedback),
    }


def build_sse_soft_chunks(raw_error: SandboxEvidence | ViolationEvidence) -> Iterator[str]:
    payload = rewrite_to_soft_payload(raw_error)
    chunk = {
        "choices": [
            {
                "delta": {"content": payload["message"]},
                "finish_reason": None,
                "index": 0,
            }
        ],
        "object": "chat.completion.chunk",
    }
    yield "data: " + json.dumps(chunk, ensure_ascii=False) + "\n\n"
    done = {
        "choices": [{"delta": {}, "finish_reason": "stop", "index": 0}],
        "object": "chat.completion.chunk",
    }
    yield "data: " + json.dumps(done, ensure_ascii=False) + "\n\n"
    yield "data: [DONE]\n\n"


def _feedback_from_error(raw_error: SandboxEvidence | ViolationEvidence) -> FeedbackEvidence:
    if isinstance(raw_error, ViolationEvidence):
        return FeedbackEvidence(
            status="blocked",
            source_hexagram=HEX_HALT,
            next_hexagram=HEX_INSPECT,
            summary=f"Action blocked by Build Mode: {raw_error.reason}. Use scoped workspace actions only.",
        )
    return FeedbackEvidence(
        status="needs_fix",
        source_hexagram=HEX_CORRECT,
        next_hexagram=HEX_INSPECT,
        summary=f"Sandbox verification failed with exit_code={raw_error.exit_code}, status={raw_error.pytest_status}.",
    )


def _message_text(feedback: FeedbackEvidence) -> str:
    return (
        "Kernel Notice: Build Mode converted a blocked or failed action into structured feedback. "
        f"Status={feedback.status}; next_state={feedback.next_hexagram}; summary={feedback.summary}"
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python3 -m unittest tests.test_build_mode_feedback -v
```

Expected: PASS.

### Task 7: Add Archive Guard

**Files:**
- Create: `agent_skill_dictionary/build_mode_archive.py`
- Test: `tests/test_build_mode_archive.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_build_mode_archive.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from agent_skill_dictionary.build_mode_archive import finalize_manifest


class BuildModeArchiveTest(unittest.TestCase):
    def test_finalize_manifest_writes_hashes_without_lockdown_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app").mkdir()
            (root / "app" / "main.py").write_text("print('ok')\n", encoding="utf-8")
            evidence = finalize_manifest(root)
            self.assertEqual(evidence.readonly_status, "audit_only")
            manifest = root / evidence.manifest_path
            self.assertTrue(manifest.exists())
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertIn("app/main.py", data["sha256_map"])
            self.assertFalse(evidence.lockdown)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_build_mode_archive -v
```

Expected: FAIL with missing module.

- [ ] **Step 3: Implement archive guard**

Create `agent_skill_dictionary/build_mode_archive.py`:

```python
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .build_mode_types import ArchiveEvidence


def finalize_manifest(workspace_root: str | Path, lockdown: bool = False) -> ArchiveEvidence:
    root = Path(workspace_root).resolve()
    manifest_dir = root / ".yizijue"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    sha256_map = _hash_workspace(root)
    manifest_path = manifest_dir / "manifest.json"
    payload = {
        "sha256_map": sha256_map,
        "lockdown": lockdown,
        "readonly_status": "lockdown" if lockdown else "audit_only",
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if lockdown:
        _lockdown(root)
    return ArchiveEvidence(
        manifest_path=manifest_path.relative_to(root).as_posix(),
        sha256_map=sha256_map,
        readonly_status="lockdown" if lockdown else "audit_only",
        lockdown=lockdown,
    )


def _hash_workspace(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith(".yizijue/"):
            continue
        result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _lockdown(root: Path) -> None:
    for path in root.rglob("*"):
        try:
            if path.is_file():
                os.chmod(path, 0o444)
            elif path.is_dir():
                os.chmod(path, 0o555)
        except PermissionError:
            continue
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python3 -m unittest tests.test_build_mode_archive -v
```

Expected: PASS.

### Task 8: Add Evidence-Gated FSM

**Files:**
- Create: `agent_skill_dictionary/build_mode_fsm.py`
- Test: `tests/test_build_mode_fsm.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_build_mode_fsm.py`:

```python
import unittest

from agent_skill_dictionary.build_mode_fsm import next_hexagram
from agent_skill_dictionary.build_mode_types import (
    HEX_CORRECT,
    HEX_CREATE,
    HEX_HALT,
    HEX_INSPECT,
    HEX_RETURN,
    HEX_VERIFY,
    ArchiveEvidence,
    FeedbackEvidence,
    SandboxEvidence,
    ViolationEvidence,
    WriteEvidence,
)


class BuildModeFsmTest(unittest.TestCase):
    def test_create_write_success_goes_to_verify(self):
        evidence = WriteEvidence(True, ("app/main.py",), "/w", "a" * 64)
        self.assertEqual(next_hexagram(HEX_CREATE, evidence), HEX_VERIFY)

    def test_create_violation_goes_to_halt(self):
        evidence = ViolationEvidence("write:../x", "path_escape", "scoped_writer")
        self.assertEqual(next_hexagram(HEX_CREATE, evidence), HEX_HALT)

    def test_verify_success_goes_to_return(self):
        evidence = SandboxEvidence(0, "passed", "a" * 64, "b" * 64, 10)
        self.assertEqual(next_hexagram(HEX_VERIFY, evidence), HEX_RETURN)

    def test_verify_failure_goes_to_correct(self):
        evidence = SandboxEvidence(1, "failed", "a" * 64, "b" * 64, 10)
        self.assertEqual(next_hexagram(HEX_VERIFY, evidence), HEX_CORRECT)

    def test_correct_feedback_goes_to_inspect(self):
        evidence = FeedbackEvidence("needs_fix", HEX_CORRECT, HEX_INSPECT, "failed")
        self.assertEqual(next_hexagram(HEX_CORRECT, evidence), HEX_INSPECT)

    def test_archive_success_goes_to_summary_label(self):
        evidence = ArchiveEvidence(".yizijue/manifest.json", {"a": "b" * 64}, "audit_only", False)
        self.assertEqual(next_hexagram(HEX_RETURN, evidence), "总")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_build_mode_fsm -v
```

Expected: FAIL with missing module.

- [ ] **Step 3: Implement FSM**

Create `agent_skill_dictionary/build_mode_fsm.py`:

```python
from __future__ import annotations

from typing import Any

from .build_mode_types import (
    HEX_CORRECT,
    HEX_CREATE,
    HEX_HALT,
    HEX_INSPECT,
    HEX_RETURN,
    HEX_VERIFY,
    ArchiveEvidence,
    FeedbackEvidence,
    SandboxEvidence,
    ViolationEvidence,
    WriteEvidence,
)


def next_hexagram(current_hexagram: str, evidence: Any, consecutive_failures: int = 0) -> str:
    if isinstance(evidence, ViolationEvidence):
        return HEX_HALT
    if current_hexagram == HEX_CREATE and isinstance(evidence, WriteEvidence):
        if evidence.ok and evidence.changed_files:
            return HEX_VERIFY
        return HEX_CORRECT
    if current_hexagram == HEX_VERIFY and isinstance(evidence, SandboxEvidence):
        if evidence.exit_code == 0 and evidence.pytest_status == "passed":
            return HEX_RETURN
        if evidence.timed_out or evidence.oom or consecutive_failures >= 3:
            return HEX_HALT
        return HEX_CORRECT
    if current_hexagram == HEX_HALT and isinstance(evidence, ViolationEvidence):
        return HEX_CORRECT
    if current_hexagram == HEX_CORRECT and isinstance(evidence, FeedbackEvidence):
        return HEX_INSPECT if evidence.next_hexagram == HEX_INSPECT else evidence.next_hexagram
    if current_hexagram == HEX_RETURN and isinstance(evidence, ArchiveEvidence):
        if evidence.manifest_path and evidence.sha256_map:
            return "总"
        return HEX_HALT
    return HEX_HALT
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python3 -m unittest tests.test_build_mode_fsm -v
```

Expected: PASS.

### Task 9: Wire Build Mode Into Gateway Behind Feature Flag

**Files:**
- Modify: `agent_skill_dictionary/gateway_server.py`
- Test: `tests/test_gateway_server_import.py` or new `tests/test_build_mode_gateway_integration.py`

- [ ] **Step 1: Write integration test**

Create `tests/test_build_mode_gateway_integration.py`:

```python
import os
import unittest

from agent_skill_dictionary.build_mode_intent import resolve_intent
from agent_skill_dictionary.build_mode_permissions import filter_tools_schema
from agent_skill_dictionary.build_mode_types import HEX_CREATE, HEX_PROMPT


class BuildModeGatewayIntegrationTest(unittest.TestCase):
    def test_feature_flag_can_route_build_task_to_create_permissions(self):
        os.environ["ONEWORD_BUILD_MODE"] = "1"
        evidence = resolve_intent({"messages": [{"role": "user", "content": "创建一个 FastAPI 项目并运行 pytest"}]})
        tools = [
            {"type": "function", "function": {"name": "write_file", "description": "x"}},
            {"type": "function", "function": {"name": "run_pytest", "description": "x"}},
        ]
        filtered = filter_tools_schema(evidence.hexagram, tools)
        self.assertEqual(evidence.hexagram, HEX_CREATE)
        self.assertEqual([item["function"]["name"] for item in filtered], ["write_file"])
        os.environ.pop("ONEWORD_BUILD_MODE", None)

    def test_feature_flag_can_route_prompt_to_zero_tools(self):
        evidence = resolve_intent({"messages": [{"role": "user", "content": "解释一下这个项目"}]})
        self.assertEqual(evidence.hexagram, HEX_PROMPT)
        self.assertEqual(filter_tools_schema(evidence.hexagram, [{"type": "function", "function": {"name": "write_file"}}]), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run integration test**

Run:

```bash
python3 -m unittest tests.test_build_mode_gateway_integration -v
```

Expected: PASS after earlier tasks. This task intentionally verifies integration behavior before editing `gateway_server.py`.

- [ ] **Step 3: Add gateway hook with feature flag**

Modify `agent_skill_dictionary/gateway_server.py` only where requests are prepared for upstream forwarding:

```python
if os.getenv("ONEWORD_BUILD_MODE") == "1":
    from .build_mode_intent import resolve_intent
    from .build_mode_permissions import filter_tools_schema

    decision = resolve_intent(payload)
    payload["tools"] = filter_tools_schema(decision.hexagram, payload.get("tools", []))
    payload.setdefault("metadata", {})
    payload["metadata"]["oneword_build_mode"] = {
        "hexagram": decision.hexagram,
        "quadrant": decision.quadrant,
        "yin_yang": decision.yin_yang,
        "reasons": list(decision.reasons),
    }
```

Use local helper functions if `gateway_server.py` already has an upstream payload preparation helper. Do not change default behavior when `ONEWORD_BUILD_MODE` is unset.

- [ ] **Step 4: Run focused gateway tests**

Run:

```bash
python3 -m unittest tests.test_gateway_server_import tests.test_build_mode_gateway_integration -v
```

Expected: PASS.

### Task 10: Final Verification And Documentation Links

**Files:**
- Modify: `README.md`
- Modify: `docs/project-status.md`

- [ ] **Step 1: Add docs links**

Add a short section to `README.md` under the current phase notes:

```markdown
## Build Mode V2 Design

Build Mode V2 is documented as a design target, not yet a completed runtime:

- `docs/build-mode-kernel-rules.md`
- `docs/hexagram-rules.md`
- `docs/build-mode-mvp-implementation-plan.md`
```

Add the same three links to `docs/project-status.md` under current boundaries, with this wording:

```markdown
Build Mode V2 currently has design and implementation-plan documents. The full runtime should not be considered complete until the six MVP modules and their evidence-gated tests pass.
```

- [ ] **Step 2: Run full focused Build Mode test set**

Run:

```bash
python3 -m unittest \
  tests.test_build_mode_types \
  tests.test_build_mode_intent \
  tests.test_build_mode_permissions \
  tests.test_build_mode_writer \
  tests.test_build_mode_sandbox \
  tests.test_build_mode_feedback \
  tests.test_build_mode_archive \
  tests.test_build_mode_fsm \
  tests.test_build_mode_gateway_integration -v
```

Expected: PASS.

- [ ] **Step 3: Run existing smoke tests that touch reused modules**

Run:

```bash
python3 -m unittest \
  tests.test_executor \
  tests.test_patch_executor \
  tests.test_tool_guard \
  tests.test_path_sentinels \
  tests.test_gateway_server_import -v
```

Expected: PASS.

## 6. Acceptance Criteria

The MVP implementation is acceptable only if all these are true:

| Requirement | Evidence |
| --- | --- |
| Build tasks route to `乾 111` | `tests.test_build_mode_intent` |
| Pure questions route to `巽 011` and clear tools | `tests.test_build_mode_permissions` |
| Read tools map to `离 101` repo card path | `tests.test_build_mode_permissions` |
| Write tools map to scoped writer | `tests.test_build_mode_permissions` and `tests.test_build_mode_writer` |
| Test commands map to sandbox runner | `tests.test_build_mode_permissions` and `tests.test_build_mode_sandbox` |
| Dangerous commands map to `艮 100` | `tests.test_build_mode_permissions` and `tests.test_build_mode_fsm` |
| Soft feedback returns HTTP 200 and empty stderr | `tests.test_build_mode_feedback` |
| Completion requires sandbox pass plus manifest | `tests.test_build_mode_types` |
| Archive does not chmod by default | `tests.test_build_mode_archive` |
| Gateway behavior is feature-flagged | `tests.test_build_mode_gateway_integration` |

## 7. Explicit Non-Goals

- No public benchmark claims in this implementation pass.
- No default `chmod 444`.
- No default transparent hijacking of every local CLI tool.
- No production Docker hardening beyond the existing executor wrapper.
- No rewrite of the V1 root-word model.

## 8. Self-Review

- Spec coverage: The plan covers shadow tool mapping, Evidence DTOs, soft feedback stream tunnelling, six MVP modules, edge halt paths, and feature-flagged gateway wiring.
- Placeholder scan: No `TBD` or `TODO` placeholders are intentionally left.
- Type consistency: All task snippets use the DTO and constant names defined in Task 1.
