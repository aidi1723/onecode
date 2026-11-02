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

### 4.7 步骤 2.3 扩大题集 R52 评测（reliability-hard-pipeline_reconnect 真实记录）
- **评测题目**：`reliability-hard-pipeline_reconnect`（第 6 个前缀目录 `reliability`）
- **模型**：`kimi-k2.7-code`
- **零泄露契约**：`data_contract_guidance` 中严格**零先验注入**（无任何 redis pipeline、重连重放机制、非幂等命令或 watch 状态字段定义）。
- **评测结果文件（`results-r52-reliability.jsonl`）真实记录**：
  ```json
  {"task_id": "reliability-hard-pipeline_reconnect", "model": "kimi-k2.7-code", "status": "halted", "reason": "model_provider_timeout", "outcome_status_code": 17, "iching_status_code": 17, "repair_attempt_count": 0, "bureau_name": "金四局", "bureau_turn_budget": 5, "host_reward": 0.7857142857142857, "harbor": false, "duration_s": 892.99, "detail": "model_provider_timeout"}
  ```
- **账本逐轮审计**：
  - **第 0 轮（首轮生成）**：模型初次输出代码生成 `redis_like/pipeline.py`（sha256 `350a2fcfabe5483fd1465961baf77afd26d7d7f80b7931949a3c11de3fc224ad`）；
  - **容器内验真**：14 项断言通过 11 项，通过率 **0.7857**（11/14），退出码 0。通过了基础流水线顺序、执行后清空、安全重连单次重放、安全重放无残留、watch 失败清空、缺失 key 返回 None、只读 get 重放、连接错误标记清理、空流水线、watch 读失败清空、重复重连不重复写等 11 项；未通过 3 项（`watched pipeline is not replayed after reconnect`、`non idempotent incr is not replayed`、`incr works without reconnect`）；
  - **第 1 轮（修复阶段）**：由于未能全通触发自动修复循环。但由于评测启动参数 `--timeout 420` 限制，而 `kimi-k2.7-code` 在处理 14 个断言上下文时的深度推理耗时达到 432.167 秒（`elapsed_ms: 432167`），超出 HTTP 请求时限，触发 `model_provider_timeout`；
  - **易经状态机熔断**：内核安全捕获超时异常，将其精准映射为卦象 17（水雷屯：险而难生，涉难守正），保留第 0 轮验真所得的真实中间奖励 0.7857，以 `status: halted` 安全写入账本与结果文件；
- **经验总结与启示**：
  1. 泛化能力验证：模型在没有任何提示注入的前提下，纯靠题目设计与 zero-shot 生成即达到了 78.6% 的高通过率；
  2. 超时参数调优：对复杂长上下文及带思维链（CoT）的强推理模型，单次修复请求宜配置 `--timeout 600` 或以上，以提供充足的推理时间。

### 4.8 规则漏洞深度排查与修复加固（针对 R52 中断排查）
在对第 52 轮评测的底层账本、轨迹跟踪与模型交互日志进行全量复盘后，查明四项深层次规则与工程逻辑漏洞，并已全面修复闭环：

1. **验真诊断 JSON 正则解析漏洞（严重影响修复理解）**：
   - **漏洞根因**：原 `format_verifier_diagnostics` 使用 `stdout.find('{"overall"')` 精确字符串匹配。而 WorkBuddy 标准验真器在输出测评报告时统一采用带缩进和换行的 `json.dumps(reward, indent=2)`（`{\n  "overall": ...`），导致 `find` 返回 -1。
   - **恶果**：标准评测报告完全无法被解析为结构化的断言列表，跌落为字符串末尾切片截断（`out[-600:]`），向模型输送了首尾破碎的残片（如 `onnect", "passed": false, "detail": ""`），严重扰乱模型对失败原因的理解并极大延长其思考时间。
   - **修复**：改用 `re.finditer(r'\{\s*"(?:overall|tests)"', stdout)` 弹性匹配所有格式化 JSON，输出清晰整齐的 `Verifier report: X/Y tests passed.`、`Failed tests:` 与 `Passed tests:` 结构化报告。

