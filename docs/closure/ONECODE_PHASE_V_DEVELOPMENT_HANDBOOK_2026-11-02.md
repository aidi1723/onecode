# OneCode Phase V：容器内验真、受控并发与 Harbor 接入准备

**日期**：2026-11-02  
**起点**：Phase IV 的主机验真分数。扩展四题的当前工作区复判都是 1.0，合计 47/47。这不是同一份 jsonl 里的一次四题连跑。  
**目标环境**：Linux `n100`（`10.0.0.184`，Ubuntu 24.04 x86_64，Docker 29.1.3，Python 3.12.3）

## 1. Phase IV 封板时已经落地的事实

- `pyproject.toml` 保持 `dependencies = []`。当前工作区相对 `HEAD`，`hexagram.py` 没有未提交改动。
- `run_host_verifier` 在主机上执行外部 `verifier.py`。通过条件是进程退出码 0 且 `reward.txt` 为 1.0。记录字段保持 `harbor: false`。
- `ONECODE_FALLBACK_ENDPOINT`、`ONECODE_FALLBACK_API_KEY`、`ONECODE_FALLBACK_MODEL` 由 `_post_model_json` 读取。主通道抛出 `ModelProviderError` 或 `ModelProviderTimeout`，且备用端点与主键都已设置、端点与主通道不同时，才改打备用通道。未设置时不转移。评测脚本若替换了 `_post_model_json`，这条路径不会生效。
- `scripts/bench_workbuddy.py` 负责解包工作区并批量调用。它在发现任务自带 `tests/verifier.py` 时设置 `ONECODE_HOST_VERIFIER`。
- `_with_sandbox_tests` 在 `ONECODE_HOST_VERIFIER` 非空时直接调用 `run_host_verifier` 并返回。`--docker python:3.12-slim-amd64` 因此到不了容器分支。第 48 轮目录名是 `runs-r48-docker`，产物里没有镜像名，也没有 `SandboxConfig`。`harbor` 四条都是 `false`。
- 扩展四题的主机分：
  - `api_contract-hard-openapi_params`：1.0（12/12）。第 48 轮记录耗时 93.88 秒，修复次数 0。
  - `security_hardening-hard-archive_path_traversal`：1.0（12/12）。第 49 轮单独记录，修复次数 2，耗时 757.82 秒。账本是 8/12，然后 11/12，然后 12/12。
  - `feature_pipeline-hard-cross_categorical`：1.0（12/12）。第 48 轮记录耗时 102.74 秒，修复次数 0。
  - `refactor-hard-sync_async_bridge`：1.0（11/11）。第 48 轮记录耗时 155.16 秒，修复次数 0。
- 四题奖励算术平均是 1.0。断言合计 47/47。第 49 轮模型字段是 `kimi-k2.7-code`。
- 卦象码：63 乾为天，39 山天大畜，40 火地晋，17 水雷屯，21 水火既济，20 水山蹇，10 雷水解。

## 2. Phase V 要做的四件事

### 2.1 验真进容器

外置验真和写盘都要能在容器里发生，而不是只在命令行留下 `--docker`。

- 设置了镜像时，`_with_sandbox_tests` 不得在进入容器前返回。
- 工作区挂进容器。验真进程用容器里的 Python。`LOG_DIR` 单独挂载，奖励文件从那里读回。
- 只有容器真的跑起来，账本才写 `container_id`、镜像名和架构。没跑起来就不写这些字段。
- 镜像使用 `python:3.12-slim-amd64`。
- 这一步的结果仍然记 `harbor: false`。它证明的是容器里的同一份 `verifier.py`，不是 Harbor 平台。

### 2.2 受控并行

`bench_workbuddy.py` 可以按任务并行，每个任务使用自己的工作区目录和自己的 `LOG_DIR`。

- 并发数有上限，默认不超过机器的可用核数，也要受网关并发限制。
- 一个任务的 502 或超时不取消其他任务已经写下的奖励。
- 紫微吞吐数字只在当次 `scripts/benchmark_ziwei.py` 的输出里引用，不沿用以前的 4,000 ops/s。

### 2.3 扩大题集

下一批从 80 题里另选 Hard 题，覆盖还没测过的目录前缀。先不要把这些题的字段名、列顺序或解码规则写进 `data_contract_guidance`。

`cross_categorical` 的契约段落已经在提示词里。用它的 1.0 不能代表未写契约的题目。

### 2.4 Harbor 接入准备

`harbor: true` 只在跑 Harbor 那套评测时写入。接入前先写成一份环境变量和目录契约：题目包、工作区、隐藏测试、奖励文件各放哪里。详见规范契约文件 [`docs/closure/ONECODE_HARBOR_INTEGRATION_CONTRACT_2026-11-02.md`](ONECODE_HARBOR_INTEGRATION_CONTRACT_2026-11-02.md)。在那份契约落地并实际跑通之前，主机分和容器分都保持 `harbor: false`。

