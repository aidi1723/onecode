#!/usr/bin/env bash
set -euo pipefail

echo "install"
python3 -m pip install -e .[tui]

echo "compileall"
python3 -m compileall src tests

if [[ "${1:-}" != "--skip-tests" ]]; then
  echo "unittest"
  python3 -m unittest discover -s tests -v
fi

echo "doctor"
python3 -m onecode doctor
