# OneCode Claw-Code Rule Absorption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first OneCode-native absorption layer for project context evidence, runtime config inspection, and advisory recovery policy while folding every new diagnostic result back through 易经八卦, 阴阳, 五行, and `IchingKernel`.

**Architecture:** Add three focused kernel modules: `project_context`, `runtime_config`, and `recovery_policy`. These modules only produce bounded evidence and summaries; `doctor`, Web API project status, and shell projection expose those summaries after rule folding. No external rule source bypasses `IchingKernel`, and no Web/API surface exposes imported rule file content by default.

**Tech Stack:** Python 3.11 standard library, `unittest`, existing OneCode kernel modules, existing CLI/Web API.

---

## File Structure

- Create `src/onecode/kernel/project_context.py`: discovers rule/instruction files, dedupes by normalized content hash, enforces metadata-only summaries by default, and emits rule-folded summary status.
- Create `tests/test_project_context.py`: focused discovery, import-control, ordering, dedupe, metadata, and boundary tests.
- Create `src/onecode/kernel/runtime_config.py`: inspects optional OneCode config files, reports per-file status, parses `rulesImport`, and folds inspection status through `IchingKernel`.
- Create `tests/test_runtime_config.py`: optional config success/error/partial-load tests.
- Create `src/onecode/kernel/recovery_policy.py`: maps known failure scenarios to advisory recovery actions and Iching status.
- Create `tests/test_recovery_policy.py`: scenario mapping, attempt count, exhaustion, and rule-folding tests.
- Modify `src/onecode/cli.py`: add doctor checks for project context, runtime config, and recovery policy.
- Modify `tests/test_doctor_cli.py`: update doctor expected check list and verify new check details include Iching fields.
- Modify `src/onecode/web/api.py`: include `project_context` and `runtime_config` summaries in project status.
- Modify `tests/test_web_api.py`: assert project status summaries and no raw content exposure.
- Modify `src/onecode/kernel/shell_projection.py`: add optional `control_state` summary to shell projection schema.
- Modify `tests/test_shell_projection.py`: assert schema and projection are stable.
- Modify `README.md`: briefly document the absorbed rule-evidence layer and its constraints.

---

### Task 1: Project Context Discovery

**Files:**
- Create: `src/onecode/kernel/project_context.py`
- Create: `tests/test_project_context.py`

- [ ] **Step 1: Write failing project context tests**

Create `tests/test_project_context.py` with:

```python
import hashlib
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.project_context import RulesImport, discover_project_context


class ProjectContextDiscoveryTests(unittest.TestCase):
    def test_discovers_sorted_rule_files_and_dedupes_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / ".git").mkdir()
            (workspace / "AGENTS.md").write_text("root rule\n", encoding="utf-8")
            rules = workspace / ".onecode" / "rules"
            rules.mkdir(parents=True)
            (rules / "b.md").write_text("shared b\n", encoding="utf-8")
            (rules / "a.txt").write_text("shared a\n", encoding="utf-8")
            (rules / "dup.mdc").write_text("shared a\n\n", encoding="utf-8")

            report = discover_project_context(workspace)

        self.assertEqual(report["status"], "ok")
        self.assertEqual([item["path"] for item in report["memory_files"]], ["AGENTS.md", ".onecode/rules/a.txt", ".onecode/rules/b.md"])
        self.assertEqual(report["summary"]["file_count"], 3)
        self.assertEqual(report["summary"]["deduped_count"], 1)
        self.assertEqual(report["summary"]["element"], "wood")
        self.assertEqual(report["summary"]["yin_yang_pressure"], "stable")
        self.assertEqual(
            report["iching_status_code"],
            IchingKernel.compute_status(IchingKernel.XUN, IchingKernel.ZHEN),
        )
        self.assertEqual(len(report["memory_files"][0]["content_sha256"]), 64)

    def test_local_rules_are_reported_as_local_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            local_rules = workspace / ".onecode" / "rules.local"
            local_rules.mkdir(parents=True)
            (local_rules / "personal.md").write_text("personal local rule\n", encoding="utf-8")

            report = discover_project_context(workspace)

        self.assertEqual(report["memory_files"][0]["origin"], "local")
        self.assertEqual(report["memory_files"][0]["source"], "onecode_rules_local")
        self.assertTrue(report["memory_files"][0]["contributes"])

    def test_imported_framework_rules_can_be_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / ".cursorrules").write_text("cursor rule\n", encoding="utf-8")
            github = workspace / ".github"
            github.mkdir()
            (github / "copilot-instructions.md").write_text("copilot rule\n", encoding="utf-8")

            disabled = discover_project_context(workspace, rules_import=RulesImport.none())
            selected = discover_project_context(workspace, rules_import=RulesImport.list(["copilot"]))

        self.assertEqual(disabled["memory_files"], [])
        self.assertEqual([item["source"] for item in selected["memory_files"]], ["copilot_instructions"])

    def test_project_context_metadata_does_not_expose_raw_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "AGENTS.md").write_text("secret-ish instruction\n", encoding="utf-8")

            report = discover_project_context(workspace)

        item = report["memory_files"][0]
        self.assertNotIn("content", item)
        self.assertEqual(item["chars"], len("secret-ish instruction\n"))
        self.assertEqual(item["content_sha256"], hashlib.sha256(b"secret-ish instruction\n").hexdigest())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_project_context -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'onecode.kernel.project_context'`.

