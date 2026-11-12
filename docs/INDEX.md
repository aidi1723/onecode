# OneCode Documentation Index

> **Archive Branch Notice**: Full historical milestone closeouts (`docs/closure/`, 79 files) and chronological specs/plans (`docs/superpowers/`, 89 files) have been archived to git branch [`archive/dev-logs-v1.1`](https://github.com/aidi1723/onecode/tree/archive/dev-logs-v1.1) so `main` stays concise and focused on active engineering contracts. Legacy commit hashes referenced inside historical logs belong to an earlier repository prior to the `2026-09-01` re-initialization described in [GIT_HISTORY_NOTE.md](GIT_HISTORY_NOTE.md).

## Quick Start & Active Documentation

- **[README](../README.md)** - Project overview, `onecode-kernel` installation, quick start, and verified benchmark scope
- **[SECURITY.md](../SECURITY.md)** - Vulnerability reporting policy & runtime trust boundary overview
- **[SECURITY_ARCHITECTURE.md](SECURITY_ARCHITECTURE.md)** - Six-layer defense-in-depth architecture & reproducible 18-vector adversarial suite (`18/18` verified)
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture diagrams, runtime flow, and optional companion decoupling
- **[CLI_REFERENCE.md](CLI_REFERENCE.md)** - Complete CLI reference (`run`, `run-plan`, `run-model`, `inspect`, `list-runs`, `doctor`, `math-audit`, `serve`, `tui`)
- **[DESIGN.md](../DESIGN.md)** - Interactive TUI and local HTTP gateway design contracts
- **[ICHING_QUICKREF.md](ICHING_QUICKREF.md)** - Deterministic 64-state Q6 transition model & state inspection guide
- **[ICHING_OBSERVABILITY_MAPPING.md](ICHING_OBSERVABILITY_MAPPING.md)** - State telemetry & observability fields
- **[ONECODE_MATH_AUDIT_REPORT_OCT.md](ONECODE_MATH_AUDIT_REPORT_OCT.md)** - Deterministic transition & Lyapunov monotonicity audit report
- **[packages/onecode-symbolic-audit/README.md](../packages/onecode-symbolic-audit/README.md)** - Physically decoupled optional companion package (`ONECODE_SYMBOLIC_TELEMETRY=1`)

## Retained Core Rule & Hygiene Contracts (on `main`)

The following core design contracts remain on `main` because runtime audit tests (`tests/meta/`) and kernel module headers link directly to them:

- **[Rule Closure Contract Report](closure/V0_6_MATH_CLOSURE_REPORT.md)** - Deterministic 64-state transition table closure contract verified by `tests/meta/test_rule_closure.py`
- **[v0.1 Alpha Kernel & Source Hygiene](superpowers/specs/2026-05-27-onecode-v0.1-alpha-kernel-design.md)** - Source hygiene & isolation boundaries verified by `tests/meta/test_source_hygiene.py`
- **[v0.5 Complete Rule Kernel Spec](superpowers/specs/2026-05-28-onecode-v0.5-iching-complete-rule-kernel-design.md)** - Q6 6-bit state space, trigram phases, and transition authority chain
- **[Yin-Yang Five-Element Runtime Mapping](superpowers/specs/2026-06-01-onecode-yinyang-wuxing-runtime-rule-mapping-design.md)** - Execution feedback mapping and cooldown rules
- **[Cybernetic Source Alignment](superpowers/specs/2026-05-28-onecode-iching-source-alignment.md)** - Mapping finite discrete rules to control theory & Lyapunov monotonicity

## Architecture Summary: 64-State Cybernetic Automaton

Every run transitions through a bounded 6-bit state space ($0 \le s \le 63$) on the hypercube $Q_6 = \{0, 1\}^6$, partitioned into outer context bits $\phi_{\text{out}} \in \{0, 1\}^3$ and inner execution bits $\phi_{\text{in}} \in \{0, 1\}^3$:

```text
Example: Status Code 40 = 0b101000
- Outer phase: 101 -> thermal boundary condition
- Inner phase: 000 -> ground state
- Action: deterministic halt with reason "sovereignty_fire_boundary_halt"
```

Static automaton scope (`onecode math-audit`):
- **64-state Q6 graph**: **56 self-loop fixed points** (terminal or idempotent checkpoint states on repeated fault inputs) and **8 strictly energy-decreasing edges** ($\Delta V < 0$ for reversible recovery/cooldown paths).
- **Runtime termination**: Multi-turn bounded execution is enforced mechanically by `--max-turns`, bureau `turn_budget`, stagnation/repeat guards, and resource budgets.

## Testing, Verification & Benchmarks

Verification is separated into three clean layers plus the full CI gate:

- **Core functional gate**: `bash scripts/verify-core.sh` (~336 engineering core tests; requires zero optional symbolic modules)
- **Meta/contract gate**: `bash scripts/verify-meta.sh` (`tests/meta/`: README links, GPL-3.0-only consistency, DESIGN/hygiene/closure contracts)
- **Optional symbolic companion gate**: `bash scripts/verify-symbolic.sh` (`packages/onecode-symbolic-audit/tests/` — 102 cross-validation & integration tests + 26 certificates micro-benchmark)
- **Full CI gate**: `bash scripts/verify.sh` (all unit tests, `ruff`, `mypy`, AST line-count limits, `coverage >= 75%`, `onecode doctor`)
- **Adversarial security benchmark**: `PYTHONPATH=src python3 scripts/security_benchmark.py` (`18/18` vectors enforced via `tests/test_security_suite.py`)
- **Token projection benchmark**: **[scripts/token_projection_benchmark.py](../scripts/token_projection_benchmark.py)** (reproducible zero-API benchmark verifying `shell_projection` compression and checkpoint telemetry decoupling in `tests/test_token_benchmark.py`)
- **Smoke diagnostics**: `onecode doctor` & `onecode math-audit`

## Governance, Release & Historical Archives

- **[CONTRIBUTING.md](../CONTRIBUTING.md)** - Developer onboarding, kernel change rules, and testing tiers
- **[CHANGELOG.md](../CHANGELOG.md)** - Chronological release & hardening notes
- **[RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)** - Pre-release verification checklist
- **[TRAINING_DATA_REFACTORING_STATUS.md](TRAINING_DATA_REFACTORING_STATUS.md)** & **[YIZIJUE_CONTROLLED_DECODING_PROBABILITY_RULES.md](YIZIJUE_CONTROLLED_DECODING_PROBABILITY_RULES.md)** - Decoupled training/evaluation documentation
- **[Historical Closure Logs Notice](closure/README.md)** - Index pointer for the 79 historical closeout documents on branch `archive/dev-logs-v1.1`
- **[Historical Specs & Plans Notice](superpowers/README.md)** - Index pointer for the 89+ archived design specs & implementation plans on branch `archive/dev-logs-v1.1`
