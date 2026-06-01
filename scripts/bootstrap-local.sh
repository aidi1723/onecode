#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=0
INSTALL_ARGS=()
START_ARGS=()
MODE="install"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      INSTALL_ARGS+=("--dry-run")
      START_ARGS+=("--dry-run")
      shift
      ;;
    --with-tui|--skip-shell|--skip-preflight)
      INSTALL_ARGS+=("$1")
      shift
      ;;
    --)
      MODE="start"
      shift
      ;;
    -h|--help)
      cat <<'USAGE'
Usage: bash scripts/bootstrap-local.sh [install options] [-- start options]

Installs OneCode locally, then starts the bundled kernel and Web shell.

Install options:
  --with-tui          Install the optional Textual TUI dependency.
  --skip-shell        Install only the Python kernel, then skip shell start.
  --skip-preflight    Skip local environment checks.
  --dry-run           Print commands without executing them.

Start options after -- are forwarded to scripts/start-local.sh.

Examples:
  bash scripts/bootstrap-local.sh
  bash scripts/bootstrap-local.sh --dry-run
  bash scripts/bootstrap-local.sh -- --no-browser
  bash scripts/bootstrap-local.sh -- --librechat-port 14180
USAGE
      exit 0
      ;;
    *)
      if [[ "$MODE" == "install" ]]; then
        echo "unknown install option: $1" >&2
        echo "hint: put start options after --" >&2
        exit 2
      fi
      START_ARGS+=("$1")
      shift
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "OneCode local bootstrap"
echo "root: $ROOT_DIR"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "+ bash $SCRIPT_DIR/install-local.sh ${INSTALL_ARGS[*]}"
else
  bash "$SCRIPT_DIR/install-local.sh" "${INSTALL_ARGS[@]}"
fi

if [[ " ${INSTALL_ARGS[*]} " == *" --skip-shell "* ]]; then
  cat <<'NEXT'

Kernel-only install completed.
Start API-only mode manually when needed:
  PYTHONPATH=src python3 -m onecode serve --host 127.0.0.1 --port 19080
NEXT
  exit 0
fi

cat <<'NEXT'

Starting bundled shell. Open:
  http://127.0.0.1:14080/c/new
NEXT

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "+ bash $SCRIPT_DIR/start-local.sh ${START_ARGS[*]}"
else
  exec bash "$SCRIPT_DIR/start-local.sh" "${START_ARGS[@]}"
fi
