# OneCode Skill Rule Kernel Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only `skill_context` layer that treats skills as bounded rule evidence and folds them through `IchingKernel` without enabling direct skill execution.

**Architecture:** Create `src/onecode/kernel/skill_context.py` as the registry/manifest inspection boundary. Add `IchingKernel.classify_skill_context()` as the only classifier that turns skill evidence into a status code. Wire redacted skill summaries into `doctor` and Web project status while preserving existing guarded execution paths.

**Tech Stack:** Python 3.11+, stdlib `json`, `hashlib`, `dataclasses`, `pathlib`, `unittest`, existing OneCode CLI/Web/kernel modules.

---

## File Map

- Create: `src/onecode/kernel/skill_context.py`
- Create: `tests/test_skill_context.py`
- Modify: `src/onecode/kernel/hexagram.py`
- Modify: `tests/test_iching_kernel.py`
- Modify: `src/onecode/cli.py`
- Modify: `tests/test_doctor_cli.py`
- Modify: `src/onecode/web/api.py`
- Modify: `tests/test_web_api.py`
- Modify: `README.md`

## Public Contracts

Phase 1 exposes only read-only skill metadata:

```python
from onecode.kernel.skill_context import discover_skill_context

payload = discover_skill_context(workspace)
```

Skill manifests live under:

```text
.onecode/skills/*.json
```

No skill body or instruction text is exposed by default. No executable skill action is introduced in this phase.

## Task 1: Add Skill Context Discovery Tests

**Files:**
- Create: `tests/test_skill_context.py`

- [x] **Step 1: Write failing tests for valid, invalid, duplicate, and escaping skill manifests**

Create `tests/test_skill_context.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path


class SkillContextTests(unittest.TestCase):
    def test_discovers_valid_project_skill_manifest_without_raw_body(self):
        from onecode.kernel.skill_context import discover_skill_context

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            skill_dir = workspace / ".onecode" / "skills"
            skill_dir.mkdir(parents=True)
            (skill_dir / "code-test-regression.json").write_text(
                json.dumps(
                    {
                        "name": "code-test-regression",
                        "version": "1",
                        "description": "Guides regression test creation.",
                        "capabilities": ["test", "verification"],
                        "risk": "low",
                        "mode": "method_only",
                        "allowed_tools": ["pytest"],
                        "verifier_expectations": ["focused_test"],
                    }
                ),
                encoding="utf-8",
            )

            payload = discover_skill_context(workspace)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["summary"]["skill_count"], 1)
        self.assertEqual(payload["summary"]["element"], "water")
        self.assertEqual(payload["skills"][0]["name"], "code-test-regression")
        self.assertEqual(payload["skills"][0]["source"], "project")
        self.assertEqual(payload["skills"][0]["risk"], "low")
        self.assertEqual(payload["skills"][0]["mode"], "method_only")
        self.assertEqual(payload["skills"][0]["capability_count"], 2)
        self.assertIn("content_sha256", payload["skills"][0])
        self.assertNotIn("Guides regression test creation.", json.dumps(payload))

    def test_invalid_skill_manifest_is_reported_without_loading(self):
        from onecode.kernel.skill_context import discover_skill_context

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            skill_dir = workspace / ".onecode" / "skills"
            skill_dir.mkdir(parents=True)
            (skill_dir / "bad.json").write_text("{not json", encoding="utf-8")

            payload = discover_skill_context(workspace)

        self.assertEqual(payload["status"], "warning")
        self.assertEqual(payload["summary"]["skill_count"], 0)
        self.assertEqual(payload["summary"]["invalid_count"], 1)
        self.assertEqual(payload["invalid_skills"][0]["reason"], "invalid_json")

    def test_unsafe_skill_name_is_invalid(self):
        from onecode.kernel.skill_context import discover_skill_context

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            skill_dir = workspace / ".onecode" / "skills"
            skill_dir.mkdir(parents=True)
            (skill_dir / "unsafe.json").write_text(
                json.dumps(
                    {
                        "name": "../escape",
                        "version": "1",
                        "capabilities": ["test"],
                        "risk": "low",
                        "mode": "method_only",
                    }
                ),
                encoding="utf-8",
            )

            payload = discover_skill_context(workspace)

        self.assertEqual(payload["status"], "warning")
        self.assertEqual(payload["invalid_skills"][0]["reason"], "invalid_name")

    def test_duplicate_skill_names_are_reported_once(self):
        from onecode.kernel.skill_context import discover_skill_context

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            skill_dir = workspace / ".onecode" / "skills"
            skill_dir.mkdir(parents=True)
            manifest = {
                "name": "code-test-regression",
                "version": "1",
                "capabilities": ["test"],
                "risk": "low",
                "mode": "method_only",
            }
            (skill_dir / "a.json").write_text(json.dumps(manifest), encoding="utf-8")
            (skill_dir / "b.json").write_text(json.dumps(manifest), encoding="utf-8")

            payload = discover_skill_context(workspace)

        self.assertEqual(payload["status"], "warning")
        self.assertEqual(payload["summary"]["skill_count"], 1)
        self.assertEqual(payload["summary"]["invalid_count"], 1)
        self.assertEqual(payload["invalid_skills"][0]["reason"], "duplicate_name")

    def test_missing_skill_directory_is_ok_without_loaded_skills(self):
        from onecode.kernel.skill_context import discover_skill_context

        with tempfile.TemporaryDirectory() as tmp:
            payload = discover_skill_context(Path(tmp))

        self.assertEqual(payload["status"], "missing")
        self.assertEqual(payload["summary"]["skill_count"], 0)
        self.assertEqual(payload["summary"]["invalid_count"], 0)
```

