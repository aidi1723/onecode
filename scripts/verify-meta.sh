#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_SRC="$REPO_ROOT/src"

PYTHON_BIN="${PYTHON:-}"
if [[ -z "$PYTHON_BIN" && -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
  PYTHON_BIN="$VIRTUAL_ENV/bin/python"
elif [[ -z "$PYTHON_BIN" && -x "$REPO_ROOT/.venv/bin/python" ]]; then
  PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
fi
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "unittest-meta"
PYTHONPATH="${REPO_SRC}${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" -m unittest discover -s tests/meta -v
