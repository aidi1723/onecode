"""Prompt guidance and task-contract text for model runs."""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.preset_tests import is_preset_test_path

_RELATIVE_PYTHON = r"((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.py)"
_NAMED_PYTHON_FILE = re.compile(rf"(?<![\w./-]){_RELATIVE_PYTHON}\b")
_OUTPUT_DATA_FILE = re.compile(
    r"(?<![\w./-])([A-Za-z0-9_.-]+\.(?:csv|tsv|parquet|feather|jsonl))\b",
    re.IGNORECASE,
)
_DO_NOT_FILE = re.compile(
    rf"(?:do not|don't|never)\s+(?:modify|change|patch|edit|touch|rewrite)\s+{_RELATIVE_PYTHON}"
    rf"|((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.py)\s*(?:不要改|别改|不要动|别动|严禁修改|不可修改|无需修改)"
    rf"|(?:不要改|别改|不要修改|严禁修改)\s*((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.py)",
    re.IGNORECASE,
)
_ONLY_FILE = re.compile(rf"\bonly\s+{_RELATIVE_PYTHON}", re.IGNORECASE)
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


def data_contract_guidance(task: str) -> str:
    task_lower = task.lower()
    rules: list[str] = []

    def match(phrase_pat: str) -> bool:
        return bool(re.search(rf"(?:^|[\s\-_])(?:{phrase_pat})(?:$|[\s\-_])", task_lower))

    if match(r"invoices?|billing|credit[_\s-]+notes?") or any(k in task for k in ("账单", "发票")):
        rules.append(
            "For invoice line and tabular exports (Tianfu-Tianxiang Stamp & Command Contract 府相朝垣·印令昭明): "
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
        rules.append(
            "For schema drift audit (Tianxiang Yintie · Audit Schema Contract 天相印绶·规范审计): "
            "validate each record systematically against declared schema definitions; "
            "check missing required fields, type mismatches, enum violations, and unexpected properties in a single atomic pass; "
            "treat valid integer inputs as acceptable for numeric float constraints; "
            "ensure nullable fields allowing null/None are not falsely flagged; "
            "preserve stable input row ordering in output."
        )
    if match(r"time[_\s-]+leakage|temporal[_\s-]+leakage|feature[_\s-]+leakage") or any(k in task for k in ("时间泄漏", "时序穿越")):
        rules.append(
            "For time leakage audit (Tianliang Canopy Audit 荫星照微·截止容限): "
            "verify that feature timestamps do not exceed configured cutoff times plus declared tolerance windows; "
            "partition clean training samples from time-leaking samples into designated clean and rejected outputs; "
            "preserve input ordering for clean records and record detailed leakage diagnostics."
        )
    if match(r"support[_\s-]+sla|service[_\s-]+level[_\s-]+agreement") or (match(r"sla") and match(r"tickets?|support|customer[_\s-]+service")) or "工单履约" in task:
        rules.append(
            "For support SLA metrics (Tianxiang Inspection 督考巡历·工单履约): "
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
                if name not in failed_names:
                    failed_names.append(name)
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


def _extract_targeted_assertions(error_parts: list[str]) -> list[str]:
    alerts: list[str] = []
    matched_assertion = False
    for ep in error_parts:
        m = re.search(r"(AssertionError: [^\n]+)", ep)
        if m:
            alerts.append(
                f"- Precision assertion target (水生木·精准断言): {m.group(1).strip()}. Focus surgical edit directly on resolving this discrepancy; do not repeat previous values."
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
            f"- Precision assertion target (水生木·精准断言): Failing test check '{first}'. Focus surgical edit directly on satisfying this test condition."
        )

    if len(failing_checks) > 1:
        items_str = ", ".join(f"'{c}'" for c in failing_checks[:8])
        alerts.append(
            f"- Precision assertion array (三方四正·全量断言照会): Multiple failing checks detected: [{items_str}]. Satisfy all test assertions simultaneously."
        )

    passing_checks: list[str] = []
    for ep in error_parts:
        for match in re.finditer(r'\"name\":\s*\"([^\"]+)\",\s*\"passed\":\s*true', ep):
            pname = match.group(1).strip()
            if pname and pname not in passing_checks:
                passing_checks.append(pname)
    if passing_checks:
        pass_str = ", ".join(f"'{c}'" for c in passing_checks[:6])
        alerts.append(
            f"- Preserved baseline tests (三台八座·既得吉果不可毁): Previous run PASSED: [{pass_str}]. "
            "Your patch MUST preserve all passing tests and strictly avoid regression (吉处藏凶·防范冲破)."
        )

    for ep in error_parts:
        m_exc = re.search(r"((?:KeyError|FileNotFoundError|UnicodeError|UnicodeDecodeError|ValueError|AttributeError|ZeroDivisionError|IndexError): [^\n]+)", ep)
        if m_exc:
            alerts.append(
                f"- Hidden runtime anomaly (铃星隐煞·天相印信昭明): {m_exc.group(1).strip()}. "
                "Check file existence, pure UTF-8 encoding (no BOM bytes), and exact key/header matching."
            )
            break

    for ep in error_parts:
        if any(token in ep.lower() for token in ("empty", "zerodivision", "keyerror", "iterable argument is empty")):
            alerts.append(
                "- Boundary opposition guard (错卦互补·空集与极值防线): Defend against empty inputs/token lists, "
                "missing dictionary keys, and boundary conditions. Never call max()/min()/next() on empty collections; supply safe fallbacks."
            )
            break

    for fc in failing_checks:
        fc_low = fc.lower()
        if "credit" in fc_low or "line_total" in fc_low:
            alerts.append(
                "- Accounting adjustment rule (府相朝垣·库印分明): For credit, discount, or deduction entries, "
                "ensure positive voucher amounts are recorded distinctly from negative net balance reductions, "
                "maintaining mathematical ledger consistency."
            )
            break
        if "score" in fc_low or "clipped" in fc_low or "format" in fc_low:
            alerts.append(
                "- Canonical number formatting (文昌化科·整型规范): In CSV outputs, "
                "format whole numbers without trailing '.0' (e.g. write '1' not '1.0', '0' not '0.0')."
            )
            break
    return alerts


def _tuo_luo_stagnation_alert(turn_history: list[dict[str, Any]]) -> list[str]:
    alerts: list[str] = []
    if len(turn_history) >= 2:
        last = turn_history[-1]
        if last.get("reason") in {"verifier_failed", "command_failed", "repair_plan_must_use_patches_only"}:
            alerts.append(
                "- Stagnation warning (陀罗暗滞·化权破滞): Previous repair attempt did not resolve the failure. "
                "Pivot decisively: check README.md contract specifications, exact field and column naming, "
                "edge cases (empty collections, zero values), and adjust implementation strategy rather than minor tweaks."
            )
    return alerts


def _format_ziwei_repair_guidance(failed_result: dict[str, Any], failure_details: list[str]) -> list[str]:
    """Derive targeted Ziwei diagnostic guidance for the repair prompt."""
    guidance: list[str] = []
    trace = failed_result.get("execution_trace", {})

    # 1. Causal Root Trace (来因宫溯源)
    error_parts: list[str] = []
    for v in failed_result.get("verifier_results", []):
        if isinstance(v, dict):
            stderr = v.get("stderr_tail")
            stdout = v.get("stdout_tail")
            reason = v.get("reason")
            if stderr:
                error_parts.append(str(stderr))
            if stdout:
                error_parts.append(str(stdout))
            if reason:
                error_parts.append(str(reason))
    if isinstance(trace, dict):
        for rr in trace.get("runner_results", []):
            if isinstance(rr, dict):
                reason = rr.get("reason")
                payload = rr.get("payload")
                if reason:
                    error_parts.append(str(reason))
                if payload:
                    error_parts.append(str(payload))

    turn_history = failed_result.get("turn_history", [])
    if error_parts and turn_history:
        combined_errors = "\n".join(error_parts)
        cause = IchingKernel.causal_origin_profile(combined_errors, turn_history)
        if cause:
            guidance.append(
                f"- Causal root trace (来因宫 {cause['incoming_branch']}): Error originates from modifications in {cause['culprit_file']} (Turn {cause['incoming_turn_id']}). Focus patches on resolving this file."
            )

    # Water Nourishing Wood & Tuo Luo/Ling Xing Diagnostics
    guidance.extend(_extract_targeted_assertions(error_parts))
    guidance.extend(_tuo_luo_stagnation_alert(turn_history))

    # 2. Comprehensive Ziwei Pattern Matrix Guidance (格局矩阵诊断)
    str_result = str(failed_result).lower()
    combined_details = " ".join(failure_details).lower()
    has_truncation = "truncated" in str_result or "truncated" in combined_details
    has_verifier_fail = failed_result.get("status") in {"halted", "failed"} or "verifier" in combined_details
    syntax_error_count = sum(1 for d in failure_details if any(k in d.lower() for k in ("syntaxerror", "patch_mismatch", "invalid_model_plan")))
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

    pattern_profile = IchingKernel.ziwei_pattern_matrix_profile(
        turn_number=len(turn_history) + 1,
        current_status=resolved_status,
        token_budget_ok=not has_truncation,
        verifier_passed=not has_verifier_fail,
        consecutive_syntax_errors=syntax_error_count,
        undefined_symbols_count=undefined_symbols_count,
        consecutive_repair_stalls=consecutive_repair_stalls,
    )
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

    # 3. Execution Anchorage & Fallback Shelter (身宫寄托)
    anchorage = IchingKernel.shen_gong_anchorage_profile(
        turn_number=len(turn_history) + 1,
        current_status=resolved_status,
        token_budget_ok=not has_truncation,
        verifier_passed=not has_verifier_fail,
        environment_ok="timeout" not in str_result and "gateway" not in str_result,
    )
    if anchorage.get("shelter_guidance"):
        guidance.append(
            f"- Execution shelter (身宫寄托·{anchorage['palace_name']}): {anchorage['shelter_guidance']}"
        )

    # 4. Star Brightness & Degraded Protection (星曜庙旺落陷)
    brightness = IchingKernel.star_brightness_profile(resolved_status, pattern_level=pattern_profile.get("level"))
    if brightness.get("governance_mode") == "degraded":
        guidance.append(
            f"- Degraded protection mode (星曜落陷·{brightness['brightness_label']}): Energy unstable. Disallow full-file rewrite; limit actions to surgical diff or traceback inspection."
        )

    # 5. Flying Sihua Cascade & Dynamic Clash Defense (跨宫飞星与级联四化防御)
    cascade = IchingKernel.flying_sihua_cascade_profile(
        turn_number=len(turn_history) + 1,
        status_code=resolved_status,
    )
    if cascade.get("double_ji"):
        guidance.append(
            "- Double Ji cascade alert (双忌重叠): Major stage and micro turn collide. Halt all non-essential changes and focus strictly on minimal regression repair."
        )
    elif cascade.get("opposite_clash"):
        guidance.append(
            "- Opposite clash alert (化忌冲破): Opposite palace clash detected. Do not modify peripheral files; isolate changes to the culprit module."
        )

    # 6. Structural & Coupling Alerts (破格/把宫当星/全参数联动)
    guidance.extend(_ziwei_structural_alerts(resolved_status))

    # 7. Jie Shen Relief & Sui Po Defense (解神化煞与岁破防御)
    guidance.extend(_recovery_defense_alerts(has_verifier_fail, turn_history, resolved_status))

    return guidance


def _ziwei_structural_alerts(resolved_status: int) -> list[str]:
    alerts: list[str] = []
    breaking_profile = IchingKernel.pattern_breaking_profile(resolved_status)
    if breaking_profile.get("is_broken"):
        shas_str = "、".join(breaking_profile.get("breaking_shas_hit", []))
        alerts.append(
            f"- Formation broken alert (格局破格·{shas_str}): Health score {breaking_profile['formation_health_score']}. "
            f"{breaking_profile['governance_directive']}. Emit minimal search_block/replace_block patches; do NOT rewrite the file."
        )
    palace_star = IchingKernel.palace_star_duality_profile(active_palace=resolved_status % 12)
    alerts.append(
        f"- Active operational domain (把宫当星·{palace_star['palace_as_star']}): Focus on {palace_star['governance_domain']}."
    )
    coupling = IchingKernel.systemic_coupling_profile(hexagram_state=resolved_status)
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
    """Resolve the task's Five Elements Bureau (五行局) and adaptive scheduling limits."""
    file_count, total_loc = workspace_scale_stats(workspace)
    return IchingKernel.task_bureau_profile(file_count, total_loc)


def _contract_spec_snippet(workspace: Path | None, max_chars: int = 1500) -> str:
    from onecode.kernel.model_loop import _record_kernel_fault
    if workspace is None or not workspace.is_dir():
        return ""
    for candidate in ("README.md", "README.txt", "spec.md", "SPEC.md"):
        doc_path = workspace / candidate
        if doc_path.is_file():
            try:
                text = doc_path.read_text(encoding="utf-8", errors="replace")[:max_chars].strip()
                if text:
                    return f"Workspace Contract Specification (文昌文曲·契约印信 - {candidate}):\n{text}\n\n"
            except OSError as ex:
                _record_kernel_fault("contract_spec", ex)
    return ""


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
    ziwei_hints = _format_ziwei_repair_guidance(failed_result, failure_details)
    if ziwei_hints:
        prompt += "Diagnostic guidance:\n" + "\n".join(ziwei_hints) + "\n"
    fault_hints: list[str] = []
    if workspace is not None and workspace.is_dir():
        try:
            from onecode.kernel.symbol_locator import SymbolLocator

            corpus = "\n".join(failure_details + raw_error_texts)
            locator = SymbolLocator(workspace)
            locations = locator.locate_fault(corpus)
            target_locations = [loc for loc in locations if not loc.is_test_file][:3]
            if target_locations:
                fault_hints.append("Fault localization (天相印绶·符号溯源定位):")
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
    spec_snippet = _contract_spec_snippet(workspace)
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


