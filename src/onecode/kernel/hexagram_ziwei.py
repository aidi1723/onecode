"""OneCode Ziwei Doushu Cross-Validation & Distributed Consensus Mixin.

This module implements the mathematical and diagnostic extensions cross-validated
with the Ziwei Doushu engine (Renhuai123/ziwei-doushu):
- Five Elements Bureau (五行局) dynamic scaling: task_bureau_profile
- Self-transformation & internal entropy leakage (自化): self_sihua_profile
- Causal root palace tracing (来因宫): causal_origin_profile
- 4-point distributed consensus (三方四正): triad_consensus_profile
"""
from __future__ import annotations

import math
from typing import Any


def _evaluate_ziwei_pattern(
    turn_number: int,
    current_status: int,
    ast_valid: bool = True,
    token_budget_ok: bool = True,
    verifier_passed: bool | None = None,
    environment_ok: bool = True,
    consecutive_read_stalls: int = 0,
    consecutive_syntax_errors: int = 0,
    undefined_symbols_count: int = 0,
    fatal_regression: bool = False,
) -> dict[str, Any]:
    """Classify execution state against classical Ziwei formations (格局矩阵).

    Evaluates resonance (吉格) vs impediments (凶格 / 陷阱格) to recommend
    deterministic execution remedies and state transitions.
    """
    if verifier_passed is False and not token_budget_ok:
        return {
            "pattern": "羊陀夹忌",
            "level": "broken",
            "action": "switch_to_surgical_diff",
            "remedy": "switch_to_surgical_unified_diff",
            "description": "Deadlock trap: verifier failing while resource or file preview is truncated.",
        }
    if fatal_regression:
        return {
            "pattern": "铃昌陀武",
            "level": "critical",
            "action": "rollback",
            "remedy": "rollback_to_last_stable_checkpoint",
            "description": "Fatal logic inversion: patch caused regression on previously passing baseline.",
        }
    if consecutive_syntax_errors >= 2 and verifier_passed is not True:
        return {
            "pattern": "火铃夹命",
            "level": "broken",
            "action": "cooldown",
            "remedy": "force_deliberation_cooldown",
            "description": "Frantic retry cycle: repeated syntax/lint faults without reflection.",
        }
    if undefined_symbols_count > 0:
        return {
            "pattern": "空劫夹命",
            "level": "caution",
            "action": "reanchor",
            "remedy": "reanchor_workspace_symbols",
            "description": "Phantom identifiers referenced. Re-reading definitions from workspace baseline.",
        }
    if not environment_ok:
        return {
            "pattern": "化忌入迁移",
            "level": "caution",
            "action": "retry",
            "remedy": "retry_with_system_embedding_and_backoff",
            "description": "External environment, gateway timeout, or WAF blockage.",
        }
    if consecutive_read_stalls >= 2:
        return {
            "pattern": "自化忌",
            "level": "caution",
            "action": "synthesize",
            "remedy": "break_read_hesitation_loop",
            "description": "Read-only hesitation loop: multiple read turns without code modification.",
        }
    if verifier_passed is False:
        return {
            "pattern": "化忌入官禄",
            "level": "caution",
            "action": "repair",
            "remedy": "inspect_test_traceback",
            "description": "Execution verifier failed: focus patches on failing assertions.",
        }
    if ast_valid and token_budget_ok and verifier_passed is True and environment_ok and ((current_status & 0b111111) == 63):
        return {
            "pattern": "三奇加会",
            "level": "excellent",
            "action": "commit",
            "remedy": "proceed_to_commit",
            "description": "Full 4-point consensus with pure yang fulfillment. Ready for delivery.",
        }
    if ast_valid and verifier_passed is True and token_budget_ok:
        return {
            "pattern": "科权双会",
            "level": "reinforced",
            "action": "approve",
            "remedy": "standard_approval",
            "description": "Syntax verified and tests passing.",
        }
    if ast_valid and token_budget_ok and consecutive_read_stalls == 0 and consecutive_syntax_errors == 0:
        return {
            "pattern": "机月同梁",
            "level": "balanced",
            "action": "continue",
            "remedy": "sequential_progression",
            "description": "Methodical execution following standard contracts.",
        }
    return {
        "pattern": "成格",
        "level": "balanced",
        "action": "continue",
        "remedy": "continue",
        "description": "Standard operational progression.",
    }


