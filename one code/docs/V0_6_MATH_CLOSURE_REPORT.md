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
- Negative low entropy means consistent yin stasis or failure. It collapses to `rollback_negative_polarity` with `entropy_negative_polarity_rollback`, so entropy rollback is not mislabeled as `network_water_preserves_resume_seed`.

The rule discovery branch is live:

```text
KUN/KUN = 0
```

This maps to `discover + stop`, so unmapped empty-state evidence does not silently continue as activation.

Patch evidence is multi-hash evidence: `patch_text evidence requires pre/post and block hashes`, namely `pre_sha256`, `post_sha256`, `search_block_sha256`, and `replace_block_sha256`.

## Control-Theory Mapping Closure

The following modern control-theory mappings are accepted into the OneCode rule
surface because they preserve deterministic execution and do not add a second
runtime law:

- `transition_graph()` maps all `64` status codes through the existing
  `transition()` function. This is the formal finite-state graph for orbit and
  attractor inspection.
- `attractor_analysis()` enumerates terminal cycles in that graph. It is an
  audit helper for deadlock and limit-cycle review, not a scheduler.
- `stability_analysis()` summarizes convergence boundaries over the same graph:
  steps-to-attractor, nontrivial limit-cycle count, and Lyapunov energy deltas.
  It is evidence for review, not a proof that every external disturbance
  converges in a fixed number of steps.
- `topology_certificate()` records the `Q6` topology boundary: `64` vertices,
  `192` hypercube edges, closed runtime transitions, and the Hamming-distance
  histogram of the actual transition map.
- `lyapunov_certificate()` turns the scalar energy into an explicit audit
  certificate by enumerating every transition delta and listing any
  energy-increasing violations.
- `entropy_gate_certificate()` evaluates a status sequence with Shannon entropy
  over full 6-bit symbols and emits a deterministic audit recommendation such
  as `sovereignty_halt`, `checkpoint`, `continue`, or `observe`. It is an
  efficiency audit for repeated failure or exploratory spread, not a
  probabilistic scheduler.
- `totality_certificate()` checks that the known runtime and resume evidence
  classes map into the closed `Q6` codomain without undefined branches.
- `safety_dominance_certificate()` checks the safety priority rule: dangerous
  inputs such as path breach, permission denial, invalid intent, resource
  budget breach, malformed input, and bad checkpoint evidence must not pass into
  active execution actions.
- `collision_risk_certificate()` reviews many-to-one projection collisions and
  flags any collision where dangerous and non-dangerous samples share a state
  that still transitions into an active pass-through action.
- `lyapunov_energy()` gives a deterministic scalar energy over a status code,
  combining yin-yang imbalance, transition severity, and execution bandwidth.
  Lower energy means closer to a safe balanced operating posture.
- `state_distribution_entropy()` computes entropy over full 6-bit status
  symbols, complementing the existing bit-level `global_entropy()`.
- `hysteresis_gate()` implements deterministic dual-threshold quantization for
  continuous inputs, so future timeout/resource projections can avoid boundary
  chattering without probabilistic sampling.

These mappings are consistent with the existing rule language:

```text
64 hexagrams        -> finite discrete state space
line change         -> deterministic transition
yin-yang balance    -> Lyapunov-style energy pressure
five-element matrix -> control bandwidth and modulation
entropy             -> uncertainty gate
time-position rule  -> hysteresis for continuous evidence
orbit review        -> stability audit over the 64-state graph
Q6 boundary         -> topology certificate over 64 vertices and Hamming edges
energy descent      -> Lyapunov certificate over every deterministic edge
entropy gate        -> sequence-level damping recommendation without sampling
total mapping       -> known evidence classes map into Q6 without undefined branches
safety dominance    -> dangerous evidence cannot override into pass-through action
collision review    -> dimensionality-loss collisions are checked by action domain
```

Reference-only ideas that are intentionally not integrated into the kernel:

- probabilistic sigmoid sampling for state bits, because it would weaken
  replayability;
- runtime self-learning of the five-element gain matrix, because it would
  weaken auditability;
- multi-agent tensor-product state spaces, because OneCode is currently a
  local-first controlled file-change kernel, not a distributed multi-agent
  runtime.

The read-only CLI command `onecode math-audit` exposes this mapping as JSON. It
reports transition graph size, attractor count, Lyapunov energy range, accepted
mappings, stability boundaries, and reference-only formulas. It does not mutate
runtime evidence and does not participate in scheduling.

## Audit Conclusion

The verified OneCode kernel now closes the rule chain from bit-level polarity to macro execution state without adding parallel control variables. External facts are evidence, not law; they are collapsed into the 6-bit tensor and interpreted through the rule surface above.
