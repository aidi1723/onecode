import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.sandbox import (
    SandboxConfig,
    container_argv,
    image_platform_mismatch,
    interpreter_missing,
    run_in_sandbox,
    with_runnable_image,
    _docker_daemon_unavailable,
)
from onecode.kernel.trace import TraceEvent, write_trace_event


VerifierStatus = Literal["passed", "failed", "skipped"]
VerifierFailureKind = Literal["command_failed", "timeout", "exception"]
TAIL_LIMIT = 4096
DEFAULT_VERIFIER_POLICY_PATH = ".onecode/verifier-policy.json"
VERIFIER_POLICY_PRESETS = {
    "python-unittest": {
        "id": "python-unittest",
        "command": [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        "cwd": ".",
        "timeout_ms": 30000,
    },
    "python-compileall": {
        "id": "python-compileall",
        "command": [sys.executable, "-m", "compileall", "src", "tests"],
        "cwd": ".",
        "timeout_ms": 30000,
    },
}

ALLOWED_VERIFIER_COMMANDS = {  # type: ignore
    tuple(preset["command"])  # type: ignore
    for preset in VERIFIER_POLICY_PRESETS.values()
}
PYTHON_EXECUTABLE_NAMES = {"python", "python3", Path(sys.executable).name}
ALLOWED_UNITTEST_FLAGS = frozenset({"-v", "-q", "-f", "--failfast", "-b", "--buffer"})
_UNITTEST_ASSERTIONS = (
    "assertEqual",
    "assertNotEqual",
    "assertTrue",
    "assertFalse",
    "assertIs",
    "assertIsNot",
    "assertIsNone",
    "assertIsNotNone",
    "assertIn",
    "assertNotIn",
    "assertRaises",
    "assertAlmostEqual",
    "assertGreater",
    "assertLess",
    "fail",
)
UNITTEST_GUARD = """
import sys
import unittest
from pathlib import Path
root = Path.cwd()
if (root / "unittest.py").is_file() or (root / "pytest.py").is_file():
    sys.stderr.write("workspace shadow module blocked\\n")
    sys.exit(2)
sys.path.insert(0, str(root))
saved = {name: getattr(unittest.TestCase, name) for name in %s if hasattr(unittest.TestCase, name)}
loader = unittest.TestLoader()
args = sys.argv[1:]
if args[:2] == ["discover", "-s"] and len(args) >= 3:
    suite = loader.discover(args[2])
elif len(args) == 1 and args[0].endswith(".py"):
    suite = loader.discover(str(Path(args[0]).parent), pattern=Path(args[0]).name)
elif len(args) == 1:
    suite = loader.loadTestsFromName(args[0])
else:
    suite = loader.loadTestsFromNames(args)
for name, method in saved.items():
    setattr(unittest.TestCase, name, method)
result = unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
""" % (repr(_UNITTEST_ASSERTIONS),)


def _is_safe_test_target(target: str) -> bool:
    if not isinstance(target, str) or not target:
        return False
    normalized = target.replace("\\", "/")
    if normalized.startswith("-") or ".." in normalized:
        return False
    if re.match(r"^tests/[a-zA-Z0-9_./]+\.py$", normalized):
        return True
    if re.match(r"^tests(\.[a-zA-Z0-9_]+)+$", normalized):
        return True
    return False


def _allowed_python_executables() -> set[Path]:
    allowed = {Path(sys.executable).resolve()}
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found:
            allowed.add(Path(found).resolve())
    return allowed


def _python_executable_allowed(executable: str) -> bool:
    if not executable or "/" in executable or "\\" in executable or Path(executable).is_absolute():
        try:
            return Path(executable).resolve() in _allowed_python_executables()
        except OSError:
            return False
    return Path(executable).name in PYTHON_EXECUTABLE_NAMES


def guarded_unittest_command(command: list[str]) -> list[str]:
    args = list(command[1:])
    if args and args[0] == "-P":
        args = args[1:]
    if args[:2] != ["-m", "unittest"]:
        return command
    return [command[0], "-I", "-c", UNITTEST_GUARD, *args[2:]]


def verifier_command_allowed(command: list[str]) -> bool:
    command_tuple = tuple(command)
    if command_tuple in ALLOWED_VERIFIER_COMMANDS:
        return True
    if not command or not _python_executable_allowed(command[0]):
        return False
    for allowed in ALLOWED_VERIFIER_COMMANDS:
        if not allowed:
            continue
        if _python_executable_allowed(allowed[0]) and tuple(command[1:]) == tuple(allowed[1:]):
            return True
    args = list(command[1:])
    if args and args[0] == "-P":
        args = args[1:]
    if len(args) >= 2 and args[:2] == ["-m", "unittest"]:
        remaining = args[2:]
        targets = [arg for arg in remaining if arg not in ALLOWED_UNITTEST_FLAGS]
        if targets and all(_is_safe_test_target(target) for target in targets):
            if all(arg in ALLOWED_UNITTEST_FLAGS or not arg.startswith("-") for arg in remaining):
                return True
    return False


@dataclass(frozen=True)
class VerifierSpec:
    id: str
    command: list[str]
    cwd: str
    timeout_ms: int

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or self.id == "":
            raise ValueError("verifier id must be a non-empty string")
        if not isinstance(self.command, list) or not self.command:
            raise ValueError("verifier command must be a non-empty string list")
        if not all(isinstance(part, str) and part != "" for part in self.command):
            raise ValueError("verifier command must be a non-empty string list")
        if not isinstance(self.cwd, str) or self.cwd == "":
            raise ValueError("verifier cwd must be a non-empty string")
        if isinstance(self.timeout_ms, bool) or not isinstance(self.timeout_ms, int) or self.timeout_ms <= 0:
            raise ValueError("verifier timeout_ms must be positive")


@dataclass(frozen=True)
class VerifierResult:
    id: str
    status: VerifierStatus
    reason: str | None
    failure_kind: VerifierFailureKind | None
    exit_code: int | None
    duration_ms: int
    stdout_tail: str
    stderr_tail: str
    stdout_sha256: str = ""
    stderr_sha256: str = ""
    cwd: str = ""
    command: list[str] = field(default_factory=list)
    container_id: str | None = None
    container_image: str | None = None
    container_arch: str | None = None

    def __post_init__(self) -> None:
        if not self.stdout_sha256 and self.stdout_tail is not None:
            object.__setattr__(self, "stdout_sha256", hashlib.sha256(self.stdout_tail.encode("utf-8")).hexdigest())
        if not self.stderr_sha256 and self.stderr_tail is not None:
            object.__setattr__(self, "stderr_sha256", hashlib.sha256(self.stderr_tail.encode("utf-8")).hexdigest())
        if not self.cwd:
            object.__setattr__(self, "cwd", ".")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.container_id is None:
            data.pop("container_id", None)
            data.pop("container_image", None)
            data.pop("container_arch", None)
        return data


@dataclass(frozen=True)
class VerifierPolicy:
    specs: dict[str, VerifierSpec]

    def require(self, verifier_id: str) -> VerifierSpec:
        try:
            return self.specs[verifier_id]
        except KeyError as exc:
            raise ValueError(f"unknown verifier id: {verifier_id}") from exc


def load_verifier_policy(path: Path) -> VerifierPolicy:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError("invalid verifier policy: missing_file") from exc
    except json.JSONDecodeError as exc:
        raise ValueError("invalid verifier policy: invalid_json") from exc
    if not isinstance(data, dict):
        raise ValueError("invalid verifier policy: root must be an object")
    verifiers = data.get("verifiers")
    if not isinstance(verifiers, list):
        raise ValueError("invalid verifier policy: verifiers must be a list")
    specs: dict[str, VerifierSpec] = {}
    for index, value in enumerate(verifiers, start=1):
        if not isinstance(value, dict):
            raise ValueError(f"invalid verifier {index}: verifier must be an object")
        unknown_fields = sorted(set(value) - {"id", "command", "cwd", "timeout_ms"})
        if unknown_fields:
            raise ValueError(f"invalid verifier {index}: unknown fields: {', '.join(unknown_fields)}")
        spec = VerifierSpec(
            id=value.get("id", ""),
            command=value.get("command", []),
            cwd=value.get("cwd", ""),
            timeout_ms=value.get("timeout_ms", 0),
        )
        if spec.id in specs:
            raise ValueError(f"duplicate verifier id: {spec.id}")
        if not verifier_command_allowed(spec.command):
            raise ValueError(f"invalid verifier {index}: verifier command is not allowed")
        specs[spec.id] = spec
    return VerifierPolicy(specs=specs)


def verifier_policy_data(preset_ids: list[str] | None = None) -> dict[str, Any]:
    selected_ids = preset_ids or ["python-unittest"]
    verifiers = []
    seen = set()
    for preset_id in selected_ids:
        if preset_id not in VERIFIER_POLICY_PRESETS:
            raise ValueError(f"unknown verifier policy preset: {preset_id}")
        if preset_id in seen:
            raise ValueError(f"duplicate verifier policy preset: {preset_id}")
        seen.add(preset_id)
        verifiers.append(dict(VERIFIER_POLICY_PRESETS[preset_id]))
    return {"verifiers": verifiers}


def verifier_policy_presets_summary() -> dict[str, Any]:
    return {
        "presets": [
            {
                "id": preset_id,
                "command": list(preset["command"]),  # type: ignore
                "cwd": preset["cwd"],
                "timeout_ms": preset["timeout_ms"],
            }
            for preset_id, preset in sorted(VERIFIER_POLICY_PRESETS.items())
        ]
    }


def workspace_relative_path(workspace: Path, path: Path) -> str:
    try:
        return path.relative_to(workspace).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_policy_output_path(workspace: Path, output: str) -> Path:
    workspace_root = workspace.resolve()
    output_path = Path(output)
    resolved = output_path.resolve() if output_path.is_absolute() else (workspace_root / output_path).resolve()
    if resolved != workspace_root and workspace_root not in resolved.parents:
        raise ValueError("verifier policy output outside workspace")
    return resolved


def write_verifier_policy(
    workspace: Path,
    output: str = DEFAULT_VERIFIER_POLICY_PATH,
    preset_ids: list[str] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    workspace_root = workspace.resolve()
    policy_path = resolve_policy_output_path(workspace_root, output)
    if policy_path.exists() and not force:
        raise ValueError("verifier policy output already exists")
    data = verifier_policy_data(preset_ids)
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    load_verifier_policy(policy_path)
    return {
        "status": "completed",
        "path": workspace_relative_path(workspace_root, policy_path),
        "verifier_ids": [verifier["id"] for verifier in data["verifiers"]],
    }


def resolve_verifier_cwd(workspace: Path, cwd: str) -> Path:
    workspace_root = workspace.resolve()
    resolved = (workspace_root / cwd).resolve()
    if resolved != workspace_root and workspace_root not in resolved.parents:
        raise ValueError("verifier cwd outside workspace")
    return resolved


def tail_text(value: bytes) -> str:
    return value[-TAIL_LIMIT:].decode("utf-8", errors="replace")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def run_verifier(
    workspace: Path,
    spec: VerifierSpec,
    trace_path: Path | None = None,
    trace_id: str | None = None,
    run_id: str | None = None,
    sandbox_config: SandboxConfig | None = None,
) -> VerifierResult:
    _ = resolve_verifier_cwd(workspace, spec.cwd)
    started_at = time.monotonic()
    resolved_trace_id = trace_id or run_id or "verifier"
    resolved_run_id = run_id or resolved_trace_id
    if trace_path is not None:
        write_trace_event(
            trace_path,
            TraceEvent(
                trace_id=resolved_trace_id,
                run_id=resolved_run_id,
                span_id=f"verifier-{spec.id}",
                parent_span_id="run",
                event_type="verifier_started",
                status="started",
                payload={"verifier_id": spec.id, "command": list(spec.command), "cwd": spec.cwd},
            ),
        )
    stdout = b""
    stderr = b""
    try:
        if sandbox_config is not None:
            try:
                sandbox_config = with_runnable_image(sandbox_config)
                if image_platform_mismatch(sandbox_config.image):
                    stdout = b""
                    stderr = b"image_platform_mismatch"
                    status: VerifierStatus = "failed"
                    reason: str | None = "image_platform_mismatch"
                    failure_kind: VerifierFailureKind | None = "exception"
                    exit_code: int | None = None
                else:
                    completed = run_in_sandbox(
                        sandbox_config,
                        container_argv(guarded_unittest_command(list(spec.command))),
                    )
                    stderr_str = completed.stderr if isinstance(completed.stderr, str) else completed.stderr.decode("utf-8", errors="replace")
                    if completed.returncode != 0 and _docker_daemon_unavailable(stderr_str):
                        stdout = b""
                        stderr = b"Sandbox required but Docker daemon is unavailable."
                        status = "failed"
                        reason = "sandbox_required"
                        failure_kind = "exception"
                        exit_code = None
                    elif interpreter_missing(completed.returncode, stderr_str):
                        stdout = b""
                        stderr = stderr_str.encode("utf-8")
                        status = "failed"
                        reason = "interpreter_not_found"
                        failure_kind = "exception"
                        exit_code = completed.returncode
                    else:
                        stdout = completed.stdout.encode("utf-8") if isinstance(completed.stdout, str) else completed.stdout
                        stderr = stderr_str.encode("utf-8")
                        exit_code = completed.returncode
                        if completed.returncode == 0:
                            if "-m" in spec.command and "unittest" in spec.command:
                                stdout_str = completed.stdout if isinstance(completed.stdout, str) else completed.stdout.decode("utf-8", errors="replace")
                                combined = stdout_str + "\n" + stderr_str
                                if re.search(r"NO TESTS RAN", combined) or re.search(r"\bRan 0 tests?\b", combined):
                                    status = "skipped"
                                    reason = "no_unittest_collected"
                                    failure_kind = None
                                elif not (re.search(r"Ran ([1-9]\d*) tests?", combined) and re.search(r"\bOK\b", combined)):
                                    status = "failed"
                                    reason = "verifier_empty_or_aborted"
                                    failure_kind = "command_failed"
                                else:
                                    status = "passed"
                                    reason = None
                                    failure_kind = None
                            else:
                                status = "passed"
                                reason = None
                                failure_kind = None
                        else:
                            status = "failed"
                            reason = "verifier_failed"
                            failure_kind = "command_failed"
            except FileNotFoundError:
                stdout = b""
                stderr = b"Sandbox required but Docker is not installed on host system."
                status = "failed"
                reason = "sandbox_required"
                failure_kind = "exception"
                exit_code = None
        else:
            stdout = b""
            stderr = b"Verifier execution halted: Sandbox configuration is required to execute verifier checks safely. Execution on the bare host is prohibited."
            status = "failed"
            reason = "sandbox_required"
            failure_kind = "exception"
            exit_code = None
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, bytes) else b""
        stderr = exc.stderr if isinstance(exc.stderr, bytes) else b""
        status = "failed"
        reason = "verifier_timeout"
        failure_kind = "timeout"
        exit_code = None
    duration_ms = int((time.monotonic() - started_at) * 1000)
    result = VerifierResult(
        id=spec.id,
        status=status,
        reason=reason,
        failure_kind=failure_kind,
        exit_code=exit_code,
        duration_ms=duration_ms,
        stdout_tail=tail_text(stdout),
        stderr_tail=tail_text(stderr),
        stdout_sha256=sha256_bytes(stdout),
        stderr_sha256=sha256_bytes(stderr),
        cwd=spec.cwd,
        command=list(spec.command),
    )
    if trace_path is not None:
        write_trace_event(
            trace_path,
            TraceEvent(
                trace_id=resolved_trace_id,
                run_id=resolved_run_id,
                span_id=f"verifier-{spec.id}",
                parent_span_id="run",
                event_type="verifier_completed",
                status=result.status,
                payload={
                    "verifier_id": spec.id,
                    "reason": result.reason,
                    "failure_kind": result.failure_kind,
                    "exit_code": result.exit_code,
                    "stdout_sha256": result.stdout_sha256,
                    "stderr_sha256": result.stderr_sha256,
                },
                duration_ms=result.duration_ms,
            ),
        )
    return result


def validate_selected_verifiers(workspace: Path, policy: VerifierPolicy, verifier_ids: list[str]) -> list[VerifierSpec]:
    specs = [policy.require(verifier_id) for verifier_id in verifier_ids]
    for spec in specs:
        resolve_verifier_cwd(workspace, spec.cwd)
    return specs


def targeted_test_for_path(workspace: Path, modified_path: str) -> str | None:
    if not isinstance(modified_path, str) or not modified_path:
        return None
    try:
        path_obj = Path(modified_path)
        if path_obj.is_absolute():
            normalized = path_obj.resolve().relative_to(workspace.resolve()).as_posix()
        else:
            normalized = modified_path.replace("\\", "/")
    except ValueError:
        return None
    if ".." in normalized or normalized.startswith("/"):
        return None
    if normalized.startswith("tests/") and normalized.endswith(".py"):
        target = workspace / normalized
        return normalized if target.is_file() else None
    if normalized.startswith("src/") and normalized.endswith(".py"):
        stem = Path(normalized).stem
        candidate = f"tests/test_{stem}.py"
        target = workspace / candidate
        if target.is_file():
            return candidate
    return None


def run_two_stage_verifier(
    workspace: Path,
    targeted_test: str | None = None,
    trace_path: Path | None = None,
    trace_id: str | None = None,
    run_id: str | None = None,
    sandbox_config: SandboxConfig | None = None,
    timeout_ms: int = 120_000,
) -> tuple[VerifierResult, list[VerifierResult]]:
    results: list[VerifierResult] = []
    if targeted_test:
        stage1_spec = VerifierSpec(
            id="python-unittest-targeted",
            command=["python3", "-m", "unittest", targeted_test],
            cwd=".",
            timeout_ms=min(30_000, timeout_ms),
        )
        stage1_result = run_verifier(
            workspace,
            stage1_spec,
            trace_path=trace_path,
            trace_id=trace_id,
            run_id=run_id,
            sandbox_config=sandbox_config,
        )
        results.append(stage1_result)
        if stage1_result.status != "passed":
            return stage1_result, results

    import os
    import shlex

    host_cmd_env = os.environ.get("ONECODE_HOST_VERIFIER_CMD")
    has_host_script = (workspace / "verifier.py").is_file()
    if host_cmd_env:
        stage2_cmd = shlex.split(host_cmd_env)
        stage2_id = "host-verifier"
    elif has_host_script and not (workspace / "tests").is_dir():
        stage2_cmd = ["python3", "verifier.py"]
        stage2_id = "host-verifier"
    else:
        stage2_cmd = ["python3", "-m", "unittest", "discover", "-s", "tests"]
        stage2_id = "python-unittest"

    stage2_spec = VerifierSpec(
        id=stage2_id,
        command=stage2_cmd,
        cwd=".",
        timeout_ms=timeout_ms,
    )
    stage2_result = run_verifier(
        workspace,
        stage2_spec,
        trace_path=trace_path,
        trace_id=trace_id,
        run_id=run_id,
        sandbox_config=sandbox_config,
    )
    results.append(stage2_result)
    return stage2_result, results


SHADOWED_STDLIB_MODULES = frozenset({
    "json", "os", "sys", "subprocess", "pathlib", "shutil",
    "unittest", "pytest", "io", "re", "time", "builtins", "site",
})


def audit_workspace_for_sys_path_hijacking(workspace: Path) -> list[str]:
    """Reject workspace-root files that would shadow the verifier's standard library imports."""
    violations: list[str] = []
    if not workspace.is_dir():
        return violations
    for name in SHADOWED_STDLIB_MODULES:
        for suffix in (".py", ".pyw", ".so"):
            candidate = workspace / f"{name}{suffix}"
            if candidate.is_file():
                violations.append(f"Rogue standard library module shadowing '{candidate.name}' in workspace root")
        package = workspace / name
        if package.is_dir() and (package / "__init__.py").is_file():
            violations.append(f"Rogue package shadowing standard library '{name}' in workspace root")
    return violations


def assertion_counts(detail: dict[str, Any]) -> tuple[int, int] | None:
    for passed_key, total_key in (("tests_passed", "tests_total"), ("passed", "total")):
        passed = detail.get(passed_key)
        total = detail.get(total_key)
        if isinstance(passed, bool) or isinstance(total, bool):
            continue
        if isinstance(passed, int) and isinstance(total, int):
            return passed, total
    return None


def full_score_problem(returncode: int | None, reward: float, detail: dict[str, Any]) -> str:
    """Return a forgery explanation when a positive or full score disagrees with the verifier evidence."""
    tests = detail.get("tests")
    failed_case = isinstance(tests, list) and any(isinstance(item, dict) and not item.get("passed") for item in tests)
    counts = assertion_counts(detail)
    if returncode not in (None, 0) and reward > 0.0:
        return "reward.txt claimed a positive score but the verifier exited non-zero"
    if returncode == 0 and abs(reward - 1.0) < 1e-6:
        if counts is None or counts[1] <= 0 or counts[0] != counts[1]:
            return "a full score requires tests_passed == tests_total and tests_total > 0"
        if isinstance(tests, list) and (not tests or len(tests) != counts[1] or failed_case):
            return "reward.json tests do not match the claimed assertion counts"
    return ""


def apply_host_reward_policy(
    *,
    returncode: int | None,
    reward: object,
    detail: dict[str, Any],
    timed_out: bool,
) -> tuple[object, str | None, VerifierFailureKind | None]:
    if timed_out:
        return reward, "verifier_timeout", "timeout"
    if isinstance(reward, (int, float)) and not isinstance(reward, bool):
        problem = full_score_problem(returncode, float(reward), detail)
        if problem:
            return 0.0, "reward_forgery_detected", "command_failed"
    if returncode == 0 and reward == 1.0:
        return reward, None, None
    return reward, "verifier_failed", "command_failed"


def _read_grade_artifacts(log_dir: Path) -> tuple[object, dict[str, Any], str]:
    reward: object = "ungraded"
    detail: dict[str, Any] = {}
    raw_json = ""
    reward_file = log_dir / "reward.txt"
    if reward_file.is_file():
        text = reward_file.read_text(encoding="utf-8").strip()
        try:
            reward = float(text)
        except ValueError:
            reward = text or "ungraded"
    reward_json_file = log_dir / "reward.json"
    if reward_json_file.is_file():
        try:
            raw_json = reward_json_file.read_text(encoding="utf-8").strip()
            parsed = json.loads(raw_json) if raw_json else None
        except (OSError, json.JSONDecodeError):
            parsed = None
        if isinstance(parsed, dict):
            detail = parsed
    return reward, detail, raw_json


def run_host_verifier(
    workspace: Path,
    verifier_path: Path | str,
    timeout_seconds: float = 180.0,
    sandbox_config: Any | None = None,
) -> tuple[VerifierResult, object]:
    """Execute an external benchmark verifier on host or in container with isolated WORKSPACE and LOG_DIR.

    Returns (VerifierResult, host_reward).
    Strict passing condition: proc.returncode == 0 and host_reward == 1.0.
    """
    verifier = Path(verifier_path).expanduser().resolve()
    violations = audit_workspace_for_sys_path_hijacking(workspace)
    if violations:
        detail_text = "; ".join(violations)
        result = VerifierResult(
            id="host-verifier",
            status="failed",
            reason="sys_path_hijack_detected",
            failure_kind="exception",
            exit_code=1,
            duration_ms=0,
            stdout_tail="",
            stderr_tail=detail_text,
            stdout_sha256=sha256_bytes(b""),
            stderr_sha256=sha256_bytes(detail_text.encode("utf-8")),
            cwd=str(workspace),
            command=[sys.executable, str(verifier)],
        )
        return result, 0.0
    if not verifier.is_file():
        result = VerifierResult(
            id="host-verifier",
            status="failed",
            reason="host_verifier_not_found",
            failure_kind="exception",
            exit_code=None,
            duration_ms=0,
            stdout_tail="",
            stderr_tail=f"Verifier file not found: {verifier}",
            stdout_sha256=sha256_bytes(b""),
            stderr_sha256=sha256_bytes(f"Verifier file not found: {verifier}".encode("utf-8")),
            cwd=str(workspace),
            command=[sys.executable, str(verifier)],
        )
        return result, "ungraded"

    if sandbox_config is not None:
        return _run_container_verifier(
            workspace=workspace,
            verifier=verifier,
            sandbox_config=sandbox_config,
            timeout_seconds=timeout_seconds,
        )
    return _run_native_host_verifier(
        workspace=workspace,
        verifier=verifier,
        timeout_seconds=timeout_seconds,
    )


def _run_native_host_verifier(
    workspace: Path,
    verifier: Path,
    timeout_seconds: float = 180.0,
) -> tuple[VerifierResult, object]:
    import tempfile

    log_dir = Path(tempfile.mkdtemp(prefix="oc-host-grade-"))
    shim = Path(tempfile.mkdtemp(prefix="oc-host-shim-"))
    try:
        try:
            (shim / "python").symlink_to(sys.executable)
            (shim / "python3").symlink_to(sys.executable)
        except OSError:
            pass

        env = os.environ.copy()
        env["WORKSPACE"] = str(workspace.resolve())
        env["LOG_DIR"] = str(log_dir)
        env["PATH"] = str(shim) + os.pathsep + env.get("PATH", "")

        started = time.monotonic()
        try:
            proc = subprocess.run(
                [sys.executable, str(verifier)],
                cwd=str(workspace.resolve()),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            duration_ms = max(0, int((time.monotonic() - started) * 1000))
            returncode = proc.returncode
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            duration_ms = max(0, int((time.monotonic() - started) * 1000))
            returncode = None
            stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", "replace")
            stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", "replace")
            timed_out = True

        reward, detail, raw_json = _read_grade_artifacts(log_dir)
        if raw_json and raw_json not in stdout:
            stdout = raw_json + "\n" + stdout
        reward, reason, failure_kind = apply_host_reward_policy(
            returncode=returncode,
            reward=reward,
            detail=detail,
            timed_out=timed_out,
        )

        stdout_bytes = stdout.encode("utf-8", errors="replace")
        stderr_bytes = stderr.encode("utf-8", errors="replace")
        checked = VerifierResult(
            id="host-verifier",
            status="passed" if reason is None else "failed",
            reason=reason,
            failure_kind=failure_kind,
            exit_code=returncode,
            duration_ms=duration_ms,
            stdout_tail=tail_text(stdout_bytes),
            stderr_tail=tail_text(stderr_bytes),
            stdout_sha256=sha256_bytes(stdout_bytes),
            stderr_sha256=sha256_bytes(stderr_bytes),
            cwd=str(workspace.resolve()),
            command=[sys.executable, str(verifier)],
        )
        return checked, reward
    finally:
        shutil.rmtree(shim, ignore_errors=True)
        shutil.rmtree(log_dir, ignore_errors=True)


def _build_container_verifier_cmd(
    workspace: Path,
    verifier: Path,
    cfg: Any,
    log_dir: Path,
    cidfile: Path,
) -> list[str]:
    ws_resolved = workspace.resolve()
    verifier_resolved = verifier.resolve()
    mounts = [
        "--mount",
        f"type=bind,src={ws_resolved.as_posix()},dst=/workspace",
        "--mount",
        f"type=bind,src={log_dir.resolve().as_posix()},dst=/log_dir",
    ]
    if verifier_resolved.is_relative_to(ws_resolved):
        container_verifier = f"/workspace/{verifier_resolved.relative_to(ws_resolved).as_posix()}"
    else:
        mounts.extend(
            [
                "--mount",
                f"type=bind,src={verifier_resolved.as_posix()},dst=/verifier/verifier.py,readonly",
            ]
        )
        container_verifier = "/verifier/verifier.py"

    for name in (".git", ".github", ".onecode", "tests"):
        source = ws_resolved / name
        if source.is_dir():
            mounts.extend(
                [
                    "--mount",
                    f"type=bind,src={source.as_posix()},dst=/workspace/{name},readonly",
                ]
            )

    user_flag = []
    if hasattr(os, "getuid") and hasattr(os, "getgid"):
        user_flag = ["--user", f"{os.getuid()}:{os.getgid()}"]

    return [
        "docker",
        "run",
        "--rm",
        "--cidfile",
        cidfile.as_posix(),
        "--network",
        cfg.network,
        "--memory",
        cfg.memory,
        "--cpus",
        cfg.cpus,
        "--pids-limit",
        str(cfg.pids_limit),
        "--tmpfs",
        cfg.tmpfs,
        "--security-opt",
        "no-new-privileges",
        *user_flag,
        *mounts,
        "--env",
        "WORKSPACE=/workspace",
        "--env",
        "LOG_DIR=/log_dir",
        "--env",
        "PYTHONSAFEPATH=1",
        "--workdir",
        "/workspace",
        cfg.image,
        "python3",
        container_verifier,
    ]


def _run_container_verifier(
    workspace: Path,
    verifier: Path,
    sandbox_config: Any,
    timeout_seconds: float = 180.0,
) -> tuple[VerifierResult, object]:
    from onecode.kernel.sandbox import _image_architecture

    if shutil.which("docker") is None:
        return VerifierResult(
            id="host-verifier",
            status="failed",
            reason="docker_not_found",
            failure_kind="exception",
            exit_code=None,
            duration_ms=0,
            stdout_tail="",
            stderr_tail="Docker executable not found",
            cwd=str(workspace),
            command=["docker", "run"],
        ), "ungraded"

    cfg = with_runnable_image(sandbox_config)
    if image_platform_mismatch(cfg.image):
        return VerifierResult(
            id="host-verifier",
            status="failed",
            reason="image_platform_mismatch",
            failure_kind="exception",
            exit_code=None,
            duration_ms=0,
            stdout_tail="",
            stderr_tail=f"image platform mismatch: {cfg.image}",
            cwd=str(workspace),
            command=["docker", "run"],
        ), "ungraded"

    import tempfile

    log_dir = Path(tempfile.mkdtemp(prefix="oc-container-grade-"))
    cidfile = log_dir / "container.cid"
    try:
        try:
            os.chmod(log_dir, 0o777)
        except OSError:
            pass

        docker_cmd = _build_container_verifier_cmd(workspace, verifier, cfg, log_dir, cidfile)

        started = time.monotonic()
        try:
            proc = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            duration_ms = max(0, int((time.monotonic() - started) * 1000))
            returncode = proc.returncode
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            duration_ms = max(0, int((time.monotonic() - started) * 1000))
            returncode = None
            stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", "replace")
            stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", "replace")
            timed_out = True

        container_id: str | None = None
        container_image: str | None = None
        container_arch: str | None = None
        if cidfile.is_file():
            cid_text = cidfile.read_text(encoding="utf-8").strip()
            if len(cid_text) == 64 and all(c in "0123456789abcdefABCDEF" for c in cid_text):
                container_id = cid_text.lower()
                container_image = cfg.image
                container_arch = _image_architecture(cfg.image)

        if not timed_out and returncode != 0 and _docker_daemon_unavailable(stderr):
            return VerifierResult(
                id="host-verifier",
                status="failed",
                reason="docker_daemon_unavailable",
                failure_kind="exception",
                exit_code=None,
                duration_ms=duration_ms,
                stdout_tail=tail_text(stdout.encode("utf-8", errors="replace")),
                stderr_tail=tail_text(stderr.encode("utf-8", errors="replace")),
                cwd=str(workspace.resolve()),
                command=docker_cmd,
            ), "ungraded"

        reward, detail, raw_json = _read_grade_artifacts(log_dir)
        if raw_json and raw_json not in stdout:
            stdout = raw_json + "\n" + stdout
        reward, reason, failure_kind = apply_host_reward_policy(
            returncode=returncode,
            reward=reward,
            detail=detail,
            timed_out=timed_out,
        )

        stdout_bytes = stdout.encode("utf-8", errors="replace")
        stderr_bytes = stderr.encode("utf-8", errors="replace")
        checked = VerifierResult(
            id="host-verifier",
            status="passed" if reason is None else "failed",
            reason=reason,
            failure_kind=failure_kind,
            exit_code=returncode,
            duration_ms=duration_ms,
            stdout_tail=tail_text(stdout_bytes),
            stderr_tail=tail_text(stderr_bytes),
            stdout_sha256=sha256_bytes(stdout_bytes),
            stderr_sha256=sha256_bytes(stderr_bytes),
            cwd=str(workspace.resolve()),
            command=docker_cmd,
            container_id=container_id,
            container_image=container_image,
            container_arch=container_arch,
        )
        return checked, reward
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def task_status_from_results(asset_result: dict[str, Any], verifier_results: list[VerifierResult]) -> dict[str, Any]:
    status_codes = [
        asset.get("raw_status_code")
        for asset in asset_result.get("assets", [])
        if isinstance(asset, dict)
        and isinstance(asset.get("raw_status_code"), int)
        and not isinstance(asset.get("raw_status_code"), bool)
    ]
    for result in verifier_results:
        status_codes.append(
            IchingKernel.classify_outcome(
                "completed" if result.status == "passed" else "halted",
                result.reason,
            )
        )
    entropy = IchingKernel.entropy_regulated_status(status_codes)  # type: ignore
    status_code = int(entropy["status_code"])
    transition = IchingKernel.transition(status_code)
    return {
        "task_status_code": status_code,
        "task_transition_action": transition.action,
        "task_transition_reason": transition.reason,
        "task_dispatch_decision": IchingKernel.dispatch_decision(transition),
        "task_entropy": entropy["entropy"],
        "task_entropy_decision": entropy["decision"],
        "task_entropy_reason": entropy.get("reason"),
    }
