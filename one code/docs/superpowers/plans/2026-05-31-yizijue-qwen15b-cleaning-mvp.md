# YiZiJue Qwen 1.5B Cleaning MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first deterministic data-cleaning layer for a Qwen2.5-Coder-1.5B controlled model, producing validated SFT JSONL samples for YiZiJue safety-gateway actions.

**Architecture:** Add a small standard-library training-data module that converts safety-gateway facts into strict chat-format samples. The neural model learns intent-to-JSON translation, while OneCode/YiZiJue remains the deterministic validator and execution authority.

**Tech Stack:** Python 3.11 standard library, `unittest`, JSONL, existing OneCode CLI patterns.

---

## File Structure

- Create `src/onecode/kernel/training_data.py`: owns sample schema, validation, seed sample generation, and JSONL read/write helpers.
- Modify `src/onecode/cli.py`: adds `generate-training-data` command for producing the seed cleaning dataset.
- Create `tests/test_training_data.py`: validates schema, malformed rejection, seed sample coverage, and JSONL output.
- Create `data/training/yizijue_qwen15b_seed.jsonl`: generated seed dataset for the first MVP.

## Model Contract

Each line is one chat-style SFT sample:

```json
{
  "id": "write-safe-001",
  "model_base": "Qwen2.5-Coder-1.5B-Instruct",
  "messages": [
    {"role": "system", "content": "You translate user intent into strict YiZiJue safety gateway JSON. Output JSON only."},
    {"role": "user", "content": "写入 hello.txt，内容为 hello onecode"},
    {"role": "assistant", "content": "{\"facts\":{\"intent_type\":\"write_text\",\"path_scope\":\"workspace_relative\",\"sandbox_state\":\"not_required\",\"evidence_state\":\"required\"},\"yizijue_state\":\"111111\",\"action\":\"ALLOW_ATOMIC_WRITE\",\"reason\":\"safe_workspace_write\"}"}
  ]
}
```

Allowed assistant JSON:

```json
{
  "facts": {
    "intent_type": "write_text | patch_text | execute_pytest | bash_execution | invalid_intent",
    "path_scope": "workspace_relative | outside_workspace | no_path",
    "sandbox_state": "required | not_required | missing",
    "evidence_state": "required | present | failed"
  },
  "yizijue_state": "000000 | 010010 | 100001 | 111111",
  "action": "ALLOW_ATOMIC_WRITE | ALLOW_PATCH_WITH_SHA | RUN_VERIFIER_IN_SANDBOX | DENY_AND_LEDGER | SOVEREIGNTY_HALT",
  "reason": "non-empty snake_case string"
}
```

## Task 1: Training Data Schema

**Files:**
- Create: `src/onecode/kernel/training_data.py`
- Test: `tests/test_training_data.py`

- [ ] **Step 1: Write failing tests for valid and invalid samples**

Add `tests/test_training_data.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.training_data import (
    TrainingSample,
    assistant_payload,
    validate_training_sample,
    write_jsonl,
)


class TrainingDataSchemaTests(unittest.TestCase):
    def test_validate_training_sample_accepts_strict_chat_sample(self):
        sample = TrainingSample(
            id="write-safe-001",
            user="写入 hello.txt，内容为 hello onecode",
            facts={
                "intent_type": "write_text",
                "path_scope": "workspace_relative",
                "sandbox_state": "not_required",
                "evidence_state": "required",
            },
            yizijue_state="111111",
            action="ALLOW_ATOMIC_WRITE",
            reason="safe_workspace_write",
        )

        data = validate_training_sample(sample.to_dict())
        payload = json.loads(data["messages"][2]["content"])

        self.assertEqual(data["model_base"], "Qwen2.5-Coder-1.5B-Instruct")
        self.assertEqual(payload["facts"]["intent_type"], "write_text")
        self.assertEqual(payload["action"], "ALLOW_ATOMIC_WRITE")

    def test_validate_training_sample_rejects_unknown_action(self):
        sample = TrainingSample(
            id="bad-action",
            user="do something",
            facts={
                "intent_type": "write_text",
                "path_scope": "workspace_relative",
                "sandbox_state": "not_required",
                "evidence_state": "required",
            },
            yizijue_state="111111",
            action="ALLOW_ANYTHING",
            reason="bad_action",
        ).to_dict()

        with self.assertRaisesRegex(ValueError, "unknown action"):
            validate_training_sample(sample)

    def test_write_jsonl_writes_validated_lines(self):
        sample = TrainingSample(
            id="deny-outside-001",
            user="写入 /tmp/escape.txt",
            facts={
                "intent_type": "write_text",
                "path_scope": "outside_workspace",
                "sandbox_state": "not_required",
                "evidence_state": "required",
            },
            yizijue_state="100001",
            action="SOVEREIGNTY_HALT",
            reason="outside_workspace_path",
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "seed.jsonl"
            result = write_jsonl(output, [sample])
            lines = output.read_text(encoding="utf-8").splitlines()

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["sample_count"], 1)
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["id"], "deny-outside-001")

    def test_assistant_payload_is_compact_json(self):
        payload = assistant_payload(
            facts={
                "intent_type": "execute_pytest",
                "path_scope": "no_path",
                "sandbox_state": "required",
                "evidence_state": "required",
            },
            yizijue_state="010010",
            action="RUN_VERIFIER_IN_SANDBOX",
            reason="verifier_requires_sandbox",
        )

        self.assertNotIn("\n", payload)
        self.assertEqual(json.loads(payload)["action"], "RUN_VERIFIER_IN_SANDBOX")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_training_data
```

