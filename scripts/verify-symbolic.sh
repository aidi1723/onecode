#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_SRC="$REPO_ROOT/src"
SYMBOLIC_ROOT="$REPO_ROOT/packages/onecode-symbolic-audit"
SYMBOLIC_SRC="$SYMBOLIC_ROOT/src"

PYTHON_BIN="${PYTHON:-}"
if [[ -z "$PYTHON_BIN" && -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
  PYTHON_BIN="$VIRTUAL_ENV/bin/python"
elif [[ -z "$PYTHON_BIN" && -x "$REPO_ROOT/.venv/bin/python" ]]; then
  PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
fi
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "compileall-symbolic"
PYTHONPATH="${REPO_SRC}:${SYMBOLIC_SRC}${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" -m compileall "$SYMBOLIC_ROOT/src" "$SYMBOLIC_ROOT/tests" "$SYMBOLIC_ROOT/scripts"

echo "unittest-symbolic"
PYTHONPATH="${REPO_SRC}:${SYMBOLIC_SRC}${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" -m unittest discover -s "$SYMBOLIC_ROOT/tests" -v

echo "benchmark-symbolic"
PYTHONPATH="${REPO_SRC}:${SYMBOLIC_SRC}${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" "$SYMBOLIC_ROOT/scripts/benchmark_ziwei.py" --json
