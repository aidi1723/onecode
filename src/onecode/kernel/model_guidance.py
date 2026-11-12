"""Prompt guidance and task-contract text for model runs."""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.preset_tests import is_preset_test_path
from onecode.kernel.symbolic_telemetry import (
    call_symbolic_profile,
    compute_systemic_intervention,
    compute_workspace_envelope,
    resolve_state_governance_mode,
    symbolic_telemetry_enabled,
    trace_causal_origin_file,
)


def _label_tag(base: str, symbolic_tag: str, symbolic: bool) -> str:
    return f"{base} ({symbolic_tag})" if symbolic else base

_RELATIVE_PYTHON = r"((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.py)"
_NAMED_PYTHON_FILE = re.compile(rf"(?<![\w./-]){_RELATIVE_PYTHON}\b")
_OUTPUT_DATA_FILE = re.compile(
    r"(?<![\w./-])([A-Za-z0-9_.-]+\.(?:csv|tsv|parquet|feather|jsonl))\b",
    re.IGNORECASE,
)
_DO_NOT_FILE = re.compile(
    rf"(?:do not|don't|never)\s+(?:modify|change|patch|edit|touch|rewrite)\s+{_RELATIVE_PYTHON}"
    rf"|((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.py)\s*(?:不要改|别改|不要动|别动|严禁修改|不可修改|无需修改|不修改|不能修改|禁止修改)"
    rf"|(?:不要改|别改|不修改|不能修改|禁止修改|不要修改|严禁修改)\s*((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.py)",
    re.IGNORECASE,
)
_ONLY_FILE = re.compile(rf"\bonly\s+{_RELATIVE_PYTHON}", re.IGNORECASE)
_NEW_TESTS = re.compile(
    r"只补测试|只写测试|仅测试|只添加测试|只新增测试|只补\s*tests|只在\s*tests"
    r"|主逻辑先别动|先别动主逻辑|补一组回归测试"
    r"|tests only|only write tests|only add tests|modify tests only|test task",
    re.IGNORECASE,
)
_CALL_BEFORE_LEAK = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\(([^)\n]{1,80})\)")
_INPUT_FIELDS = ("args", "inputs", "arguments")
_REPAIR_SKIP = frozenset(
    {
        ".git",
        ".github",
        ".onecode",
        "tests",
        "venv",
        ".venv",
        "__pycache__",
        "node_modules",
        "docs",
        "dist",
        "build",
    }
)

def _accepted_relative_python(path: str) -> str | None:
    relative = path.replace("\\", "/")
    parts = relative.split("/")
    if any(part in {"", ".", ".."} or part.startswith(".") for part in parts):
        return None
    return relative


def named_python_files(task: str) -> list[str]:
    found: list[str] = []
    for match in _NAMED_PYTHON_FILE.findall(task):
        cleaned = _accepted_relative_python(match)
        if cleaned is not None and cleaned not in found:
            found.append(cleaned)
    return found


def asks_for_new_tests(task: str) -> bool:
    """True when the task asks for new tests and the implementation should stay put."""
    return _NEW_TESTS.search(task) is not None


def protected_python_files(task: str) -> list[str]:
    found: list[str] = []
    for match in _DO_NOT_FILE.findall(task):
        items = [match] if isinstance(match, str) else [m for m in match if m]
        for item in items:
            cleaned = _accepted_relative_python(item)
            if cleaned is not None and cleaned not in found:
                found.append(cleaned)
    only = [cleaned for match in _ONLY_FILE.findall(task) if (cleaned := _accepted_relative_python(match))]
    if only:
        allowed = set(only)
        for path in named_python_files(task):
            if path not in allowed and path not in found:
                found.append(path)
    return found


def required_python_files(task: str) -> list[str]:
    protected = set(protected_python_files(task))
    return [path for path in named_python_files(task) if path not in protected]


def file_write_slots(task: str, max_repair_attempts: int) -> int:
    if max_repair_attempts <= 0:
        return 0
    return max(max_repair_attempts, len(required_python_files(task)))


def missing_required_files(task: str, workspace: Path) -> list[str]:
    return [path for path in required_python_files(task) if not (workspace / path).is_file()]


def _required_files_landed(task: str, written: list[str]) -> bool:
    required = required_python_files(task)
    if not required:
        return False
    done = {path.replace("\\", "/") for path in written}
    return all(path in done for path in required)


def narrow_plan_prompt(task: str, failure: dict[str, Any], written: list[str] | None = None) -> str:
    detail = failure.get("detail") or failure.get("failure_kind") or "plan did not fit"
    already = ", ".join(written) if written else "none"
    protected = ", ".join(protected_python_files(task))
    kept = f" Do not write these protected paths: {protected}." if protected else ""
    contract_note = data_contract_guidance(task)
    return (
        "The previous plan did not fit in one response.\n"
        f"Failure: {detail}\n"
        f"Original task: {task}\n"
        f"Already written: {already}\n"
        "Return JSON for exactly one new Python file. "
        "Do not rewrite a file that is already written. "
        "If the task is already complete, return no_action with a concrete reason and no assets. "
        "The asset content must be complete and non-empty. "
        "Do not return patches. "
        + (
            "Use unittest, not pytest. No relative imports. "
            if any(is_preset_test_path(path) for path in required_python_files(task) if path not in set(written or []))
            else "Do not import unittest or pytest. "
        )
        + "Do not include execution_plan or run_command. "
        "Do not install packages or use the network."
        + contract_note
        + kept
    )


