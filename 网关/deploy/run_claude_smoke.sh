#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT_DIR/deploy/load_env.sh"

CLAUDE_BIN="${CLAUDE_BIN:-claude}"
SETTINGS_FILE="$(python3 "$ROOT_DIR/deploy/make_claude_settings.py")"
mkdir -p "$ROOT_DIR/.oneword"

PROMPT="${1:-查：请只读评估当前项目，输出 500 字中文简报。必须包含项目目标、核心模块、安全风险、3 条改进建议。不要修改文件，不要安装依赖，不要联网。}"

cd "$ONEWORD_WORKSPACE_ROOT"

set +e
"$CLAUDE_BIN" --bare \
  --settings "$SETTINGS_FILE" \
  -p \
  --output-format json \
  --model "$ONEWORD_ANTHROPIC_MODEL" \
  --tools "Read,Bash" \
  --permission-mode dontAsk \
  --max-budget-usd "${ONEWORD_CLAUDE_MAX_BUDGET_USD:-0.05}" \
  "$PROMPT" \
  > "$ROOT_DIR/.oneword/claude-smoke-output.json" \
  2> "$ROOT_DIR/.oneword/claude-smoke-stderr.txt"
EXIT_CODE="$?"
set -e

echo "exit_code=$EXIT_CODE"
echo "stdout=$ROOT_DIR/.oneword/claude-smoke-output.json"
echo "stderr=$ROOT_DIR/.oneword/claude-smoke-stderr.txt"
sed -n '1,80p' "$ROOT_DIR/.oneword/claude-smoke-output.json"
exit "$EXIT_CODE"
