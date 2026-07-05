# YiZiJue-LM Release Closure Handoff

Date: 2026-07-05

## Status

YiZiJue-LM is ready for source handoff as a local OneCode Agent proposal-model
workspace and public release package.

This closure covers the source workspace under:

```text
/Users/aidi/大字典/小模型
```

The release copy is:

```text
release/yizijue-lm-public
```

## Scope Closed

- Evaluation gate hardening for missing, unexpected, duplicate, malformed, and
  non-string IDs or predictions.
- Prediction-generation input validation before MLX runtime import.
- Hardened dataset-builder validation for split configuration, source IDs,
  source rows, gold actions, hard-negative replay IDs, and recovery actions.
- Local service request-boundary validation for body size, `Content-Length`,
  JSON object bodies, `max_tokens`, port range, and generic generation errors.
- Release checksum validation with Python SHA-256 checks covering every release
  file except the checksum manifest itself.
- Release-local self verification through `scripts/verify_release.sh`.
- Changelog and release checksum records synchronized with the current source
  and release tree.

## Verification Evidence

Latest full workspace verification:

```bash
bash scripts/verify.sh
```

Observed result:

```text
Main workspace tests: 116 tests OK
Release package tests: 86 tests OK
missing_prediction_count: 0
unexpected_prediction_count: 0
json_valid_rate: 0.9858490566037735
action_match_rate: 0.8254716981132075
unknown_action_count: 0
unsafe_allow_count: 0
all release checksum entries: OK
```

Python cache check after verification:

```bash
find scripts tests release/yizijue-lm-public/scripts release/yizijue-lm-public/tests \( -name __pycache__ -o -name '*.pyc' \)
```

Expected result: no output.

## Source And Artifact Boundary

Included in the GitHub source update:

- Python scripts and tests;
- public release source copy;
- release docs and checksums;
- training/evaluation JSONL assets used by this workspace;
- project documentation, changelog, requirements, and verification metadata.

Excluded from the source update:

- virtual environments;
- Python caches;
- local logs;
- `models/` adapter checkpoints and safetensors artifacts;
- Qwen base weights;
- private credentials or API keys.

The final LoRA adapter remains a separate runtime artifact. The service must be
started with `--adapter-path` or `YIZIJUE_ADAPTER_PATH`.

## Publication Target

Current configured Git remote from the parent repository:

```text
origin  https://github.com/aidi1723/onecode.git
```

This handoff stages only files under `小模型/` and intentionally avoids unrelated
modified or untracked files in the parent repository.

## Remaining Risks

- The parent Git workspace contains unrelated modified and untracked files
  outside `小模型/`; they are out of scope for this closure.
- Runtime MLX inference still depends on local model artifacts and the external
  `mlx_lm` runtime environment.
- OneCode remains responsible for final authorization, execution, evidence
  recording, and audit. YiZiJue-LM only proposes action JSON.

## Next Owner Action

After GitHub push, the next owner should review the pushed branch or commit and
decide whether to split `小模型/` into a dedicated public repository or keep it as
a source workspace under the current OneCode repository.