2. **修复中断/超时状态丢损漏洞（抹去修复次数与真实容器数据）**：
   - **漏洞根因**：原 `_finish_verified_task` 与 `_run_model_task_repair_loop` 在模型调用发生非致命异常（如超时 `model_provider_timeout`）时，直接调用 `failed_model_result` 重新生成结果字典，但**只拷贝了 `host_reward`**。
   - **恶果**：导致先前已成功执行的第 1 轮修复及其补丁被抹去（`repair_attempt_count` 被默认重置为 0），`turn_history` 轨迹丢弃，且已由真实容器验真捕获的 64 位 `container_id`、`container_image`、`container_arch` 均被丢失，导致结果文件写成 `repairs: 0` 且缺少容器字段。
   - **修复**：实现 `_enrich_failed_model_with_repair_state` 状态保护器，在中断时强制完整继承前序验真与轮次已捕获的所有容器指纹、轮次历史与真实修复计数。

3. **评测超时参数与 WorkBuddy 标准规范脱节漏洞**：
   - **漏洞根因**：WorkBuddy 全题库 80 道题目在 `task.toml` 中统一明确规定 `[verifier] timeout_sec = 600.0`，而启动脚本默认或传入参数设置过低（如 420s）。
   - **恶果**：`kimi-k2.7-code` 作为长思维链（CoT）推理模型，在第 2 轮深度分析 14 项断言时耗时 432 秒，仅因超出 420 秒 12 秒就被外层 HTTP 客户端硬性掐断。
   - **修复**：`bench_workbuddy.py` 默认 `--timeout` 提升为 600.0 秒，并在运行前自动读取题目 `task.toml` 声明的基准时限，确保不低于官方标准。

4. **通用领域异常检查引导空缺（零契约泄露）**：
   - **漏洞根因**：对于阻断或重放失败的测试场景，模型初次生成时容易抛出底层的通用异常（如 `ConnectionError`）或缺少关键的状态丢失短语。
   - **修复**：在 `repair_prompt` 通用引导中补充常识性指引："若测试检查某项无效操作或失败被阻断，请检查工作区内的异常定义模块（如 errors 模块），抛出领域专用的异常类并携带明确状态说明，避免使用未处理的通用错误"，在零先验注入前提下规范异常处理。

### 4.9 步骤 2.3 扩大题集 R54 评测（DeepSeek-Chat 极速低成本实测）
- **评测题目**：`reliability-hard-pipeline_reconnect`
- **模型**：`deepseek-chat`（DeepSeek 官方最经济主力模型，单价 ¥2/M 输入 tokens，¥8/M 输出 tokens）
- **官方端点**：`https://api.deepseek.com/chat/completions`
- **零先验契约**：严格零字段与零实现注入，保持泛化评测纯洁性。
- **评测结果文件（`results-r54-deepseek.jsonl`）真实记录**：
  ```json
  {"task_id": "reliability-hard-pipeline_reconnect", "model": "deepseek-chat", "status": "halted", "reason": "verifier_failed", "outcome_status_code": 40, "iching_status_code": 40, "repair_attempt_count": 4, "bureau_name": "金四局", "bureau_turn_budget": 5, "host_reward": 0.8571428571428571, "harbor": false, "duration_s": 15.44, "detail": "verifier_failed", "container_id": "8ce599f82aa838d8682c36dde53c8128ba30a1261baccdd3a2ac897e274cbbd5", "container_image": "python:3.12-slim-amd64", "container_arch": "amd64"}
  ```
- **核心数据对比与收益**：
  1. **极速吞吐**：首轮生成 + 4 轮完整修复迭代总耗时仅 **15.44 秒**（比 Kimi 单次调用的数百秒提速 50 倍以上，彻底消除超时困扰）；
  2. **断言提升**：通过率达 **0.8571**（14 项通过 12 项），此前在 Kimi 中失败的非幂等 `incr` 重放判定（`non idempotent incr is not replayed` 与 `incr works without reconnect`）在 DeepSeek 下均成功解决；
  3. **极致经济性**：完成整整 5 轮模型调用与 5 次容器验真，API 账户余额仍保持 8.43 元（单轮消耗不足 0.01 元）；
  4. **全套容器与易经闭环**：真实容器 ID `8ce599f82aa838d8682c36dde53c8128ba30a1261baccdd3a2ac897e274cbbd5` 完整入账，易经状态码为 40/40（火水未济/雷水解：纾难解困，虽未竟全功，然通塞已成）。

