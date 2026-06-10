#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON:-}"
if [[ -z "$PYTHON_BIN" && -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
  PYTHON_BIN="$VIRTUAL_ENV/bin/python"
fi
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "compileall"
PYTHONPATH=src "$PYTHON_BIN" -m compileall src tests

echo "unittest-core"
PYTHONPATH=src "$PYTHON_BIN" -m unittest \
  tests.test_runner_cli \
  tests.test_builtin_skills \
  tests.test_packaging \
  tests.test_inspect_cli \
  tests.test_list_runs_cli \
  tests.test_execution_engine \
  tests.test_model_loop \
  tests.test_benchmark \
  tests.test_shell_projection \
  tests.test_wal \
  tests.test_iching_kernel_integration \
  tests.test_resumption \
  tests.test_task_resume \
  -v

echo "doctor"
PYTHONPATH=src "$PYTHON_BIN" -m onecode doctor
