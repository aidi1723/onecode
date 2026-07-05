#!/usr/bin/env bash
set -euo pipefail

export PYTHONDONTWRITEBYTECODE=1

find scripts tests release/yizijue-lm-public/scripts release/yizijue-lm-public/tests \
  -name __pycache__ -type d -prune -exec rm -rf {} +
find scripts tests release/yizijue-lm-public/scripts release/yizijue-lm-public/tests \
  -name '*.pyc' -type f -delete

python3 -m unittest discover -s tests
(cd release/yizijue-lm-public && python3 -m unittest discover -s tests)
python3 - <<'PY'
from pathlib import Path

for root in (Path("scripts"), Path("release/yizijue-lm-public/scripts")):
    for path in sorted(root.glob("*.py")):
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
PY

if python3 scripts/eval_mlx_predictions.py \
  --gold data/train_messages_distilled.jsonl \
  --predictions data/training/yizijue-qwen06b-strict-hard-negative-v2-on-original-test-strict-prompt-cn-rule-predictions-full.jsonl \
  --output /tmp/yizijue-review-full-report-should-fail.json \
  --guard-unknown-actions \
  --gate >/tmp/yizijue-review-full-report-should-fail.stdout 2>/tmp/yizijue-review-full-report-should-fail.stderr; then
  echo "Expected full-data gate check to fail because predictions cover only the test split." >&2
  exit 1
fi
if ! grep -q "missing_prediction_count" /tmp/yizijue-review-full-report-should-fail.stderr; then
  echo "Expected full-data gate failure to mention missing_prediction_count." >&2
  cat /tmp/yizijue-review-full-report-should-fail.stderr >&2
  exit 1
fi

python3 scripts/eval_mlx_predictions.py \
  --gold data/mlx_qwen06b_full/test.jsonl \
  --predictions data/training/yizijue-qwen06b-strict-hard-negative-v2-on-original-test-strict-prompt-cn-rule-predictions-full.jsonl \
  --output /tmp/yizijue-review-original-test-report.json \
  --guard-unknown-actions \
  --gate

python3 scripts/check_release_checksums.py