def data_contract_guidance(task: str, *, symbolic: bool | None = None) -> str:
    task_lower = task.lower()
    use_symbolic = symbolic_telemetry_enabled() if symbolic is None else symbolic
    rules: list[str] = []

    def match(phrase_pat: str) -> bool:
        return bool(re.search(rf"(?:^|[\s\-_])(?:{phrase_pat})(?:$|[\s\-_])", task_lower))

    if match(r"invoices?|billing|credit[_\s-]+notes?") or any(k in task for k in ("账单", "发票")):
        hdr = _label_tag(
            "For invoice line and tabular exports",
            "Tianfu-Tianxiang Stamp & Command Contract 府相朝垣·印令昭明",
            use_symbolic,
        )
        rules.append(
            f"{hdr}: "
            "write pure UTF-8 encoding (never use utf-8-sig or write UTF-8 BOM bytes); "
            "properly quote string values with commas so they round trip in single CSV cells; "
            "ensure numeric calculations (quantity * unit price, taxes, credits, and line totals) are mathematically consistent; "
            "format credits and negative adjustments distinctly as required; "
            "sort rows deterministically."
        )
    if match(r"text[_\s-]+hashing|feature[_\s-]+hashing|hashing[_\s-]+vectorizer|hash[_\s-]+trick|deterministic[_\s-]+hash|hashlib") or "特征哈希" in task:
        rules.append(
            "For text or feature hashing: use hashlib (e.g. hashlib.md5 or hashlib.sha256) "
            "for deterministic hashing invariant across Python hash seeds, never built-in hash(); "
            "normalize text tokens deterministically; "
            "read input tabular data using standard csv modules (not line.split(',') since text fields may contain commas); "
            "output sparse features sorted by numeric bucket; "
            "handle empty or filtered-out inputs gracefully without unhandled exceptions."
        )
    if match(r"label[_\s-]+conflicts?|conflicting[_\s-]+labels?|entity[_\s-]+resolution") or "标签冲突" in task:
        rules.append(
            "For label conflicts (Zhen-Kan Cleansing & Priority Contract 震坎涤瑕·权重定争): "
            "adhere to declared source priorities when resolving entity label conflicts; "
            "deduplicate exact identical records cleanly without duplicate counting; "
            "separate valid consensus records from ambiguous or conflicting records into designated clean and rejected outputs; "
            "select the newest event timestamp when breaking ties within winning priority."
        )
    if match(r"winsoriz\w*|outliers?[_\s-]+clipping|outlier[_\s-]+truncation|outlier[_\s-]+winsorize") or any(k in task for k in ("异常值截断", "缩尾")):
        rules.append(
            "For outlier winsorization (Tianliang-Tiantong Protective Imputation 荫福化解·补全与边界): "
            "clip values strictly at declared lower and upper bounds; "
            "fill missing (null, NaN, empty string) and unparseable values with declared default column fills; "
            "leave normal valid rows completely unchanged; "
            "in tabular output, format whole numbers without trailing '.0' (e.g. '1' not '1.0'); "
            "generate accurate summary statistics of filled and clipped counts per numeric column."
        )
    if match(r"schema[_\s-]+drift|drift[_\s-]+detection") or any(k in task for k in ("模式漂移", "架构漂移")):
        hdr = _label_tag(
            "For schema drift audit",
            "Tianxiang Yintie · Audit Schema Contract 天相印绶·规范审计",
            use_symbolic,
        )
        rules.append(
            f"{hdr}: "
            "validate each record systematically against declared schema definitions; "
            "check missing required fields, type mismatches, enum violations, and unexpected properties in a single atomic pass; "
            "treat valid integer inputs as acceptable for numeric float constraints; "
            "ensure nullable fields allowing null/None are not falsely flagged; "
            "preserve stable input row ordering in output."
        )
    if match(r"time[_\s-]+leakage|temporal[_\s-]+leakage|feature[_\s-]+leakage") or any(k in task for k in ("时间泄漏", "时序穿越")):
        hdr = _label_tag(
            "For time leakage audit",
            "Tianliang Canopy Audit 荫星照微·截止容限",
            use_symbolic,
        )
        rules.append(
            f"{hdr}: "
            "verify that feature timestamps do not exceed configured cutoff times plus declared tolerance windows; "
            "partition clean training samples from time-leaking samples into designated clean and rejected outputs; "
            "preserve input ordering for clean records and record detailed leakage diagnostics."
        )
    if match(r"support[_\s-]+sla|service[_\s-]+level[_\s-]+agreement") or (match(r"sla") and match(r"tickets?|support|customer[_\s-]+service")) or "工单履约" in task:
        hdr = _label_tag(
            "For support SLA metrics",
            "Tianxiang Inspection 督考巡历·工单履约",
            use_symbolic,
        )
        rules.append(
            f"{hdr}: "
            "compute response and resolution times accurately against declared service level agreements (SLA thresholds); "
            "identify SLA misses consistently for overdue or missing responses; "
            "aggregate team-level performance metrics and round numerical averages appropriately."
        )
    if match(r"cross[_\s-]categorical|categorical[_\s-]+interactions?|feature[_\s-]+cross(?:es)?") or "交叉特征" in task:
        rules.append(
            "For cross categorical features: normalize categorical values by trimming and lowercasing; "
            "generate interaction cross-features deterministically; "
            "map categorical values to integer vocab IDs rather than copying raw strings."
        )
    if match(r"train[_\s-]serv(?:e|ing)[_\s-]+parity|training[_\s-]+serving[_\s-]+skew") or any(k in task for k in ("训练推断一致性", "训练服务一致性")):
        rules.append(
            "For train-serve parity: impute missing values consistently with defaults, "
            "compute normalization accurately across training and serving distributions, and respect inclusive boundary comparisons."
        )
    if match(r"rolling[_\s-]+window|sliding[_\s-]+window|window[_\s-]+aggregat\w*") or any(k in task for k in ("滑动窗口", "时间窗口聚合")):
        rules.append(
            "For window aggregates: compute event recency deltas relative to the anchor timestamp, "
            "handle zero-event entities cleanly with appropriate null or zero defaults, and preserve anchor reference time."
        )
    if match(r"expected[_\s-]+calibration[_\s-]+error|ece|calibration[_\s-]+bins?") or (match(r"calibrat\w*") and match(r"bins?|reliability[_\s-]+diagram")) or "校准桶" in task:
        rules.append(
            "For calibration bins and ECE: partition confidence scores into calibration bins, "
            "compute accuracy and calibration gaps per bin, handle empty bins cleanly with zero counts, "
            "and aggregate weighted Expected Calibration Error (ECE) across all bins."
        )
    if match(r"(?:a[_\s-]+)?crash[_\s-]+in[_\s-]+local|unbound[_\s-]+local[_\s-]+variable|unboundlocalerror") or "未绑定局部变量" in task:
        rules.append(
            "For local crash and bug fixes: defensively guard against None, missing keys, and empty collections; "
            "ensure local variables are initialized across all conditional branches, preserve original exception types, "
            "and preserve existing package import structures and relative imports within packages to avoid circular import issues."
        )
    if match(r"envless[_\s-]+file[_\s-]+load|environment[_\s-]+fallback|zero[_\s-]+env[_\s-]+load") or "无环境" in task:
        rules.append(
            "For environment-less file loading: support loading configuration without environment prefix constraints, "
            "safely resolve relative and absolute paths with default search fallbacks when env vars are unset, "
            "and preserve default environment loading behaviors."
        )
    if match(r"(?:validation[_\s-]+to[_\s-]+)?eliminate[_\s-]+uriref|uriref[_\s-]+validation|uri[_\s-]+reference"):
        rules.append(
            "For URI reference elimination and component validation: deeply validate URI components, "
            "and raise designated domain exception classes when components fail validation."
        )
    if match(r"filtered[_\s-]+relation|relation[_\s-]+queryset|queryset[_\s-]+filters?|filtered[_\s-]+relation[_\s-]+queryset[_\s-]+arg"):
        rules.append(
            "For filtered relations and querysets: preserve custom query arguments and kwargs without clobbering existing query filters or relation joins."
        )

    # General tabular contract rules apply ONLY when the task is working with datasets/tabular contracts
    is_tabular_contract = bool(re.search(r"\b(dataset|dataframe|tabular|csv|table|records?|schema|jsonl)\b", task_lower) or any(c in task for c in ("数据集", "表格", "数据表", "字段", "数据清洗")))
    if is_tabular_contract:
        if match(r"sort|ordering|sorted") and not any("sort" in r for r in rules):
            rules.append("Sort outputs deterministically by specified keys; preserve required row and column ordering.")
        if match(r"null|nan|missing|empty|impute") and not any("missing" in r for r in rules):
            rules.append("Explicitly handle missing values and empty groups/bins (e.g. fill with 0 or default values rather than omitting).")
        if match(r"threshold|bound|cutoff|limits?|inclusive") and not any("threshold" in r for r in rules):
            rules.append("Respect boundary conditions carefully (check >= vs >, <= vs <, inclusive vs exclusive).")
        if match(r"schema|column|field|columns?|fields?") and not any("field" in r for r in rules):
            rules.append("Match exact field names and output schema without extra or omitted columns.")
        if match(r"summary|total|aggregate|aggregates?") and not any("total" in r for r in rules):
            rules.append("Include any requested summary, total, or aggregate rows.")

    return (" " + " ".join(rules)) if rules else ""


