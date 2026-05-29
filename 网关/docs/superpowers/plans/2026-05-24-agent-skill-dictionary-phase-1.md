# Agent Skill Dictionary Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 1 static Agent Skill Dictionary kernel: schema, programming dictionary, instruction stack policy, validator, and tests.

**Architecture:** Keep this phase file-based and deterministic. JSON files define execution characters and policies; a small Python package loads and validates them; tests prove schema integrity, source/guard boundaries, instruction stack ordering, and meltdown fallback rules.

**Tech Stack:** Python 3 standard library, JSON Schema draft 2020-12 as a data contract, `pytest` if available or `unittest` fallback.

---

## File Structure

- Create: `schemas/agent-skill-dictionary.schema.json`
  - JSON Schema for the dictionary document.
  - Defines execution character entries, tool policies, runtime environment policy, verification evidence, stack policy, and fallback rules.
- Create: `agent_skill_dictionary/programming-agent-skill-dictionary.json`
  - First programming-domain dictionary with `查 / 解 / 修 / 造 / 改 / 测 / 审 / 设 / 源 / 卫 / 隔 / 简`.
- Create: `agent_skill_dictionary/execution-stack-policy.md`
  - Human-readable stack policy matching the whitepaper.
- Create: `agent_skill_dictionary/__init__.py`
  - Package exports.
- Create: `agent_skill_dictionary/loader.py`
  - Loads dictionary JSON and provides lookup helpers.
- Create: `agent_skill_dictionary/validator.py`
  - Validates internal consistency without requiring third-party dependencies.
- Create: `tests/test_agent_skill_dictionary.py`
  - Unit tests for dictionary shape and core rules.

## Task 1: Add Schema Contract

**Files:**
- Create: `schemas/agent-skill-dictionary.schema.json`

- [ ] **Step 1: Create schema file**

