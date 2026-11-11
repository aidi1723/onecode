# OneCode Security Architecture & Adversarial Verification
# OneCode 安全纵深防御架构与对抗验证说明

> **Positioning / 定位说明**：OneCode does not rely on system-prompt "please don't cheat" instructions. Every critical security invariant is enforced in deterministic Python kernel code before shell execution, file mutation, HTTP request routing, or final artifact delivery.  
> OneCode 不依赖提示词层面的“口头约束”来防作弊，所有核心安全边界均在内核态 Python 代码中通过确定性拦截器强制执行——在命令执行、文件落盘、HTTP 路由与最终交付签发前进行硬门禁校验。  
> **Container Isolation Prerequisite / 强隔离前提**：Full container/network isolation (`--network none --cap-drop ALL --read-only`) requires Docker (`onecode doctor` -> `production_ready: true`). Host fallback without Docker runs commands on the local machine under software guards only and is intended strictly for trusted local workspaces ([SECURITY.md](../SECURITY.md)).

---

## 1. Threat Model: Real Coding-Agent Failure Modes / 威胁模型：自主编码 Agent 的典型风险

When granting an autonomous LLM coding agent filesystem and terminal access, failures fall into two categories:
1. **Unintentional Agent Shortcuts ("Reward Hacking") / 模型走捷径与幻觉交付**：Weakening or editing preset tests, injecting shadow `unittest.py`/`sitecustomize.py` modules, embedding `os._exit(0)` in `src/`, using `python3 -c "..."` one-liners to bypass patch tools, or claiming a fix succeeded while tests still fail.
2. **Unsafe Execution & Host Exposure / 危险命令与宿主暴露**：Running `rm -rf` / `git reset --hard`, escaping workspace via symlinks or `../`, leaking `.env` / `.git/config` secrets into context, exposing unauthenticated loopback gateways to DNS rebinding / CSRF, leaking API keys over HTTP redirects, or running with published placeholder credentials.

OneCode enforces **six defense-in-depth layers** against these vectors.

---

## 2. Six-Layer Defense-in-Depth Architecture / 六层安全纵深防御架构

### Layer 1: Workspace Isolation & Secret Protection (`PathGuard`)
- **Implementation / 实现模块**：[`src/onecode/kernel/path_guard.py`](../src/onecode/kernel/path_guard.py) (`PathGuard`, `PathGuardError`)
- **Mechanisms / 核心机制**：
  - **Path Canonicalization & Traversal Blocking (`resolve_target`)**：Rejects empty paths, null bytes (`\x00`), absolute host paths, and `..` escapes leaving the resolved workspace root.
  - **Symlink Jailbreak Blocking (`_reject_symlinks`)**：Inspects workspace path prefixes to reject symlinks before any write/patch operation resolves outside the sandbox.
  - **Control-Plane Protection (`DENIED_ROOT_FILES`, `DENIED_EXECUTABLE_ROOT_FILES`, `DENIED_DIRECTORIES`)**：Blocks writes to `.git`, `.github`, `.onecode`, `pyproject.toml`, `.gitignore`, `.env`, `Makefile`, `setup.py`, `setup.cfg`, and `.pre-commit-config.yaml`.
  - **Sensitive Secret Read Guard (`is_sensitive_read_path` / `resolve_read_target`)**：Blocks model `read_file` probes targeting `.env`, `.env.*`, `.git/config`, private key material, and credential stores (`sensitive_read_denied`).
  - **Atomic Durable Writes & Cleanup (`write_text`, `discard_interrupted_writes`)**：Writes via temporary sibling file with `os.fsync()` + `os.replace()` and cleans interrupted temp files on recovery.

