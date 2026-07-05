#!/usr/bin/env bash
set -euo pipefail

export PYTHONDONTWRITEBYTECODE=1

find scripts tests -name __pycache__ -type d -prune -exec rm -rf {} +
find scripts tests -name '*.pyc' -type f -delete

python3 -m unittest discover -s tests
python3 - <<'PY'
from pathlib import Path

for path in sorted(Path("scripts").glob("*.py")):
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
PY

python3 scripts/check_release_checksums.py