- [ ] **Step 3: Implement project context discovery**

Create `src/onecode/kernel/project_context.py`:

```python
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from onecode.kernel.hexagram import IchingKernel

SUPPORTED_RULE_SUFFIXES = {".md", ".txt", ".mdc"}
MAX_FILE_CHARS = 4_000
MAX_TOTAL_CHARS = 12_000


@dataclass(frozen=True)
class RulesImport:
    mode: str
    frameworks: tuple[str, ...] = ()

    @classmethod
    def auto(cls) -> "RulesImport":
        return cls("auto")

    @classmethod
    def none(cls) -> "RulesImport":
        return cls("none")

    @classmethod
    def list(cls, frameworks: list[str]) -> "RulesImport":
        return cls("list", tuple(item.lower() for item in frameworks))

    def should_import(self, framework: str) -> bool:
        if self.mode == "auto":
            return True
        if self.mode == "none":
            return False
        return framework.lower() in self.frameworks


@dataclass(frozen=True)
class Candidate:
    path: Path
    source: str
    origin: str


def discover_project_context(workspace: Path, *, rules_import: RulesImport | None = None) -> dict:
    root = workspace.resolve()
    import_policy = rules_import or RulesImport.auto()
    candidates = list(_candidate_files(root, import_policy))
    memory_files = []
    seen_hashes: set[str] = set()
    total_chars = 0
    deduped_count = 0
    invalid_files = []

    for candidate in candidates:
        try:
            content = candidate.path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            invalid_files.append(_invalid_file(root, candidate.path, "decode_error", str(exc)))
            continue
        except OSError as exc:
            invalid_files.append(_invalid_file(root, candidate.path, "read_error", str(exc)))
            continue
        if not content.strip():
            continue
        normalized_hash = hashlib.sha256(_normalize(content).encode("utf-8")).hexdigest()
        if normalized_hash in seen_hashes:
            deduped_count += 1
            continue
        seen_hashes.add(normalized_hash)
        if total_chars >= MAX_TOTAL_CHARS:
            break
        contributes = total_chars + min(len(content), MAX_FILE_CHARS) <= MAX_TOTAL_CHARS
        total_chars += min(len(content), MAX_FILE_CHARS)
        memory_files.append(
            {
                "path": _relpath(root, candidate.path),
                "source": candidate.source,
                "origin": candidate.origin,
                "scope_path": str(root),
                "outside_project": not _inside_root(candidate.path.resolve(), root),
                "chars": len(content),
                "contributes": contributes,
                "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            }
        )

    status = "warning" if invalid_files else "ok"
    status_code = _status_code(status)
    transition = IchingKernel.transition(status_code)
    return {
        "status": status,
        "memory_files": memory_files,
        "invalid_files": invalid_files,
        "summary": {
            "file_count": len(memory_files),
            "invalid_count": len(invalid_files),
            "deduped_count": deduped_count,
            "total_chars": sum(item["chars"] for item in memory_files),
            "element": "wood",
            "yin_yang_pressure": "stable" if status == "ok" else "activate",
        },
        "iching_status_code": status_code,
        "iching_transition_action": transition.action,
        "iching_transition_reason": transition.reason,
        "dispatch_decision": IchingKernel.dispatch_decision(transition),
    }


def _candidate_files(root: Path, rules_import: RulesImport) -> Iterable[Candidate]:
    for relative, source, origin in [
        ("AGENTS.md", "agents_md", "project"),
        ("CLAUDE.md", "claude_md", "project"),
        ("CLAW.md", "claw_md", "project"),
        (".onecode/instructions.md", "onecode_instructions", "project"),
    ]:
        path = root / relative
        if path.is_file():
            yield Candidate(path, source, origin)
    yield from _rules_dir(root / ".onecode" / "rules", "onecode_rules", "project")
    yield from _rules_dir(root / ".onecode" / "rules.local", "onecode_rules_local", "local")
    if rules_import.should_import("cursor"):
        cursor = root / ".cursorrules"
        if cursor.is_file():
            yield Candidate(cursor, "cursor_rules", "imported")
        yield from _rules_dir(root / ".cursor" / "rules", "cursor_rules_dir", "imported")
    if rules_import.should_import("copilot"):
        copilot = root / ".github" / "copilot-instructions.md"
        if copilot.is_file():
            yield Candidate(copilot, "copilot_instructions", "imported")
    if rules_import.should_import("windsurf"):
        windsurf = root / ".windsurfrules"
        if windsurf.is_file():
            yield Candidate(windsurf, "windsurf_rules", "imported")
    if rules_import.should_import("plandex"):
        plandex = root / ".plandex" / "instructions.md"
        if plandex.is_file():
            yield Candidate(plandex, "plandex_instructions", "imported")


def _rules_dir(path: Path, source: str, origin: str) -> Iterable[Candidate]:
    if not path.is_dir():
        return []
    return [
        Candidate(item, source, origin)
        for item in sorted(path.iterdir())
        if item.is_file() and item.suffix.lower() in SUPPORTED_RULE_SUFFIXES
    ]


def _normalize(content: str) -> str:
    lines = []
    previous_blank = False
    for line in content.lines():
        blank = not line.strip()
        if blank and previous_blank:
            continue
        lines.append(line.rstrip())
        previous_blank = blank
    return "\n".join(lines).strip()


def _inside_root(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _relpath(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return str(path.resolve())


def _invalid_file(root: Path, path: Path, reason: str, detail: str) -> dict:
    return {"path": _relpath(root, path), "reason": reason, "detail": detail}


def _status_code(status: str) -> int:
    if status == "ok":
        return IchingKernel.compute_status(IchingKernel.XUN, IchingKernel.ZHEN)
    return IchingKernel.compute_status(IchingKernel.XUN, IchingKernel.KAN)
```

