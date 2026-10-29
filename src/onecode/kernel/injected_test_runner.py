"""Injected test runner and result parser for external benchmark exams.

Provides robust, multi-strategy parsing for pytest output, JUnit XML, and
command resolution across diverse task repositories (Django, repo_understanding,
and standard Python pytest tasks).
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11 fallback
    tomllib = None  # type: ignore[assignment]


@dataclass(frozen=True)
class InjectedSummary:
    passed: int
    failed: int
    errors: int
    skipped: int
    total: int
    pass_rate: float
    raw_summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_SUMMARY_LINE_PATTERN = re.compile(
    r"=+\s*(.*?)\s+in\s+[\d.]+(?:s|ms)?\s*=+",
    re.IGNORECASE,
)
_PASSED_TOKEN = re.compile(r"(\d+)\s+passed\b", re.IGNORECASE)
_FAILED_TOKEN = re.compile(r"(\d+)\s+failed\b", re.IGNORECASE)
_ERRORS_TOKEN = re.compile(r"(\d+)\s+error(?:s)?\b", re.IGNORECASE)
_SKIPPED_TOKEN = re.compile(r"(\d+)\s+skipped\b", re.IGNORECASE)

_LINE_PASSED = re.compile(r"^(?:PASSED\b|.*?\s+PASSED$)", re.MULTILINE)
_LINE_FAILED = re.compile(r"^(?:FAILED\b|.*?\s+FAILED$)", re.MULTILINE)
_LINE_ERROR = re.compile(r"^(?:ERROR\b|.*?\s+ERROR$)", re.MULTILINE)
_LINE_SKIPPED = re.compile(r"^(?:SKIPPED\b|.*?\s+SKIPPED$)", re.MULTILINE)


def parse_pytest_summary(output: str) -> InjectedSummary:
    """Parse pytest console output into a robust InjectedSummary.
    
    Supports:
    - Standard summary banners (= 1 failed, 2 passed in 0.12s =)
    - Any ordering of tokens (failed before passed, warnings, errors)
    - Fallback to line-by-line test outcome scanning when summary banner is omitted.
    """
    if not isinstance(output, str):
        return InjectedSummary(0, 0, 0, 0, 0, 0.0, "")

    matches = _SUMMARY_LINE_PATTERN.findall(output)
    if matches:
        candidate_line = matches[-1]
        passed_m = _PASSED_TOKEN.search(candidate_line)
        failed_m = _FAILED_TOKEN.search(candidate_line)
        errors_m = _ERRORS_TOKEN.search(candidate_line)
        skipped_m = _SKIPPED_TOKEN.search(candidate_line)

        passed = int(passed_m.group(1)) if passed_m else 0
        failed = int(failed_m.group(1)) if failed_m else 0
        errors = int(errors_m.group(1)) if errors_m else 0
        skipped = int(skipped_m.group(1)) if skipped_m else 0
        total = passed + failed + errors
        rate = round(passed / total, 3) if total > 0 else 0.0
        return InjectedSummary(
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            total=total,
            pass_rate=rate,
            raw_summary=candidate_line.strip(),
        )

    # Strategy 2: Search for individual tokens in the entire output tail
    tail_text = "\n".join(output.strip().splitlines()[-20:])
    passed_m = _PASSED_TOKEN.search(tail_text)
    failed_m = _FAILED_TOKEN.search(tail_text)
    errors_m = _ERRORS_TOKEN.search(tail_text)
    skipped_m = _SKIPPED_TOKEN.search(tail_text)

    if passed_m or failed_m or errors_m or skipped_m:
        passed = int(passed_m.group(1)) if passed_m else 0
        failed = int(failed_m.group(1)) if failed_m else 0
        errors = int(errors_m.group(1)) if errors_m else 0
        skipped = int(skipped_m.group(1)) if skipped_m else 0
        total = passed + failed + errors
        rate = round(passed / total, 3) if total > 0 else 0.0
        return InjectedSummary(
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            total=total,
            pass_rate=rate,
            raw_summary="tail-tokens",
        )

    # Strategy 3: Fallback line-by-line counting
    passed = len(_LINE_PASSED.findall(output))
    failed = len(_LINE_FAILED.findall(output))
    errors = len(_LINE_ERROR.findall(output))
    skipped = len(_LINE_SKIPPED.findall(output))
    total = passed + failed + errors
    rate = round(passed / total, 3) if total > 0 else 0.0
    return InjectedSummary(
        passed=passed,
        failed=failed,
        errors=errors,
        skipped=skipped,
        total=total,
        pass_rate=rate,
        raw_summary="line-events" if total > 0 else "none",
    )


def parse_junit_xml(xml_content: str) -> InjectedSummary:
    """Parse a JUnit XML report into an InjectedSummary."""
    if not isinstance(xml_content, str) or not xml_content.strip():
        return InjectedSummary(0, 0, 0, 0, 0, 0.0, "")

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return InjectedSummary(0, 0, 0, 0, 0, 0.0, "parse_error")

    total_tests = 0
    failures = 0
    errors = 0
    skipped = 0

    if root.tag == "testsuite":
        suites = [root]
    elif root.tag == "testsuites":
        suites = list(root.findall("testsuite"))
    else:
        suites = root.findall(".//testsuite")

    if suites:
        for s in suites:
            total_tests += int(s.attrib.get("tests", 0))
            failures += int(s.attrib.get("failures", 0))
            errors += int(s.attrib.get("errors", 0))
            skipped += int(s.attrib.get("skipped", 0))
    else:
        # Fallback to direct testcases
        cases = root.findall(".//testcase")
        total_tests = len(cases)
        for c in cases:
            if c.find("failure") is not None:
                failures += 1
            if c.find("error") is not None:
                errors += 1
            if c.find("skipped") is not None:
                skipped += 1

    passed = max(0, total_tests - failures - errors - skipped)
    eval_total = passed + failures + errors
    rate = round(passed / eval_total, 3) if eval_total > 0 else 0.0
    return InjectedSummary(
        passed=passed,
        failed=failures,
        errors=errors,
        skipped=skipped,
        total=eval_total,
        pass_rate=rate,
        raw_summary=f"junit-xml(tests={total_tests}, failures={failures}, errors={errors})",
    )


def resolve_task_test_command(
    task_id: str,
    task_dir: Path | None,
    workspace: Path,
    injected_test_path: Path | None = None,
) -> list[str]:
    """Resolve the appropriate test execution command for a given task.
    
    Supports:
    - Custom verification scripts defined in verifier.toml
    - Django projects with tests/runtests.py
    - Safe pytest command with conflict isolation flags
    """
    # 1. Inspect verifier.toml if available
    if task_dir is not None and (task_dir / "verifier.toml").is_file():
        toml_path = task_dir / "verifier.toml"
        command = _extract_command_from_verifier_toml(toml_path)
        if command:
            return command

    # 2. Django native test runner
    if (workspace / "tests" / "runtests.py").is_file() or "django" in task_id.lower():
        test_arg = str(injected_test_path) if injected_test_path else "tests"
        return [sys.executable, "tests/runtests.py", test_arg]

    # 3. Default to pytest with isolation flags
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "no:cacheprovider",
        "-o",
        "addopts=",
    ]
    if injected_test_path is not None:
        cmd.append(str(injected_test_path))
    return cmd


def _extract_command_from_verifier_toml(toml_path: Path) -> list[str] | None:
    try:
        content = toml_path.read_text(encoding="utf-8")
    except OSError:
        return None

    if tomllib is not None:
        try:
            data = tomllib.loads(content)
            # Look for command in [test] or root
            if isinstance(data.get("test"), dict) and "command" in data["test"]:
                val = data["test"]["command"]
                if isinstance(val, list):
                    return [str(v) for v in val]
                if isinstance(val, str):
                    import shlex

                    return shlex.split(val)
            if "command" in data:
                val = data["command"]
                if isinstance(val, list):
                    return [str(v) for v in val]
                if isinstance(val, str):
                    import shlex

                    return shlex.split(val)
        except Exception:
            pass

    # Simple regex fallback for command = "..."
    match = re.search(r'command\s*=\s*["\']([^"\']+)["\']', content)
    if match:
        import shlex

        return shlex.split(match.group(1))
    return None


def classify_injected_test_failure(
    stdout: str,
    stderr: str,
    exit_code: int,
) -> dict[str, str]:
    """Diagnose the root cause of a test failure or collection issue."""
    combined = (stdout + "\n" + stderr).strip()

    # Missing dependencies
    dep_match = re.search(r"ModuleNotFoundError:\s+No module named\s+['\"]([^'\"]+)['\"]", combined)
    if dep_match:
        return {
            "category": "missing_dependency",
            "detail": f"Missing module: {dep_match.group(1)}",
        }

    # Pytest plugin or hook incompatibility
    if "PluginValidationError" in combined or "pytest_plugins" in combined:
        return {
            "category": "plugin_incompatibility",
            "detail": "Pytest plugin incompatibility with Python 3.12 or current pytest version",
        }

    # Django environment required
    if "DJANGO_SETTINGS_MODULE" in combined or "Requested setting" in combined:
        return {
            "category": "django_environment_required",
            "detail": "Django settings not configured; requires tests/runtests.py runner",
        }

    # Internal pytest error or collection error
    if "INTERNALERROR>" in combined or exit_code in (3, 4):
        return {
            "category": "collection_error",
            "detail": "Pytest internal collection error",
        }

    # Pure assertion failure
    if "FAILED" in combined or "AssertionError" in combined or exit_code == 1:
        return {
            "category": "assertion_failure",
            "detail": "Test executed and assertion failed",
        }

    return {
        "category": "unknown_failure",
        "detail": f"Process exited with code {exit_code}",
    }
