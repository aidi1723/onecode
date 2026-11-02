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

`harbor: true` 只在跑 Harbor 那套评测时写入。接入前先写成一份环境变量和目录契约：题目包、工作区、隐藏测试、奖励文件各放哪里。在那份契约落地并实际跑通之前，主机分和容器分都保持 `harbor: false`。

## 3. 不在本阶段改动的部分

- 不修改 `IchingKernel.classify_outcome`。
- 不把备用通道写成新的卦象码。
- 不把局域网地址写进默认配置。备用通道只来自环境变量。
- 不把单题答案补进修复提示词来换 1.0。

## 4. Phase V 步骤 2.1 容器验真实测落地事实

### 4.1 代码与调度改造（提交 `d02f493`）
- `VerifierResult` 扩展 `container_id`、`container_image`、`container_arch` 字段；`to_dict()` 在 `container_id is None` 时自动剔除。
- `run_host_verifier` 增加 `sandbox_config` 分发逻辑：当 `sandbox_config` 存在时转入 `_run_container_verifier`，挂载 `/workspace`（rw）、`/log_dir`（rw）和 `/verifier/verifier.py`（ro），并注入资源约束与安全选项（`--security-opt no-new-privileges`、`--network none` 等）。
- 通过 `--cidfile` 抓取真实 Docker 容器 64 位 ID，严格杜绝「仅传参数未起容器」的伪隔离记录。
- `_with_sandbox_tests` 将 `sandbox_config` 透传至 `run_host_verifier`，并在完成态和未完成态中准确回传容器指纹字段。
- `scripts/bench_workbuddy.py` 在 fallback 校验中透传 `sandbox_config`，并在终局 record 中记录容器信息；`harbor: false` 保持不变。
- 质量门禁全通：单函数 $\le 200$ 行，单类 $\le 500$ 行，无外部依赖（`dependencies = []`），52 项单元测试通过。

### 4.2 历史四题容器内复验事实（`n100` 实测）
在 `n100` 环境基于镜像 `python:3.12-slim-amd64` 分别加载四题工作区执行容器隔离验真：
- `api_contract-hard-openapi_params`（R48 工作区）：`passed`，`reward: 1.0`（12/12），容器 ID `b3d3fec0228c...`
- `security_hardening-hard-archive_path_traversal`（R49 工作区）：`passed`，`reward: 1.0`（12/12），容器 ID `8c2b9e50a727...`
- `feature_pipeline-hard-cross_categorical`（R48 工作区）：`passed`，`reward: 1.0`（12/12），容器 ID `a065785d5bc5...`
- `refactor-hard-sync_async_bridge`（R48 工作区）：`passed`，`reward: 1.0`（11/11），容器 ID `688ba9ee8582...`
合计 47/47 断言在真 Docker 容器中全部通过。

### 4.3 第 50 轮全流程端到端实测事实（`results-r50-container.jsonl`）
- **任务**：`api_contract-hard-openapi_params`
- **模型**：`kimi-k2.7-code`
- **终态**：`status: completed`，`reason: null`
- **奖励**：`host_reward: 1.0`（12/12 全部通过）
- **卦象码**：`outcome_status_code: 63`（乾为天），`iching_status_code: 39`（山天大畜）
- **轮次与耗时**：修复次数 2，耗时 610.92 秒，水二局预算 3。
- **容器指纹证据**：
  - `container_id`: `ecfc44b8fcd4530d91013f92dea52231fa01d313048965cb74bf965514d65269`
  - `container_image`: `python:3.12-slim-amd64`
  - `container_arch`: `amd64`
- **评测标记**：`harbor: false`
- **账本记录**：`turn_history` 记录 `子`（`verifier_failed`）$\to$ `丑`（`completed`）$\to$ `寅`（`completed`），隔离容器内执行耗时 941ms。

