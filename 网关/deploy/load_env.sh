#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ONEWORD_ENV_FILE:-$ROOT_DIR/.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing .env. Copy .env.example to .env and fill it first." >&2
  exit 2
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

export ONEWORD_HOST="${ONEWORD_HOST:-127.0.0.1}"
export ONEWORD_PORT="${ONEWORD_PORT:-8080}"
export ONEWORD_GATEWAY_TOKEN="${ONEWORD_GATEWAY_TOKEN:-}"
export ONEWORD_WORKSPACE_ROOT="${ONEWORD_WORKSPACE_ROOT:-$ROOT_DIR}"
export ONEWORD_ANTHROPIC_MODEL="${ONEWORD_ANTHROPIC_MODEL:-claude-sonnet-4-6}"
