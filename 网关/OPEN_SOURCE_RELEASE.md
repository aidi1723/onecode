# Open Source Release Checklist

Target license: Apache License 2.0

This project should be published as a new standalone repository rooted at this gateway project directory.

Do not publish the parent monorepo as-is. It contains unrelated product lines, research files, reports, images, and local workspace artifacts.

## Recommended Repository Name

`oneword-agent-gateway`

## Include In The Public Repository

Core runtime:

- `agent_skill_dictionary/`
- `tests/`
- `scripts/cluster_state_sync_ab.py`
- `scripts/cyber_dice_ab_report.py`
- `scripts/golden_matrix.py`
- `scripts/http_gateway_smoke.py`
- `scripts/live_agent_benchmark.py`
- `scripts/live_gateway_smoke.py`
- `scripts/mock_tool_call_upstream.py`
- `scripts/real_model_ab_benchmark.py`
- `scripts/smoke_test.py`
- `deploy/`

Project metadata:

- `README.md`
- `HANDBOOK.md`
- `PRIVATE_BETA_QUICKSTART.md`
- `Dockerfile.gateway`
- `Makefile`
- `pytest.ini`
- `requirements-gateway.txt`
- `.env.example`
- `.gitignore`
- `LICENSE`
- `NOTICE`

Documentation suitable for first public release:

- `docs/architecture.md`
- `docs/build-mode-control-network.md`
- `docs/build-mode-equilibrium-engine.md`
- `docs/build-mode-kernel-rules.md`
- `docs/build-mode-sovereignty-engine.md`
- `docs/build-mode-v2-3d-dynamics.md`
- `docs/community-skill-inspirations.md`
- `docs/community-skill-research-2026.md`
- `docs/delivery-test-plan.md`
- `docs/development.md`
- `docs/dictionary-contract.md`
- `docs/eight-opcode-primitives.md`
- `docs/existing-agent-gateway-integration.md`
- `docs/gateway-onecode-rule-sync-design.md`
- `docs/gateway-rule-sync-closeout-2026-05-29.md`
- `docs/gateway-security-audit-closeout-2026-05-29.md`
- `docs/hexagram-rules.md`
- `docs/one-character-agent-workflow-whitepaper.md`
- `docs/oneword-agent-framework.md`
- `docs/oneword-agentos-v1-kernel-manual.md`
- `docs/private-beta-distribution.md`
- `docs/project-status.md`
- `docs/root-skill-mount-registry.md`
- `docs/v0.3-action-framework.md`
- `docs/yin-yang-binary-kernel.md`
- `docs/yizijue-gateway-quickstart.md`

## Exclude From First Public Release

Local or private operational materials:

- `scripts/setup_domestic_agent_clients.sh`
- `scripts/codex_domestic_smoke.sh`
- `scripts/supervise_codex_dazidian_eval.sh`
- `docs/update-diary.md`
- `docs/agentos-test-summary-20260525.md`
- `docs/build-mode-local-closeout-20260526.md`
- `docs/n100-aider-integration-test.md`
- `docs/phase3-temporary-closeout-20260525.md`
- `docs/superpowers/`

Runtime artifacts:

- `.env`
- `.oneword/`
- `.venv/`
- `.venv-gateway/`
- `__pycache__/`
- `*.pyc`
- logs and pid files

Parent repository materials:

- `../data/`
- `../schemas/`
- `../reports/`
- images
- docx files
- other non-gateway product lines

## Required Verification Before Publishing

Run inside the standalone release repository:

```bash
python3 -m unittest discover -v
python3 -m agent_skill_dictionary.validator agent_skill_dictionary/programming-agent-skill-dictionary.json
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import py_compile
from pathlib import Path
for path in Path('.').rglob('*.py'):
    if any(part in {'.git', '.venv', '.venv-gateway', '__pycache__'} for part in path.parts):
        continue
    py_compile.compile(str(path), doraise=True)
print('py_compile OK')
PY
git diff --check
```

Run a secret scan before the first push:

```bash
rg -n 'sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{20,}|10\.0\.0\.184|/Users/|/home/[A-Za-z0-9_-]+' .
```

The only acceptable hits should be deliberate placeholders or already-redacted examples.