def _evaluate_shen_gong_anchorage(
    turn_number: int,
    current_status: int,
    token_budget_ok: bool = True,
    verifier_passed: bool | None = None,
    environment_ok: bool = True,
    ast_valid: bool = True,
    has_test_suite: bool = True,
    contract_ambiguity: bool = False,
    architectural_risk: bool = False,
    interop_risk: bool = False,
) -> dict[str, Any]:
    """Evaluate post-natal execution anchorage and fallback shelter (身宫寄托).

    In Ziwei Doushu, Shen Gong (身宫) represents the post-natal anchor of action and
    reality-check shelter. Across all 12 birth hours H in {0..11}, the relative
    offset from 命宫 is k = (-2H) mod 12 in {0, 2, 4, 6, 8, 10} = 2*Z_12 ~= Z_6.
    The six possible anchor palaces are:
    - 0: 命宫 (身命同宫) -> Contract Spec & Baseline Driven
    - 2: 夫妻宫 (身寄夫妻) -> Interop & Caller Interface Compatibility
    - 4: 财帛宫 (身寄财帛) -> Token Economy & Minimal Surgical Diff
    - 6: 迁移宫 (身寄迁移) -> Environment Adaptation & Gateway Shielding
    - 8: 官禄宫 (身寄官禄) -> Verifier & Test Assertion Driven
    - 10: 福德宫 (身寄福德) -> Architectural Integrity & Modular Decoupling
    """
    palace_names = {
        0: "命宫",
        2: "夫妻宫",
        4: "财帛宫",
        6: "迁移宫",
        8: "官禄宫",
        10: "福德宫",
    }
    modes = {
        0: "contract_spec_driven",
        2: "interop_compatible",
        4: "token_minimal_diff",
        6: "environment_adaptive",
        8: "verifier_driven",
        10: "architectural_integrity",
    }
    guidance_map = {
        0: "Anchor strictly to specification baseline (身命同宫): Rely strictly on user prompt specification and core contract requirements.",
        2: "Anchor to interface compatibility (身寄夫妻): Modifying shared module contract. Preserve function signatures and backward compatibility for callers.",
        4: "Anchor to token conservation (身寄财帛): File exceeds comfortable asset length or budget is low. Produce minimal surgical diffs and avoid full-file rewrites.",
        6: "Anchor to environment shelter (身寄迁移): External gateway or runtime barrier detected. Rely on standard library primitives and embed instructions defensively.",
        8: "Anchor to test verifier (身寄官禄): Prioritize passing existing test assertions. Align implementation strictly to test expectations.",
        10: "Anchor to structural integrity (身寄福德): High architectural complexity detected. Decouple helper logic, split functions, and preserve modular cleanliness.",
    }

    hour_branch = (turn_number - 1) % 12
    theoretical_index = (-2 * hour_branch) % 12

    if verifier_passed is False or (has_test_suite and verifier_passed is None and not ast_valid):
        active_index = 8
    elif not token_budget_ok:
        active_index = 4
    elif not environment_ok:
        active_index = 6
    elif architectural_risk:
        active_index = 10
    elif interop_risk:
        active_index = 2
    else:
        active_index = 0

    return {
        "turn_number": turn_number,
        "hour_branch_index": hour_branch,
        "theoretical_index": theoretical_index,
        "theoretical_palace": palace_names[theoretical_index],
        "active_index": active_index,
        "palace_name": palace_names[active_index],
        "anchorage_mode": modes[active_index],
        "shelter_guidance": guidance_map[active_index],
        "subgroup_parity": "even_subgroup_2z12",
        "is_valid_anchorage": active_index in palace_names,
    }