- [ ] **Step 4: Run project context tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_project_context -v
```

Expected: PASS.

- [ ] **Step 5: Commit project context discovery**

```bash
git add src/onecode/kernel/project_context.py tests/test_project_context.py
git commit -m "feat: add project context evidence discovery"
```

---

### Task 2: Runtime Config Inspection

**Files:**
- Create: `src/onecode/kernel/runtime_config.py`
- Create: `tests/test_runtime_config.py`

- [ ] **Step 1: Write failing runtime config tests**

Create `tests/test_runtime_config.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.runtime_config import inspect_runtime_config, parse_rules_import


class RuntimeConfigInspectionTests(unittest.TestCase):
    def test_missing_optional_configs_report_not_found_without_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            home = Path(tmp) / "home"
            with patch.dict("os.environ", {"ONECODE_HOME": str(home)}, clear=False):
                report = inspect_runtime_config(workspace)

        self.assertEqual(report["status"], "ok")
        self.assertEqual([item["status"] for item in report["files"]], ["not_found", "not_found", "not_found"])
        self.assertEqual(report["summary"]["loaded_count"], 0)
        self.assertEqual(report["summary"]["element"], "earth")

    def test_valid_and_invalid_sibling_configs_are_reported_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            config_dir = workspace / ".onecode"
            config_dir.mkdir(parents=True)
            (config_dir / "config.json").write_text(json.dumps({"rulesImport": "none"}), encoding="utf-8")
            (config_dir / "config.local.json").write_text("{bad json", encoding="utf-8")
            home = Path(tmp) / "home"
            with patch.dict("os.environ", {"ONECODE_HOME": str(home)}, clear=False):
                report = inspect_runtime_config(workspace)

        self.assertEqual(report["status"], "warning")
        self.assertEqual(report["summary"]["loaded_count"], 1)
        self.assertEqual(report["summary"]["load_error_count"], 1)
        self.assertEqual(report["effective"]["rulesImport"], "none")
        self.assertEqual(
            report["iching_status_code"],
            IchingKernel.compute_status(IchingKernel.GEN, IchingKernel.KAN),
        )

    def test_parse_rules_import_accepts_string_and_list_forms(self):
        self.assertEqual(parse_rules_import({"rulesImport": "none"}).mode, "none")
        self.assertEqual(parse_rules_import({"rulesImport": ["cursor", "copilot"]}).frameworks, ("cursor", "copilot"))
        self.assertEqual(parse_rules_import({}).mode, "auto")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_runtime_config -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'onecode.kernel.runtime_config'`.

- [ ] **Step 3: Implement runtime config inspection**

Create `src/onecode/kernel/runtime_config.py`:

```python
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.project_context import RulesImport


