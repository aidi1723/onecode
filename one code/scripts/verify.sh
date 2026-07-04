#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON:-}"
if [[ -z "$PYTHON_BIN" && -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
  PYTHON_BIN="$VIRTUAL_ENV/bin/python"
elif [[ -z "$PYTHON_BIN" && -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "install"
if "$PYTHON_BIN" -c "import onecode, textual" >/dev/null 2>&1; then
  echo "install skipped: onecode and textual already available"
else
  "$PYTHON_BIN" -m pip install -e .[tui]
fi

echo "compileall"
"$PYTHON_BIN" -m compileall src tests

echo "source-quality"
"$PYTHON_BIN" scripts/check_source_quality.py src

if [[ "${1:-}" != "--skip-tests" ]]; then
  echo "unittest"
  "$PYTHON_BIN" -m unittest discover -s tests -v
fi

echo "doctor"
"$PYTHON_BIN" -m onecode doctor