def initial_asset_prompt(task: str, target: str) -> str:
    protected = ", ".join(protected_python_files(task))
    kept = f" Do not write these protected paths: {protected}." if protected else ""
    data_files = _OUTPUT_DATA_FILE.findall(task)
    artifact_note = (
        f" If the task requires producing an output data file ({', '.join(data_files)}), include it as an additional asset in assets or ensure it is generated."
        if data_files
        else ""
    )
    contract_note = data_contract_guidance(task)
    return (
        "Write exactly one complete Python file as a JSON asset.\n"
        f"Target: {target}\n"
        f"Original task: {task}\n"
        "The asset content must be the complete non-empty file. "
        "Do not return patches, execution_plan, or run_command. "
        "Do not install packages or use the network. "
        "Depend only on the standard library and files already in the workspace. "
        + (
            "Use unittest, not pytest. No relative imports."
            if is_preset_test_path(target)
            else "Do not import unittest or pytest."
        )
        + contract_note
        + artifact_note
        + kept
    )


_SAFE_FAILURE_LABEL = re.compile(
    r"^(KeyError|TypeError|AttributeError|IndexError|ValueError|FileNotFoundError)"
    r"(?::\s*'([A-Za-z_][A-Za-z0-9_]*)')?$"
)
_EXCEPTION_CLASS = re.compile(
    r"^(AssertionError|KeyError|TypeError|AttributeError|IndexError|ValueError|FileNotFoundError|NameError|ZeroDivisionError)\b"
)


def _render_inputs(value: object, depth: int = 0) -> str:
    if depth > 2:
        return ""
    if value is None or isinstance(value, bool) or isinstance(value, int):
        return repr(value)
    if isinstance(value, float):
        return repr(value) if abs(value) <= 1_000_000 else ""
    if isinstance(value, str):
        text = value.strip()
        if not text or len(text) > 80 or any(token in text.lower() for token in ("expected", "secret_", "assert")):
            return ""
        return text
    if isinstance(value, (list, tuple)):
        parts = [item for item in (_render_inputs(child, depth + 1) for child in value[:6]) if item]
        return ", ".join(parts)
    if isinstance(value, dict):
        fields: list[str] = []
        for key, child in list(value.items())[:6]:
            rendered = _render_inputs(child, depth + 1)
            if rendered:
                fields.append(f"{key}={rendered}")
        return ", ".join(fields)
    return ""


def _inputs_before_expected_text(detail: object) -> str:
    text = str(detail or "")
    lowered = text.lower()
    cut = len(text)
    for token in ("expected", "!=", "secret_"):
        index = lowered.find(token)
        if index >= 0:
            cut = min(cut, index)
    match = _CALL_BEFORE_LEAK.search(text[:cut])
    if match is None:
        return ""
    arguments = match.group(2).strip()
    if not arguments or "secret_" in arguments.lower() or "expected" in arguments.lower():
        return ""
    return f"{match.group(1)}({arguments})"


def _safe_failure_inputs(item: dict) -> str:
    for key in _INPUT_FIELDS:
        if key not in item:
            continue
        rendered = _render_inputs(item.get(key))
        if rendered and "secret_" not in rendered.lower() and "expected" not in rendered.lower():
            return rendered
    return _inputs_before_expected_text(item.get("detail"))


def _safe_failure_label(detail: object) -> str:
    text = str(detail or "").strip()
    if not text:
        return ""
    leaked = "expected" in text.lower() or "SECRET_" in text
    match = _SAFE_FAILURE_LABEL.match(text)
    if match is not None and not leaked:
        if match.group(2):
            return f"{match.group(1)}: '{match.group(2)}'"
        return match.group(1)
    named = _EXCEPTION_CLASS.match(text)
    if named is not None:
        return named.group(1)
    return ""


def sanitize_host_failure_summary(detail: dict) -> str:
    """Name the failed host checks without copying expected-answer text into the repair prompt."""
    lines: list[str] = []
    passed = detail.get("tests_passed")
    total = detail.get("tests_total")
    if isinstance(passed, int) and not isinstance(passed, bool) and isinstance(total, int) and not isinstance(total, bool):
        lines.append(f"Verifier report: {passed}/{total} tests passed.")
    tests = detail.get("tests")
    failed_names: list[str] = []
    if isinstance(tests, list):
        for item in tests:
            if isinstance(item, dict) and item.get("passed") is False:
                name = str(item.get("name") or "unknown").strip() or "unknown"
                label = _safe_failure_label(item.get("detail"))
                inputs = _safe_failure_inputs(item)
                rendered = f"{name} ({label})" if label else name
                if inputs:
                    rendered = f"{rendered} args {inputs}"
                if rendered not in failed_names:
                    failed_names.append(rendered)
    if failed_names:
        lines.append("Failed tests:")
        lines.extend(f"- [FAIL] {name}" for name in failed_names)
    return "\n".join(lines)