@dataclass(frozen=True)
class ConfigPath:
    source: str
    path: Path


def inspect_runtime_config(workspace: Path) -> dict[str, Any]:
    root = workspace.resolve()
    merged: dict[str, Any] = {}
    files = []
    warnings = []
    for index, entry in enumerate(_config_paths(root), start=1):
        if not entry.path.exists():
            files.append(_file_report(entry, index, "not_found"))
            continue
        try:
            payload = json.loads(entry.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            files.append(_file_report(entry, index, "load_error", reason="json_parse_error", detail=str(exc)))
            continue
        if not isinstance(payload, dict):
            files.append(_file_report(entry, index, "load_error", reason="not_object", detail="config must be a JSON object"))
            continue
        validation_warnings = _warnings_for(payload)
        warnings.extend(validation_warnings)
        merged.update(payload)
        files.append(_file_report(entry, index, "loaded", key_paths=sorted(payload.keys()), warnings=validation_warnings))

    load_error_count = sum(1 for item in files if item["status"] == "load_error")
    status = "warning" if load_error_count else "ok"
    status_code = _status_code(status)
    transition = IchingKernel.transition(status_code)
    rules_import = parse_rules_import(merged)
    return {
        "status": status,
        "files": files,
        "warnings": warnings,
        "effective": {"rulesImport": _rules_import_value(rules_import)},
        "summary": {
            "loaded_count": sum(1 for item in files if item["status"] == "loaded"),
            "not_found_count": sum(1 for item in files if item["status"] == "not_found"),
            "load_error_count": load_error_count,
            "element": "earth",
            "yin_yang_pressure": "activate" if load_error_count else "stable",
        },
        "iching_status_code": status_code,
        "iching_transition_action": transition.action,
        "iching_transition_reason": transition.reason,
        "dispatch_decision": IchingKernel.dispatch_decision(transition),
    }


def parse_rules_import(config: dict[str, Any]) -> RulesImport:
    value = config.get("rulesImport")
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "none":
            return RulesImport.none()
        if normalized == "auto":
            return RulesImport.auto()
    if isinstance(value, list):
        return RulesImport.list([item for item in value if isinstance(item, str)])
    return RulesImport.auto()


def _config_paths(root: Path) -> list[ConfigPath]:
    home = Path(os.getenv("ONECODE_HOME", "~/.onecode")).expanduser()
    return [
        ConfigPath("user", home / "config.json"),
        ConfigPath("project", root / ".onecode" / "config.json"),
        ConfigPath("local", root / ".onecode" / "config.local.json"),
    ]


def _file_report(
    entry: ConfigPath,
    precedence_rank: int,
    status: str,
    *,
    reason: str | None = None,
    detail: str | None = None,
    key_paths: list[str] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "source": entry.source,
        "path": str(entry.path),
        "status": status,
        "loaded": status == "loaded",
        "reason": reason,
        "detail": detail,
        "precedence_rank": precedence_rank,
        "key_paths": key_paths or [],
        "warnings": warnings or [],
    }


def _warnings_for(payload: dict[str, Any]) -> list[str]:
    warnings = []
    if "rulesImport" in payload and not isinstance(payload["rulesImport"], (str, list)):
        warnings.append("rulesImport must be string or list; falling back to auto")
    return warnings


def _rules_import_value(value: RulesImport) -> str | list[str]:
    if value.mode == "list":
        return list(value.frameworks)
    return value.mode


def _status_code(status: str) -> int:
    if status == "ok":
        return IchingKernel.compute_status(IchingKernel.GEN, IchingKernel.KUN)
    return IchingKernel.compute_status(IchingKernel.GEN, IchingKernel.KAN)
```

- [ ] **Step 4: Run runtime config tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_runtime_config -v
```

Expected: PASS.

- [ ] **Step 5: Commit runtime config inspection**

```bash
git add src/onecode/kernel/runtime_config.py tests/test_runtime_config.py
git commit -m "feat: inspect runtime config evidence"
```

---

### Task 3: Advisory Recovery Policy

**Files:**
- Create: `src/onecode/kernel/recovery_policy.py`
- Create: `tests/test_recovery_policy.py`

- [ ] **Step 1: Write failing recovery policy tests**

Create `tests/test_recovery_policy.py`:

```python
import unittest

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.recovery_policy import RecoveryContext, recovery_status


class RecoveryPolicyTests(unittest.TestCase):
    def test_each_initial_scenario_maps_to_bounded_action_and_iching_status(self):
        expected_actions = {
            "trace_flush_failure": "repair",
            "verifier_failure": "repair",
            "resume_conflict": "inspect",
            "sandbox_failure": "reconfigure",
            "provider_failure": "retry_once",
            "config_partial_invalid": "inspect",
            "project_context_invalid": "inspect",
        }
        for scenario, action in expected_actions.items():
            with self.subTest(scenario=scenario):
                status = recovery_status(scenario)
                self.assertEqual(status["recommended_action"], action)
                self.assertEqual(status["attempted"], False)
                self.assertEqual(status["element"], "fire")
                self.assertIn("iching_status_code", status)
                self.assertIn("dispatch_decision", status)

    def test_attempts_are_limited_and_exhaustion_halts(self):
        context = RecoveryContext()
        first = context.record_attempt("provider_failure", success=False)
        second = context.record_attempt("provider_failure", success=False)

        self.assertEqual(first["attempt_count"], 1)
        self.assertEqual(first["attempts_remaining"], 1)
        self.assertEqual(second["state"], "exhausted")
        self.assertEqual(second["recommended_action"], "halt")
        self.assertEqual(
            second["iching_status_code"],
            IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN),
        )

    def test_successful_attempt_records_recovered_state(self):
        context = RecoveryContext()
        result = context.record_attempt("verifier_failure", success=True)

        self.assertEqual(result["state"], "succeeded")
        self.assertEqual(result["recommended_action"], "inspect")
        self.assertEqual(result["attempt_count"], 1)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_recovery_policy -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'onecode.kernel.recovery_policy'`.

- [ ] **Step 3: Implement advisory recovery policy**

Create `src/onecode/kernel/recovery_policy.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field

from onecode.kernel.hexagram import IchingKernel


SCENARIO_ACTIONS = {
    "trace_flush_failure": "repair",
    "verifier_failure": "repair",
    "resume_conflict": "inspect",
    "sandbox_failure": "reconfigure",
    "provider_failure": "retry_once",
    "config_partial_invalid": "inspect",
    "project_context_invalid": "inspect",
}
MAX_ATTEMPTS = 2


@dataclass
class RecoveryContext:
    attempts: dict[str, int] = field(default_factory=dict)

    def record_attempt(self, scenario: str, *, success: bool) -> dict:
        count = self.attempts.get(scenario, 0) + 1
        self.attempts[scenario] = count
        if success:
            return recovery_status(scenario, attempted=True, attempt_count=count, state="succeeded", recommended_action="inspect")
        if count >= MAX_ATTEMPTS:
            return recovery_status(scenario, attempted=True, attempt_count=count, state="exhausted", recommended_action="halt")
        return recovery_status(scenario, attempted=True, attempt_count=count, state="failed")


def recovery_status(
    scenario: str,
    *,
    attempted: bool = False,
    attempt_count: int = 0,
    state: str = "queued",
    recommended_action: str | None = None,
) -> dict:
    action = recommended_action or SCENARIO_ACTIONS.get(scenario, "inspect")
    attempts_remaining = max(0, MAX_ATTEMPTS - attempt_count)
    status_code = _status_code(state, action)
    transition = IchingKernel.transition(status_code)
    return {
        "scenario": scenario,
        "status": "ok" if state in {"queued", "succeeded"} else "warning",
        "attempted": attempted,
        "attempt_count": attempt_count,
        "attempts_remaining": attempts_remaining,
        "retry_limit": MAX_ATTEMPTS,
        "state": state,
        "recommended_action": action,
        "element": "fire",
        "yin_yang_pressure": "activate" if state not in {"queued", "succeeded"} else "stable",
        "iching_status_code": status_code,
        "iching_transition_action": transition.action,
        "iching_transition_reason": transition.reason,
        "dispatch_decision": IchingKernel.dispatch_decision(transition),
    }


def _status_code(state: str, action: str) -> int:
    if state == "exhausted" or action == "halt":
        return IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN)
    if state == "succeeded":
        return IchingKernel.compute_status(IchingKernel.LI, IchingKernel.GEN)
    return IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KAN)
```

- [ ] **Step 4: Run recovery policy tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_recovery_policy -v
```

Expected: PASS.

- [ ] **Step 5: Commit recovery policy**

```bash
git add src/onecode/kernel/recovery_policy.py tests/test_recovery_policy.py
git commit -m "feat: add advisory recovery policy"
```

---

### Task 4: Doctor And Audit Integration

**Files:**
- Modify: `src/onecode/cli.py`
- Modify: `tests/test_doctor_cli.py`

- [ ] **Step 1: Update failing doctor test expectations**

Modify `tests/test_doctor_cli.py` in `test_cli_doctor_runs_core_smoke_checks`:

```python
self.assertEqual(
    [check["name"] for check in result["checks"]],
    [
        "write_text",
        "resume_skip",
        "sovereignty_breach",
        "http_timeout",
        "project_context",
        "runtime_config",
        "recovery_policy",
    ],
)
```

Add after the existing run-id assertions:

```python
self.assertEqual(result["checks"][4]["detail"]["summary"]["element"], "wood")
self.assertEqual(result["checks"][5]["detail"]["summary"]["element"], "earth")
self.assertEqual(result["checks"][6]["detail"]["element"], "fire")
for check in result["checks"][4:]:
    self.assertIn("iching_status_code", check["detail"])
    self.assertIn("iching_transition_action", check["detail"])
    self.assertIn("dispatch_decision", check["detail"])
```

- [ ] **Step 2: Run doctor test to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_doctor_cli.DoctorCliTests.test_cli_doctor_runs_core_smoke_checks -v
```

Expected: FAIL because `run_doctor()` does not include the three new checks.

- [ ] **Step 3: Wire doctor checks**

Modify imports in `src/onecode/cli.py`:

```python
from onecode.kernel.project_context import discover_project_context
from onecode.kernel.runtime_config import inspect_runtime_config
from onecode.kernel.recovery_policy import recovery_status
```

At the end of `run_doctor()`, before returning, add:

```python
        project_context = discover_project_context(workspace)
        checks.append(
            doctor_check(
                "project_context",
                project_context["status"] in {"ok", "warning"},
                project_context,
            )
        )

        runtime_config = inspect_runtime_config(workspace)
        checks.append(
            doctor_check(
                "runtime_config",
                runtime_config["status"] in {"ok", "warning"},
                runtime_config,
            )
        )

        recovery = recovery_status("provider_failure")
        checks.append(
            doctor_check(
                "recovery_policy",
                recovery["recommended_action"] == "retry_once",
                recovery,
            )
        )
```

- [ ] **Step 4: Run doctor tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_doctor_cli -v
```

Expected: PASS.

- [ ] **Step 5: Commit doctor integration**

```bash
git add src/onecode/cli.py tests/test_doctor_cli.py
git commit -m "feat: expose absorbed rule evidence in doctor"
```

---

### Task 5: Web API Project Status Summaries

**Files:**
- Modify: `src/onecode/web/api.py`
- Modify: `tests/test_web_api.py`

- [ ] **Step 1: Add failing Web API status test**

Append to `OneCodeWebApiTests` in `tests/test_web_api.py`:

```python
    def test_project_status_includes_context_and_config_summaries_without_raw_rule_content(self):
        from onecode.web.api import project_status_payload

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "AGENTS.md").write_text("private instruction body\n", encoding="utf-8")
            payload = project_status_payload(workspace)

        self.assertIn("project_context", payload)
        self.assertIn("runtime_config", payload)
        self.assertEqual(payload["project_context"]["summary"]["element"], "wood")
        self.assertEqual(payload["runtime_config"]["summary"]["element"], "earth")
        self.assertNotIn("content", json.dumps(payload["project_context"]))
        self.assertIn("content_sha256", payload["project_context"]["memory_files"][0])
