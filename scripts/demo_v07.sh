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
PRESETS_JSON="$DEMO_WORKSPACE/presets.json"
POLICY_JSON="$DEMO_WORKSPACE/policy.json"
RUN_PLAN_JSON="$DEMO_WORKSPACE/run-plan.json"
INSPECT_JSON="$DEMO_WORKSPACE/inspect.json"
LIST_RUNS_JSON="$DEMO_WORKSPACE/list-runs.json"

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

"$PYTHON_BIN" -m onecode list-verifier-presets > "$PRESETS_JSON"
"$PYTHON_BIN" -c 'import json, sys; data = json.load(open(sys.argv[1], encoding="utf-8")); print("presets: " + ", ".join(p["id"] for p in data["presets"]))' "$PRESETS_JSON"

"$PYTHON_BIN" -m onecode init-verifier-policy \
  --workspace "$DEMO_WORKSPACE" \
  --preset python-unittest \
  > "$POLICY_JSON"
"$PYTHON_BIN" -c 'import json, sys; data = json.load(open(sys.argv[1], encoding="utf-8")); print("policy: " + data.get("status", "unknown"))' "$POLICY_JSON"

"$PYTHON_BIN" -m onecode run-plan \
  --workspace "$DEMO_WORKSPACE" \
  --run-id demo-plan-verified \
  --plan "$PLAN_PATH" \
  --verifier python-unittest \
  > "$RUN_PLAN_JSON"
"$PYTHON_BIN" -c 'import json, sys; data = json.load(open(sys.argv[1], encoding="utf-8")); print("run-plan: " + data.get("status", "unknown") + " / " + data.get("delivery_status", "unknown")); verifier = (data.get("verifier_results") or [{}])[0]; print("verifier: " + verifier.get("id", "unknown") + " " + verifier.get("status", "unknown"))' "$RUN_PLAN_JSON"

"$PYTHON_BIN" -m onecode inspect \
  --workspace "$DEMO_WORKSPACE" \
  --run-id demo-plan-verified \
  > "$INSPECT_JSON"
"$PYTHON_BIN" -c 'import json, sys; data = json.load(open(sys.argv[1], encoding="utf-8")); print("inspect: " + data.get("status", "unknown") + " / " + data.get("delivery_status", "unknown"))' "$INSPECT_JSON"

"$PYTHON_BIN" -m onecode list-runs \
  --workspace "$DEMO_WORKSPACE" \
  > "$LIST_RUNS_JSON"
"$PYTHON_BIN" -c 'import json, sys; data = json.load(open(sys.argv[1], encoding="utf-8")); print("runs: " + ", ".join(run.get("run_id", "") for run in data.get("runs", [])))' "$LIST_RUNS_JSON"

echo "json artifacts: $DEMO_WORKSPACE/*.json"