def format_verifier_diagnostics(stdout: str, stderr: str) -> str:
    """Parse verifier stdout/stderr into actionable diagnostics for repair prompts."""
    if stdout:
        decoder = json.JSONDecoder()
        for match in re.finditer(r'\{\s*"(?:overall|tests)"', stdout):
            idx = match.start()
            try:
                candidate, _ = decoder.raw_decode(stdout[idx:])
                if isinstance(candidate, dict) and "tests" in candidate and isinstance(candidate["tests"], list):
                    passed_cnt = candidate.get("tests_passed", 0)
                    total_cnt = candidate.get("tests_total", len(candidate["tests"]))
                    lines = [f"Verifier report: {passed_cnt}/{total_cnt} tests passed."]
                    failed = [t for t in candidate["tests"] if isinstance(t, dict) and not t.get("passed")]
                    passed = [t for t in candidate["tests"] if isinstance(t, dict) and t.get("passed")]
                    if failed:
                        lines.append("Failed tests:")
                        for item in failed:
                            name = item.get("name", "unknown")
                            detail = item.get("detail")
                            lines.append(f"- [FAIL] {name}" + (f": {detail}" if detail else ""))
                    if passed:
                        lines.append("Passed tests:")
                        for item in passed:
                            lines.append(f"- [PASS] {item.get('name', 'unknown')}")
                    return "\n".join(lines)
            except json.JSONDecodeError:
                pass

    diagnostics: list[str] = []
    if stderr:
        err_lines = [line.strip() for line in stderr.splitlines() if line.strip()]
        assertion_lines = [l for l in err_lines if any(k in l for k in ("AssertionError", "Error:", "FAILED"))]
        if assertion_lines:
            diagnostics.append("Stderr errors:\n" + "\n".join(f"- {l}" for l in assertion_lines[-5:]))
        else:
            diagnostics.append(f"Stderr:\n{stderr[-800:]}")
    if stdout:
        out_lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        failing_lines = [l for l in out_lines if any(k in l for k in ("FAIL", "ERROR", "AssertionError"))]
        if failing_lines:
            diagnostics.append("Stdout errors:\n" + "\n".join(f"- {l}" for l in failing_lines[-10:]))
        else:
            diagnostics.append(f"Stdout:\n{stdout[-800:]}")
    return "\n".join(diagnostics)


def _extract_targeted_assertions(error_parts: list[str], *, symbolic: bool = False) -> list[str]:
    alerts: list[str] = []
    matched_assertion = False
    target_hdr = _label_tag("- Precision assertion target", "水生木·精准断言", symbolic)
    for ep in error_parts:
        m = re.search(r"(AssertionError: [^\n]+)", ep)
        if m:
            alerts.append(
                f"{target_hdr}: {m.group(1).strip()}. Focus surgical edit directly on resolving this discrepancy; do not repeat previous values."
            )
            matched_assertion = True
            break

    failing_checks: list[str] = []
    for ep in error_parts:
        for match in re.finditer(r"-\s*\[FAIL\]\s*([^:\n]+)", ep):
            chk = match.group(1).strip()
            if chk and chk not in failing_checks:
                failing_checks.append(chk)
        for match in re.finditer(r'\"name\":\s*\"([^\"]+)\",\s*\"passed\":\s*false(?:,\s*\"detail\":\s*\"([^\"]*)\")?', ep):
            name = match.group(1).strip()
            detail = match.group(2).strip() if match.group(2) else ""
            desc = f"{name} ({detail})" if detail else name
            if desc and desc not in failing_checks:
                failing_checks.append(desc)

    if not matched_assertion and failing_checks:
        first = failing_checks[0]
        alerts.append(
            f"{target_hdr}: Failing test check '{first}'. Focus surgical edit directly on satisfying this test condition."
        )
        if any(term in first.lower() for term in ("blocked", "denied", "allowed", "approved", "reason", "status")):
            alerts.append(
                f"- Precision reason target: Failing check '{first}' evaluates a policy decision. "
                "Ensure the decision 'reason' and 'status' correspond precisely to the specific condition phrase in the check name (distinguishing qualifiers like recent activity thresholds, zero payment/charges, and seat availability)."
            )

    if len(failing_checks) > 1:
        items_str = ", ".join(f"'{c}'" for c in failing_checks[:8])
        array_hdr = _label_tag("- Precision assertion array", "三方四正·全量断言照会", symbolic)
        alerts.append(
            f"{array_hdr}: Multiple failing checks detected: [{items_str}]. Satisfy all test assertions simultaneously."
        )

    passing_checks: list[str] = []
    for ep in error_parts:
        for match in re.finditer(r'\"name\":\s*\"([^\"]+)\",\s*\"passed\":\s*true', ep):
            pname = match.group(1).strip()
            if pname and pname not in passing_checks:
                passing_checks.append(pname)
    if passing_checks:
        pass_str = ", ".join(f"'{c}'" for c in passing_checks[:6])
        base_hdr = _label_tag("- Preserved baseline tests", "三台八座·既得吉果不可毁", symbolic)
        suffix = " (吉处藏凶·防范冲破)" if symbolic else ""
        alerts.append(
            f"{base_hdr}: Previous run PASSED: [{pass_str}]. "
            f"Your patch MUST preserve all passing tests and strictly avoid regression{suffix}."
        )

    for ep in error_parts:
        m_exc = re.search(r"((?:KeyError|FileNotFoundError|UnicodeError|UnicodeDecodeError|ValueError|AttributeError|ZeroDivisionError|IndexError): [^\n]+)", ep)
        if m_exc:
            exc_hdr = _label_tag("- Hidden runtime anomaly", "铃星隐煞·天相印信昭明", symbolic)
            alerts.append(
                f"{exc_hdr}: {m_exc.group(1).strip()}. "
                "Check file existence, pure UTF-8 encoding (no BOM bytes), and exact key/header matching."
            )
            break

    for ep in error_parts:
        if any(token in ep.lower() for token in ("empty", "zerodivision", "keyerror", "iterable argument is empty")):
            bound_hdr = _label_tag("- Boundary opposition guard", "错卦互补·空集与极值防线", symbolic)
            alerts.append(
                f"{bound_hdr}: Defend against empty inputs/token lists, "
                "missing dictionary keys, and boundary conditions. Never call max()/min()/next() on empty collections; supply safe fallbacks."
            )
            break

    for fc in failing_checks:
        fc_low = fc.lower()
        if "credit" in fc_low or "line_total" in fc_low:
            acct_hdr = _label_tag("- Accounting adjustment rule", "府相朝垣·库印分明", symbolic)
            alerts.append(
                f"{acct_hdr}: For credit, discount, or deduction entries, "
                "ensure positive voucher amounts are recorded distinctly from negative net balance reductions, "
                "maintaining mathematical ledger consistency."
            )
            break
        if "score" in fc_low or "clipped" in fc_low or "format" in fc_low:
            fmt_hdr = _label_tag("- Canonical number formatting", "文昌化科·整型规范", symbolic)
            alerts.append(
                f"{fmt_hdr}: In CSV outputs, "
                "format whole numbers without trailing '.0' (e.g. write '1' not '1.0', '0' not '0.0')."
            )
            break
    return alerts


