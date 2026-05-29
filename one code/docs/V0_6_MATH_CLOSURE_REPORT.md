# OneCode v0.6 Math Closure Report

Baseline: `49a505d feat: expose liangyi sixiang state pipeline`

Verification baseline:

- `scripts/verify.sh`: 228 tests OK
- `doctor status: ok`
- `audit-self status: ok`

## Scope

This report records the verified OneCode control-surface model after the v0.6 rule closure work. It is an audit document, not a second rules engine. The code of record remains `IchingKernel`, `LogosGate`, `PathGuard`, runner evidence, checkpoints, and ledgers.

## State Pipeline

The verified feature pipeline is:

```text
Taiyi -> Liangyi -> Sixiang -> Bagua -> 64-hexagram
```

The same 6-bit state tensor is projected through each layer:

- Taiyi: raw physical evidence such as path safety, API timeout, SHA256 state, and write outcome.
- Liangyi: `liangyi` / `liangyi_bits()` projects each bit into yin or yang with active/inactive runtime semantics.
- Sixiang: `overlapping_four_symbols()` builds adjacent 2-bit windows; `four_symbol_balance` / `four_symbol_balance_vector()` detects `tai_yang` overflow.
- Bagua: lower three bits are the inner asset trigram; upper three bits are the outer environment trigram.
- 64-hexagram: `S = (O << 3) | I` is the macro state consumed by `transition()`.

## Corrected Completion Case

A fully completed write initially classifies as:

```text
QIAN/QIAN = 63
```

The macro transition layer then performs the verified cooldown:

```text
GEN/QIAN = 39
```

This is `yang_overload_cooldown`. Its dispatch semantics are `cooldown + continue`, not halt.

Important distinction:

- `balance_mask() is local yin-yang feedback`.
- `transition() performs macro cooldown`.

Therefore `63 -> 39` is the macro transition result for pure yang completion. It must not be documented as the generic `balance_mask()` path.

## Sovereignty And Timeout Cases

Sovereignty breach remains:

```text
LI/KUN = 48
```

This halts because the outer trigram is sovereignty fire, and physical write authority is denied before disk mutation.

HTTP timeout remains:

```text
KAN/ZHEN = 17
```

This checkpoints the recovery seed for later resume.

## Evidence Surface

Runner and execution evidence now expose the mathematical surface directly:

- `raw_status_code`
- `balanced_status_code`
- `balance_mask`
- `four_symbol_decision`
- `four_symbol_change_mask`
- `global_entropy`
- `global_entropy_decision`
- `iching_profile`

The profile includes `liangyi`, `overlapping_four_symbols`, `four_symbol_balance`, yin-yang pressure, trigrams, five-element dynamics, evolved element modulation, and transition output.

## Post-Audit Corrections

The entropy gate must preserve polarity direction: low entropy is polarization, not rollback.

- Positive low entropy means consistent yang completion. It is accepted as `accept_positive_polarity`, then macro transition applies cooldown (`QIAN/QIAN = 63` -> `GEN/QIAN = 39`).
- Negative low entropy means consistent yin stasis or failure. It collapses to `rollback_negative_polarity` and the recovery status.

The rule discovery branch is live:

```text
KUN/KUN = 0
```

This maps to `discover + stop`, so unmapped empty-state evidence does not silently continue as activation.

Patch evidence is multi-hash evidence: `patch_text evidence requires pre/post and block hashes`, namely `pre_sha256`, `post_sha256`, `search_block_sha256`, and `replace_block_sha256`.

## Audit Conclusion

The verified OneCode kernel now closes the rule chain from bit-level polarity to macro execution state without adding parallel control variables. External facts are evidence, not law; they are collapsed into the 6-bit tensor and interpreted through the rule surface above.