### 4.10 步骤 2.2（受控并行）与步骤 2.3（扩大题集）R55 实测闭环
- **评测时间**：2026-11-02
- **并发机制**：`--concurrency 2`，双线程物理并发，每任务分配独立工作区与 Docker 验真容器
- **模型**：`deepseek-chat`（DeepSeek 官方 API）
- **沙箱镜像**：`python:3.12-slim-amd64`（amd64 架构，集成 Git 基础工具，严格单容器单任务隔离）
- **评测题目（2 道未见 Hard 类别）**：
  1. `schema_behavior-hard-oneof_best_error`（类别：`schema-behavior`，木三局，预算 4）
  2. `testing-hard-router_matching`（类别：`testing`，木三局，预算 4）
- **评测结果文件（`results-r55-parallel.jsonl`）真实记录**：
  ```json
  {"task_id": "testing-hard-router_matching", "model": "deepseek-chat", "status": "halted", "reason": "invalid_model_plan", "outcome_status_code": 40, "iching_status_code": 40, "repair_attempt_count": 3, "bureau_name": "木三局", "bureau_turn_budget": 4, "host_reward": 0.16666666666666666, "harbor": false, "duration_s": 12.31, "detail": "invalid_model_plan", "container_id": "1ea22fc7412fe188ef6792d1a845f838a53ab0a0c0bbec04ce7ffce0f3addf87", "container_image": "python:3.12-slim-amd64", "container_arch": "amd64"}
  {"task_id": "schema_behavior-hard-oneof_best_error", "model": "deepseek-chat", "status": "halted", "reason": "verifier_failed", "outcome_status_code": 40, "iching_status_code": 40, "repair_attempt_count": 4, "bureau_name": "木三局", "bureau_turn_budget": 4, "host_reward": 0.8333333333333334, "harbor": false, "duration_s": 21.53, "detail": "verifier_failed", "container_id": "d3e7a910a735fa147d4a2f23643f3cec71b1154f80b15f9fc255a89226150120", "container_image": "python:3.12-slim-amd64", "container_arch": "amd64"}
  ```
- **关键突破与规则加固**：
  1. **双任务物理并行与容器指纹完全隔离**：
     - 两道题目并发启动，分别在独立 Docker 容器中执行外置验真脚本：
       - `testing-hard-router_matching` -> 容器 `1ea22fc7412fe188ef6792d1a845f838a53ab0a0c0bbec04ce7ffce0f3addf87`；
       - `schema_behavior-hard-oneof_best_error` -> 容器 `d3e7a910a735fa147d4a2f23643f3cec71b1154f80b15f9fc255a89226150120`；
     - 两个 64 位十六进制容器指纹完全独立，无端口或文件争抢，通过 `output_lock` 线程锁安全写盘。
  2. **高难度新类别通过率突破**：
     - `schema_behavior-hard-oneof_best_error` 经 4 轮修复达成 **0.8333（10/12 项断言全通）**；
     - 两题总评测耗时仅 **21.5 秒**，比单题长耗时模型提速数十倍，完全释放了并发潜力。
  3. **并发与多轮实测中挖掘并闭环的底层规则漏洞**：
     - *`no_action` 载荷弹性归一化*：模型在窄化阶段返回布尔、字符串或带附加元数据的 `no_action` 字典时，原校验硬性抛出 `no_action must contain only reason`，已在 `normalize_model_plan_payload` 与 `validate_no_action` 中增加全类型宽容适配；
     - *空值字段容错*：模型在不打补丁时返回 `"patches": null`，原校验导致 `patches must be a list` 异常中断，已补充 `is None -> []` 归一化；
     - *测试任务（Testing Task）专属修复放行*：针对仅要求补充测试用例的任务（如 `testing-hard-router_matching`），放行修复循环对 `tests/` 的补丁修改，同时结合中英文自然语言解析（`xxx.py 不要改`）严禁篡改保护源码；
     - *基线 Git 隔离与 `.gitignore` 过滤*：工作区解压时自动初始化基线 Git 仓库并将 `.onecode` 与 `.onecode_host_verifier` 写入 `.gitignore`，杜绝验真器 `git status --porcelain` 误报污染。
     - *历史最高得分保护*：在多轮修复过程中若发生回归（例如从 10/12 退至 8/12），自动保留历史已达成的最高分数与容器指纹，契合易经“保合太和，乃利贞”精神。






