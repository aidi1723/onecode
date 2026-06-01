#!/usr/bin/env bash
set -euo pipefail

echo "release-audit: $(pwd)"
echo

echo "tracked changes"
git diff --name-status -- . | sed 's#one code/##'
echo

echo "untracked release candidates"
git ls-files --others --exclude-standard -- .
echo

echo "ignored local artifacts"
git status --short --ignored -- . | awk '/^!! / {print substr($0, 4)}'