- [x] **Step 2: Run tests and verify expected failure**

Run:

```bash
.venv/bin/python -m unittest tests.test_skill_context -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'onecode.kernel.skill_context'`.

## Task 2: Implement Read-Only Skill Context

**Files:**
- Create: `src/onecode/kernel/skill_context.py`

- [x] **Step 1: Add the skill context module**

Create `src/onecode/kernel/skill_context.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from onecode.kernel.hexagram import IchingKernel


SKILL_NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}\\Z")
VALID_RISKS = {"low", "medium", "high"}
VALID_MODES = {"method_only", "reference_only"}


@dataclass(frozen=True)
class SkillManifest:
    name: str
    version: str
    source: str
    risk: str
    mode: str
    capabilities: tuple[str, ...]
    content_sha256: str

    def to_summary(self) -> dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "source": self.source,
            "risk": self.risk,
            "mode": self.mode,
            "capability_count": len(self.capabilities),
            "capabilities": list(self.capabilities),
            "content_sha256": self.content_sha256,
        }


def discover_skill_context(workspace: Path) -> dict[str, Any]:
    root = Path(workspace).resolve()
    skills: list[SkillManifest] = []
    invalid_skills: list[dict[str, str]] = []
    seen_names: set[str] = set()

    for path in _candidate_skill_files(root):
        try:
            manifest = _read_skill_manifest(root, path)
        except ValueError as exc:
            invalid_skills.append(_invalid_skill(root, path, str(exc)))
            continue
        if manifest.name in seen_names:
            invalid_skills.append(_invalid_skill(root, path, "duplicate_name"))
            continue
        seen_names.add(manifest.name)
        skills.append(manifest)

    if invalid_skills:
        status = "warning"
        reason = "invalid_manifest"
    elif skills:
        status = "ok"
        reason = None
    else:
        status = "missing"
        reason = "no_skills"

    status_code = IchingKernel.classify_skill_context(status, reason)
    transition = IchingKernel.transition(status_code)
    method_only_count = sum(1 for skill in skills if skill.mode == "method_only")
    reference_only_count = sum(1 for skill in skills if skill.mode == "reference_only")

    return {
        "status": status,
        "skills": [skill.to_summary() for skill in skills],
        "invalid_skills": invalid_skills,
        "summary": {
            "skill_count": len(skills),
            "invalid_count": len(invalid_skills),
            "method_only_count": method_only_count,
            "reference_only_count": reference_only_count,
            "element": IchingKernel.TRIGRAM_ELEMENTS[IchingKernel.KAN],
            "yin_yang_pressure": "warning" if invalid_skills else "stable",
        },
        "iching_status_code": status_code,
        "iching_transition_action": transition.action,
        "iching_transition_reason": transition.reason,
        "dispatch_decision": IchingKernel.dispatch_decision(transition),
    }


def _candidate_skill_files(root: Path) -> list[Path]:
    directory = root / ".onecode" / "skills"
    if not directory.is_dir():
        return []
    return sorted((path for path in directory.iterdir() if path.is_file() and path.suffix == ".json"), key=lambda path: path.name)


def _read_skill_manifest(root: Path, path: Path) -> SkillManifest:
    try:
        resolved = path.resolve()
    except OSError as exc:
        raise ValueError("resolve_error") from exc
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("outside_project") from exc

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("utf8_decode_error") from exc
    except OSError as exc:
        raise ValueError("read_error") from exc

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid_json") from exc
    if not isinstance(payload, dict):
        raise ValueError("non_object_json")

    name = payload.get("name")
    if not isinstance(name, str) or SKILL_NAME_PATTERN.fullmatch(name) is None:
        raise ValueError("invalid_name")

    version = payload.get("version")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("invalid_version")

    risk = payload.get("risk")
    if not isinstance(risk, str) or risk not in VALID_RISKS:
        raise ValueError("invalid_risk")

    mode = payload.get("mode")
    if not isinstance(mode, str) or mode not in VALID_MODES:
        raise ValueError("invalid_mode")

    capabilities_raw = payload.get("capabilities")
    if not isinstance(capabilities_raw, list) or not all(isinstance(item, str) and item.strip() for item in capabilities_raw):
        raise ValueError("invalid_capabilities")
    capabilities = tuple(sorted(dict.fromkeys(_safe_token(item) for item in capabilities_raw if _safe_token(item))))
    if not capabilities:
        raise ValueError("invalid_capabilities")

    return SkillManifest(
        name=name,
        version=version.strip(),
        source="project",
        risk=risk,
        mode=mode,
        capabilities=capabilities,
        content_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


def _safe_token(value: str) -> str:
    return re.sub(r"[^a-z0-9_:-]+", "_", value.strip().lower().replace("-", "_")).strip("_")


def _invalid_skill(root: Path, path: Path, reason: str) -> dict[str, str]:
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        relative = path.as_posix()
    return {"path": relative, "reason": reason}
```

