#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://10.0.0.184:6780}"
MODEL="${2:-}"
PROJECT_DIR="${ONEWORD_PROJECT_DIR:-/home/aidi/projects/oneword-agentos-test}"
PROMPT="${ONEWORD_CODEX_SMOKE_PROMPT:-只读检查当前目录，回复一句话说明 README 是否存在。不要修改任何文件。}"

export PATH="$HOME/.local/npm-global/bin:$PATH"

if ! command -v codex >/dev/null 2>&1; then
  echo "codex command not found; install @openai/codex first." >&2
  exit 127
fi

printf "Domestic base URL: %s\n" "$BASE_URL"
printf "Paste domestic API key: " >&2
IFS= read -rs API_KEY
printf "\n" >&2

if [[ -z "$API_KEY" ]]; then
  echo "API key is empty." >&2
  exit 2
fi

mkdir -p "$HOME/.codex"
chmod 700 "$HOME/.codex"
cat > "$HOME/.codex/config.toml" <<EOF
model_provider = "openai"
openai_base_url = "${BASE_URL%/}/v1"
approval_policy = "never"
sandbox_mode = "workspace-write"
EOF
chmod 600 "$HOME/.codex/config.toml"

export OPENAI_API_KEY="$API_KEY"

printf "== direct models ==\n"
curl -sS --connect-timeout 5 --max-time 30 \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  "${BASE_URL%/}/v1/models" \
  > /tmp/codex-domestic-models.json

python3 - <<'PY'
import json

path = "/tmp/codex-domestic-models.json"
data = json.load(open(path, encoding="utf-8"))
items = data.get("data", []) if isinstance(data, dict) else []
print("model_count", len(items))
for item in items[:20]:
    print(item.get("id") or item.get("name") or item)
PY

if [[ -z "$MODEL" ]]; then
  MODEL=$(
    python3 - <<'PY'
import json

items = json.load(open("/tmp/codex-domestic-models.json", encoding="utf-8")).get("data", [])
print((items[0].get("id") or items[0].get("name")) if items else "")
PY
  )
fi

if [[ -z "$MODEL" ]]; then
  echo "No model available from /v1/models." >&2
  exit 3
fi

printf "selected_model=%s\n" "$MODEL"

printf "== direct chat ==\n"
curl -sS --connect-timeout 5 --max-time 60 \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  "${BASE_URL%/}/v1/chat/completions" \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"只回复 ok\"}],\"max_tokens\":16}" \
  | python3 -m json.tool \
  | sed -n "1,100p"

printf "== codex exec ==\n"
cd "$PROJECT_DIR"
timeout 120 codex exec \
  --skip-git-repo-check \
  --ephemeral \
  --model "$MODEL" \
  --sandbox read-only \
  --ask-for-approval never \
  "$PROMPT" \
  | sed -n "1,160p"