def _tuo_luo_stagnation_alert(turn_history: list[dict[str, Any]], *, symbolic: bool = False) -> list[str]:
    alerts: list[str] = []
    if len(turn_history) >= 2:
        last = turn_history[-1]
        if last.get("reason") in {"verifier_failed", "command_failed", "repair_plan_must_use_patches_only"}:
            hdr = _label_tag("- Stagnation warning", "陀罗暗滞·化权破滞", symbolic)
            alerts.append(
                f"{hdr}: Previous repair attempt did not resolve the failure. "
                "Pivot decisively: check README.md contract specifications, exact field and column naming, "
                "edge cases (empty collections, zero values), and adjust implementation strategy rather than minor tweaks."
            )
    return alerts


def _append_symbolic_diagnostic_alerts(
    guidance: list[str],
    *,
    resolved_status: int,
    turn_history: list[dict[str, Any]],
    has_truncation: bool,
    has_verifier_fail: bool,
    syntax_error_count: int,
    undefined_symbols_count: int,
    consecutive_repair_stalls: int,
    str_result: str,
) -> None:
    pattern_profile = call_symbolic_profile(
        IchingKernel,
        "ziwei_pattern_matrix_profile",
        turn_number=len(turn_history) + 1,
        current_status=resolved_status,
        token_budget_ok=not has_truncation,
        verifier_passed=not has_verifier_fail,
        consecutive_syntax_errors=syntax_error_count,
        undefined_symbols_count=undefined_symbols_count,
        consecutive_repair_stalls=consecutive_repair_stalls,
    )
    if pattern_profile is None:
        _append_engineering_diagnostic_alerts(
            guidance,
            resolved_status=resolved_status,
            has_truncation=has_truncation,
            has_verifier_fail=has_verifier_fail,
            syntax_error_count=syntax_error_count,
            undefined_symbols_count=undefined_symbols_count,
            consecutive_repair_stalls=consecutive_repair_stalls,
        )
        return

    p_name = pattern_profile["pattern"]
    if p_name == "羊陀夹忌":
        guidance.append(
            "- Deadlock alert (羊陀夹忌): Verifier failed while context/file was truncated. Do NOT attempt to rewrite the entire file. Emit surgical search_block/replace_block patches targeting only changed lines."
        )
    elif p_name == "陀罗暗滞":
        if not any("陀罗暗滞" in g for g in guidance):
            guidance.append(
                "- Stagnation warning (陀罗暗滞·化权破滞): Repair attempt yielded identical failures. The previous repair hypothesis failed. Pivot away from previous logic and revise core calculations."
            )
    elif p_name == "火铃夹命":
        guidance.append(
            "- Frantic retry warning (火铃夹命): Repeated syntax or patch mismatch errors. Take a step back and examine the file outline carefully before submitting another patch."
        )
    elif p_name == "空劫夹命":
        guidance.append(
            "- Hallucination alert (空劫夹命): Undefined symbols or missing modules detected. Only reference imports and symbols that exist in the workspace or Python standard library."
        )
    elif p_name == "化忌入官禄":
        guidance.append(
            "- Verifier failure (化忌入官禄): Test suite assertion failed. Focus surgical edits directly on the failing assertion requirements."
        )

    anchorage = call_symbolic_profile(
        IchingKernel,
        "shen_gong_anchorage_profile",
        turn_number=len(turn_history) + 1,
        current_status=resolved_status,
        token_budget_ok=not has_truncation,
        verifier_passed=not has_verifier_fail,
        environment_ok="timeout" not in str_result and "gateway" not in str_result,
    ) or {}
    if anchorage.get("shelter_guidance"):
        guidance.append(
            f"- Execution shelter (身宫寄托·{anchorage['palace_name']}): {anchorage['shelter_guidance']}"
        )

    brightness = call_symbolic_profile(
        IchingKernel,
        "star_brightness_profile",
        resolved_status,
        pattern_level=pattern_profile.get("level"),
    ) or {}
    if brightness.get("governance_mode") == "degraded":
        guidance.append(
            f"- Degraded protection mode (星曜落陷·{brightness['brightness_label']}): Energy unstable. Disallow full-file rewrite; limit actions to surgical diff or traceback inspection."
        )

    cascade = call_symbolic_profile(
        IchingKernel,
        "flying_sihua_cascade_profile",
        turn_number=len(turn_history) + 1,
        status_code=resolved_status,
    ) or {}
    if cascade.get("double_ji"):
        guidance.append(
            "- Double Ji cascade alert (双忌重叠): Major stage and micro turn collide. Halt all non-essential changes and focus strictly on minimal regression repair."
        )
    elif cascade.get("opposite_clash"):
        guidance.append(
            "- Opposite clash alert (化忌冲破): Opposite palace clash detected. Do not modify peripheral files; isolate changes to the culprit module."
        )

    guidance.extend(_ziwei_structural_alerts(resolved_status))
    guidance.extend(_recovery_defense_alerts(has_verifier_fail, turn_history, resolved_status))


def _append_engineering_diagnostic_alerts(
    guidance: list[str],
    *,
    resolved_status: int,
    has_truncation: bool,
    has_verifier_fail: bool,
    syntax_error_count: int,
    undefined_symbols_count: int,
    consecutive_repair_stalls: int,
) -> None:
    if has_verifier_fail and has_truncation:
        guidance.append(
            "- Deadlock alert: Verifier failed while context/file was truncated. Do NOT attempt to rewrite the entire file. Emit surgical search_block/replace_block patches targeting only changed lines."
        )
    elif consecutive_repair_stalls >= 2 and not any("Stagnation warning" in g for g in guidance):
        guidance.append(
            "- Stagnation warning: Repair attempt yielded identical failures. The previous repair hypothesis failed. Pivot away from previous logic and revise core calculations."
        )
    elif syntax_error_count > 0:
        guidance.append(
            "- Frantic retry warning: Repeated syntax or patch mismatch errors. Take a step back and examine the file outline carefully before submitting another patch."
        )
    elif undefined_symbols_count > 0:
        guidance.append(
            "- Hallucination alert: Undefined symbols or missing modules detected. Only reference imports and symbols that exist in the workspace or Python standard library."
        )
    elif has_verifier_fail:
        guidance.append(
            "- Verifier failure: Test suite assertion failed. Focus surgical edits directly on the failing assertion requirements."
        )

    if resolve_state_governance_mode(resolved_status) == "degraded":
        guidance.append(
            "- Degraded protection mode: Energy unstable. Disallow full-file rewrite; limit actions to surgical diff or traceback inspection."
        )
    interv = compute_systemic_intervention(resolved_status)
    if interv.get("turn_budget_damping_factor", 1.0) < 1.0:
        guidance.append("- Overload cooldown alert: System entropy too high. Enforce cooldown and surgical micro-patches.")
    elif interv.get("force_wal_checkpoint_sync"):
        guidance.append("- Preservation alert: System inertia high. Enforce state preservation and incremental commit.")


