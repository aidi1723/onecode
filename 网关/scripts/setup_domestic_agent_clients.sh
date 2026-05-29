#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://10.0.0.184:6780}"
MODEL="${2:-}"
PROFILE="${3:-domestic-sub2api}"
PROJECT_DIR="${ONEWORD_PROJECT_DIR:-/home/aidi/projects/oneword-agentos-test}"
GATEWAY_TOKEN="${ONEWORD_GATEWAY_TOKEN:-test-gateway-token}"

export PATH="$HOME/.local/npm-global/bin:$PATH"

printf "Domestic base URL: %s\n" "$BASE_URL"
printf "Profile: %s\n" "$PROFILE"
printf "Paste domestic API key: " >&2
IFS= read -rs API_KEY
printf "\n" >&2

if [[ -z "$API_KEY" ]]; then
  echo "API key is empty" >&2
  exit 2
fi

mkdir -p "$HOME/.claude/profiles" "$HOME/.codex"
chmod 700 "$HOME/.claude" "$HOME/.claude/profiles" "$HOME/.codex"

python3 - "$BASE_URL" "$PROFILE" "$API_KEY" <<'PY'
import json
import os
import stat
import sys

base_url, profile, api_key = sys.argv[1:4]
claude_settings = {
    "env": {
        "ANTHROPIC_AUTH_TOKEN": api_key,
        "ANTHROPIC_API_KEY": api_key,
        "ANTHROPIC_BASE_URL": base_url,
    }
}
claude_root = os.path.expanduser("~/.claude")
profiles = os.path.join(claude_root, "profiles")
os.makedirs(profiles, exist_ok=True)
for path in [
    os.path.join(profiles, f"{profile}.json"),
    os.path.join(claude_root, "settings.json"),
]:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(claude_settings, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    os.replace(tmp, path)
current = os.path.join(profiles, ".current")
with open(current, "w", encoding="utf-8") as handle:
    handle.write(profile + "\n")
os.chmod(current, stat.S_IRUSR | stat.S_IWUSR)

codex_config = os.path.expanduser("~/.codex/config.toml")
tmp = f"{codex_config}.tmp"
with open(tmp, "w", encoding="utf-8") as handle:
    handle.write('model_provider = "openai"\n')
    handle.write(f'openai_base_url = "{base_url.rstrip("/")}/v1"\n')
    handle.write('approval_policy = "never"\n')
    handle.write('sandbox_mode = "workspace-write"\n')
    if os.environ.get("ONEWORD_CODEX_MODEL"):
        handle.write(f'model = "{os.environ["ONEWORD_CODEX_MODEL"]}"\n')
os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
os.replace(tmp, codex_config)

env_path = os.path.expanduser("~/.codex/oneword-domestic.env")
tmp = f"{env_path}.tmp"
with open(tmp, "w", encoding="utf-8") as handle:
    handle.write(f'export OPENAI_API_KEY="{api_key}"\n')
    handle.write(f'export ANTHROPIC_API_KEY="{api_key}"\n')
    handle.write(f'export ANTHROPIC_AUTH_TOKEN="{api_key}"\n')
    handle.write(f'export ANTHROPIC_BASE_URL="{base_url}"\n')
    handle.write(f'export OPENAI_BASE_URL="{base_url.rstrip("/")}/v1"\n')
os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
os.replace(tmp, env_path)
PY

if command -v cc-switch >/dev/null 2>&1; then
  cc-switch current || true
fi

pkill -f "uvicorn agent_skill_dictionary.gateway_server:app" 2>/dev/null || true
cd "$PROJECT_DIR"
export ONEWORD_WORKSPACE_ROOT="$PROJECT_DIR"
export ONEWORD_GATEWAY_TOKEN="$GATEWAY_TOKEN"
export ONEWORD_ANTHROPIC_BASE_URL="${BASE_URL%/}/v1"
export ONEWORD_ANTHROPIC_API_KEY="$API_KEY"
export ONEWORD_UPSTREAM_BASE_URL="${BASE_URL%/}/v1"
export ONEWORD_UPSTREAM_API_KEY="$API_KEY"
nohup .venv-gateway/bin/python -m uvicorn agent_skill_dictionary.gateway_server:app \
  --host 127.0.0.1 \
  --port 8080 \
  > /tmp/oneword-gateway-8080.log 2>&1 &
GATEWAY_PID=$!
sleep 1

printf "gateway_pid=%s\n" "$GATEWAY_PID"
curl -sS http://127.0.0.1:8080/ready \
  -H "authorization: Bearer $GATEWAY_TOKEN" \
  | python3 -m json.tool

if [[ -n "$MODEL" ]]; then
  printf "Testing gateway /v1/messages with model=%s\n" "$MODEL"
  curl -sS --connect-timeout 5 --max-time 60 \
    -H "authorization: Bearer $GATEWAY_TOKEN" \
    -H "anthropic-version: 2023-06-01" \
    -H "content-type: application/json" \
    http://127.0.0.1:8080/v1/messages \
    -d "{\"model\":\"$MODEL\",\"max_tokens\":32,\"messages\":[{\"role\":\"user\",\"content\":\"问：只回复 ok，测试连通性。\"}]}" \
    | python3 -m json.tool
else
  echo "MODEL not provided; skipped model call."
fi