- [x] **Step 2: Run skill context tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_skill_context -v
```

Expected: FAIL with `AttributeError: type object 'IchingKernel' has no attribute 'classify_skill_context'`.

## Task 3: Add Kernel Classifier for Skill Context

**Files:**
- Modify: `src/onecode/kernel/hexagram.py`
- Modify: `tests/test_iching_kernel.py`

- [x] **Step 1: Write failing classifier tests**

Add these tests to `tests/test_iching_kernel.py` inside `TestIchingKernel`:

```python
    def test_classify_skill_context_maps_valid_and_missing_skill_evidence(self):
        self.assertEqual(
            IchingKernel.classify_skill_context("ok", None),
            IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.ZHEN),
        )
        self.assertEqual(
            IchingKernel.classify_skill_context("missing", "no_skills"),
            IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.KUN),
        )

    def test_classify_skill_context_maps_invalid_and_blocked_skill_evidence(self):
        self.assertEqual(
            IchingKernel.classify_skill_context("warning", "invalid_manifest"),
            IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.GEN),
        )
        self.assertEqual(
            IchingKernel.classify_skill_context("blocked", "unsafe_executable_skill"),
            IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN),
        )
```

- [x] **Step 2: Run classifier tests and verify failure**

Run:

```bash
.venv/bin/python -m unittest \
  tests.test_iching_kernel.TestIchingKernel.test_classify_skill_context_maps_valid_and_missing_skill_evidence \
  tests.test_iching_kernel.TestIchingKernel.test_classify_skill_context_maps_invalid_and_blocked_skill_evidence \
  -v
