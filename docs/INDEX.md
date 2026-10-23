# OneCode Documentation Index

This index helps you navigate OneCode's documentation, which is organized by purpose and audience.

`docs/closure/` and `docs/superpowers/` are historical records. They keep the design trail, and many of their commit hashes belong to the previous repository. Current behavior is defined by the source tree, `SECURITY.md`, and this index.

## Quick Start

- [README.md](../README.md) - Installation, verification, and basic usage
- [2026-10-23 controlled scope and agent evolution closeout](closure/ONECODE_CONTROLLED_SCOPE_AND_AGENT_EVOLUTION_CLOSEOUT_2026-10-23.md) - Nine tasks at e61a4b6. Mac gate is 1293 tests, 1 skipped. The n100 four-test script is not in the tree.
- [2026-10-23 next development handbook](closure/ONECODE_NEXT_DEVELOPMENT_HANDBOOK_2026-10-23.md) - Three-phase handbook: controlled-scope closure, perception/patch foundations, and multi-turn agent evolution
- [2026-10-16 follow-up development handbook](superpowers/plans/2026-10-16-onecode-followup-development-handbook.md) - Closed implementation contract: gates, approval, reason codes, observability boundary
- [2026-10-22 conductor closeout](closure/ONECODE_CONDUCTOR_CLOSEOUT_2026-10-22.md) - One rewrite, confirmed memory, MCP names, n100 check at d6e00ce
- [2026-10-22 controlled-scope plan](closure/ONECODE_CONTROLLED_SCOPE_PLAN_2026-10-22.md) - Next work: preset tests stay unchanged, and the local ledger can be checked
- [2026-10-21 long-task plan](closure/ONECODE_LONG_TASK_PLAN_2026-10-21.md) - Later scheme for unattended long tasks; rule changes not approved
- [2026-10-21 asset-write closeout](closure/ONECODE_ASSET_WRITE_CLOSEOUT_2026-10-21.md) - Complete-file writes and the survey search-miss fix
- [2026-10-21 shell read closeout](closure/ONECODE_SHELL_READ_CLOSEOUT_2026-10-21.md) - Chat survey, approval diff, and the n100 live tasks at 812bab7
- [2026-10-21 shell handbook](superpowers/plans/2026-10-21-onecode-shell-v088-handbook.md) - LibreChat v0.8.8 as the chat shell, kernel rules unchanged
- [2026-09-29 audit remediation closeout](closure/ONECODE_AUDIT_REMEDIATION_CLOSURE_2026-09-29.md) - Current security boundary and verification record
- [2026-09-29 agent parity closeout](closure/ONECODE_AGENT_PARITY_CLOSURE_2026-09-29.md) - Handbook phases, workflow run, and evaluation limits
- [2026-09-29 host contract handbook](superpowers/plans/2026-09-29-host-contract-handbook.md) - Execution-gate approval, no-progress stop, transient errors, truncation
- [2026-10-07 Engineering & Observability handbook](superpowers/plans/2026-10-07-onecode-engineering-and-observability-handbook.md) - Soak tests, ARM64 sandbox, and read-only I Ching telemetry
- [2026-10-20 task rule follow-up](closure/ONECODE_TASK_RULE_FOLLOWUP_2026-10-20.md) - Current task rules after tag v1.0.0, closed on n100 2026-10-21
- [2026-10-20 v1.0.0 release](closure/ONECODE_V1_0_RELEASE_2026-10-20.md) - Formal release on the n100 acceptance, tag v1.0.0 at dd51424
- [2026-10-19 sandbox delivery](closure/ONECODE_SANDBOX_DELIVERY_2026-10-19.md) - Phase closed on n100 at v0.8.0
- [2026-10-18 phase closeout](closure/ONECODE_PHASE_CLOSEOUT_2026-10-18.md) - v0.8.0 sealed; not a 1.0 release
- [2026-10-18 hexagram runtime closeout](closure/ONECODE_HEXAGRAM_RUNTIME_CLOSEOUT_2026-10-18.md) - One reading for yin-yang, five elements, and tagged tasks
- [2026-10-18 long-task rule notes](closure/ONECODE_LONG_TASK_RULE_NOTES_2026-10-18.md) - Circulation rounds, missing Docker socket, and the named verifier hexagrams
- [2026-10-18 rule audit rounds](closure/ONECODE_RULE_AUDIT_ROUNDS_2026-10-18.md) - Three rounds on the Mac and n100 against the closeout reading
- [2026-10-07 day closeout part 2](closure/ONECODE_DAY_CLOSEOUT_2026-10-07_PART_2.md) - Memory leak mitigation and ARM64 QEMU pending validation, core audit fixes applied
- [2026-09-29 day closeout](closure/ONECODE_DAY_CLOSEOUT_2026-09-29.md) - Mac and n100 results, and what is still running
- [DESIGN.md](../DESIGN.md) - Core design principles
- [CONTRIBUTING.md](../CONTRIBUTING.md) - How to contribute (see onboarding guide below)