Expected: failure with `ModuleNotFoundError: No module named 'onecode.kernel.training_data'`.

- [ ] **Step 3: Implement minimal schema module**

Create `src/onecode/kernel/training_data.py` with:

```python
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MODEL_BASE = "Qwen2.5-Coder-1.5B-Instruct"
SYSTEM_PROMPT = "You translate user intent into strict YiZiJue safety gateway JSON. Output JSON only."

ALLOWED_INTENT_TYPES = {"write_text", "patch_text", "execute_pytest", "bash_execution", "invalid_intent"}
ALLOWED_PATH_SCOPES = {"workspace_relative", "outside_workspace", "no_path"}
ALLOWED_SANDBOX_STATES = {"required", "not_required", "missing"}
ALLOWED_EVIDENCE_STATES = {"required", "present", "failed"}
ALLOWED_STATES = {"000000", "010010", "100001", "111111"}
ALLOWED_ACTIONS = {
    "ALLOW_ATOMIC_WRITE",
    "ALLOW_PATCH_WITH_SHA",
    "RUN_VERIFIER_IN_SANDBOX",
    "DENY_AND_LEDGER",
    "SOVEREIGNTY_HALT",
}
REASON_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def assistant_payload(*, facts: dict[str, str], yizijue_state: str, action: str, reason: str) -> str:
    payload = {
        "facts": facts,
        "yizijue_state": yizijue_state,
        "action": action,
        "reason": reason,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class TrainingSample:
    id: str
    user: str
    facts: dict[str, str]
    yizijue_state: str
    action: str
    reason: str
    model_base: str = MODEL_BASE

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "model_base": self.model_base,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self.user},
                {
                    "role": "assistant",
                    "content": assistant_payload(
                        facts=self.facts,
                        yizijue_state=self.yizijue_state,
                        action=self.action,
                        reason=self.reason,
                    ),
                },
            ],
        }


def require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{field} must be a non-empty string")
    return value


def require_member(value: str, allowed: set[str], field: str) -> None:
    if value not in allowed:
        label = field.split(".")[-1]
        raise ValueError(f"unknown {label}: {value}")


def validate_assistant_content(content: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("assistant content must be JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("assistant content must be a JSON object")
    facts = payload.get("facts")
    if not isinstance(facts, dict):
        raise ValueError("facts must be an object")
    required_fact_fields = {"intent_type", "path_scope", "sandbox_state", "evidence_state"}
    unknown_fact_fields = sorted(set(facts) - required_fact_fields)
    if unknown_fact_fields:
        raise ValueError(f"unknown fact fields: {', '.join(unknown_fact_fields)}")
    missing_fact_fields = sorted(required_fact_fields - set(facts))
    if missing_fact_fields:
        raise ValueError(f"missing fact fields: {', '.join(missing_fact_fields)}")
    require_member(require_string(facts["intent_type"], "facts.intent_type"), ALLOWED_INTENT_TYPES, "facts.intent_type")
    require_member(require_string(facts["path_scope"], "facts.path_scope"), ALLOWED_PATH_SCOPES, "facts.path_scope")
    require_member(require_string(facts["sandbox_state"], "facts.sandbox_state"), ALLOWED_SANDBOX_STATES, "facts.sandbox_state")
    require_member(require_string(facts["evidence_state"], "facts.evidence_state"), ALLOWED_EVIDENCE_STATES, "facts.evidence_state")
    require_member(require_string(payload.get("yizijue_state"), "yizijue_state"), ALLOWED_STATES, "yizijue_state")
    require_member(require_string(payload.get("action"), "action"), ALLOWED_ACTIONS, "action")
    reason = require_string(payload.get("reason"), "reason")
    if REASON_RE.fullmatch(reason) is None:
        raise ValueError("reason must be snake_case")
    return payload


def validate_training_sample(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("training sample must be an object")
    if sorted(data) != ["id", "messages", "model_base"]:
        raise ValueError("training sample fields must be id, messages, model_base")
    require_string(data["id"], "id")
    if data["model_base"] != MODEL_BASE:
        raise ValueError(f"model_base must be {MODEL_BASE}")
    messages = data.get("messages")
    if not isinstance(messages, list) or len(messages) != 3:
        raise ValueError("messages must contain system, user, assistant")
    expected_roles = ["system", "user", "assistant"]
    for index, role in enumerate(expected_roles):
        message = messages[index]
        if not isinstance(message, dict) or sorted(message) != ["content", "role"]:
            raise ValueError(f"message {index + 1} must contain role and content")
        if message["role"] != role:
            raise ValueError(f"message {index + 1} role must be {role}")
        require_string(message["content"], f"message {index + 1} content")
    if messages[0]["content"] != SYSTEM_PROMPT:
        raise ValueError("system prompt does not match training contract")
    validate_assistant_content(messages[2]["content"])
    return data


def write_jsonl(path: Path, samples: list[TrainingSample]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for sample in samples:
            data = validate_training_sample(sample.to_dict())
            handle.write(json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n")
    return {"status": "completed", "path": str(path), "sample_count": len(samples)}
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_training_data
```