def format_repair_diagnostics(
    failed_result: dict[str, Any],
    failure_details: list[str],
    *,
    symbolic: bool | None = None,
) -> list[str]:
    """Derive targeted engineering diagnostics (and opt-in symbolic telemetry) for repair prompts."""
    use_symbolic = symbolic_telemetry_enabled() if symbolic is None else symbolic
    guidance: list[str] = []
    trace = failed_result.get("execution_trace", {})

    error_parts: list[str] = []
    for v in failed_result.get("verifier_results", []):
        if isinstance(v, dict):
            for key in ("stderr_tail", "stdout_tail", "reason"):
                val = v.get(key)
                if val:
                    error_parts.append(str(val))
    if isinstance(trace, dict):
        for rr in trace.get("runner_results", []):
            if isinstance(rr, dict):
                for key in ("reason", "payload"):
                    val = rr.get(key)
                    if val:
                        error_parts.append(str(val))

    turn_history = failed_result.get("turn_history", [])
    if error_parts and turn_history:
        joined_errors = "\n".join(error_parts)
        cause = (
            call_symbolic_profile(IchingKernel, "causal_origin_profile", joined_errors, turn_history)
            if use_symbolic
            else None
        ) or trace_causal_origin_file(joined_errors, turn_history)
        if cause:
            root_hdr = (
                f"- Causal root trace (来因宫 {cause['incoming_branch']})"
                if use_symbolic and "incoming_branch" in cause
                else "- Causal root trace"
            )
            guidance.append(
                f"{root_hdr}: Error originates from modifications in {cause['culprit_file']} (Turn {cause['incoming_turn_id']}). Focus patches on resolving this file."
            )

    guidance.extend(_extract_targeted_assertions(error_parts, symbolic=use_symbolic))
    guidance.extend(_tuo_luo_stagnation_alert(turn_history, symbolic=use_symbolic))

    str_result = str(failed_result).lower()
    combined_details = " ".join(failure_details).lower()
    has_truncation = "truncated" in str_result or "truncated" in combined_details
    has_verifier_fail = failed_result.get("status") in {"halted", "failed"} or "verifier" in combined_details
    syntax_error_count = sum(
        1
        for d in failure_details
        if any(
            k in d.lower()
            for k in ("syntaxerror", "syntax error", "syntax_error", "patch_mismatch", "invalid_model_plan")
        )
    )
    undefined_symbols_count = sum(1 for d in failure_details if any(k in d.lower() for k in ("nameerror", "importerror", "has no attribute", "modulenotfounderror")))

    raw_status = failed_result.get("task_status_code")
    if raw_status is None:
        raw_status = failed_result.get("iching_status_code")
    try:
        resolved_status = int(raw_status) if raw_status is not None else 32
    except (ValueError, TypeError):
        resolved_status = 32

    consecutive_repair_stalls = sum(
        1 for t in turn_history[1:] if t.get("reason") in {"verifier_failed", "command_failed", "repair_plan_must_use_patches_only"}
    ) if len(turn_history) >= 2 else 0

    if use_symbolic:
        _append_symbolic_diagnostic_alerts(
            guidance,
            resolved_status=resolved_status,
            turn_history=turn_history,
            has_truncation=has_truncation,
            has_verifier_fail=has_verifier_fail,
            syntax_error_count=syntax_error_count,
            undefined_symbols_count=undefined_symbols_count,
            consecutive_repair_stalls=consecutive_repair_stalls,
            str_result=str_result,
        )
    else:
        _append_engineering_diagnostic_alerts(
            guidance,
            resolved_status=resolved_status,
            has_truncation=has_truncation,
            has_verifier_fail=has_verifier_fail,
            syntax_error_count=syntax_error_count,
            undefined_symbols_count=undefined_symbols_count,
            consecutive_repair_stalls=consecutive_repair_stalls,
        )

    return guidance


def _format_ziwei_repair_guidance(failed_result: dict[str, Any], failure_details: list[str]) -> list[str]:
    """Backward-compatible wrapper returning repair diagnostics with symbolic tags enabled."""
    return format_repair_diagnostics(failed_result, failure_details, symbolic=True)


def _ziwei_structural_alerts(resolved_status: int) -> list[str]:
    alerts: list[str] = []
    breaking_profile = call_symbolic_profile(IchingKernel, "pattern_breaking_profile", resolved_status)
    if breaking_profile and breaking_profile.get("is_broken"):
        shas_str = "、".join(breaking_profile.get("breaking_shas_hit", []))
        alerts.append(
            f"- Formation broken alert (格局破格·{shas_str}): Health score {breaking_profile['formation_health_score']}. "
            f"{breaking_profile['governance_directive']}. Emit minimal search_block/replace_block patches; do NOT rewrite the file."
        )
    palace_star = call_symbolic_profile(
        IchingKernel,
        "palace_star_duality_profile",
        active_palace=resolved_status % 12,
    )
    if palace_star:
        alerts.append(
            f"- Active operational domain (把宫当星·{palace_star['palace_as_star']}): Focus on {palace_star['governance_domain']}."
        )
    coupling = call_symbolic_profile(
        IchingKernel,
        "systemic_coupling_profile",
        hexagram_state=resolved_status,
    )
    if coupling:
        if coupling["governance_posture"] == "yang_overload_cooldown_governance":
            alerts.append("- Yang overload alert (纯阳亢进): System entropy too high. Enforce cooldown and surgical micro-patches.")
        elif coupling["governance_posture"] == "yin_excess_checkpoint_preservation":
            alerts.append("- Yin excess alert (重阴凝滞): System inertia high. Enforce state preservation and incremental commit.")
    return alerts