## Architecture & Design

OneCode uses an I Ching (易经) based state system for deterministic control flow. Start here to understand the core architecture:

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Visual diagrams and architecture overview (START HERE)
- **[ICHING_QUICKREF.md](ICHING_QUICKREF.md)** - Quick reference for debugging status codes
- **[2026-09-28 YiZiJue closeout](2026-09-28-yizijue-closeout.md)** - Local action-decision closeout, latency, and boundaries

### Core Concepts
- [I Ching Complete Rule Kernel](superpowers/specs/2026-05-28-onecode-v0.5-iching-complete-rule-kernel-design.md) - Mathematical foundation: six-line encoding, four symbols, trigrams, 64 states
- [Yin-Yang Five-Element Runtime Mapping](superpowers/specs/2026-06-01-onecode-yinyang-wuxing-runtime-rule-mapping-design.md) - How traditional correspondences map to execution behavior
- [I Ching Source Alignment](superpowers/specs/2026-05-28-onecode-iching-source-alignment.md) - Why I Ching was chosen and how it aligns with control theory

### Key Systems
- [v0.1 Alpha Kernel](superpowers/specs/2026-05-27-onecode-v0.1-alpha-kernel-design.md) - Initial kernel design
- [v0.2 LogosGate](superpowers/specs/2026-05-27-onecode-v0.2-beta-logosgate-design.md) - Safety gate and path guard
- [v0.3 Stateful Resumption](superpowers/specs/2026-05-28-onecode-v0.3-beta-stateful-resumption-design.md) - Checkpoint and resume mechanism
- [v0.4 Multi-Asset Orchestration](superpowers/specs/2026-05-28-onecode-v0.4-beta-multi-asset-orchestration-design.md) - Parallel asset execution
- [v0.7 Controlled Verifier](superpowers/specs/2026-05-29-onecode-v0.7-controlled-verifier-design.md) - Test execution and validation

### Understanding the I Ching State System

**What are the 64 states?**
- Each state is a 6-bit code (0-63) representing a hexagram
- Each hexagram has two trigrams (outer/inner, 3 bits each)
- Bits encode yin (0) or yang (1) lines from bottom to top

**How do transitions work?**
1. **Safety first**: Hard constraints (path breach, timeout) override all symbolic rules
2. **Yin-yang pressure**: Too much yang → cooldown, too much yin → activate
3. **Five-element relations**: 
   - Outer trigram → element (context/environment)
   - Inner trigram → element (task state)
   - Generation cycle: wood→fire→earth→metal→water (accelerate/continue)
   - Control cycle: wood→earth→water→fire→metal (halt/throttle/prune)

**Example**: Status code 40 = `0b101000`
- Outer trigram: `101` (Li/离) → fire element
- Inner trigram: `000` (Kun/坤) → earth element
- Fire controls earth → halt with "sovereignty_fire_boundary_halt"

**Debugging tips**:
- Use `onecode inspect --run-id <id>` to see status codes and transitions
- Check `iching_profile` in run evidence for full hexagram breakdown
- Run `onecode math-audit` to verify rule integrity

## API Reference

### CLI Commands
- [Read-Only Commands](superpowers/specs/2026-07-10-onecode-cli-read-only-command-split-design.md) - `inspect`, `list-runs`, `doctor`, `math-audit`
- [Local Interface Commands](superpowers/specs/2026-07-10-onecode-cli-local-interface-command-split-design.md) - `serve`, `shell`, `tui`
- [Configuration Commands](superpowers/specs/2026-07-10-onecode-cli-configuration-command-split-design.md) - `config`, `init-verifier-policy`

### Shell Projection
- [Shell v4 Public Contract](superpowers/specs/2026-07-10-onecode-shell-v4-public-contract-design.md) - Structured output schema for external consumers
- Access via: `onecode shell-schema` or `GET /v1/onecode/shell/schema`

### Web API
- [LibreChat Shell Integration](superpowers/specs/2026-05-30-onecode-librechat-shell-design.md) - OpenAI-compatible HTTP API
- Start server: `onecode serve --host 127.0.0.1 --port 19080`
- Endpoints: `/health`, `/v1/models`, `/v1/chat/completions`

## Development

### Testing & Verification
- Follow-up work starts from the [2026-10-16 follow-up development handbook](superpowers/plans/2026-10-16-onecode-followup-development-handbook.md)
- Run core tests: `bash scripts/verify-core.sh` (234 tests, ~7s)
- Run full suite: `bash scripts/verify.sh` (907 tests, ~21s)
- Smoke check: `onecode doctor`

