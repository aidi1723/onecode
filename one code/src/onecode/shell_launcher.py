from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, TextIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from onecode.kernel.model_config import read_model_config, write_private_text
from onecode.shell_state import (
    load_or_create_shell_secrets,
    redact_runtime_text,
    write_runtime_status,
)


DEFAULT_LOCAL_EMAIL = "onecode@local.test"
DEFAULT_LOCAL_PASSWORD = "OneCode123!"
DEFAULT_ONECODE_PORT = 19080
DEFAULT_LIBRECHAT_PORT = 14080
DEFAULT_MONGO_PORT = 39017
EXPECTED_LIBRECHAT_VERSION = "v0.8.7"
EXPECTED_LIBRECHAT_COMMIT = "9e74cc0e57b395926122bd4062c1fcedc48ed465"
DEFAULT_SERVICE_LOG_MAX_BYTES = 2_000_000


@dataclass(frozen=True)
class ShellLaunchConfig:
    onecode_root: Path
    librechat_dir: Path
    onecode_host: str
    onecode_port: int
    librechat_host: str
    librechat_port: int
    mongo_port: int
    api_token: str
    workspace_root: Path
    runtime_state_root: Path | None = None
    email: str = DEFAULT_LOCAL_EMAIL
    password: str = DEFAULT_LOCAL_PASSWORD
    open_browser: bool = True
    show_credentials: bool = False
    model_timeout_seconds: float = 60.0


@dataclass(frozen=True)
class ManagedProcess:
    name: str
    process: Any
    log_path: Path
    pump_thread: threading.Thread | None


def shell_state_root(config: ShellLaunchConfig) -> Path:
    return config.runtime_state_root or config.workspace_root


def default_librechat_dir(project_root: Path) -> Path:
    return project_root.resolve().parent / "onecode-librechat"