def _recovery_defense_alerts(
    has_verifier_fail: bool,
    turn_history: list[dict[str, Any]],
    resolved_status: int | None = None,
) -> list[str]:
    from onecode.kernel.model_loop import _record_kernel_fault
    alerts: list[str] = []
    try:
        from onecode.kernel.recovery_policy import recovery_status

        scenario = "verifier_failure" if has_verifier_fail else "provider_failure"
        turn_num = len(turn_history) + 1
        rec = recovery_status(
            scenario,
            turn_number=turn_num,
            attempted=True,
            attempt_count=len(turn_history),
            status_code=resolved_status,
        )
        jie = rec.get("jie_shen_relief", {})
        if jie.get("relief_effective"):
            alerts.append(f"- Jie Shen relief active (解神化煞): {jie.get('reason')} Apply damping {jie.get('damping_factor')}.")
        deities = rec.get("twelve_deities", {})
        if deities.get("suipo_clash"):
            alerts.append(f"- Sui Po clash barrier (岁破隔离): {deities.get('reason')}")
    except (TypeError, ValueError, KeyError, AttributeError) as ex:
        _record_kernel_fault("recovery_defense_alerts", ex)
    return alerts


def _cached_workspace_scale_stats(workspace_key: str, mtime_ns: int = 0) -> tuple[int, int]:
    from onecode.kernel.model_loop import _record_kernel_fault
    ws = Path(workspace_key)
    file_count = 0
    total_loc = 0
    for path in ws.rglob("*.py"):
        parts = set(path.parts)
        if any(p.startswith(".") or p in {"venv", ".venv", "build", "dist", "__pycache__"} for p in parts):
            continue
        file_count += 1
        try:
            total_loc += len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
        except OSError as ex:
            _record_kernel_fault("workspace_line_count", ex)
    return file_count, total_loc


def workspace_scale_stats(workspace: Path) -> tuple[int, int]:
    from onecode.kernel.model_loop import _record_kernel_fault
    """Return (file_count, total_loc) for Python files in workspace, excluding venvs and hidden dirs."""
    try:
        resolved = workspace.resolve()
        mtime_ns = resolved.stat().st_mtime_ns if resolved.exists() else 0
        return _cached_workspace_scale_stats(str(resolved), mtime_ns)
    except (OSError, ValueError) as ex:
        _record_kernel_fault("workspace_scale_stats", ex)
        return 1, 40


def resolve_task_bureau(workspace: Path) -> dict[str, Any]:
    """Resolve workspace scale envelope and adaptive turn/timeout limits."""
    file_count, total_loc = workspace_scale_stats(workspace)
    ext = call_symbolic_profile(IchingKernel, "task_bureau_profile", file_count, total_loc)
    if ext is not None:
        return ext
    return compute_workspace_envelope(file_count, total_loc)


_DOC_SKIP_DIRS = frozenset({
    ".git", "tests", "reference_repo", "node_modules", "venv", ".venv", "__pycache__", ".onecode", "dist", "build",
})


def _iter_contract_docs(workspace: Path) -> list[Path]:
    docs: list[Path] = []
    for name in ("README.md", "README.txt", "spec.md", "SPEC.md"):
        path = workspace / name
        if path.is_file():
            docs.append(path)
    if not workspace.is_dir():
        return docs
    for path in sorted(workspace.rglob("README.md")):
        if path in docs:
            continue
        parts = path.relative_to(workspace).parts
        if any(part in _DOC_SKIP_DIRS or part.startswith(".") for part in parts):
            continue
        if len(parts) > 3:
            continue
        docs.append(path)
        if len(docs) >= 4:
            break
    docs_dir = workspace / "docs"
    if docs_dir.is_dir():
        for path in sorted(docs_dir.glob("*.md")):
            if path in docs:
                continue
            docs.append(path)
            if len(docs) >= 6:
                break
    return docs


def _contract_shape_rules(corpus: str) -> str:
    lowered = corpus.lower()
    rules: list[str] = []
    if "decisions.json" in lowered or ("decisions" in lowered and "reason" in lowered):
        rules.append(
            "A decision reason must be a short lowercase snake_case identifier, not a sentence or an explanation."
        )
    if "path" in lowered and any(token in lowered for token in ("error", "validation", "invalid")):
        rules.append("Indexes inside an error path or location list must be integers, not numeric strings.")
    if "header" in lowered or "valueerror" in lowered:
        rules.append(
            "When rejecting an invalid input, include the offending field or header name in the exception message."
        )
    if "--json" in lowered or ("json" in lowered and any(token in lowered for token in ("cli", "main.py", "image", "args.json"))):
        rules.append(
            "When a CLI outputs JSON objects for processed files, identify each file using both 'path' and 'file' keys (e.g. {'path': str(filepath), 'file': str(filepath), ...})."
        )
    return " ".join(rules)


def _package_import_rule(workspace: Path | None) -> str:
    if workspace is None or not workspace.is_dir():
        return ""
    packages: list[str] = []
    for path in sorted(workspace.rglob("__init__.py")):
        parts = path.relative_to(workspace).parts
        if any(part in _DOC_SKIP_DIRS or part.startswith(".") for part in parts):
            continue
        if len(parts) > 3:
            continue
        package = path.parent.relative_to(workspace).as_posix()
        if package and package not in packages:
            packages.append(package)
        if len(packages) >= 6:
            break
    if not packages:
        return ""
    listed = ", ".join(packages)
    return f"Import modules inside these packages by package path ({listed}.module), not by a bare module name."


def _contract_spec_snippet(workspace: Path | None, max_chars: int = 1500, task: str = "") -> str:
    from onecode.kernel.model_loop import _record_kernel_fault
    if workspace is None or not workspace.is_dir():
        rules = _contract_shape_rules(task)
        return f"Interface rules:\n{rules}\n\n" if rules else ""
    chunks: list[str] = []
    for path in _iter_contract_docs(workspace):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")[:800].strip()
        except OSError as ex:
            _record_kernel_fault("contract_spec", ex)
            continue
        if text:
            chunks.append(f"Workspace Contract Specification ({path.relative_to(workspace).as_posix()}):\n{text}")
    rules = _contract_shape_rules(f"{task}\n" + "\n".join(chunks))
    package_rule = _package_import_rule(workspace)
    if package_rule:
        rules = f"{rules} {package_rule}".strip()
    rule_block = f"Interface rules:\n{rules}\n\n" if rules else ""
    budget = max(0, max_chars - len(rule_block))
    body_parts: list[str] = []
    used = 0
    for chunk in chunks:
        piece = chunk[: max(0, budget - used)]
        if not piece:
            break
        body_parts.append(piece)
        used += len(piece) + 2
    body = rule_block + "\n\n".join(body_parts)
    return body + "\n\n" if body else ""