## 3. 不在本阶段改动的部分

- 不修改 `IchingKernel.classify_outcome`。
- 不把备用通道写成新的卦象码。
- 不把局域网地址写进默认配置。备用通道只来自环境变量。
- 不把单题答案补进修复提示词来换 1.0。

## 4. Phase V 步骤 2.1 容器验真实测落地事实

### 4.1 代码与调度改造（提交 `d02f493` 与后续加固）
- `VerifierResult` 扩展 `container_id`、`container_image`、`container_arch` 字段；`to_dict()` 在 `container_id is None` 时自动剔除。
- `run_host_verifier` 增加 `sandbox_config` 分发逻辑：当 `sandbox_config` 存在时转入 `_run_container_verifier`，挂载 `/workspace`（rw）、`/log_dir`（rw）和 `/verifier/verifier.py`（ro），并注入资源约束与安全选项（`--security-opt no-new-privileges`、`--network none` 等）。
- 通过 `--cidfile` 抓取真实 Docker 容器 64 位十六进制 ID（严格校验 `len == 64` 且为纯十六进制字符），若容器未真正启动则不写入容器字段。
- `_with_sandbox_tests` 将 `sandbox_config` 透传至 `run_host_verifier`，并在完成态和未完成态中准确回传容器指纹字段。
- `scripts/bench_workbuddy.py` 在 fallback 校验中透传 `sandbox_config`，并在终局 record 中记录容器信息；`harbor: false` 保持不变。
- 质量门禁全通：单函数 $\le 200$ 行，单类 $\le 500$ 行，无外部依赖（`dependencies = []`），53 项单元测试通过。

### 4.2 历史四题工作区临时容器复验（命令行交互输出，未写入 jsonl）
在 `n100` 节点上，对历史已解题工作区通过 Python 单行命令调用带 `SandboxConfig` 的 `run_host_verifier` 进行隔离复核（仅作为交互核验，未记入任何 `~/workbuddy-exam/*.jsonl` 评测结果）：
- `api_contract-hard-openapi_params`（`runs-r48-docker` 工作区）：`passed`，`reward: 1.0`（12/12），容器 ID `b3d3fec0228c...`
- `security_hardening-hard-archive_path_traversal`（`runs-r49-traversal` 工作区）：`passed`，`reward: 1.0`（12/12），容器 ID `8c2b9e50a727...`
- `feature_pipeline-hard-cross_categorical`（`runs-r48-docker` 工作区）：`passed`，`reward: 1.0`（12/12），容器 ID `a065785d5bc5...`
- `refactor-hard-sync_async_bridge`（`runs-r48-docker` 工作区）：`passed`，`reward: 1.0`（11/11），容器 ID `688ba9ee8582...`

### 4.3 第 50 轮全流程端到端实测事实（`results-r50-container.jsonl`）
- **评测文件**：`results-r50-container.jsonl`，当前仅包含 `openapi_params` 一题记录。
- **任务**：`api_contract-hard-openapi_params`
- **模型**：`kimi-k2.7-code`
- **终态**：`status: completed`，`reason: null`
- **奖励**：`host_reward: 1.0`
- **卦象码**：`outcome_status_code: 63`（乾为天），`iching_status_code: 39`（山天大畜）
- **修复次数与耗时**：`repair_attempt_count: 2`，`duration_s: 610.92`，水二局预算 3。
- **终局容器指纹（写入 jsonl）**：
  - `container_id`: `ecfc44b8fcd4530d91013f92dea52231fa01d313048965cb74bf965514d65269`
  - `container_image`: `python:3.12-slim-amd64`
  - `container_arch`: `amd64`
- **评测标记**：`harbor: false`
- **工作区账本演进（`ledger.jsonl` 三次真容器生命周期）**：
  1. 初验（Turn 0）：5/12 通过，退出码 0，容器 ID `cfd1f0c6cda1...`，断言失败进入修复；
  2. 修复第 1 轮（丑，Turn 1）：9/12 通过，退出码 0，容器 ID `665550fa50f8...`，模型修改完成但断言未全过；
  3. 修复第 2 轮（寅，Turn 2）：12/12 通过，退出码 0，容器 ID `ecfc44b8fcd4...`（单次容器内耗时 941ms，成为终局记录）。
  `turn_history` 记录 `子`（`verifier_failed`）$\to$ `丑`（`completed`）$\to$ `寅`（`completed`）。941ms 与外部 API 余额查询仅属中间调试证据，不属于 `results-r50-container.jsonl` 数据字段。