```

- [ ] **Step 2: Run Web API test to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_web_api.OneCodeWebApiTests.test_project_status_includes_context_and_config_summaries_without_raw_rule_content -v
```

Expected: FAIL because `project_status_payload()` does not include the new summaries.

- [ ] **Step 3: Wire Web API project status**

Modify imports in `src/onecode/web/api.py`:

```python
from onecode.kernel.project_context import discover_project_context
from onecode.kernel.runtime_config import inspect_runtime_config
```

In `project_status_payload()`, add these fields to the returned dict:

```python
        "project_context": discover_project_context(resolved),
        "runtime_config": inspect_runtime_config(resolved),
```

- [ ] **Step 4: Run Web API tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_web_api -v
```

Expected: PASS.

- [ ] **Step 5: Commit Web API integration**

```bash
git add src/onecode/web/api.py tests/test_web_api.py
git commit -m "feat: expose project rule evidence in api status"
```

---

### Task 6: Shell Projection Control State

**Files:**
- Modify: `src/onecode/kernel/shell_projection.py`
- Modify: `tests/test_shell_projection.py`

- [ ] **Step 1: Add failing shell projection tests**

Modify `tests/test_shell_projection.py` imports in `test_shell_projection_schema_is_explicit_and_stable` to include:

```python
            CONTROL_STATE_FIELDS,
