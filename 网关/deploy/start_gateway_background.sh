#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT_DIR/deploy/load_env.sh"

mkdir -p "$ROOT_DIR/.oneword"

if [[ -f "$ROOT_DIR/.oneword/gateway.pid" ]]; then
  OLD_PID="$(cat "$ROOT_DIR/.oneword/gateway.pid")"
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Gateway already running: pid=$OLD_PID"
    exit 0
  fi
fi

nohup bash "$ROOT_DIR/deploy/start_gateway.sh" \
  > "$ROOT_DIR/.oneword/gateway.log" 2>&1 &

PID="$!"
echo "$PID" > "$ROOT_DIR/.oneword/gateway.pid"
echo "Gateway started: pid=$PID log=$ROOT_DIR/.oneword/gateway.log"
