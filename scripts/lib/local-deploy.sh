#!/usr/bin/env bash

onecode_have_command() {
  command -v "$1" >/dev/null 2>&1
}

onecode_python_bin() {
  if [[ -n "${PYTHON:-}" ]]; then
    printf '%s\n' "$PYTHON"
  elif [[ -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
    printf '%s\n' "$VIRTUAL_ENV/bin/python"
  elif [[ -x ".venv/bin/python" ]]; then
    printf '%s\n' ".venv/bin/python"
  else
    printf '%s\n' "python3"
  fi
}

onecode_check_command() {
  local label="$1"
  local command_name="$2"
  local hint="$3"

  if onecode_have_command "$command_name"; then
    printf 'ok: %s (%s)\n' "$label" "$(command -v "$command_name")"
    return 0
  fi

  printf 'missing: %s (%s)\n' "$label" "$command_name" >&2
  printf 'hint: %s\n' "$hint" >&2
  return 1
}

onecode_check_python() {
  local python_bin="$1"

  if "$python_bin" --version >/dev/null 2>&1; then
    printf 'ok: python (%s)\n' "$("$python_bin" --version 2>&1)"
    return 0
  fi

  printf 'missing: python (%s)\n' "$python_bin" >&2
  printf 'hint: install Python 3.10+ or set PYTHON=/path/to/python.\n' >&2
  return 1
}

onecode_check_pip() {
  local python_bin="$1"

  if "$python_bin" -m pip --version >/dev/null 2>&1; then
    printf 'ok: pip (%s)\n' "$("$python_bin" -m pip --version 2>&1)"
    return 0
  fi

  printf 'missing: pip for %s\n' "$python_bin" >&2
  printf 'hint: install pip for this Python interpreter, or use a virtualenv with pip.\n' >&2
  return 1
}

onecode_check_shell_tree() {
  local shell_dir="$1"

  if [[ -f "$shell_dir/package.json" ]]; then
    printf 'ok: bundled shell (%s)\n' "$shell_dir"
    return 0
  fi

  printf 'missing: bundled shell package.json (%s/package.json)\n' "$shell_dir" >&2
  printf 'hint: use a full repository checkout that includes shell/onecode-librechat.\n' >&2
  return 1
}

onecode_check_shell_deps() {
  local shell_dir="$1"

  if [[ -d "$shell_dir/node_modules" ]]; then
    printf 'ok: shell dependencies (%s/node_modules)\n' "$shell_dir"
    return 0
  fi

  printf 'missing: shell dependencies (%s/node_modules)\n' "$shell_dir" >&2
  printf 'hint: run bash scripts/install-local.sh, or npm install --prefix %s.\n' "$shell_dir" >&2
  return 1
}

onecode_port_in_use() {
  local port="$1"

  if onecode_have_command lsof; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi

  "$PYTHON_BIN" - "$port" <<'PY'
import socket
import sys

port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sys.exit(0 if sock.connect_ex(("127.0.0.1", port)) == 0 else 1)
PY
}

onecode_check_port_free() {
  local label="$1"
  local port="$2"

  if onecode_port_in_use "$port"; then
    printf 'busy: %s port %s\n' "$label" "$port" >&2
    printf 'hint: stop the existing process, or pass a custom port to scripts/start-local.sh.\n' >&2
    return 1
  fi

  printf 'ok: %s port %s is free\n' "$label" "$port"
  return 0
}

onecode_arg_value() {
  local name="$1"
  shift

  while [[ $# -gt 0 ]]; do
    if [[ "$1" == "$name" && $# -gt 1 ]]; then
      printf '%s\n' "$2"
      return 0
    fi
    shift
  done

  return 1
}
