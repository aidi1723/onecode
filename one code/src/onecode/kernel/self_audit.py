import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.model_provider import DEFAULT_DOMESTIC_PROVIDER_CONFIGS, build_provider_config


def audit_check(name: str, passed: bool, detail: dict | None = None) -> dict:
    return {"name": name, "passed": passed, "detail": detail or {}}


def run_command_check(name: str, command: list[str], cwd: Path) -> dict:
    env = os.environ.copy()
    env["ONECODE_AUDIT_SELF_DEPTH"] = str(int(env.get("ONECODE_AUDIT_SELF_DEPTH", "0")) + 1)
    src_path = str(cwd / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)
    return audit_check(
        name,
        completed.returncode == 0,
        {
            "returncode": completed.returncode,
            "stdout_tail": completed.stdout[-1000:],
            "stderr_tail": completed.stderr[-1000:],
        },
    )


def audit_self(
    project_root: Path,
    doctor_runner: Callable[[], dict],
    *,
    run_unittest: bool = True,
) -> dict:
    checks = []
    checks.append(audit_cli_entrypoint())
    checks.append(audit_tui_bootstrap())
    checks.append(audit_model_provider_matrix())
    checks.append(
        run_command_check(
            "compileall",
            [sys.executable, "-m", "compileall", "-q", "src", "tests"],
            cwd=project_root,
        )
    )
    if run_unittest:
        if int(os.environ.get("ONECODE_AUDIT_SELF_DEPTH", "0")) > 0:
            checks.append(audit_check("unittest", True, {"skipped_reason": "audit_self_recursion_guard"}))
        else:
            checks.append(
                run_command_check(
                    "unittest",
                    [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                    cwd=project_root,
                )
            )
    doctor_result = doctor_runner()
    checks.append(audit_check("doctor", doctor_result.get("status") == "ok", doctor_result))

    status = "ok" if all(check["passed"] for check in checks) else "failed"
    status_code = IchingKernel.classify_outcome("completed" if status == "ok" else "halted", None)
    transition = IchingKernel.transition(status_code)
    return {
        "status": status,
        "iching_status_code": status_code,
        "iching_transition_action": transition.action,
        "iching_transition_reason": transition.reason,
        "dispatch_decision": IchingKernel.dispatch_decision(transition),
        "checks": checks,
    }


def audit_cli_entrypoint() -> dict:
    from onecode.cli import build_parser

    parser = build_parser()
    subcommands = sorted(parser._subparsers._group_actions[0].choices)
    return audit_check(
        "cli_entrypoint",
        "audit-self" in subcommands and "tui" in subcommands and "run-model" in subcommands,
        {"shell": "cli", "subcommands": subcommands},
    )


def audit_tui_bootstrap() -> dict:
    try:
        from onecode.tui.app import OneCodeApp

        app = OneCodeApp()
        passed = app.workspace is not None and bool(app.model) and bool(app.endpoint)
        detail = {
            "shell": "tui",
            "workspace": str(app.workspace),
            "model": app.model,
            "provider_kind": app.provider_kind,
            "endpoint": app.endpoint,
        }
    except Exception as exc:  # pragma: no cover - exercised through audit output
        passed = False
        detail = {"shell": "tui", "error": f"{type(exc).__name__}: {exc}"}
    return audit_check("tui_bootstrap", passed, detail)


def audit_model_provider_matrix() -> dict:
    providers = ["qwen", "deepseek", "kimi", "zhipu"]
    configs = {provider: build_provider_config(provider, endpoint=None, model=None) for provider in providers}
    passed = all(
        provider in DEFAULT_DOMESTIC_PROVIDER_CONFIGS
        and configs[provider].endpoint.endswith("/chat/completions")
        and configs[provider].env_key.endswith("_API_KEY")
        and configs[provider].model
        for provider in providers
    )
    return audit_check(
        "model_provider_matrix",
        passed,
        {
            "providers": providers,
            "configs": {
                provider: {
                    "endpoint": config.endpoint,
                    "env_key": config.env_key,
                    "model": config.model,
                }
                for provider, config in configs.items()
            },
        },
    )
