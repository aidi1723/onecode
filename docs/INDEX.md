# OneCode Documentation Index

This index helps you navigate OneCode's documentation, which is organized by purpose and audience.

## Quick Start

- [README.md](../README.md) - Installation, verification, and basic usage
- [DESIGN.md](../DESIGN.md) - Core design principles
- [CONTRIBUTING.md](../CONTRIBUTING.md) - How to contribute (see onboarding guide below)

## Architecture & Design

OneCode uses an I Ching (易经) based state system for deterministic control flow. Start here to understand the core architecture:

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Visual diagrams and architecture overview (START HERE)
- **[ICHING_QUICKREF.md](ICHING_QUICKREF.md)** - Quick reference for debugging status codes

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
- Version: v0.8.0 (2026-07-10)
- [Release Checklist](RELEASE_CHECKLIST.md) - Release verification process

### Closure Reports
All development closure and verification records have been moved to the [closure/](closure/) directory (37 documents).

Key closure documents:
- [v0.8 Final Closure](closure/ONECODE_V0_8_FINAL_CLOSURE_2026-07-10.md)
- [I Ching v2 Canonicalization](closure/ONECODE_ICHING_V2_CANONICALIZATION_CLOSURE_2026-07-10.md)
- [LibreChat v0.8.7 Integration](closure/ONECODE_LIBRECHAT_V087_HARDENING_CLOSURE_2026-07-15.md)

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
