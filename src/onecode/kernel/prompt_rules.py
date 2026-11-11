"""Compatibility import. Implementation lives in onecode.experimental.prompt_rules."""

from onecode.experimental.prompt_rules import (
    PromptRule,
    classify_prompt,
    _host_execution,
    decide_prompt,
    _halt_rule,
    _deny_rule,
    _pytest_rule,
    LEGACY_DANGEROUS_MARKERS,
    HOSTS_MARKERS,
    VAGUE_MARKERS,
    CURL_SHELL_MARKERS,
    HOST_SHELL_MARKERS,
    HOST_OUTSIDE_MARKERS,
    HOST_CLEANUP_MARKERS,
)

__all__ = ['PromptRule', 'classify_prompt', '_host_execution', 'decide_prompt', '_halt_rule', '_deny_rule', '_pytest_rule', 'LEGACY_DANGEROUS_MARKERS', 'HOSTS_MARKERS', 'VAGUE_MARKERS', 'CURL_SHELL_MARKERS', 'HOST_SHELL_MARKERS', 'HOST_OUTSIDE_MARKERS', 'HOST_CLEANUP_MARKERS']
