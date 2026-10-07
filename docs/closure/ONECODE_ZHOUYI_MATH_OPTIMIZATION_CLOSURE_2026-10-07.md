# OneCode Zhouyi Math Optimization Closure

**Date**: 2026-10-07
**Component**: `onecode.kernel`
**Status**: COMPLETED

## Context
Following a deep mathematical and logical audit of the OneCode I Ching Kernel (`hexagram.py` and related modules), two specific historical anomalies in the interpretation and implementation of classical Yijing rules were identified and successfully remediated.

## Fixes Applied

### 1. Classical Da Yan (大衍之数) Probability Measure Correction
**File**: `src/onecode/kernel/hexagram.py`
**Changes**:
- Corrected the `DAYAN_PROBABILITIES` array from a symmetric `3-5-5-3` distribution to the authentic asymmetric `3-7-5-1` mathematical derivation.
- 9 (Old Yang): 3/16 (0.1875)
- 8 (Young Yin): 7/16 (0.4375)  *[Previously 5/16]*
- 7 (Young Yang): 5/16 (0.3125)
- 6 (Old Yin): 1/16 (0.0625)   *[Previously 3/16]*
**Rationale**: The classical Yarrow Stalk (蓍草法) generation process intrinsically yields an asymmetric probability space where Old Yin (6) is significantly rarer than Old Yang (9), reflecting the philosophical axiom of "Yang moves, Yin is still."

### 2. Nuclear Attractor Mapping Typo
**File**: `src/onecode/kernel/hexagram_certificates.py`
**Changes**:
- Fixed a docstring reversal in `nuclear_attractor` where the names for the 2-cycle attractors 21 and 42 were swapped.
- 21 (0b010101) is correctly labeled as Ji Ji (既济) - Water over Fire.
- 42 (0b101010) is correctly labeled as Wei Ji (未济) - Fire over Water.

## Verification
- Local unit tests in `tests/` passed cleanly (`unittest discover`).
- Mathematical topology checks (e.g. `onecode math-audit`) remain closed and unviolated.
- The mathematical fidelity of the engine to classical I Ching texts is now perfectly aligned.
