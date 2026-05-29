from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .context_breaker import build_active_context
from .executor import execute_command
from .guard_executor import guard_text, guard_workspace, validate_guard_policy_file
from .halt_executor import freeze_halt_snapshot
from .inspect_executor import inspect_workspace
from .kernel_policy import KernelPolicy, get_kernel_policy
from .memory_executor import archive_markdown
from .patch_executor import apply_controlled_patch
from .prompt_executor import create_confirmation_ticket
from .summary_executor import summarize_active_context
from .trigram_contract import get_trigram_contract, get_trigram_relations


class OneWordState(Enum):
    LI = ("离", "查")
    ZHEN = ("震", "修")
    XUN = ("巽", "测")
    KAN = ("坎", "卫")
    GEN = ("艮", "停")
    DUI = ("兑", "问")
    KUN = ("坤", "记")
    QIAN = ("乾", "总")

    @property
    def hexagram(self) -> str:
        return self.value[0]

    @property
    def code(self) -> str:
        return self.value[1]


STATE_BY_CODE = {state.code: state for state in OneWordState}


@dataclass
class Compiler:
    def compile(self, user_input: str) -> OneWordState:
        message = user_input.lower()
        if any(marker in message for marker in ("停一下", "暂停", "熔断")):
            return OneWordState.GEN
        if any(marker in message for marker in ("危险", "安全", "rm -rf", "注入", "外联", "供应链", "漏洞", "依赖风险", "cve")):
            return OneWordState.KAN
        if any(marker in message for marker in ("bug", "报错", "跑不通", "失败", "修")):
            return OneWordState.ZHEN
        if any(marker in message for marker in ("测试", "验证", "覆盖率")):
            return OneWordState.XUN
        if any(marker in message for marker in ("问清楚", "确认", "不明确", "澄清")):
            return OneWordState.DUI
        if any(marker in message for marker in ("记录", "记一下", "文档", "adr")):
            return OneWordState.KUN
        if any(marker in message for marker in ("总结", "交接", "压缩上下文")):
            return OneWordState.QIAN
        return OneWordState.LI