def repair_prompt(task: str, failed_result: dict[str, Any], workspace: Path | None = None) -> str:
    from onecode.kernel.model_loop import _record_kernel_fault
    from onecode.kernel.model_repair import _detail_mentions_tests, _is_test_path, _repair_source_block
    trace = failed_result.get("execution_trace", {})
    paths = []
    failure_details = []
    closest_hints = []
    if isinstance(trace, dict):
        for runner_result in trace.get("runner_results", []):
            payload = runner_result.get("payload", {}) if isinstance(runner_result, dict) else {}
            if isinstance(payload, dict) and isinstance(payload.get("path"), str) and not _is_test_path(payload["path"]):
                paths.append(payload["path"])
                if workspace is not None and runner_result.get("reason") in {"patch_mismatch", "patch_search_not_found", "patch_search_ambiguous"}:
                    from onecode.kernel.patching import find_closest_patch_context

                    search_block = payload.get("search_block")
                    if isinstance(search_block, str):
                        ctx = find_closest_patch_context(workspace, payload["path"], search_block)
                        if ctx.get("found") and ctx.get("excerpt"):
                            closest_hints.append(f"Closest matching lines in {payload['path']} (lines {ctx['start_line']}-{ctx['end_line']}):\n{ctx['excerpt']}")
            if isinstance(runner_result, dict) and not _detail_mentions_tests(payload):
                reason = runner_result.get("reason")
                status = runner_result.get("status")
                if reason or status:
                    failure_details.append(f"runner status={status} reason={reason} payload={payload}")
        for step_result in trace.get("step_results", []):
            if not isinstance(step_result, dict):
                continue
            reason = step_result.get("reason")
            if reason:
                failure_details.append(f"step {step_result.get('step_id')}: {reason}")
            for tool_result in step_result.get("tool_results", []):
                if isinstance(tool_result, dict) and tool_result.get("reason"):
                    failure_details.append(
                        f"tool {tool_result.get('tool_name')}: {tool_result.get('reason')}"
                    )
    raw_error_texts: list[str] = []
    for v in failed_result.get("verifier_results", []):
        if not isinstance(v, dict):
            continue
        v_reason = v.get("reason") or v.get("status")
        err = str(v.get("stderr_tail") or "").strip()
        out = str(v.get("stdout_tail") or "").strip()
        if err:
            raw_error_texts.append(err)
        if out:
            raw_error_texts.append(out)
        diag = format_verifier_diagnostics(out, err)
        if diag:
            failure_details.append(diag)
        else:
            parts = []
            if v_reason:
                parts.append(f"verifier {v_reason}")
            if err:
                parts.append(f"stderr:\n{err[-600:]}")
            if out:
                parts.append(f"stdout:\n{out[-600:]}")
            if parts:
                failure_details.append("\n".join(parts))
    path_summary = ", ".join(sorted(set(paths))) if paths else "unknown"
    details_list = []
    for d in failure_details[:10]:
        d_str = str(d).strip()
        if d_str.startswith("- ") or "\n" in d_str:
            details_list.append(d_str)
        else:
            details_list.append(f"- {d_str}")
    details = "\n".join(details_list) or "- unavailable"
    prompt = (
        "Repair the previous OneCode run using patches only.\n"
        f"Original task: {task}\n"
        f"Failure status: {failed_result.get('status')}\n"
        f"Failure reason: {failed_result.get('reason')}\n"
        f"Affected paths: {path_summary} (files already touched; you may patch any other relevant source file in the workspace)\n"
        f"Failure details:\n{details}\n"
        "A failing check may call a function defined outside the files already touched. "
        "Find that function's defining module and patch it there, instead of editing the same file again.\n"
        "If a test checks that an invalid operation or failure is blocked, inspect the workspace's error/exception definitions (e.g. errors module) and raise the intended domain exception class with an informative message rather than a generic or unhandled error.\n"
        "When reading or writing structured records (e.g. CSV, text tables, JSON lines), convert scalar fields to their intended primitive types (integers for IDs/counts/labels, floats for metrics, booleans for flags) rather than leaving them as raw strings. When input records contain structured dicts or metadata objects, preserve the underlying object structure rather than collapsing them to bare strings unless explicitly requested. When deduplicating or grouping rows, ensure distinct records are counted accurately without spurious duplicates.\n"
    )
    if closest_hints:
        prompt += "Patch context hints:\n" + "\n\n".join(closest_hints) + "\n"
    diag_hints = format_repair_diagnostics(failed_result, failure_details)
    if diag_hints:
        prompt += "Diagnostic guidance:\n" + "\n".join(diag_hints) + "\n"
    fault_hints: list[str] = []
    if workspace is not None and workspace.is_dir():
        try:
            from onecode.kernel.symbol_locator import SymbolLocator

            corpus = "\n".join(failure_details + raw_error_texts)
            locator = SymbolLocator(workspace)
            locations = locator.locate_fault(corpus)
            target_locations = [loc for loc in locations if not loc.is_test_file][:3]
            if target_locations:
                fault_hdr = _label_tag("Fault localization", "天相印绶·符号溯源定位", symbolic_telemetry_enabled())
                fault_hints.append(f"{fault_hdr}:")
                ws_files = failed_result.setdefault("workspace_files", {})
                for loc in target_locations:
                    fault_hints.append(
                        f"- Recommended patch target: file '{loc.file_path}', symbol '{loc.symbol_name}' "
                        f"(lines {loc.line_start}-{loc.line_end}, confidence {loc.confidence:.2f}). Reason: {loc.reason}"
                    )
                    if isinstance(ws_files, dict) and loc.file_path not in ws_files:
                        target_file = workspace / loc.file_path
                        if target_file.is_file():
                            try:
                                content = target_file.read_text(encoding="utf-8")
                                ws_files[loc.file_path] = content[:4000]
                            except OSError as ex:
                                _record_kernel_fault("fault_localization_read", ex)
        except (OSError, ValueError, TypeError, AttributeError) as ex:
            _record_kernel_fault("fault_localization", ex)
    if fault_hints:
        prompt += "\n".join(fault_hints) + "\n"
    spec_snippet = _contract_spec_snippet(workspace, task=task)
    if spec_snippet:
        prompt += spec_snippet
    prompt += (
        f"{_repair_source_block(failed_result)}"
        "Return JSON with patches only. Do not return assets, execution_plan, or no_action. "
        "Every repair plan must contain at least one patch fixing the test failure. "
        'Use {"task":"repair verifier failure","patches":[{"path":"<file>","search_block":"<exact original lines>","replace_block":"<fixed lines>"}]}. '
        "If multiple edits are needed in one file, provide a single consolidated patch for that file to prevent offset drift. Do not patch any path under tests/."
        + data_contract_guidance(task)
    )
    return prompt