class IchingZiweiMixin:
    """Diagnostic and consensus extensions based on Ziwei Doushu isomorphism."""

    @classmethod
    def task_bureau_profile(cls, file_count: int, total_loc: int) -> dict[str, Any]:
        """Compute the Five Elements Bureau (五行局) and scheduling envelopes from workspace scale.

        Isomorphism with Ziwei Doushu Five Elements Bureau:
        - Scale < 4.0: 水二局 (Bureau 2, Water) - Agile single-file patch, budget 3 turns, timeout 45s.
        - Scale < 8.0: 木三局 (Bureau 3, Wood) - Incremental feature growth, budget 4 turns, timeout 60s.
        - Scale < 14.0: 金四局 (Bureau 4, Metal) - Rigid contract & type refactoring, budget 5 turns, timeout 90s.
        - Scale < 22.0: 土五局 (Bureau 5, Earth) - Schema/state persistence migration, budget 6 turns, timeout 120s.
        - Scale >= 22.0: 火六局 (Bureau 6, Fire) - Multi-module architecture evolution, budget 8 turns, timeout 180s.
        """
        scale = math.log(max(1, total_loc) + 1) * math.sqrt(max(1, file_count))
        if scale < 4.0:
            bureau = 2
            name = "水二局"
            turn_budget = 3
            timeout_sec = 45
            patch_strategy = "surgical_diff_only"
            preview_limit_chars = 4000
            repair_file_limit = 6
        elif scale < 8.0:
            bureau = 3
            name = "木三局"
            turn_budget = 4
            timeout_sec = 60
            patch_strategy = "incremental_feature_growth"
            preview_limit_chars = 6000
            repair_file_limit = 8
        elif scale < 14.0:
            bureau = 4
            name = "金四局"
            turn_budget = 5
            timeout_sec = 90
            patch_strategy = "strict_contract_refactoring"
            preview_limit_chars = 8000
            repair_file_limit = 10
        elif scale < 22.0:
            bureau = 5
            name = "土五局"
            turn_budget = 6
            timeout_sec = 120
            patch_strategy = "foundational_stability_migration"
            preview_limit_chars = 10000
            repair_file_limit = 12
        else:
            bureau = 6
            name = "火六局"
            turn_budget = 8
            timeout_sec = 180
            patch_strategy = "distributed_orchestration"
            preview_limit_chars = 14000
            repair_file_limit = 16

        return {
            "scale": round(scale, 2),
            "bureau": bureau,
            "bureau_name": name,
            "turn_budget": turn_budget,
            "timeout_sec": timeout_sec,
            "patch_strategy": patch_strategy,
            "preview_limit_chars": preview_limit_chars,
            "repair_file_limit": repair_file_limit,
        }

    @classmethod
    def self_sihua_profile(
        cls,
        current_turn: dict[str, Any],
        history: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        """Detect internal entropy dissipation and deadlock (宫干自化: 自化忌 / 自化禄 / 自化权 / 自化科).

        - 自化忌: Consecutive read-only turns without code modification or test runs (hesitation loop).
        - 自化禄: Phantom completion claim where model reports success without modified files or verifier pass.
        - 自化权: Excessive over-refactoring modifying too many files beyond task boundary.
        - 自化科: Pre-execution self-auditing with inline verification assertions.
        """
        tags: list[str] = []
        modified = current_turn.get("modified_files")
        modified_set = set(modified) if isinstance(modified, (list, set)) else set()
        has_test = bool(current_turn.get("has_test_run", False))
        test_passed = bool(current_turn.get("test_passed", False))
        action = str(current_turn.get("action", ""))

        history_list = history or []

        # 自化忌: read-only hesitation loop
        if not modified_set and not has_test:
            recent_stalls = [
                t for t in history_list[-2:]
                if not (t.get("modified_files") or t.get("has_test_run"))
            ]
            if len(recent_stalls) >= 1:
                tags.append("自化忌:circular_read_hesitation")

        # 自化禄: phantom completion without proof
        if action in {"complete", "continue", "finish"} and not modified_set and not test_passed:
            tags.append("自化禄:phantom_completion_without_verifier")

        # 自化权: scope explosion
        if len(modified_set) > 8:
            tags.append("自化权:excessive_scope_expansion")

        # 自化科: clean self-audit
        if action in {"audit", "checkpoint"} and not current_turn.get("error_traceback") and current_turn.get("read_files"):
            tags.append("自化科:pre_execution_self_audit")

        return tags

    @classmethod
    def causal_origin_profile(
        cls,
        error_traceback: str | None,
        history: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Trace the causal origin palace (来因宫) of an execution error / halt.

        When a failure (化忌) occurs at Turn N, trace back through checkpoint history
        to identify which historical turn (M < N) modified the file or symbol appearing
        in the error traceback.
        """
        if not error_traceback or not history:
            return None

        branches = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")
        for past_turn in reversed(history):
            modified = past_turn.get("modified_files")
            files = list(modified) if isinstance(modified, (list, set)) else []
            for file_path in files:
                if str(file_path) in error_traceback:
                    turn_id = int(past_turn.get("turn_id", past_turn.get("turn_index", 0)))
                    branch_idx = (turn_id - 1) % 12 if turn_id > 0 else 0
                    return {
                        "incoming_turn_id": turn_id,
                        "incoming_branch": branches[branch_idx],
                        "culprit_file": str(file_path),
                        "target_rollback_point": max(0, turn_id - 1),
                        "reason": f"Defect originated in Turn {turn_id} modifying {file_path}",
                    }
        return None

    @classmethod
    def triad_consensus_profile(
        cls,
        turn_number: int,
        current_status: int,
        ast_valid: bool = True,
        token_budget_ok: bool = True,
        verifier_passed: bool = True,
        environment_ok: bool = True,
    ) -> dict[str, Any]:
        """Evaluate 4-point distributed consensus across San Fang Si Zheng (三方四正):
        - Palace 1 (命宫 / Current Turn): Patch AST syntactic validity
        - Palace 5 (财帛 / Token & Resource Envelope): Token limit & preview truncation
        - Palace 9 (官禄 / Verifier & Linter Status): Test suite pass/fail
        - Palace 7 (迁移 / External Environment & Sandbox): Gateway reachability & container env

        Recognizes classical formations:
        - 三奇加会 (All 4 valid) -> Excellent, ready for autonomous commit
        - 科权双会 (Syntax + Verifier valid) -> Reinforced, verified patch
        - 羊陀夹忌 (Deadlock: Verifier failed + Token/file preview truncated) -> Broken, switch strategy
        - 化忌入迁移 (Gateway/Env failure) -> Caution, retry with system-in-user embedding
        - 成格 -> Balanced, standard step
        """
        branches = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")
        branch_idx = (turn_number - 1) % 12

        points = {
            "ming": {
                "branch": branches[branch_idx],
                "dimension": "syntax_ast",
                "ok": ast_valid and ((current_status & 0b111111) not in {0, 32}),
            },
            "cai": {
                "branch": branches[(branch_idx + 4) % 12],
                "dimension": "token_resources",
                "ok": token_budget_ok,
            },
            "guan": {
                "branch": branches[(branch_idx + 8) % 12],
                "dimension": "verifier_test",
                "ok": verifier_passed,
            },
            "qian": {
                "branch": branches[(branch_idx + 6) % 12],
                "dimension": "environment_gateway",
                "ok": environment_ok,
            },
        }

        if not points["guan"]["ok"] and not points["cai"]["ok"]:
            pattern = "羊陀夹忌"
            level = "broken"
            remedy = "switch_to_surgical_unified_diff"
            description = "Deadlock trap: verifier failing while resource or file preview is truncated."
        elif not points["qian"]["ok"]:
            pattern = "化忌入迁移"
            level = "caution"
            remedy = "retry_with_system_embedding_and_backoff"
            description = "External environment, gateway timeout, or WAF blockage."
        elif all(p["ok"] for p in points.values()):
            pattern = "三奇加会"
            level = "excellent"
            remedy = "proceed_to_commit"
            description = "Full 4-point consensus: syntax, resources, verifier, and environment all clean."
        elif points["guan"]["ok"] and points["ming"]["ok"]:
            pattern = "科权双会"
            level = "reinforced"
            remedy = "standard_approval"
            description = "Syntax and verifier both confirmed."
        elif not points["guan"]["ok"]:
            pattern = "化忌入官禄"
            level = "caution"
            remedy = "inspect_test_traceback"
            description = "Execution verifier assertion failed."
        else:
            pattern = "成格"
            level = "balanced"
            remedy = "continue"
            description = "Standard operational progression."

        return {
            "turn_number": turn_number,
            "branch": branches[branch_idx],
            "pattern": pattern,
            "pattern_level": level,
            "recommended_remedy": remedy,
            "description": description,
            "points": points,
        }

    @classmethod
    def ziwei_pattern_matrix_profile(
        cls,
        turn_number: int,
        current_status: int,
        ast_valid: bool = True,
        token_budget_ok: bool = True,
        verifier_passed: bool | None = None,
        environment_ok: bool = True,
        consecutive_read_stalls: int = 0,
        consecutive_syntax_errors: int = 0,
        undefined_symbols_count: int = 0,
        fatal_regression: bool = False,
    ) -> dict[str, Any]:
        """Classify execution state against classical Ziwei formations (格局矩阵)."""
        return _evaluate_ziwei_pattern(
            turn_number=turn_number,
            current_status=current_status,
            ast_valid=ast_valid,
            token_budget_ok=token_budget_ok,
            verifier_passed=verifier_passed,
            environment_ok=environment_ok,
            consecutive_read_stalls=consecutive_read_stalls,
            consecutive_syntax_errors=consecutive_syntax_errors,
            undefined_symbols_count=undefined_symbols_count,
            fatal_regression=fatal_regression,
        )

    @classmethod
    def sovereign_ring_isomorphism_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of the Sovereign Hexagram Ring <-> Earthly Branches isomorphism.

        Theorems:
        1. Bijective mapping: 12 sovereign hexagrams bijection to 12 earthly branches.
        2. Opposition involution: Opposite branch (b + 6 mod 12) is bitwise NOT in Q_6.
        3. Triad hypercube balance: Water and fire trines have exactly 3.00 mean yang bits;
           metal and wood trines are exact reciprocal duals (average = 3.00).
        """
        branches = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")
        codes = cls.SOVEREIGN_HEXAGRAM_CODES  # type: ignore[attr-defined]

        opposition_verified = True
        for b_idx in range(12):
            opp_idx = (b_idx + 6) % 12
            if (codes[b_idx] ^ 0b111111) != codes[opp_idx]:
                opposition_verified = False
                break

        water_yang = sum((codes[i] & 0b111111).bit_count() for i in (8, 0, 4))
        fire_yang = sum((codes[i] & 0b111111).bit_count() for i in (2, 6, 10))
        metal_yang = sum((codes[i] & 0b111111).bit_count() for i in (5, 9, 1))
        wood_yang = sum((codes[i] & 0b111111).bit_count() for i in (11, 3, 7))

        triads_balanced = (
            water_yang == 9
            and fire_yang == 9
            and (metal_yang + wood_yang) == 18
        )

        return {
            "status": "verified" if (opposition_verified and triads_balanced) else "failed",
            "branch_count": len(branches),
            "opposition_involution_verified": opposition_verified,
            "triad_balance_verified": triads_balanced,
            "mean_yang_water": round(water_yang / 3.0, 2),
            "mean_yang_fire": round(fire_yang / 3.0, 2),
            "mean_yang_metal": round(metal_yang / 3.0, 2),
            "mean_yang_wood": round(wood_yang / 3.0, 2),
            "dual_axis_mean": round((metal_yang + wood_yang) / 6.0, 2),
        }

    @classmethod
    def an_he_coupling_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Six Harmonies (六合 / 暗合) on the 6-bit Boolean Hypercube.

        Theorems:
        1. Algebraic coupling: (b_1 + b_2) = 1 (mod 12).
        2. Palindromic Hamming distance: [1, 3, 5, 5, 3, 1] across symmetric pairs.
        3. Dual couple invariant: YangSum(Pair_k) + YangSum(Pair_{7-k}) == 12 for all k in {1, 2, 3}.
        """
        codes = cls.SOVEREIGN_HEXAGRAM_CODES  # type: ignore[attr-defined]
        pairs = [(0, 1), (2, 11), (3, 10), (4, 9), (5, 8), (6, 7)]

        distances = []
        yang_sums = []
        for b1, b2 in pairs:
            c1, c2 = codes[b1], codes[b2]
            distances.append((c1 ^ c2).bit_count())
            w1 = (c1 & 0b111111).bit_count()
            w2 = (c2 & 0b111111).bit_count()
            yang_sums.append(w1 + w2)

        is_palindrome = (distances == list(reversed(distances)))
        dual_sums_constant = (
            (yang_sums[0] + yang_sums[5] == 12)
            and (yang_sums[1] + yang_sums[4] == 12)
            and (yang_sums[2] + yang_sums[3] == 12)
        )

        return {
            "status": "verified" if (is_palindrome and dual_sums_constant) else "failed",
            "pair_count": len(pairs),
            "hamming_distances": distances,
            "distance_palindrome_verified": is_palindrome,
            "yang_sums": yang_sums,
            "dual_sums_constant_12": dual_sums_constant,
            "mean_yang_per_pair": round(sum(yang_sums) / (2 * len(pairs)), 2),
        }

    @classmethod
    def ziwei_mathematical_audit(cls) -> dict[str, Any]:
        """Comprehensive mathematical audit of all Ziwei Doushu cross-validation certificates."""
        ring = cls.sovereign_ring_isomorphism_certificate()
        an_he = cls.an_he_coupling_certificate()
        shen_gong = cls.shen_gong_anchorage_certificate()
        all_passed = (
            ring.get("status") == "verified"
            and an_he.get("status") == "verified"
            and shen_gong.get("status") == "verified"
        )
        return {
            "status": "ok" if all_passed else "failed",
            "sovereign_ring": ring,
            "an_he_coupling": an_he,
            "shen_gong_anchorage": shen_gong,
        }

    @classmethod
    def shen_gong_anchorage_profile(
        cls,
        turn_number: int,
        current_status: int,
        token_budget_ok: bool = True,
        verifier_passed: bool | None = None,
        environment_ok: bool = True,
        ast_valid: bool = True,
        has_test_suite: bool = True,
        contract_ambiguity: bool = False,
        architectural_risk: bool = False,
        interop_risk: bool = False,
    ) -> dict[str, Any]:
        """Compute post-natal execution anchorage and fallback shelter (身宫寄托)."""
        return _evaluate_shen_gong_anchorage(
            turn_number=turn_number,
            current_status=current_status,
            token_budget_ok=token_budget_ok,
            verifier_passed=verifier_passed,
            environment_ok=environment_ok,
            ast_valid=ast_valid,
            has_test_suite=has_test_suite,
            contract_ambiguity=contract_ambiguity,
            architectural_risk=architectural_risk,
            interop_risk=interop_risk,
        )

    @classmethod
    def shen_gong_anchorage_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Shen Gong Even Subgroup Theorem (身宫偶数子群同构定理).

        Theorems:
        1. Subgroup Isomorphism: The image of psi(H) = (-2H) mod 12 across all H in Z_12
           is exactly the cyclic subgroup 2*Z_12 = {0, 2, 4, 6, 8, 10} ~= Z_6.
        2. Parity Invariance: All elements in Im(psi) are strictly even (no odd palaces:
           brothers(1), children(3), health(5), friends(7), property(9), parents(11) can ever be Shen Gong).
        3. Kernel & Antipodal Symmetry: ker(psi) = {0, 6} (Zi-Wu pair). For all H, psi(H) == psi((H+6) mod 12).
        """
        image: set[int] = set()
        kernel: list[int] = []
        antipodal_verified = True
        odd_palace_violation = False

        for H in range(12):
            k = (-2 * H) % 12
            image.add(k)
            if k == 0:
                kernel.append(H)
            if k % 2 != 0:
                odd_palace_violation = True
            if k != (-2 * ((H + 6) % 12)) % 12:
                antipodal_verified = False

        expected_image = {0, 2, 4, 6, 8, 10}
        subgroup_verified = (
            (image == expected_image)
            and not odd_palace_violation
            and (kernel == [0, 6])
            and antipodal_verified
        )

        return {
            "status": "verified" if subgroup_verified else "failed",
            "image": sorted(list(image)),
            "image_cardinality": len(image),
            "kernel": kernel,
            "antipodal_symmetry_verified": antipodal_verified,
            "odd_palace_exclusion_verified": not odd_palace_violation,
            "subgroup_isomorphism": "2Z_12 ~= Z_6",
        }

    @classmethod
    def temporal_superposition_profile(
        cls,
        macro_stage: str,
        turn_status: int,
        event: str | None = None,
    ) -> dict[str, Any]:
        """Superimpose Macro Project Phase (大限) and Micro Step Iteration (流年/流月).

        Isomorphism with Ziwei Doushu Yunxian DieGong (运限叠宫):
        - Macro Stage 'exploration' (震/坎): Test failure / error is tolerated as learning feedback.
        - Macro Stage 'implementation' (泰/大壮): Test failure triggers adaptive patch repair.
        - Macro Stage 'delivery' (乾/离): Any failure is treated as fatal regression -> immediate rollback.
        """
        stages = {
            "exploration": {"phase_code": 1, "element": "wood", "tolerance": 1.0, "default_action": "discover"},
            "implementation": {"phase_code": 15, "element": "fire", "tolerance": 0.5, "default_action": "continue"},
            "verification": {"phase_code": 31, "element": "metal", "tolerance": 0.2, "default_action": "checkpoint"},
            "delivery": {"phase_code": 63, "element": "metal", "tolerance": 0.0, "default_action": "halt"},
        }
        stage_cfg = stages.get(macro_stage.lower(), stages["implementation"])
        is_error = event in {"test_failure", "verifier_failed", "syntax_error", "timeout", "halt"} or ((turn_status & 0b111111) in {0, 32})

        if not is_error:
            superposition_state = "harmonious_progression"
            policy_action = stage_cfg["default_action"]
            risk_level = "low"
        else:
            if stage_cfg["tolerance"] >= 0.8:
                superposition_state = "exploratory_feedback_tolerated"
                policy_action = "discover"
                risk_level = "tolerated"
            elif stage_cfg["tolerance"] >= 0.4:
                superposition_state = "repairable_defect"
                policy_action = "repair"
                risk_level = "medium"
            else:
                superposition_state = "fatal_regression_in_delivery"
                policy_action = "rollback"
                risk_level = "critical"

        return {
            "macro_stage": macro_stage,
            "macro_tolerance": stage_cfg["tolerance"],
            "micro_status_code": turn_status & 0b111111,
            "event": event,
            "superposition_state": superposition_state,
            "policy_action": policy_action,
            "risk_level": risk_level,
        }