@dataclass
class MutationEngine:
    max_retries: int = 3

    def next_state(
        self,
        current_state: OneWordState,
        result: dict[str, Any],
        context: dict[str, Any],
    ) -> OneWordState:
        trigger = self._trigger_for(current_state, result, context)
        if current_state is OneWordState.GEN:
            return self._record_transition(current_state, OneWordState.GEN, trigger, result, context)
        if result.get("risk") == "high":
            return self._record_transition(current_state, OneWordState.GEN, trigger, result, context)
        if result.get("needs_human"):
            return self._record_transition(current_state, OneWordState.DUI, trigger, result, context)

        ok = bool(result.get("ok"))
        if not ok:
            context["retry_count"] = int(context.get("retry_count", 0)) + 1
            if context["retry_count"] >= self.max_retries:
                return self._record_transition(current_state, OneWordState.GEN, "retry_limit_exceeded", result, context)
            if current_state is OneWordState.XUN:
                return self._record_transition(current_state, OneWordState.ZHEN, trigger, result, context)
            return self._record_transition(current_state, current_state, trigger, result, context)

        context["retry_count"] = 0
        if current_state is OneWordState.LI:
            return self._record_transition(current_state, OneWordState.QIAN, trigger, result, context)
        if current_state is OneWordState.ZHEN:
            return self._record_transition(current_state, OneWordState.XUN, trigger, result, context)
        if current_state is OneWordState.XUN:
            return self._record_transition(current_state, OneWordState.KUN, trigger, result, context)
        if current_state is OneWordState.KAN:
            return self._record_transition(current_state, OneWordState.LI, trigger, result, context)
        if current_state is OneWordState.DUI:
            return self._record_transition(current_state, OneWordState.LI, trigger, result, context)
        if current_state is OneWordState.KUN:
            return self._record_transition(current_state, OneWordState.QIAN, trigger, result, context)
        return self._record_transition(current_state, OneWordState.QIAN, trigger, result, context)

    def _trigger_for(
        self,
        current_state: OneWordState,
        result: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        if result.get("risk") == "high":
            return "risk_high"
        if result.get("needs_human"):
            return "needs_human"
        if current_state is OneWordState.KAN and result.get("ok"):
            return "guard_pass"
        if current_state is OneWordState.ZHEN and result.get("ok"):
            return "patch_applied"
        if current_state is OneWordState.XUN and result.get("exit_code") == 0:
            return "exit_code_0"
        if result.get("exit_code") not in (None, 0):
            return "exit_code_nonzero"
        if result.get("ok"):
            return "ok"
        return "failed"

    def _record_transition(
        self,
        current_state: OneWordState,
        next_state: OneWordState,
        trigger: str,
        result: dict[str, Any],
        context: dict[str, Any],
    ) -> OneWordState:
        transitions = context.setdefault("transitions", [])
        from_contract = get_trigram_contract(current_state.code)
        to_contract = get_trigram_contract(next_state.code)
        from_relations = get_trigram_relations(current_state.code)
        to_relations = get_trigram_relations(next_state.code)
        evidence = result.get("evidence") if isinstance(result, dict) else None
        transitions.append(
            {
                "from": current_state.code,
                "from_trigram": from_contract["binary_trigram"],
                "from_opposite_root": from_relations["opposite_root"],
                "from_opposite_trigram": from_relations["opposite_trigram"],
                "from_reverse_root": from_relations["reverse_root"],
                "from_reverse_trigram": from_relations["reverse_trigram"],
                "to": next_state.code,
                "to_trigram": to_contract["binary_trigram"],
                "to_opposite_root": to_relations["opposite_root"],
                "to_opposite_trigram": to_relations["opposite_trigram"],
                "to_reverse_root": to_relations["reverse_root"],
                "to_reverse_trigram": to_relations["reverse_trigram"],
                "trigger": trigger,
                "retry_count": int(context.get("retry_count", 0)),
                "evidence_sha256": evidence.get("sha256") if isinstance(evidence, dict) else None,
            }
        )
        return next_state


@dataclass
class OneWordAgent:
    codebase_path: str
    compiler: Compiler = field(default_factory=Compiler)
    mutation_engine: MutationEngine = field(default_factory=MutationEngine)
    max_steps: int = 12
    verification_command: list[str] | None = None
    audit_log_path: str | Path | None = None
    enable_real_inspect: bool = False
    enable_real_guard: bool = False
    guard_policy_path: str | Path | None = None
    enable_real_summary: bool = False
    enable_real_memory: bool = False
    enable_real_halt: bool = False
    enable_real_prompt: bool = False
    enable_real_patch: bool = False
    use_docker: bool = False
    docker_image: str = "python:3.11-slim"
    require_docker: bool = False
    enable_external_scanners: bool = False
    require_guard_scanner: bool = False
    guard_scanner_types: list[str] | tuple[str, ...] | None = None
    memory_dir: str | Path | None = None
    halt_snapshot_dir: str | Path | None = None
    prompt_ticket_dir: str | Path | None = None
    patch_plan: list[dict[str, Any]] | None = None

    def __post_init__(self) -> None:
        if self.enable_real_guard and self.guard_policy_path is not None:
            errors = validate_guard_policy_file(self.guard_policy_path)
            if errors:
                joined = "; ".join(errors)
                raise ValueError(f"Invalid guard policy: {joined}")
        self.current_state = OneWordState.LI
        self.context: dict[str, Any] = {
            "path": self.codebase_path,
            "original_request": "",
            "active_context": {},
            "history": [],
            "retry_count": 0,
        }

    def compile_intent(self, user_input: str) -> OneWordState:
        return self.compiler.compile(user_input)

    def run(self, user_input: str) -> dict[str, Any]:
        self.current_state = self.compile_intent(user_input)
        self.context["original_request"] = user_input
        trace: list[str] = []
        audit_log: list[dict[str, Any]] = []

        for _ in range(self.max_steps):
            self._refresh_active_context()
            trace.append(self.current_state.code)
            policy = get_kernel_policy(self.current_state.code)
            audit_log.append(self._audit_entry(self.current_state, policy))

            if self.current_state is OneWordState.GEN:
                if self.enable_real_halt and not self._latest_result_for_state("停"):
                    result = self.execute_llm_core(self.current_state, policy, self.context)
                    self.context["history"].append(
                        {"state": self.current_state.code, "result": result}
                    )
                    self._refresh_active_context()
                return {"status": "halted", "trace": trace, "audit_log": audit_log}
            if self.current_state is OneWordState.DUI and self.enable_real_prompt:
                result = self.execute_llm_core(self.current_state, policy, self.context)
                self.context["history"].append(
                    {"state": self.current_state.code, "result": result}
                )
                self._refresh_active_context()
                return {"status": "waiting_for_human", "trace": trace, "audit_log": audit_log}
            if self.current_state is OneWordState.QIAN and len(trace) > 1 and not self.enable_real_summary:
                return {"status": "completed", "trace": trace, "audit_log": audit_log}

            result = self.execute_llm_core(self.current_state, policy, self.context)
            self.context["history"].append(
                {"state": self.current_state.code, "result": result}
            )
            if self.current_state is OneWordState.QIAN and self.enable_real_summary:
                self._refresh_active_context()
                return {"status": "completed", "trace": trace, "audit_log": audit_log}
            self.current_state = self.mutation_engine.next_state(
                self.current_state,
                result,
                self.context,
            )
            self._refresh_active_context()

        return {"status": "max_steps_exceeded", "trace": trace, "audit_log": audit_log}

    def execute_llm_core(
        self,
        state: OneWordState,
        policy: KernelPolicy,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        if state is OneWordState.LI and self.enable_real_inspect:
            return inspect_workspace(
                self.codebase_path,
                audit_log_path=self.audit_log_path,
            )
        if state is OneWordState.KAN and self.enable_real_guard:
            workspace_result = guard_workspace(
                self.codebase_path,
                audit_log_path=self.audit_log_path,
                policy_path=self.guard_policy_path,
                enable_external_scanners=self.enable_external_scanners,
                require_external_scanner=self.require_guard_scanner,
                scanner_types=self.guard_scanner_types,
            )
            input_result = guard_text(
                str(context.get("original_request", "")),
                policy_path=self.guard_policy_path,
            )
            if not input_result["findings"]:
                return workspace_result
            findings = list(input_result["findings"]) + list(workspace_result.get("findings", []))
            risk = "high" if any(item.get("severity") == "high" for item in findings) else workspace_result.get("risk", "low")
            blocked = any(bool(item.get("block")) for item in findings)
            return {
                **workspace_result,
                "ok": not blocked,
                "risk": risk,
                "trigger": "risk_high" if blocked or risk == "high" else "guard_pass",
                "finding_count": len(findings),
                "findings": findings,
            }
        if state is OneWordState.ZHEN and self.enable_real_patch:
            return apply_controlled_patch(
                self.codebase_path,
                self.patch_plan or [],
                audit_log_path=self.audit_log_path,
            )
        if state is OneWordState.ZHEN:
            return {
                "ok": False,
                "changed_files": [],
                "stdout": "",
                "stderr": "patch_evidence_missing",
                "error": "patch_evidence_missing",
            }
        if state is OneWordState.XUN and self.verification_command:
            result = execute_command(
                self.verification_command,
                cwd=self.codebase_path,
                workspace_root=self.codebase_path,
                audit_log_path=self.audit_log_path,
                use_docker=self.use_docker,
                docker_image=self.docker_image,
                require_docker=self.require_docker,
            )
            return {
                "ok": result["exit_code"] == 0,
                "exit_code": result["exit_code"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "sandbox": result["sandbox"],
                "sandbox_fallback": result["sandbox_fallback"],
                "evidence": result["evidence"],
            }
        if state is OneWordState.XUN:
            return {
                "ok": False,
                "exit_code": 127,
                "stdout": "",
                "stderr": "verification_command_missing",
                "error": "verification_command_missing",
            }
        if state is OneWordState.QIAN and self.enable_real_summary:
            return summarize_active_context(
                context.get("active_context", {}),
                audit_log_path=self.audit_log_path,
            )
        if state is OneWordState.KUN and self.enable_real_memory:
            markdown = self._latest_summary_markdown()
            target_dir = self.memory_dir or Path(self.codebase_path) / "memory"
            return archive_markdown(
                markdown,
                memory_dir=target_dir,
                audit_log_path=self.audit_log_path,
            )
        if state is OneWordState.GEN and self.enable_real_halt:
            target_dir = self.halt_snapshot_dir or Path(self.codebase_path) / "halt"
            return freeze_halt_snapshot(
                context.get("active_context", {}),
                snapshot_dir=target_dir,
                audit_log_path=self.audit_log_path,
            )
        if state is OneWordState.DUI and self.enable_real_prompt:
            target_dir = self.prompt_ticket_dir or Path(self.codebase_path) / "tickets"
            return create_confirmation_ticket(
                context.get("active_context", {}),
                ticket_dir=target_dir,
                audit_log_path=self.audit_log_path,
            )
        return {"ok": True}

    def _audit_entry(self, state: OneWordState, policy: KernelPolicy) -> dict[str, Any]:
        last_evidence = self._last_evidence()
        relations = get_trigram_relations(state.code)
        return {
            "state": state.code,
            "hexagram": state.hexagram,
            "allowed_tools": list(policy.allowed_tools),
            "evidence_required": list(policy.evidence_required),
            "retry_count": int(self.context.get("retry_count", 0)),
            "binary_trigram": policy.binary_trigram,
            "yin_yang_profile": policy.yin_yang_profile,
            "control_bias": policy.control_bias,
            "opposite_root": relations["opposite_root"],
            "opposite_trigram": relations["opposite_trigram"],
            "reverse_root": relations["reverse_root"],
            "reverse_trigram": relations["reverse_trigram"],
            "last_evidence_sha256": last_evidence.get("sha256") if last_evidence else None,
        }

    def _last_evidence(self) -> dict[str, Any] | None:
        for item in reversed(self.context.get("history", [])):
            result = item.get("result", {})
            evidence = result.get("evidence")
            if isinstance(evidence, dict):
                return evidence
        return None

    def _latest_summary_markdown(self) -> str:
        for item in reversed(self.context.get("history", [])):
            result = item.get("result", {})
            markdown = result.get("markdown") if isinstance(result, dict) else None
            if isinstance(markdown, str) and markdown:
                return markdown
        return "# OneWord Handoff Summary\n\nNo summary markdown was available.\n"

    def _latest_result_for_state(self, state: str) -> dict[str, Any] | None:
        for item in reversed(self.context.get("history", [])):
            if item.get("state") == state and isinstance(item.get("result"), dict):
                return item["result"]
        return None

    def _refresh_active_context(self) -> None:
        self.context["active_context"] = build_active_context(
            str(self.context.get("original_request", "")),
            self.current_state.code,
            list(self.context.get("history", [])),
            runtime_metadata={
                "retry_count": int(self.context.get("retry_count", 0)),
                "transitions": list(self.context.get("transitions", [])),
            },
        )