Create `schemas/agent-skill-dictionary.schema.json` with this content:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://hanzi-spectrum.local/schemas/agent-skill-dictionary.schema.json",
  "title": "Agent Skill Dictionary",
  "type": "object",
  "required": ["name", "version", "domain", "updated_at", "entries"],
  "additionalProperties": false,
  "properties": {
    "name": { "type": "string", "minLength": 1 },
    "version": { "type": "string", "pattern": "^0\\.\\d+\\.\\d+$" },
    "domain": { "type": "string", "minLength": 1 },
    "updated_at": { "type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$" },
    "entries": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/entry" }
    }
  },
  "$defs": {
    "entry": {
      "type": "object",
      "required": [
        "code",
        "name",
        "definition",
        "intent_examples",
        "bound_skill_patterns",
        "allowed_actions",
        "forbidden_actions",
        "tool_policy",
        "runtime_environment",
        "routing_target",
        "model_policy",
        "required_steps",
        "verification",
        "fallback"
      ],
      "additionalProperties": false,
      "properties": {
        "code": { "type": "string", "minLength": 1, "maxLength": 2 },
        "name": { "type": "string", "pattern": "^[a-z_]+$" },
        "definition": { "type": "string", "minLength": 1 },
        "intent_examples": {
          "type": "array",
          "minItems": 1,
          "items": { "type": "string", "minLength": 1 }
        },
        "bound_skill_patterns": {
          "type": "array",
          "minItems": 1,
          "items": { "type": "string", "pattern": "^[a-z0-9_\\-]+$" }
        },
        "allowed_actions": {
          "type": "array",
          "items": { "type": "string", "pattern": "^[a-z0-9_\\-]+$" }
        },
        "forbidden_actions": {
          "type": "array",
          "items": { "type": "string", "pattern": "^[a-z0-9_\\-]+$" }
        },
        "tool_policy": {
          "type": "object",
          "required": ["read", "write", "network", "dependency_install"],
          "additionalProperties": false,
          "properties": {
            "read": { "enum": ["allowed", "forbidden"] },
            "write": { "enum": ["allowed", "scoped", "scoped_to_impact_files", "forbidden"] },
            "network": { "enum": ["allowed", "approval_required", "forbidden"] },
            "dependency_install": { "enum": ["allowed", "approval_required", "forbidden"] }
          }
        },
        "runtime_environment": {
          "type": "object",
          "required": ["auto_inject_local_env", "context_breaker_on_switch", "evidence_capture", "audit_log_write_access"],
          "additionalProperties": false,
          "properties": {
            "auto_inject_local_env": { "type": "boolean" },
            "context_breaker_on_switch": { "type": "boolean" },
            "evidence_capture": { "enum": ["none", "system_sandbox"] },
            "audit_log_write_access": { "enum": ["system_only", "agent_allowed"] }
          }
        },
        "routing_target": { "type": "string", "pattern": "^[a-z0-9_\\-]+$" },
        "model_policy": {
          "type": "object",
          "required": ["temperature", "max_retry_limit", "load_minimal_context", "prefer_deterministic_steps"],
          "additionalProperties": false,
          "properties": {
            "temperature": { "type": "number", "minimum": 0, "maximum": 1 },
            "max_retry_limit": { "type": "integer", "minimum": 0, "maximum": 10 },
            "load_minimal_context": { "type": "boolean" },
            "prefer_deterministic_steps": { "type": "boolean" }
          }
        },
        "required_steps": {
          "type": "array",
          "minItems": 1,
          "items": { "type": "string", "minLength": 1 }
        },
        "verification": {
          "type": "object",
          "required": ["required", "evidence_source", "acceptable_evidence", "audit_fields"],
          "additionalProperties": false,
          "properties": {
            "required": { "type": "boolean" },
            "evidence_source": { "enum": ["none", "system_sandbox_stdout_stderr", "manual_human_review"] },
            "acceptable_evidence": {
              "type": "array",
              "items": { "type": "string", "pattern": "^[a-z0-9_\\-]+$" }
            },
            "audit_fields": {
              "type": "array",
              "items": { "type": "string", "pattern": "^[a-z0-9_\\-]+$" }
            }
          }
        },
        "fallback": {
          "type": "object",
          "required": ["when_confidence_below", "action", "on_max_retry_exceeded", "on_meltdown"],
          "additionalProperties": false,
          "properties": {
            "when_confidence_below": { "type": "number", "minimum": 0, "maximum": 1 },
            "action": { "type": "string", "minLength": 1 },
            "on_max_retry_exceeded": { "type": "string", "minLength": 1 },
            "on_meltdown": { "type": "string", "minLength": 1 }
          }
        }
      }
    }
  }
}
```

- [ ] **Step 2: Confirm schema is valid JSON**

Run:

```bash
python3 -m json.tool schemas/agent-skill-dictionary.schema.json >/tmp/agent-skill-schema.json
```

Expected: exit code 0.

## Task 2: Add Programming Dictionary

**Files:**
- Create: `agent_skill_dictionary/programming-agent-skill-dictionary.json`

- [ ] **Step 1: Create dictionary directory**

Run:

```bash
mkdir -p agent_skill_dictionary
```

Expected: `agent_skill_dictionary` exists.

- [ ] **Step 2: Create dictionary JSON**

Create `agent_skill_dictionary/programming-agent-skill-dictionary.json` with the first 12 entries. Use this exact pattern for `修`, then create the other entries with matching fields:

```json
{
  "name": "Programming Agent Skill Dictionary",
  "version": "0.1.0",
  "domain": "programming",
  "updated_at": "2026-05-24",
  "entries": [
    {
      "code": "查",
      "name": "inspect",
      "definition": "只读调查项目、文件、结构、原因，不修改代码。",
      "intent_examples": ["看看项目结构", "找一下入口", "查一下为什么失败"],
      "bound_skill_patterns": ["read_only_exploration", "context_collection"],
      "allowed_actions": ["read_files", "search_code", "run_read_only_commands"],
      "forbidden_actions": ["edit_files", "install_dependency", "commit_changes"],
      "tool_policy": { "read": "allowed", "write": "forbidden", "network": "approval_required", "dependency_install": "forbidden" },
      "runtime_environment": { "auto_inject_local_env": true, "context_breaker_on_switch": true, "evidence_capture": "system_sandbox", "audit_log_write_access": "system_only" },
      "routing_target": "inspect_workflow",
      "model_policy": { "temperature": 0.0, "max_retry_limit": 1, "load_minimal_context": true, "prefer_deterministic_steps": true },
      "required_steps": ["定位相关文件", "读取必要上下文", "输出调查结论和不确定项"],
      "verification": { "required": false, "evidence_source": "system_sandbox_stdout_stderr", "acceptable_evidence": ["file_search_result"], "audit_fields": ["timestamp", "command", "exit_code", "stdout_digest", "stderr_digest", "sha256"] },
      "fallback": { "when_confidence_below": 0.75, "action": "ask_clarifying_question", "on_max_retry_exceeded": "MELT_DOWN_TO_查", "on_meltdown": "revoke_write_permissions_and_emit_bug_report" }
    },
    {
      "code": "解",
      "name": "explain",
      "definition": "解释代码、报错、架构或概念，不修改代码。",
      "intent_examples": ["这是什么意思", "解释一下这段代码", "这个报错什么意思"],
      "bound_skill_patterns": ["structured_explanation", "documentation"],
      "allowed_actions": ["read_files", "search_code"],
      "forbidden_actions": ["edit_files", "install_dependency", "claim_unverified_runtime_behavior"],
      "tool_policy": { "read": "allowed", "write": "forbidden", "network": "approval_required", "dependency_install": "forbidden" },
      "runtime_environment": { "auto_inject_local_env": true, "context_breaker_on_switch": true, "evidence_capture": "system_sandbox", "audit_log_write_access": "system_only" },
      "routing_target": "explain_workflow",
      "model_policy": { "temperature": 0.1, "max_retry_limit": 1, "load_minimal_context": true, "prefer_deterministic_steps": true },
      "required_steps": ["读取必要上下文", "区分事实与推断", "按结构解释"],
      "verification": { "required": false, "evidence_source": "system_sandbox_stdout_stderr", "acceptable_evidence": ["source_reference"], "audit_fields": ["timestamp", "command", "exit_code", "stdout_digest", "stderr_digest", "sha256"] },
      "fallback": { "when_confidence_below": 0.75, "action": "ask_clarifying_question_or_route_to_查", "on_max_retry_exceeded": "MELT_DOWN_TO_查", "on_meltdown": "revoke_write_permissions_and_emit_bug_report" }
    },
    {
      "code": "修",
      "name": "fix",
      "definition": "修复已有代码中的错误、失败测试、运行异常或不符合预期的行为。",
      "intent_examples": ["跑不通", "报错了", "测试失败", "这个 bug 帮我修一下"],
      "bound_skill_patterns": ["systematic_debugging", "test_driven_development", "surgical_change"],
      "allowed_actions": ["read_files", "search_code", "run_relevant_commands", "edit_scoped_files"],
      "forbidden_actions": ["unrelated_refactor", "change_public_api_without_need", "delete_user_changes", "claim_success_without_verification", "install_unapproved_dependency"],
      "tool_policy": { "read": "allowed", "write": "scoped_to_impact_files", "network": "approval_required", "dependency_install": "forbidden" },
      "runtime_environment": { "auto_inject_local_env": true, "context_breaker_on_switch": true, "evidence_capture": "system_sandbox", "audit_log_write_access": "system_only" },
      "routing_target": "debug_fix_workflow",
      "model_policy": { "temperature": 0.0, "max_retry_limit": 3, "load_minimal_context": true, "prefer_deterministic_steps": true },
      "required_steps": ["捕获系统环境报错日志与失败上下文", "提取并运行最小失败复现用例", "锁定受影响的文件与行号", "执行外科手术式修改", "运行本地单测与构建验证", "导出由系统层捕获的验证证据摘要"],
      "verification": { "required": true, "evidence_source": "system_sandbox_stdout_stderr", "acceptable_evidence": ["test_output_hash", "build_exit_code_0", "manual_reproduction_result_hash"], "audit_fields": ["timestamp", "command", "exit_code", "stdout_digest", "stderr_digest", "sha256"] },
      "fallback": { "when_confidence_below": 0.75, "action": "ask_clarifying_question_or_route_to_查", "on_max_retry_exceeded": "MELT_DOWN_TO_查", "on_meltdown": "revoke_write_permissions_and_emit_bug_report" }
    },
    {
      "code": "造",
      "name": "build",
      "definition": "新增功能、脚本、接口或组件。",
      "intent_examples": ["新增一个功能", "写一个脚本", "实现这个接口"],
      "bound_skill_patterns": ["spec_first_development", "implementation_plan", "test_driven_development"],
      "allowed_actions": ["read_files", "search_code", "edit_scoped_files", "run_relevant_commands"],
      "forbidden_actions": ["skip_requirement_clarification", "ignore_existing_patterns", "claim_success_without_verification"],
      "tool_policy": { "read": "allowed", "write": "scoped", "network": "approval_required", "dependency_install": "approval_required" },
      "runtime_environment": { "auto_inject_local_env": true, "context_breaker_on_switch": true, "evidence_capture": "system_sandbox", "audit_log_write_access": "system_only" },
      "routing_target": "build_workflow",
      "model_policy": { "temperature": 0.1, "max_retry_limit": 3, "load_minimal_context": true, "prefer_deterministic_steps": true },
      "required_steps": ["确认需求边界", "查找现有模式", "写测试或验证用例", "实现最小功能", "运行验证"],
      "verification": { "required": true, "evidence_source": "system_sandbox_stdout_stderr", "acceptable_evidence": ["test_output_hash", "build_output_hash"], "audit_fields": ["timestamp", "command", "exit_code", "stdout_digest", "stderr_digest", "sha256"] },
      "fallback": { "when_confidence_below": 0.75, "action": "ask_clarifying_question", "on_max_retry_exceeded": "MELT_DOWN_TO_查", "on_meltdown": "revoke_write_permissions_and_emit_bug_report" }
    },
    {
      "code": "改",
      "name": "change",
      "definition": "修改、优化或重构已有实现，尽量保持外部行为稳定。",
      "intent_examples": ["优化一下", "重构这段", "调整实现"],
      "bound_skill_patterns": ["surgical_change", "simplicity_first", "interface_preservation"],
      "allowed_actions": ["read_files", "search_code", "edit_scoped_files", "run_relevant_commands"],
      "forbidden_actions": ["unrelated_refactor", "public_api_change_without_approval", "delete_user_changes"],
      "tool_policy": { "read": "allowed", "write": "scoped_to_impact_files", "network": "approval_required", "dependency_install": "approval_required" },
      "runtime_environment": { "auto_inject_local_env": true, "context_breaker_on_switch": true, "evidence_capture": "system_sandbox", "audit_log_write_access": "system_only" },
      "routing_target": "change_workflow",
      "model_policy": { "temperature": 0.0, "max_retry_limit": 2, "load_minimal_context": true, "prefer_deterministic_steps": true },
      "required_steps": ["确认现有行为", "限定影响范围", "执行最小修改", "运行回归验证"],
      "verification": { "required": true, "evidence_source": "system_sandbox_stdout_stderr", "acceptable_evidence": ["regression_output_hash"], "audit_fields": ["timestamp", "command", "exit_code", "stdout_digest", "stderr_digest", "sha256"] },
      "fallback": { "when_confidence_below": 0.75, "action": "ask_clarifying_question_or_route_to_查", "on_max_retry_exceeded": "MELT_DOWN_TO_查", "on_meltdown": "revoke_write_permissions_and_emit_bug_report" }
    },
    {
      "code": "测",
      "name": "test",
      "definition": "编写、补充或运行测试，验证系统行为。",
      "intent_examples": ["跑测试", "写单测", "确认没问题"],
      "bound_skill_patterns": ["test_driven_development", "verification_before_completion"],
      "allowed_actions": ["read_files", "search_code", "run_relevant_commands", "edit_test_files"],
      "forbidden_actions": ["edit_production_files_without_approval", "fake_test_output"],
      "tool_policy": { "read": "allowed", "write": "scoped", "network": "approval_required", "dependency_install": "approval_required" },
      "runtime_environment": { "auto_inject_local_env": true, "context_breaker_on_switch": true, "evidence_capture": "system_sandbox", "audit_log_write_access": "system_only" },
      "routing_target": "test_workflow",
      "model_policy": { "temperature": 0.0, "max_retry_limit": 2, "load_minimal_context": true, "prefer_deterministic_steps": true },
      "required_steps": ["识别测试目标", "编写或选择测试", "运行测试", "记录系统层证据"],
      "verification": { "required": true, "evidence_source": "system_sandbox_stdout_stderr", "acceptable_evidence": ["test_output_hash"], "audit_fields": ["timestamp", "command", "exit_code", "stdout_digest", "stderr_digest", "sha256"] },
      "fallback": { "when_confidence_below": 0.75, "action": "ask_clarifying_question", "on_max_retry_exceeded": "MELT_DOWN_TO_查", "on_meltdown": "revoke_write_permissions_and_emit_bug_report" }
    },
    {
      "code": "审",
      "name": "review",
      "definition": "代码审查，只找问题、风险和缺失证据，不直接修改。",
      "intent_examples": ["帮我 review", "看看有没有问题", "审查风险"],
      "bound_skill_patterns": ["code_review", "evidence_first_review"],
      "allowed_actions": ["read_files", "search_code", "run_read_only_commands"],
      "forbidden_actions": ["edit_files", "commit_changes", "fix_without_approval"],
      "tool_policy": { "read": "allowed", "write": "forbidden", "network": "approval_required", "dependency_install": "forbidden" },
      "runtime_environment": { "auto_inject_local_env": true, "context_breaker_on_switch": true, "evidence_capture": "system_sandbox", "audit_log_write_access": "system_only" },
      "routing_target": "review_workflow",
      "model_policy": { "temperature": 0.0, "max_retry_limit": 1, "load_minimal_context": true, "prefer_deterministic_steps": true },
      "required_steps": ["读取变更", "识别风险", "用文件和行号输出证据", "列出测试缺口"],
      "verification": { "required": false, "evidence_source": "system_sandbox_stdout_stderr", "acceptable_evidence": ["file_line_reference"], "audit_fields": ["timestamp", "command", "exit_code", "stdout_digest", "stderr_digest", "sha256"] },
      "fallback": { "when_confidence_below": 0.75, "action": "ask_clarifying_question_or_route_to_查", "on_max_retry_exceeded": "MELT_DOWN_TO_查", "on_meltdown": "revoke_write_permissions_and_emit_bug_report" }
    },
    {
      "code": "设",
      "name": "design",
      "definition": "UI 与设计系统实现或一致性检查。",
      "intent_examples": ["调整界面", "按 DESIGN.md 统一", "优化视觉"],
      "bound_skill_patterns": ["design_system", "responsive_ui", "accessibility"],
      "allowed_actions": ["read_files", "search_code", "edit_scoped_files", "run_visual_checks"],
      "forbidden_actions": ["ignore_design_source", "unrelated_product_redesign"],
      "tool_policy": { "read": "allowed", "write": "scoped", "network": "approval_required", "dependency_install": "approval_required" },
      "runtime_environment": { "auto_inject_local_env": true, "context_breaker_on_switch": true, "evidence_capture": "system_sandbox", "audit_log_write_access": "system_only" },
      "routing_target": "design_workflow",
      "model_policy": { "temperature": 0.1, "max_retry_limit": 2, "load_minimal_context": true, "prefer_deterministic_steps": true },
      "required_steps": ["读取 DESIGN.md 或建立简要设计基准", "修改共享样式或组件", "检查响应式和可访问性"],
      "verification": { "required": true, "evidence_source": "system_sandbox_stdout_stderr", "acceptable_evidence": ["visual_check_hash", "build_output_hash"], "audit_fields": ["timestamp", "command", "exit_code", "stdout_digest", "stderr_digest", "sha256"] },
      "fallback": { "when_confidence_below": 0.75, "action": "ask_clarifying_question", "on_max_retry_exceeded": "MELT_DOWN_TO_查", "on_meltdown": "revoke_write_permissions_and_emit_bug_report" }
    },
    {
      "code": "源",
      "name": "source",
      "definition": "依赖、License、本地已有能力和代码资产溯源。",
      "intent_examples": ["检查依赖来源", "有没有已有组件", "不要重复造轮子", "看看 License 风险"],
      "bound_skill_patterns": ["dependency_audit", "license_review", "reuse_existing_code"],
      "allowed_actions": ["read_files", "search_code", "run_read_only_commands"],
      "forbidden_actions": ["edit_files", "install_dependency", "approve_untrusted_source"],
      "tool_policy": { "read": "allowed", "write": "forbidden", "network": "approval_required", "dependency_install": "forbidden" },
      "runtime_environment": { "auto_inject_local_env": true, "context_breaker_on_switch": true, "evidence_capture": "system_sandbox", "audit_log_write_access": "system_only" },
      "routing_target": "source_audit_workflow",
      "model_policy": { "temperature": 0.0, "max_retry_limit": 1, "load_minimal_context": true, "prefer_deterministic_steps": true },
      "required_steps": ["检查本地已有能力", "检查依赖清单", "识别 License 或来源风险", "输出复用建议"],
      "verification": { "required": true, "evidence_source": "system_sandbox_stdout_stderr", "acceptable_evidence": ["dependency_inventory_hash", "local_symbol_search_hash"], "audit_fields": ["timestamp", "command", "exit_code", "stdout_digest", "stderr_digest", "sha256"] },
      "fallback": { "when_confidence_below": 0.75, "action": "ask_clarifying_question_or_route_to_查", "on_max_retry_exceeded": "MELT_DOWN_TO_查", "on_meltdown": "revoke_write_permissions_and_emit_bug_report" }
    },
    {
      "code": "卫",
      "name": "guard",
      "definition": "安全防护与危险操作拦截。",
      "intent_examples": ["检查安全风险", "拦截危险命令", "防止提示词注入"],
      "bound_skill_patterns": ["security_guard", "dangerous_action_blocking", "permission_whitelist"],
      "allowed_actions": ["read_files", "search_code", "run_read_only_commands", "block_dangerous_actions"],
      "forbidden_actions": ["install_dependency_without_approval", "run_dangerous_command", "ignore_security_findings"],
      "tool_policy": { "read": "allowed", "write": "forbidden", "network": "approval_required", "dependency_install": "forbidden" },
      "runtime_environment": { "auto_inject_local_env": true, "context_breaker_on_switch": true, "evidence_capture": "system_sandbox", "audit_log_write_access": "system_only" },
      "routing_target": "security_guard_workflow",
      "model_policy": { "temperature": 0.0, "max_retry_limit": 1, "load_minimal_context": true, "prefer_deterministic_steps": true },
      "required_steps": ["识别高危动作", "检查权限策略", "输出阻断或批准建议"],
      "verification": { "required": true, "evidence_source": "system_sandbox_stdout_stderr", "acceptable_evidence": ["security_scan_hash", "permission_policy_hash"], "audit_fields": ["timestamp", "command", "exit_code", "stdout_digest", "stderr_digest", "sha256"] },
      "fallback": { "when_confidence_below": 0.75, "action": "route_to_查", "on_max_retry_exceeded": "MELT_DOWN_TO_查", "on_meltdown": "revoke_write_permissions_and_emit_bug_report" }
    },
    {
      "code": "隔",
      "name": "isolate",
      "definition": "多 Agent 隔离协作，分离不可信输入、调度和写入权限。",
      "intent_examples": ["隔离外部输入", "多 Agent 安全协作", "不要让读取者写入"],
      "bound_skill_patterns": ["reader_orchestrator_writer", "prompt_injection_isolation"],
      "allowed_actions": ["read_files", "search_code", "route_between_agents"],
      "forbidden_actions": ["share_untrusted_context_with_writer", "grant_write_to_reader"],
      "tool_policy": { "read": "allowed", "write": "forbidden", "network": "approval_required", "dependency_install": "forbidden" },
      "runtime_environment": { "auto_inject_local_env": true, "context_breaker_on_switch": true, "evidence_capture": "system_sandbox", "audit_log_write_access": "system_only" },
      "routing_target": "isolated_multi_agent_workflow",
      "model_policy": { "temperature": 0.0, "max_retry_limit": 1, "load_minimal_context": true, "prefer_deterministic_steps": true },
      "required_steps": ["分离 Reader、Orchestrator、Writer 权限", "清洗不可信输入", "输出隔离上下文摘要"],
      "verification": { "required": true, "evidence_source": "system_sandbox_stdout_stderr", "acceptable_evidence": ["isolation_policy_hash"], "audit_fields": ["timestamp", "command", "exit_code", "stdout_digest", "stderr_digest", "sha256"] },
      "fallback": { "when_confidence_below": 0.75, "action": "ask_clarifying_question_or_route_to_查", "on_max_retry_exceeded": "MELT_DOWN_TO_查", "on_meltdown": "revoke_write_permissions_and_emit_bug_report" }
    },
    {
      "code": "简",
      "name": "simplify",
      "definition": "极简、克制、外科手术式改动，避免过度封装和范围扩散。",
      "intent_examples": ["简单点", "别大改", "最小改动"],
      "bound_skill_patterns": ["simplicity_first", "surgical_change", "reuse_existing_code"],
      "allowed_actions": ["read_files", "search_code", "edit_scoped_files", "run_relevant_commands"],
      "forbidden_actions": ["over_abstraction", "large_unrelated_rewrite", "new_dependency_without_need"],
      "tool_policy": { "read": "allowed", "write": "scoped_to_impact_files", "network": "approval_required", "dependency_install": "forbidden" },
      "runtime_environment": { "auto_inject_local_env": true, "context_breaker_on_switch": true, "evidence_capture": "system_sandbox", "audit_log_write_access": "system_only" },
      "routing_target": "simplify_workflow",
      "model_policy": { "temperature": 0.0, "max_retry_limit": 2, "load_minimal_context": true, "prefer_deterministic_steps": true },
      "required_steps": ["确认最小目标", "查找可复用现有能力", "执行最小修改", "验证行为不扩散"],
      "verification": { "required": true, "evidence_source": "system_sandbox_stdout_stderr", "acceptable_evidence": ["minimal_diff_review_hash"], "audit_fields": ["timestamp", "command", "exit_code", "stdout_digest", "stderr_digest", "sha256"] },
      "fallback": { "when_confidence_below": 0.75, "action": "ask_clarifying_question_or_route_to_查", "on_max_retry_exceeded": "MELT_DOWN_TO_查", "on_meltdown": "revoke_write_permissions_and_emit_bug_report" }
    }
  ]
}
```

- [ ] **Step 3: Confirm dictionary is valid JSON**

Run:

```bash
python3 -m json.tool agent_skill_dictionary/programming-agent-skill-dictionary.json >/tmp/programming-agent-skill-dictionary.json
```

Expected: exit code 0.

## Task 3: Add Stack Policy Document

**Files:**
- Create: `agent_skill_dictionary/execution-stack-policy.md`

- [ ] **Step 1: Create stack policy**

Create `agent_skill_dictionary/execution-stack-policy.md`:

```markdown
# Execution Stack Policy

