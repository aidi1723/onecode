# V0.3 Eight Opcode Primitives Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add eight root Opcode primitives to the one-character Agent Skill dictionary and make every existing execution character inherit from one root.

**Architecture:** Extend the dictionary schema with `root_opcode`, `opcode_vector`, `inheritance_policy`, `six_phase_workflow`, and `transition_policy`. Keep the existing OpenAI-compatible gateway stable while enriching system-rule injection with root Opcode and workflow data. Validator enforces root membership and inheritance constraints.

**Tech Stack:** Python standard library, JSON Schema document, `unittest`, existing FastAPI gateway module.

---

### Task 1: Opcode Tests

**Files:**
- Create: `tests/test_opcode_primitives.py`
- Read: `docs/v0.3-action-framework.md`
- Read: `docs/eight-opcode-primitives.md`

- [ ] **Step 1: Add failing tests for root Opcode fields**

Create `tests/test_opcode_primitives.py` with tests that load `agent_skill_dictionary/programming-agent-skill-dictionary.json` and assert:

```python
import unittest

from agent_skill_dictionary.gateway_core import rewrite_chat_completion_request
from agent_skill_dictionary.loader import load_dictionary, lookup_entry
from agent_skill_dictionary.validator import validate_dictionary


DICTIONARY_PATH = "agent_skill_dictionary/programming-agent-skill-dictionary.json"
ROOT_OPCODES = {"查", "修", "测", "卫", "停", "问", "记", "总"}


class OpcodePrimitivesTest(unittest.TestCase):
    def setUp(self):
        self.dictionary = load_dictionary(DICTIONARY_PATH)

    def test_root_opcodes_exist_and_point_to_themselves(self):
        codes = {entry["code"] for entry in self.dictionary["entries"]}
        self.assertTrue(ROOT_OPCODES.issubset(codes))
        for code in ROOT_OPCODES:
            entry = lookup_entry(self.dictionary, code).raw
            self.assertEqual(entry["root_opcode"], code)

    def test_every_entry_has_opcode_fields(self):
        for entry in self.dictionary["entries"]:
            with self.subTest(code=entry["code"]):
                self.assertIn(entry["root_opcode"], ROOT_OPCODES)
                self.assertIsInstance(entry["opcode_vector"], dict)
                self.assertIsInstance(entry["inheritance_policy"], dict)
                self.assertGreaterEqual(len(entry["six_phase_workflow"]), 6)
                self.assertIsInstance(entry["transition_policy"], dict)

    def test_known_child_opcode_mapping(self):
        expected = {
            "解": "查",
            "审": "查",
            "源": "查",
            "搜": "查",
            "评": "查",
            "造": "修",
            "改": "修",
            "简": "修",
            "设": "修",
            "合": "卫",
            "隔": "卫",
            "部": "卫",
            "文": "记",
            "数": "记",
        }
        for code, root in expected.items():
            with self.subTest(code=code):
                self.assertEqual(lookup_entry(self.dictionary, code).raw["root_opcode"], root)

    def test_validator_rejects_child_permission_relaxation(self):
        broken = load_dictionary(DICTIONARY_PATH)
        for entry in broken["entries"]:
            if entry["code"] == "解":
                entry["tool_policy"]["write"] = "allowed"
        errors = validate_dictionary(broken)
        self.assertTrue(any("cannot relax root write policy" in error for error in errors))

    def test_gateway_injects_root_opcode_and_six_phase_workflow(self):
        body = {
            "model": "gpt-test",
            "messages": [{"role": "user", "content": "解释一下这个报错什么意思"}],
        }
        rewritten, metadata = rewrite_chat_completion_request(body, self.dictionary)
        system_message = rewritten["messages"][0]["content"]
        self.assertEqual(metadata["active_code"], "解")
        self.assertEqual(metadata["root_opcode"], "查")
        self.assertIn("根字 Opcode: 查", system_message)
        self.assertIn("六步工作流", system_message)
        self.assertIn("状态转移策略", system_message)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new tests and verify failure**

Run:

```bash
python3 -m unittest tests.test_opcode_primitives -v
```

Expected: FAIL because dictionary entries do not yet have the new fields.

### Task 2: Schema And Dictionary

**Files:**
- Modify: `schemas/agent-skill-dictionary.schema.json`
- Modify: `agent_skill_dictionary/programming-agent-skill-dictionary.json`

- [ ] **Step 1: Extend schema**

Add required fields:

```text
root_opcode
opcode_vector
inheritance_policy
six_phase_workflow
transition_policy
```

`root_opcode` enum is `查 / 修 / 测 / 卫 / 停 / 问 / 记 / 总`.

- [ ] **Step 2: Populate dictionary**

For all 22 entries:

- add `root_opcode`
- add `opcode_vector`
- add `inheritance_policy`
- add six workflow steps
- add transition policy
- bump `version` to `0.3.0`

- [ ] **Step 3: Validate JSON shape**

Run:

```bash
python3 -m json.tool agent_skill_dictionary/programming-agent-skill-dictionary.json >/tmp/programming-agent-skill-dictionary.json
python3 -m json.tool schemas/agent-skill-dictionary.schema.json >/tmp/agent-skill-schema.json
```

Expected: exit code 0.

### Task 3: Validator Rules

**Files:**
- Modify: `agent_skill_dictionary/validator.py`
- Test: `tests/test_opcode_primitives.py`

- [ ] **Step 1: Add validator constants**

Add:

```python
ROOT_OPCODES = {"查", "修", "测", "卫", "停", "问", "记", "总"}
WRITE_POLICY_RANK = {"forbidden": 0, "scoped": 1, "scoped_to_impact_files": 1, "allowed": 2}
```

- [ ] **Step 2: Validate root and inheritance**

Validator must check:

- `root_opcode` exists and is in `ROOT_OPCODES`
- root entries point to themselves
- child write policy is not looser than root write policy
- every entry has non-empty `six_phase_workflow`
- every entry has transition policy keys `on_success`, `on_failure`, `on_risk`

- [ ] **Step 3: Run opcode tests**

Run:

```bash
python3 -m unittest tests.test_opcode_primitives -v
```

Expected: PASS.

### Task 4: Gateway Injection

**Files:**
- Modify: `agent_skill_dictionary/gateway_core.py`
- Test: `tests/test_opcode_primitives.py`

- [ ] **Step 1: Add root entry lookup to rewrite metadata**

In `rewrite_chat_completion_request()`, add:

```python
root_code = active_entry.raw.get("root_opcode", active_code)
root_entry = lookup_entry(dictionary, root_code)
```

Then include `root_opcode` in metadata.

- [ ] **Step 2: Inject root Opcode and workflow**

Pass `root_entry.raw` to `build_system_instruction()` and include:

```text
根字 Opcode
根字定义
三维控制向量
六步工作流
状态转移策略
```

- [ ] **Step 3: Run gateway and opcode tests**

Run:

```bash
python3 -m unittest tests.test_gateway_core tests.test_opcode_primitives -v
```

Expected: PASS.

### Task 5: Documentation And Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/project-status.md`
- Modify: `docs/dictionary-contract.md`
- Modify: `docs/development.md`