```

Add after resume state assertion:

```python
self.assertEqual(tuple(projection["control_state"].keys()), CONTROL_STATE_FIELDS)
```

In `test_shell_projection_schema_payload_is_machine_readable`, add:

```python
self.assertEqual(schema["nested_fields"]["control_state"], ["project_context_status", "runtime_config_status", "recovery_action"])
```

Add a new test:

```python
    def test_shell_projection_projects_optional_control_state(self):
        from onecode.kernel.shell_projection import project_run_to_shell

        projection = project_run_to_shell(
            {
                "run_id": "control-run",
                "status": "completed",
                "project_context": {"status": "ok"},
                "runtime_config": {"status": "warning"},
                "recovery_policy": {"recommended_action": "inspect"},
            }
        )

        self.assertEqual(projection["control_state"]["project_context_status"], "ok")
        self.assertEqual(projection["control_state"]["runtime_config_status"], "warning")
        self.assertEqual(projection["control_state"]["recovery_action"], "inspect")
```

- [ ] **Step 2: Run shell projection tests to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_shell_projection -v
```

Expected: FAIL because `control_state` does not exist.

- [ ] **Step 3: Add optional control state projection**

Modify `src/onecode/kernel/shell_projection.py`:

```python
CONTROL_STATE_FIELDS = (
    "project_context_status",
    "runtime_config_status",
    "recovery_action",
)
```

