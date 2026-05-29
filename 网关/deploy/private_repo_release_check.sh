#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "== Secret scan =="
python3 - <<'PY'
from __future__ import annotations

import re
from pathlib import Path

root = Path(".")
skip_dirs = {
    ".git",
    ".venv",
    ".venv-gateway",
    ".oneword",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
}
skip_files = {".env"}
patterns = [
    re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?<![A-Za-z0-9])AIza[0-9A-Za-z_-]{20,}"),
]
hits: list[str] = []
for path in root.rglob("*"):
    if any(part in skip_dirs for part in path.parts):
        continue
    if path.name in skip_files or not path.is_file():
        continue
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue
    for lineno, line in enumerate(text.splitlines(), 1):
        if any(pattern.search(line) for pattern in patterns):
            hits.append(f"{path}:{lineno}:{line[:160]}")
if hits:
    print("Potential secret found. Remove it before pushing.")
    for hit in hits:
        print(hit)
    raise SystemExit(1)
print("No obvious API keys found.")
PY

echo "== Python compile =="
python3 -m compileall -q agent_skill_dictionary tests

echo "== Core tests =="
python3 -m unittest tests.test_gateway_core tests.test_tool_executor_registry tests.test_tool_preflight -v

echo "Private beta release check passed."
