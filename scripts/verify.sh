#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON:-}"
if [[ -z "$PYTHON_BIN" && -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
  PYTHON_BIN="$VIRTUAL_ENV/bin/python"
elif [[ -z "$PYTHON_BIN" && -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi
PYTHON_BIN="${PYTHON_BIN:-python3}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_SRC="${REPO_ROOT}/src"

echo "install"
if PYTHONPATH="${REPO_SRC}${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" -c "import onecode, textual" >/dev/null 2>&1; then
  echo "install skipped: onecode and textual already available"
else
  "$PYTHON_BIN" -m pip install -e .[tui]
fi

echo "compileall"
PYTHONPATH="${REPO_SRC}${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" -m compileall src tests

echo "source-quality"
PYTHONPATH="${REPO_SRC}${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" scripts/check_source_quality.py src

echo "ruff"
PYTHONPATH="${REPO_SRC}${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" -m ruff check src tests

echo "mypy"
PYTHONPATH="${REPO_SRC}${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" -m mypy \
  src/onecode/kernel/deployment_boundary.py \
  src/onecode/kernel/outcome_policy.py \
  src/onecode/kernel/evidence_io.py \
  src/onecode/kernel/path_guard.py \
  src/onecode/web/auth.py

if [[ "${1:-}" != "--skip-tests" ]]; then
  echo "unittest"
  PYTHONPATH="${REPO_SRC}${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" -m coverage run -m unittest discover -s tests -v
  echo "coverage"
  PYTHONPATH="${REPO_SRC}${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" -m coverage report --fail-under=75
fi

echo "doctor"
PYTHONPATH="${REPO_SRC}${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" -m onecode doctor
