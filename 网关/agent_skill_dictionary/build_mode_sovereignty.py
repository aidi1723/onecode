from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .build_mode_orchestrator import RequiredArtifactPlan


PROJECT_REQUIRED_PACKAGES: dict[str, tuple[str, ...]] = {
    "secure-rpc-mesh": ("fastapi", "pytest_asyncio", "cryptography"),
    "cluster-state-sync": ("fastapi", "sqlmodel", "pytest_asyncio", "redis"),
    "ephemeral-mesh-kv": (),
}

SUPPORT_FILES: dict[str, tuple[str, ...]] = {
    "secure-rpc-mesh": ("api/__init__.py", "core/__init__.py", "tests/__init__.py"),
    "cluster-state-sync": ("api/__init__.py", "sync/__init__.py", "tests/__init__.py"),
    "secure-b2b-ledger-sync-repair": (
        "auth.py",
        "ledger.json",
        "ledger.py",
        "main.py",
        "pyproject.toml",
        "requirements.txt",
        "tests/__init__.py",
        "tests/test_sync.py",
        "warehouse_snapshot.json",
    ),
    "ephemeral-mesh-kv": ("tests/__init__.py",),
}

ALLOWED_METADATA_PREFIXES = (
    ".yizijue/",
    "__pycache__/",
)


@dataclass(frozen=True)
class EnvironmentGateReport:
    ok: bool
    action: str
    required_packages: tuple[str, ...]
    missing_packages: tuple[str, ...]
    python_executable: str


@dataclass(frozen=True)
class WorkspaceSovereigntyReport:
    ok: bool
    action: str
    allowed_paths: tuple[str, ...]
    unplanned_paths: tuple[str, ...]


def expected_packages_for_plan(plan: RequiredArtifactPlan) -> tuple[str, ...]:
    return PROJECT_REQUIRED_PACKAGES.get(plan.project_name, ())


def audit_environment_gate(
    plan: RequiredArtifactPlan,
    *,
    python_executable: str | Path | None = None,
) -> EnvironmentGateReport:
    required = expected_packages_for_plan(plan)
    executable = Path(python_executable) if python_executable is not None else None
    if executable is not None:
        availability = _packages_available_with_python(executable, required)
        missing = tuple(package for package in required if not availability.get(package, False))
    else:
        missing = tuple(package for package in required if not _package_available(package))
    return EnvironmentGateReport(
        ok=not missing,
        action="allow_build" if not missing else "halt_missing_environment",
        required_packages=required,
        missing_packages=missing,
        python_executable=str(python_executable or sys.executable),
    )


def audit_workspace_sovereignty(
    workspace: str | Path,
    plan: RequiredArtifactPlan,
) -> WorkspaceSovereigntyReport:
    root = Path(workspace).resolve()
    allowed = _allowed_paths(plan)
    unplanned: list[str] = []
    if root.exists():
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            if _path_allowed(relative, allowed):
                continue
            unplanned.append(relative)
    return WorkspaceSovereigntyReport(
        ok=not unplanned,
        action="allow_workspace" if not unplanned else "reject_unplanned_workspace_artifacts",
        allowed_paths=tuple(sorted(allowed)),
        unplanned_paths=tuple(sorted(unplanned)),
    )


def environment_gate_to_dict(report: EnvironmentGateReport) -> dict[str, object]:
    return {
        "ok": report.ok,
        "action": report.action,
        "required_packages": list(report.required_packages),
        "missing_packages": list(report.missing_packages),
        "python_executable": report.python_executable,
    }


def workspace_sovereignty_to_dict(report: WorkspaceSovereigntyReport) -> dict[str, object]:
    return {
        "ok": report.ok,
        "action": report.action,
        "allowed_paths": list(report.allowed_paths),
        "unplanned_paths": list(report.unplanned_paths),
    }


def _package_available(package: str) -> bool:
    return importlib.util.find_spec(package) is not None


def _packages_available_with_python(
    python_executable: Path,
    packages: tuple[str, ...],
) -> dict[str, bool]:
    if not python_executable.exists():
        return {package: False for package in packages}
    probe = (
        "import importlib.util, json, sys; "
        "packages = sys.argv[1:]; "
        "print(json.dumps({package: importlib.util.find_spec(package) is not None for package in packages}))"
    )
    try:
        completed = subprocess.run(
            [str(python_executable), "-c", probe, *packages],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return {package: False for package in packages}
    if completed.returncode != 0:
        return {package: False for package in packages}
    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {package: False for package in packages}
    return {package: bool(parsed.get(package)) for package in packages}


def _allowed_paths(plan: RequiredArtifactPlan) -> set[str]:
    return {
        artifact.path
        for artifact in plan.artifacts
    } | set(SUPPORT_FILES.get(plan.project_name, ()))


def _path_allowed(relative: str, allowed: set[str]) -> bool:
    if relative in allowed:
        return True
    if relative.endswith(".pyc") and "/__pycache__/" in f"/{relative}":
        return True
    return any(relative.startswith(prefix) for prefix in ALLOWED_METADATA_PREFIXES)