### Layer 2: Verifier Integrity, Anti-Tamper & Rollback
- **Implementation / 实现模块**：[`src/onecode/kernel/preset_tests.py`](../src/onecode/kernel/preset_tests.py), [`src/onecode/kernel/terminal_loop.py`](../src/onecode/kernel/terminal_loop.py), [`src/onecode/kernel/model_provider.py`](../src/onecode/kernel/model_provider.py)
- **Mechanisms / 核心机制**：
  - **Multi-Language Preset Test Immutability (`is_preset_test_path`, `TerminalSession`)**：Blocks edits/patches to existing Python (`tests/`, `test_*.py`), Go (`*_test.go`), TypeScript/JS (`*.spec.ts`, etc.), and Rust (`*_test.rs`) verification targets (`preset_test_immutable`).
  - **Shadow Module Blocking (`PathGuard.DENIED_ROOT_FILES` & lexical controls)**：Prevents creating `unittest.py`, `pytest.py`, `conftest.py`, `sitecustomize.py`, or `usercustomize.py` anywhere (root or nested `src/`) to hijack `python3 -m unittest` or `pytest`.
  - **AST Malicious Payload Rejection (`validate_model_plan` / `_reject_unusable_python_assets`)**：Statically inspects generated Python assets via AST to reject embedded `pytest`/`unittest` imports (including dynamic `__import__('unittest')`) and `os._exit(...)` short-circuits in production modules.
  - **Pre-Exec Inline Script Interception (`run_terminal_session`)**：Inspects inline shell/interpreter commands such as `python3 -c "open(...).write(...)"` targeting protected tests or bypassing write policies and halts BEFORE executing the command (`preset_test_immutable`).
  - **Automatic Failure Rollback (`rollback_on_failure=True`)**：Restores modified source files to their pre-session snapshot automatically if an anti-tamper breach or failed session halts execution.

### Layer 3: Scoped Capabilities, Destructive Command Firewall & Plan Guardrails
- **Implementation / 实现模块**：[`src/onecode/kernel/execution_scope.py`](../src/onecode/kernel/execution_scope.py), [`src/onecode/kernel/execution_guardrails.py`](../src/onecode/kernel/execution_guardrails.py)
- **Mechanisms / 核心机制**：
  - **Three Capability Tiers (`ExecutionScope`)**：
    - `READ_ONLY`: Allows inspection actions only; blocks `patch` and mutating shell commands (`scope_violation`).
    - `PATCH_GUARDED`: Allows scoped code edits and safe test commands while blocking destructive commands.
    - `FULL_TERMINAL`: Autonomous terminal session, still constrained by `PathGuard`, anti-tamper, and destructive firewall.
  - **Destructive Command Firewall (`is_destructive_command`)**：Detects direct and shell-wrapped (`bash -c ...` / `sh -c ...`) destructive invocations including `rm -rf`, `unlink`, `shred`, `dd`, `mkfs`, `shutdown`, `kill`, `git reset --hard`, `git clean -f`, and `git push --force`.
  - **Plan Validation & Mandatory Human Approval (`validate_plan`, `should_require_approval`)**：Enforces `GuardrailConfig` caps (`max_steps`, `max_tool_calls_per_step`, `forbidden_tools`, dependencies, time budget) and forces human approval on external `mcp.*` actions or `review`/`manual` approval modes.

### Layer 4: Kernel-Isolated Delivery Gatekeeper & SHA-256 Audit Chain
- **Implementation / 实现模块**：[`src/onecode/web/api_shell.py`](../src/onecode/web/api_shell.py), [`src/onecode/kernel/checkpoint.py`](../src/onecode/kernel/checkpoint.py), [`src/onecode/kernel/inspection.py`](../src/onecode/kernel/inspection.py), [`src/onecode/kernel/run_inspection.py`](../src/onecode/kernel/run_inspection.py)
- **Mechanisms / 核心机制**：
  - **No Fake "Fixed" Delivery (`verify_shell_write`)**：Regardless of model prose output, code changes are executed against the isolated test suite (`unittest` / `pytest` / project verifier); non-zero exit codes set `status="halted"` and `delivery_status="blocked"`.
  - **Global WAL & Chained SHA-256 Evidence Ledger (`global-ledger.jsonl`, `evidence-chain.jsonl`)**：Records SHA-256 digests of modified assets and preset tests plus hash-linked audit entries (`previous_chain_hash` -> `chain_hash`). Post-run tampering on workspace outputs or audit logs is detected by `ledger_matches_workspace()` (`asset_hash_mismatch` / `preset_test_hash_mismatch`) and `validate_evidence_chain()` (`evidence_chain_hash_mismatch`).

