#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        raise SystemExit("Missing .env. Copy .env.example to .env and fill it first.")
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    env_path = Path(os.getenv("ONEWORD_ENV_FILE", root / ".env"))
    env = load_env(env_path)
    host = env.get("ONEWORD_HOST") or "127.0.0.1"
    port = env.get("ONEWORD_PORT") or "8080"
    token = env.get("ONEWORD_GATEWAY_TOKEN") or ""
    model = env.get("ONEWORD_ANTHROPIC_MODEL") or "claude-sonnet-4-6"
    if not token:
        raise SystemExit("ONEWORD_GATEWAY_TOKEN is empty in .env")

    out = Path(os.getenv("ONEWORD_CLAUDE_SETTINGS", root / ".oneword" / "claude-gateway-settings.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    settings = {
        "env": {
            "ANTHROPIC_BASE_URL": f"http://{host}:{port}",
            "ANTHROPIC_API_KEY": token,
            "ANTHROPIC_AUTH_TOKEN": token,
            "ANTHROPIC_MODEL": model,
        }
    }
    out.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out.chmod(0o600)
    print(out)


if __name__ == "__main__":
    main()
