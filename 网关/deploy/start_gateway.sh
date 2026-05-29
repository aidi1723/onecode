#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT_DIR/deploy/load_env.sh"

mkdir -p "$ROOT_DIR/.oneword"

if [[ ! -d "$ROOT_DIR/.venv-gateway" ]]; then
  python3 -m venv "$ROOT_DIR/.venv-gateway"
fi

"$ROOT_DIR/.venv-gateway/bin/python" -m pip install -q -r "$ROOT_DIR/requirements-gateway.txt"

echo "Starting 一字诀 gateway on http://$ONEWORD_HOST:$ONEWORD_PORT"
echo "Workspace: $ONEWORD_WORKSPACE_ROOT"

cd "$ROOT_DIR"
exec "$ROOT_DIR/.venv-gateway/bin/python" -m uvicorn \
  agent_skill_dictionary.gateway_server:app \
  --host "$ONEWORD_HOST" \
  --port "$ONEWORD_PORT"