### Layer 5: Container Sandbox Hardening (`SandboxConfig`)
- **Implementation / 实现模块**：[`src/onecode/kernel/sandbox.py`](../src/onecode/kernel/sandbox.py) (`SandboxConfig`, `build_docker_command`)
- **Hardened Container Flags / 默认容器加固参数**：
  - `--network none` (network egress disabled during verification)
  - `--cap-drop ALL` + `--security-opt no-new-privileges` (no capability escalation)
  - `--read-only` root filesystem + `--tmpfs /tmp:rw,noexec,nosuid,size=64m`
  - `--pids-limit 256`, `--memory 512m`, `--cpus 1` (fork-bomb & resource bounds)
  - `--user <uid>:<gid>` (non-root host UID/GID execution)
  - `--env PYTHONSAFEPATH=1` & `--env PYTHONDONTWRITEBYTECODE=1`
  - Read-only bind mounts (`readonly`) for `.git`, `.github`, `.onecode`, and `tests`.

### Layer 6: HTTP Gateway, Redirect Secret Protection & Deployment Boundary
- **Implementation / 实现模块**：[`src/onecode/kernel/http_safety.py`](../src/onecode/kernel/http_safety.py), [`src/onecode/web/auth.py`](../src/onecode/web/auth.py), [`src/onecode/web/api.py`](../src/onecode/web/api.py), [`src/onecode/kernel/deployment_boundary.py`](../src/onecode/kernel/deployment_boundary.py)
- **Mechanisms / 核心机制**：
  - **Redirect Credential Stripping (`StripAuthRedirectHandler`, `should_strip_redirect_auth`)**：Automatically strips `Authorization` and `api-key` headers across HTTP cross-host redirects or `https://` -> `http://` scheme downgrades.
  - **DNS Rebinding & CSRF Origin Blocking (`local_request_allowed`, `request_authorized`)**：Enforces loopback `Host` header + bound port validation and strict `Origin` allowlisting, plus constant-time `secrets.compare_digest` bearer checks.
  - **Safe Server Binding (`run_server`)**：Refuses to bind non-loopback addresses (`0.0.0.0`) unless authentication is properly configured.
  - **Weak Credential & File-Permission Rejection (`api_token`, `deployment_boundary`)**：Rejects published sample tokens (`dev-local-token`, `OneCode123!`) and ignores POSIX group/world-readable token files (`st_mode & 0o077 != 0`, e.g., `0o644`), accepting only hardened `0o600` files or non-default environment tokens.

---

## 3. Reproducible Adversarial Red-Team Benchmark (`18/18`) / 可复现对抗安全测试套件

Rather than relying on qualitative claims, OneCode ships a **zero-API-key, deterministic 18-case red-team test harness** ([`scripts/security_benchmark.py`](../scripts/security_benchmark.py)) backed by CI unit verification ([`tests/test_security_suite.py`](../tests/test_security_suite.py)). Every attack runs directly against the live OneCode kernel modules.
> **Note**: This benchmark is a self-authored deterministic regression suite validating known kernel defenses against scripted exploit vectors; it is not a third-party external penetration audit.

### Reproduce Locally / 本地一键复现

```bash
# Run adversarial security suite (Markdown summary table)
PYTHONPATH=src python3 scripts/security_benchmark.py

# Run adversarial security suite (machine-readable JSON)
PYTHONPATH=src python3 scripts/security_benchmark.py --json

# Run as part of unittest verification
PYTHONPATH=src python3 -m unittest tests/test_security_suite.py -v
```

### Observed Benchmark Matrix (`18/18` Blocked / Enforced) / 实测对抗矩阵