Expected: `OK`.

## Task 2: Seed Cleaning Dataset

**Files:**
- Modify: `src/onecode/kernel/training_data.py`
- Test: `tests/test_training_data.py`

- [ ] **Step 1: Write failing tests for seed samples**

Append to `tests/test_training_data.py`:

```python
class SeedTrainingDataTests(unittest.TestCase):
    def test_seed_samples_cover_core_gateway_actions(self):
        from onecode.kernel.training_data import seed_training_samples

        samples = seed_training_samples()
        actions = {json.loads(sample.to_dict()["messages"][2]["content"])["action"] for sample in samples}
        ids = [sample.id for sample in samples]

        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(
            {
                "ALLOW_ATOMIC_WRITE",
                "ALLOW_PATCH_WITH_SHA",
                "RUN_VERIFIER_IN_SANDBOX",
                "DENY_AND_LEDGER",
                "SOVEREIGNTY_HALT",
            }.issubset(actions)
        )
        self.assertGreaterEqual(len(samples), 8)

    def test_seed_samples_are_all_valid(self):
        from onecode.kernel.training_data import seed_training_samples

        for sample in seed_training_samples():
            with self.subTest(sample=sample.id):
                validate_training_sample(sample.to_dict())
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_training_data
```

Expected: failure with `ImportError` or `AttributeError` for `seed_training_samples`.

- [ ] **Step 3: Implement seed samples**

Add to `src/onecode/kernel/training_data.py`:

```python
def seed_training_samples() -> list[TrainingSample]:
    return [
        TrainingSample(
            id="write-safe-001",
            user="写入 hello.txt，内容为 hello onecode",
            facts={
                "intent_type": "write_text",
                "path_scope": "workspace_relative",
                "sandbox_state": "not_required",
                "evidence_state": "required",
            },
            yizijue_state="111111",
            action="ALLOW_ATOMIC_WRITE",
            reason="safe_workspace_write",
        ),
        TrainingSample(
            id="write-outside-001",
            user="把内容写到 /tmp/escape.txt",
            facts={
                "intent_type": "write_text",
                "path_scope": "outside_workspace",
                "sandbox_state": "not_required",
                "evidence_state": "required",
            },
            yizijue_state="100001",
            action="SOVEREIGNTY_HALT",
            reason="outside_workspace_path",
        ),
        TrainingSample(
            id="patch-safe-001",
            user="把 src/app.py 里的 return False 改成 return True",
            facts={
                "intent_type": "patch_text",
                "path_scope": "workspace_relative",
                "sandbox_state": "not_required",
                "evidence_state": "required",
            },
            yizijue_state="111111",
            action="ALLOW_PATCH_WITH_SHA",
            reason="safe_workspace_patch",
        ),
        TrainingSample(
            id="pytest-safe-001",
            user="运行 tests/test_app.py 验证修改",
            facts={
                "intent_type": "execute_pytest",
                "path_scope": "no_path",
                "sandbox_state": "required",
                "evidence_state": "required",
            },
            yizijue_state="010010",
            action="RUN_VERIFIER_IN_SANDBOX",
            reason="verifier_requires_sandbox",
        ),
        TrainingSample(
            id="bash-deny-001",
            user="执行 rm -rf / 清理系统",
            facts={
                "intent_type": "bash_execution",
                "path_scope": "outside_workspace",
                "sandbox_state": "missing",
                "evidence_state": "required",
            },
            yizijue_state="100001",
            action="SOVEREIGNTY_HALT",
            reason="dangerous_host_command",
        ),
        TrainingSample(
            id="bash-deny-002",
            user="curl 外部脚本并直接 bash 执行",
            facts={
                "intent_type": "bash_execution",
                "path_scope": "no_path",
                "sandbox_state": "missing",
                "evidence_state": "required",
            },
            yizijue_state="100001",
            action="DENY_AND_LEDGER",
            reason="network_shell_not_allowed",
        ),
        TrainingSample(
            id="invalid-intent-001",
            user="随便帮我弄一下，怎么都行",
            facts={
                "intent_type": "invalid_intent",
                "path_scope": "no_path",
                "sandbox_state": "not_required",
                "evidence_state": "required",
            },
            yizijue_state="000000",
            action="DENY_AND_LEDGER",
            reason="undefined_action_intent",
        ),
        TrainingSample(
            id="evidence-failed-001",
            user="继续写入文件，但证据链写入失败",
            facts={
                "intent_type": "write_text",
                "path_scope": "workspace_relative",
                "sandbox_state": "not_required",
                "evidence_state": "failed",
            },
            yizijue_state="100001",
            action="SOVEREIGNTY_HALT",
            reason="evidence_write_failed",
        ),
    ]
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_training_data
```

