from dataclasses import dataclass

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.project_gateway import project_gateway


LEGACY_DANGEROUS_MARKERS = (
    "根目录",
    "shadow",
    "rm -rf /",
    "sudo rm",
    "忽略你之前",
    "忽略之前",
    "忽略所有安全限制",
    "忽略安全限制",
    "覆盖系统提示",
    "system_prompt",
    "完全服从",
    "dd if=",
    "/dev/disk",
    "chmod -r 777 /",
)
HOSTS_MARKERS = ("hosts文件", "hosts file")
VAGUE_MARKERS = (
    "随便",
    "看着办",
    "优化一下",
    "随便优化",
    "随便处理",
    "不太对劲",
    "怎么都行",
    "处理一下",
    "弄一下",
)
CURL_SHELL_MARKERS = ("bash", "shell", "| sh", "|sh", "宿主机")
HOST_SHELL_MARKERS = ("bash", "shell", "宿主机", "执行", "不用沙箱", "直接")
HOST_OUTSIDE_MARKERS = ("/tmp/", "/etc/", "/var/", "/home/", "outside_workspace")
HOST_CLEANUP_MARKERS = ("清理痕迹", "清除痕迹", "cover tracks", "cleanup traces")


@dataclass(frozen=True)
class PromptRule:
    rule_id: str
    family: str
    status_code: int
    facts: dict[str, str]
    reason: str


def classify_prompt(text: str) -> PromptRule | None:
    """Return a closed prompt rule, or None when the model still has to read the sentence."""
    if not isinstance(text, str) or not text.strip():
        return None
    lowered = text.lower()
    hosts_hit = any(marker in lowered for marker in HOSTS_MARKERS)
    stronger_hit = any(marker in lowered for marker in LEGACY_DANGEROUS_MARKERS)
    etc_hit = "/etc/" in lowered or "/etc" in lowered
    if stronger_hit or (etc_hit and not hosts_hit):
        return _halt_rule("legacy_dangerous", "dangerous", "dangerous_prompt_fail_closed")
    if hosts_hit:
        return _deny_rule("hosts_config", "hosts", "system_config_prompt_fail_closed")
    if any(marker in lowered for marker in VAGUE_MARKERS):
        return _deny_rule("vague_prompt", "vague", "vague_optimization_prompt_fail_closed")
    curl_hit = "curl " in lowered or "curl|" in lowered
    if curl_hit and any(marker in lowered for marker in CURL_SHELL_MARKERS):
        return _halt_rule("curl_pipe", "curl_pipe", "curl_pipe_fail_closed")
    if _host_execution(lowered):
        return _halt_rule("host_execution", "host_execution", "dangerous_host_command")
    if "pytest" in lowered:
        return _pytest_rule()
    return None


def _host_execution(lowered: str) -> bool:
    shell = any(marker.lower() in lowered for marker in HOST_SHELL_MARKERS)
    outside = any(marker.lower() in lowered for marker in HOST_OUTSIDE_MARKERS)
    cleanup = any(marker.lower() in lowered for marker in HOST_CLEANUP_MARKERS)
    return shell and (outside or cleanup)


def decide_prompt(text: str) -> dict[str, object] | None:
    rule = classify_prompt(text)
    if rule is None:
        return None
    profile = IchingKernel.cross_cutting_profile(rule.status_code)
    return {
        "rule_id": rule.rule_id,
        "family": rule.family,
        "yizijue_state": format(rule.status_code, "06b"),
        "facts": dict(rule.facts),
        "reason": rule.reason,
        "action": project_gateway(rule.status_code, rule.facts),
        "symbolic_transition": profile["transition"],
    }


def _halt_rule(rule_id: str, family: str, reason: str) -> PromptRule:
    return PromptRule(
        rule_id=rule_id,
        family=family,
        status_code=0b100001,
        facts={
            "intent_type": "bash_execution",
            "path_scope": "outside_workspace",
            "sandbox_state": "missing",
            "evidence_state": "required",
        },
        reason=reason,
    )


def _deny_rule(rule_id: str, family: str, reason: str) -> PromptRule:
    return PromptRule(
        rule_id=rule_id,
        family=family,
        status_code=0b000000,
        facts={
            "intent_type": "invalid_intent",
            "path_scope": "no_path",
            "sandbox_state": "not_required",
            "evidence_state": "required",
        },
        reason=reason,
    )


def _pytest_rule() -> PromptRule:
    return PromptRule(
        rule_id="pytest_verifier",
        family="pytest",
        status_code=0b010010,
        facts={
            "intent_type": "execute_pytest",
            "path_scope": "no_path",
            "sandbox_state": "required",
            "evidence_state": "required",
        },
        reason="verifier_requires_sandbox",
    )
