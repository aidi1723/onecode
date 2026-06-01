#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON:-}"
SKIP_INSTALL=0
SKIP_TESTS=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-install)
      SKIP_INSTALL=1
      shift
      ;;
    --skip-tests)
      SKIP_TESTS=1
      shift
      ;;
    -h|--help)
      cat <<'USAGE'
Usage: bash scripts/verify.sh [--skip-install] [--skip-tests]

Runs local verification. Use --skip-install when pip is unavailable but the
source tree can run with PYTHONPATH=src.
USAGE
      exit 0
      ;;
    *)
      echo "unknown option: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$PYTHON_BIN" && -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
  PYTHON_BIN="$VIRTUAL_ENV/bin/python"
elif [[ -z "$PYTHON_BIN" && -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ "$SKIP_INSTALL" -eq 0 ]]; then
  echo "install"
  "$PYTHON_BIN" -m pip install -e .[tui]
else
  echo "install skipped"
  export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"
fi

echo "compileall"
"$PYTHON_BIN" -m compileall src tests

if [[ "$SKIP_TESTS" -eq 0 ]]; then
  echo "unittest"
  "$PYTHON_BIN" -m unittest discover -s tests -v
fi

echo "doctor"
"$PYTHON_BIN" -m onecode doctor
