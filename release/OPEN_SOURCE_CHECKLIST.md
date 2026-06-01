# OneCode Open Source Readiness Checklist / OneCode 开源准备检查清单

This checklist records the current public-release readiness state.

本清单记录当前公开发布准备状态。

## Completed / 已完成

- [x] Apache License 2.0 license file.
  Apache License 2.0 协议文件。
- [x] Public release pack isolated under `release/`.
  公开发布包独立放在 `release/`。
- [x] Bilingual public release documents.
  中英文双语公开发布文档。
- [x] Engineering-neutral public terminology.
  工程中性的公开术语。
- [x] Public positioning: trusted industrial AI kernel for enterprise-grade local agent workflows.
  公开定位：面向企业级本地 Agent 工作流的可信任工业级 AI 内核。
- [x] Core verification gate.
  核心验证门禁。
- [x] Web API focused test gate.
  Web API 聚焦测试门禁。
- [x] Release audit script.
  发布审计脚本。
- [x] Local deterministic A/B benchmark result.
  本地确定性 A/B 基准测试结果。
- [x] Clear benchmark boundary: token savings not claimed without model-backed A/B data.
  明确基准边界：没有模型版 A/B 数据前不宣称 token 节省。
- [x] Local development materials remain unchanged.
  本地开发材料保持不变。

## Verified Evidence / 已验证证据

```text
bash scripts/verify-core.sh
185 tests OK
doctor status: ok
```

```text
PYTHONPATH=src python3 -m unittest tests.test_web_api -v
48 tests OK
```

```text
PYTHONPATH=src python3 -m onecode benchmark --compare-baseline
Baseline pass_at_1: 45%
OneCode pass_at_1: 100%
Baseline invalid-action propagation proxy: 50%
OneCode invalid-action propagation proxy: 0%
Baseline evidence completeness: 0%
OneCode evidence completeness: 100%
```

## Optional Before Public Announcement / 公开宣传前可选项

- [ ] Run a model-backed A/B benchmark with the same task set and fixed model.
  使用相同任务集和固定模型运行模型版 A/B。
- [ ] Fill token and live-model latency metrics after model-backed A/B.
  在模型版 A/B 后填入 token 和真实模型延迟指标。
- [ ] Create a signed release tag.
  创建签名 release tag。
- [ ] Publish release artifacts or source archive.
  发布 release 产物或源码归档。