def build_librechat_env(config: ShellLaunchConfig, base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(base_env or os.environ)
    for key in list(env):
        if key.startswith("ONEWORD_") or key.startswith("OPENAI_"):
            env.pop(key)
    secret_keys = ("JWT_SECRET", "JWT_REFRESH_SECRET", "CREDS_KEY", "CREDS_IV")
    stored_secrets = None
    if any(not env.get(key) for key in secret_keys):
        stored_secrets = load_or_create_shell_secrets(shell_state_root(config))
    env.update(
        {
            "APP_TITLE": "OneCode",
            "CUSTOM_FOOTER": "OneCode",
            "ENDPOINTS": "custom",
            "HOST": config.librechat_host,
            "PORT": str(config.librechat_port),
            "DOMAIN_CLIENT": f"http://{config.librechat_host}:{config.librechat_port}",
            "DOMAIN_SERVER": f"http://{config.librechat_host}:{config.librechat_port}",
            "MONGO_URI": f"mongodb://127.0.0.1:{config.mongo_port}/LibreChat",
            "ONECODE_API_BASE_URL": f"http://{config.onecode_host}:{config.onecode_port}/v1",
            "ONECODE_API_TOKEN": config.api_token,
            "ONECODE_ALLOWED_WORKSPACE_ROOTS": str(config.workspace_root),
            "ALLOW_EMAIL_LOGIN": "true",
            "ALLOW_REGISTRATION": "true",
            "ALLOW_UNVERIFIED_EMAIL_LOGIN": "true",
            "LOGIN_WINDOW": "1",
            "LOGIN_MAX": "100",
            "JWT_SECRET": env.get("JWT_SECRET")
            or stored_secrets.jwt_secret,
            "JWT_REFRESH_SECRET": env.get("JWT_REFRESH_SECRET")
            or stored_secrets.jwt_refresh_secret,
            "CREDS_KEY": env.get("CREDS_KEY") or stored_secrets.creds_key,
            "CREDS_IV": env.get("CREDS_IV") or stored_secrets.creds_iv,
            "MEILI_NO_SYNC": "true",
            "CONFIG_PATH": str(runtime_config_path(config)),
        }
    )
    return env


def runtime_config_path(config: ShellLaunchConfig) -> Path:
    state_root = config.runtime_state_root or config.workspace_root
    return state_root / "librechat.onecode.yaml"


def build_runtime_config(config: ShellLaunchConfig) -> Path:
    path = runtime_config_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "version: 1.3.11",
                "cache: true",
                "",
                "interface:",
                "  customWelcome: 'OneCode：可信任的工业级 AI 内核'",
                "  modelSelect: true",
                "  parameters: true",
                "  presets: true",
                "  prompts:",
                "    use: true",
                "    create: true",
                "    share: false",
                "    public: false",
                "  bookmarks: true",
                "  multiConvo: true",
                "  agents:",
                "    use: true",
                "    create: false",
                "    share: false",
                "    public: false",
                "  marketplace:",
                "    use: false",
                "  fileCitations: true",
                "",
                "endpoints:",
                "  allowedAddresses:",
                f"    - 'host.docker.internal:{config.onecode_port}'",
                f"    - '127.0.0.1:{config.onecode_port}'",
                f"    - 'localhost:{config.onecode_port}'",
                "  custom:",
                "    - name: 'OneCode'",
                "      apiKey: '${ONECODE_API_TOKEN}'",
                "      baseURL: '${ONECODE_API_BASE_URL}'",
                "      models:",
                "        default: ['onecode-agent']",
                "        fetch: false",
                "      titleConvo: true",
                "      titleModel: 'onecode-agent'",
                "      summarize: false",
                "      modelDisplayLabel: 'OneCode'",
                "      dropParams: ['stop', 'user', 'frequency_penalty', 'presence_penalty']",
                "      addParams:",
                "        maxRetries: 0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def build_onecode_env(config: ShellLaunchConfig, base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(base_env or os.environ)
    src_path = str(config.onecode_root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    env["ONECODE_API_TOKEN"] = config.api_token
    env["ONECODE_WORKSPACE_ROOT"] = str(config.workspace_root)
    env["ONECODE_ALLOWED_WORKSPACE_ROOTS"] = str(config.workspace_root)
    env["ONECODE_MODEL_TIMEOUT_SECONDS"] = str(config.model_timeout_seconds)
    env["ONECODE_REQUIRE_EXPLICIT_TASK_WORKSPACE"] = "true"
    if env.get("OPENAI_BASE_URL") and not env.get("ONECODE_MODEL_ENDPOINT"):
        env["ONECODE_MODEL_ENDPOINT"] = env["OPENAI_BASE_URL"]
        env["ONECODE_MODEL_PROVIDER"] = "chat"
    if env.get("OPENAI_MODEL") and not env.get("ONECODE_MODEL"):
        env["ONECODE_MODEL"] = env["OPENAI_MODEL"]
    return env


def process_is_running(record: ManagedProcess) -> bool:
    return record.process.poll() is None


def wait_for_url(url: str, timeout_seconds: float = 30) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urlopen(Request(url, headers={"accept": "application/json"}), timeout=2):
                return True
        except (OSError, URLError):
            time.sleep(0.5)
    return False


def check_url(url: str, *, timeout_seconds: float = 2) -> dict[str, object]:
    try:
        with urlopen(Request(url, headers={"accept": "application/json"}), timeout=timeout_seconds) as response:
            return {"url": url, "ok": True, "status": response.status}
    except HTTPError as exc:
        return {"url": url, "ok": False, "status": exc.code, "error": str(exc)}
    except (OSError, URLError) as exc:
        return {"url": url, "ok": False, "status": None, "error": str(exc)}


def check_tcp(host: str, port: int, *, timeout_seconds: float = 2) -> dict[str, object]:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return {"host": host, "port": port, "ok": True}
    except OSError as exc:
        return {"host": host, "port": port, "ok": False, "error": str(exc)}


def mongo_command(config: ShellLaunchConfig) -> list[str]:
    db_path = shell_state_root(config) / "mongo"
    db_path.mkdir(parents=True, exist_ok=True, mode=0o700)
    db_path.chmod(0o700)
    node_script = (
        "const { MongoMemoryServer } = require('mongodb-memory-server');"
        "let server;"
        "const stop = async () => {"
        "if (server) await server.stop({ doCleanup: false });"
        "process.exit(0);"
        "};"
        "MongoMemoryServer.create({ instance: {"
        "ip: '127.0.0.1',"
        f"port: {config.mongo_port},"
        "dbName: 'LibreChat',"
        f"dbPath: {json.dumps(str(db_path))}"
        " } }).then((value) => {"
        "server = value;"
        "process.on('SIGINT', stop);"
        "process.on('SIGTERM', stop);"
        "setInterval(() => {}, 1 << 30);"
        "}).catch((error) => { console.error(error); process.exit(1); });"
    )
    return ["node", "-e", node_script]


def librechat_provenance(config: ShellLaunchConfig) -> dict[str, object]:
    package_path = config.librechat_dir / "package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    version = package.get("version") if isinstance(package, dict) else None
    if version != EXPECTED_LIBRECHAT_VERSION:
        raise RuntimeError(
            f"LibreChat version must be {EXPECTED_LIBRECHAT_VERSION}: {version!r}"
        )
    head = subprocess.run(
        ["git", "-C", str(config.librechat_dir), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    if head.returncode != 0 or not head.stdout.strip():
        raise RuntimeError("unable to resolve LibreChat HEAD commit")
    ancestor = subprocess.run(
        [
            "git",
            "-C",
            str(config.librechat_dir),
            "merge-base",
            "--is-ancestor",
            EXPECTED_LIBRECHAT_COMMIT,
            "HEAD",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if ancestor.returncode != 0:
        raise RuntimeError("LibreChat v0.8.7 is not an ancestor of the shell HEAD")
    return {
        "version": version,
        "directory": str(config.librechat_dir),
        "community_base_commit": EXPECTED_LIBRECHAT_COMMIT,
        "head_commit": head.stdout.strip(),
        "community_base_is_ancestor": True,
    }


def _version_tuple(value: str) -> tuple[int, ...]:
    match = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", value)
    if match is None:
        raise RuntimeError(f"unable to parse command version: {value!r}")
    return tuple(int(part or 0) for part in match.groups())


def _resolved_command_version(name: str) -> tuple[str, str]:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"required executable not found: {name}")
    completed = subprocess.run(
        [path, "--version"],
        text=True,
        capture_output=True,
        check=False,
    )
    output = (completed.stdout or completed.stderr).strip()
    if completed.returncode != 0 or not output:
        raise RuntimeError(f"unable to read {name} version")
    return path, output


def port_is_available(host: str, port: int) -> bool:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    try:
        with socket.socket(family, socket.SOCK_STREAM) as candidate:
            candidate.bind((host, port))
        return True
    except OSError:
        return False


def model_config_preflight() -> tuple[dict[str, object], list[str]]:
    config = read_model_config()
    summary = {
        "configured": bool(config.get("configured")),
        "provider": config.get("provider"),
        "endpoint": config.get("endpoint"),
        "model": config.get("model"),
        "api_key_configured": bool(config.get("api_key_configured")),
    }
    warnings = []
    if not summary["configured"]:
        warnings.append(
            "model provider is not configured; configure it in the OneCode Console"
        )
    return summary, warnings


def preflight_shell(config: ShellLaunchConfig) -> dict[str, object]:
    if sys.version_info < (3, 11):
        raise RuntimeError("Python 3.11 or newer is required")
    require_path(config.onecode_root / "src" / "onecode", "OneCode source package")
    require_path(config.librechat_dir / "package.json", "LibreChat shell package")
    node_path, node_version = _resolved_command_version("node")
    npm_path, npm_version = _resolved_command_version("npm")
    if _version_tuple(node_version) < (20, 19, 0):
        raise RuntimeError("Node 20.19 or newer is required")
    if _version_tuple(npm_version)[0] != 11:
        raise RuntimeError("npm major version 11 is required")
    provenance = librechat_provenance(config)
    state_root = shell_state_root(config)
    state_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    state_root.chmod(0o700)
    for name, host, port in (
        ("OneCode", config.onecode_host, config.onecode_port),
        ("LibreChat", config.librechat_host, config.librechat_port),
        ("MongoDB", "127.0.0.1", config.mongo_port),
    ):
        if not port_is_available(host, port):
            raise RuntimeError(f"{name} port {host}:{port} is already in use")
    model_config, warnings = model_config_preflight()
    return {
        "python_version": sys.version.split()[0],
        "node": {"path": node_path, "version": node_version},
        "npm": {"path": npm_path, "version": npm_version},
        "provenance": provenance,
        "model_config": model_config,
        "warnings": warnings,
    }


def _read_runtime_status(root: Path) -> dict[str, object] | None:
    path = root / "runtime-status.json"
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "invalid"}
    return payload if isinstance(payload, dict) else {"status": "invalid"}


def _status_provenance(config: ShellLaunchConfig) -> dict[str, object]:
    try:
        return librechat_provenance(config)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": redact_runtime_text(str(exc))[-500:]}


def shell_status(config: ShellLaunchConfig) -> dict[str, object]:
    onecode_url = f"http://{config.onecode_host}:{config.onecode_port}/health"
    shell_url = f"http://{config.librechat_host}:{config.librechat_port}/c/new"
    api_check = check_url(onecode_url)
    shell_check = check_url(shell_url)
    mongo_check = check_tcp("127.0.0.1", config.mongo_port)
    checks = {
        "onecode_api": api_check,
        "librechat_shell": shell_check,
        "mongo": mongo_check,
    }
    ok = all(bool(check.get("ok")) for check in checks.values())
    state_root = shell_state_root(config)
    try:
        _, warnings = model_config_preflight()
    except (OSError, ValueError, json.JSONDecodeError):
        warnings = ["model configuration could not be read"]
    logs_root = state_root / "logs"
    return {
        "status": "ok" if ok else "down",
        "shell_url": shell_url,
        "login": {"email": config.email},
        "checks": checks,
        "state_path": str(state_root),
        "model_timeout_seconds": config.model_timeout_seconds,
        "provenance": _status_provenance(config),
        "preflight_warnings": warnings,
        "runtime_status": _read_runtime_status(state_root),
        "runtime_status_path": str(state_root / "runtime-status.json"),
        "service_logs": {
            name: str(logs_root / f"{name}.log")
            for name in ("mongo", "onecode-api", "librechat")
        },
        "hint": None
        if ok
        else "Run `PYTHONPATH=src python3 -m onecode shell` and keep that terminal open.",
    }


def require_path(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{description} not found: {path}")


def append_bounded_log(
    path: Path,
    text: str,
    max_bytes: int = DEFAULT_SERVICE_LOG_MAX_BYTES,
) -> None:
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
        raise ValueError("max_bytes must be a positive integer")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    encoded = (existing + redact_runtime_text(text)).encode("utf-8")
    if len(encoded) > max_bytes:
        encoded = encoded[-max_bytes:]
        while encoded and encoded[0] & 0b1100_0000 == 0b1000_0000:
            encoded = encoded[1:]
    write_private_text(path, encoded.decode("utf-8", errors="ignore"))


def redact_shell_failure(config: ShellLaunchConfig, text: str) -> str:
    redacted = text
    for secret in (config.api_token, config.password):
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redact_runtime_text(redacted)


def _pump_process_output(stream: TextIO | None, log_path: Path) -> None:
    if stream is None:
        return
    try:
        for line in stream:
            append_bounded_log(log_path, line)
    finally:
        stream.close()


def start_process(
    name: str,
    command: list[str],
    cwd: Path,
    env: Mapping[str, str],
    log_path: Path,
) -> ManagedProcess:
    print(f"[onecode shell] starting {name}: {' '.join(command)}", flush=True)
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    pump_thread = threading.Thread(
        target=_pump_process_output,
        args=(process.stdout, log_path),
        name=f"onecode-{name}-log",
        daemon=True,
    )
    pump_thread.start()
    return ManagedProcess(name, process, log_path, pump_thread)


def terminate_processes(processes: list[ManagedProcess]) -> None:
    for record in reversed(processes):
        if not process_is_running(record):
            continue
        record.process.terminate()
    deadline = time.monotonic() + 8
    for record in reversed(processes):
        while process_is_running(record) and time.monotonic() < deadline:
            time.sleep(0.1)
        if process_is_running(record):
            record.process.kill()
    for record in processes:
        if record.pump_thread is not None:
            record.pump_thread.join(timeout=2)


def process_exit_summary(record: ManagedProcess) -> str:
    if record.pump_thread is not None:
        record.pump_thread.join(timeout=1)
    return_code = record.process.poll()
    lines = []
    if record.log_path.is_file():
        lines = record.log_path.read_text(encoding="utf-8").splitlines()[-20:]
    tail = "\n".join(lines)
    message = f"{record.name} exited with code {return_code}"
    return f"{message}\n{tail}" if tail else message


def ensure_local_user(config: ShellLaunchConfig, env: Mapping[str, str]) -> None:
    command = [
        "node",
        "config/create-user.js",
        config.email,
        "OneCode",
        "onecode",
        config.password,
        "--email-verified=true",
    ]
    completed = subprocess.run(
        command,
        cwd=str(config.librechat_dir),
        env=dict(env),
        text=True,
        capture_output=True,
        check=False,
    )
    output = f"{completed.stdout}\n{completed.stderr}"
    if completed.returncode != 0 and "already exists" not in output:
        raise RuntimeError(output.strip() or "failed to create local LibreChat user")


def launch_shell(config: ShellLaunchConfig) -> int:
    preflight = preflight_shell(config)
    build_runtime_config(config)
    librechat_env = build_librechat_env(config)
    onecode_env = build_onecode_env(config)
    processes: list[ManagedProcess] = []
    services: dict[str, int] = {}
    state_root = shell_state_root(config)
    logs_root = state_root / "logs"
    logs_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    logs_root.chmod(0o700)
    failure_summary: str | None = None
    write_runtime_status(state_root, status="starting", services=services)
    for warning in preflight["warnings"]:
        print(f"[onecode shell] warning: {warning}", flush=True)

    try:
        mongo = start_process(
            "mongo",
            mongo_command(config),
            config.librechat_dir,
            librechat_env,
            logs_root / "mongo.log",
        )
        processes.append(mongo)
        services[mongo.name] = mongo.process.pid
        write_runtime_status(state_root, status="starting", services=services)
        time.sleep(1.5)
        if not process_is_running(mongo):
            raise RuntimeError(process_exit_summary(mongo))

        onecode_api = start_process(
            "onecode-api",
            [
                sys.executable,
                "-m",
                "onecode",
                "serve",
                "--host",
                config.onecode_host,
                "--port",
                str(config.onecode_port),
                "--allow-unauthenticated-local",
            ],
            config.onecode_root,
            onecode_env,
            logs_root / "onecode-api.log",
        )
        processes.append(onecode_api)
        services[onecode_api.name] = onecode_api.process.pid
        write_runtime_status(state_root, status="starting", services=services)
        if not wait_for_url(f"http://{config.onecode_host}:{config.onecode_port}/health", timeout_seconds=20):
            raise RuntimeError("OneCode API did not become healthy")

        ensure_local_user(config, librechat_env)

        librechat = start_process(
            "librechat",
            ["npm", "run", "backend"],
            config.librechat_dir,
            librechat_env,
            logs_root / "librechat.log",
        )
        processes.append(librechat)
        services[librechat.name] = librechat.process.pid
        write_runtime_status(state_root, status="starting", services=services)
        url = f"http://{config.librechat_host}:{config.librechat_port}"
        if not wait_for_url(f"{url}/api/config", timeout_seconds=45):
            raise RuntimeError("LibreChat did not become healthy")
        write_runtime_status(state_root, status="running", services=services)

        print("", flush=True)
        print(f"OneCode Agent shell is running: {url}", flush=True)
        print("Local login account is ready.", flush=True)
        if config.show_credentials:
            print(f"Login email: {config.email}", flush=True)
            print(f"Login password: {config.password}", flush=True)
        else:
            print("Use --show-credentials to print the local preview login.", flush=True)
        print("Press Ctrl+C to stop local services.", flush=True)
        if config.open_browser:
            webbrowser.open(url)

        while all(process_is_running(process) for process in processes):
            time.sleep(1)
        exited = next(process for process in processes if not process_is_running(process))
        raise RuntimeError(process_exit_summary(exited))
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        failure_summary = redact_shell_failure(config, str(exc))[-2000:]
        raise
    finally:
        if processes:
            write_runtime_status(state_root, status="stopping", services=services)
        terminate_processes(processes)
        write_runtime_status(
            state_root,
            status="failed" if failure_summary is not None else "stopped",
            services=services,
            last_failure=failure_summary,
        )


def config_from_args(args: object) -> ShellLaunchConfig:
    onecode_root = Path(getattr(args, "onecode_root", Path.cwd())).resolve()
    librechat_dir_arg = getattr(args, "librechat_dir", None)
    librechat_dir = Path(librechat_dir_arg).resolve() if librechat_dir_arg else default_librechat_dir(onecode_root)
    workspace_arg = getattr(args, "workspace", None)
    workspace_root = Path(workspace_arg).resolve() if workspace_arg else onecode_root
    onecode_home = Path(os.getenv("ONECODE_HOME", "~/.onecode")).expanduser()
    state_dir = getattr(args, "state_dir", None)
    runtime_state_root = (
        Path(state_dir).expanduser().resolve() if state_dir else onecode_home / "shell"
    )
    model_timeout_seconds = getattr(args, "model_timeout_seconds", 60.0)
    if (
        isinstance(model_timeout_seconds, bool)
        or not isinstance(model_timeout_seconds, (int, float))
        or not 0 < model_timeout_seconds <= 600
    ):
        raise RuntimeError("model timeout seconds must be greater than zero and at most 600")
    return ShellLaunchConfig(
        onecode_root=onecode_root,
        librechat_dir=librechat_dir,
        onecode_host=getattr(args, "onecode_host", "127.0.0.1"),
        onecode_port=getattr(args, "onecode_port", DEFAULT_ONECODE_PORT),
        librechat_host=getattr(args, "librechat_host", "127.0.0.1"),
        librechat_port=getattr(args, "librechat_port", DEFAULT_LIBRECHAT_PORT),
        mongo_port=getattr(args, "mongo_port", DEFAULT_MONGO_PORT),
        api_token=getattr(args, "api_token", "dev-local-token"),
        workspace_root=workspace_root,
        runtime_state_root=runtime_state_root,
        email=getattr(args, "email", DEFAULT_LOCAL_EMAIL),
        password=getattr(args, "password", DEFAULT_LOCAL_PASSWORD),
        open_browser=getattr(args, "open_browser", True),
        show_credentials=getattr(args, "show_credentials", False),
        model_timeout_seconds=float(model_timeout_seconds),
    )
