from __future__ import annotations

import os
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.error import URLError
from urllib.request import Request, urlopen


DEFAULT_LOCAL_EMAIL = "preview@example.invalid"
DEFAULT_LOCAL_PASSWORD = "change-me-local-preview"


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
    email: str = DEFAULT_LOCAL_EMAIL
    password: str = DEFAULT_LOCAL_PASSWORD
    open_browser: bool = True
    show_credentials: bool = False


def default_librechat_dir(project_root: Path) -> Path:
    return project_root.resolve().parent / "onecode-librechat"


def build_librechat_env(config: ShellLaunchConfig, base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(base_env or os.environ)
    for key in list(env):
        if key.startswith("ONEWORD_") or key.startswith("OPENAI_"):
            env.pop(key)
    env.update(
        {
            "APP_TITLE": "one code",
            "CUSTOM_FOOTER": "one code",
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
            "CONFIG_PATH": str(runtime_config_path(config)),
        }
    )
    return env


def runtime_config_path(config: ShellLaunchConfig) -> Path:
    return config.workspace_root / "librechat.onecode.yaml"


def build_runtime_config(config: ShellLaunchConfig) -> Path:
    config.workspace_root.mkdir(parents=True, exist_ok=True)
    path = runtime_config_path(config)
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
    if env.get("OPENAI_BASE_URL") and not env.get("ONECODE_MODEL_ENDPOINT"):
        env["ONECODE_MODEL_ENDPOINT"] = env["OPENAI_BASE_URL"]
        env["ONECODE_MODEL_PROVIDER"] = "chat"
    if env.get("OPENAI_MODEL") and not env.get("ONECODE_MODEL"):
        env["ONECODE_MODEL"] = env["OPENAI_MODEL"]
    return env


def process_is_running(process: subprocess.Popen) -> bool:
    return process.poll() is None


def wait_for_url(url: str, timeout_seconds: float = 30) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urlopen(Request(url, headers={"accept": "application/json"}), timeout=2):
                return True
        except (OSError, URLError):
            time.sleep(0.5)
    return False


def require_path(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{description} not found: {path}")


def start_process(name: str, command: list[str], cwd: Path, env: Mapping[str, str]) -> subprocess.Popen:
    print(f"[onecode shell] starting {name}: {' '.join(command)}", flush=True)
    return subprocess.Popen(command, cwd=str(cwd), env=dict(env))


def terminate_processes(processes: list[subprocess.Popen]) -> None:
    for process in reversed(processes):
        if not process_is_running(process):
            continue
        process.terminate()
    deadline = time.monotonic() + 8
    for process in reversed(processes):
        while process_is_running(process) and time.monotonic() < deadline:
            time.sleep(0.1)
        if process_is_running(process):
            process.kill()


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
    require_path(config.onecode_root / "src" / "onecode", "OneCode source package")
    require_path(config.librechat_dir / "package.json", "LibreChat shell package")

    build_runtime_config(config)
    librechat_env = build_librechat_env(config)
    onecode_env = build_onecode_env(config)
    processes: list[subprocess.Popen] = []

    try:
        processes.append(
            start_process(
                "mongo",
                [
                    "node",
                    "-e",
                    (
                        "const { MongoMemoryServer } = require('mongodb-memory-server');"
                        f"MongoMemoryServer.create({{ instance: {{ ip: '127.0.0.1', port: {config.mongo_port}, dbName: 'LibreChat' }} }})"
                        ".then(() => setInterval(() => {}, 1 << 30))"
                        ".catch((error) => { console.error(error); process.exit(1); });"
                    ),
                ],
                config.librechat_dir,
                librechat_env,
            )
        )
        time.sleep(1.5)
        if not process_is_running(processes[-1]):
            raise RuntimeError("temporary MongoDB process exited during startup")

        processes.append(
            start_process(
                "onecode api",
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
            )
        )
        if not wait_for_url(f"http://{config.onecode_host}:{config.onecode_port}/health", timeout_seconds=20):
            raise RuntimeError("OneCode API did not become healthy")

        ensure_local_user(config, librechat_env)

        processes.append(
            start_process(
                "librechat",
                ["npm", "run", "backend"],
                config.librechat_dir,
                librechat_env,
            )
        )
        url = f"http://{config.librechat_host}:{config.librechat_port}"
        if not wait_for_url(f"{url}/api/config", timeout_seconds=45):
            raise RuntimeError("LibreChat did not become healthy")

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
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        terminate_processes(processes)


def config_from_args(args: object) -> ShellLaunchConfig:
    onecode_root = Path(getattr(args, "onecode_root", Path.cwd())).resolve()
    librechat_dir_arg = getattr(args, "librechat_dir", None)
    librechat_dir = Path(librechat_dir_arg).resolve() if librechat_dir_arg else default_librechat_dir(onecode_root)
    workspace_arg = getattr(args, "workspace", None)
    workspace_root = Path(workspace_arg).resolve() if workspace_arg else Path.cwd() / ".onecode" / "shell-workspace"
    return ShellLaunchConfig(
        onecode_root=onecode_root,
        librechat_dir=librechat_dir,
        onecode_host=getattr(args, "onecode_host", "127.0.0.1"),
        onecode_port=getattr(args, "onecode_port", 8080),
        librechat_host=getattr(args, "librechat_host", "127.0.0.1"),
        librechat_port=getattr(args, "librechat_port", 3080),
        mongo_port=getattr(args, "mongo_port", 27017),
        api_token=getattr(args, "api_token", "dev-local-token"),
        workspace_root=workspace_root,
        email=getattr(args, "email", DEFAULT_LOCAL_EMAIL),
        password=getattr(args, "password", DEFAULT_LOCAL_PASSWORD),
        open_browser=getattr(args, "open_browser", True),
        show_credentials=getattr(args, "show_credentials", False),
    )