Add `"control_state"` to `SHELL_PROJECTION_FIELDS` after `"resume_state"`.

In `shell_projection_schema()`, add:

```python
            "control_state": {"type": "object", "fields": list(CONTROL_STATE_FIELDS)},
```

and add to `nested_fields`:

```python
            "control_state": list(CONTROL_STATE_FIELDS),
```

In `project_run_to_shell()`, add:

```python
        "control_state": _control_state(run),
```

Add helper:

```python
def _control_state(run: dict[str, Any]) -> dict[str, Any]:
    project_context = run.get("project_context")
    runtime_config = run.get("runtime_config")
    recovery_policy = run.get("recovery_policy")
    return {
        "project_context_status": _string(project_context.get("status")) if isinstance(project_context, dict) else None,
        "runtime_config_status": _string(runtime_config.get("status")) if isinstance(runtime_config, dict) else None,
        "recovery_action": _string(recovery_policy.get("recommended_action")) if isinstance(recovery_policy, dict) else None,
    }
```

- [ ] **Step 4: Run shell projection tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_shell_projection -v
```

Expected: PASS.

- [ ] **Step 5: Commit shell projection integration**

```bash
git add src/onecode/kernel/shell_projection.py tests/test_shell_projection.py
git commit -m "feat: project control state in shell projection"
```

---

### Task 7: Documentation And Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document the absorbed rule-evidence layer**

Add a short section after `## v0.2 Hardening Foundations` in `README.md`:

