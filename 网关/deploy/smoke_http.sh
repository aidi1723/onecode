#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT_DIR/deploy/load_env.sh"

BASE_URL="http://$ONEWORD_HOST:$ONEWORD_PORT"
MODEL="${ONEWORD_ANTHROPIC_MODEL:-claude-sonnet-4-6}"

echo "== /ready =="
curl -sS --max-time 10 \
  -H "authorization: Bearer $ONEWORD_GATEWAY_TOKEN" \
  "$BASE_URL/ready" | python3 -m json.tool

echo
echo "== /v1/messages smoke =="
curl -sS --max-time 60 \
  -H "x-api-key: $ONEWORD_GATEWAY_TOKEN" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  "$BASE_URL/v1/messages" \
  -d "{\"model\":\"$MODEL\",\"max_tokens\":96,\"messages\":[{\"role\":\"user\",\"content\":\"问：只回复 ok，用于测试网关连通性。\"}]}" \
  | python3 -m json.tool
