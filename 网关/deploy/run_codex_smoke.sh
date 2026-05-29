#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT_DIR/deploy/load_env.sh"

CODEX_BIN="${CODEX_BIN:-codex}"
MODEL="${ONEWORD_CODEX_MODEL:-${ONEWORD_ANTHROPIC_MODEL:-}}"
PROMPT="${1:-查：请只读评估当前项目，输出 500 字中文简报。必须包含项目目标、核心模块、安全风险、3 条改进建议。不要修改文件，不要安装依赖，不要联网。}"

if [[ -z "$MODEL" ]]; then
  echo "Set ONEWORD_CODEX_MODEL or ONEWORD_ANTHROPIC_MODEL in .env." >&2
  exit 2
fi

if ! command -v "$CODEX_BIN" >/dev/null 2>&1; then
  echo "Codex CLI not found. Set CODEX_BIN or install Codex CLI." >&2
  exit 127
fi

mkdir -p "$ROOT_DIR/.oneword"

CONFIG_FILE="$ROOT_DIR/.oneword/codex-config.toml"
cat > "$CONFIG_FILE" <<EOF
model_provider = "oneword"
model = "$MODEL"
preferred_auth_method = "apikey"
approval_policy = "never"
sandbox_mode = "read-only"

[model_providers.oneword]
name = "oneword"
base_url = "http://${ONEWORD_HOST}:${ONEWORD_PORT}/v1"
wire_api = "responses"
EOF
chmod 600 "$CONFIG_FILE"

export CODEX_HOME="$ROOT_DIR/.oneword/codex-home"
mkdir -p "$CODEX_HOME"
cp "$CONFIG_FILE" "$CODEX_HOME/config.toml"
printf '{"OPENAI_API_KEY":"%s"}\n' "$ONEWORD_GATEWAY_TOKEN" > "$CODEX_HOME/auth.json"
chmod 600 "$CODEX_HOME/auth.json"

cd "$ONEWORD_WORKSPACE_ROOT"

set +e
"$CODEX_BIN" exec \
  --skip-git-repo-check \
  --ephemeral \
  --model "$MODEL" \
  --sandbox read-only \
  -c approval_policy='"never"' \
  --json \
  "$PROMPT" \
  > "$ROOT_DIR/.oneword/codex-smoke-output.jsonl" \
  2> "$ROOT_DIR/.oneword/codex-smoke-stderr.txt"
EXIT_CODE="$?"
set -e

echo "exit_code=$EXIT_CODE"
echo "stdout=$ROOT_DIR/.oneword/codex-smoke-output.jsonl"
echo "stderr=$ROOT_DIR/.oneword/codex-smoke-stderr.txt"
sed -n '1,120p' "$ROOT_DIR/.oneword/codex-smoke-output.jsonl"
exit "$EXIT_CODE"
