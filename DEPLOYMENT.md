# OneCode Deployment / OneCode 部署说明

This guide describes the local deployment path for the OneCode kernel and the
bundled custom Web shell.

本文说明 OneCode 内核和内置定制 Web 壳的本地部署方式。

## Requirements / 环境要求

- Python 3.11 or newer.
  Python 3.11 或更新版本。
- Node.js 20 or newer, plus npm.
  Node.js 20 或更新版本，以及 npm。
- macOS or Linux for the local preview path.
  本地预览路径建议使用 macOS 或 Linux。
- Network access is needed only for `npm install` and optional Python package
  installation.
  只有执行 `npm install` 和可选 Python 包安装时需要联网。

The core kernel has no runtime third-party dependency. The bundled Web shell is
a LibreChat-based Node application and requires its own npm dependencies.

核心内核运行时不依赖第三方库。内置 Web 壳基于 LibreChat，是 Node 应用，需要单独安装 npm 依赖。

## 1. Get The Source / 获取源码

```bash
git clone https://github.com/aidi1723/onecode.git
cd onecode
```

If you already have the repository, pull the latest `main` branch.

如果已经有仓库，拉取最新 `main` 分支即可。

## 2. Install The Kernel / 安装内核

Editable local install:

本地可编辑安装：

```bash
pip install -e .
```

For source-tree execution without installing:

如果不安装、直接从源码树运行：

```bash
PYTHONPATH=src python3 -m onecode doctor
```

## 3. Verify The Kernel / 验证内核

Fast verification:

快速验证：

```bash
bash scripts/verify-core.sh
```

Expected result:

预期结果：

```text
185 tests OK
doctor status: ok
```

Full local verification:

完整本地验证：

```bash
bash scripts/verify.sh
```

## 4. Install The Web Shell / 安装 Web 壳

The bundled custom shell is located at `shell/onecode-librechat`.

内置定制壳位于 `shell/onecode-librechat`。

```bash
cd shell/onecode-librechat
npm install
cd ../..
```

Do not commit `node_modules`, `.env`, local logs, or runtime data. They are
runtime artifacts.

不要提交 `node_modules`、`.env`、本地日志或运行数据，这些都是运行期产物。

## 5. Start Kernel And Shell Together / 同时启动内核和壳

From the repository root:

在仓库根目录执行：

```bash
PYTHONPATH=src python3 -m onecode shell --show-credentials
```

What this command starts:

这个命令会启动：

- OneCode API on `127.0.0.1:19080`.
  OneCode API：`127.0.0.1:19080`。
- The custom LibreChat Web shell on `127.0.0.1:14080`.
  定制 LibreChat Web 壳：`127.0.0.1:14080`。
- A local temporary MongoDB process on `127.0.0.1:39017`.
  本地临时 MongoDB 进程：`127.0.0.1:39017`。
- A local preview account.
  本地预览账号。

Open:

打开：

```text
http://127.0.0.1:14080/c/new
```

Default local preview login:

默认本地预览账号：

```text
Email: onecode@local.test
Password: OneCode123!
```

Stop the services with `Ctrl+C` in the terminal running `onecode shell`.

在运行 `onecode shell` 的终端按 `Ctrl+C` 停止服务。

## 6. API-Only Deployment / 只部署内核 API

Use API-only mode when another shell, gateway, or integration layer will call
OneCode directly.

当其他壳、网关或集成层直接调用 OneCode 时，使用 API-only 模式。

```bash
PYTHONPATH=src ONECODE_API_TOKEN=dev-local-token \
  python3 -m onecode serve --host 127.0.0.1 --port 19080
```

Health check:

健康检查：

```bash
curl -sS http://127.0.0.1:19080/health
```

OpenAI-compatible endpoint base:

OpenAI-compatible 端点基础地址：

```text
http://127.0.0.1:19080/v1
```

## 7. Useful Options / 常用参数

Use custom ports:

使用自定义端口：

```bash
PYTHONPATH=src python3 -m onecode shell \
  --onecode-port 19080 \
  --librechat-port 14080 \
  --mongo-port 39017
```

Use a custom workspace:

使用自定义工作区：

```bash
PYTHONPATH=src python3 -m onecode shell \
  --workspace /absolute/path/to/workspace
```

Start without opening the browser:

启动但不自动打开浏览器：

```bash
PYTHONPATH=src python3 -m onecode shell --no-browser
```

Use a separate development shell checkout:

使用单独的开发版壳目录：

```bash
PYTHONPATH=src python3 -m onecode shell \
  --librechat-dir /absolute/path/to/onecode-librechat
```

## 8. Runtime Files / 运行期文件

The launcher creates runtime directories needed by the shell before startup.
The public repository includes only an empty placeholder under
`shell/onecode-librechat/data/`; it does not include local logs, databases, or
private environment files.

启动器会在启动前创建壳需要的运行目录。公开仓库只在
`shell/onecode-librechat/data/` 下包含空占位文件，不包含本地日志、数据库或私有环境文件。

## 9. Troubleshooting / 故障排查

If `onecode shell` reports missing LibreChat dependencies:

如果 `onecode shell` 报告缺少 LibreChat 依赖：

```bash
cd shell/onecode-librechat
npm install
cd ../..
```

If port `14080`, `19080`, or `39017` is occupied, either stop the existing
process or start OneCode with custom ports.

如果 `14080`、`19080` 或 `39017` 端口被占用，停止已有进程，或用自定义端口启动 OneCode。

If the browser shows an old frontend after frontend edits, rebuild the shell:

如果修改前端后浏览器仍显示旧页面，重建壳前端：

```bash
cd shell/onecode-librechat
npm run build:client
cd ../..
```

Then restart `onecode shell`.

然后重启 `onecode shell`。

## Production Boundary / 生产边界

The bundled command is a local deployment and evaluation path. Production
deployment should add an operator-owned gateway, TLS, authentication policy,
request-size limits, rate limiting, persistent database planning, backup
policy, and environment-specific secret management.

内置命令是本地部署和评估路径。生产部署应增加使用方掌控的网关、TLS、鉴权策略、请求大小限制、限流、持久化数据库规划、备份策略和环境级密钥管理。
