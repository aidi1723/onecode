#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://10.0.0.184:6780}"
MODEL="${2:-gpt-5.5}"
ROOT="/home/aidi/projects/codex-evals"
REPORT_DIR="$ROOT/reports"
RUNNER="$ROOT/run_codex_dazidian_eval.sh"

mkdir -p "$REPORT_DIR"

before_list="$(mktemp)"
after_list="$(mktemp)"
find "$REPORT_DIR" -maxdepth 1 -type f -name 'dazidian-codex-eval-*.md' | sort > "$before_list"

"$RUNNER" "$BASE_URL" "$MODEL"

find "$REPORT_DIR" -maxdepth 1 -type f -name 'dazidian-codex-eval-*.md' | sort > "$after_list"
report_file="$(
  comm -13 "$before_list" "$after_list" | tail -n 1
)"
if [[ -z "$report_file" ]]; then
  report_file="$(find "$REPORT_DIR" -maxdepth 1 -type f -name 'dazidian-codex-eval-*.md' -printf '%T@ %p\n' | sort -n | tail -n 1 | cut -d' ' -f2-)"
fi
if [[ -z "$report_file" || ! -s "$report_file" ]]; then
  echo "No non-empty Codex report was produced." >&2
  exit 10
fi

python3 - "$report_file" <<'PY'
import json
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8", errors="replace")

checks = {
    "has_project_goal": any(k in text for k in ("项目目标", "当前形态", "定位")),
    "has_structure": any(k in text for k in ("目录结构", "核心模块", "模块")),
    "has_architecture": any(k in text for k in ("架构", "可维护", "成熟度")),
    "has_tests": any(k in text for k in ("测试", "回归", "验证")),
    "has_security": any(k in text for k in ("安全", "密钥", "供应链", "漏洞")),
    "has_agentos_alignment": any(k in text for k in ("一字诀", "AgentOS", "大字典")),
    "has_top_10": bool(re.search(r"(10\s*条|十\s*条|Top\s*10|优先.*10)", text, re.I)),
    "has_score_table": bool(re.search(r"(0\s*-\s*100|100\s*分|评分)", text)),
    "has_evidence": any(k in text for k in ("实际检查", "证据", "检查过的文件", "文件或目录")),
    "has_no_secret": not bool(re.search(r"sk-[A-Za-z0-9_\-]{20,}|AIza[0-9A-Za-z_\-]{20,}", text)),
}
score = sum(1 for ok in checks.values() if ok)
passed = score >= 9 and checks["has_no_secret"]
summary = {
    "report_file": str(path),
    "chars": len(text),
    "checks": checks,
    "score": score,
    "total": len(checks),
    "passed": passed,
}
summary_path = path.with_suffix(".quality.json")
summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
if not passed:
    raise SystemExit(11)
PY

printf "\nREPORT_FILE=%s\n" "$report_file"
printf "QUALITY_FILE=%s\n" "${report_file%.md}.quality.json"