```markdown
## Rule Evidence Absorption Layer

OneCode can inspect project instruction files, optional runtime config, and advisory recovery scenarios as bounded evidence. These inputs are not independent rules. They are folded through `IchingKernel` into six-bit status codes, yin-yang pressure, five-element interpretation, transition action, and dispatch decision.

The default project status and doctor surfaces expose metadata such as paths, sources, character counts, and SHA256 digests. They do not expose raw imported rule content by default.
```

- [ ] **Step 2: Run focused tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_project_context tests.test_runtime_config tests.test_recovery_policy tests.test_doctor_cli tests.test_web_api tests.test_shell_projection -v
```

Expected: PASS.

- [ ] **Step 3: Run doctor smoke**

Run:

```bash
PYTHONPATH=src python3 -m onecode doctor
```

Expected: JSON with `"status": "ok"` and checks named `project_context`, `runtime_config`, and `recovery_policy`.

- [ ] **Step 4: Run core verification**

Run:

```bash
bash scripts/verify-core.sh
```

Expected: PASS.

- [ ] **Step 5: Commit documentation and final verification**

```bash
git add README.md
git commit -m "docs: document rule evidence absorption layer"
```

---

## Self-Review

- Spec coverage: project context evidence is covered by Task 1 and Task 5; runtime config inspection is covered by Task 2 and Task 5; advisory recovery policy is covered by Task 3 and Task 4; doctor/API/shell exposure is covered by Tasks 4-6; documentation and verification are covered by Task 7.
- Boundary coverage: every new module emits `iching_status_code`, `iching_transition_action`, `iching_transition_reason`, and `dispatch_decision`; raw rule content is explicitly excluded from default metadata and tested through Web API.
- Scope check: permission-mode vocabulary, hooks, MCP runtime, automatic recovery execution, and session persistence hygiene remain out of this first implementation milestone.
- Type consistency: `project_context`, `runtime_config`, and `recovery_policy` are the cross-surface payload names; status fields use `status`, `summary`, `iching_status_code`, `iching_transition_action`, `iching_transition_reason`, and `dispatch_decision`.

