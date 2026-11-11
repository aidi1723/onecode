# OneCode 审核整改实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 2026-09-29 审核报告，先堵住已证实的安全边界和本地验证失真，再把架构拆分留到后续批次。

**Architecture:** 每一项都走同一条工作流：红（先写失败测试）→ 绿（最小改动让测试通过）→ 复跑相邻测试。不改易经运行时，不拆大文件，不改 git 历史。默认安全：Web 写操作必须审批，路径检查看解析后的结果，子进程不继承密钥。

**Tech Stack:** Python 3.11+，标准库 `unittest`，现有 `PathGuard` / `run_model_task` / `verify.sh`。

**依据:** `reports/ONECODE_AUDIT_REPORT_2026-09-29.md`。本计划只执行第一批。第二、三批写在文末，本轮不改代码。

---

## 工作流

每一项重复这四步，做完再进下一项：

1. 在现有测试文件里加一条断言，描述修完后的行为。
2. 只跑这条测试，确认它因为旧行为失败。
3. 改最少的生产代码让它通过。
4. 跑该模块的测试文件，以及 `scripts/check_source_quality.py`。

不在本轮提交。提交需要单独要求。

## 本轮要改的文件

- `src/onecode/kernel/path_guard.py`：解析前拒绝 `..`，解析后按小写比对 `.git` / `.github` / `.onecode` 和根目录敏感文件，写入路径上的符号链接直接拒绝。
- `src/onecode/web/api.py`：`/resume` 传入 `require_explicit_approval=True`；每个 HTTP 方法先检查 Host 和 Origin。
- `src/onecode/web/request_body.py`：带了非 `application/json` 的 Content-Type 时返回 415。
- `src/onecode/web/auth.py`：新增本地 Host / Origin 判断。
- `src/onecode/kernel/model_config.py`：endpoint 的协议或主机变化时，不再沿用旧 API key。
- `src/onecode/kernel/verifier.py`：子进程使用 `execution_tools._command_environment()`。
- `src/onecode/cli_commands/local_interfaces.py`、`src/onecode/shell_launcher.py`：省略令牌和密码时生成并持久化随机值；关闭开放注册。
- `scripts/verify.sh`：运行解释器时把本仓库 `src` 放在 `PYTHONPATH` 最前。不使用 `export PYTHONPATH`，现有测试禁止这行。
- `src/onecode/tui/app.py`：默认工作区改为当前目录，可用 `ONECODE_TUI_WORKSPACE` 覆盖。

## Task 1：PathGuard

**Files:** `tests/test_path_guard.py`，`src/onecode/kernel/path_guard.py`

- [x] 测试拒绝 `nested/../.env`、`.GIT/hooks/pre-commit`、`.ENV`、仓库内符号链接，以及读取 `.ENV`。
- [x] 确认这些测试在旧实现上失败。
- [x] 按上面的规则改 `PathGuard`。
- [x] `PYTHONPATH=src python -m unittest tests.test_path_guard` 通过。

## Task 2：resume 审批

**Files:** `tests/test_web_api.py`，`src/onecode/web/api.py`

- [x] `test_onecode_resume_endpoint_runs_model_with_resume_from_run_id` 断言 `require_explicit_approval is True`。
- [x] 确认失败后，只在 resume 调用处传入 `True`。不改 `run_model_task` 的默认值，避免 CLI 行为被连带改变。
- [x] resume 相关测试通过。

## Task 3：本地 Web 边界

**Files:** `tests/test_web_api.py`，`tests/test_model_config.py`，`src/onecode/web/request_body.py`，`src/onecode/web/auth.py`，`src/onecode/web/api.py`，`src/onecode/kernel/model_config.py`

- [x] `Content-Type: text/plain` 返回 415；没有该头时仍接受，避免打断现有调用。
- [x] Host 不是回环地址加实际端口时拒绝；Origin 若存在，必须是本服务自己的 `http://127.0.0.1|localhost|[::1]:端口`。LibreChat 服务端请求不带 Origin，不受影响。
- [x] 同一主机只改路径时仍可沿用旧 key（现有测试覆盖 `/v1` 到 `/v1/chat/completions`）。换成另一台主机且 key 为空时返回错误，原 key 保持不变。
- [x] `tests.test_model_config` 与相关 web 测试通过。

## Task 4：verifier 环境

**Files:** `tests/test_verifier.py`，`src/onecode/kernel/verifier.py`

- [x] verifier 执行 `python3 -c` 打印 `OPENAI_API_KEY` 时，输出里不能出现该值。
- [x] `subprocess.run(..., env=_command_environment())`。
- [x] `tests.test_verifier` 通过。

## Task 5：shell 默认凭据

**Files:** `tests/test_shell_launcher.py`，`src/onecode/cli_commands/local_interfaces.py`，`src/onecode/shell_launcher.py`

- [x] 省略 `--api-token` 和 `--password` 时，两次解析得到同一组随机值，且不等于 `dev-local-token` / `OneCode123!`，并写入 state 目录。
- [x] `ALLOW_REGISTRATION` 改为 `false`，同步修改对应断言。
- [x] 显式传入的令牌和密码保持原样。`ShellLaunchConfig` 的数据类默认值不动，避免无关测试大面积变化。

## Task 6：verify.sh 与 TUI 默认目录

**Files:** `tests/test_verify_script.py`，`scripts/verify.sh`，`src/onecode/tui/app.py`

- [x] 脚本在 compileall、质量检查、unittest、doctor 前把 `${REPO_SRC}` 放到 `PYTHONPATH` 前面。
- [x] 不出现 `export PYTHONPATH`。
- [x] TUI 默认工作区不再是 `/private/tmp/oneword-tui-live`。

## 验收

```bash
PYTHONPATH=src python -m unittest \
  tests.test_path_guard \
  tests.test_verifier \
  tests.test_model_config \
  tests.test_shell_launcher \
  tests.test_verify_script \
  tests.test_web_api \
  tests.test_tui_layout
PYTHONPATH=src python scripts/check_source_quality.py src
```

## 本轮明确不做

| 批次 | 内容 | 原因 |
|---|---|---|
| 第二批 | README 16 个失效链接、`tmp/` 与 `output/` 移出 git、verifier 可执行文件名校验、审批计划 HMAC | 文档和仓库卫生需要单独确认；后两项要再核对调用方 |
| 第三批 | 抽出易经运行时策略表、拆 `web/api.py` 与 `cli.main`、接入 ruff/mypy | 行为等价重构，不和安全修复混在同一次改动里 |