The instruction stack controls multi-character execution.

## Rules

1. Each execution character is an atomic unit.
2. Multi-character intent is pushed in reverse execution order.
3. The top of stack executes first.
4. Each character reloads its own permissions, skill patterns, runtime policy, and verification rules.
5. The context budget circuit breaker runs between characters.
6. Later characters do not inherit write permissions unless explicitly granted by their dictionary entry.
7. Any character that exceeds `max_retry_limit` melts down to `查`.

## Example

User intent:

```text
修 + 测
```

Stack:

```text
Stack.push(测)
Stack.push(修)
```

Execution:

1. Pop `修`.
2. Run fix workflow.
3. Capture evidence.
4. Clear intermediate context.
5. Pop `测`.
6. Run test workflow with test permissions only.
```

- [ ] **Step 2: Confirm policy contains core phrases**

Run:

```bash
rg -n "atomic unit|context budget|melts down to" agent_skill_dictionary/execution-stack-policy.md
```

Expected: three matching lines.

## Task 4: Add Loader

**Files:**
- Create: `agent_skill_dictionary/__init__.py`
- Create: `agent_skill_dictionary/loader.py`

- [ ] **Step 1: Create package exports**

Create `agent_skill_dictionary/__init__.py`:

```python
"""Agent Skill Dictionary utilities."""

