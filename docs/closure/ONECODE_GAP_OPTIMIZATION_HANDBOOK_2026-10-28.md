# OneCode 不足优化手册，2026-10-28

> 这一阶段已经收口，记录在 [`ONECODE_GAP_OPTIMIZATION_CLOSEOUT_2026-10-28.md`](ONECODE_GAP_OPTIMIZATION_CLOSEOUT_2026-10-28.md)。不要把已经勾完的 Task 再实现一遍。
>
> `claims_mainstream_parity` 保持 `false`。不新增卦象，不修改 `IchingKernel.classify_outcome`。已经存在的预置测试不可改。沙盒保持 `--network none`。不把硬防护改成 Markdown。不实现 Harness² 自修改，也不加 `--substrate`。

**日期：** 2026-10-28  
**版本：** v1.0.0（`v1.0.0` 在 `dd51424`，`v0.8.0` 在 `e1adb3c`）  
**依据：** [`ONECODE_WORKBUDDY_EXAM_CLOSEOUT_2026-10-28.md`](ONECODE_WORKBUDDY_EXAM_CLOSEOUT_2026-10-28.md)

n100 上 80 道 code 题：12 道完成且卦象 39，31 道 `no_actionable_plan`，36 道网关 HTTP 520，1 道空补丁在执行时抛错。没有 Harbor 正式分，没有满分。`f9c74f8` 已让任务里点名的已有 Python 文件进入前言，并拒绝空的 `replace_block`。这 31 道还没有用那次提交重跑。

## 不在本手册里改的事

- 不把已有预置测试改成可写。任务写明只补测试时，可以新增一个 `tests/*.py`，已有文件的哈希变了仍然阻断。
- 不把 HTTP 520 记成通过。最多再请求两次，第三次失败仍是通道错误。
- 不用宿主机 `python verifier.py` 代替任务镜像里的 Harbor 评分。
- 不把 80 道题再自动跑一遍。操作者点名之后，才抽查已经改过的那几类。
- 已有预置测试的内容仍然不可改。只允许任务明确要求时新增一个测试文件。

## Task 1：调查读到的文件优先于字母表前 8 个

**Files:**
- Modify: `src/onecode/web/api.py`
- Test: `tests/test_web_api.py`

前言标题里的已有 Python 文件成为写入目标。标题形如 `## pkg / real.py` 或 `## pkg/real.py`。只有一个时，用这一份的整文件提示。有多个时，名单只用这几个，不用按文件名排序截出的前 8 个。`tests/` 和根目录影子文件不进入名单。

- [x] 失败测试：仓库里有 `a.py` 到 `h.py`，前言里是 `pkg/real.py`，提示的目标是 `pkg/real.py`。
- [x] 实现 `_shell_write_prompt(..., preface="")`，`prepare_shell_model_call` 把已经拼好的前言传进去。
- [x] 聚焦测试通过。

## Task 2：只写一个被点名的 JSON 文件

**Files:**
- Modify: `src/onecode/web/api.py`
- Test: `tests/test_web_api.py`

任务写明不要改业务代码，并且只点了一个 `.json` 路径时，写入目标是这个 JSON，不是仓库里的 Python 文件。路径不得包含 `..`，不得落在 `tests/`、`.git`、`.github`、`.onecode`。仍然是一次一个完整文件，仍然要批准。

- [x] 失败测试：任务要求生成根目录 `analysis.json` 且不要改业务代码，仓库里另有 `app.py`，提示目标是 `analysis.json`。
- [x] 实现这条分支。
- [x] 聚焦测试通过。

## Task 4：按任务里的标识符找实现文件

任务没有点名路径、调查也没读到文件时，不再只用按文件名排序的前 8 个。在最多 400 个 Python 文件里按标识符打分，取得分最高的最多 4 个，并把它们的正文放进前言。`tests/` 和根目录影子文件不参与。

- [x] `FilteredRelation` 只出现在 `pkg/query_utils.py` 时，写入目标是这个文件，不是 `a.py`。
- [x] 聚焦测试通过。

## Task 5：只补测试时允许新增一个测试文件

已经存在的 `tests/**/*.py` 哈希变了仍然阻断交付。补丁仍不能改 `tests/`。新的 `tests/*.py` 可以成为一次完整资产，并且可以 `import unittest`。`conftest.py`、`unittest.py`、`pytest.py` 不能新增。提示在任务写明「只补测试」时要求只新增一个测试文件，不改实现文件。

- [x] 基线里没有的 `tests/test_router.py` 可以通过计划校验；基线里已有的 `tests/test_fee.py` 仍然拒绝。
- [x] 只新增测试文件不算改写预置测试。
- [x] 「只补测试，先别改 formatting.py」的提示要求新增 unittest 文件。

## Task 6：网关 HTTP 520 再试两次

`_post_model_json` 对 HTTP 520 最多再请求两次。第三次仍失败才是 `model_provider_error`。这不把通道失败记成通过。

- [x] 连续两次 520 后第三次成功，返回 JSON。

## Task 8：审批基线、MCP 名称、影子模块、调查队列

- [x] 预置测试哈希在宿主机暂存之前记下。已经存在的 `tests/` 文件不能通过 `stage` 被盖掉。
- [x] 前言里的 MCP 名称只来自 `ONECODE_HOME/mcp_servers.json`。工作区里同名文件不再出现。
- [x] `src/unittest.py` 这类影子模块不能写入。
- [x] 默认调查先读标识符对上的实现文件，并仍会带上对应的 `tests/test_*.py`。
- [x] `bash scripts/verify.sh`：`Ran 1327 tests`，`OK (skipped=1)`，覆盖率 86%（14355 条语句，1964 条未覆盖），`doctor` 状态 `ok`。

## 还没有消掉的限制

三次 HTTP 520 仍失败时，通道错误仍然停题。宿主机评分仍然不是 Harbor 正式分。`claims_mainstream_parity` 仍是 false。持有 `approval-plan.key` 的人仍能重写本地账本。这 31 道拒绝题还没有用新代码重考。