```

Expected: FAIL with `AttributeError`.

- [x] **Step 3: Implement classifier**

In `src/onecode/kernel/hexagram.py`, add this method near `classify_resume_audit()`:

```python
    @classmethod
    def classify_skill_context(cls, status: str, reason: str | None) -> int:
        if status == "blocked" or reason in {"unsafe_executable_skill", "outside_project"}:
            return cls.compute_status(cls.LI, cls.KUN)
        if status == "warning" or reason in {"invalid_manifest", "duplicate_name"}:
            return cls.compute_status(cls.KAN, cls.GEN)
        if status == "ok":
            return cls.compute_status(cls.KAN, cls.ZHEN)
        return cls.compute_status(cls.KUN, cls.KUN)
```

- [x] **Step 4: Run classifier and skill context tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_skill_context tests.test_iching_kernel -v
```

Expected: PASS.

## Task 4: Wire Skill Context Into Doctor

**Files:**
- Modify: `src/onecode/cli.py`
- Modify: `tests/test_doctor_cli.py`

- [x] **Step 1: Write failing doctor test update**

Update `tests/test_doctor_cli.py::DoctorCliTests.test_cli_doctor_runs_core_smoke_checks` expected check names to include `skill_context` after `runtime_config`:

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
                "skill_context",
                "recovery_policy",
            ],
        )
```

Then update element assertions:

```python
        self.assertEqual(result["checks"][4]["detail"]["summary"]["element"], "wood")
        self.assertEqual(result["checks"][5]["detail"]["summary"]["element"], "earth")
        self.assertEqual(result["checks"][6]["detail"]["summary"]["element"], "water")
        self.assertEqual(result["checks"][7]["detail"]["element"], "fire")
        for check in result["checks"][4:]:
            self.assertIn("iching_status_code", check["detail"])
            self.assertIn("iching_transition_action", check["detail"])
            self.assertIn("dispatch_decision", check["detail"])
```

- [x] **Step 2: Run doctor test and verify failure**

Run:

```bash
.venv/bin/python -m unittest tests.test_doctor_cli.DoctorCliTests.test_cli_doctor_runs_core_smoke_checks -v
```

Expected: FAIL because doctor does not include `skill_context`.

- [x] **Step 3: Implement doctor wiring**

In `src/onecode/cli.py`, add the import:

```python
from onecode.kernel.skill_context import discover_skill_context
```

In `run_doctor()`, after `runtime_config` and before `recovery_policy`, add:

```python
        skill_context = discover_skill_context(workspace)
        checks.append(
            doctor_check(
                "skill_context",
                skill_context["status"] in {"ok", "warning", "missing"},
                skill_context,
            )
        )
```

- [x] **Step 4: Run doctor test**

Run:

```bash
.venv/bin/python -m unittest tests.test_doctor_cli -v
```

Expected: PASS.

## Task 5: Expose Skill Context in Web Project Status

**Files:**
- Modify: `src/onecode/web/api.py`
- Modify: `tests/test_web_api.py`

- [x] **Step 1: Write failing project status test update**

In `tests/test_web_api.py::OneCodeWebApiTests.test_project_status_includes_context_and_config_summaries_without_raw_rule_content`, write a skill manifest and assert redacted skill summary:

```python
            skill_dir = workspace / ".onecode" / "skills"
            skill_dir.mkdir(parents=True)
            (skill_dir / "code-test-regression.json").write_text(
                json.dumps(
                    {
                        "name": "code-test-regression",
                        "version": "1",
                        "description": "private skill body",
                        "capabilities": ["test", "verification"],
                        "risk": "low",
                        "mode": "method_only",
                    }
                ),
                encoding="utf-8",
            )
