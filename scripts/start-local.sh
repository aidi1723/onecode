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
Usage: bash scripts/start-local.sh [onecode shell options] [--dry-run]

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
PYTHON_BIN="${PYTHON:-python3}"
COMMAND=("$PYTHON_BIN" -m onecode shell --show-credentials)
if [[ "${#ARGS[@]}" -gt 0 ]]; then
  COMMAND+=("${ARGS[@]}")
fi

echo "OneCode local shell"
echo "root: $ROOT_DIR"
echo "open: http://127.0.0.1:14080/c/new"
echo "status: PYTHONPATH=src $PYTHON_BIN -m onecode shell-status"

cd "$ROOT_DIR"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "+ PYTHONPATH=src ${COMMAND[*]}"
else
  export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
  exec "${COMMAND[@]}"
fi
