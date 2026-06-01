#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=0
WITH_TUI=0
SKIP_SHELL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --with-tui)
      WITH_TUI=1
      shift
      ;;
    --skip-shell)
      SKIP_SHELL=1
      shift
      ;;
    -h|--help)
      cat <<'USAGE'
Usage: bash scripts/install-local.sh [--with-tui] [--skip-shell] [--dry-run]

Installs the OneCode kernel and, by default, the bundled LibreChat shell.

Options:
  --with-tui    Install the optional Textual TUI dependency.
  --skip-shell  Install only the Python kernel.
  --dry-run     Print commands without executing them.
USAGE
      exit 0
      ;;
    *)
      echo "unknown option: $1" >&2
      exit 2
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SHELL_DIR="$ROOT_DIR/shell/onecode-librechat"
PYTHON_BIN="${PYTHON:-python3}"

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "+ $*"
  else
    "$@"
  fi
}

echo "OneCode local install"
echo "root: $ROOT_DIR"
echo "python: $PYTHON_BIN"

cd "$ROOT_DIR"
if [[ "$WITH_TUI" -eq 1 ]]; then
  run "$PYTHON_BIN" -m pip install -e ".[tui]"
else
  run "$PYTHON_BIN" -m pip install -e .
fi

run "$PYTHON_BIN" -m onecode doctor

if [[ "$SKIP_SHELL" -eq 0 ]]; then
  if [[ ! -f "$SHELL_DIR/package.json" ]]; then
    echo "bundled shell package.json not found: $SHELL_DIR/package.json" >&2
    exit 1
  fi
  echo "Installing bundled shell dependencies in shell/onecode-librechat"
  run npm install --prefix "$SHELL_DIR"
fi

cat <<'NEXT'

Next:
  bash scripts/start-local.sh

Open:
  http://127.0.0.1:14080/c/new
NEXT
