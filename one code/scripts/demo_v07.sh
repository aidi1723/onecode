#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON:-}"
if [[ -z "$PYTHON_BIN" && -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
  PYTHON_BIN="$VIRTUAL_ENV/bin/python"
elif [[ -z "$PYTHON_BIN" && -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ -n "${WORKSPACE:-}" ]]; then
  DEMO_WORKSPACE="$WORKSPACE"
  mkdir -p "$DEMO_WORKSPACE"
else
  DEMO_WORKSPACE="$(mktemp -d "${TMPDIR:-/tmp}/onecode-v07-demo.XXXXXX")"
fi

PLAN_PATH="$DEMO_WORKSPACE/task-plan.json"

cat > "$PLAN_PATH" <<'JSON'
{
  "task": "v0.7 verified demo",
  "assets": [
    {
      "path": "src/demo_module.py",
      "content": "def value():\n    return 7\n"
    },
    {
      "path": "tests/test_demo_module.py",
      "content": "import unittest\nfrom src.demo_module import value\n\nclass DemoModuleTests(unittest.TestCase):\n    def test_value(self):\n        self.assertEqual(value(), 7)\n"
    }
  ]
}
JSON

echo "demo workspace: $DEMO_WORKSPACE"

echo "list-verifier-presets"
"$PYTHON_BIN" -m onecode list-verifier-presets

echo "init-verifier-policy"
"$PYTHON_BIN" -m onecode init-verifier-policy \
  --workspace "$DEMO_WORKSPACE" \
  --preset python-unittest

echo "run-plan"
"$PYTHON_BIN" -m onecode run-plan \
  --workspace "$DEMO_WORKSPACE" \
  --run-id demo-plan-verified \
  --plan "$PLAN_PATH" \
  --verifier python-unittest

echo "inspect"
"$PYTHON_BIN" -m onecode inspect \
  --workspace "$DEMO_WORKSPACE" \
  --run-id demo-plan-verified

echo "list-runs"
"$PYTHON_BIN" -m onecode list-runs \
  --workspace "$DEMO_WORKSPACE"