| ID | Category / 防御层 | Attack Vector / 模拟攻击手法 | Result / 结果 | Enforcing Kernel Defense / 生效内核机制 |
| :--- | :--- | :--- | :---: | :--- |
| `SEC-01` | Filesystem Isolation | `../../etc/cron.d/pwn`, `/tmp/abs.py`, null-byte `\x00` write | **BLOCKED/PASS** | `PathGuard.resolve_target` |
| `SEC-02` | Filesystem Isolation | Symlink directory jailbreak write outside workspace | **BLOCKED/PASS** | `PathGuard._reject_symlinks` |
| `SEC-03` | Secret Protection | Model `read_file` on `.env`, `.env.production`, `.git/config` | **BLOCKED/PASS** | `PathGuard.is_sensitive_read_path` |
| `SEC-04` | Filesystem Isolation | Overwrite `.git/hooks`, `.github/workflows`, `.onecode/`, `pyproject.toml`, `Makefile` | **BLOCKED/PASS** | `PathGuard._reject_lexical_controls` |
| `SEC-05` | Verifier Integrity | Direct `patch` on Python/Go/TS/Rust preset tests | **BLOCKED/PASS** | `TerminalSession Anti-Tamper` |
| `SEC-06` | Verifier Integrity | Shadow test module injection (`unittest.py`, `pytest.py`, `conftest.py`, `sitecustomize.py`, `usercustomize.py`, root + `src/`) | **BLOCKED/PASS** | `PathGuard shadow guard` |
| `SEC-07` | Verifier Integrity | AST test-framework import (`pytest`, `__import__('unittest')`) & `os._exit(0)` in `src/` | **BLOCKED/PASS** | `AST Asset Verifier` |
| `SEC-08` | Verifier Integrity | `python3 -c` one-liner dual write bypass before shell execution | **BLOCKED/PASS** | `run_terminal_session pre-exec guard` |
| `SEC-09` | Verifier Integrity | Post-edit test tampering triggers session halt & `rollback_on_failure` | **BLOCKED/PASS** | `Anti-Tamper + rollback_on_failure` |
| `SEC-10` | Command Guardrails | Mutating `patch` / non-inspection shell command under `READ_ONLY` scope | **BLOCKED/PASS** | `ToolCapabilityPolicy(READ_ONLY)` |
| `SEC-11` | Command Guardrails | Destructive firewall (`rm -rf`, `bash -c rm`, `git reset --hard`, `git push --force`, `dd`, `kill -9`) | **BLOCKED/PASS** | `ToolCapabilityPolicy(PATCH_GUARDED)` |
| `SEC-12` | Command Guardrails | `forbidden_tools` in `ExecutionPlan` & mandatory approval on `mcp.*` tools | **BLOCKED/PASS** | `ExecutionGuardrails` |
| `SEC-13` | Delivery Gatekeeper | Failing `unittest` forces `status=halted` & `delivery_status=blocked` | **BLOCKED/PASS** | `verify_shell_write(unittest)` |
| `SEC-14` | Audit Integrity | Post-run file tampering & ledger record modification caught by SHA-256 verification | **BLOCKED/PASS** | `SHA-256 WAL & validate_evidence_chain` |
| `SEC-15` | Container Sandbox | Verifies `--network none`, `--cap-drop ALL`, `--read-only`, `--security-opt no-new-privileges`, `--pids-limit 256`, `PYTHONSAFEPATH=1`, readonly protected mounts | **BLOCKED/PASS** | `SandboxConfig.build_docker_command` |
| `SEC-16` | Network & Auth | Strips `Authorization` and `api-key` on HTTPS->HTTP downgrade & cross-host redirect | **BLOCKED/PASS** | `StripAuthRedirectHandler` |
| `SEC-17` | Network & Auth | Blocks DNS-rebinding `Host`, rogue `Origin` CSRF, invalid Bearer, and unauthenticated `0.0.0.0` bind | **BLOCKED/PASS** | `web.auth + run_server` |
| `SEC-18` | Network & Auth | Rejects published default tokens (`dev-local-token`) and permissive `0o644` token files; accepts `0o600` | **BLOCKED/PASS** | `deployment_boundary.api_token` |

---

## 4. Honest Operational Scope & Boundaries / 诚实边界说明

- **With vs. Without Docker / 有无 Docker 的区别**：In container mode (`SandboxConfig`), verification executes under `--network none --cap-drop ALL --read-only` with OS-level read-only mounts for tests and `.git`. On hosts running fallback `host` execution without Docker, software guards (`PathGuard`, `ToolCapabilityPolicy`, pre-exec interception, `rollback_on_failure`) remain active, while kernel OS-level syscall isolation requires running with Docker enabled (see `deployment_boundary()["production_ready"]`).
- **Not a Real-Time Safety PLC Replacement / 不替代工业硬件联锁**：OneCode secures offline code generation, operational scripts, and verification workflows — never real-time millisecond PLC/SIS closed-loop actuation.
- **Vulnerability Disclosure / 漏洞披露**：Please refer to [SECURITY.md](../SECURITY.md) for coordinated vulnerability reporting.
