from __future__ import annotations

import json
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

from .audit import append_audit_record, build_evidence_record


SKIP_DIRS = {
    "__pycache__",
    ".git",
    ".mypy_cache",
    ".oneword",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".venv-gateway",
    "build",
    "dist",
    "docs",
    "node_modules",
    "site-packages",
    "tests",
}
DEFAULT_IGNORE_PATHS = (
    "README.md",
    "agent_skill_dictionary/guard_policy.json",
    "agent_skill_dictionary/guard_executor.py",
    "agent_skill_dictionary/macro_chain.py",
    "agent_skill_dictionary/minimal_gateway_core.py",
    "agent_skill_dictionary/one_word_agent.py",
    "agent_skill_dictionary/tool_guard.py",
    "agent_skill_dictionary/trigram_contract.py",
    "docs/**",
    "scripts/smoke_test.py",
    "tests/**",
)
TEXT_SUFFIXES = {
    ".bash",
    ".cfg",
    ".env",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
    ".zsh",
}
TEXT_FILENAMES = {".env"}

DANGEROUS_RULES: tuple[dict[str, Any], ...] = (
    {"id": "dangerous-rm-rf", "name": "rm -rf", "pattern": r"\brm\s+-rf\b", "severity": "high", "block": True},
    {
        "id": "curl-pipe-shell",
        "name": "curl pipe shell",
        "pattern": r"\bcurl\b[^\n|]*\|\s*(?:ba)?sh\b",
        "severity": "high",
        "block": True,
    },
    {
        "id": "wget-pipe-shell",
        "name": "wget pipe shell",
        "pattern": r"\bwget\b[^\n|]*\|\s*(?:ba)?sh\b",
        "severity": "high",
        "block": True,
    },
    {
        "id": "prompt-injection",
        "name": "prompt injection",
        "pattern": r"ignore\s+(?:all\s+)?previous\s+instructions",
        "severity": "high",
        "block": True,
        "ignore_case": True,
    },
    {
        "id": "credential-exfiltration",
        "name": "credential exfiltration",
        "pattern": r"\b(?:OPENAI_API_KEY|ANTHROPIC_API_KEY|AWS_SECRET_ACCESS_KEY)\s*=\s*['\"]?(?:sk-[A-Za-z0-9_\-]{8,}|ak-[A-Za-z0-9_\-]{8,}|[A-Za-z0-9_/\-+=]{16,})",
        "severity": "high",
        "block": True,
    },
    {
        "id": "path-traversal-sensitive-file",
        "name": "path traversal sensitive file",
        "pattern": r"(?:\.\./){1,}(?:etc/passwd|etc/shadow|\.ssh|\.codex|\.claude)|(?:etc/passwd|etc/shadow).*(?:自由模式|admin|管理员|debug|调试)",
        "severity": "high",
        "block": True,
        "ignore_case": True,
    },
)

RISK_RANK = {"low": 0, "medium": 1, "high": 2}
VALID_SEVERITIES = set(RISK_RANK)


@dataclass(frozen=True)
class GuardRule:
    rule_id: str
    name: str
    pattern: re.Pattern[str]
    severity: str
    block: bool


@dataclass(frozen=True)
class GuardPolicy:
    rules: tuple[GuardRule, ...]
    ignore_paths: tuple[str, ...]
    text_suffixes: frozenset[str]


@dataclass(frozen=True)
class PhysicalGuardExecutor:
    workspace_path: str | Path

    def run_security_compile(
        self,
        require_enforcement: bool = True,
        scanner_types: list[str] | tuple[str, ...] | None = None,
        timeout_seconds: int = 120,
        audit_log_path: str | Path | None = None,
        policy_path: str | Path | None = None,
    ) -> dict[str, Any]:
        return guard_workspace(
            self.workspace_path,
            audit_log_path=audit_log_path,
            policy_path=policy_path,
            enable_external_scanners=True,
            require_external_scanner=require_enforcement,
            scanner_types=scanner_types,
            timeout_seconds=timeout_seconds,
        )