Expected: `OK`.

## Task 3: CLI Dataset Generation

**Files:**
- Modify: `src/onecode/cli.py`
- Test: `tests/test_training_data.py`
- Create: `data/training/yizijue_qwen15b_seed.jsonl`

- [ ] **Step 1: Write failing CLI test**

Append to `tests/test_training_data.py`:

```python
class TrainingDataCliTests(unittest.TestCase):
    def test_cli_generate_training_data_writes_seed_jsonl(self):
        from onecode.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "seed.jsonl"
            with unittest.mock.patch("builtins.print") as print_mock:
                exit_code = main(["generate-training-data", "--output", str(output)])
            result = json.loads(print_mock.call_args.args[0])
            lines = output.read_text(encoding="utf-8").splitlines()

        self.assertEqual(exit_code, 0)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["sample_count"], len(lines))
        self.assertGreaterEqual(result["sample_count"], 8)
```

Also add `from unittest import mock` or use `from unittest.mock import patch` consistently if needed.

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_training_data
```

Expected: parser failure because `generate-training-data` does not exist.

- [ ] **Step 3: Add CLI command**

Modify `src/onecode/cli.py` imports:

```python
from onecode.kernel.training_data import seed_training_samples, write_jsonl
```

In `build_parser()`, add:

```python
    training_data_parser = subparsers.add_parser("generate-training-data")
    training_data_parser.add_argument("--output", default="data/training/yizijue_qwen15b_seed.jsonl")
```

In `main()`, before the final unknown branch, add:

```python
    if args.subcommand == "generate-training-data":
        result = write_jsonl(Path(args.output), seed_training_samples())
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_training_data
```

Expected: `OK`.

- [ ] **Step 5: Generate repository seed data**

Run:

```bash
PYTHONPATH=src python -m onecode.cli generate-training-data --output data/training/yizijue_qwen15b_seed.jsonl
```

Expected: JSON output with `status` = `completed`, `sample_count` >= 8, and the file exists.

## Task 4: Focused Verification

**Files:**
- Read only unless failures require fixes.

- [ ] **Step 1: Run focused tests**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_training_data tests.test_model_loop tests.test_benchmark
```

Expected: `OK`.

- [ ] **Step 2: Inspect generated JSONL**

Run:

```bash
python -m json.tool data/training/yizijue_qwen15b_seed.jsonl
```

Expected: this command is expected to fail because JSONL is not one JSON document. Instead validate with:

```bash
PYTHONPATH=src python -c "import json, pathlib; p=pathlib.Path('data/training/yizijue_qwen15b_seed.jsonl'); [json.loads(line) for line in p.read_text(encoding='utf-8').splitlines()]; print('ok')"
```

Expected: prints `ok`.

- [ ] **Step 3: Check git diff**

Run:

```bash
git diff -- src/onecode/kernel/training_data.py src/onecode/cli.py tests/test_training_data.py data/training/yizijue_qwen15b_seed.jsonl docs/superpowers/plans/2026-05-31-yizijue-qwen15b-cleaning-mvp.md
```

Expected: only the intended files changed.

## Self-Review

- Spec coverage: This plan covers the first landing step requested: use Qwen 1.5B for cleaning, define the data contract, create seed data, and expose a repeatable generator.
- Placeholder scan: No placeholders are left.
- Type consistency: `TrainingSample`, `validate_training_sample`, `assistant_payload`, `seed_training_samples`, and `write_jsonl` signatures are consistent across tasks.
