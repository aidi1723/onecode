#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON:-}"
if [[ -z "$PYTHON_BIN" && -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
  PYTHON_BIN="$VIRTUAL_ENV/bin/python"
fi
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "install"
"$PYTHON_BIN" -m pip install -e .[tui]

echo "compileall"
"$PYTHON_BIN" -m compileall src tests

if [[ "${1:-}" != "--skip-tests" ]]; then
  echo "unittest"
  "$PYTHON_BIN" -m unittest discover -s tests -v
fi

echo "doctor"
"$PYTHON_BIN" -m onecode doctor