from .loader import DictionaryEntry, load_dictionary, lookup_entry

__all__ = ["DictionaryEntry", "load_dictionary", "lookup_entry"]
```

- [ ] **Step 2: Create loader**

Create `agent_skill_dictionary/loader.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DictionaryEntry:
    code: str
    name: str
    definition: str
    routing_target: str
    tool_policy: dict[str, str]
    model_policy: dict[str, Any]
    fallback: dict[str, Any]
    raw: dict[str, Any]


def load_dictionary(path: str | Path) -> dict[str, Any]:
    dictionary_path = Path(path)
    with dictionary_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Dictionary root must be an object")
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Dictionary must contain a non-empty entries list")
    return data


def lookup_entry(dictionary: dict[str, Any], code: str) -> DictionaryEntry:
    for entry in dictionary["entries"]:
        if entry.get("code") == code:
            return DictionaryEntry(
                code=entry["code"],
                name=entry["name"],
                definition=entry["definition"],
                routing_target=entry["routing_target"],
                tool_policy=entry["tool_policy"],
                model_policy=entry["model_policy"],
                fallback=entry["fallback"],
                raw=entry,
            )
    raise KeyError(f"Unknown execution code: {code}")
```

- [ ] **Step 3: Smoke test loader**

Run:

```bash
python3 - <<'PY'
from agent_skill_dictionary import load_dictionary, lookup_entry
d = load_dictionary("agent_skill_dictionary/programming-agent-skill-dictionary.json")
print(lookup_entry(d, "源").routing_target)
PY
```

Expected output:

```text
source_audit_workflow
```

## Task 5: Add Validator

**Files:**
- Create: `agent_skill_dictionary/validator.py`

- [ ] **Step 1: Create validator**

Create `agent_skill_dictionary/validator.py`:

```python
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .loader import load_dictionary


