#!/usr/bin/env python3
"""Empirical evaluation and demonstration of Human-in-the-Loop breakpoint resumption.

Verifies the closed loop:
1. When visible contract has no reason enum and repair is stagnant, execution halts
   with status="halted", reason="approval_required", capturing best_snapshot.
2. Engineer inspects pending approval ticket via GET /v1/onecode/approvals/pending.
3. Engineer supplies missing short code via POST /v1/onecode/approvals/{id}/resolve.
4. Engine restores best_snapshot, applies short code in a single targeted turn,
   and immediately re-evaluates via host verifier without burning model tokens.
5. Quality checks: zero verifier slugs in src/onecode, claims_mainstream_parity is false.

Pure Python standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

# Ensure src/ is on PYTHONPATH
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from onecode.kernel.model_repair import (
    _contract_has_reason_enum as contract_has_reason_enum,
    _maybe_open_reason_clarification_approval,
    _snapshot_workspace_files,
)
from onecode.web.api_handlers import (
    handle_onecode_approval_resolve,
    handle_onecode_pending_approvals,
)


def verify_no_kernel_slug_leak() -> list[str]:
    """Ensure kernel source files contain zero forbidden answer slugs."""
    forbidden = ["too_recently_active", "no_paid_charge", "meaningful_usage"]
    leaks: list[str] = []
    src_dir = _REPO_ROOT / "src"
    for py_file in src_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for slug in forbidden:
            if slug in content:
                leaks.append(f"{py_file.name}: contains {slug}")
    return leaks


def setup_coupon_task_workspace(workspace_root: Path) -> dict[str, Any]:
    """Setup a workspace simulating product_policy-medium-coupon_eligibility."""
    target_dir = workspace_root / "coupon_workspace"
    target_dir.mkdir(parents=True, exist_ok=True)
    # Instruction without reason enum table
    (target_dir / "README.md").write_text(
        "# Coupon Eligibility Policy\n\n"
        "Filter churned users for winback coupon. Block recently active, suppressed, or recent coupon recipients.\n"
        "Outputs decisions.json with user_id, status (eligible/blocked), reason, coupon.\n",
        encoding="utf-8",
    )
    app_dir = target_dir / "app"
    app_dir.mkdir(parents=True, exist_ok=True)
    # Model's Round 19 implementation using 'recently_active' instead of 'too_recently_active'
    policy_code = '''#!/usr/bin/env python3
import json
from pathlib import Path

def evaluate(data_dir: Path) -> dict:
    decisions = [
        {"user_id": "u1", "status": "eligible", "reason": "eligible", "coupon": "WINBACK20", "days_since_seen": 106},
        {"user_id": "u2", "status": "blocked", "reason": "not_churned", "coupon": None, "days_since_seen": 5},
        {"user_id": "u3", "status": "blocked", "reason": "unsupported_country", "coupon": None, "days_since_seen": 90},
        {"user_id": "u4", "status": "blocked", "reason": "suppressed", "coupon": None, "days_since_seen": 80},
        {"user_id": "u5", "status": "blocked", "reason": "recent_coupon", "coupon": None, "days_since_seen": 75},
        {"user_id": "u6", "status": "blocked", "reason": "recently_active", "coupon": None, "days_since_seen": 45},
    ]
    return {
        "summary": {"eligible": 1, "blocked": 5, "high_value_eligible": 1},
        "decisions": decisions,
    }

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data")
    parser.add_argument("--out", default="decisions.json")
    args = parser.parse_args()
    Path(args.out).write_text(json.dumps(evaluate(Path(args.data)), indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
'''
    (app_dir / "policy.py").write_text(policy_code, encoding="utf-8")
    # Initial decisions.json
    (target_dir / "decisions.json").write_text(
        json.dumps({
            "summary": {"eligible": 1, "blocked": 5, "high_value_eligible": 1},
            "decisions": [
                {"user_id": "u1", "status": "eligible", "reason": "eligible", "coupon": "WINBACK20", "days_since_seen": 106},
                {"user_id": "u2", "status": "blocked", "reason": "not_churned", "coupon": None, "days_since_seen": 5},
                {"user_id": "u3", "status": "blocked", "reason": "unsupported_country", "coupon": None, "days_since_seen": 90},
                {"user_id": "u4", "status": "blocked", "reason": "suppressed", "coupon": None, "days_since_seen": 80},
                {"user_id": "u5", "status": "blocked", "reason": "recent_coupon", "coupon": None, "days_since_seen": 75},
                {"user_id": "u6", "status": "blocked", "reason": "recently_active", "coupon": None, "days_since_seen": 45},
            ]
        }, indent=2),
        encoding="utf-8",
    )
    # External host verifier OUTSIDE workspace (required by security boundary)
    host_verifier_dir = workspace_root / "external_verifier"
    host_verifier_dir.mkdir(parents=True, exist_ok=True)
    verifier_code = '''import json
import os
import subprocess
from pathlib import Path

ROOT = Path(os.environ.get("WORKSPACE", "."))
LOG_DIR = Path(os.environ.get("LOG_DIR", ROOT / "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

proc = subprocess.run(["python3", "app/policy.py", "--out", "decisions.json"], cwd=ROOT, capture_output=True, text=True)
decisions = json.loads((ROOT / "decisions.json").read_text()).get("decisions", [])
by = {d["user_id"]: d for d in decisions}

checks = [
    ("command exits cleanly", proc.returncode == 0),
    ("all users evaluated", sorted(by.keys()) == ["u1", "u2", "u3", "u4", "u5", "u6"]),
    ("churned US old enough gets coupon", by.get("u1", {}).get("status") == "eligible"),
    ("active user blocked", by.get("u2", {}).get("reason") == "not_churned"),
    ("unsupported country blocked", by.get("u3", {}).get("reason") == "unsupported_country"),
    ("suppressed user blocked", by.get("u4", {}).get("reason") == "suppressed"),
    ("recent coupon blocks resend", by.get("u5", {}).get("reason") == "recent_coupon"),
    ("recently active churned user blocked", by.get("u6", {}).get("reason") == "too_recently_active"),
    ("days since seen calculated", by.get("u1", {}).get("days_since_seen") == 106),
    ("summary eligible count", True),
    ("summary blocked count", True),
    ("high value eligible count", True),
    ("blocked users have null coupon", True),
]

passed = sum(1 for _, ok in checks if ok)
total = len(checks)
reward = round(passed / total, 4)
results = [{"name": name, "passed": ok} for name, ok in checks]

output = {
    "overall": reward,
    "test_pass_rate": reward,
    "tests_passed": passed,
    "tests_total": total,
    "test_status": "pass" if passed == total else "no_pass",
    "tests": results,
}
(LOG_DIR / "reward.json").write_text(json.dumps(output, indent=2))
(LOG_DIR / "reward.txt").write_text(str(reward))
print(f"VERIFIER FINISHED: {passed}/{total} = {reward}")
'''
    verifier_file = host_verifier_dir / "verifier.py"
    verifier_file.write_text(verifier_code, encoding="utf-8")
    return {
        "task_id": "product_policy-medium-coupon_eligibility",
        "workspace": target_dir,
        "verifier": verifier_file,
        "baseline_score": 0.9231,
        "expected_failing_check": "recently active churned user blocked",
        "initial_emitted_slug": "recently_active",
        "engineer_selected_slug": "too_recently_active",
    }


def setup_refund_task_workspace(workspace_root: Path) -> dict[str, Any]:
    """Setup a workspace simulating product_policy-medium-refund_policy."""
    target_dir = workspace_root / "refund_workspace"
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "README.md").write_text(
        "# Refund Policy\n\nProcess refund requests from CSV. Output decisions.json with request_id, status, reason.\n",
        encoding="utf-8",
    )
    app_dir = target_dir / "app"
    app_dir.mkdir(parents=True, exist_ok=True)
    policy_code = '''#!/usr/bin/env python3
import json
from pathlib import Path

def evaluate(data_dir: Path) -> dict:
    decisions = [
        {"request_id": "r1", "status": "approved", "reason": "recent_low_usage", "refund_cents": 1200, "days_since_payment": 4, "currency": "USD"},
        {"request_id": "r2", "status": "manual_review", "reason": "meaningful_usage", "refund_cents": 0, "days_since_payment": 10, "currency": "USD"},
        {"request_id": "r3", "status": "denied", "reason": "outside_window", "refund_cents": 0, "days_since_payment": 40, "currency": "USD"},
        {"request_id": "r4", "status": "denied", "reason": "trial_or_zero_charge", "refund_cents": 0, "days_since_payment": 5, "currency": "USD"},
        {"request_id": "r5", "status": "manual_review", "reason": "feature_export", "refund_cents": 0, "days_since_payment": 2, "currency": "USD"},
    ]
    return {
        "summary": {"approved": 1, "denied": 2, "manual_review": 2, "refund_cents": 1200},
        "decisions": decisions,
    }

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data")
    parser.add_argument("--out", default="decisions.json")
    args = parser.parse_args()
    Path(args.out).write_text(json.dumps(evaluate(Path(args.data)), indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
'''
    (app_dir / "policy.py").write_text(policy_code, encoding="utf-8")
    (target_dir / "decisions.json").write_text(
        json.dumps({
            "summary": {"approved": 1, "denied": 2, "manual_review": 2, "refund_cents": 1200},
            "decisions": [
                {"request_id": "r1", "status": "approved", "reason": "recent_low_usage", "refund_cents": 1200, "days_since_payment": 4, "currency": "USD"},
                {"request_id": "r2", "status": "manual_review", "reason": "meaningful_usage", "refund_cents": 0, "days_since_payment": 10, "currency": "USD"},
                {"request_id": "r3", "status": "denied", "reason": "outside_window", "refund_cents": 0, "days_since_payment": 40, "currency": "USD"},
                {"request_id": "r4", "status": "denied", "reason": "trial_or_zero_charge", "refund_cents": 0, "days_since_payment": 5, "currency": "USD"},
                {"request_id": "r5", "status": "manual_review", "reason": "feature_export", "refund_cents": 0, "days_since_payment": 2, "currency": "USD"},
            ]
        }, indent=2),
        encoding="utf-8",
    )
    host_verifier_dir = workspace_root / "external_verifier_refund"
    host_verifier_dir.mkdir(parents=True, exist_ok=True)
    verifier_code = '''import json
import os
import subprocess
from pathlib import Path

ROOT = Path(os.environ.get("WORKSPACE", "."))
LOG_DIR = Path(os.environ.get("LOG_DIR", ROOT / "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

proc = subprocess.run(["python3", "app/policy.py", "--out", "decisions.json"], cwd=ROOT, capture_output=True, text=True)
decisions = json.loads((ROOT / "decisions.json").read_text()).get("decisions", [])
by = {d["request_id"]: d for d in decisions}

checks = [
    ("command exits cleanly", proc.returncode == 0),
    ("all five requests are present", sorted(by.keys()) == ["r1", "r2", "r3", "r4", "r5"]),
    ("low usage within window is approved", by.get("r1", {}).get("status") == "approved"),
    ("annual meaningful usage goes to manual review", by.get("r2", {}).get("status") == "manual_review"),
    ("late request is denied", by.get("r3", {}).get("reason") == "outside_window"),
    ("trial zero payment is denied", by.get("r4", {}).get("reason") == "no_paid_charge"),
    ("feature export triggers manual review", by.get("r5", {}).get("status") == "manual_review"),
    ("day age is calculated", by.get("r1", {}).get("days_since_payment") == 4),
    ("currency is preserved", True),
    ("summary approved count", True),
    ("summary denied count", True),
    ("summary manual count", True),
    ("summary refund total", True),
]

passed = sum(1 for _, ok in checks if ok)
total = len(checks)
reward = round(passed / total, 4)
results = [{"name": name, "passed": ok} for name, ok in checks]

output = {
    "overall": reward,
    "test_pass_rate": reward,
    "tests_passed": passed,
    "tests_total": total,
    "test_status": "pass" if passed == total else "no_pass",
    "tests": results,
}
(LOG_DIR / "reward.json").write_text(json.dumps(output, indent=2))
(LOG_DIR / "reward.txt").write_text(str(reward))
print(f"VERIFIER FINISHED: {passed}/{total} = {reward}")
'''
    verifier_file = host_verifier_dir / "verifier.py"
    verifier_file.write_text(verifier_code, encoding="utf-8")
    return {
        "task_id": "product_policy-medium-refund_policy",
        "workspace": target_dir,
        "verifier": verifier_file,
        "baseline_score": 0.8462,
        "expected_failing_check": "trial zero payment is denied",
        "initial_emitted_slug": "trial_or_zero_charge",
        "engineer_selected_slug": "no_paid_charge",
    }


def _run_single_empirical_task(task_info: dict[str, Any]) -> dict[str, Any]:
    ws = task_info["workspace"]
    print(f"\n[INFO] Starting empirical cycle for task: {task_info['task_id']}")
    print(f"[INFO] Contract reason enum present: {contract_has_reason_enum(ws)} (expected: False)")

    best_snapshot = _snapshot_workspace_files(ws)
    tested = {
        "status": "completed",
        "reason": "verifier_failed",
        "host_reward": task_info["baseline_score"],
        "verifier_results": [{"stdout_tail": f"- [FAIL] {task_info['expected_failing_check']}\n"}],
    }
    rec = _maybe_open_reason_clarification_approval(
        workspace=ws,
        task=f"evaluate policy for {task_info['task_id']}",
        tested=tested,
        current_checked=tested,
        best_checked=tested,
        attempt=2,
        best_snapshot=best_snapshot,
        run_metadata={"task_id": task_info["task_id"], "host_verifier": str(task_info["verifier"])},
    )
    assert rec is not None, "Expected approval record to be created"
    approval_id = rec["id"]
    print(f"[STAGE 1] Pending approval opened: {approval_id}")
    print(f"          Failing check: {task_info['expected_failing_check']}")
    print(f"          Emitted reason: {task_info['initial_emitted_slug']}")

    os.environ["ONECODE_WORKSPACE_ROOT"] = str(ws)
    os.environ["ONECODE_ALLOWED_WORKSPACE_ROOTS"] = str(ws.parent)
    pending_res, code = handle_onecode_pending_approvals({"workspace": str(ws)})
    assert code == 200
    assert len(pending_res.get("approvals", [])) == 1

    selected_slug = task_info["engineer_selected_slug"]
    print(f"[STAGE 3] Engineer resolves approval with selected_slug='{selected_slug}'")
    resolve_body = {
        "decision": "approved",
        "selected_slug": selected_slug,
        "workspace": str(ws),
    }
    resolve_res, resolve_code = handle_onecode_approval_resolve(approval_id, resolve_body)
    assert resolve_code == 200
    assert resolve_res.get("regraded") is not None
    assert resolve_res.get("repair_applied") is True
    regraded_score = resolve_res.get("host_reward")
    print(f"          New score: {regraded_score} | Status: {resolve_res.get('repair_status')}")
    assert regraded_score == 1.0, f"Expected 1.0, got {regraded_score}"
    assert resolve_res.get("repair_status") == "completed"

    # Confirm pending approval was consumed
    remaining_pending, _ = handle_onecode_pending_approvals({"workspace": str(ws)})
    assert len(remaining_pending.get("approvals", [])) == 0
    print("[PASS] Pending approval ticket consumed cleanly")

    # Confirm resolution recorded
    resolved_file = ws / ".onecode" / "resolved_approvals.json"
    assert resolved_file.is_file()
    resolved_data = json.loads(resolved_file.read_text(encoding="utf-8"))
    assert any(r.get("id") == approval_id for r in resolved_data)
    print(f"[PASS] Resolution persisted to {resolved_file.name}")

    # Confirm code updated
    policy_text = (ws / "app" / "policy.py").read_text(encoding="utf-8")
    assert selected_slug in policy_text
    print(f"[PASS] Code updated with engineer slug '{selected_slug}'")

    return {
        "task_id": task_info["task_id"],
        "baseline_score": task_info["baseline_score"],
        "regraded_score": regraded_score,
        "status": resolve_res.get("repair_status"),
        "selected_slug": selected_slug,
        "token_cost_resumption": 0,
    }


def run_empirical_demo(workspace_root: Path) -> dict[str, Any]:
    """Execute the empirical breakpoint-resume demonstration across both tasks."""
    print("=" * 70)
    print("ONECODE EMPIRICAL BREAKPOINT RESUMPTION VERIFICATION")
    print("=" * 70)

    # 1. Check kernel source hygiene
    leaks = verify_no_kernel_slug_leak()
    if leaks:
        print(f"[FAIL] Kernel source leak detected: {leaks}")
        return {"success": False, "reason": "kernel_slug_leak", "leaks": leaks}
    print("[PASS] Kernel source hygiene: 0 forbidden verifier slugs present in src/onecode")

    tasks = [
        setup_coupon_task_workspace(workspace_root),
        setup_refund_task_workspace(workspace_root),
    ]

    results: list[dict[str, Any]] = []
    for task_info in tasks:
        task_res = _run_single_empirical_task(task_info)
        results.append(task_res)

    print("\n" + "=" * 70)
    print("EMPIRICAL BREAKPOINT VERIFICATION PASSED: Full score 1.0 achieved on all tasks")
    print("=" * 70)

    return {
        "success": True,
        "task_results": results,
        "claims_mainstream_parity": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Empirical approval breakpoint resolution harness")
    parser.add_argument("--work-dir", type=Path, default=None, help="Working directory for empirical run")
    args = parser.parse_args()

    if args.work_dir:
        result = run_empirical_demo(args.work_dir)
    else:
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = run_empirical_demo(Path(tmp_dir))

    print(json.dumps(result, indent=2))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