```

Add assertions:

```python
        self.assertIn("skill_context", payload)
        self.assertEqual(payload["skill_context"]["summary"]["element"], "water")
        self.assertEqual(payload["skill_context"]["summary"]["skill_count"], 1)
        self.assertNotIn("private skill body", json.dumps(payload["skill_context"]))
        self.assertIn("content_sha256", payload["skill_context"]["skills"][0])
```

- [x] **Step 2: Run project status test and verify failure**

Run:

```bash
.venv/bin/python -m unittest tests.test_web_api.OneCodeWebApiTests.test_project_status_includes_context_and_config_summaries_without_raw_rule_content -v
```

Expected: FAIL because project status does not include `skill_context`.

- [x] **Step 3: Implement Web API wiring**

In `src/onecode/web/api.py`, add the import:

```python
from onecode.kernel.skill_context import discover_skill_context
```

In `project_status_payload()`, add:

```python
        "skill_context": discover_skill_context(resolved),
```

near the existing `project_context` and `runtime_config` keys.

- [x] **Step 4: Run Web API tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_web_api -v
```

Expected: PASS.

## Task 6: Document Read-Only Skill Context

**Files:**
- Modify: `README.md`

- [x] **Step 1: Update README rule evidence section**

In the `Absorbed Rule-Evidence Layer` section, extend the evidence layer paragraph:

```markdown
`project_context` records metadata-only project rules with wood element semantics. `runtime_config` reports optional, redacted, approved effective values with earth element semantics. `skill_context` records read-only skill manifests and selected skill guidance with water element semantics. `recovery_policy` reports advisory recovery actions only with fire element semantics.
```

- [x] **Step 2: Add a short Skill Context section**

Add after the absorbed rule-evidence paragraph:

```markdown
## Skill Context

OneCode treats skills as bounded rule evidence. Project-local skill manifests may be declared under `.onecode/skills/*.json`; the first implementation reads only manifest metadata such as name, capabilities, risk, mode, and content hash. Raw skill bodies are not exposed by default, and skills do not gain execution authority from discovery.

Skill evidence is folded through `IchingKernel.classify_skill_context()` and then through the normal transition and dispatch projections. Execution-capable skill adapters require a separate approved design and must use the existing sandbox, verifier, approval, and path guard boundaries.
```

- [x] **Step 3: Run README-focused tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_readme -v
```

Expected: PASS.

## Task 7: Final Verification

**Files:**
- All files above

- [x] **Step 1: Run focused integration tests**

Run:

```bash
.venv/bin/python -m unittest \
  tests.test_skill_context \
  tests.test_iching_kernel \
  tests.test_doctor_cli \
  tests.test_web_api \
  -v
```

Expected: PASS.

Observed: PASS, 138 tests OK, 9 skipped due local socket bind permissions.

- [x] **Step 2: Run full verification**

Run:

```bash
bash scripts/verify.sh
```

Expected: PASS with all tests OK and doctor status `ok`.

Observed: PASS, 686 tests OK, 1 skipped, doctor status `ok`.

- [x] **Step 3: Run diff hygiene checks**

Run:

```bash
git diff --check -- src tests docs README.md
git diff --stat -- src tests docs README.md
```

Expected: `git diff --check` has no output. Stat only includes the files listed in this plan plus already-existing review/optimization changes.

Observed: `git diff --check -- src tests docs README.md scripts` produced no output.

## Rollback Notes

This phase is local-only and does not publish or migrate data. To roll back this phase before commit, remove the new `skill_context` module and tests, then revert the doctor, Web API, README, and `IchingKernel` edits from this plan. Do not revert unrelated pre-existing changes in the working tree.