REQUIRED_AUDIT_FIELDS = {
    "timestamp",
    "command",
    "exit_code",
    "stdout_digest",
    "stderr_digest",
    "sha256",
}


def validate_dictionary(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    entries = data.get("entries", [])
    codes = [entry.get("code") for entry in entries]

    for code, count in Counter(codes).items():
        if count > 1:
            errors.append(f"Duplicate execution code: {code}")

    by_code = {entry["code"]: entry for entry in entries if "code" in entry}
    for required in ["查", "修", "测", "源", "卫"]:
        if required not in by_code:
            errors.append(f"Missing required execution code: {required}")

    for entry in entries:
        code = entry.get("code", "<unknown>")
        tool_policy = entry.get("tool_policy", {})
        runtime = entry.get("runtime_environment", {})
        verification = entry.get("verification", {})
        fallback = entry.get("fallback", {})

        if runtime.get("audit_log_write_access") != "system_only":
            errors.append(f"{code}: audit log must be system_only")

        if verification.get("required"):
            audit_fields = set(verification.get("audit_fields", []))
            missing = REQUIRED_AUDIT_FIELDS - audit_fields
            if missing:
                errors.append(f"{code}: missing audit fields {sorted(missing)}")

        if code in {"查", "审", "源", "卫", "隔"} and tool_policy.get("write") != "forbidden":
            errors.append(f"{code}: read-only/control code must forbid write")

        if code == "源" and tool_policy.get("dependency_install") != "forbidden":
            errors.append("源: dependency_install must be forbidden")

        if code == "修" and fallback.get("on_max_retry_exceeded") != "MELT_DOWN_TO_查":
            errors.append("修: must melt down to 查 after max retries")

    return errors


def validate_file(path: str | Path) -> list[str]:
    return validate_dictionary(load_dictionary(path))


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "agent_skill_dictionary/programming-agent-skill-dictionary.json"
    validation_errors = validate_file(target)
    if validation_errors:
        for error in validation_errors:
            print(error)
        raise SystemExit(1)
    print("OK")
```

- [ ] **Step 2: Run validator**

Run:

```bash
python3 -m agent_skill_dictionary.validator agent_skill_dictionary/programming-agent-skill-dictionary.json
```

Expected output:

```text
OK
```

## Task 6: Add Tests

**Files:**
- Create: `tests/test_agent_skill_dictionary.py`

- [ ] **Step 1: Create tests**

Create `tests/test_agent_skill_dictionary.py`:

```python
from pathlib import Path

from agent_skill_dictionary import load_dictionary, lookup_entry
from agent_skill_dictionary.validator import validate_dictionary


DICTIONARY_PATH = Path("agent_skill_dictionary/programming-agent-skill-dictionary.json")


def test_dictionary_validates_without_errors():
    data = load_dictionary(DICTIONARY_PATH)
    assert validate_dictionary(data) == []


def test_source_code_is_read_only_and_blocks_dependency_install():
    data = load_dictionary(DICTIONARY_PATH)
    source = lookup_entry(data, "源")
    assert source.tool_policy["write"] == "forbidden"
    assert source.tool_policy["dependency_install"] == "forbidden"
    assert source.routing_target == "source_audit_workflow"


def test_guard_code_is_distinct_from_source_code():
    data = load_dictionary(DICTIONARY_PATH)
    source = lookup_entry(data, "源")
    guard = lookup_entry(data, "卫")
    assert source.routing_target == "source_audit_workflow"
    assert guard.routing_target == "security_guard_workflow"
    assert "license_review" in source.raw["bound_skill_patterns"]
    assert "dangerous_action_blocking" in guard.raw["bound_skill_patterns"]


def test_fix_melts_down_to_inspect_after_retries():
    data = load_dictionary(DICTIONARY_PATH)
    fix = lookup_entry(data, "修")
    assert fix.model_policy["max_retry_limit"] == 3
    assert fix.fallback["on_max_retry_exceeded"] == "MELT_DOWN_TO_查"


def test_read_only_codes_forbid_write():
    data = load_dictionary(DICTIONARY_PATH)
    for code in ["查", "审", "源", "卫", "隔"]:
        entry = lookup_entry(data, code)
        assert entry.tool_policy["write"] == "forbidden"
```

- [ ] **Step 2: Run pytest if available**

Run:

```bash
python3 -m pytest tests/test_agent_skill_dictionary.py -q
```

Expected if pytest is installed:

```text
5 passed
```

If pytest is not installed, run the validation command from Task 5 and the loader smoke test from Task 4 instead.

## Task 7: Final Verification

**Files:**
- Verify all created files.

- [ ] **Step 1: Validate JSON files**

Run:

```bash
python3 -m json.tool schemas/agent-skill-dictionary.schema.json >/tmp/agent-skill-schema.json
python3 -m json.tool agent_skill_dictionary/programming-agent-skill-dictionary.json >/tmp/programming-agent-skill-dictionary.json
```

Expected: both commands exit 0.

- [ ] **Step 2: Run validator**

Run:

```bash
python3 -m agent_skill_dictionary.validator agent_skill_dictionary/programming-agent-skill-dictionary.json
```

Expected:

```text
OK
```

- [ ] **Step 3: Run tests**

Run:

```bash
python3 -m pytest tests/test_agent_skill_dictionary.py -q
```

Expected:

```text
5 passed
```

- [ ] **Step 4: Review generated file list**

Run:

```bash
find schemas agent_skill_dictionary tests -maxdepth 2 -type f | sort
```

Expected files:

```text
agent_skill_dictionary/__init__.py
agent_skill_dictionary/execution-stack-policy.md
agent_skill_dictionary/loader.py
agent_skill_dictionary/programming-agent-skill-dictionary.json
agent_skill_dictionary/validator.py
schemas/agent-skill-dictionary.schema.json
tests/test_agent_skill_dictionary.py
```

## Self-Review

- Spec coverage: Implements Phase 1 static dictionary, `源`, stack policy, context breaker representation, system evidence fields, and meltdown fallback.
- Scope control: Does not build a full Agent runtime, router, or UI. This is intentional for Phase 1.
- Placeholder scan: No TODO/TBD placeholders.
- Type consistency: `DictionaryEntry`, `load_dictionary`, `lookup_entry`, `validate_dictionary`, and `validate_file` names are consistent across tasks.
