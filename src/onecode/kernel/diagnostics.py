import tempfile
from pathlib import Path

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.project_context import discover_project_context
from onecode.kernel.recovery_policy import recovery_status
from onecode.kernel.runner import run_task
from onecode.kernel.runtime_config import inspect_runtime_config
from onecode.kernel.skill_context import discover_skill_context, public_skill_context


def doctor_check(name: str, passed: bool, detail: dict | None = None) -> dict:
    return {"name": name, "passed": passed, "detail": detail or {}}


def doctor_result_detail(result: dict) -> dict:
    return {
        "run_id": result["run_id"],
        "status": result["status"],
        "reason": result["reason"],
        "iching_status_code": result["iching_status_code"],
        "iching_transition_action": result["iching_transition_action"],
        "iching_transition_reason": result["iching_transition_reason"],
        "dispatch_decision": result["iching_profile"]["dispatch_decision"],
    }


def doctor_rule_passed(result: dict) -> bool:
    profile = result["iching_profile"]
    profile_transition = IchingKernel.transition(profile["status_code"])
    return (
        profile["status_code"] == result["iching_status_code"]
        and profile["transition"]["action"] == profile_transition.action
        and profile["transition"]["reason"] == profile_transition.reason
        and profile["dispatch_decision"] == IchingKernel.dispatch_decision(profile_transition)
    )


def run_doctor() -> dict:
    checks = []
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)

        write_result = run_task(
            "doctor write",
            workspace=workspace,
            run_id="doctor-write",
            write_path="src/doctor_asset.py",
            write_content="value = 1\n",
        )
        checks.append(
            doctor_check(
                "write_text",
                write_result["status"] == "completed"
                and (workspace / "src" / "doctor_asset.py").exists()
                and doctor_rule_passed(write_result),
                doctor_result_detail(write_result),
            )
        )

        run_task(
            "doctor source",
            workspace=workspace,
            run_id="doctor-source",
            write_path="src/resume_asset.py",
            write_content="ready = True\n",
        )
        resume_result = run_task(
            "doctor resume",
            workspace=workspace,
            run_id="doctor-resume",
            resume_from_run_id="doctor-source",
            write_path="src/resume_asset.py",
            write_content="ready = False\n",
        )
        checks.append(
            doctor_check(
                "resume_skip",
                resume_result["status"] == "skipped"
                and resume_result["reason"] == "resumed_asset_ready"
                and (workspace / "src" / "resume_asset.py").read_text(encoding="utf-8") == "ready = True\n"
                and doctor_rule_passed(resume_result),
                doctor_result_detail(resume_result),
            )
        )

        outside = workspace.parent / "onecode-doctor-outside.txt"
        if outside.exists():
            outside.unlink()
        breach_result = run_task(
            "doctor breach",
            workspace=workspace,
            run_id="doctor-breach",
            write_path="../onecode-doctor-outside.txt",
            write_content="blocked\n",
        )
        checks.append(
            doctor_check(
                "sovereignty_breach",
                breach_result["status"] == "halted"
                and breach_result["reason"] == "sovereignty_breach"
                and not outside.exists()
                and doctor_rule_passed(breach_result),
                doctor_result_detail(breach_result),
            )
        )

        timeout_result = run_task(
            "doctor timeout",
            workspace=workspace,
            run_id="doctor-timeout",
            http_timeout_seconds=0.01,
            simulated_action_seconds=0.05,
        )
        checks.append(
            doctor_check(
                "http_timeout",
                timeout_result["status"] == "halted"
                and timeout_result["reason"] == "http_timeout"
                and doctor_rule_passed(timeout_result),
                doctor_result_detail(timeout_result),
            )
        )

        project_context = discover_project_context(workspace)
        checks.append(
            doctor_check(
                "project_context",
                project_context["status"] in {"ok", "warning"},
                project_context,
            )
        )

        runtime_config = inspect_runtime_config(workspace)
        checks.append(
            doctor_check(
                "runtime_config",
                runtime_config["status"] in {"ok", "warning"},
                runtime_config,
            )
        )

        skill_context = discover_skill_context(workspace)
        checks.append(
            doctor_check(
                "skill_context",
                skill_context["status"] in {"ok", "warning", "missing"},
                public_skill_context(skill_context),
            )
        )

        recovery = recovery_status("provider_failure")
        checks.append(
            doctor_check(
                "recovery_policy",
                recovery["recommended_action"] == "retry_once",
                recovery,
            )
        )

    return {"status": "ok" if all(check["passed"] for check in checks) else "failed", "checks": checks}