- [ ] **Step 1: Update docs to V0.3 implemented status**

Document:

- version `0.3.0`
- eight Opcode fields are now in the dictionary
- V0.3 verifies inheritance and gateway injection

- [ ] **Step 2: Run full verification**

Run:

```bash
python3 -m unittest tests.test_agent_skill_dictionary tests.test_gateway_core tests.test_gateway_plan tests.test_audit tests.test_gateway_server_import tests.test_tool_guard tests.test_tool_preflight tests.test_phase2_dictionary tests.test_reference_patterns tests.test_opcode_primitives tests.test_workflow_loader tests.test_kernel_policy tests.test_macro_chain -v
python3 -m agent_skill_dictionary.validator agent_skill_dictionary/programming-agent-skill-dictionary.json
python3 -m json.tool agent_skill_dictionary/programming-agent-skill-dictionary.json >/tmp/programming-agent-skill-dictionary.json
python3 -m json.tool schemas/agent-skill-dictionary.schema.json >/tmp/agent-skill-schema.json
python3 -m compileall -q agent_skill_dictionary
rg -n "TODO|TBD|FIXME|待补|占位|0\\.1|V0\\.1" README.md docs/*.md
```

Expected:

- all tests PASS
- validator prints `OK`
- JSON checks exit 0
- compileall exits 0
- `rg` has no real stale placeholders; section numbers like `10.1` are acceptable
