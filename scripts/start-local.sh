#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=0
SKIP_PREFLIGHT=0
ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --skip-preflight)
      SKIP_PREFLIGHT=1
      shift
      ;;
    -h|--help)
      cat <<'USAGE'
Usage: bash scripts/start-local.sh [onecode shell options]
                                   [--skip-preflight] [--dry-run]

Starts the bundled local OneCode kernel and LibreChat shell.
Extra arguments are forwarded to `onecode shell`.

Examples:
  bash scripts/start-local.sh
  bash scripts/start-local.sh --no-browser
  bash scripts/start-local.sh --onecode-port 19180 --librechat-port 14180 --mongo-port 39117
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

cd "$ROOT_DIR"
PYTHON_BIN="$(onecode_python_bin)"
COMMAND=("$PYTHON_BIN" -m onecode shell --show-credentials)
if [[ "${#ARGS[@]}" -gt 0 ]]; then
  COMMAND+=("${ARGS[@]}")
fi

echo "OneCode local shell"
echo "root: $ROOT_DIR"
echo "open: http://127.0.0.1:$LIBRECHAT_PORT/c/new"
echo "status: PYTHONPATH=src $PYTHON_BIN -m onecode shell-status"

if [[ "$DRY_RUN" -eq 1 ]]; then
  if [[ "$SKIP_PREFLIGHT" -eq 0 ]]; then
    echo "+ bash $SCRIPT_DIR/doctor-local.sh --onecode-port $ONECODE_PORT --librechat-port $LIBRECHAT_PORT --mongo-port $MONGO_PORT"
  fi
  echo "+ PYTHONPATH=src ${COMMAND[*]}"
else
  if [[ "$SKIP_PREFLIGHT" -eq 0 ]]; then
    bash "$SCRIPT_DIR/doctor-local.sh" \
      --onecode-port "$ONECODE_PORT" \
      --librechat-port "$LIBRECHAT_PORT" \
      --mongo-port "$MONGO_PORT"
  fi
  export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
  exec "${COMMAND[@]}"
fi