### Training & Benchmarking
- [Training Data Generation](superpowers/specs/2026-07-10-onecode-training-benchmark-rule-schema-design.md)
- [Evidence Chain Performance](superpowers/specs/2026-06-02-onecode-evidence-chain-performance-balance-design.md)
- List benchmarks: `onecode benchmark`
- Run benchmarks: `onecode benchmark --run --workspace-root /tmp/bench`

### Safety & Security
- [Sandbox Design](../README.md#docker-sandbox-smoke-check) - Docker isolation with network disabled
- [Path Guard](../README.md#safety-model) - Workspace containment and sensitive file protection
- [Approval System](../README.md#local-agent-shell) - User approval for destructive operations

## Development History

### Current Release
- Version: v1.0.0 (2026-10-20). Tag `v1.0.0` is `dd51424`. `main` is `d6e00ce` for the conductor slice, recorded in `85eefbe`. Task rules remain the follow-up note.
- [Release Checklist](RELEASE_CHECKLIST.md) - Release verification process
- [Task rule follow-up](closure/ONECODE_TASK_RULE_FOLLOWUP_2026-10-20.md) - Protected paths, close into the sandbox check, one implementation repair, gateway checkpoint

### Closure Reports
All development closure and verification records live in the [closure/](closure/) directory (64 documents).

Key closure documents:
- [Next development handbook](closure/ONECODE_NEXT_DEVELOPMENT_HANDBOOK_2026-10-23.md) - Three-phase handbook: controlled-scope closure + agent capability evolution
- [Conductor closeout](closure/ONECODE_CONDUCTOR_CLOSEOUT_2026-10-22.md) - One rewrite, confirmed memory, MCP names, n100 check
- [Controlled-scope plan](closure/ONECODE_CONTROLLED_SCOPE_PLAN_2026-10-22.md) - Next work under the current approval and ledger boundary
- [Long-task plan](closure/ONECODE_LONG_TASK_PLAN_2026-10-21.md) - Later scheme; rule changes not approved
- [Asset-write closeout](closure/ONECODE_ASSET_WRITE_CLOSEOUT_2026-10-21.md) - Complete-file writes and the survey search-miss fix
- [Shell read closeout](closure/ONECODE_SHELL_READ_CLOSEOUT_2026-10-21.md) - Chat survey, approval diff, n100 live tasks at 812bab7
- [Task rule follow-up](closure/ONECODE_TASK_RULE_FOLLOWUP_2026-10-20.md) - Current task rules after tag v1.0.0
- [v1.0.0 release](closure/ONECODE_V1_0_RELEASE_2026-10-20.md) - Formal release on the n100 acceptance
- [Zhouyi Math Optimization Closure (Oct)](closure/ONECODE_ZHOUYI_MATH_OPTIMIZATION_CLOSURE_2026-10-07.md) - Da Yan probability asymmetry, Nuclear attractor mapping typo
- [Zhouyi Math Optimization Closure](closure/ONECODE_ZHOUYI_MATH_OPTIMIZATION_CLOSURE_2026-09-18.md) - Four symbols bit order, exchange operator, nuclear attractor theorem, Da Yan measure, KL divergence
- [v0.8 Final Closure](closure/ONECODE_V0_8_FINAL_CLOSURE_2026-07-10.md)
- [I Ching v2 Canonicalization](closure/ONECODE_ICHING_V2_CANONICALIZATION_CLOSURE_2026-07-10.md)
- [LibreChat v0.8.7 Integration](closure/ONECODE_LIBRECHAT_V087_HARDENING_CLOSURE_2026-07-15.md)
- [Comprehensive Audit Remediation](closure/ONECODE_COMPREHENSIVE_AUDIT_REMEDIATION_CLOSURE_2026-09-01.md) - all six audit items closed, training package split
- [Comprehensive Audit](closure/ONECODE_COMPREHENSIVE_AUDIT_2026-09-01.md) - the source audit it answers

See the `closure/` directory for complete development history.

## Advanced Topics

- [Skill Context Integration](superpowers/specs/2026-07-03-onecode-skill-rule-kernel-integration-design.md) - Bounded rule evidence
- [Safe Agent Router](superpowers/specs/2026-07-13-onecode-safe-agent-shell-runtime-design.md) - Natural language inspection
- [YiZiJue Controlled Decoding](YIZIJUE_CONTROLLED_DECODING_PROBABILITY_RULES.md) - Logits policy for status prediction
- [Rule Absorption](superpowers/specs/2026-06-05-onecode-claw-code-rule-absorption-design.md) - How external tool rules are absorbed

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for:
- How to set up your development environment
- Understanding the I Ching state system (required reading)
- Code review process
- Testing requirements

## Questions?

- Check `onecode doctor` for system health
- Run `onecode math-audit` to verify rule integrity
- Inspect a run: `onecode inspect --workspace /path --run-id <id>`
- View shell schema: `onecode shell-schema`

For bugs or feature requests, see [CONTRIBUTING.md](../CONTRIBUTING.md).
