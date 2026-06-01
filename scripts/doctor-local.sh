#!/usr/bin/env bash
set -euo pipefail

CHECK_PORTS=1
CHECK_SHELL=1
CHECK_SHELL_DEPS=1
ONECODE_PORT=19080
LIBRECHAT_PORT=14080
MONGO_PORT=39017

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-ports)
      CHECK_PORTS=0
      shift
      ;;
    --skip-shell)
      CHECK_SHELL=0
      CHECK_SHELL_DEPS=0
      shift
      ;;
    --skip-shell-deps)
      CHECK_SHELL_DEPS=0
      shift
      ;;
    --onecode-port)
      ONECODE_PORT="${2:?missing value for --onecode-port}"
      shift 2
      ;;
    --librechat-port)
      LIBRECHAT_PORT="${2:?missing value for --librechat-port}"
      shift 2
      ;;
    --mongo-port)
      MONGO_PORT="${2:?missing value for --mongo-port}"
      shift 2
      ;;
    -h|--help)
      cat <<'USAGE'
Usage: bash scripts/doctor-local.sh [--skip-ports] [--skip-shell]
                                    [--skip-shell-deps]
                                    [--onecode-port PORT]
                                    [--librechat-port PORT]
                                    [--mongo-port PORT]

Checks the local machine before installing or starting OneCode.
USAGE
      exit 0
      ;;
    *)
      echo "unknown option: $1" >&2
      exit 2
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SHELL_DIR="$ROOT_DIR/shell/onecode-librechat"
# shellcheck source=scripts/lib/local-deploy.sh
source "$SCRIPT_DIR/lib/local-deploy.sh"

cd "$ROOT_DIR"
PYTHON_BIN="$(onecode_python_bin)"
FAILURES=0

echo "OneCode local deployment doctor"
echo "root: $ROOT_DIR"

onecode_check_python "$PYTHON_BIN" || FAILURES=$((FAILURES + 1))
onecode_check_pip "$PYTHON_BIN" || FAILURES=$((FAILURES + 1))

if [[ "$CHECK_SHELL" -eq 1 ]]; then
  onecode_check_command "node" "node" "install Node.js 20+." || FAILURES=$((FAILURES + 1))
  onecode_check_command "npm" "npm" "install npm with Node.js." || FAILURES=$((FAILURES + 1))
  onecode_check_shell_tree "$SHELL_DIR" || FAILURES=$((FAILURES + 1))

  if [[ "$CHECK_SHELL_DEPS" -eq 1 ]]; then
    onecode_check_shell_deps "$SHELL_DIR" || FAILURES=$((FAILURES + 1))
  fi
fi

if [[ "$CHECK_PORTS" -eq 1 ]]; then
  onecode_check_port_free "LibreChat shell" "$LIBRECHAT_PORT" || FAILURES=$((FAILURES + 1))
  onecode_check_port_free "OneCode kernel API" "$ONECODE_PORT" || FAILURES=$((FAILURES + 1))
  onecode_check_port_free "MongoDB" "$MONGO_PORT" || FAILURES=$((FAILURES + 1))
fi

if [[ "$FAILURES" -gt 0 ]]; then
  echo "status: blocked ($FAILURES issue(s))" >&2
  exit 1
fi

echo "status: ok"