### 4.4 步骤 2.2 受控并行与紫微实测吞吐数据（提交 `a00fd0e`）
- **并发调度与线程隔离**：
  - `bench_workbuddy.py` 引入 `--concurrency / -j` 参数，并发上限受限于机器可用 CPU 核数（`os.cpu_count() or 1`）与安全阈值（8）；
  - 每个任务独占其工作区目录（`runs_dir/<task_id>`）；
  - 工作区级验真指针：`bench_workbuddy.py` 将任务对应的验真脚本路径写入工作区根目录的 `.onecode_host_verifier` 标记文件；`model_loop.py` 优先解析工作区标记，彻底消除多线程并发时改写全局 `ONECODE_HOST_VERIFIER` 环境变量引发的竞争风险；
  - 每次容器验真独立生成临时目录 `oc-container-grade-*` 作为隔离的 `LOG_DIR` 与 `--cidfile` 容器 ID 捕捉路径；
  - `output_lock` 保证多任务终局结果线程安全地追加写入结果文件；单个任务异常（502、超时或异常）仅记录报错，不中断其他任务执行。
- **当次紫微全状态吞吐实测数据（`n100` 实测）**：
  在 `n100` 主机（Ubuntu 24.04 x86_64，Intel N100，Python 3.12.3）上执行 `scripts/benchmark_ziwei.py --iterations 10000`：
  - 迭代轮次：10,000
  - 执行总耗时：20.5697 秒
  - **实测吞吐**：**486.15 ops/sec**
  - 平均延迟：2,053.56 µs
  - 中位数（p50）：2,036.62 µs
  - 95 分位数（p95）：2,153.20 µs
  - 99 分位数（p99）：2,338.30 µs
  - 数学证书：26 项跨验数学证书全部 `[PASS]`（`true`）
  - 严格以本次实测的 486.15 ops/sec 为基准，不套用既往 4,000 ops/s 估值。

### 4.5 步骤 2.3 扩大题集：首个未测目录前缀 Hard 题实测（`results-r51-expand.jsonl`）
- **评测文件**：`results-r51-expand.jsonl`
- **任务**：`performance-hard-template_cache`（所属目录前缀 `performance`，此前从未测试）
- **契约提示纯净度**：`data_contract_guidance` 中**没有任何**该题字段名、配置项或缓存键规则的注入，严格基于通用系统提示词与修复引导。
- **模型**：`kimi-k2.7-code`
- **终态**：`status: completed`，`reason: null`
- **奖励**：`host_reward: 1.0`（12/12 全部通过）
- **卦象码**：`outcome_status_code: 63`（乾为天），`iching_status_code: 39`（山天大畜）
- **轮次与耗时**：`repair_attempt_count: 0`（第 0 轮一次性通过），耗时 23.39 秒。
- **紫微星局**：金四局，轮次预算 5。
- **容器指纹（写入 jsonl）**：
  - `container_id`: `9df9b97bf0efb31a661bc2bf05a5a36dddf2a418b1d83598ebe02e35cdb9a2f6`
  - `container_image`: `python:3.12-slim-amd64`
  - `container_arch`: `amd64`
- **评测标记**：`harbor: false`
- **工作区账本（`ledger.jsonl`）**：
  - 资产：`jinja_like/environment.py`（实现 `OrderedDict` LRU 缓存、`(source, autoescape)` 缓存键与动态过滤器解耦）；
  - 单次隔离容器内执行耗时：958 毫秒，退出码 0，12/12 断言全部通过。
- **五题跨轮次累计基线（非同一次评测的同一结果文件）**：
  59/59 是把分属不同独立结果文件与历史轮次（第 48 轮三题、第 49 轮路径穿越单独文件、第 51 轮模板缓存单独文件）的各题终分相加得到（12 + 12 + 12 + 11 + 12 = 59/59），覆盖了 5 个不同目录前缀（`api_contract`、`security_hardening`、`feature_pipeline`、`refactor`、`performance`），并非同一次连续评测写进同一个 jsonl 文件。四题前缀 `b3d3fec0228c`、`8c2b9e50a727`、`a065785d5bc5`、`688ba9ee8582` 仅为命令行交互输出，严格不在任何 jsonl 文件中。

### 4.6 步骤 2.4 Harbor 接入契约制定
- 正式制定独立契约规范：[`docs/closure/ONECODE_HARBOR_INTEGRATION_CONTRACT_2026-11-02.md`](ONECODE_HARBOR_INTEGRATION_CONTRACT_2026-11-02.md)；
- 明确 7 项标准环境变量：`HARBOR_TASK_ID`、`HARBOR_TASK_PACKAGE`、`HARBOR_WORKSPACE`、`HARBOR_HIDDEN_TESTS`、`HARBOR_LOG_DIR`、`HARBOR_IMAGE`、`HARBOR_EVAL_MODE`；
- 规定题目包（RO）、运行工作区（RW）、隐藏断言脚本（评分阶段只读挂载）、日志输出目录（RW）的标准拓扑；
- 容器执行协议：强制通过 `--cidfile` 抓取 64 位十六进制容器 ID，严格约束 `--network none`、`--security-opt no-new-privileges` 与内存 CPU 配额；
- 真实性准入：在 Harbor 评测流水线上实际调用并跑通之前，所有单机与远端执行一律保持 `harbor: false`。



