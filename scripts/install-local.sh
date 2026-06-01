#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=0
WITH_TUI=0
SKIP_SHELL=0
SKIP_PREFLIGHT=0

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
    --skip-preflight)
      SKIP_PREFLIGHT=1
      shift
      ;;
    -h|--help)
      cat <<'USAGE'
Usage: bash scripts/install-local.sh [--with-tui] [--skip-shell]
                                     [--skip-preflight] [--dry-run]

Installs the OneCode kernel and, by default, the bundled LibreChat shell.

Options:
  --with-tui         Install the optional Textual TUI dependency.
  --skip-shell       Install only the Python kernel.
  --skip-preflight   Skip local environment checks.
  --dry-run          Print commands without executing them.
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
# shellcheck source=scripts/lib/local-deploy.sh
source "$SCRIPT_DIR/lib/local-deploy.sh"

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "+ $*"
  else
    "$@"
  fi
}

echo "OneCode local install"
echo "root: $ROOT_DIR"

cd "$ROOT_DIR"
PYTHON_BIN="$(onecode_python_bin)"
echo "python: $PYTHON_BIN"

if [[ "$SKIP_PREFLIGHT" -eq 0 && "$DRY_RUN" -eq 0 ]]; then
  if [[ "$SKIP_SHELL" -eq 1 ]]; then
    bash "$SCRIPT_DIR/doctor-local.sh" --skip-ports --skip-shell
  else
    bash "$SCRIPT_DIR/doctor-local.sh" --skip-ports --skip-shell-deps
  fi
elif [[ "$SKIP_PREFLIGHT" -eq 0 ]]; then
  if [[ "$SKIP_SHELL" -eq 1 ]]; then
    echo "+ bash $SCRIPT_DIR/doctor-local.sh --skip-ports --skip-shell"
  else
    echo "+ bash $SCRIPT_DIR/doctor-local.sh --skip-ports --skip-shell-deps"
  fi
fi

if [[ "$WITH_TUI" -eq 1 ]]; then
  run "$PYTHON_BIN" -m pip install -e ".[tui]"
else
  run "$PYTHON_BIN" -m pip install -e .
fi

run "$PYTHON_BIN" -m onecode doctor

if [[ "$SKIP_SHELL" -eq 0 ]]; then
  echo "Installing bundled shell dependencies in shell/onecode-librechat"
  run npm install --prefix "$SHELL_DIR"
fi

cat <<'NEXT'

Next:
  bash scripts/start-local.sh

Open:
  http://127.0.0.1:14080/c/new
NEXT