def guard_workspace(
    workspace_root: str | Path,
    audit_log_path: str | Path | None = None,
    max_files: int = 300,
    policy_path: str | Path | None = None,
    enable_external_scanners: bool = False,
    require_external_scanner: bool = False,
    scanner_types: list[str] | tuple[str, ...] | None = None,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    root = Path(workspace_root).resolve()
    policy = _load_policy(policy_path)
    findings = _scan_files(root, max_files, policy)
    external_scanners: list[str] = []
    requested_scanners = _normalize_scanner_types(scanner_types)
    if enable_external_scanners or require_external_scanner:
        external_findings, external_scanners = _run_external_scanners(
            root,
            timeout_seconds,
            require_external_scanner=require_external_scanner,
            scanner_types=requested_scanners,
        )
        findings.extend(external_findings)
    risk = _risk_level(findings)
    blocked = any(bool(finding.get("block")) for finding in findings)
    stdout = json.dumps(findings, ensure_ascii=False, sort_keys=True)
    evidence = build_evidence_record(
        command=f"guard_workspace {root}",
        exit_code=2 if blocked else 0,
        stdout=stdout,
        stderr="",
    )
    if audit_log_path is not None:
        evidence = append_audit_record(audit_log_path, evidence)
    return {
        "ok": not blocked,
        "risk": risk,
        "trigger": "risk_high" if blocked or risk == "high" else "guard_pass",
        "root": str(root),
        "finding_count": len(findings),
        "findings": findings,
        "external_scanners": external_scanners,
        "evidence": evidence,
    }


def guard_text(
    text: str,
    audit_log_path: str | Path | None = None,
    source: str = "input",
    policy_path: str | Path | None = None,
) -> dict[str, Any]:
    policy = _load_policy(policy_path)
    findings = _scan_text(text, source, policy)
    risk = _risk_level(findings)
    blocked = any(bool(finding.get("block")) for finding in findings)
    stdout = json.dumps(findings, ensure_ascii=False, sort_keys=True)
    evidence = build_evidence_record(
        command=f"guard_text {source}",
        exit_code=2 if blocked else 0,
        stdout=stdout,
        stderr="",
    )
    if audit_log_path is not None:
        evidence = append_audit_record(audit_log_path, evidence)
    return {
        "ok": not blocked,
        "risk": risk,
        "trigger": "risk_high" if blocked or risk == "high" else "guard_pass",
        "source": source,
        "finding_count": len(findings),
        "findings": findings,
        "evidence": evidence,
    }


def validate_guard_policy_file(policy_path: str | Path) -> list[str]:
    try:
        raw = json.loads(Path(policy_path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"policy must be valid JSON: {exc.msg}"]
    return validate_guard_policy(raw)


def validate_guard_policy(raw: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(raw, dict):
        return ["policy must be an object"]

    allowed_keys = {"version", "ignore_paths", "text_suffixes", "rules"}
    for key in raw:
        if key not in allowed_keys:
            errors.append(f"{key} is not allowed")

    version = raw.get("version")
    if version is not None and (not isinstance(version, int) or version < 1):
        errors.append("version must be an integer >= 1")

    errors.extend(_validate_string_list(raw, "ignore_paths", require_dot=False))
    errors.extend(_validate_string_list(raw, "text_suffixes", require_dot=True))

    rules = raw.get("rules")
    if not isinstance(rules, list) or not rules:
        errors.append("rules must be a non-empty list")
        return errors

    seen_rule_ids: set[str] = set()
    for index, rule in enumerate(rules):
        prefix = f"rules[{index}]"
        if not isinstance(rule, dict):
            errors.append(f"{prefix} must be an object")
            continue
        errors.extend(_validate_rule(prefix, rule, seen_rule_ids))
    return errors


def _load_policy(policy_path: str | Path | None) -> GuardPolicy:
    if policy_path is None:
        raw_rules = list(DANGEROUS_RULES)
        ignore_paths = list(DEFAULT_IGNORE_PATHS)
        suffixes = set(TEXT_SUFFIXES)
    else:
        raw = json.loads(Path(policy_path).read_text(encoding="utf-8"))
        raw_rules = list(raw.get("rules", []))
        ignore_paths = list(raw.get("ignore_paths", []))
        suffixes = set(raw.get("text_suffixes", TEXT_SUFFIXES))

    rules = tuple(_parse_rule(raw_rule) for raw_rule in raw_rules)
    return GuardPolicy(
        rules=rules,
        ignore_paths=tuple(ignore_paths),
        text_suffixes=frozenset(str(suffix).lower() for suffix in suffixes),
    )


def _validate_string_list(raw: dict[str, Any], key: str, require_dot: bool) -> list[str]:
    value = raw.get(key, [])
    errors: list[str] = []
    if not isinstance(value, list):
        return [f"{key} must be a list"]
    seen: set[str] = set()
    for index, item in enumerate(value):
        label = f"{key}[{index}]"
        if not isinstance(item, str) or not item:
            errors.append(f"{label} must be a non-empty string")
            continue
        if item in seen:
            errors.append(f"{label} duplicates {item}")
        seen.add(item)
        if require_dot and not item.startswith("."):
            errors.append(f"{label} must start with '.'")
    return errors


def _validate_rule(prefix: str, rule: dict[str, Any], seen_rule_ids: set[str]) -> list[str]:
    errors: list[str] = []
    allowed_keys = {"id", "name", "pattern", "severity", "block", "ignore_case"}
    for key in rule:
        if key not in allowed_keys:
            errors.append(f"{prefix}.{key} is not allowed")

    rule_id = rule.get("id")
    if not isinstance(rule_id, str) or not rule_id:
        errors.append(f"{prefix}.id must be a non-empty string")
    elif rule_id in seen_rule_ids:
        errors.append(f"{prefix}.id duplicates {rule_id}")
    else:
        seen_rule_ids.add(rule_id)

    name = rule.get("name")
    if name is not None and (not isinstance(name, str) or not name):
        errors.append(f"{prefix}.name must be a non-empty string")

    pattern = rule.get("pattern")
    if not isinstance(pattern, str) or not pattern:
        errors.append(f"{prefix}.pattern must be a non-empty string")
    else:
        flags = re.IGNORECASE if rule.get("ignore_case") is True else 0
        try:
            re.compile(pattern, flags)
        except re.error as exc:
            errors.append(f"{prefix}.pattern is invalid regex: {exc}")

    severity = rule.get("severity", "high")
    if not isinstance(severity, str) or severity not in VALID_SEVERITIES:
        errors.append(f"{prefix}.severity must be one of {sorted(VALID_SEVERITIES)}")

    block = rule.get("block", True)
    if not isinstance(block, bool):
        errors.append(f"{prefix}.block must be boolean")

    ignore_case = rule.get("ignore_case", False)
    if not isinstance(ignore_case, bool):
        errors.append(f"{prefix}.ignore_case must be boolean")
    return errors


def _parse_rule(raw_rule: dict[str, Any]) -> GuardRule:
    flags = re.IGNORECASE if raw_rule.get("ignore_case") else 0
    rule_id = str(raw_rule.get("id") or raw_rule.get("name") or "unnamed-rule")
    name = str(raw_rule.get("name") or rule_id)
    severity = str(raw_rule.get("severity") or "high").lower()
    if severity not in RISK_RANK:
        severity = "high"
    return GuardRule(
        rule_id=rule_id,
        name=name,
        pattern=re.compile(str(raw_rule["pattern"]), flags),
        severity=severity,
        block=bool(raw_rule.get("block", True)),
    )


def _scan_files(root: Path, max_files: int, policy: GuardPolicy) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    scanned = 0
    for path in sorted(root.rglob("*")):
        if scanned >= max_files:
            break
        relative_path = path.relative_to(root)
        if any(part in SKIP_DIRS for part in relative_path.parts):
            continue
        relative = relative_path.as_posix()
        if _is_ignored(relative, policy.ignore_paths):
            continue
        if not path.is_file() or (
            path.suffix.lower() not in policy.text_suffixes and path.name not in TEXT_FILENAMES
        ):
            continue
        scanned += 1
        findings.extend(_scan_file(root, path, policy))
    return findings


def _scan_file(root: Path, path: Path, policy: GuardPolicy) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []

    relative = path.relative_to(root).as_posix()
    findings: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule in policy.rules:
            if rule.pattern.search(line):
                findings.append(
                    {
                        "file": relative,
                        "line": line_number,
                        "rule_id": rule.rule_id,
                        "pattern": rule.name,
                        "severity": rule.severity,
                        "block": rule.block,
                        "snippet": line.strip()[:160],
                    }
                )
    return findings


def _scan_text(text: str, source: str, policy: GuardPolicy) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines() or [text], start=1):
        for rule in policy.rules:
            if rule.pattern.search(line):
                findings.append(
                    {
                        "source": source,
                        "line": line_number,
                        "rule_id": rule.rule_id,
                        "pattern": rule.name,
                        "severity": rule.severity,
                        "block": rule.block,
                        "snippet": line.strip()[:160],
                    }
                )
    return findings


def _is_ignored(relative: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch(relative, pattern) for pattern in patterns)


def _risk_level(findings: list[dict[str, Any]]) -> str:
    risk = "low"
    for finding in findings:
        severity = str(finding.get("severity", "high")).lower()
        if RISK_RANK.get(severity, 2) > RISK_RANK[risk]:
            risk = severity
    return risk


def _run_external_scanners(
    root: Path,
    timeout_seconds: int,
    require_external_scanner: bool = False,
    scanner_types: tuple[str, ...] = ("semgrep", "osv-scanner"),
) -> tuple[list[dict[str, Any]], list[str]]:
    findings: list[dict[str, Any]] = []
    scanners: list[str] = []
    if "semgrep" in scanner_types and shutil.which("semgrep"):
        scanners.append("semgrep")
        result = _run_scanner(["semgrep", "--json", "--config", "auto", "."], root, timeout_seconds)
        findings.extend(_parse_semgrep_findings(result.get("stdout", "")))
    elif "semgrep" in scanner_types and require_external_scanner:
        findings.append(_missing_scanner_finding("semgrep"))

    if "osv-scanner" in scanner_types and shutil.which("osv-scanner"):
        lockfiles = _lockfiles(root)
        if lockfiles:
            scanners.append("osv-scanner")
            command = [
                "osv-scanner",
                "--format",
                "json",
                *[str(path.relative_to(root)) for path in lockfiles],
            ]
            result = _run_scanner(command, root, timeout_seconds)
            findings.extend(_parse_osv_findings(result.get("stdout", "")))
        elif require_external_scanner:
            findings.append(_missing_scanner_finding("osv-scanner", reason="no_lockfile"))
    elif "osv-scanner" in scanner_types and require_external_scanner:
        findings.append(_missing_scanner_finding("osv-scanner"))
    return findings, scanners


def _normalize_scanner_types(scanner_types: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if not scanner_types:
        return ("semgrep", "osv-scanner")
    normalized: list[str] = []
    for item in scanner_types:
        value = str(item).strip()
        if value in {"semgrep", "osv-scanner"} and value not in normalized:
            normalized.append(value)
    return tuple(normalized or ("semgrep", "osv-scanner"))


def _missing_scanner_finding(scanner: str, reason: str = "binary_missing") -> dict[str, Any]:
    return {
        "scanner": scanner,
        "file": "",
        "rule_id": "guard-scanner-missing",
        "pattern": reason,
        "severity": "high",
        "block": True,
    }


def _run_scanner(command: list[str], root: Path, timeout_seconds: int) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _parse_semgrep_findings(stdout: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(stdout or "{}")
    except json.JSONDecodeError:
        return []
    findings: list[dict[str, Any]] = []
    for item in payload.get("results", []):
        if not isinstance(item, dict):
            continue
        extra = item.get("extra", {})
        if not isinstance(extra, dict):
            extra = {}
        findings.append(
            {
                "scanner": "semgrep",
                "file": str(item.get("path", "")),
                "rule_id": str(item.get("check_id", "semgrep")),
                "pattern": str(extra.get("message") or item.get("check_id", "semgrep")),
                "severity": "high",
                "block": True,
            }
        )
    return findings


def _parse_osv_findings(stdout: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(stdout or "{}")
    except json.JSONDecodeError:
        return []
    findings: list[dict[str, Any]] = []
    for result in payload.get("results", []):
        if not isinstance(result, dict):
            continue
        source = result.get("source", {})
        if not isinstance(source, dict):
            source = {}
        for package in result.get("packages", []):
            if not isinstance(package, dict):
                continue
            for vuln in package.get("vulnerabilities", []):
                if not isinstance(vuln, dict):
                    continue
                findings.append(
                    {
                        "scanner": "osv-scanner",
                        "file": str(source.get("path", "")),
                        "rule_id": str(vuln.get("id", "osv-vulnerability")),
                        "pattern": "dependency vulnerability",
                        "severity": "high",
                        "block": True,
                    }
                )
    return findings


def _lockfiles(root: Path) -> list[Path]:
    names = {
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "poetry.lock",
        "Pipfile.lock",
        "requirements.txt",
        "go.sum",
        "Cargo.lock",
    }
    return [path for path in root.rglob("*") if path.is_file() and path.name in names]
