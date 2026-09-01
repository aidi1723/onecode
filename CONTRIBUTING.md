# Contributing to OneCode

Thank you for considering contributing to OneCode! This guide will help you get started.

## Quick Start

1. **Set up development environment**:
   ```bash
   git clone <repository-url>
   cd onecode
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e .[tui]
   ```

2. **Verify your setup**:
   ```bash
   bash scripts/verify.sh
   ```
   This runs 907 tests and takes ~21 seconds. All tests should pass.

3. **Run smoke check**:
   ```bash
   onecode doctor
   ```

## Understanding OneCode Architecture (Required Reading)

OneCode uses an **I Ching (易经) based state system** for deterministic control flow. Before contributing code, you must understand how this works:

### The 64-State System

Every run produces a **6-bit status code** (0-63) representing one of the 64 hexagrams:
- Each bit is a yin (0) or yang (1) line
- Bits 0-2: inner trigram (task state)
- Bits 3-5: outer trigram (environment/context)

**Example**: Status code 40 = `0b101000`
- Inner: `000` (Kun/坤) → earth element
- Outer: `101` (Li/离) → fire element
- Relation: fire controls earth → halt with "sovereignty_fire_boundary_halt"

### Key Concepts

1. **Trigrams → Elements**:
   - Qian (乾), Dui (兑) → metal
   - Zhen (震), Xun (巽) → wood
   - Kan (坎) → water
   - Li (离) → fire
   - Kun (坤), Gen (艮) → earth

2. **Five-Element Relations**:
   - **Generation cycle**: wood→fire→earth→metal→water (accelerate/continue)
   - **Control cycle**: wood→earth→water→fire→metal (halt/throttle/prune)

3. **Yin-Yang Pressure**:
   - Pure yang (6 yang lines) → cooldown
   - Pure yin (0 yang lines) → discover
   - Balanced (3-4 yang) → use element relations

4. **Transition Priority** (enforced in this order):
   1. Hard safety (path breach, timeout) overrides all
   2. Yin-yang pressure
   3. Five-element relations
   4. Neutral fallback

### Essential Reading

Before making changes to the kernel, read these design documents in order:

1. [I Ching Complete Rule Kernel](docs/superpowers/specs/2026-05-28-onecode-v0.5-iching-complete-rule-kernel-design.md) - Mathematical foundation
2. [Yin-Yang Five-Element Runtime Mapping](docs/superpowers/specs/2026-06-01-onecode-yinyang-wuxing-runtime-rule-mapping-design.md) - Execution behavior mapping
3. [I Ching Source Alignment](docs/superpowers/specs/2026-05-28-onecode-iching-source-alignment.md) - Design rationale

### Debugging Status Codes

When debugging a failed run:

1. **Inspect the run**:
   ```bash
   onecode inspect --workspace /path --run-id <run-id>
   ```

2. **Check the iching_profile** in the output:
   - `status_code`: the 6-bit hexagram
   - `inner_trigram`, `outer_trigram`: which trigrams are active
   - `yin_yang_profile`: balance state
   - `transition_action`: what the kernel decided to do

3. **Verify rule integrity**:
   ```bash
   onecode math-audit
   ```
   This checks for state-space coverage, attractor cycles, and stability boundaries.

## Development Guidelines

### Code Changes

1. **TDD required**: Write failing tests first, then implement
2. **Verify before commit**:
   ```bash
   bash scripts/verify.sh
   ```
3. **Keep changes focused**: One logical change per commit
4. **Follow existing patterns**: Match the style of surrounding code

### Kernel Changes (Special Rules)

Changes to `src/onecode/kernel/hexagram.py` require extra scrutiny:

- **Do NOT add external control variables** (confidence, priority, retry counts, mood)
- **Preserve the rule authority chain**: yin/yang → trigrams → five-elements → transition → dispatch
- **Keep rule changes deterministic**: Same input → same output, always
- **Add tests for new transitions**: Show that the math closes

### Testing Requirements

- Core tests must pass: `bash scripts/verify-core.sh` (234 tests, ~7s)
- Full suite must pass: `bash scripts/verify.sh` (907 tests, ~21s)
- Add tests for new features before implementing them
- Edge cases: test yin-overflow, yang-overflow, pure states, balanced states

### Documentation

- Update `docs/INDEX.md` if adding new features
- Design documents go in `docs/superpowers/specs/`
- Follow the existing naming pattern: `YYYY-MM-DD-onecode-<feature>-design.md`
- Closure reports go in `docs/` after verification

## Repository Structure

Keep these boundaries clean:

- **OneCode core**: No gateway dependencies
- **LibreChat shell**: Separate repository, integrated via local API
- **No generated data in commits**: Run evidence, temporary workspaces, API keys

### What NOT to Commit

- `.env`, `.env.*` files
- Generated run data under `.onecode/`
- Temporary workspaces (`/tmp/onecode-*`)
- Private keys or provider credentials
- Training corpus or benchmark results

## Pull Request Process

1. **Verify locally** before pushing:
   ```bash
   bash scripts/verify.sh
   python3 -m onecode doctor
   ```

2. **Write clear commit messages**:
   ```
   Brief summary of change
   
   - Detailed point about what changed
   - Why the change was needed
   - Reference to design doc if applicable
   ```

3. **Link design documents**: If implementing a spec, reference it in the PR

4. **Update version** if needed (coordinate with maintainers)

## Getting Help

- **Check existing docs**: [Documentation Index](docs/INDEX.md)
- **Run diagnostics**: `onecode doctor`, `onecode math-audit`
- **Inspect evidence**: `onecode inspect --workspace /path --run-id <id>`
- **Ask questions**: Open an issue with the `question` label

## Design Philosophy

OneCode follows these principles:

1. **Local-first**: No network dependencies for core kernel
2. **Deterministic**: Same input → same output, always
3. **Evidence-based**: Append-only records, tamper-evident chains
4. **Rule closure**: External facts are evidence, not law
5. **Mathematical foundation**: Control theory over folklore

When in doubt, ask: "Does this preserve determinism?" and "Does this close inside the existing rule surface?"

## License

OneCode is GPL-3.0-only. All contributions must be compatible with this license.

---

Thank you for contributing! Your changes help make OneCode more robust and capable.
