# OneCode Harbor 接入协议与环境契约规范

**日期**：2026-11-02  
**版本**：v1.0.0  
**状态**：正式制定（Phase V 步骤 2.4）  
**约束基线**：在遵循本契约并在 Harbor 评测流水线上实际跑通之前，所有宿主机评测与本地/远端 Docker 容器验真记录一律严格保持 `harbor: false`。`harbor: true` 仅且必须在 Harbor 评测平台原生调用中写入。

---

## 1. 契约目标与职责边界

本契约规范 OneCode 与 Harbor Agent Benchmark 评测 harness 之间的输入目录、环境参数、工作区生命周期、隐藏测试隔离及评分日志交付契约。

- **OneCode Agent 职责**：在隔离工作区内读取题目需求、完成代码分析与打补丁，保持宿主与容器安全边界；
- **Harbor Harness 职责**：提供只读题目包、分配独立工作区、挂载隐藏测试集并采集验真结果；
- **分界红线**：
  - 无论是否使用 Docker 容器，非 Harbor 评测调用的产物严禁标记为 `harbor: true`；
  - 隐藏测试（`verifier.py`）严禁在模型推理与修改阶段暴露给模型代码生成环境。

---

## 2. 环境变量契约（Environment Variables）

Harbor 调度器启动 OneCode 执行评测任务时，必须注入以下标准环境变量：

| 变量名 | 类型 | 是否必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `HARBOR_TASK_ID` | `string` | 是 | 评测任务唯一标识符（如 `api_contract-hard-openapi_params`） |
| `HARBOR_TASK_PACKAGE` | `path` | 是 | 只读题目包绝对路径（包含 `instruction.md`、`environment/` 等） |
| `HARBOR_WORKSPACE` | `path` | 是 | 分配给该任务的独立可写工作区根目录 |
| `HARBOR_HIDDEN_TESTS` | `path` | 是 | 隐藏断言验真脚本路径（只在评分阶段挂载进验真容器） |
| `HARBOR_LOG_DIR` | `path` | 是 | 评分结果落盘目录（容器向此挂载点输出 `reward.txt` 与 `reward.json`） |
| `HARBOR_IMAGE` | `string` | 否 | 验真容器基础镜像，默认 `python:3.12-slim-amd64` |
| `HARBOR_EVAL_MODE` | `string` | 否 | 运行模式，`container`（默认）或 `host` |

---

## 3. 目录布局与挂载拓扑（Directory Topology）

Harbor 平台上的物理与容器挂载拓扑定义如下：

```
/harbor/
├── task_packages/           # [只读 RO] 题目数据包根目录
│   └── <task_id>/
│       ├── instruction.md   # 任务需求说明
│       ├── task.toml        # 任务元数据（难度、超时等）
│       └── environment/     # 初始源码骨架包
│           └── workspace.tar.gz
│
├── workspaces/              # [读写 RW] 任务独立运行工作区
│   └── <run_id>/
│       ├── <解压后的源码文件>
│       ├── .onecode_host_verifier  # 工作区级验真指针
│       └── .onecode/        # 内核断点、Trace 与 Ledger
│
├── hidden_tests/            # [只读 RO，仅验真容器挂载]
│   └── <task_id>/
│       ├── verifier.py      # 外置隐藏断言脚本
│       └── verifier.toml
│
└── eval_logs/               # [读写 RW] 评分输出目录
    └── <run_id>/
        ├── container.cid    # 64 位十六进制容器 ID
        ├── reward.txt       # 单一标量奖励（0.0 ~ 1.0）
        └── reward.json      # 结构化断言细则与错误摘要
```

---

## 4. 验真容器执行协议（Container Execution Protocol）

在 `HARBOR_EVAL_MODE=container` 下，验真过程必须遵循严格的容器调用契约：

```bash
docker run --rm \
  --cidfile "${HARBOR_LOG_DIR}/container.cid" \
  --network none \
  --memory 512m \
  --cpus 1 \
  --pids-limit 256 \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --security-opt no-new-privileges \
  --mount "type=bind,src=${HARBOR_WORKSPACE},dst=/workspace" \
  --mount "type=bind,src=${HARBOR_LOG_DIR},dst=/log_dir" \
  --mount "type=bind,src=${HARBOR_HIDDEN_TESTS}/verifier.py,dst=/verifier/verifier.py,readonly" \
  --mount "type=bind,src=${HARBOR_WORKSPACE}/.onecode,dst=/workspace/.onecode,readonly" \
  --env "WORKSPACE=/workspace" \
  --env "LOG_DIR=/log_dir" \
  --env "PYTHONSAFEPATH=1" \
  --workdir /workspace \
  "${HARBOR_IMAGE}" \
  python3 /verifier/verifier.py
```

### 交付物契约
1. **`reward.txt`**：纯文本浮点数字符串（`0.0` 至 `1.0`）；
2. **`reward.json`**：包含 `overall`、`tests_passed`、`tests_total` 及逐项 `tests` 断言结果的有效 JSON；
3. **`container.cid`**：Docker 实际写入的 64 位小写十六进制字符串。

---

## 5. 通过与写盘规则

1. **严格通过条件**：
   - 容器进程退出码为 `0`；
   - `reward.txt` 内容可转换为浮点数且严格等于 `1.0`。
2. **`harbor` 字段准入**：
   - 当且仅当由 Harbor Harness 通过检测到上述 `HARBOR_*` 契约且在平台评测流水线上运行时，结果 JSONL 中写入 `"harbor": true`；
   - 本地开发、单机脚本执行（如 `bench_workbuddy.py`）或非 Harbor 流水线触发的评测，无论是否带有容器隔离，均必须写入 `"harbor": false`。
