#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=0
ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      cat <<'USAGE'
Usage: bash scripts/status-local.sh [onecode shell-status options] [--dry-run]

Checks whether the local OneCode kernel and bundled Web shell are reachable.
Extra arguments are forwarded to `onecode shell-status`.

Examples:
  bash scripts/status-local.sh
  bash scripts/status-local.sh --onecode-port 19180 --librechat-port 14180
USAGE
      exit 0
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=scripts/lib/local-deploy.sh
source "$SCRIPT_DIR/lib/local-deploy.sh"

cd "$ROOT_DIR"
PYTHON_BIN="$(onecode_python_bin)"
ONECODE_PORT=""
LIBRECHAT_PORT=""
MONGO_PORT=""
if [[ "${#ARGS[@]}" -gt 0 ]]; then
  ONECODE_PORT="$(onecode_arg_value --onecode-port "${ARGS[@]}" || true)"
  LIBRECHAT_PORT="$(onecode_arg_value --librechat-port "${ARGS[@]}" || true)"
  MONGO_PORT="$(onecode_arg_value --mongo-port "${ARGS[@]}" || true)"
fi
ONECODE_PORT="${ONECODE_PORT:-19080}"
LIBRECHAT_PORT="${LIBRECHAT_PORT:-14080}"
MONGO_PORT="${MONGO_PORT:-39017}"
COMMAND=(
  "$PYTHON_BIN" -m onecode shell-status
  --onecode-port "$ONECODE_PORT"
  --librechat-port "$LIBRECHAT_PORT"
  --mongo-port "$MONGO_PORT"
)

echo "OneCode local status"
echo "root: $ROOT_DIR"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "+ PYTHONPATH=src ${COMMAND[*]}"
else
  export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
  exec "${COMMAND[@]}"
fi
