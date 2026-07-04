#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON:-}"
if [[ -z "$PYTHON_BIN" && -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
  PYTHON_BIN="$VIRTUAL_ENV/bin/python"
elif [[ -z "$PYTHON_BIN" && -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi
PYTHON_BIN="${PYTHON_BIN:-python3}"
WHEEL_BASE="${TMPDIR:-/tmp}"
WHEEL_DIR="$(mktemp -d "$WHEEL_BASE/onecode-release-audit-wheel.XXXXXX")"
BUILD_DIR_EXISTED=0
if [[ -e "build" ]]; then
  BUILD_DIR_EXISTED=1
fi

cleanup_generated_build_dir() {
  if [[ "$BUILD_DIR_EXISTED" == "0" && -d "build" ]]; then
    "$PYTHON_BIN" - <<'PY'
from pathlib import Path
import shutil

build = Path("build")
if build.resolve().name == "build" and build.is_dir():
    shutil.rmtree(build)
PY
  fi
}

cleanup_wheel_dir() {
  case "$WHEEL_DIR" in
    "$WHEEL_BASE"/onecode-release-audit-wheel.*)
      rm -rf "$WHEEL_DIR"
      ;;
  esac
}

cleanup_generated_artifacts() {
  cleanup_generated_build_dir
  cleanup_wheel_dir
}
trap cleanup_generated_artifacts EXIT

echo "release-audit: $(pwd)"
echo "python: $PYTHON_BIN"
echo "publish action: not performed"
echo

echo "release readiness checks"
echo "git diff --check"
git diff --check
echo "source quality"
"$PYTHON_BIN" scripts/check_source_quality.py src
echo "wheel assets"
"$PYTHON_BIN" -m pip wheel . -w "$WHEEL_DIR" --no-deps
"$PYTHON_BIN" scripts/check_wheel_assets.py "$WHEEL_DIR"
cleanup_generated_artifacts
echo

echo "tracked changes"
git diff --name-status -- . | sed 's#one code/##'
echo

echo "untracked release candidates"
git ls-files --others --exclude-standard -- .
echo

echo "ignored local artifacts"
git status --short --ignored -- . | awk '/^!! / {print substr($0, 4)}'
echo

echo "release readiness summary"
echo "- whitespace: checked"
echo "- source quality: checked"
echo "- wheel assets: checked"
echo "- publish action: not performed"
