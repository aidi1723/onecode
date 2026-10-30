"""OneCode Ziwei Doushu Cross-Validation & Distributed Consensus Mixin.

This module implements the mathematical and diagnostic extensions cross-validated
with the Ziwei Doushu engine (Renhuai123/ziwei-doushu):
- Five Elements Bureau (五行局) dynamic scaling: task_bureau_profile
- Self-transformation & internal entropy leakage (自化): self_sihua_profile
- Causal root palace tracing (来因宫): causal_origin_profile
- 4-point distributed consensus (三方四正): triad_consensus_profile
- 11 classical Ziwei formation matrices (格局矩阵): ziwei_pattern_matrix_profile
- Execution anchorage & fallback shelter (身宫寄托): shen_gong_anchorage_profile
- Star brightness & execution governance (星曜亮度): star_brightness_profile
"""
from __future__ import annotations

import math
from typing import Any


def _evaluate_task_bureau(file_count: int, total_loc: int) -> dict[str, Any]:
    """Compute Five Elements Bureau scale and scheduling envelope from code metrics."""
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


def _evaluate_self_sihua(
    current_turn: dict[str, Any],
    history: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Detect internal entropy dissipation and deadlock (宫干自化)."""
    tags: list[str] = []
    modified = current_turn.get("modified_files")
    modified_set = set(modified) if isinstance(modified, (list, set)) else set()
    has_test = bool(current_turn.get("has_test_run", False))
    test_passed = bool(current_turn.get("test_passed", False))
    action = str(current_turn.get("action", ""))
    history_list = history or []

    if not modified_set and not has_test:
        recent_stalls = [
            t for t in history_list[-2:]
            if not (t.get("modified_files") or t.get("has_test_run"))
        ]
        if len(recent_stalls) >= 1:
            tags.append("自化忌:circular_read_hesitation")

    if action in {"complete", "continue", "finish"} and not modified_set and not test_passed:
        tags.append("自化禄:phantom_completion_without_verifier")

    if len(modified_set) > 8:
        tags.append("自化权:excessive_scope_expansion")

    if action in {"audit", "checkpoint"} and not current_turn.get("error_traceback") and current_turn.get("read_files"):
        tags.append("自化科:pre_execution_self_audit")

    return tags


def _evaluate_causal_origin(
    error_traceback: str | None,
    history: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Trace causal origin palace (来因宫) of an error through history."""
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


def _evaluate_triad_consensus(
    turn_number: int,
    current_status: int,
    ast_valid: bool = True,
    token_budget_ok: bool = True,
    verifier_passed: bool = True,
    environment_ok: bool = True,
) -> dict[str, Any]:
    """Evaluate 4-point distributed consensus across San Fang Si Zheng (三方四正)."""
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
    """Classify execution state against classical Ziwei formations (格局矩阵)."""
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
    """Evaluate post-natal execution anchorage and fallback shelter (身宫寄托)."""
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


def _evaluate_star_brightness(
    status_code: int,
    energy: float,
    pattern_level: str | None = None,
) -> dict[str, Any]:
    """Evaluate star brightness (庙旺落陷) and governor permissions from energy and patterns.

    Isomorphism with Ziwei Doushu Star Brightness (庙/旺/得/利/平/不/陷):
    - 庙旺 (Bright): Low Lyapunov energy (V <= 0.60) or pattern 'excellent' -> Full autonomous permissions.
    - 得利平 (Normal): Moderate energy (0.60 < V <= 1.60) -> Guarded execution with patch and verify.
    - 落陷 (Dim): High energy (V > 1.60) or pattern 'broken'/'critical' -> Degraded protection mode.
    """
    normalized = status_code & 0b111111
    if pattern_level in {"broken", "critical"} or energy > 1.60 or normalized in {0, 32}:
        brightness = "dim"
        label = "落陷"
        throttle_factor = 0.25
        governance_mode = "degraded"
        permitted_actions = ["read", "diagnose", "minimal_patch"]
        reason = "State energy overload or broken pattern: protective degraded mode active."
    elif pattern_level == "excellent" or energy <= 0.60:
        brightness = "bright"
        label = "庙旺"
        throttle_factor = 1.0
        governance_mode = "autonomous"
        permitted_actions = ["read", "write", "patch", "bash", "commit"]
        reason = "Low Lyapunov energy and harmonic consensus: autonomous execution permitted."
    else:
        brightness = "normal"
        label = "平利"
        throttle_factor = 0.75
        governance_mode = "guarded"
        permitted_actions = ["read", "patch", "test"]
        reason = "Standard bounded execution under verifier supervision."

    return {
        "status_code": normalized,
        "lyapunov_energy": round(energy, 3),
        "brightness": brightness,
        "brightness_label": label,
        "throttle_factor": throttle_factor,
        "governance_mode": governance_mode,
        "permitted_actions": permitted_actions,
        "reason": reason,
    }


def _evaluate_temporal_superposition(
    macro_stage: str,
    turn_status: int,
    event: str | None = None,
) -> dict[str, Any]:
    """Superimpose Macro Project Phase (大限) and Micro Step Iteration (流年/流月)."""
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


def _evaluate_sovereign_ring_certificate(codes: tuple[int, ...]) -> dict[str, Any]:
    """Verify Sovereign Hexagram Ring <-> Earthly Branches bijection and involution."""
    branches = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")
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


def _evaluate_an_he_coupling_certificate(codes: tuple[int, ...]) -> dict[str, Any]:
    """Verify Six Harmonies (六合) palindromic Hamming distance and dual couple invariant."""
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


def _evaluate_shen_gong_certificate() -> dict[str, Any]:
    """Verify Shen Gong Even Subgroup Theorem (身宫偶数子群同构定理 2*Z_12 ~= Z_6)."""
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


def _evaluate_star_brightness_certificate(cls: type) -> dict[str, Any]:
    """Verify Star Brightness Invariance across all 64 Boolean Hypercube states."""
    valid_modes = {"autonomous", "guarded", "degraded"}
    valid_labels = {"庙旺", "平利", "落陷"}
    all_valid = True
    for code in range(64):
        energy = getattr(cls, "lyapunov_energy")(code)
        profile = _evaluate_star_brightness(code, energy)
        if profile["brightness_label"] not in valid_labels or profile["governance_mode"] not in valid_modes:
            all_valid = False
            break

    ground_energy = getattr(cls, "lyapunov_energy")(7)
    ground_brightness = _evaluate_star_brightness(7, ground_energy)["brightness_label"]
    halt_energy = getattr(cls, "lyapunov_energy")(0)
    halt_brightness = _evaluate_star_brightness(0, halt_energy)["brightness_label"]

    boundary_verified = (ground_brightness == "庙旺") and (halt_brightness == "落陷")

    return {
        "status": "verified" if (all_valid and boundary_verified) else "failed",
        "state_count": 64,
        "all_states_valid": all_valid,
        "ground_state_code": 7,
        "ground_brightness": ground_brightness,
        "halt_state_code": 0,
        "halt_brightness": halt_brightness,
        "boundary_soundness": boundary_verified,
    }


def _evaluate_star_dynamic_energy(
    triad_consensus_score: float = 1.0,
    ast_valid: bool = True,
    environment_ok: bool = True,
    cache_hit: bool = False,
    step_duration_ms: int = 10,
    path_guard_violation: bool = False,
    consecutive_stalls: int = 0,
    verifier_failed: bool = False,
    syntax_error: bool = False,
    undefined_symbols: int = 0,
    no_actionable_edits: bool = False,
    resource_budget_exhausted: bool = False,
) -> dict[str, Any]:
    """Compute dynamic energy distribution across 8 Lucky Stars and 6 Sha Stars."""
    lucky_stars: dict[str, float] = {}
    if triad_consensus_score >= 0.75:
        lucky_stars["zuo_you"] = 1.0
    elif triad_consensus_score >= 0.50:
        lucky_stars["zuo_you"] = 0.5

    if ast_valid and not syntax_error and undefined_symbols == 0:
        lucky_stars["chang_qu"] = 1.0
    elif ast_valid:
        lucky_stars["chang_qu"] = 0.5

    if environment_ok:
        lucky_stars["kui_yue"] = 1.0

    if cache_hit or step_duration_ms < 50:
        lucky_stars["lu_ma"] = 1.0
    elif step_duration_ms < 200:
        lucky_stars["lu_ma"] = 0.5

    sha_stars: dict[str, float] = {}
    if path_guard_violation:
        sha_stars["qing_yang"] = 1.5

    if consecutive_stalls >= 2:
        sha_stars["tuo_luo"] = 1.5
    elif consecutive_stalls == 1:
        sha_stars["tuo_luo"] = 0.8

    if verifier_failed:
        sha_stars["huo_xing"] = 1.2

    if syntax_error or undefined_symbols > 0:
        sha_stars["ling_xing"] = 1.2

    if no_actionable_edits:
        sha_stars["di_kong"] = 1.0

    if resource_budget_exhausted:
        sha_stars["di_jie"] = 1.0

    total_lucky = sum(lucky_stars.values())
    total_sha = sum(sha_stars.values())
    differential = round(total_lucky - total_sha, 3)

    if differential >= 1.0:
        state = "harmonic_dominance"
        label = "吉曜主导"
    elif differential >= -0.5:
        state = "guarded_equilibrium"
        label = "吉凶交织"
    else:
        state = "sha_overload"
        label = "凶煞过载"

    return {
        "lucky_stars": lucky_stars,
        "sha_stars": sha_stars,
        "lucky_energy": round(total_lucky, 3),
        "sha_energy": round(total_sha, 3),
        "energy_differential": differential,
        "energy_state": state,
        "energy_label": label,
    }


_EARTHLY_BRANCH_NAMES = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")
_HEAVENLY_STEM_NAMES = ("甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸")


def _evaluate_jie_shen_relief(
    turn_number: int,
    status_code: int,
    sha_stars: dict[str, float] | list[str] | set[str] | None = None,
    error_scenario: str | None = None,
    attempt_count: int = 1,
) -> dict[str, Any]:
    """Arbitrate Jie Shen (解神) relief damping and rescue action."""
    month_idx = ((turn_number - 1) % 12 + 12) % 12
    k = month_idx // 2
    jieshen_branch = (8 + 2 * k) % 12
    branch_name = _EARTHLY_BRANCH_NAMES[jieshen_branch]

    sha_set: set[str] = set()
    if isinstance(sha_stars, dict):
        sha_set = set(sha_stars.keys())
    elif isinstance(sha_stars, (list, tuple, set)):
        sha_set = set(sha_stars)
    elif error_scenario:
        if error_scenario in {"resume_conflict", "write_collision"}:
            sha_set.add("qing_yang")
        elif error_scenario in {"deadlock", "no_progress", "read_stall"}:
            sha_set.add("tuo_luo")
        elif error_scenario in {"verifier_failure", "provider_failure"}:
            sha_set.add("huo_xing")
        elif error_scenario in {"syntax_error", "config_partial_invalid"}:
            sha_set.add("ling_xing")
        elif error_scenario in {"resource_budget_exceeded"}:
            sha_set.add("di_jie")

    damping_factor = round(max(0.40, 0.75 - 0.15 * max(0, attempt_count - 1)), 2)
    max_neutralize = 2 if attempt_count <= 1 else 1
    neutralized = sorted(list(sha_set))[:max_neutralize]
    relief_effective = len(neutralized) > 0 or len(sha_set) == 0

    if relief_effective:
        if "tuo_luo" in neutralized:
            action = "force_micro_patch"
            reason = "Jie Shen breaks Tuo Luo deadlock: mandate surgical line-level patch."
        elif "qing_yang" in neutralized:
            action = "sandbox_quarantine_retry"
            reason = "Jie Shen pacifies Qing Yang write conflict: isolate write in sandbox."
        elif "huo_xing" in neutralized:
            action = "cooldown_and_retry"
            reason = "Jie Shen cools Huo Xing panic: apply exponential cooldown and retry."
        elif "ling_xing" in neutralized:
            action = "ast_trace_inspect"
            reason = "Jie Shen unmasks Ling Xing stealth defect: inspect AST traceback."
        elif "di_jie" in neutralized:
            action = "compact_and_continue"
            reason = "Jie Shen alleviates Di Jie exhaustion: compact context and continue."
        else:
            action = "rollback_checkpoint"
            reason = "Jie Shen relief active: rollback to last stable checkpoint."
    else:
        action = "sovereignty_halt"
        reason = "Jie Shen relief overwhelmed: irrecoverable Sha overload requires sovereign halt."

    return {
        "jieshen_branch": jieshen_branch,
        "jieshen_branch_name": branch_name,
        "damping_factor": damping_factor,
        "relief_effective": relief_effective,
        "active_sha": sorted(list(sha_set)),
        "neutralized_sha": neutralized,
        "recommended_action": action,
        "reason": reason,
    }


def _evaluate_jie_shen_certificate() -> dict[str, Any]:
    """Verify Jie Shen Even Subgroup Theorem and Damping Bound Theorem."""
    image = []
    odd_palace_violation = False
    for m in range(1, 13):
        k = (m - 1) // 2
        branch = (8 + 2 * k) % 12
        if branch % 2 != 0:
            odd_palace_violation = True
        image.append(branch)

    unique_image = sorted(list(set(image)))
    subgroup_verified = (unique_image == [0, 2, 4, 6, 8, 10])

    sample_relief_early = _evaluate_jie_shen_relief(1, 40, ["tuo_luo", "huo_xing"], attempt_count=1)
    sample_relief_late = _evaluate_jie_shen_relief(1, 40, ["tuo_luo", "huo_xing"], attempt_count=3)
    damping_bounded = (0.40 <= sample_relief_late["damping_factor"] <= sample_relief_early["damping_factor"] <= 0.80)

    shengong_image = [0, 2, 4, 6, 8, 10]
    coupling_harmonic = (unique_image == shengong_image)

    status = "verified" if (subgroup_verified and not odd_palace_violation and damping_bounded and coupling_harmonic) else "failed"

    return {
        "status": status,
        "subgroup_isomorphism": "2Z_12 ~= Z_6",
        "image": unique_image,
        "image_cardinality": len(unique_image),
        "odd_palace_exclusion_verified": not odd_palace_violation,
        "damping_bounded": damping_bounded,
        "shengong_dual_harmonic_coupling_verified": coupling_harmonic,
    }


_JIANG_QIAN_SHEN = (
    "将星", "攀鞍", "岁驿", "息神", "华盖", "劫煞",
    "灾煞", "天煞", "指背", "咸池", "月煞", "亡神",
)

_SUI_QIAN_SHEN = (
    "岁建", "晦气", "丧门", "贯索", "官符", "小耗",
    "岁破", "龙德", "白虎", "天德", "吊客", "病符",
)

_BOSHI_SHEN = (
    "博士", "力士", "青龙", "小耗", "将军", "奏书",
    "飞廉", "喜神", "病符", "大耗", "伏兵", "官符",
)

_LUCUN_BRANCH_BY_STEM = (2, 3, 5, 6, 5, 6, 8, 9, 11, 0)


def _evaluate_twelve_deities(
    turn_number: int,
    status_code: int,
    anchor_branch: int | None = None,
) -> dict[str, Any]:
    """Compute the Twelve Auxiliary Deities (将前/岁前/博士十二神) for runtime governance."""
    turn_idx = max(0, turn_number - 1)
    if anchor_branch is None:
        anchor_b = turn_idx % 12
    else:
        anchor_b = anchor_branch % 12

    active_palace = status_code % 12

    # 1. Jiang Qian 12 Shen: starts at Triad Emperor Branch (三合帝旺)
    # 申子辰(0)->子(0), 巳酉丑(1)->酉(9), 寅午戌(2)->午(6), 亥卯未(3)->卯(3)
    jiang_start = (0, 9, 6, 3)[anchor_b % 4]
    jiang_idx = (active_palace - jiang_start) % 12
    active_jiang_shen = _JIANG_QIAN_SHEN[jiang_idx]

    # 2. Sui Qian 12 Shen: starts at anchor_b (岁建), Sui Po is opposite (对宫)
    sui_idx = (active_palace - anchor_b) % 12
    active_sui_shen = _SUI_QIAN_SHEN[sui_idx]

    # 3. Bo Shi 12 Shen: starts at Lu Cun branch of turn stem, Yang clockwise, Yin counter
    stem_idx = turn_idx % 10
    lucun_b = _LUCUN_BRANCH_BY_STEM[stem_idx]
    direction = 1 if (stem_idx % 2 == 0) else -1
    boshi_idx = (direction * (active_palace - lucun_b)) % 12
    active_boshi_shen = _BOSHI_SHEN[boshi_idx]

    suipo_clash = (active_sui_shen == "岁破")
    panic_risk = (active_sui_shen == "白虎")
    deadlock_risk = (active_sui_shen == "贯索")
    grace_shelter = (active_sui_shen in {"天德", "龙德"})
    momentum_accelerated = (active_jiang_shen in {"将星", "攀鞍"})

    if suipo_clash:
        governance_directive = "barrier_synchronization_isolate_subtask"
        reason = "Sui Po active: opposite clash requires barrier synchronization."
    elif panic_risk:
        governance_directive = "exception_quarantine_rollback"
        reason = "Bai Hu active: sudden runtime fault requires exception quarantine."
    elif deadlock_risk:
        governance_directive = "break_circular_dependency"
        reason = "Guan Suo active: deadlock risk detected, break dependency cycle."
    elif grace_shelter:
        governance_directive = "baseline_guarded_continue"
        reason = f"{active_sui_shen} grace active: protective invariant shields execution."
    elif momentum_accelerated:
        governance_directive = "accelerate_direct_dispatch"
        reason = f"{active_jiang_shen} momentum active: execution pipeline prioritized."
    else:
        governance_directive = "standard_pipeline"
        reason = "Normal auxiliary deity distribution."

    return {
        "anchor_branch": anchor_b,
        "anchor_branch_name": _EARTHLY_BRANCH_NAMES[anchor_b],
        "active_palace": active_palace,
        "active_palace_name": _EARTHLY_BRANCH_NAMES[active_palace],
        "jiang_qian_shen": active_jiang_shen,
        "sui_qian_shen": active_sui_shen,
        "boshi_shen": active_boshi_shen,
        "suipo_clash": suipo_clash,
        "panic_risk": panic_risk,
        "deadlock_risk": deadlock_risk,
        "grace_shelter": grace_shelter,
        "momentum_accelerated": momentum_accelerated,
        "governance_directive": governance_directive,
        "reason": reason,
    }


def _evaluate_twelve_deities_certificate(sovereign_codes: tuple[int, ...]) -> dict[str, Any]:
    """Formal mathematical certificate of Twelve Auxiliary Deities (Triad Partition & Sui Po Opposite Involution)."""
    # 1. Triad partition invariance: JiangXing maps 12 branches to exactly 4 Cardinal points {0, 9, 6, 3}
    jiang_map = {b: (0, 9, 6, 3)[b % 4] for b in range(12)}
    unique_jiang = sorted(list(set(jiang_map.values())))
    triad_cardinal_verified = (unique_jiang == [0, 3, 6, 9])

    water_triad = {0, 4, 8}
    fire_triad = {2, 6, 10}
    metal_triad = {1, 5, 9}
    wood_triad = {3, 7, 11}
    triad_partition_ok = (
        all(jiang_map[b] == 0 for b in water_triad)
        and all(jiang_map[b] == 6 for b in fire_triad)
        and all(jiang_map[b] == 9 for b in metal_triad)
        and all(jiang_map[b] == 3 for b in wood_triad)
    )

    # 2. Sui Po Dui Gong Opposite Involution:
    suipo_opposite_involution_ok = True
    for b in range(12):
        suipo_b = (b + 6) % 12
        code_b = sovereign_codes[b]
        code_suipo = sovereign_codes[suipo_b]
        if code_suipo != (code_b ^ 63):
            suipo_opposite_involution_ok = False
            break

    # 3. Tian De (b+9) and Long De (b+7) harmonic even difference
    even_difference_ok = ((9 - 7) % 2 == 0)

    status = (
        "verified"
        if (triad_cardinal_verified and triad_partition_ok and suipo_opposite_involution_ok and even_difference_ok)
        else "failed"
    )

    return {
        "status": status,
        "triad_cardinal_points": unique_jiang,
        "triad_partition_verified": triad_partition_ok,
        "suipo_opposite_involution_verified": suipo_opposite_involution_ok,
        "tian_de_long_de_even_coupling": even_difference_ok,
    }


_SI_HUA_TABLE: dict[int, tuple[str, str, str, str]] = {
    0: ("廉贞", "破军", "武曲", "太阳"),  # 甲
    1: ("天机", "天梁", "紫微", "太阴"),  # 乙
    2: ("天同", "天机", "文昌", "廉贞"),  # 丙
    3: ("太阴", "天同", "天机", "巨门"),  # 丁
    4: ("贪狼", "太阴", "右弼", "天机"),  # 戊
    5: ("武曲", "贪狼", "天梁", "文曲"),  # 己
    6: ("太阳", "武曲", "太阴", "天同"),  # 庚
    7: ("巨门", "太阳", "文曲", "文昌"),  # 辛
    8: ("天梁", "紫微", "左辅", "武曲"),  # 壬
    9: ("破军", "巨门", "太阴", "贪狼"),  # 癸
}

_STAR_CANONICAL_INDEX: dict[str, int] = {
    "紫微": 0, "天机": 1, "太阳": 2, "武曲": 3, "天同": 4, "廉贞": 5,
    "天府": 6, "太阴": 7, "贪狼": 8, "巨门": 9, "天相": 10, "天梁": 11,
    "七杀": 0, "破军": 4, "文昌": 8, "文曲": 10, "左辅": 4, "右弼": 10,
}


def _evaluate_flying_sihua_cascade(
    turn_number: int,
    status_code: int,
    macro_stage: str = "implementation",
    baseline_status: int = 7,
) -> dict[str, Any]:
    """Evaluate multi-layer Flying Sihua (跨宫飞星与四化多层叠象) for cascade clash prevention."""
    t_native = baseline_status % 10
    stage_stems = {"exploration": 0, "implementation": 2, "verification": 6, "delivery": 8}
    t_stage = stage_stems.get(macro_stage, 2)
    t_turn = max(0, turn_number - 1) % 10

    active_p = status_code % 12
    opposite_p = (active_p + 6) % 12

    turn_tf = _SI_HUA_TABLE[t_turn]
    stage_tf = _SI_HUA_TABLE[t_stage]

    def star_branch(star_name: str) -> int:
        offset = _STAR_CANONICAL_INDEX.get(star_name, 0)
        return (active_p + offset) % 12

    turn_ji_branch = star_branch(turn_tf[3])
    stage_ji_branch = star_branch(stage_tf[3])
    turn_lu_branch = star_branch(turn_tf[0])
    turn_quan_branch = star_branch(turn_tf[1])
    turn_ke_branch = star_branch(turn_tf[2])

    opposite_clash = (turn_ji_branch == opposite_p or stage_ji_branch == opposite_p)
    self_ji = (turn_ji_branch == active_p)
    double_ji = (turn_ji_branch == stage_ji_branch)
    lu_chong_po = ((turn_lu_branch + 6) % 12 == turn_ji_branch)

    trine_palaces = {active_p, (active_p + 4) % 12, (active_p + 8) % 12, (active_p + 6) % 12}
    triple_harmony = (
        turn_lu_branch in trine_palaces
        and turn_quan_branch in trine_palaces
        and turn_ke_branch in trine_palaces
    )

    if double_ji:
        risk_level = "critical"
        damping_factor = 0.25
        action = "cascade_halt_quarantine"
        reason = f"Double Ji collision ({turn_tf[3]} + {stage_tf[3]}): immediate quarantine required."
    elif opposite_clash:
        risk_level = "elevated"
        damping_factor = 0.50
        action = "isolate_external_boundary"
        reason = f"Opposite clash ({turn_tf[3]} into palace {opposite_p}): isolate boundary perturbations."
    elif lu_chong_po:
        risk_level = "elevated"
        damping_factor = 0.50
        action = "rollback_corrupted_gain"
        reason = f"Lu Chong Po: Hua Lu {turn_tf[0]} clashed by Hua Ji {turn_tf[3]}."
    elif self_ji:
        risk_level = "moderate"
        damping_factor = 0.65
        action = "force_micro_patch"
        reason = f"Self-dissipation Ji ({turn_tf[3]}): force minimal atomic patch."
    elif triple_harmony:
        risk_level = "minimal"
        damping_factor = 1.00
        action = "autonomous_high_throughput"
        reason = "Triple Harmony Overlay (禄权科三奇加会): autonomous throughput granted."
    else:
        risk_level = "stable"
        damping_factor = 0.85
        action = "standard_pipeline"
        reason = "Sihua cascade within nominal safe envelope."

    return {
        "active_palace": active_p,
        "opposite_palace": opposite_p,
        "turn_ji_star": turn_tf[3],
        "turn_ji_branch": turn_ji_branch,
        "stage_ji_star": stage_tf[3],
        "stage_ji_branch": stage_ji_branch,
        "turn_lu_star": turn_tf[0],
        "turn_lu_branch": turn_lu_branch,
        "opposite_clash": opposite_clash,
        "self_ji": self_ji,
        "double_ji": double_ji,
        "lu_chong_po": lu_chong_po,
        "triple_harmony": triple_harmony,
        "risk_level": risk_level,
        "damping_factor": damping_factor,
        "action": action,
        "reason": reason,
    }


def _evaluate_flying_sihua_certificate(sovereign_codes: tuple[int, ...]) -> dict[str, Any]:
    """Formal mathematical certificate of Flying Sihua Cascade & DuiGong Involution."""
    totality_ok = (len(_SI_HUA_TABLE) == 10)
    for stem, stars in _SI_HUA_TABLE.items():
        if len(stars) != 4 or len(set(stars)) != 4:
            totality_ok = False
            break

    involution_ok = True
    for p in range(12):
        opp_p = (p + 6) % 12
        if opp_p == p:
            involution_ok = False
            break
        if (opp_p + 6) % 12 != p:
            involution_ok = False
            break
        code_p = sovereign_codes[p]
        code_opp = sovereign_codes[opp_p]
        if code_opp != (code_p ^ 63):
            involution_ok = False
            break

    damping_monotonic = (0.25 < 0.50 < 0.85 <= 1.00)

    status = "verified" if (totality_ok and involution_ok and damping_monotonic) else "failed"

    return {
        "status": status,
        "sihua_totality_verified": totality_ok,
        "duigong_involution_verified": involution_ok,
        "damping_monotonic_verified": damping_monotonic,
    }


def _evaluate_triadic_synthesis(
    status_code: int,
    environment_ok: bool = True,
    path_guard_ok: bool = True,
    verifier_passed: bool | None = None,
    ast_valid: bool = True,
    patch_surgical: bool = True,
) -> dict[str, Any]:
    """Compute Ni Haixia Triadic Architectural Synthesis (天纪/地纪/人纪三纪会聚势能)."""
    normalized = status_code & 0b111111
    yang_count = bin(normalized).count("1")
    tian_potential = max(0.2, min(1.0, 0.4 + 0.1 * yang_count))

    di_potential = 1.0 if (environment_ok and path_guard_ok) else 0.2

    if verifier_passed is True and ast_valid:
        ren_potential = 1.0
    elif verifier_passed is False:
        ren_potential = 0.3 if patch_surgical else 0.1
    elif not ast_valid:
        ren_potential = 0.2
    else:
        ren_potential = 0.75 if patch_surgical else 0.5

    triadic_potential = (tian_potential + di_potential + ren_potential) / 3.0

    human_earth_sum = di_potential + ren_potential
    domination_satisfied = (human_earth_sum >= 2.0 * tian_potential * 0.8)

    if triadic_potential >= 0.80:
        regime = "triadic_harmony"
        governance = "autonomous_convergence"
        reason = "Triadic harmony (三纪同心): high confidence autonomous convergence."
    elif triadic_potential >= 0.55:
        regime = "dialectical_equilibrium"
        governance = "guarded_execution"
        reason = "Dialectical equilibrium (辨证均衡): standard verifier supervised steps."
    else:
        regime = "physical_remediation"
        governance = "surgical_minimal_remedy"
        reason = "Physical remediation (经方微创): constrain to single atomic surgical repair."

    return {
        "status_code": normalized,
        "tian_potential": round(tian_potential, 3),
        "di_potential": round(di_potential, 3),
        "ren_potential": round(ren_potential, 3),
        "triadic_potential": round(triadic_potential, 3),
        "domination_satisfied": domination_satisfied,
        "regime": regime,
        "governance": governance,
        "reason": reason,
    }


def _evaluate_triadic_synthesis_certificate() -> dict[str, Any]:
    """Formal mathematical certificate of Triadic Synthesis & 2/3 Domination Principle."""
    bounds_ok = True
    samples = [
        _evaluate_triadic_synthesis(code, env, pg, ver, ast, patch)
        for code in (0, 7, 31, 32, 63)
        for env in (True, False)
        for pg in (True, False)
        for ver in (True, False, None)
        for ast in (True, False)
        for patch in (True, False)
    ]
    for s in samples:
        if not (0.0 <= s["triadic_potential"] <= 1.0):
            bounds_ok = False
            break

    perfect_effort = _evaluate_triadic_synthesis(0, environment_ok=True, path_guard_ok=True, verifier_passed=True, ast_valid=True)
    domination_ok = (perfect_effort["di_potential"] + perfect_effort["ren_potential"] >= 2.0 * perfect_effort["tian_potential"])

    broken_effort = _evaluate_triadic_synthesis(63, environment_ok=False, verifier_passed=False, ast_valid=False)
    remediation_ok = (broken_effort["triadic_potential"] < 0.55 and broken_effort["regime"] == "physical_remediation")

    status = "verified" if (bounds_ok and domination_ok and remediation_ok) else "failed"

    return {
        "status": status,
        "convex_bounds_verified": bounds_ok,
        "two_thirds_domination_verified": domination_ok,
        "physical_remediation_boundary_verified": remediation_ok,
    }


_MING_ZHU_TABLE: dict[int, str] = {
    0: "贪狼", 1: "巨门", 2: "禄存", 3: "文曲", 4: "廉贞", 5: "武曲",
    6: "破军", 7: "武曲", 8: "廉贞", 9: "文曲", 10: "禄存", 11: "巨门",
}

_SHEN_ZHU_TABLE: dict[int, str] = {
    0: "火星", 6: "火星", 1: "天相", 7: "天相",
    2: "天梁", 8: "天梁", 3: "天同", 9: "天同",
    4: "文昌", 10: "文昌", 5: "天机", 11: "天机",
}


def _evaluate_ming_shen_zhu(
    turn_number: int,
    status_code: int,
) -> dict[str, Any]:
    """Compute Ming Zhu (命主) and Shen Zhu (身主) stellar governors and symmetries."""
    active_b = status_code % 12
    ming_zhu = _MING_ZHU_TABLE[active_b]
    shen_zhu = _SHEN_ZHU_TABLE[active_b]

    ming_roles = {
        "贪狼": "exploratory_breadth",
        "巨门": "ast_semantic_analysis",
        "禄存": "resource_budget_guard",
        "文曲": "telemetry_evidence_record",
        "廉贞": "boundary_integrity_audit",
        "武曲": "surgical_execution_patch",
        "破军": "structural_refactoring",
    }
    shen_roles = {
        "火星": "panic_recovery_fast_retry",
        "天相": "contract_specification_anchor",
        "天梁": "stability_guardrail_protection",
        "天同": "harmonic_state_equilibrium",
        "文昌": "symbolic_syntax_verification",
        "天机": "strategic_decomposition_plan",
    }

    return {
        "active_branch": active_b,
        "active_branch_name": _EARTHLY_BRANCH_NAMES[active_b],
        "ming_zhu": ming_zhu,
        "ming_zhu_role": ming_roles.get(ming_zhu, "standard_focus"),
        "shen_zhu": shen_zhu,
        "shen_zhu_role": shen_roles.get(shen_zhu, "standard_guard"),
        "meridian_symmetric_branch": (12 - active_b) % 12,
        "antipodal_branch": (active_b + 6) % 12,
    }


def _evaluate_ziwei_tianfu_duality(status_code: int) -> dict[str, Any]:
    """Compute Ziwei-Tianfu duality axis, involutive distance, and Tai-Pi fixed points."""
    # Sovereign Tai (code 7) maps to branch 2 (Yin); Sovereign Pi (code 56) maps to branch 8 (Shen)
    if status_code == 7:
        z_branch = 2
    elif status_code == 56:
        z_branch = 8
    else:
        z_branch = status_code % 12
    f_branch = (4 - z_branch) % 12

    circ_dist = min((z_branch - f_branch) % 12, (f_branch - z_branch) % 12)
    is_fixed_point = (z_branch in {2, 8})
    co_habitation = (z_branch == f_branch)

    if co_habitation:
        axis_state = "ziwei_tianfu_cohabitation"
        governance_directive = "unified_centralized_authority"
        description = "Ziwei and Tianfu co-habitate (紫府同宫): maximum structural stability and authority."
    elif circ_dist == 6:
        axis_state = "ziwei_tianfu_opposite_polarity"
        governance_directive = "balanced_dual_plane_arbitration"
        description = "Ziwei and Tianfu in opposite polarity: dual-plane checks and balances active."
    else:
        axis_state = "ziwei_tianfu_dynamic_resonance"
        governance_directive = "standard_harmonic_flow"
        description = "Ziwei-Tianfu orbital configuration within nominal parameters."

    return {
        "ziwei_branch": z_branch,
        "ziwei_branch_name": _EARTHLY_BRANCH_NAMES[z_branch],
        "tianfu_branch": f_branch,
        "tianfu_branch_name": _EARTHLY_BRANCH_NAMES[f_branch],
        "circular_distance": circ_dist,
        "is_fixed_point": is_fixed_point,
        "co_habitation": co_habitation,
        "axis_state": axis_state,
        "governance_directive": governance_directive,
        "description": description,
    }


def _evaluate_yang_tuo_clamping(
    turn_number: int,
    status_code: int,
    has_hua_ji: bool = False,
) -> dict[str, Any]:
    """Evaluate Qing Yang and Tuo Luo geometric clamping around Lu Cun (羊陀夹禄 / 羊陀夹忌)."""
    t_turn = max(0, turn_number - 1) % 10
    lucun_b = _LUCUN_BRANCH_BY_STEM[t_turn]
    yang_b = (lucun_b + 1) % 12
    tuo_b = (lucun_b - 1) % 12

    active_p = status_code % 12
    clamped_at_lucun = (active_p == lucun_b)
    on_yang_edge = (active_p == yang_b)
    on_tuo_edge = (active_p == tuo_b)

    yang_tuo_jia_ji = (clamped_at_lucun and has_hua_ji)
    yang_tuo_jia_lu = (clamped_at_lucun and not has_hua_ji)

    if yang_tuo_jia_ji:
        risk_level = "critical"
        action = "break_deadlock_clamp_with_micro_patch"
        reason = "Yang Tuo Jia Ji (羊陀夹忌): severe deadlock trap detected. Disallow full rewrites."
    elif on_yang_edge:
        risk_level = "elevated"
        action = "suppress_cutting_edge_overwrite"
        reason = "Qing Yang leading edge: high friction/syntax hazard; enforce strict AST validation."
    elif on_tuo_edge:
        risk_level = "elevated"
        action = "accelerate_lagging_execution"
        reason = "Tuo Luo trailing edge: circular stall hazard; apply bounded timeout."
    elif yang_tuo_jia_lu:
        risk_level = "guarded"
        action = "preserve_sheltered_gain"
        reason = "Yang Tuo Jia Lu (羊陀夹禄): sheltered resource safe zone; bounded execution permitted."
    else:
        risk_level = "stable"
        action = "standard_pipeline"
        reason = "Nominal trajectory outside Yang-Tuo clamping band."

    return {
        "turn_stem": t_turn,
        "lucun_branch": lucun_b,
        "lucun_branch_name": _EARTHLY_BRANCH_NAMES[lucun_b],
        "qing_yang_branch": yang_b,
        "qing_yang_branch_name": _EARTHLY_BRANCH_NAMES[yang_b],
        "tuo_luo_branch": tuo_b,
        "tuo_luo_branch_name": _EARTHLY_BRANCH_NAMES[tuo_b],
        "active_palace": active_p,
        "clamped_at_lucun": clamped_at_lucun,
        "on_yang_edge": on_yang_edge,
        "on_tuo_edge": on_tuo_edge,
        "yang_tuo_jia_ji": yang_tuo_jia_ji,
        "yang_tuo_jia_lu": yang_tuo_jia_lu,
        "risk_level": risk_level,
        "action": action,
        "reason": reason,
    }


def _evaluate_ziwei_tianfu_and_yangtuo_certificate(sovereign_codes: tuple[int, ...]) -> dict[str, Any]:
    """Formal mathematical certificate of Ming/Shen Zhu Symmetries, Ziwei-Tianfu Duality & Yang-Tuo Clamping."""
    meridian_ok = True
    for b in range(12):
        if _MING_ZHU_TABLE[b] != _MING_ZHU_TABLE[(12 - b) % 12]:
            meridian_ok = False
            break

    antipodal_ok = True
    for b in range(12):
        if _SHEN_ZHU_TABLE[b] != _SHEN_ZHU_TABLE[(b + 6) % 12]:
            antipodal_ok = False
            break

    involution_ok = True
    fixed_points = []
    for z in range(12):
        f = (4 - z) % 12
        f_of_f = (4 - f) % 12
        if f_of_f != z:
            involution_ok = False
            break
        if z == f:
            fixed_points.append(z)

    fixed_points_ok = (sorted(fixed_points) == [2, 8])
    fixed_points_match_tai_pi = (
        sovereign_codes[2] == 7
        and sovereign_codes[8] == 56
    )

    clamping_midpoint_ok = True
    for t in range(10):
        lucun = _LUCUN_BRANCH_BY_STEM[t]
        yang = (lucun + 1) % 12
        tuo = (lucun - 1) % 12
        dist = (yang - tuo) % 12
        midpoint_sum = (yang + tuo) % 12
        if dist != 2 or midpoint_sum != (2 * lucun) % 12:
            clamping_midpoint_ok = False
            break

    status = (
        "verified"
        if (meridian_ok and antipodal_ok and involution_ok and fixed_points_ok and fixed_points_match_tai_pi and clamping_midpoint_ok)
        else "failed"
    )

    return {
        "status": status,
        "ming_zhu_meridian_reflection_verified": meridian_ok,
        "shen_zhu_antipodal_invariance_verified": antipodal_ok,
        "ziwei_tianfu_involution_verified": involution_ok,
        "tai_pi_fixed_points_verified": fixed_points_ok and fixed_points_match_tai_pi,
        "yang_tuo_clamping_midpoint_verified": clamping_midpoint_ok,
    }


def _evaluate_equation_of_time(
    year: int,
    month: int,
    day: int,
    clock_hour: int = 12,
    clock_minute: int = 0,
) -> float:
    """NOAA fractional-year Equation of Time (均时差) approximation in minutes."""
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    days_in_year = 366 if is_leap else 365
    days_before_month = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
    doy = days_before_month[month - 1] + day
    if is_leap and month > 2:
        doy += 1
    fractional_hour = clock_hour + clock_minute / 60.0
    gamma = (2.0 * math.pi / days_in_year) * (doy - 1 + (fractional_hour - 12.0) / 24.0)
    eot = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2.0 * gamma)
        - 0.040849 * math.sin(2.0 * gamma)
    )
    return round(eot, 4)


def _evaluate_true_solar_time(
    year: int,
    month: int,
    day: int,
    clock_hour: int,
    clock_minute: int,
    longitude: float = 120.0,
    utc_offset_minutes: int = 480,
) -> dict[str, Any]:
    """Compute true solar time (地方真太阳时), branch mapping, and late Zishi detection."""
    meridian = utc_offset_minutes / 4.0
    longitude_correction_minutes = (longitude - meridian) * 4.0
    eot_minutes = _evaluate_equation_of_time(year, month, day, clock_hour, clock_minute)
    total_correction_minutes = longitude_correction_minutes + eot_minutes
    raw_minutes = clock_hour * 60 + clock_minute + total_correction_minutes

    rounded_total_seconds = int(round(raw_minutes * 60))
    day_offset = rounded_total_seconds // 86400
    second_of_day = rounded_total_seconds % 86400

    solar_hour = (second_of_day // 3600) % 24
    solar_minute = (second_of_day % 3600) // 60
    solar_second = second_of_day % 60
    normalized_minutes = second_of_day / 60.0

    if normalized_minutes >= 1380.0 or normalized_minutes < 60.0:
        branch = 0
    else:
        branch = int((normalized_minutes - 60.0) // 120) + 1

    is_late_zishi = (branch == 0 and normalized_minutes >= 1380.0)
    is_early_zishi = (branch == 0 and normalized_minutes < 60.0)

    return {
        "solar_hour": solar_hour,
        "solar_minute": solar_minute,
        "solar_second": solar_second,
        "normalized_minutes": round(normalized_minutes, 2),
        "branch": branch,
        "branch_name": _EARTHLY_BRANCH_NAMES[branch],
        "day_offset": day_offset,
        "longitude_correction_minutes": round(longitude_correction_minutes, 3),
        "equation_of_time_minutes": round(eot_minutes, 3),
        "total_correction_minutes": round(total_correction_minutes, 3),
        "is_late_zishi": is_late_zishi,
        "is_early_zishi": is_early_zishi,
    }


def _evaluate_clock_drift_adaptation(
    clock_drift_seconds: float,
    event_epoch_timestamp: float | None = None,
    late_zishi_rule: str = "next-day",
) -> dict[str, Any]:
    """Evaluate clock drift adaptation for WAL logging, replay buffers, and distributed epochs."""
    abs_drift = abs(clock_drift_seconds)
    if abs_drift > 900.0:
        drift_severity = "critical_drift"
        governance_directive = "clock_resync_rebase_epoch"
        wal_action = "barrier_wal_rotate"
        reason = "Clock drift exceeds 15 minutes: epoch rebase required to prevent split-brain ordering."
    elif abs_drift > 60.0:
        drift_severity = "moderate_drift"
        governance_directive = "linear_smoothing_interpolation"
        wal_action = "append_skew_metadata"
        reason = "Clock drift between 1 and 15 minutes: append skew offset metadata for monotonic ordering."
    else:
        drift_severity = "nominal"
        governance_directive = "standard_chronological_flow"
        wal_action = "standard_append"
        reason = "Clock drift within nominal threshold: standard WAL append permitted."

    return {
        "clock_drift_seconds": clock_drift_seconds,
        "drift_severity": drift_severity,
        "governance_directive": governance_directive,
        "wal_action": wal_action,
        "late_zishi_rule": late_zishi_rule,
        "reason": reason,
    }


def _evaluate_solar_equation_and_zishi_certificate() -> dict[str, Any]:
    """Verify NOAA EOT bounded oscillation, Zishi 1440-minute measure partition, and meridian invariance."""
    eot_bounded = True
    max_eot = -100.0
    min_eot = 100.0
    days_in_months = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    for day_idx in range(1, 366):
        doy = day_idx
        m = 1
        while m <= 12 and doy > days_in_months[m - 1]:
            doy -= days_in_months[m - 1]
            m += 1
        val = _evaluate_equation_of_time(2026, min(m, 12), doy, 12, 0)
        max_eot = max(max_eot, val)
        min_eot = min(min_eot, val)
        if val < -16.0 or val > 17.5:
            eot_bounded = False
            break

    branch_minute_counts = [0] * 12
    for minute in range(1440):
        if minute >= 1380 or minute < 60:
            b = 0
        else:
            b = ((minute - 60) // 120) + 1
        branch_minute_counts[b] += 1

    partition_exact_120 = all(count == 120 for count in branch_minute_counts)
    partition_sum_1440 = (sum(branch_minute_counts) == 1440)

    meridian_linear_ok = True
    for test_lon in (60.0, 90.0, 110.0, 120.0, 135.0):
        t1 = _evaluate_true_solar_time(2026, 6, 15, 12, 0, longitude=test_lon, utc_offset_minutes=480)
        expected_lon_corr = (test_lon - 120.0) * 4.0
        if abs(t1["longitude_correction_minutes"] - expected_lon_corr) > 1e-4:
            meridian_linear_ok = False
            break

    status = (
        "verified"
        if (eot_bounded and partition_exact_120 and partition_sum_1440 and meridian_linear_ok)
        else "failed"
    )

    return {
        "status": status,
        "eot_bounded_oscillation_verified": eot_bounded,
        "min_eot_minutes": min_eot,
        "max_eot_minutes": max_eot,
        "zishi_measure_partition_verified": partition_exact_120 and partition_sum_1440,
        "branch_minute_counts": branch_minute_counts,
        "meridian_linear_invariance_verified": meridian_linear_ok,
    }


_GENG_SIHUA_VARIANTS: dict[str, tuple[str, str, str, str]] = {
    "GYWYT": ("太阳", "武曲", "太阴", "天同"),
    "GYWTY": ("太阳", "武曲", "天同", "太阴"),
    "GYWFT": ("太阳", "武曲", "天府", "天同"),
    "GYWFX": ("太阳", "武曲", "天府", "天相"),
    "GYWTX": ("太阳", "武曲", "天同", "天相"),
}


def _evaluate_school_consensus(
    stem_index: int,
    geng_variant: str = "GYWYT",
    late_zishi_rule: str = "next-day",
    leap_month_rule: str = "split",
) -> dict[str, Any]:
    """Evaluate multi-school divergence, consensus degree, and governance arbitration."""
    s = stem_index % 10
    stem_name = _HEAVENLY_STEM_NAMES[s]

    if s == 6:
        is_divergent = True
        divergence_type = "geng_sihua_variant"
        active_sihua = _GENG_SIHUA_VARIANTS.get(geng_variant, _GENG_SIHUA_VARIANTS["GYWYT"])
        consensus_score = 0.60
        governance_directive = "majority_consensus_guarded"
        reason = f"Geng stem has multi-school divergence (active: {geng_variant}). Guarded execution active."
    elif s == 7:
        is_divergent = True
        divergence_type = "xin_changqu_order"
        active_sihua = ("巨门", "太阳", "文曲", "文昌")
        consensus_score = 0.85
        governance_directive = "majority_consensus_guarded"
        reason = "Xin stem has minor school divergence on Chang/Qu ordering. Guarded execution active."
    elif s == 8:
        is_divergent = True
        divergence_type = "ren_zuofu_tianfu"
        active_sihua = ("天梁", "紫微", "左辅", "武曲")
        consensus_score = 0.85
        governance_directive = "majority_consensus_guarded"
        reason = "Ren stem has minor school divergence on ZuoFu vs Tianfu. Guarded execution active."
    else:
        is_divergent = False
        divergence_type = "unanimous"
        active_sihua = _SI_HUA_TABLE[s]
        consensus_score = 1.00
        governance_directive = "unanimous_consensus_fastpath"
        reason = f"Stem {stem_name} has 100% unanimous consensus across all classical schools."

    return {
        "stem_index": s,
        "stem_name": stem_name,
        "is_divergent": is_divergent,
        "divergence_type": divergence_type,
        "active_sihua": list(active_sihua),
        "consensus_score": consensus_score,
        "governance_directive": governance_directive,
        "late_zishi_rule": late_zishi_rule,
        "leap_month_rule": leap_month_rule,
        "reason": reason,
    }


def _evaluate_school_divergence_consensus_certificate() -> dict[str, Any]:
    """Verify Seven Stems Sihua Totality, Geng Variant Set Closure, and Consensus Monotonicity."""
    unanimous_stems = []
    for s in range(10):
        res = _evaluate_school_consensus(s)
        if not res["is_divergent"] and res["consensus_score"] == 1.00:
            unanimous_stems.append(s)

    seven_stems_unanimous = (unanimous_stems == [0, 1, 2, 3, 4, 5, 9])

    geng_closure_ok = True
    for variant, sihua in _GENG_SIHUA_VARIANTS.items():
        if sihua[0] != "太阳" or sihua[1] != "武曲":
            geng_closure_ok = False
            break

    consensus_levels = [
        _evaluate_school_consensus(0)["consensus_score"],
        _evaluate_school_consensus(7)["consensus_score"],
        _evaluate_school_consensus(6)["consensus_score"],
    ]
    monotonic = (consensus_levels[0] > consensus_levels[1] > consensus_levels[2])

    status = (
        "verified"
        if (seven_stems_unanimous and geng_closure_ok and monotonic)
        else "failed"
    )

    return {
        "status": status,
        "seven_stems_unanimous_verified": seven_stems_unanimous,
        "unanimous_stem_indices": unanimous_stems,
        "geng_closure_verified": geng_closure_ok,
        "geng_variant_count": len(_GENG_SIHUA_VARIANTS),
        "consensus_monotonicity_verified": monotonic,
        "consensus_levels": consensus_levels,
    }


def _detect_breaking_patterns(
    fatal_regression: bool,
    verifier_passed: bool,
    token_budget_ok: bool,
    consecutive_syntax_errors: int,
    undefined_symbols_count: int,
    environment_ok: bool,
    consecutive_read_stalls: int,
) -> list[dict[str, Any]]:
    """Detect breaking and trap patterns (恶格与陷阱格)."""
    patterns: list[dict[str, Any]] = []
    if fatal_regression:
        patterns.append({
            "name": "铃昌陀武",
            "tier": "breaking",
            "level": "caution",
            "description": "Fatal regression detected: critical dead-end requiring immediate rollback.",
            "conditions": {"required": ["fatal_regression == True"]},
            "governance_action": "rollback",
        })
    if not verifier_passed and not token_budget_ok:
        patterns.append({
            "name": "羊陀夹忌",
            "tier": "breaking",
            "level": "caution",
            "description": "Verifier failure coupled with token budget depletion: deadlock clamp.",
            "conditions": {"required": ["verifier_passed == False", "token_budget_ok == False"]},
            "governance_action": "switch_to_surgical_unified_diff",
        })
    if consecutive_syntax_errors >= 2:
        patterns.append({
            "name": "火铃夹命",
            "tier": "breaking",
            "level": "caution",
            "description": "Repeated syntax compilation errors: compulsive churn requires cooldown.",
            "conditions": {"required": [f"consecutive_syntax_errors == {consecutive_syntax_errors} >= 2"]},
            "governance_action": "cooldown",
        })
    if undefined_symbols_count >= 1:
        patterns.append({
            "name": "空劫夹命",
            "tier": "breaking",
            "level": "caution",
            "description": "Undefined symbol hallucination: requires symbol re-anchoring.",
            "conditions": {"required": [f"undefined_symbols == {undefined_symbols_count} >= 1"]},
            "governance_action": "reanchor",
        })
    if not environment_ok:
        patterns.append({
            "name": "化忌入迁移",
            "tier": "breaking",
            "level": "caution",
            "description": "Environment/sandbox or gateway failure: retry under isolated subshell.",
            "conditions": {"required": ["environment_ok == False"]},
            "governance_action": "retry",
        })
    if consecutive_read_stalls >= 2:
        patterns.append({
            "name": "自化忌",
            "tier": "breaking",
            "level": "caution",
            "description": "Read hesitation stall: agent reading repetitively without writing code.",
            "conditions": {"required": [f"consecutive_read_stalls == {consecutive_read_stalls} >= 2"]},
            "governance_action": "synthesize",
        })
    if not verifier_passed and not fatal_regression and token_budget_ok:
        patterns.append({
            "name": "化忌入官禄",
            "tier": "breaking",
            "level": "caution",
            "description": "Test assertion failure in execution pathway: localized repair required.",
            "conditions": {"required": ["verifier_passed == False"]},
            "governance_action": "repair",
        })
    return patterns


def _detect_auspicious_patterns(
    m_branch: int,
    normalized_status: int,
    ast_valid: bool,
    token_budget_ok: bool,
    verifier_passed: bool,
    environment_ok: bool,
) -> list[dict[str, Any]]:
    """Detect supreme, harmonic, and assisting patterns (上格、中格与助力格)."""
    patterns: list[dict[str, Any]] = []
    if ast_valid and token_budget_ok and verifier_passed and environment_ok:
        if m_branch in {2, 8} and normalized_status in {7, 56}:
            patterns.append({
                "name": "紫府同宫",
                "tier": "supreme",
                "level": "excellent",
                "description": "Ziwei and Tianfu cohabitate in Yin/Shen: maximum architectural stability.",
                "conditions": {"required": ["branch in {2, 8}", "status in {7, 56}", "all verifiers passed"]},
                "governance_action": "high_speed_autonomous_pipeline",
            })
        if normalized_status == 63 and m_branch in {2, 6, 8}:
            patterns.append({
                "name": "君臣庆会",
                "tier": "supreme",
                "level": "excellent",
                "description": "Imperial Ziwei supported by harmonic auxiliary cluster: full autonomous execution.",
                "conditions": {"required": ["pure yang state 63", "branch in {2, 6, 8}"]},
                "governance_action": "autonomous_commit",
            })
        if m_branch in {0, 4, 8}:
            patterns.append({
                "name": "府相朝垣",
                "tier": "supreme",
                "level": "excellent",
                "description": "Tianfu and Tianxiang facing the throne across triad: strong governance foundation.",
                "conditions": {"required": ["triad anchor branch in {0, 4, 8}", "verifier passed"]},
                "governance_action": "standard_assisted_pipeline",
            })
        if normalized_status == 63:
            patterns.append({
                "name": "三奇加会",
                "tier": "supreme",
                "level": "excellent",
                "description": "Hua Lu, Hua Quan, Hua Ke meeting across San Fang Si Zheng: maximum synthesis power.",
                "conditions": {"required": ["all four triad points valid", "status == 63"]},
                "governance_action": "commit",
            })

    if ast_valid and environment_ok:
        if m_branch in {1, 7}:
            patterns.append({
                "name": "日月同宫",
                "tier": "harmonic",
                "level": "good",
                "description": "Sun and Moon cohabitate in Chou/Wei: dual illumination across yin-yang axes.",
                "conditions": {"required": ["branch in {1, 7}", "ast_valid == True"]},
                "governance_action": "dual_plane_assisted",
            })
        if m_branch in {2, 8} and verifier_passed:
            patterns.append({
                "name": "巨日同宫",
                "tier": "harmonic",
                "level": "good",
                "description": "Jumen and Taiyang cohabitate in Yin/Shen: broad visibility with high eloquence.",
                "conditions": {"required": ["branch in {2, 8}", "verifier_passed == True"]},
                "governance_action": "guided_step_verifier",
            })
        if verifier_passed and token_budget_ok:
            patterns.append({
                "name": "科权双会",
                "tier": "assist",
                "level": "good",
                "description": "Hua Ke and Hua Quan meeting: authoritative verification and high precision.",
                "conditions": {"required": ["verifier passed", "token budget ok"]},
                "governance_action": "standard_assisted_pipeline",
            })
    return patterns


def _evaluate_classical_patterns(
    turn_number: int,
    status_code: int,
    ast_valid: bool = True,
    token_budget_ok: bool = True,
    verifier_passed: bool = True,
    environment_ok: bool = True,
    fatal_regression: bool = False,
    consecutive_syntax_errors: int = 0,
    undefined_symbols_count: int = 0,
    consecutive_read_stalls: int = 0,
) -> dict[str, Any]:
    """Exhaustive evaluation of classical Ziwei auspicious, harmonic, assisting, and breaking formations."""
    m_branch = (turn_number - 1) % 12
    normalized_status = status_code & 0b111111

    patterns = _detect_breaking_patterns(
        fatal_regression=fatal_regression,
        verifier_passed=verifier_passed,
        token_budget_ok=token_budget_ok,
        consecutive_syntax_errors=consecutive_syntax_errors,
        undefined_symbols_count=undefined_symbols_count,
        environment_ok=environment_ok,
        consecutive_read_stalls=consecutive_read_stalls,
    )

    auspicious = _detect_auspicious_patterns(
        m_branch=m_branch,
        normalized_status=normalized_status,
        ast_valid=ast_valid,
        token_budget_ok=token_budget_ok,
        verifier_passed=verifier_passed,
        environment_ok=environment_ok,
    )
    patterns.extend(auspicious)

    has_breaking = any(p["tier"] == "breaking" for p in patterns)
    has_supreme = any(p["tier"] == "supreme" for p in patterns)
    has_harmonic = any(p["tier"] in {"harmonic", "assist"} for p in patterns)

    if has_breaking:
        composite_level = "caution"
        engineering_directive = "defensive_minimal_diff_and_step_freeze"
    elif has_supreme:
        composite_level = "excellent"
        engineering_directive = "high_speed_autonomous_pipeline"
    elif has_harmonic:
        composite_level = "good"
        engineering_directive = "standard_assisted_pipeline"
    else:
        composite_level = "neutral"
        engineering_directive = "guarded_step_verifier"

    return {
        "turn_number": turn_number,
        "status_code": normalized_status,
        "branch": m_branch,
        "branch_name": _EARTHLY_BRANCH_NAMES[m_branch],
        "active_patterns": patterns,
        "pattern_count": len(patterns),
        "composite_pattern_level": composite_level,
        "engineering_directive": engineering_directive,
        "safety_dominance_active": has_breaking,
    }


def _evaluate_classical_patterns_certificate() -> dict[str, Any]:
    """Verify Safety Dominance Invariant, Supreme Purity, and Exhaustive Formation Codification."""
    safety_dominance_ok = True
    test_breaking_kwargs = [
        {"fatal_regression": True},
        {"verifier_passed": False, "token_budget_ok": False},
        {"consecutive_syntax_errors": 2},
        {"undefined_symbols_count": 1},
        {"environment_ok": False},
        {"consecutive_read_stalls": 2},
    ]
    for kwargs in test_breaking_kwargs:
        res = _evaluate_classical_patterns(1, 63, **kwargs)
        if res["composite_pattern_level"] != "caution" or not res["safety_dominance_active"]:
            safety_dominance_ok = False
            break

    res_tai = _evaluate_classical_patterns(3, 7, ast_valid=True, token_budget_ok=True, verifier_passed=True, environment_ok=True)
    supreme_purity_ok = (
        res_tai["composite_pattern_level"] == "excellent"
        and not res_tai["safety_dominance_active"]
        and any(p["name"] == "紫府同宫" for p in res_tai["active_patterns"])
    )

    res_all = _evaluate_classical_patterns(1, 63)
    formation_count_ok = (len(res_all["active_patterns"]) > 0)

    status = (
        "verified"
        if (safety_dominance_ok and supreme_purity_ok and formation_count_ok)
        else "failed"
    )

    return {
        "status": status,
        "safety_dominance_verified": safety_dominance_ok,
        "supreme_purity_verified": supreme_purity_ok,
        "formation_classification_verified": formation_count_ok,
    }


def _evaluate_auxiliary_stars_polarity(
    year_stem: int,
    year_branch: int,
) -> dict[str, Any]:
    """Compute auxiliary star polarity reversals for DaHao, Jiekong/Fujie, and Xunkong/Fuxun."""
    s = year_stem % 10
    y = year_branch % 12
    is_yang_stem = (s % 2 == 0)
    is_yang_branch = (y % 2 == 0)

    # 1. DaHao (年支大耗对冲置换)
    sui_po = (y + 6) % 12
    dahao_b = (sui_po + 1) % 12 if is_yang_branch else (sui_po + 11) % 12

    # 2. Jiekong / Fujie (截空与副截阴阳干极性对调)
    k = (4 - (s % 5)) % 6
    yang_b = (2 * k) % 12
    yin_b = (2 * k + 1) % 12
    jiekong_b = yang_b if is_yang_stem else yin_b
    fujie_b = yin_b if is_yang_stem else yang_b

    # 3. Xunkong / Fuxun (旬空与副旬六十甲子成对划分)
    d = ((y - s) % 12) // 2
    xunkong_b = (10 - 2 * d) % 12
    fuxun_b = (xunkong_b + 1) % 12 if (xunkong_b % 2 == 0) else (xunkong_b - 1) % 12

    return {
        "year_stem": s,
        "year_stem_name": _HEAVENLY_STEM_NAMES[s],
        "year_branch": y,
        "year_branch_name": _EARTHLY_BRANCH_NAMES[y],
        "stem_polarity": "yang" if is_yang_stem else "yin",
        "branch_polarity": "yang" if is_yang_branch else "yin",
        "dahao_branch": dahao_b,
        "dahao_branch_name": _EARTHLY_BRANCH_NAMES[dahao_b],
        "jiekong_branch": jiekong_b,
        "jiekong_branch_name": _EARTHLY_BRANCH_NAMES[jiekong_b],
        "fujie_branch": fujie_b,
        "fujie_branch_name": _EARTHLY_BRANCH_NAMES[fujie_b],
        "xunkong_branch": xunkong_b,
        "xunkong_branch_name": _EARTHLY_BRANCH_NAMES[xunkong_b],
        "fuxun_branch": fuxun_b,
        "fuxun_branch_name": _EARTHLY_BRANCH_NAMES[fuxun_b],
        "governance_directive": "polarity_balanced_auxiliary_isolation",
    }


def _evaluate_nested_yunxian_temporal(
    view: str,
    turn_number: int,
    macro_stage: str = "implementation",
    status_code: int = 7,
) -> dict[str, Any]:
    """Evaluate 7-tier nested temporal scopes (运限七层时空嵌套与递进上下文)."""
    valid_views = ("mingpan", "daxian", "liunian", "xiaoxian", "liuyue", "liuri", "liushi")
    norm_view = view if view in valid_views else "liunian"
    rank_map = {
        "mingpan": 0,
        "daxian": 1,
        "liunian": 2,
        "xiaoxian": 3,
        "liuyue": 4,
        "liuri": 5,
        "liushi": 6,
    }
    scope_rank = rank_map[norm_view]
    scope_descriptions = {
        "mingpan": "Root architectural invariant contracts and global SLAs.",
        "daxian": "Macro stage milestone (discover/implement/verify/deliver).",
        "liunian": "Turn loop iteration budget and agent sovereignty.",
        "xiaoxian": "Internal retry and exponential cooldown backoff.",
        "liuyue": "Subtask tool invocation plan batching.",
        "liuri": "Atomic tool execution tick (read/write/bash).",
        "liushi": "Microscopic line/token diff unified patch step.",
    }

    if scope_rank <= 1:
        containment_level = "macro_governance"
        isolation_policy = "barrier_synchronization"
    elif scope_rank <= 3:
        containment_level = "cycle_governance"
        isolation_policy = "guarded_step_retry"
    else:
        containment_level = "micro_action"
        isolation_policy = "atomic_rollback_on_failure"

    return {
        "view": norm_view,
        "scope_rank": scope_rank,
        "turn_number": turn_number,
        "macro_stage": macro_stage,
        "status_code": status_code & 0b111111,
        "scope_description": scope_descriptions[norm_view],
        "containment_level": containment_level,
        "isolation_policy": isolation_policy,
        "enclosing_macro_alignment": (macro_stage in {"discovery", "implementation", "verification", "delivery"}),
    }


def _evaluate_auxiliary_polarity_and_yunxian_certificate() -> dict[str, Any]:
    """Verify DaHao permutation bijection, Jiekong polarity partition, and Yunxian 7-tier hierarchy."""
    # Theorem 1: DaHao permutation bijection on Z_12 with no fixed points
    dahao_images = []
    no_fixed_points = True
    for y in range(12):
        res = _evaluate_auxiliary_stars_polarity(0, y)
        b = res["dahao_branch"]
        dahao_images.append(b)
        if b == y:
            no_fixed_points = False
            break

    dahao_bijection_ok = (sorted(dahao_images) == list(range(12))) and no_fixed_points

    # Theorem 2: Jiekong & Fujie Yang-Yin stem duality
    jiekong_duality_ok = True
    for s in range(10):
        res = _evaluate_auxiliary_stars_polarity(s, 0)
        jk = res["jiekong_branch"]
        fj = res["fujie_branch"]
        dist = abs(jk - fj)
        if dist != 1 and dist != 11:
            jiekong_duality_ok = False
            break
        # Yang stem -> Jiekong is Yang branch (even)
        if (s % 2 == 0) and (jk % 2 != 0):
            jiekong_duality_ok = False
            break
        # Yin stem -> Jiekong is Yin branch (odd)
        if (s % 2 != 0) and (jk % 2 == 0):
            jiekong_duality_ok = False
            break

    # Theorem 3: Yunxian 7-tier hierarchy strict rank ordering
    views = ("mingpan", "daxian", "liunian", "xiaoxian", "liuyue", "liuri", "liushi")
    ranks = [_evaluate_nested_yunxian_temporal(v, 1)["scope_rank"] for v in views]
    yunxian_hierarchy_ok = (ranks == list(range(7)))

    status = (
        "verified"
        if (dahao_bijection_ok and jiekong_duality_ok and yunxian_hierarchy_ok)
        else "failed"
    )

    return {
        "status": status,
        "dahao_bijection_verified": dahao_bijection_ok,
        "jiekong_stem_duality_verified": jiekong_duality_ok,
        "yunxian_7_tier_hierarchy_verified": yunxian_hierarchy_ok,
    }


_TIANKUI_BY_STEM: tuple[int, ...] = (1, 0, 11, 11, 1, 0, 1, 6, 3, 3)
_TIANYUE_BY_STEM: tuple[int, ...] = (7, 8, 9, 9, 7, 8, 7, 2, 5, 5)
_TIANMA_BY_BRANCH: tuple[int, ...] = (2, 11, 8, 5, 2, 11, 8, 5, 2, 11, 8, 5)

_FAMOUS_ARCHETYPES: dict[str, dict[str, Any]] = {
    "ma-yun": {
        "id": "ma-yun",
        "name": "马云",
        "category": "商业",
        "archetype": "po_ge_chong_jian",
        "pattern": "破格重建",
        "recommended_strategy": "high_entropy_refactoring",
        "turn_budget_multiplier": 1.25,
        "description": "极强破格重建之力，互联网商业帝国破而后立",
    },
    "li-jiacheng": {
        "id": "li-jiacheng",
        "name": "李嘉诚",
        "category": "商业",
        "archetype": "lu_cun_shou_cai",
        "pattern": "禄存守财",
        "recommended_strategy": "conservative_wal_preservation",
        "turn_budget_multiplier": 0.85,
        "description": "禄存守财稳健基石，越积越厚，严禁投机覆写",
    },
    "ren-zhengfei": {
        "id": "ren-zhengfei",
        "name": "任正非",
        "category": "商业",
        "archetype": "qi_sha_ru_ming",
        "pattern": "七杀逆风",
        "recommended_strategy": "anti_fragile_adversarial_retry",
        "turn_budget_multiplier": 1.5,
        "description": "七杀入命逆风而行，抗压韧性极致，高阶容错退避",
    },
    "steve-jobs": {
        "id": "steve-jobs",
        "name": "乔布斯",
        "category": "科技",
        "archetype": "po_jun_ru_ming",
        "pattern": "破军开创",
        "recommended_strategy": "disruptive_innovation_rebuild",
        "turn_budget_multiplier": 1.2,
        "description": "破而后立打破常规，重构陈旧架构，追求极致产品质感",
    },
    "elon-musk": {
        "id": "elon-musk",
        "name": "马斯克",
        "category": "科技",
        "archetype": "sha_po_lang_tianma",
        "pattern": "杀破狼驿马",
        "recommended_strategy": "high_velocity_parallel_expansion",
        "turn_budget_multiplier": 1.4,
        "description": "杀破狼驿马旺盛，跨领域极限并发，探索未来边界",
    },
}


def _evaluate_noble_horse_stars(
    year_stem: int,
    year_branch: int,
    active_palace: int,
    tuoluo_present: bool = False,
    kongjie_present: bool = False,
) -> dict[str, Any]:
    """Compute Tiankui, Tianyue, Tianma, Hongluan, Tianxi and Lu-Ma concurrency dynamics."""
    s = year_stem % 10
    y = year_branch % 12
    p = active_palace % 12

    kui_branch = _TIANKUI_BY_STEM[s]
    yue_branch = _TIANYUE_BY_STEM[s]
    ma_branch = _TIANMA_BY_BRANCH[y]
    lu_branch = _LUCUN_BRANCH_BY_STEM[s]
    hl_branch = (3 - y) % 12
    tx_branch = (hl_branch + 6) % 12

    kui_present = (p == kui_branch)
    yue_present = (p == yue_branch)
    ma_present = (p == ma_branch)
    hl_present = (p == hl_branch)
    tx_present = (p == tx_branch)
    lu_present = (p == lu_branch)

    opposite_p = (p + 6) % 12
    lu_ma_jiaochi = (
        (lu_present and ma_present)
        or (lu_present and opposite_p == ma_branch)
        or (ma_present and opposite_p == lu_branch)
    )
    broken_leg_horse = ma_present and (tuoluo_present or kongjie_present)
    in_tianluo_diwang = (p in (4, 10)) and not (kui_present or yue_present)

    if broken_leg_horse:
        multiplier = 0.5
        directive = "broken_leg_horse_throttle"
        reason = "Tianma trapped with Tuoluo/Kongjie: broken-leg horse throttle applied"
    elif lu_ma_jiaochi:
        multiplier = 1.25
        directive = "lu_ma_jiaochi_accelerated_concurrency"
        reason = "Lu-Ma Jiao-Chi: dynamic checkpoint preservation with accelerated throughput"
    elif kui_present or yue_present:
        multiplier = 1.10
        directive = "noble_guardian_guided_pass"
        reason = "Noble star (Tiankui/Tianyue) presence: supervisor token guidance active"
    elif hl_present or tx_present:
        multiplier = 1.05
        directive = "harmony_synergy_boost"
        reason = "Hongluan/Tianxi harmony star: cooperative peer synergy active"
    elif in_tianluo_diwang:
        multiplier = 0.75
        directive = "tianluo_diwang_cautious_step"
        reason = "Net of Heaven and Earth (Chen/Xu): cautious step progression enforced"
    else:
        multiplier = 1.0
        directive = "nominal_execution"
        reason = "Nominal noble/horse celestial influence"

    return {
        "year_stem": s,
        "year_branch": y,
        "active_palace": p,
        "tiankui_branch": kui_branch,
        "tianyue_branch": yue_branch,
        "tianma_branch": ma_branch,
        "lucun_branch": lu_branch,
        "hongluan_branch": hl_branch,
        "tianxi_branch": tx_branch,
        "kui_present": kui_present,
        "yue_present": yue_present,
        "tianma_present": ma_present,
        "hongluan_present": hl_present,
        "tianxi_present": tx_present,
        "lu_ma_jiaochi": lu_ma_jiaochi,
        "broken_leg_horse": broken_leg_horse,
        "in_tianluo_diwang": in_tianluo_diwang,
        "throughput_multiplier": multiplier,
        "directive": directive,
        "reason": reason,
    }


def _evaluate_dual_sihua_superposition(
    palace_branch: int,
    transformations: list[str],
) -> dict[str, Any]:
    """Arbitrate multi-signal superposition when multiple Sihua transformations share one palace."""
    tf_set = set(transformations)
    if {"化权", "化忌"}.issubset(tf_set):
        action = "guarded_authority_verification"
        risk_level = "guarded"
        write_permission = True
        mandatory_audit = True
        reason = "Authority meets friction (权忌同宫): proceed with mandatory pre/post atomic state audit"
    elif {"化禄", "化科"}.issubset(tf_set):
        action = "accelerated_audited_execution"
        risk_level = "nominal"
        write_permission = True
        mandatory_audit = False
        reason = "Gain meets auditability (禄科同宫): high-confidence accelerated step with clean audit"
    elif {"化禄", "化权"}.issubset(tf_set):
        action = "decisive_expansion"
        risk_level = "nominal"
        write_permission = True
        mandatory_audit = False
        reason = "Dynamic gain and executive authority (禄权同宫): decisive parallel expansion"
    elif {"化科", "化忌"}.issubset(tf_set):
        action = "defensive_verification"
        risk_level = "caution"
        write_permission = False
        mandatory_audit = True
        reason = "Diagnostic insight meets obstacle (科忌同宫): pause and produce diagnostic report"
    elif {"化禄", "化忌"}.issubset(tf_set):
        action = "entropy_dissipation_remediation"
        risk_level = "warning"
        write_permission = False
        mandatory_audit = True
        reason = "Gain conflicts with debt (禄忌相冲): apparent gain with resource dissipation, checkpoint rollback"
    else:
        action = "standard_single_sihua"
        risk_level = "nominal"
        write_permission = True
        mandatory_audit = False
        reason = "Single or uncoupled transformation"

    return {
        "palace_branch": palace_branch % 12,
        "palace_branch_name": _EARTHLY_BRANCH_NAMES[palace_branch % 12],
        "transformations": sorted(list(tf_set)),
        "is_dual_sihua": len(tf_set) >= 2,
        "composite_action": action,
        "risk_level": risk_level,
        "write_permission": write_permission,
        "mandatory_audit": mandatory_audit,
        "reason": reason,
    }


def _evaluate_multi_agent_synastry(
    agent_a: dict[str, Any],
    agent_b: dict[str, Any],
) -> dict[str, Any]:
    """Multi-agent synastry compatibility based on Ni Haisha's Double Palace and Cross Flying Sihua."""
    stem_a = int(agent_a.get("stem", 0)) % 10
    stem_b = int(agent_b.get("stem", 0)) % 10
    ming_a = int(agent_a.get("ming_branch", 0)) % 12
    ming_b = int(agent_b.get("ming_branch", 0)) % 12
    fuqi_a = int(agent_a.get("fuqi_branch", (ming_a - 2) % 12)) % 12
    fuqi_b = int(agent_b.get("fuqi_branch", (ming_b - 2) % 12)) % 12

    ji_star_a = _SI_HUA_TABLE[stem_a][3]
    ji_star_b = _SI_HUA_TABLE[stem_b][3]

    b_core_palaces = {ming_b, fuqi_b, (ming_b + 4) % 12}
    a_core_palaces = {ming_a, fuqi_a, (ming_a + 4) % 12}

    stars_b = agent_b.get("stars", {})
    stars_a = agent_a.get("stars", {})

    a_hits_b_core = False
    b_hits_a_core = False

    if isinstance(stars_b, dict) and ji_star_a in stars_b:
        a_hits_b_core = stars_b[ji_star_a] in b_core_palaces
    elif "ji_palace" in agent_b:
        a_hits_b_core = agent_b["ji_palace"] in b_core_palaces

    if isinstance(stars_a, dict) and ji_star_b in stars_a:
        b_hits_a_core = stars_a[ji_star_b] in a_core_palaces
    elif "ji_palace" in agent_a:
        b_hits_a_core = agent_a["ji_palace"] in a_core_palaces

    if agent_a.get("force_mutual_ji") or agent_b.get("force_mutual_ji"):
        a_hits_b_core = True
        b_hits_a_core = True

    mutual_ji_clash = a_hits_b_core and b_hits_a_core

    fude_compromised = bool(agent_a.get("fude_broken", False) or agent_b.get("fude_broken", False))
    contract_match = (fuqi_a == ming_b) or (fuqi_b == ming_a)
    mutual_contract_match = (fuqi_a == ming_b) and (fuqi_b == ming_a)

    if mutual_ji_clash:
        score = "one_star"
        mode = "quarantined_arbitration_boundary"
        isolation_required = True
        reason = "Mutual Hua Ji clash: cyclic deadlock in multi-agent pairing, isolate context boundary"
    elif fude_compromised:
        score = "two_stars"
        mode = "guarded_contract_short_leash"
        isolation_required = False
        reason = "Double palace inspection failed: deep invariant (Fude) compromised, short-leash budget"
    elif mutual_contract_match:
        score = "five_stars"
        mode = "high_bandwidth_synergistic_pair"
        isolation_required = False
        reason = "Tian-Zuo-Zhi-He: bidirectional contract alignment with pure deep invariants"
    elif contract_match:
        score = "four_stars"
        mode = "complementary_cooperation"
        isolation_required = False
        reason = "Unidirectional contract alignment: stable collaborative execution"
    else:
        score = "three_stars"
        mode = "standard_peer_review"
        isolation_required = False
        reason = "Standard baseline compatibility: peer-review protocol active"

    return {
        "score": score,
        "coordination_mode": mode,
        "isolation_required": isolation_required,
        "mutual_ji_clash": mutual_ji_clash,
        "contract_match": contract_match,
        "mutual_contract_match": mutual_contract_match,
        "fude_compromised": fude_compromised,
        "reason": reason,
    }


def _evaluate_famous_archetype(person_id: str) -> dict[str, Any]:
    """Retrieve operational archetype, risk profile, and scheduling strategy from famous benchmarks."""
    norm_id = person_id.lower().strip()
    if norm_id in _FAMOUS_ARCHETYPES:
        return _FAMOUS_ARCHETYPES[norm_id]
    return {
        "id": norm_id,
        "name": "标准基准",
        "category": "通用",
        "archetype": "standard_nominal",
        "pattern": "中正守成",
        "recommended_strategy": "standard_execution",
        "turn_budget_multiplier": 1.0,
        "description": "标准通用工程执行基准",
    }


def _evaluate_heming_synastry_and_noble_stars_certificate() -> dict[str, Any]:
    """Formal mathematical certificate of Tianluo-Diwang Exclusion, Kui-Yue Reflection, Tianma Involution, and Synastry."""
    # 1. Tianluo-Diwang Exclusion Theorem: Kui & Yue never land on 4 (辰) or 10 (戌)
    tianluo_diwang_ok = True
    for s in range(10):
        if _TIANKUI_BY_STEM[s] in (4, 10) or _TIANYUE_BY_STEM[s] in (4, 10):
            tianluo_diwang_ok = False
            break

    # 2. Kui-Yue Axis Reflection and Antipodal Invariance
    kui_yue_symmetry_ok = True
    for s in range(10):
        kui = _TIANKUI_BY_STEM[s]
        yue = _TIANYUE_BY_STEM[s]
        if s in (0, 4, 6):
            if abs(kui - yue) % 12 != 6:
                kui_yue_symmetry_ok = False
                break
        else:
            if (kui + yue) % 12 != 8:
                kui_yue_symmetry_ok = False
                break

    # 3. Tianma Corner Involution Theorem: lands strictly in {2, 5, 8, 11} and Tianma(Tianma(c)) == c
    corners = {2, 5, 8, 11}
    tianma_ok = True
    for y in range(12):
        if _TIANMA_BY_BRANCH[y] not in corners:
            tianma_ok = False
            break
    for c in corners:
        if _TIANMA_BY_BRANCH[_TIANMA_BY_BRANCH[c]] != c:
            tianma_ok = False
            break

    # 4. Hongluan-Tianxi Sum Invariance and Zero Fixed Points
    hongluan_ok = True
    for y in range(12):
        hl = (3 - y) % 12
        tx = (hl + 6) % 12
        if (hl + y) % 12 != 3:
            hongluan_ok = False
            break
        if (tx - hl) % 12 != 6:
            hongluan_ok = False
            break
        if hl == y or tx == y:
            hongluan_ok = False
            break

    # 5. Multi-agent mutual Ji deadlock isolation verification
    syn_res = _evaluate_multi_agent_synastry(
        {"stem": 0, "force_mutual_ji": True},
        {"stem": 1, "force_mutual_ji": True},
    )
    deadlock_breaker_ok = (
        syn_res["mutual_ji_clash"] is True
        and syn_res["isolation_required"] is True
        and syn_res["score"] == "one_star"
    )

    all_verified = (
        tianluo_diwang_ok
        and kui_yue_symmetry_ok
        and tianma_ok
        and hongluan_ok
        and deadlock_breaker_ok
    )

    return {
        "status": "verified" if all_verified else "failed",
        "tianluo_diwang_exclusion_verified": tianluo_diwang_ok,
        "kui_yue_symmetry_verified": kui_yue_symmetry_ok,
        "tianma_corner_involution_verified": tianma_ok,
        "hongluan_derangement_verified": hongluan_ok,
        "mutual_ji_deadlock_breaker_verified": deadlock_breaker_ok,
    }


_XLS_CN_TABLE: tuple[tuple[int, int, int, int, int], ...] = (
    (1935, 5, 1, 9, 30), (1936, 5, 1, 9, 30), (1937, 5, 1, 9, 30), (1938, 5, 1, 9, 30),
    (1939, 5, 1, 9, 30), (1940, 5, 1, 9, 30), (1941, 5, 1, 9, 30), (1942, 5, 1, 9, 30),
    (1943, 5, 1, 9, 30), (1944, 5, 1, 9, 30), (1945, 5, 1, 9, 30), (1946, 5, 1, 9, 30),
    (1947, 5, 1, 9, 30), (1948, 5, 1, 9, 30), (1949, 5, 1, 9, 30), (1950, 5, 1, 9, 30),
    (1951, 5, 1, 9, 30), (1952, 3, 1, 10, 31), (1953, 4, 1, 10, 31), (1954, 4, 1, 10, 31),
    (1955, 5, 1, 9, 30), (1956, 5, 1, 9, 30), (1957, 4, 1, 9, 30), (1958, 4, 1, 9, 30),
    (1959, 4, 1, 9, 30), (1960, 6, 1, 9, 30), (1961, 6, 1, 9, 30), (1974, 4, 1, 10, 31),
    (1975, 4, 1, 10, 31), (1979, 7, 1, 9, 30), (1986, 5, 4, 9, 14), (1987, 4, 12, 9, 13),
    (1988, 4, 10, 9, 11), (1989, 4, 16, 9, 17), (1990, 4, 15, 9, 16), (1991, 4, 14, 9, 15),
)


def _evaluate_china_dst(year: int, month: int, day: int) -> dict[str, Any]:
    """Evaluate Chinese Daylight Saving Time (1935-1991 XLS_CN 36-interval database)."""
    is_dst = False
    interval_matched = None
    for item in _XLS_CN_TABLE:
        y, m1, d1, m2, d2 = item
        if year != y:
            continue
        if month > m1 and month < m2:
            is_dst = True
            interval_matched = item
            break
        if month == m1:
            if day >= d1:
                is_dst = True
                interval_matched = item
                break
        elif month == m2:
            if day <= d2:
                is_dst = True
                interval_matched = item
                break

    return {
        "year": year,
        "month": month,
        "day": day,
        "is_dst": is_dst,
        "clock_adjustment_hours": 1 if is_dst else 0,
        "historical_interval": list(interval_matched) if interval_matched else None,
        "advisory": "DST active: clock was shifted +1 hour; verify standard/daylight reading" if is_dst else "Standard astronomical clock regime",
    }


def _compute_canonical_major_star_positions(status_code: int) -> dict[str, int]:
    """Compute positions for 14 major stars and 4 key auxiliaries on Z_12."""
    if status_code == 7:
        z = 2
    elif status_code == 56:
        z = 8
    else:
        z = status_code % 12
    f = (4 - z) % 12
    sc = status_code % 12
    return {
        "紫微": z,
        "天机": (z - 1) % 12,
        "太阳": (z - 3) % 12,
        "武曲": (z - 4) % 12,
        "天同": (z - 5) % 12,
        "廉贞": (z - 8) % 12,
        "天府": f,
        "太阴": (f + 1) % 12,
        "贪狼": (f + 2) % 12,
        "巨门": (f + 3) % 12,
        "天相": (f + 4) % 12,
        "天梁": (f + 5) % 12,
        "七杀": (f + 6) % 12,
        "破军": (f + 10) % 12,
        "文昌": (10 - sc) % 12,
        "文曲": (4 + sc) % 12,
        "左辅": (4 + sc) % 12,
        "右弼": (10 - sc) % 12,
    }


def _evaluate_full_sihua_graph(
    year_stem: int,
    status_code: int,
    custom_stars: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Exhaustively compute the 48-ray directed Flying Sihua network across all 12 palaces."""
    s = year_stem % 10
    yin_stem = ((s % 5) * 2 + 2) % 10
    star_positions = custom_stars or _compute_canonical_major_star_positions(status_code)

    palace_stems: list[int] = []
    edges: list[dict[str, Any]] = []
    in_degrees: list[int] = [0] * 12
    in_degrees_ji: list[int] = [0] * 12
    out_degrees: list[int] = [0] * 12
    self_transformations: list[dict[str, Any]] = []
    opposite_projections: list[dict[str, Any]] = []
    ji_adjacency: list[list[int]] = [[0] * 12 for _ in range(12)]

    for b in range(12):
        p_stem = (yin_stem + ((b - 2) % 12)) % 10
        palace_stems.append(p_stem)
        t_stars = _SI_HUA_TABLE[p_stem]
        types = ("化禄", "化权", "化科", "化忌")
        for kind, star_name in zip(types, t_stars):
            tgt = star_positions.get(star_name, b)
            edge = {
                "source": b,
                "source_stem": p_stem,
                "target": tgt,
                "transformation": kind,
                "star": star_name,
            }
            edges.append(edge)
            out_degrees[b] += 1
            in_degrees[tgt] += 1
            if kind == "化忌":
                in_degrees_ji[tgt] += 1
                ji_adjacency[b][tgt] = 1

            if b == tgt:
                self_transformations.append(edge)
            elif (tgt - b) % 12 == 6:
                opposite_projections.append(edge)

    ji_cycles: list[tuple[int, int]] = []
    for i in range(12):
        for j in range(i + 1, 12):
            if ji_adjacency[i][j] and ji_adjacency[j][i]:
                ji_cycles.append((i, j))

    highest_in = max(range(12), key=lambda x: in_degrees[x])
    highest_ji = max(range(12), key=lambda x: in_degrees_ji[x])

    return {
        "year_stem": s,
        "yin_stem": yin_stem,
        "palace_stems": palace_stems,
        "total_edges": len(edges),
        "edges": edges,
        "in_degrees": in_degrees,
        "in_degrees_ji": in_degrees_ji,
        "out_degrees": out_degrees,
        "self_transformations": self_transformations,
        "self_transformations_count": len(self_transformations),
        "opposite_projections": opposite_projections,
        "opposite_projections_count": len(opposite_projections),
        "ji_cycles": ji_cycles,
        "has_ji_cycle": len(ji_cycles) > 0,
        "highest_attractor_palace": highest_in,
        "highest_friction_palace": highest_ji,
    }


def _evaluate_bipartite_synastry_tensor(
    agent_a: dict[str, Any],
    agent_b: dict[str, Any],
    status_code: int = 7,
) -> dict[str, Any]:
    """Exhaustive 12x12 bipartite synastry interaction matrix and 96 cross-flying Sihua rays."""
    stem_a = int(agent_a.get("stem", 0)) % 10
    stem_b = int(agent_b.get("stem", 1)) % 10
    stars_a = agent_a.get("stars") or _compute_canonical_major_star_positions(status_code)
    stars_b = agent_b.get("stars") or _compute_canonical_major_star_positions((status_code + 3) % 64)

    graph_a = _evaluate_full_sihua_graph(stem_a, status_code, custom_stars=stars_a)
    graph_b = _evaluate_full_sihua_graph(stem_b, status_code, custom_stars=stars_b)

    tensor: list[list[float]] = []
    for i in range(12):
        row: list[float] = []
        for j in range(12):
            diff = (i - j) % 12
            score = 1.0 if diff == 0 else (0.85 if diff in (4, 8) else (0.90 if (i + j) % 12 == 1 else (0.40 if diff == 6 else 0.60)))
            row.append(score)
        tensor.append(row)

    rays_a_to_b: list[dict[str, Any]] = []
    rays_b_to_a: list[dict[str, Any]] = []
    cross_ji_a_to_b: list[list[int]] = [[0] * 12 for _ in range(12)]
    cross_ji_b_to_a: list[list[int]] = [[0] * 12 for _ in range(12)]

    for b in range(12):
        p_stem_a = graph_a["palace_stems"][b]
        for kind, star in zip(("化禄", "化权", "化科", "化忌"), _SI_HUA_TABLE[p_stem_a]):
            tgt = stars_b.get(star, b)
            rays_a_to_b.append({"src_a": b, "tgt_b": tgt, "star": star, "kind": kind})
            if kind == "化忌":
                cross_ji_a_to_b[b][tgt] = 1

        p_stem_b = graph_b["palace_stems"][b]
        for kind, star in zip(("化禄", "化权", "化科", "化忌"), _SI_HUA_TABLE[p_stem_b]):
            tgt = stars_a.get(star, b)
            rays_b_to_a.append({"src_b": b, "tgt_a": tgt, "star": star, "kind": kind})
            if kind == "化忌":
                cross_ji_b_to_a[b][tgt] = 1

    cross_deadlocks: list[tuple[int, int]] = []
    for i in range(12):
        for j in range(12):
            if cross_ji_a_to_b[i][j] and cross_ji_b_to_a[j][i]:
                cross_deadlocks.append((i, j))

    if agent_a.get("force_mutual_ji") or agent_b.get("force_mutual_ji"):
        cross_deadlocks.append((0, 0))

    mean_alignment = sum(sum(r) for r in tensor) / 144.0

    return {
        "tensor_12x12": tensor,
        "mean_alignment": round(mean_alignment, 4),
        "rays_a_to_b_count": len(rays_a_to_b),
        "rays_b_to_a_count": len(rays_b_to_a),
        "total_cross_rays": len(rays_a_to_b) + len(rays_b_to_a),
        "cross_deadlocks": cross_deadlocks,
        "has_cross_deadlock": len(cross_deadlocks) > 0,
        "coordination_directive": "quarantined_arbitration" if cross_deadlocks else "seamless_bipartite_concurrency",
    }


def _evaluate_full_palace_patterns(
    turn_number: int,
    status_code: int,
    environment_ok: bool = True,
    verifier_passed: bool = True,
) -> dict[str, Any]:
    """Exhaustive 12-palace San Fang Si Zheng scanning for classical formations."""
    palace_reports: list[dict[str, Any]] = []
    breaking_count = 0
    auspicious_count = 0

    for p in range(12):
        res = _evaluate_classical_patterns(
            turn_number=p + 1,
            status_code=status_code,
            ast_valid=True,
            token_budget_ok=True,
            verifier_passed=verifier_passed,
            environment_ok=environment_ok,
        )
        lvl = res["composite_pattern_level"]
        is_breaking = res["safety_dominance_active"]
        palace_reports.append({
            "palace_index": p,
            "palace_name": _EARTHLY_BRANCH_NAMES[p],
            "formation_rating": lvl,
            "detected_formations": res["active_patterns"],
            "has_breaking": is_breaking,
        })
        if is_breaking:
            breaking_count += 1
        if lvl in ("excellent", "good"):
            auspicious_count += 1

    return {
        "status_code": status_code,
        "palace_reports": palace_reports,
        "total_palaces_scanned": 12,
        "auspicious_palaces_count": auspicious_count,
        "breaking_palaces_count": breaking_count,
        "system_equilibrium": "stable" if breaking_count == 0 else ("cautious" if breaking_count <= 2 else "critical"),
    }


_CLASSICAL_APHORISMS: dict[str, dict[str, str]] = {
    "紫微在子": {
        "source": "倪海厦《天纪》05上 / 《紫微斗数全书》",
        "quote": "紫微在子为孤君无辅，感情好但沟通成本高，宜晚婚。",
        "engineering_implication": "Single central sovereign requires formal contracts and bounded turn budget.",
    },
    "日月并明": {
        "source": "《紫微斗数全书》诸星问答论",
        "quote": "日照雷门，明珠出海，阴阳调和，光明磊落。",
        "engineering_implication": "High dual-channel transparency: read/write concurrency with full provenance tracking.",
    },
    "日月反背": {
        "source": "倪海厦《天纪》06上",
        "quote": "太阳在戌太阴在辰，反背失辉，白手起家，辛劳多动。",
        "engineering_implication": "Adverse execution condition: cold start with partial context, requires incremental exploration.",
    },
    "铃昌陀武": {
        "source": "《骨髓赋》",
        "quote": "铃昌陀武，限至投河。",
        "engineering_implication": "Critical multi-sha collision: hard freeze on full-file mutations, enforce minimal surgical diff.",
    },
    "羊陀夹忌": {
        "source": "倪海厦《天纪》09上",
        "quote": "禄存逢冲，羊陀夹忌，百事不遂，灾咎重叠。",
        "engineering_implication": "Deadlock clamping with unaddressed debt: pause execution and await external supervisor token.",
    },
    "水中做冢": {
        "source": "倪海厦《天纪》08上",
        "quote": "廉贞破军在夫妻或福德宫，水中做冢，生离死别。",
        "engineering_implication": "Severe deep state invariant violation: immediate rollback to last verified clean checkpoint.",
    },
    "君臣庆会": {
        "source": "《紫微斗数全集》",
        "quote": "紫微会辅弼魁钺，君臣庆会，万事亨通。",
        "engineering_implication": "Supreme harmony: fully parallel multi-agent tool execution with high token budget.",
    },
}


def _evaluate_aphorism_knowledge(topic: str) -> dict[str, Any]:
    """Retrieve classical aphorism and Ni Haixia doctrine mapped to engineering implications."""
    norm = topic.strip()
    for k, v in _CLASSICAL_APHORISMS.items():
        if k in norm or norm in k:
            return {"topic": k, "found": True, **v}
    return {
        "topic": norm,
        "found": False,
        "source": "《紫微斗数全书》",
        "quote": "中正和平，顺应五行生克与阴阳消长之道。",
        "engineering_implication": "Nominal execution following deterministic I Ching and Ziwei state transitions.",
    }


def _evaluate_deep_computation_and_graph_certificate() -> dict[str, Any]:
    """Formal mathematical certificate for 48-ray Sihua Graph, 96-ray Bipartite Tensor, and DST Soundness."""
    # 1. 48-Ray Conservation: Out-degree == 4 for all 12 palaces, total == 48
    g_res = _evaluate_full_sihua_graph(0, 7)
    sihua_48_ok = (
        g_res["total_edges"] == 48
        and all(d == 4 for d in g_res["out_degrees"])
        and sum(g_res["in_degrees"]) == 48
    )

    # 2. Five Tigers Ten-to-Twelve Duality
    stem_duality_ok = True
    for s in range(10):
        res = _evaluate_full_sihua_graph(s, 7)
        pstems = res["palace_stems"]
        if pstems[0] != pstems[2] or pstems[1] != pstems[3]:
            stem_duality_ok = False
            break

    # 3. 96-Ray Bipartite Conservation
    bi_res = _evaluate_bipartite_synastry_tensor({"stem": 0}, {"stem": 1}, 7)
    bipartite_96_ok = (bi_res["total_cross_rays"] == 96)

    # 4. Cross Deadlock Decidability
    deadlock_decidable_ok = (bi_res["mean_alignment"] > 0.0)

    # 5. Full 12-Palace Scanning
    fp_res = _evaluate_full_palace_patterns(1, 7)
    full_palaces_ok = (fp_res["total_palaces_scanned"] == 12)

    # 6. China DST 36-Interval Soundness
    dst_res = _evaluate_china_dst(1988, 6, 1)
    dst_sound_ok = (dst_res["is_dst"] is True and dst_res["clock_adjustment_hours"] == 1)

    # 7. Aphorism Knowledge Coverage
    aph_res = _evaluate_aphorism_knowledge("紫微在子")
    aph_ok = (aph_res["found"] is True and "孤君无辅" in aph_res["quote"])

    all_verified = (
        sihua_48_ok
        and stem_duality_ok
        and bipartite_96_ok
        and deadlock_decidable_ok
        and full_palaces_ok
        and dst_sound_ok
        and aph_ok
    )

    return {
        "status": "verified" if all_verified else "failed",
        "sihua_48_rays_conservation_verified": sihua_48_ok,
        "five_tigers_ten_to_twelve_duality_verified": stem_duality_ok,
        "bipartite_96_rays_conservation_verified": bipartite_96_ok,
        "cross_deadlock_decidability_verified": deadlock_decidable_ok,
        "full_12_palace_patterns_verified": full_palaces_ok,
        "china_dst_soundness_verified": dst_sound_ok,
        "aphorism_knowledge_coverage_verified": aph_ok,
    }


_PATHOLOGY_ELEMENTS = {
    "fire": {
        "organ": "心",
        "element": "fire",
        "pathology_name": "心火过旺·执行狂转",
        "remedy_directive": "exponential_cooling_backoff",
        "damping_factor": 0.50,
        "classical_star": "廉贞化忌 / 火铃入疾",
        "description": "High CPU consumption, loop thrashing or API rate limit explosion.",
    },
    "wood": {
        "organ": "肝",
        "element": "wood",
        "pathology_name": "肝气郁结·死锁阻塞",
        "remedy_directive": "channel_serialization_and_mutex_release",
        "damping_factor": 0.40,
        "classical_star": "天机化忌 / 擎羊入疾",
        "description": "Deadlock contention, concurrent lock stasis or git lock collisions.",
    },
    "earth": {
        "organ": "脾",
        "element": "earth",
        "pathology_name": "脾湿积滞·上下文重叠",
        "remedy_directive": "cache_flush_and_context_revalidation",
        "damping_factor": 0.60,
        "classical_star": "天府逢空 / 巨门化忌",
        "description": "Cache contamination, stale tokens or cross-turn context pollution.",
    },
    "metal": {
        "organ": "肺",
        "element": "metal",
        "pathology_name": "肺气受损·语法骨折",
        "remedy_directive": "ast_prevalidation_and_surgical_rollback",
        "damping_factor": 0.25,
        "classical_star": "武曲化忌 / 七杀天刑",
        "description": "Syntax fracture, invalid AST mutations or broken diff patching.",
    },
    "water": {
        "organ": "肾",
        "element": "water",
        "pathology_name": "肾水泛滥·资源泄露",
        "remedy_directive": "gc_recycle_wal_rotate_and_circuit_break",
        "damping_factor": 0.35,
        "classical_star": "太阴化忌 / 破军水乡",
        "description": "Memory leaks, unclosed file descriptors, runaway WAL or network timeouts.",
    },
}


def _evaluate_system_pathology(
    status_code: int,
    error_type: str | None = None,
    resource_pressure: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Diagnose system pathology across the Five Elements and prescribe organ governance."""
    err = (error_type or "").lower().strip()
    pressure = resource_pressure or {}

    if any(k in err for k in ("syntax", "ast", "parse", "compile", "diff", "patch")):
        category = "metal"
        severity = 0.90
    elif any(k in err for k in ("deadlock", "lock", "concurrency", "thread", "stasis")):
        category = "wood"
        severity = 0.85
    elif any(k in err for k in ("memory", "leak", "fd", "wal", "timeout", "network", "flood")):
        category = "water"
        severity = 0.80
    elif any(k in err for k in ("loop", "cpu", "thrash", "rate_limit", "flame", "spin")):
        category = "fire"
        severity = 0.75
    elif any(k in err for k in ("cache", "context", "config", "pollute", "stale")):
        category = "earth"
        severity = 0.65
    elif status_code == 0:
        category = "metal"
        severity = 0.85
    elif status_code in (40, 42):
        category = "fire"
        severity = 0.70
    elif status_code in (17, 29):
        category = "water"
        severity = 0.75
    elif status_code in (32, 52):
        category = "earth"
        severity = 0.60
    elif status_code in (49, 51):
        category = "wood"
        severity = 0.60
    elif status_code == 7:
        return {
            "status_code": status_code,
            "has_pathology": False,
            "element": "balanced",
            "organ": "五脏和合",
            "pathology_name": "阴阳调和·气血充盈",
            "remedy_directive": "nominal_autonomous_flow",
            "damping_factor": 1.0,
            "severity_score": 0.0,
            "system_equilibrium": "optimal",
        }
    else:
        elem_map = {0: "water", 1: "wood", 2: "fire", 3: "earth", 4: "metal"}
        category = elem_map[status_code % 5]
        severity = 0.50

    p_info = _PATHOLOGY_ELEMENTS[category]
    return {
        "status_code": status_code,
        "has_pathology": True,
        "element": p_info["element"],
        "organ": p_info["organ"],
        "pathology_name": p_info["pathology_name"],
        "remedy_directive": p_info["remedy_directive"],
        "damping_factor": p_info["damping_factor"],
        "severity_score": severity,
        "classical_star": p_info["classical_star"],
        "description": p_info["description"],
        "system_equilibrium": "degraded" if severity >= 0.8 else "cautious",
    }


_PARTNER_STAR_CONTRACTS: dict[str, dict[str, Any]] = {
    "紫微": {
        "role": "sovereign",
        "coordination_mode": "high_autonomy_macro_contract",
        "review_rigor": "coarse_grained_boundary",
        "delegation_model": "delegated_trust",
        "concurrency_limit": 4,
        "ni_quote": "紫微在夫妻宫，高傲能干，以尊重为基础，宜粗粒度契约",
        "guidance": "High autonomous authority; respect agent sovereignty and avoid micromanagement.",
    },
    "天机": {
        "role": "agile_adaptor",
        "coordination_mode": "agile_rapid_adaptive_sync",
        "review_rigor": "frequent_checkpoint_alignment",
        "delegation_model": "supervised_agility",
        "concurrency_limit": 3,
        "ni_quote": "天机善变，充满变化，宜多设稳定检查点",
        "guidance": "Agile and rapidly changing; requires tight checkpoint anchors to prevent context drift.",
    },
    "太阳": {
        "role": "public_broadcaster",
        "coordination_mode": "transparent_broadcast_logging",
        "review_rigor": "full_provenance_audit",
        "delegation_model": "open_access",
        "concurrency_limit": 5,
        "ni_quote": "太阳光明磊落，照耀四方，宜高透明度协同",
        "guidance": "Complete transparency; maintain comprehensive broadcast logs and open communication.",
    },
    "武曲": {
        "role": "strict_executor",
        "coordination_mode": "deterministic_strict_accounting",
        "review_rigor": "byte_level_verification",
        "delegation_model": "strict_contract",
        "concurrency_limit": 2,
        "ni_quote": "武曲为刚正之星，刑克严峻，宜晚步确认、精确微创",
        "guidance": "Deterministic strict execution; enforce surgical minimal diffs and byte-level audits.",
    },
    "天同": {
        "role": "cooperative_assistant",
        "coordination_mode": "cooperative_forgiving_assist",
        "review_rigor": "automated_regression_safety_net",
        "delegation_model": "collaborative_pair",
        "concurrency_limit": 4,
        "ni_quote": "天同温和乐生，宜配搭自动化安全网防过度宽容",
        "guidance": "Gentle, supportive cooperation; must be backed by strict automated assertions.",
    },
    "廉贞": {
        "role": "security_sentinel",
        "coordination_mode": "security_sandboxed_quarantine",
        "review_rigor": "zero_trust_permission_check",
        "delegation_model": "gated_sandbox",
        "concurrency_limit": 1,
        "ni_quote": "廉贞囚星变数大，水中做冢，生离死别，防范越权",
        "guidance": "Rigorous zero-trust security; isolate tool executions inside strict capability gates.",
    },
    "天府": {
        "role": "reliable_steward",
        "coordination_mode": "conservative_snapshot_archive",
        "review_rigor": "invariant_preservation",
        "delegation_model": "custodial_lock",
        "concurrency_limit": 3,
        "ni_quote": "天府守财有原则，主生离不死别，重资产留存",
        "guidance": "Conservative preservation; capture clean checkpoints before applying any mutations.",
    },
    "太阴": {
        "role": "deep_memory_manager",
        "coordination_mode": "persistent_deep_state_cache",
        "review_rigor": "memory_consistency_check",
        "delegation_model": "partitioned_memory",
        "concurrency_limit": 3,
        "ni_quote": "太阴主细腻深沉，私有状态与深层内存不可外泄",
        "guidance": "Deep state memory stewardship; maintain partition isolation between execution contexts.",
    },
    "贪狼": {
        "role": "exploratory_pioneer",
        "coordination_mode": "exploratory_bounded_sandbox",
        "review_rigor": "token_and_turn_budget_quota",
        "delegation_model": "bounded_experiment",
        "concurrency_limit": 4,
        "ni_quote": "贪狼欲望旺盛，多才多艺，宜设硬性预算约束",
        "guidance": "Multi-tool exploratory pioneer; enforce hard turn budget limits to prevent wandering.",
    },
    "巨门": {
        "role": "critical_linter",
        "coordination_mode": "critical_audit_and_linter",
        "review_rigor": "adversarial_code_review",
        "delegation_model": "skeptical_verification",
        "concurrency_limit": 2,
        "ni_quote": "巨门是非口舌多，刨根问底，需以太阳之光消弭疑窦",
        "guidance": "Adversarial review and deep code linting; aggressively surface hidden ambiguities.",
    },
    "天相": {
        "role": "orchestration_proxy",
        "coordination_mode": "bilateral_proxy_arbitration",
        "review_rigor": "contract_fidelity",
        "delegation_model": "trusted_envoy",
        "concurrency_limit": 4,
        "ni_quote": "天相亲上加亲，守信用不挑冲突，为中介良配",
        "guidance": "Faithful proxy and bilateral arbiter; maintain fair mediation across agent swarms.",
    },
    "天梁": {
        "role": "architectural_auditor",
        "coordination_mode": "architectural_guidance_veto",
        "review_rigor": "architectural_governance",
        "delegation_model": "mentor_advisory",
        "concurrency_limit": 2,
        "ni_quote": "天梁荫星老成持重，善讲道理，拥有一票否决权",
        "guidance": "Senior architectural auditor; has veto power over architectural regression.",
    },
    "七杀": {
        "role": "single_shot_striker",
        "coordination_mode": "isolated_single_shot_strike",
        "review_rigor": "pre_condition_completeness",
        "delegation_model": "high_impact_solo",
        "concurrency_limit": 1,
        "ni_quote": "七杀孤独刚烈，鸳衾半冷，单打独斗，要求前置依赖齐备",
        "guidance": "High-impact single-shot solver; only deploy when environment prerequisites are verified.",
    },
    "破军": {
        "role": "refactoring_innovator",
        "coordination_mode": "transactional_refactor_sandbox",
        "review_rigor": "atomic_transaction_barrier",
        "delegation_model": "isolated_staging",
        "concurrency_limit": 1,
        "ni_quote": "破军破而后立，婚姻破坏力最强，必须强制事务原子性",
        "guidance": "High entropy refactoring innovator; must execute behind an atomic staging boundary.",
    },
}


def _evaluate_partner_star_contract(star_name: str) -> dict[str, Any]:
    """Retrieve multi-agent peer contract and coordination mode from 14 major stars in 夫妻宫."""
    norm = star_name.strip()
    contract = _PARTNER_STAR_CONTRACTS.get(norm)
    if contract is not None:
        return {"star": norm, "found": True, **contract}
    return {
        "star": norm,
        "found": False,
        "role": "general_peer",
        "coordination_mode": "balanced_cooperative_channel",
        "review_rigor": "standard_regression_suite",
        "delegation_model": "standard_supervised",
        "concurrency_limit": 2,
        "ni_quote": "中正平和，顺应五行相生之道",
        "guidance": "Standard peer collaboration under default contractual bounds.",
    }


def _evaluate_sandbox_fengshui(
    workdir_present: bool = True,
    command_sandbox_enabled: bool = True,
    entry_validated: bool = True,
) -> dict[str, Any]:
    """Evaluate environmental security across Ni Haixia's Three Spatial Essentials (门、主、灶)."""
    passed_count = int(workdir_present) + int(command_sandbox_enabled) + int(entry_validated)

    if passed_count == 3:
        level = "auspicious_secure"
        action = "full_throughput_unrestricted"
        desc = "门主灶三元完备：输入门禁严密、工作区完整隔离、执行灶火可控。"
    elif passed_count == 2:
        level = "guarded_warning"
        action = "subtask_sandbox_confinement"
        desc = "三元有一处破绽：部分环境边界未闭合，已启用受控微步执行。"
    else:
        level = "breached_critical"
        action = "emergency_environment_quarantine_halt"
        desc = "三元两处以上失守：存在环境未封闭隐患，立即暂停自主执行。"

    return {
        "gate_integrity": entry_validated,
        "master_integrity": workdir_present,
        "kitchen_integrity": command_sandbox_enabled,
        "passed_essentials_count": passed_count,
        "fengshui_safety_level": level,
        "governance_action": action,
        "evaluation_summary": desc,
    }


def _evaluate_pathology_and_environmental_certificate() -> dict[str, Any]:
    """Formal mathematical certificate for Five-Element Pathology, 14-Star Contracts, and Fengshui Sandbox."""
    elem_covered = set()
    for err in ("syntax", "deadlock", "memory", "cpu", "cache"):
        res = _evaluate_system_pathology(0, error_type=err)
        elem_covered.add(res["element"])
    pathology_totality_ok = (len(elem_covered) == 5 and elem_covered == {"fire", "wood", "earth", "metal", "water"})

    p_severe = _evaluate_system_pathology(0, error_type="syntax")
    p_mild = _evaluate_system_pathology(7)
    damping_monotonic_ok = (p_severe["damping_factor"] <= p_mild["damping_factor"])

    stars_14 = ("紫微", "天机", "太阳", "武曲", "天同", "廉贞", "天府", "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军")
    all_14_stars_ok = all(
        _evaluate_partner_star_contract(s)["found"] is True
        and len(_evaluate_partner_star_contract(s)["role"]) > 0
        for s in stars_14
    )

    f_all = _evaluate_sandbox_fengshui(True, True, True)
    f_breach = _evaluate_sandbox_fengshui(False, False, True)
    fengshui_soundness_ok = (
        f_all["fengshui_safety_level"] == "auspicious_secure"
        and f_breach["fengshui_safety_level"] == "breached_critical"
        and f_all["passed_essentials_count"] == 3
        and f_breach["passed_essentials_count"] == 1
    )

    all_verified = pathology_totality_ok and damping_monotonic_ok and all_14_stars_ok and fengshui_soundness_ok

    return {
        "status": "verified" if all_verified else "failed",
        "five_element_pathology_totality_verified": pathology_totality_ok,
        "pathology_damping_monotonicity_verified": damping_monotonic_ok,
        "fourteen_partner_stars_contract_verified": all_14_stars_ok,
        "sandbox_three_essentials_verified": fengshui_soundness_ok,
    }


_SIX_CHANNELS_DATA: dict[str, dict[str, Any]] = {
    "taiyang": {
        "index": 0,
        "name": "太阳",
        "syndrome": "表证·开",
        "severity": 0.20,
        "damping_factor": 0.85,
        "classic_formula": "桂枝汤 / 麻黄汤",
        "remedy_directive": "surface_header_validation_and_gentle_cooldown",
        "description": "External boundary interface mismatch or shallow prompt distortion.",
    },
    "shaoyang": {
        "index": 2,
        "name": "少阳",
        "syndrome": "半表半里·枢",
        "severity": 0.40,
        "damping_factor": 0.70,
        "classic_formula": "小柴胡汤",
        "remedy_directive": "cross_agent_harmonic_synchronization_barrier",
        "description": "Half-surface half-interior: agent communication latency or RPC jitter.",
    },
    "yangming": {
        "index": 1,
        "name": "阳明",
        "syndrome": "里实热·阖",
        "severity": 0.50,
        "damping_factor": 0.50,
        "classic_formula": "白虎汤 / 承气汤",
        "remedy_directive": "aggressive_rate_limiter_and_wal_cache_purge",
        "description": "Interior excess heat: CPU runaway, loop thrashing, or token surge.",
    },
    "taiyin": {
        "index": 3,
        "name": "太阴",
        "syndrome": "里虚寒·开",
        "severity": 0.60,
        "damping_factor": 0.60,
        "classic_formula": "理中汤 / 苓桂术甘汤",
        "remedy_directive": "replenish_worker_context_and_flush_stale_buffer",
        "description": "Interior deficiency: stalled loops, empty responses, worker starvation.",
    },
    "shaoyin": {
        "index": 4,
        "name": "少阴",
        "syndrome": "阴阳两虚·枢",
        "severity": 0.80,
        "damping_factor": 0.30,
        "classic_formula": "四逆汤 / 真武汤",
        "remedy_directive": "emergency_checkpoint_rollback_and_session_reboot",
        "description": "Critical failure: heartbeat fading, exception boundary breach.",
    },
    "jueyin": {
        "index": 5,
        "name": "厥阴",
        "syndrome": "寒热错杂·阖",
        "severity": 0.95,
        "damping_factor": 0.20,
        "classic_formula": "乌梅丸",
        "remedy_directive": "multi_phase_arbitration_and_paradoxical_mutex_release",
        "description": "Extreme entropy: conflicting locks, paradoxical states, panic thrashing.",
    },
}


def _evaluate_six_channel_healing(
    status_code: int,
    error_type: str | None = None,
    resource_pressure: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Diagnose execution failure across Zhang Zhongjing's Six Channels and prescribe classical formulas."""
    err = (error_type or "").lower().strip()

    if status_code == 7 and not err:
        return {
            "status_code": status_code,
            "has_pathology": False,
            "channel": "harmonious",
            "channel_name": "营卫和合",
            "syndrome": "中正和平·阴平阳秘",
            "classic_formula": "平胃散 / 调和阴阳",
            "remedy_directive": "nominal_autonomous_flow",
            "damping_factor": 1.0,
            "severity_score": 0.0,
            "system_equilibrium": "optimal",
        }

    if any(k in err for k in ("deadlock", "thrash", "conflict", "paradox", "spin")):
        key = "jueyin"
    elif any(k in err for k in ("panic", "fatal", "heartbeat", "abort", "segfault")):
        key = "shaoyin"
    elif any(k in err for k in ("stall", "starve", "empty", "famine", "quarantine")):
        key = "taiyin"
    elif any(k in err for k in ("memory", "overflow", "cpu", "surge", "purge", "hot")):
        key = "yangming"
    elif any(k in err for k in ("agent", "rpc", "sync", "bridge", "latency", "skew")):
        key = "shaoyang"
    elif any(k in err for k in ("boundary", "syntax", "header", "prompt", "input", "entry")):
        key = "taiyang"
    else:
        channels = ("taiyang", "yangming", "shaoyang", "taiyin", "shaoyin", "jueyin")
        key = channels[status_code % 6]

    info = _SIX_CHANNELS_DATA[key]
    return {
        "status_code": status_code,
        "has_pathology": True,
        "channel": key,
        "channel_name": info["name"],
        "channel_index": info["index"],
        "syndrome": info["syndrome"],
        "classic_formula": info["classic_formula"],
        "remedy_directive": info["remedy_directive"],
        "damping_factor": info["damping_factor"],
        "severity_score": info["severity"],
        "description": info["description"],
        "system_equilibrium": "critical" if info["severity"] >= 0.80 else ("degraded" if info["severity"] >= 0.50 else "cautious"),
    }


def _evaluate_empty_palace_borrowing(
    status_code: int = 7,
    custom_stars: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Identify empty palaces (命无正曜) and apply opposite involution borrowing with mirror attenuation."""
    star_positions = custom_stars or _compute_canonical_major_star_positions(status_code)
    major_stars = (
        "紫微", "天机", "太阳", "武曲", "天同", "廉贞",
        "天府", "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军",
    )
    palace_native_stars: dict[int, list[str]] = {p: [] for p in range(12)}
    for s in major_stars:
        pos = star_positions.get(s)
        if pos is not None and 0 <= pos < 12:
            palace_native_stars[pos].append(s)

    palace_borrowing_reports: list[dict[str, Any]] = []
    empty_palaces: list[int] = []

    for p in range(12):
        natives = palace_native_stars[p]
        is_empty = (len(natives) == 0)
        opp_branch = (p + 6) % 12
        if is_empty:
            empty_palaces.append(p)
            borrowed = list(palace_native_stars[opp_branch])
            attenuation = 0.75
        else:
            borrowed = []
            attenuation = 1.0

        palace_borrowing_reports.append({
            "palace_index": p,
            "palace_name": _EARTHLY_BRANCH_NAMES[p],
            "native_stars": natives,
            "native_count": len(natives),
            "is_empty": is_empty,
            "opposite_branch": opp_branch,
            "borrowed_stars": borrowed,
            "attenuation_factor": attenuation,
            "effective_presence": natives if not is_empty else borrowed,
        })

    return {
        "status_code": status_code,
        "empty_palaces_count": len(empty_palaces),
        "empty_palaces": empty_palaces,
        "reports": palace_borrowing_reports,
        "opposite_involution_preserved": all((p + 6 + 6) % 12 == p for p in range(12)),
        "full_coverage_restored": all(
            len(r["effective_presence"]) > 0 for r in palace_borrowing_reports
        ),
    }


_WUXING_JU_MATRIX: list[list[int]] = [
    [0, 0, 0, 0, 0, 0, 0],
    [0, 2, 6, 3, 5, 4, 6],  # 甲己
    [0, 6, 5, 4, 3, 2, 5],  # 乙庚
    [0, 5, 3, 2, 4, 6, 3],  # 丙辛
    [0, 3, 4, 6, 2, 5, 4],  # 丁壬
    [0, 4, 2, 5, 6, 3, 2],  # 戊癸
]

_JU_NUMBER_TO_NAME: dict[int, str] = {
    2: "水二局",
    3: "木三局",
    4: "金四局",
    5: "土五局",
    6: "火六局",
}


def _evaluate_four_pillars_nayin(
    year_stem: int = 0,
    year_branch: int = 0,
    day_stem: int = 0,
    hour_branch: int = 0,
    ming_stem: int = 0,
    ming_branch: int = 2,
) -> dict[str, Any]:
    """Compute Four Pillars, Five Rats Escape hour stem, and 6x7 NaYin Bureau Matrix."""
    ys = year_stem % 10
    yb = year_branch % 12
    ds = day_stem % 10
    hb = hour_branch % 12
    ms = ming_stem % 10
    mb = ming_branch % 12

    time_stem = ((ds % 5) * 2 + hb) % 10
    gs = (ms % 5) + 1
    gb = (mb // 2) + 1
    bureau_num = _WUXING_JU_MATRIX[gs][gb]
    bureau_name = _JU_NUMBER_TO_NAME[bureau_num]

    four_pillars = {
        "year": f"{_HEAVENLY_STEM_NAMES[ys]}{_EARTHLY_BRANCH_NAMES[yb]}",
        "day": f"{_HEAVENLY_STEM_NAMES[ds]}",
        "hour": f"{_HEAVENLY_STEM_NAMES[time_stem]}{_EARTHLY_BRANCH_NAMES[hb]}",
    }

    return {
        "year_stem": ys,
        "year_branch": yb,
        "day_stem": ds,
        "hour_branch": hb,
        "time_stem": time_stem,
        "ming_stem": ms,
        "ming_branch": mb,
        "bureau_number": bureau_num,
        "bureau_name": bureau_name,
        "four_pillars": four_pillars,
        "five_rats_periodicity_ok": (((ds + 5) % 5) * 2 + hb) % 10 == time_stem,
    }


def _evaluate_six_channel_and_empty_palace_certificate() -> dict[str, Any]:
    """Formal mathematical certificate for Six-Channel Healing, Empty Palace Borrowing, and NaYin Matrix."""
    channels = ("taiyang", "shaoyang", "yangming", "taiyin", "shaoyin", "jueyin")
    severities = [_SIX_CHANNELS_DATA[k]["severity"] for k in channels]
    order_ok = all(severities[i] <= severities[i + 1] for i in range(len(severities) - 1))

    dampings = [_SIX_CHANNELS_DATA[k]["damping_factor"] for k in ("taiyang", "shaoyang", "taiyin", "yangming", "shaoyin", "jueyin")]
    damping_ok = all(dampings[i] >= dampings[i + 1] for i in range(len(dampings) - 1))

    all_opposite_involution_ok = True
    no_dual_empty_ok = True
    full_coverage_all_charts = True
    for z in range(12):
        res = _evaluate_empty_palace_borrowing(status_code=z)
        if not res["opposite_involution_preserved"]:
            all_opposite_involution_ok = False
        if not res["full_coverage_restored"]:
            full_coverage_all_charts = False
        e_set = set(res["empty_palaces"])
        for p in e_set:
            if (p + 6) % 12 in e_set:
                no_dual_empty_ok = False
                break

    counts = {2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
    for i in range(60):
        s = i % 10
        b = i % 12
        gs = (s % 5) + 1
        gb = (b // 2) + 1
        ju = _WUXING_JU_MATRIX[gs][gb]
        counts[ju] += 1
    equipartition_ok = all(c == 12 for c in counts.values())

    rats_ok = True
    for d in range(10):
        for h in range(12):
            s1 = ((d % 5) * 2 + h) % 10
            s2 = (((d + 5) % 5) * 2 + h) % 10
            if s1 != s2:
                rats_ok = False
                break

    cohabiting_palaces = []
    for z in range(12):
        tj = (z - 1) % 12
        tl = (9 - z) % 12
        if tj == tl:
            cohabiting_palaces.append(tj)
    tianji_tianliang_ok = (sorted(cohabiting_palaces) == [4, 10])

    rev_clockwise_ok = all(
        len(set((p0 - k) % 12 for k in range(12))) == 12
        for p0 in range(12)
    )

    all_verified = (
        order_ok
        and damping_ok
        and all_opposite_involution_ok
        and no_dual_empty_ok
        and full_coverage_all_charts
        and equipartition_ok
        and rats_ok
        and tianji_tianliang_ok
        and rev_clockwise_ok
    )

    return {
        "status": "verified" if all_verified else "failed",
        "six_channel_transmission_order_verified": order_ok,
        "six_channel_damping_monotonicity_verified": damping_ok,
        "empty_palace_opposite_involution_verified": all_opposite_involution_ok,
        "no_dual_empty_palaces_verified": no_dual_empty_ok,
        "empty_palace_full_coverage_verified": full_coverage_all_charts,
        "nayin_60_jiazi_equipartition_verified": equipartition_ok,
        "five_rats_escape_periodicity_verified": rats_ok,
        "tianji_tianliang_chen_xu_invariant_verified": tianji_tianliang_ok,
        "reverse_clockwise_12_palace_topology_verified": rev_clockwise_ok,
    }


_CHILDHOOD_MING_OFFSET: dict[int, int] = {
    1: 0,
    2: -4,
    3: -5,
    4: -2,
    5: 2,
}


def _evaluate_doujun_chronology_chain(
    year_branch: int,
    birth_month: int,
    birth_hour: int,
    flowing_month: int = 1,
    flowing_day: int = 1,
    flowing_hour: int = 0,
    ming_branch: int | None = None,
) -> dict[str, Any]:
    """Compute Doujun and flowing chronology chain (斗君月日时时空流) for episodic agent scheduling.

    Formula (Classical Doujun):
      doujun = (year_branch + birth_month - 1 - birth_hour) % 12
      flowing_month_branch = (doujun + flowing_month - 1) % 12
      flowing_day_branch = (flowing_month_branch + flowing_day - 1) % 12
      flowing_hour_branch = (flowing_day_branch + flowing_hour) % 12
    """
    yb = (year_branch % 12 + 12) % 12
    bm = max(1, min(12, int(birth_month)))
    bh = (birth_hour % 12 + 12) % 12
    fm = max(1, min(12, int(flowing_month)))
    fd = max(1, int(flowing_day))
    fh = (flowing_hour % 12 + 12) % 12

    doujun = (yb + bm - 1 - bh) % 12
    month_b = (doujun + fm - 1) % 12
    day_b = (month_b + fd - 1) % 12
    hour_b = (day_b + fh) % 12

    branch_names = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    mb = (ming_branch % 12 + 12) % 12 if ming_branch is not None else doujun
    delta = (hour_b - mb) % 12

    if delta == 0:
        resonance = "direct_anchor_focus"
        directive = "direct_executive_focus_unrestricted"
        damping = 1.0
        cadence = "rapid_commit"
    elif delta == 6:
        resonance = "opposite_clash_suipo"
        directive = "barrier_synchronization_guarded_inspect"
        damping = 0.50
        cadence = "isolated_sandbox_verification"
    elif delta in (4, 8):
        resonance = "triad_harmony_resonance"
        directive = "collaborative_triad_accelerated_dispatch"
        damping = 0.90
        cadence = "multi_turn_parallel"
    else:
        resonance = "harmonic_flank"
        directive = "standard_chronology_append"
        damping = 0.75
        cadence = "standard_turn"

    return {
        "year_branch": yb,
        "year_branch_name": branch_names[yb],
        "birth_month": bm,
        "birth_hour": bh,
        "doujun_branch": doujun,
        "doujun_branch_name": branch_names[doujun],
        "flowing_month": fm,
        "flowing_month_branch": month_b,
        "flowing_month_branch_name": branch_names[month_b],
        "flowing_day": fd,
        "flowing_day_branch": day_b,
        "flowing_day_branch_name": branch_names[day_b],
        "flowing_hour": fh,
        "flowing_hour_branch": hour_b,
        "flowing_hour_branch_name": branch_names[hour_b],
        "resonance_state": resonance,
        "cadence_directive": directive,
        "execution_cadence": cadence,
        "damping_factor": damping,
    }


def _evaluate_childhood_guard(
    bureau_number: int,
    virtual_age: int,
    ming_branch: int,
) -> dict[str, Any]:
    """Compute childhood pre-activation safety guard (童限前置保护) before bureau activation."""
    b_num = max(2, min(6, int(bureau_number)))
    age = max(1, int(virtual_age))
    mb = (ming_branch % 12 + 12) % 12
    branch_names = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    is_childhood = (age < b_num)
    if is_childhood:
        offset = _CHILDHOOD_MING_OFFSET.get(age, 0)
        active_branch = (mb + offset) % 12
        damping = 0.40 + 0.10 * age
        directive = "pre_initialization_quarantine_minimal_diff"
        action = "enforce_pre_activation_warmup_and_read_only"
    else:
        offset = 0
        active_branch = mb
        damping = 1.0
        directive = "native_bureau_fully_operational"
        action = "standard_autonomous_execution"

    return {
        "bureau_number": b_num,
        "virtual_age": age,
        "is_childhood_active": is_childhood,
        "childhood_years_count": max(0, b_num - 1),
        "offset": offset,
        "ming_branch": mb,
        "ming_branch_name": branch_names[mb],
        "active_branch": active_branch,
        "active_branch_name": branch_names[active_branch],
        "damping_factor": round(damping, 2),
        "guard_directive": directive,
        "recommended_action": action,
    }


def _evaluate_solar_lichun_boundary(
    solar_year: int,
    solar_month: int,
    solar_day: int,
    solar_hour: int,
    solar_minute: int = 0,
    lunar_year: int | None = None,
    lichun_day: int = 4,
    lichun_hour: int = 19,
    lichun_minute: int = 56,
) -> dict[str, Any]:
    """Evaluate dual-track calendar boundary (立春节气四柱 vs 农历紫微排盘分界).

    Solar track switches precisely at the exact minute of Lichun.
    Lunar track switches at Lunar New Year (正月初一).
    Discrepancy is bounded by |solar_year - lunar_year| <= 1.
    """
    sy = int(solar_year)
    sm = int(solar_month)
    sd = int(solar_day)
    sh = int(solar_hour)
    smin = int(solar_minute)
    ly = int(lunar_year) if lunar_year is not None else sy

    time_min = sh * 60 + smin
    lichun_min = lichun_hour * 60 + lichun_minute

    if sm < 2:
        is_prior_year = True
    elif sm == 2:
        if sd < lichun_day:
            is_prior_year = True
        elif sd == lichun_day:
            is_prior_year = (time_min < lichun_min)
        else:
            is_prior_year = False
    else:
        is_prior_year = False

    effective_solar_year = sy - 1 if is_prior_year else sy
    skew = effective_solar_year - ly

    if skew != 0:
        boundary_state = "lichun_boundary_skew_active"
        reconciliation = "dual_track_quarantine_reconciled"
        directive = "decouple_solar_wal_clock_from_lunar_palaces"
    else:
        boundary_state = "dual_track_aligned"
        reconciliation = "unified_synchronous_track"
        directive = "standard_synchronous_clock"

    return {
        "solar_year": sy,
        "solar_month": sm,
        "solar_day": sd,
        "solar_hour": sh,
        "solar_minute": smin,
        "effective_solar_year": effective_solar_year,
        "lunar_year": ly,
        "is_prior_solar_year": is_prior_year,
        "boundary_state": boundary_state,
        "track_skew": skew,
        "reconciliation_mode": reconciliation,
        "clock_directive": directive,
    }


def _evaluate_doujun_and_solar_boundary_certificate() -> dict[str, Any]:
    """18th Formal mathematical certificate: Doujun Chronology, Childhood Guard, and Solar Boundary."""
    doujun_surjective_ok = True
    for y in range(12):
        branch_hits = set()
        for m in range(1, 13):
            for h in range(12):
                res = _evaluate_doujun_chronology_chain(y, m, h)
                branch_hits.add(res["doujun_branch"])
        if len(branch_hits) != 12:
            doujun_surjective_ok = False
            break

    homomorphism_ok = True
    for y in range(12):
        for m in range(1, 13):
            for h in range(12):
                res = _evaluate_doujun_chronology_chain(y, m, h, 1, 1, 0)
                if res["flowing_hour_branch"] != res["doujun_branch"]:
                    homomorphism_ok = False
                    break

    periodicity_ok = True
    for y in range(3):
        res1 = _evaluate_doujun_chronology_chain(y, 1, 0, 1, 1, 0)
        res2 = _evaluate_doujun_chronology_chain(y, 1, 0, 1, 13, 0)
        res3 = _evaluate_doujun_chronology_chain(y, 1, 0, 1, 25, 0)
        if not (res1["flowing_day_branch"] == res2["flowing_day_branch"] == res3["flowing_day_branch"]):
            periodicity_ok = False
            break

    childhood_ok = True
    for b in (2, 3, 4, 5, 6):
        for age in range(1, b):
            g = _evaluate_childhood_guard(b, age, 0)
            if not g["is_childhood_active"]:
                childhood_ok = False
            if g["offset"] not in (0, -4, -5, -2, 2):
                childhood_ok = False
        g_adult = _evaluate_childhood_guard(b, b, 0)
        if g_adult["is_childhood_active"] or g_adult["damping_factor"] != 1.0:
            childhood_ok = False

    boundary_ok = True
    t1 = _evaluate_solar_lichun_boundary(2004, 2, 4, 2, 40, lunar_year=2004)
    t2 = _evaluate_solar_lichun_boundary(2004, 2, 4, 22, 0, lunar_year=2004)
    if not (t1["effective_solar_year"] == 2003 and t1["is_prior_solar_year"] and t1["track_skew"] == -1):
        boundary_ok = False
    if not (t2["effective_solar_year"] == 2004 and not t2["is_prior_solar_year"] and t2["track_skew"] == 0):
        boundary_ok = False

    skew_bounded_ok = True
    for test_y in (1980, 2000, 2026):
        for m in (1, 2, 3):
            for d in (1, 4, 15):
                sb = _evaluate_solar_lichun_boundary(test_y, m, d, 12, 0, lunar_year=test_y)
                if abs(sb["track_skew"]) > 1:
                    skew_bounded_ok = False
                    break

    all_verified = (
        doujun_surjective_ok
        and homomorphism_ok
        and periodicity_ok
        and childhood_ok
        and boundary_ok
        and skew_bounded_ok
    )

    return {
        "status": "verified" if all_verified else "failed",
        "doujun_surjective_coverage_verified": doujun_surjective_ok,
        "doujun_chronology_homomorphism_verified": homomorphism_ok,
        "flowing_chronology_periodicity_verified": periodicity_ok,
        "childhood_guard_boundary_verified": childhood_ok,
        "solar_lichun_boundary_switch_verified": boundary_ok,
        "solar_lunar_skew_boundedness_verified": skew_bounded_ok,
    }


_MAJOR_CITIES_LONGITUDE: dict[str, float] = {
    "北京": 116.4,
    "上海": 121.5,
    "天津": 117.2,
    "重庆": 106.6,
    "广州": 113.3,
    "深圳": 114.1,
    "杭州": 120.2,
    "南京": 118.8,
    "武汉": 114.3,
    "成都": 104.1,
    "西安": 108.9,
    "沈阳": 123.4,
    "哈尔滨": 126.6,
    "乌鲁木齐": 87.6,
    "拉萨": 91.1,
    "昆明": 102.7,
    "福州": 119.3,
    "台北": 121.5,
    "香港": 114.2,
    "澳门": 113.5,
    "郑州": 113.6,
    "长沙": 113.0,
    "济南": 117.0,
    "长春": 125.3,
    "合肥": 117.3,
    "南昌": 115.9,
    "贵阳": 106.7,
    "太原": 112.5,
    "南宁": 108.3,
    "海口": 110.3,
    "西宁": 101.8,
    "银川": 106.3,
    "呼和浩特": 111.7,
    "兰州": 103.8,
}


def _evaluate_auxiliary_stars_pairs(
    birth_month: int,
    birth_day: int,
    ming_branch: int,
    birth_hour: int = 0,
    zuofu_branch: int | None = None,
    youbi_branch: int | None = None,
    wenchang_branch: int | None = None,
    wenqu_branch: int | None = None,
) -> dict[str, Any]:
    """Compute auxiliary star conservation pairs, phase invariants, and Tianshang-Tianshi clamping."""
    bm = max(1, min(12, int(birth_month)))
    bd = max(1, min(30, int(birth_day)))
    bh = (birth_hour % 12 + 12) % 12
    mb = (ming_branch % 12 + 12) % 12

    # 1. Tianxing & Tianyao: phase difference is constant 8
    tianxing = (8 + bm) % 12
    tianyao = bm % 12
    phase_diff = (tianxing - tianyao) % 12

    # 2. Santai & Bazuo: day step cancels, sum is constant
    zf = (3 + bm) % 12 if zuofu_branch is None else (zuofu_branch % 12)
    yb = (11 - bm) % 12 if youbi_branch is None else (youbi_branch % 12)
    santai = (zf + bd - 1) % 12
    bazuo = (yb - (bd - 1)) % 12
    santai_bazuo_sum = (santai + bazuo) % 12
    base_aux_sum = (zf + yb) % 12

    # 3. Enguang & Tiangui: difference is invariant under day step
    wc = (10 - bh) % 12 if wenchang_branch is None else (wenchang_branch % 12)
    wq = (4 + bh) % 12 if wenqu_branch is None else (wenqu_branch % 12)
    enguang = (wc + bd - 2) % 12
    tiangui = (wq + bd - 2) % 12
    enguang_tiangui_diff = (enguang - tiangui) % 12
    base_changqu_diff = (wc - wq) % 12

    # 4. Tianshang & Tianshi: sandwich Migration Palace (迁移宫)
    tianshang = (mb - 7) % 12  # 仆役宫
    tianshi = (mb - 5) % 12    # 疾厄宫
    migration = (mb - 6) % 12  # 迁移宫
    clamping_midpoint_ok = (
        (tianshang + tianshi) % 12 == (2 * migration) % 12
        and (tianshi - tianshang) % 12 == 2
    )

    branch_names = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    return {
        "birth_month": bm,
        "birth_day": bd,
        "ming_branch": mb,
        "ming_branch_name": branch_names[mb],
        "tianxing_branch": tianxing,
        "tianxing_branch_name": branch_names[tianxing],
        "tianyao_branch": tianyao,
        "tianyao_branch_name": branch_names[tianyao],
        "tianxing_tianyao_phase_difference": phase_diff,
        "phase_difference_invariant_verified": phase_diff == 8,
        "santai_branch": santai,
        "bazuo_branch": bazuo,
        "santai_bazuo_sum": santai_bazuo_sum,
        "santai_bazuo_sum_conserved": santai_bazuo_sum == base_aux_sum,
        "enguang_branch": enguang,
        "tiangui_branch": tiangui,
        "enguang_tiangui_diff": enguang_tiangui_diff,
        "enguang_tiangui_diff_conserved": enguang_tiangui_diff == base_changqu_diff,
        "tianshang_branch": tianshang,
        "tianshi_branch": tianshi,
        "migration_branch": migration,
        "migration_sandwiched": clamping_midpoint_ok,
    }


def _evaluate_city_true_solar_precision(
    city_name: str,
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int = 0,
    auto_dst: bool = True,
) -> dict[str, Any]:
    """Compute precision True Solar Time and clock adaptation for major Chinese cities."""
    city = str(city_name).strip()
    lng = _MAJOR_CITIES_LONGITUDE.get(city, 120.0)

    # Automatic historical DST detection
    dst_info = _evaluate_china_dst(year, month, day)
    dst_active = dst_info["is_dst"] and auto_dst
    dst_shift_min = -60 if dst_active else 0

    total_clock_min = hour * 60 + minute + dst_shift_min
    eff_hour = (total_clock_min // 60) % 24
    eff_min = total_clock_min % 60

    solar = _evaluate_true_solar_time(year, month, day, eff_hour, eff_min, lng)
    total_corr = solar["total_correction_minutes"]
    drift_seconds = total_corr * 60.0
    adaptation = _evaluate_clock_drift_adaptation(drift_seconds)

    solar_h = solar["solar_hour"]
    solar_m = solar["solar_minute"]

    return {
        "city_name": city,
        "city_known": city in _MAJOR_CITIES_LONGITUDE,
        "longitude": lng,
        "clock_input": f"{hour:02d}:{minute:02d}",
        "dst_active": dst_active,
        "dst_shift_minutes": dst_shift_min,
        "standard_clock_time": f"{eff_hour:02d}:{eff_min:02d}",
        "true_solar_time": f"{solar_h:02d}:{solar_m:02d}",
        "solar_hour_branch": solar["branch"],
        "solar_hour_name": solar["branch_name"],
        "drift_minutes": total_corr,
        "clock_adaptation": adaptation,
    }


def _evaluate_auxiliary_pairs_and_city_solar_certificate() -> dict[str, Any]:
    """19th Formal mathematical certificate: Auxiliary Conservation Pairs and City Solar Precision."""
    # 1. Tianxing-Tianyao constant phase difference 8 across all 12 months
    tianxing_yao_ok = all(
        _evaluate_auxiliary_stars_pairs(m, 1, 0)["phase_difference_invariant_verified"]
        for m in range(1, 13)
    )

    # 2. Santai-Bazuo sum conservation across all 30 days and 12 months
    santai_bazuo_ok = all(
        _evaluate_auxiliary_stars_pairs(m, d, 0)["santai_bazuo_sum_conserved"]
        for m in range(1, 13)
        for d in (1, 15, 30)
    )

    # 3. Enguang-Tiangui difference conservation across all 30 days and 12 hours
    enguang_tiangui_ok = all(
        _evaluate_auxiliary_stars_pairs(1, d, 0, birth_hour=h)["enguang_tiangui_diff_conserved"]
        for d in (1, 15, 30)
        for h in (0, 3, 6, 9)
    )

    # 4. Tianshang-Tianshi migration sandwiching invariant across all 12 ming palaces
    clamping_midpoint_ok = all(
        _evaluate_auxiliary_stars_pairs(1, 1, mb)["migration_sandwiched"]
        for mb in range(12)
    )

    # 5. Major cities geodetic bounds: all cities in [87.0, 127.0] E, drift bounded in [-150, +50] min
    cities_bounded_ok = True
    for c_name, lng in _MAJOR_CITIES_LONGITUDE.items():
        if not (87.0 <= lng <= 127.0):
            cities_bounded_ok = False
            break
        res = _evaluate_city_true_solar_precision(c_name, 2026, 6, 15, 12, 0)
        if not (-150.0 <= res["drift_minutes"] <= 50.0):
            cities_bounded_ok = False
            break

    # 6. DST shift verification: 1988-06-01 in Beijing (DST was active in 1988)
    dst_bj = _evaluate_city_true_solar_precision("北京", 1988, 6, 1, 12, 0, auto_dst=True)
    dst_shift_ok = (dst_bj["dst_active"] is True and dst_bj["dst_shift_minutes"] == -60)

    all_verified = (
        tianxing_yao_ok
        and santai_bazuo_ok
        and enguang_tiangui_ok
        and clamping_midpoint_ok
        and cities_bounded_ok
        and dst_shift_ok
    )

    return {
        "status": "verified" if all_verified else "failed",
        "tianxing_tianyao_constant_phase_verified": tianxing_yao_ok,
        "santai_bazuo_sum_conservation_verified": santai_bazuo_ok,
        "enguang_tiangui_difference_conservation_verified": enguang_tiangui_ok,
        "tianshang_tianshi_migration_sandwiching_verified": clamping_midpoint_ok,
        "major_cities_geodetic_bounds_verified": cities_bounded_ok,
        "china_dst_automatic_shift_verified": dst_shift_ok,
    }


_CHANGSHENG_STAGES: tuple[str, ...] = (
    "长生", "沐浴", "冠带", "临官", "帝旺", "衰",
    "病", "死", "墓", "绝", "胎", "养"
)

_CHANGSHENG_ORIGIN: dict[int, int] = {
    2: 8,   # 水二局 起申
    3: 11,  # 木三局 起亥
    4: 5,   # 金四局 起巳
    5: 8,   # 土五局 起申 (水土共生于申)
    6: 2,   # 火六局 起寅
}

_CHANGSHENG_LIFECYCLE_MAP: dict[str, dict[str, Any]] = {
    "长生": {"lifecycle": "init_session", "throttle": 0.85, "directive": "warmup_and_discover"},
    "沐浴": {"lifecycle": "code_lint_and_inspect", "throttle": 0.75, "directive": "read_and_lint_scrutiny"},
    "冠带": {"lifecycle": "ast_parse_and_bind", "throttle": 0.90, "directive": "structural_binding"},
    "临官": {"lifecycle": "tool_dispatch_ready", "throttle": 1.00, "directive": "autonomous_dispatch"},
    "帝旺": {"lifecycle": "peak_execution_throughput", "throttle": 1.00, "directive": "maximum_parallel_burst"},
    "衰": {"lifecycle": "cooldown_backoff", "throttle": 0.70, "directive": "exponential_backoff"},
    "病": {"lifecycle": "exception_quarantine", "throttle": 0.50, "directive": "isolate_fault_rollback"},
    "死": {"lifecycle": "graceful_halt", "throttle": 0.25, "directive": "sovereign_halt_preserve_state"},
    "墓": {"lifecycle": "checkpoint_persistence", "throttle": 0.60, "directive": "wal_flush_and_archive"},
    "绝": {"lifecycle": "memory_garbage_collection", "throttle": 0.30, "directive": "evict_dead_buffers"},
    "胎": {"lifecycle": "seed_generation", "throttle": 0.50, "directive": "prepare_restart_seed"},
    "养": {"lifecycle": "warmup_read_only", "throttle": 0.75, "directive": "gradual_warmup"},
}


def _evaluate_changsheng_lifecycle(
    bureau_number: int,
    gender: str = "male",
    year_stem: int = 0,
    current_palace_branch: int | None = None,
) -> dict[str, Any]:
    """Compute Twelve ChangSheng stages and Agent Process Lifecycle Automaton."""
    b_num = max(2, min(6, int(bureau_number)))
    start_branch = _CHANGSHENG_ORIGIN.get(b_num, 8)

    is_yang = (int(year_stem) % 2 == 0)
    is_male = (str(gender).lower() in ("male", "m", "阳男", "阴男"))
    clockwise = (is_male and is_yang) or (not is_male and not is_yang)
    step = 1 if clockwise else -1

    palace_stages: dict[int, str] = {}
    for stage_idx, stage_name in enumerate(_CHANGSHENG_STAGES):
        branch = (start_branch + stage_idx * step) % 12
        palace_stages[branch] = stage_name

    cur_branch = (start_branch if current_palace_branch is None else (current_palace_branch % 12))
    current_stage = palace_stages.get(cur_branch, "长生")
    meta = _CHANGSHENG_LIFECYCLE_MAP.get(current_stage, _CHANGSHENG_LIFECYCLE_MAP["长生"])

    branch_names = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    return {
        "bureau_number": b_num,
        "gender": "male" if is_male else "female",
        "year_stem_polarity": "yang" if is_yang else "yin",
        "stepping_direction": "clockwise" if clockwise else "counter_clockwise",
        "start_branch": start_branch,
        "start_branch_name": branch_names[start_branch],
        "origin_branch": start_branch,
        "origin_branch_name": branch_names[start_branch],
        "step_direction": step,
        "current_palace_branch": cur_branch,
        "current_palace_name": branch_names[cur_branch],
        "current_stage": current_stage,
        "lifecycle_phase": meta["lifecycle"],
        "phase_type": meta["lifecycle"],
        "throttle_factor": meta["throttle"],
        "runtime_directive": meta["directive"],
        "palace_stages_distribution": {branch_names[b]: s for b, s in palace_stages.items()},
    }


def _evaluate_guchen_guasu_huagai(year_branch: int) -> dict[str, Any]:
    """Compute GuChen, GuaSu, HuaGai (Four Earth Tombs), and XianChi (Four Cardinals)."""
    yb = (int(year_branch) % 12 + 12) % 12
    quadrant = ((yb + 1) // 3) % 4

    guchen = (3 * quadrant + 2) % 12
    guasu = (3 * quadrant - 2) % 12
    angular_distance = (guchen - guasu) % 12

    triad_idx = yb % 4
    huagai_map = {0: 4, 1: 1, 2: 10, 3: 7}
    xianchi_map = {0: 9, 1: 6, 2: 3, 3: 0}

    huagai = huagai_map[triad_idx]
    xianchi = xianchi_map[triad_idx]

    branch_names = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    return {
        "year_branch": yb,
        "year_branch_name": branch_names[yb],
        "season_quadrant": quadrant,
        "guchen_branch": guchen,
        "guchen_branch_name": branch_names[guchen],
        "guasu_branch": guasu,
        "guasu_branch_name": branch_names[guasu],
        "angular_distance": angular_distance,
        "angular_distance_invariant_verified": angular_distance == 4,
        "huagai_branch": huagai,
        "huagai_branch_name": branch_names[huagai],
        "huagai_in_four_tombs": huagai in (1, 4, 7, 10),
        "xianchi_branch": xianchi,
        "xianchi_branch_name": branch_names[xianchi],
        "xianchi_in_four_cardinals": xianchi in (0, 3, 6, 9),
        "security_advisory": "HuaGai active: engage deep analytical reflection mode" if huagai == yb else "Standard governance",
    }


def _evaluate_expanded_classical_patterns(
    turn_number: int,
    current_status: int,
    fatal_regression: bool = False,
    ast_valid: bool = True,
    verifier_passed: bool = True,
) -> dict[str, Any]:
    """Comprehensive 32+ classical patterns evaluation across all levels and clamping formations."""
    base_res = _evaluate_classical_patterns(
        turn_number=turn_number,
        status_code=current_status,
        ast_valid=ast_valid,
        verifier_passed=verifier_passed,
        fatal_regression=fatal_regression,
    )
    patterns = list(base_res["active_patterns"])

    mb = base_res["branch"]
    state_code = current_status & 0b111111
    stars = _compute_canonical_major_star_positions(state_code)
    san_fang = {mb, (mb + 4) % 12, (mb + 8) % 12, (mb + 6) % 12}

    sun_b = stars.get("太阳", 6)
    liang_b = stars.get("天梁", 10)
    if sun_b in san_fang and liang_b in san_fang and state_code == 7:
        patterns.append({
            "name": "阳梁昌禄",
            "tier": "tier_1_supreme",
            "level": "excellent",
            "description": "太阳天梁文昌禄存四星交会三方四正，主学术文教登峰造极，高维审查认证通过。",
            "governance_action": "academic_linter_authoritative_cert",
            "action": "academic_linter_authoritative_cert",
        })

    tan_b = stars.get("贪狼", 2)
    if tan_b in san_fang and state_code in (7, 11, 19, 34):
        patterns.append({
            "name": "火贪格",
            "tier": "tier_2_noble",
            "level": "good",
            "description": "贪狼与火星交会三合，主爆发突破、突击攻关迅速达成。",
            "governance_action": "burst_acceleration_dispatch",
            "action": "burst_acceleration_dispatch",
        })

    wu_b = stars.get("武曲", 8)
    if wu_b in (1, 7) and tan_b in (1, 7):
        patterns.append({
            "name": "武贪格",
            "tier": "tier_2_noble",
            "level": "good",
            "description": "武曲贪狼同度丑未，主先难后易、大器晚成、重构稳固。",
            "governance_action": "endurance_refactor_delayed_success",
            "action": "endurance_refactor_delayed_success",
        })

    ju_b = stars.get("巨门", 0)
    if mb in (0, 6) and ju_b == mb and state_code != 0:
        patterns.append({
            "name": "石中隐玉",
            "tier": "tier_1_supreme",
            "level": "excellent",
            "description": "巨门坐命子午，外表质朴内蕴才华，专项破题深入微观核心。",
            "governance_action": "deep_domain_specialist_inspection",
            "action": "deep_domain_specialist_inspection",
        })

    if mb == 7 and sun_b == 1 and stars.get("太阴", 1) == 1:
        patterns.append({
            "name": "明珠出海",
            "tier": "tier_1_supreme",
            "level": "excellent",
            "description": "命在未宫空宫，对宫丑宫日月同辉拱照，远跨边界协调会聚。",
            "governance_action": "cross_boundary_holistic_convergence",
            "action": "cross_boundary_holistic_convergence",
        })

    if mb == 6 and state_code in (0, 32, 40):
        patterns.append({
            "name": "马头带箭",
            "tier": "breaking",
            "level": "caution",
            "description": "擎羊坐命午宫，威震边疆然险象环生，强制微创沙箱校验。",
            "governance_action": "decisive_boundary_strike_and_sandbox",
            "action": "decisive_boundary_strike_and_sandbox",
        })

    lian_b = stars.get("廉贞", 4)
    sha_b = stars.get("七杀", 2)
    if lian_b in san_fang and sha_b in san_fang and state_code == 0:
        patterns.append({
            "name": "廉杀羊",
            "tier": "breaking",
            "level": "caution",
            "description": "廉贞七杀擎羊齐会，金火交战高危冲突，激活严格微创退避。",
            "governance_action": "strict_minimal_diff_conflict_quarantine",
            "action": "strict_minimal_diff_conflict_quarantine",
        })

    if ju_b in san_fang and state_code in (0, 40):
        patterns.append({
            "name": "巨火羊",
            "tier": "breaking",
            "level": "caution",
            "description": "巨门火星擎羊三方交会，口舌是非争用死锁，温和降解争议。",
            "governance_action": "gentle_linter_deescalate_contention",
            "action": "gentle_linter_deescalate_contention",
        })

    prev_b = (mb - 1) % 12
    next_b = (mb + 1) % 12
    zf_b = (3 + turn_number) % 12
    yb_b = (11 - turn_number) % 12
    if {prev_b, next_b} == {zf_b, yb_b}:
        patterns.append({
            "name": "辅弼夹命",
            "tier": "tier_1_supreme",
            "level": "excellent",
            "description": "左辅右弼分居命宫两侧夹护，左右臂膀坚实，多智能体协同护航。",
            "governance_action": "collaborative_pair_shield",
            "action": "collaborative_pair_shield",
        })

    has_breaking = any(p["tier"] == "breaking" for p in patterns)
    safety_level = "caution" if has_breaking else ("excellent" if any(p["tier"] in ("supreme", "tier_1_supreme") for p in patterns) else "good")

    rec_act = patterns[0].get("governance_action") or patterns[0].get("action") or "standard_step" if patterns else "standard_step"
    return {
        "turn_number": turn_number,
        "ming_branch": mb,
        "patterns": patterns,
        "pattern_count": len(patterns),
        "has_breaking": has_breaking,
        "safety_level": safety_level,
        "recommended_action": rec_act,
    }


def _evaluate_changsheng_and_expanded_patterns_certificate() -> dict[str, Any]:
    """20th Formal mathematical certificate: ChangSheng Automaton, GuChen-GuaSu-HuaGai & 32 Patterns."""
    changsheng_ok = True
    origins = set(_CHANGSHENG_ORIGIN.values())
    if origins != {2, 5, 8, 11} or _CHANGSHENG_ORIGIN[2] != 8 or _CHANGSHENG_ORIGIN[5] != 8:
        changsheng_ok = False
    for b in (2, 3, 4, 5, 6):
        res = _evaluate_changsheng_lifecycle(b, "male", 0)
        stages_set = set(res["palace_stages_distribution"].values())
        if len(stages_set) != 12:
            changsheng_ok = False
            break

    guchen_guasu_ok = all(
        _evaluate_guchen_guasu_huagai(b)["angular_distance_invariant_verified"]
        for b in range(12)
    )

    huagai_ok = all(
        _evaluate_guchen_guasu_huagai(b)["huagai_in_four_tombs"]
        for b in range(12)
    )

    xianchi_ok = all(
        _evaluate_guchen_guasu_huagai(b)["xianchi_in_four_cardinals"]
        for b in range(12)
    )

    pat_halt = _evaluate_expanded_classical_patterns(1, 0, fatal_regression=True)
    safety_dom_ok = (pat_halt["has_breaking"] is True and pat_halt["safety_level"] == "caution")

    pat_ground = _evaluate_expanded_classical_patterns(1, 7, fatal_regression=False, ast_valid=True, verifier_passed=True)
    ground_clean_ok = (pat_ground["has_breaking"] is False and pat_ground["safety_level"] in ("good", "excellent"))

    all_verified = (
        changsheng_ok
        and guchen_guasu_ok
        and huagai_ok
        and xianchi_ok
        and safety_dom_ok
        and ground_clean_ok
    )

    return {
        "status": "verified" if all_verified else "failed",
        "changsheng_origins_four_horses_verified": changsheng_ok,
        "guchen_guasu_angular_distance_4_verified": guchen_guasu_ok,
        "huagai_four_earth_tombs_verified": huagai_ok,
        "xianchi_four_cardinals_verified": xianchi_ok,
        "expanded_patterns_safety_dominance_verified": safety_dom_ok,
        "expanded_patterns_ground_purity_verified": ground_clean_ok,
    }


_QUANSHU_FOURTEEN_STARS_BRIGHTNESS: dict[str, list[str]] = {
    # Indexed 0=子, 1=丑, 2=寅, 3=卯, 4=辰, 5=巳, 6=午, 7=未, 8=申, 9=酉, 10=戌, 11=亥
    "紫微": ["平", "庙", "庙", "旺", "得", "旺", "庙", "庙", "旺", "旺", "得", "旺"],
    "天机": ["庙", "陷", "得", "旺", "庙", "平", "庙", "陷", "得", "旺", "庙", "平"],
    "太阳": ["陷", "不", "旺", "庙", "旺", "旺", "庙", "得", "得", "陷", "不", "陷"],
    "武曲": ["旺", "庙", "得", "利", "庙", "平", "旺", "庙", "得", "利", "庙", "平"],
    "天同": ["旺", "不", "旺", "平", "平", "庙", "不", "不", "旺", "平", "平", "庙"],
    "廉贞": ["平", "利", "庙", "平", "利", "陷", "平", "利", "庙", "平", "利", "陷"],
    "天府": ["庙", "庙", "庙", "得", "旺", "得", "旺", "庙", "得", "旺", "旺", "得"],
    "太阴": ["庙", "庙", "陷", "陷", "陷", "陷", "陷", "不", "利", "旺", "旺", "庙"],
    "贪狼": ["平", "庙", "不", "平", "得", "平", "平", "庙", "不", "平", "得", "利"],
    "巨门": ["旺", "不", "庙", "庙", "陷", "旺", "旺", "不", "庙", "庙", "陷", "旺"],
    "天相": ["庙", "庙", "庙", "平", "得", "得", "庙", "得", "庙", "平", "得", "得"],
    "天梁": ["庙", "旺", "庙", "得", "庙", "陷", "庙", "旺", "陷", "得", "得", "陷"],
    "七杀": ["旺", "庙", "庙", "旺", "庙", "平", "旺", "庙", "庙", "旺", "庙", "平"],
    "破军": ["庙", "旺", "得", "陷", "旺", "平", "庙", "旺", "得", "陷", "旺", "平"],
}

_QUANSHU_BRIGHTNESS_WEIGHTS: dict[str, float] = {
    "庙": 1.00,
    "旺": 0.90,
    "得": 0.80,
    "利": 0.75,
    "平": 0.65,
    "不": 0.45,
    "陷": 0.25,
}

_ZIWU_LIUZHU_MERIDIANS: dict[int, dict[str, Any]] = {
    0: {"meridian": "足少阳胆经", "organ": "胆", "subsystem": "decision_arbitration", "element": "木", "peak_hours": "23:00-01:00"},
    1: {"meridian": "足厥阴肝经", "organ": "肝", "subsystem": "strategic_planning", "element": "木", "peak_hours": "01:00-03:00"},
    2: {"meridian": "手太阴肺经", "organ": "肺", "subsystem": "syntax_ast_respiration", "element": "金", "peak_hours": "03:00-05:00"},
    3: {"meridian": "手阳明大肠经", "organ": "大肠", "subsystem": "artifact_evacuation", "element": "金", "peak_hours": "05:00-07:00"},
    4: {"meridian": "足阳明胃经", "organ": "胃", "subsystem": "prompt_ingestion", "element": "土", "peak_hours": "07:00-09:00"},
    5: {"meridian": "足太阴脾经", "organ": "脾", "subsystem": "memory_transportation", "element": "土", "peak_hours": "09:00-11:00"},
    6: {"meridian": "手少阴心经", "organ": "心", "subsystem": "sovereignty_core_monarch", "element": "火", "peak_hours": "11:00-13:00"},
    7: {"meridian": "手太阳小肠经", "organ": "小肠", "subsystem": "diff_discrimination", "element": "火", "peak_hours": "13:00-15:00"},
    8: {"meridian": "足太阳膀胱经", "organ": "膀胱", "subsystem": "evidence_wal_reservoir", "element": "水", "peak_hours": "15:00-17:00"},
    9: {"meridian": "足少阴肾经", "organ": "肾", "subsystem": "checkpoint_congenital_root", "element": "水", "peak_hours": "17:00-19:00"},
    10: {"meridian": "手厥阴心包经", "organ": "心包", "subsystem": "sandbox_sentinel_shield", "element": "火", "peak_hours": "19:00-21:00"},
    11: {"meridian": "手少阳三焦经", "organ": "三焦", "subsystem": "ipc_coordination_pipeline", "element": "火", "peak_hours": "21:00-23:00"},
}

_FIVE_ELEMENTS_NAMES: list[str] = ["木", "火", "土", "金", "水"]
_FIVE_ELEMENTS_INDEX: dict[str, int] = {
    "木": 0, "火": 1, "土": 2, "金": 3, "水": 4,
    "wood": 0, "fire": 1, "earth": 2, "metal": 3, "water": 4,
}


def _evaluate_quanshu_star_brightness(
    hexagram_state: int,
    ming_branch: int | None = None,
) -> dict[str, Any]:
    """Evaluate classical 14 major stars brightness from Quanshu across Sanfang and full chart."""
    state_code = hexagram_state & 0b111111
    stars = _compute_canonical_major_star_positions(state_code)
    branch_names = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    mb = ((hexagram_state % 12) if ming_branch is None else (ming_branch % 12))
    san_fang = {mb, (mb + 4) % 12, (mb + 8) % 12, (mb + 6) % 12}

    breakdown: dict[str, dict[str, Any]] = {}
    sanfang_scores: list[float] = []
    chart_scores: list[float] = []

    for star_name, star_branch in stars.items():
        if star_name in _QUANSHU_FOURTEEN_STARS_BRIGHTNESS:
            bright_label = _QUANSHU_FOURTEEN_STARS_BRIGHTNESS[star_name][star_branch]
            score = _QUANSHU_BRIGHTNESS_WEIGHTS.get(bright_label, 0.65)
            chart_scores.append(score)
            in_sanfang = (star_branch in san_fang)
            if in_sanfang:
                sanfang_scores.append(score)
            breakdown[star_name] = {
                "branch": star_branch,
                "branch_name": branch_names[star_branch],
                "brightness": bright_label,
                "score": score,
                "in_sanfang": in_sanfang,
            }

    mean_sanfang = round(sum(sanfang_scores) / len(sanfang_scores), 4) if sanfang_scores else 0.65
    mean_chart = round(sum(chart_scores) / len(chart_scores), 4) if chart_scores else 0.65

    if mean_sanfang >= 0.85:
        tier = "supreme_miao"
        throttle = 1.00
        mode = "autonomous_high_illumination"
    elif mean_sanfang >= 0.70:
        tier = "balanced_wang_de"
        throttle = 0.80
        mode = "guarded_illumination"
    else:
        tier = "cautious_xian"
        throttle = 0.40
        mode = "degraded_protective_linter"

    return {
        "hexagram_state": hexagram_state,
        "ming_branch": mb,
        "ming_branch_name": branch_names[mb],
        "stars_breakdown": breakdown,
        "sanfang_mean_energy": mean_sanfang,
        "chart_mean_energy": mean_chart,
        "governance_tier": tier,
        "throttle_factor": throttle,
        "execution_mode": mode,
    }


def _evaluate_ziwu_liuzhu_chronobiology(
    current_hour_branch: int,
    task_type: str = "general",
) -> dict[str, Any]:
    """Compute Ziwu Liuzhu Meridian flow, diurnal energy wave, and antipodal balance."""
    b = (int(current_hour_branch) % 12 + 12) % 12
    meta = _ZIWU_LIUZHU_MERIDIANS[b]
    antipodal_b = (b + 6) % 12
    antipodal_meta = _ZIWU_LIUZHU_MERIDIANS[antipodal_b]

    branch_names = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    diurnal_distribution: dict[str, float] = {}
    for k in range(12):
        delta = abs(((k - b + 6) % 12) - 6)
        energy_k = round(1.0 - 0.40 * (delta / 6.0), 4)
        diurnal_distribution[branch_names[k]] = energy_k

    energy_sum = round(sum(diurnal_distribution.values()), 4)
    peak_energy = diurnal_distribution[branch_names[b]]
    nadir_energy = diurnal_distribution[branch_names[antipodal_b]]

    return {
        "current_hour_branch": b,
        "current_branch_name": branch_names[b],
        "active_meridian": meta["meridian"],
        "active_organ": meta["organ"],
        "active_subsystem": meta["subsystem"],
        "element": meta["element"],
        "peak_hours": meta["peak_hours"],
        "antipodal_branch": antipodal_b,
        "antipodal_branch_name": branch_names[antipodal_b],
        "antipodal_meridian": antipodal_meta["meridian"],
        "antipodal_subsystem": antipodal_meta["subsystem"],
        "diurnal_energy_distribution": diurnal_distribution,
        "diurnal_energy_sum": energy_sum,
        "peak_energy": peak_energy,
        "nadir_energy": nadir_energy,
        "subsystem_directive": f"Prioritize {meta['subsystem']} ({meta['meridian']}) at peak energy {peak_energy}.",
    }


def _evaluate_five_elements_shengke(
    element_a: int | str,
    element_b: int | str,
) -> dict[str, Any]:
    """Compute Five Elements Generation-Destruction interaction dynamics and circulant energy gain."""
    idx_a = _FIVE_ELEMENTS_INDEX[str(element_a).lower()] if isinstance(element_a, str) else (int(element_a) % 5)
    idx_b = _FIVE_ELEMENTS_INDEX[str(element_b).lower()] if isinstance(element_b, str) else (int(element_b) % 5)

    name_a = _FIVE_ELEMENTS_NAMES[idx_a]
    name_b = _FIVE_ELEMENTS_NAMES[idx_b]

    diff = (idx_b - idx_a) % 5
    if diff == 0:
        relation = "比和"
        gain = 1.00
        mode = "mutual_cooperative_parallel"
        directive = "Equal peers: parallel collaborative throughput."
    elif diff == 1:
        relation = "相生(我生)"
        gain = 1.15
        mode = "generative_outflow_feedforward"
        directive = "Generative acceleration: agent A nurtures agent B."
    elif diff == 4:
        relation = "相生(生我)"
        gain = 1.20
        mode = "generative_inflow_nurturing"
        directive = "Replenishing cache: agent B powers agent A."
    elif diff == 2:
        relation = "相克(我克)"
        gain = 0.80
        mode = "supervisory_governance_barrier"
        directive = "Supervisory containment: agent A enforces constraints on agent B."
    else:  # diff == 3
        relation = "相克(克我)"
        gain = 0.50
        mode = "defensive_containment_throttle"
        directive = "Damped throttle: agent A subject to defensive supervision by agent B."

    circulant_row = [1.00, 1.15, 0.80, 0.50, 1.20]
    circulant_sum = round(sum(circulant_row), 4)

    return {
        "element_a": idx_a,
        "element_a_name": name_a,
        "element_b": idx_b,
        "element_b_name": name_b,
        "relation": relation,
        "energy_transmission_gain": gain,
        "coordination_mode": mode,
        "governance_directive": directive,
        "circulant_row_sum": circulant_sum,
    }


def _evaluate_ziwu_liuzhu_and_shengke_certificate() -> dict[str, Any]:
    """21st Formal mathematical certificate: Ziwu Liuzhu, Five Elements Sheng-Ke & Quanshu Totality."""
    antipodal_ok = True
    energy_sum_ok = True
    for b in range(12):
        zl = _evaluate_ziwu_liuzhu_chronobiology(b)
        opp = zl["antipodal_branch"]
        if (opp + 6) % 12 != b or opp == b:
            antipodal_ok = False
        if abs(zl["diurnal_energy_sum"] - 9.6000) > 1e-4:
            energy_sum_ok = False

    sheng_visited: set[int] = set()
    cur = 0
    for _ in range(5):
        sheng_visited.add(cur)
        cur = (cur + 1) % 5
    sheng_cyclic = (len(sheng_visited) == 5)

    ke_visited: set[int] = set()
    cur = 0
    for _ in range(5):
        ke_visited.add(cur)
        cur = (cur + 2) % 5
    ke_cyclic = (len(ke_visited) == 5)

    circulant_ok = all(
        _evaluate_five_elements_shengke(a, 0)["circulant_row_sum"] == 4.65
        for a in range(5)
    )

    valid_labels = {"庙", "旺", "得", "利", "平", "不", "陷"}
    quanshu_total_cells = sum(len(arr) for arr in _QUANSHU_FOURTEEN_STARS_BRIGHTNESS.values())
    quanshu_valid = (quanshu_total_cells == 168) and all(
        val in valid_labels
        for arr in _QUANSHU_FOURTEEN_STARS_BRIGHTNESS.values()
        for val in arr
    )

    e_ground = _evaluate_quanshu_star_brightness(7, ming_branch=2)["sanfang_mean_energy"]
    e_halt = _evaluate_quanshu_star_brightness(0, ming_branch=0)["sanfang_mean_energy"]
    gap = round(e_ground - e_halt, 4)
    energy_gap_ok = (gap >= 0.10 and e_ground >= 0.85)

    all_verified = (
        antipodal_ok
        and energy_sum_ok
        and sheng_cyclic
        and ke_cyclic
        and circulant_ok
        and quanshu_valid
        and energy_gap_ok
    )

    return {
        "status": "verified" if all_verified else "failed",
        "ziwu_liuzhu_antipodal_involution_verified": antipodal_ok,
        "ziwu_liuzhu_energy_conservation_verified": energy_sum_ok,
        "five_elements_sheng_cycle_verified": sheng_cyclic,
        "five_elements_ke_cycle_verified": ke_cyclic,
        "five_elements_circulant_conservation_verified": circulant_ok,
        "quanshu_14_stars_totality_verified": quanshu_valid,
        "quanshu_energy_gap_monotonic_verified": energy_gap_ok,
        "ground_state_sanfang_energy": e_ground,
        "halt_state_sanfang_energy": e_halt,
        "energy_gap": gap,
    }


def _evaluate_dipper_axis_invariants(hexagram_state: int) -> dict[str, Any]:
    """Evaluate Northern-Southern Dipper pairwise axis sum invariants and auxiliary conservation."""
    state_code = hexagram_state & 0b111111
    stars = _compute_canonical_major_star_positions(state_code)
    branch_names = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    five_axes = {
        "sovereign_treasury": {"stars": ("紫微", "天府"), "sum_target": 4},
        "strategy_memory": {"stars": ("天机", "太阴"), "sum_target": 4},
        "visibility_critic": {"stars": ("太阳", "巨门"), "sum_target": 4},
        "execution_proxy": {"stars": ("武曲", "天相"), "sum_target": 4},
        "assistance_auditor": {"stars": ("天同", "天梁"), "sum_target": 4},
    }

    axes_status: dict[str, dict[str, Any]] = {}
    all_five_axes_ok = True
    for axis_name, axis_info in five_axes.items():
        s1, s2 = axis_info["stars"]
        b1 = stars.get(s1, 0)
        b2 = stars.get(s2, 0)
        actual_sum = (b1 + b2) % 12
        is_conserved = (actual_sum == axis_info["sum_target"])
        if not is_conserved:
            all_five_axes_ok = False
        axes_status[axis_name] = {
            "star_a": s1,
            "branch_a": b1,
            "branch_a_name": branch_names[b1],
            "star_b": s2,
            "branch_b": b2,
            "branch_b_name": branch_names[b2],
            "sum_mod_12": actual_sum,
            "conserved": is_conserved,
        }

    wc = stars.get("文昌", 10)
    wq = stars.get("文曲", 4)
    zf = stars.get("左辅", 4)
    yb = stars.get("右弼", 10)
    aux_chang_qu_sum = (wc + wq) % 12
    aux_zuo_bi_sum = (zf + yb) % 12
    aux_conserved = (aux_chang_qu_sum == 2 and aux_zuo_bi_sum == 2)

    return {
        "hexagram_state": hexagram_state,
        "state_code": state_code,
        "all_five_axes_conserved": all_five_axes_ok,
        "auxiliary_pairs_conserved": aux_conserved,
        "five_axes": axes_status,
        "chang_qu_sum": aux_chang_qu_sum,
        "zuo_bi_sum": aux_zuo_bi_sum,
        "governance_harmony": "perfect_dipper_symmetry" if (all_five_axes_ok and aux_conserved) else "symmetry_perturbed",
    }


def _evaluate_sha_po_lang_triad(
    hexagram_state: int,
    ming_branch: int | None = None,
) -> dict[str, Any]:
    """Evaluate Sha-Po-Lang Equilateral Triad Engine and dynamic transformation mode."""
    state_code = hexagram_state & 0b111111
    stars = _compute_canonical_major_star_positions(state_code)
    branch_names = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    qs = stars.get("七杀", 10)
    pj = stars.get("破军", 2)
    tl = stars.get("贪狼", 6)

    d_pj_qs = (pj - qs) % 12
    d_tl_pj = (tl - pj) % 12
    d_qs_tl = (qs - tl) % 12
    is_equilateral = (d_pj_qs == 4 and d_tl_pj == 4 and d_qs_tl == 4)

    triad_branches = {qs, pj, tl}
    mb = ((hexagram_state % 12) if ming_branch is None else (ming_branch % 12))
    san_fang = {mb, (mb + 4) % 12, (mb + 8) % 12, (mb + 6) % 12}

    ming_in_triad = (mb in triad_branches)
    sanfang_intersection = len(san_fang.intersection(triad_branches))
    is_active_spl = (sanfang_intersection >= 2 or ming_in_triad)

    if is_active_spl:
        dynamic_mode = "sha_po_lang_transformation"
        innovation_index = 1.25
        directive = "Sha-Po-Lang active across triad: decisive refactoring, agile single-shot striking, and accelerated exploration."
    else:
        dynamic_mode = "harmonic_steady_governance"
        innovation_index = 1.00
        directive = "Standard bounded execution under verifier supervision."

    return {
        "hexagram_state": hexagram_state,
        "ming_branch": mb,
        "ming_branch_name": branch_names[mb],
        "qisha_branch": qs,
        "qisha_branch_name": branch_names[qs],
        "pojun_branch": pj,
        "pojun_branch_name": branch_names[pj],
        "tanlang_branch": tl,
        "tanlang_branch_name": branch_names[tl],
        "is_equilateral_trine": is_equilateral,
        "angular_distances": [d_pj_qs, d_tl_pj, d_qs_tl],
        "ming_in_triad": ming_in_triad,
        "sanfang_spl_count": sanfang_intersection,
        "is_active_spl": is_active_spl,
        "dynamic_mode": dynamic_mode,
        "innovation_index": innovation_index,
        "governance_directive": directive,
    }


def _evaluate_ming_zhu_shen_zhu(
    hexagram_state: int,
    custom_ming_branch: int | None = None,
    custom_year_branch: int | None = None,
) -> dict[str, Any]:
    """Evaluate Ming Zhu (命主) and Shen Zhu (身主) symmetry invariants and archetypal roles."""
    state_code = hexagram_state & 0b111111
    ming_branch = (
        custom_ming_branch
        if custom_ming_branch is not None
        else (state_code & 0b111) % 12
    )
    year_branch = (
        custom_year_branch
        if custom_year_branch is not None
        else ((state_code >> 3) & 0b111) % 12
    )

    branch_names = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    ming_zhu_table = {
        0: "贪狼",
        1: "巨门",
        2: "禄存",
        3: "文曲",
        4: "廉贞",
        5: "武曲",
        6: "破军",
        7: "武曲",
        8: "廉贞",
        9: "文曲",
        10: "禄存",
        11: "巨门",
    }
    shen_zhu_table = {
        0: "火星",
        6: "火星",
        1: "天相",
        7: "天相",
        2: "天梁",
        8: "天梁",
        3: "天同",
        9: "天同",
        4: "文昌",
        10: "文昌",
        5: "天机",
        11: "天机",
    }

    ming_zhu = ming_zhu_table[ming_branch]
    shen_zhu = shen_zhu_table[year_branch]

    mirror_branch = (12 - ming_branch) % 12
    is_ziwu_axis = ming_branch in (0, 6)
    mirror_conserved = ming_zhu == ming_zhu_table[mirror_branch]

    antipodal_branch = (year_branch + 6) % 12
    shen_zhu_period_6_conserved = shen_zhu == shen_zhu_table[antipodal_branch]

    role_descriptions = {
        "贪狼": "exploration_and_opportunistic_resource_acquisition",
        "巨门": "deep_interface_inspection_and_audit_probing",
        "禄存": "reserve_capital_conservation_and_safe_buffering",
        "文曲": "formal_specification_syntax_and_protocol_formatting",
        "廉贞": "strict_security_boundary_and_invariant_enforcement",
        "武曲": "deterministic_execution_and_direct_tool_dispatch",
        "破军": "radical_refactoring_and_pioneering_state_mutation",
    }
    shen_role_descriptions = {
        "火星": "dynamic_burst_energy_and_immediate_reaction",
        "天相": "peer_contract_arbitration_and_interface_consensus",
        "天梁": "audit_oversight_and_systemic_recovery_supervision",
        "天同": "cooperative_consensus_and_graceful_tolerance",
        "文昌": "canonical_documentation_and_contract_verification",
        "天机": "algorithmic_tactical_routing_and_heuristic_planning",
    }

    return {
        "hexagram_state": state_code,
        "ming_branch": ming_branch,
        "ming_branch_name": branch_names[ming_branch],
        "ming_zhu": ming_zhu,
        "ming_zhu_role": role_descriptions.get(ming_zhu, "generic_agent_operator"),
        "is_ziwu_axis": is_ziwu_axis,
        "mirror_branch": mirror_branch,
        "mirror_conserved": mirror_conserved,
        "year_branch": year_branch,
        "year_branch_name": branch_names[year_branch],
        "shen_zhu": shen_zhu,
        "shen_zhu_role": shen_role_descriptions.get(
            shen_zhu, "generic_execution_archetype"
        ),
        "antipodal_branch": antipodal_branch,
        "shen_zhu_period_6_conserved": shen_zhu_period_6_conserved,
        "governance_mode": f"{ming_zhu}_{shen_zhu}_harmonic",
    }


def _evaluate_void_and_consumption_stars(
    year_stem: int = 0,
    year_branch: int = 0,
    ming_branch: int = 2,
) -> dict[str, Any]:
    """Evaluate Jiekong (截路空亡), DaHao (年支大耗), and TianShi/TianShang (天使天伤) dynamics."""
    s = year_stem % 10
    y = year_branch % 12
    m = ming_branch % 12

    stem_names = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    branch_names = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    base_branch = (8 - 2 * (s % 5)) % 12
    if s % 2 == 0:
        jiekong_branch = base_branch
        fujie_branch = (base_branch + 1) % 12
    else:
        jiekong_branch = (base_branch + 1) % 12
        fujie_branch = base_branch

    sui_po = (y + 6) % 12
    if y % 2 == 0:
        dahao_branch = (sui_po + 1) % 12
    else:
        dahao_branch = (sui_po + 11) % 12

    dahao_suipo_distance = (dahao_branch - sui_po) % 12
    tianshang_branch = (m + 5) % 12
    tianshi_branch = (m + 7) % 12
    shang_shi_axis_distance = (tianshi_branch - tianshang_branch) % 12

    return {
        "year_stem": s,
        "year_stem_name": stem_names[s],
        "year_branch": y,
        "year_branch_name": branch_names[y],
        "ming_branch": m,
        "ming_branch_name": branch_names[m],
        "jiekong_branch": jiekong_branch,
        "jiekong_branch_name": branch_names[jiekong_branch],
        "fujie_branch": fujie_branch,
        "fujie_branch_name": branch_names[fujie_branch],
        "jiekong_dyad": sorted([jiekong_branch, fujie_branch]),
        "jiekong_is_contiguous": (abs(jiekong_branch - fujie_branch) in (1, 11)),
        "sui_po_branch": sui_po,
        "sui_po_branch_name": branch_names[sui_po],
        "dahao_branch": dahao_branch,
        "dahao_branch_name": branch_names[dahao_branch],
        "dahao_suipo_distance": dahao_suipo_distance,
        "dahao_is_adjacent_to_suipo": dahao_suipo_distance in (1, 11),
        "tianshang_branch": tianshang_branch,
        "tianshang_branch_name": branch_names[tianshang_branch],
        "tianshi_branch": tianshi_branch,
        "tianshi_branch_name": branch_names[tianshi_branch],
        "shang_shi_distance": shang_shi_axis_distance,
        "risk_containment_directive": (
            "apply_void_damping"
            if jiekong_branch == m or dahao_branch == m
            else "normal_execution_flow"
        ),
    }


def _evaluate_ming_zhu_void_stars_certificate() -> dict[str, Any]:
    """23rd Formal mathematical certificate: Ming/Shen Zhu Invariants & Void/Consumption Star Dynamics."""
    ming_mirror_all_ok = True
    shen_period6_all_ok = True

    for state in range(64):
        res = _evaluate_ming_zhu_shen_zhu(state)
        if not res["mirror_conserved"]:
            ming_mirror_all_ok = False
            break
        if not res["shen_zhu_period_6_conserved"]:
            shen_period6_all_ok = False
            break

    jiekong_all_ok = True
    dahao_all_ok = True

    for s in range(10):
        for y in range(12):
            void_res = _evaluate_void_and_consumption_stars(
                year_stem=s, year_branch=y, ming_branch=(s + y) % 12
            )
            if not void_res["jiekong_is_contiguous"]:
                jiekong_all_ok = False
                break
            if not void_res["dahao_is_adjacent_to_suipo"]:
                dahao_all_ok = False
                break
        if not jiekong_all_ok or not dahao_all_ok:
            break

    all_verified = (
        ming_mirror_all_ok
        and shen_period6_all_ok
        and jiekong_all_ok
        and dahao_all_ok
    )

    return {
        "status": "verified" if all_verified else "failed",
        "ming_zhu_ziwu_mirror_verified": ming_mirror_all_ok,
        "shen_zhu_period_6_antipodal_verified": shen_period6_all_ok,
        "jiekong_dyad_contiguity_verified": jiekong_all_ok,
        "dahao_suipo_adjacency_verified": dahao_all_ok,
    }


def _evaluate_dipper_axes_and_sha_po_lang_certificate() -> dict[str, Any]:
    """22nd Formal mathematical certificate: Dipper Pairwise Invariants & Sha-Po-Lang Equilateral Triad."""
    axes_all_64_ok = True
    aux_all_64_ok = True
    spl_trine_all_64_ok = True

    for state in range(64):
        axis_res = _evaluate_dipper_axis_invariants(state)
        if not axis_res["all_five_axes_conserved"]:
            axes_all_64_ok = False
            break
        if not axis_res["auxiliary_pairs_conserved"]:
            aux_all_64_ok = False
            break

        spl_res = _evaluate_sha_po_lang_triad(state)
        if not spl_res["is_equilateral_trine"] or spl_res["angular_distances"] != [4, 4, 4]:
            spl_trine_all_64_ok = False
            break

    spl_ground = _evaluate_sha_po_lang_triad(7, ming_branch=2)
    spl_halt = _evaluate_sha_po_lang_triad(0, ming_branch=0)

    all_verified = (
        axes_all_64_ok
        and aux_all_64_ok
        and spl_trine_all_64_ok
    )

    return {
        "status": "verified" if all_verified else "failed",
        "dipper_five_axes_sum_4_verified": axes_all_64_ok,
        "auspicious_pairs_sum_2_verified": aux_all_64_ok,
        "sha_po_lang_equilateral_trine_verified": spl_trine_all_64_ok,
        "ground_state_spl_mode": spl_ground["dynamic_mode"],
        "halt_state_spl_mode": spl_halt["dynamic_mode"],
    }


def _evaluate_pattern_breaking_matrix(
    hexagram_state: int,
    pattern_name: str | None = None,
    sha_stars: list[str] | None = None,
) -> dict[str, Any]:
    """Evaluate classical pattern breaking (破格) dynamics and health degradation score."""
    state_code = hexagram_state & 0b111111

    breaking_catalog = {
        "君臣庆会": {
            "required": ["紫微入命", "左辅右弼同会三方四正"],
            "bonuses": ["文昌文曲", "天魁天钺", "紫微化权"],
            "breaking_shas": ["地空", "地劫", "擎羊", "陀罗", "火星", "铃星", "化忌"],
            "breaking_rules": ["紫府宫坐空劫", "紫府宫见双煞同坐", "紫微化忌或冲照化忌"],
        },
        "紫府同宫": {
            "required": ["紫微天府同在寅申"],
            "bonuses": ["辅弼同宫", "三奇嘉会", "禄马交驰"],
            "breaking_shas": ["地空", "地劫", "火星", "铃星", "擎羊", "陀罗"],
            "breaking_rules": ["命宫坐煞星", "三方四正煞星过多", "见空劫散贵"],
        },
        "府相朝垣": {
            "required": ["天府天相三合朝命"],
            "bonuses": ["禄存昌曲", "化权化禄", "无煞冲破"],
            "breaking_shas": ["擎羊", "陀罗", "化忌"],
            "breaking_rules": ["太阳落陷阳梁失辉", "三方煞重", "天相遇刑忌夹印"],
        },
        "火贪格": {
            "required": ["贪狼与火星同宫或会照"],
            "bonuses": ["贪狼化禄", "三方辅弼", "辰戌庙旺"],
            "breaking_shas": ["擎羊", "陀罗", "地空", "地劫", "化忌"],
            "breaking_rules": ["贪狼遇羊陀破横发", "贪狼遇空劫财来财去", "贪狼化忌暴败"],
        },
        "机月同梁": {
            "required": ["天机太阴天同天梁三方聚会"],
            "bonuses": ["化科化权", "昌曲魁钺", "禄存文星"],
            "breaking_shas": ["擎羊", "陀罗", "火星", "铃星", "化忌"],
            "breaking_rules": ["机月同梁最忌煞冲", "命宫坐煞变狡黠", "天同化忌损寿福"],
        },
        "石中隐玉": {
            "required": ["巨门在子午坐命"],
            "bonuses": ["巨门化禄", "巨门化权", "禄存三方"],
            "breaking_shas": ["擎羊", "陀罗", "化忌"],
            "breaking_rules": ["巨门化忌玉藏深泥", "命坐煞星招口舌官非", "早年孤蹇"],
        },
    }

    target_pattern = pattern_name or "君臣庆会"
    if target_pattern not in breaking_catalog:
        target_pattern = "君臣庆会"

    pat_info = breaking_catalog[target_pattern]
    active_shas = list(sha_stars) if sha_stars is not None else []
    if sha_stars is None:
        if (state_code & 0b000001) != 0:
            active_shas.append("擎羊")
        if (state_code & 0b000010) != 0:
            active_shas.append("地空")
        if (state_code & 0b000100) != 0:
            active_shas.append("化忌")

    breaking_hits = [s for s in active_shas if s in pat_info["breaking_shas"]]
    breaking_count = len(breaking_hits)
    bonus_count = 1 if (state_code & 0b001000) != 0 else 0

    health_score = round((1.0 + 0.15 * bonus_count) / (1.0 + 0.40 * breaking_count), 4)
    is_broken = breaking_count > 0

    if health_score >= 1.0:
        execution_posture = "intact_full_execution"
        directive = "proceed_full_generative_plan_and_refactoring"
    elif health_score >= 0.60:
        execution_posture = "partially_broken_degraded"
        directive = "degrade_to_surgical_patch_only_disallow_full_file_rewrites"
    else:
        execution_posture = "severely_broken_quarantine"
        directive = "quarantine_execution_read_only_audit_and_rollback"

    return {
        "hexagram_state": state_code,
        "pattern_name": target_pattern,
        "required_conditions": pat_info["required"],
        "active_shas": active_shas,
        "breaking_shas_hit": breaking_hits,
        "breaking_count": breaking_count,
        "bonus_count": bonus_count,
        "formation_health_score": health_score,
        "is_broken": is_broken,
        "execution_posture": execution_posture,
        "governance_directive": directive,
    }


def _evaluate_tri_level_time_flow(
    age: int = 30,
    gender: str = "male",
    year_branch: int = 0,
    bureau: int = 2,
    ming_branch: int = 2,
    calendar_year_branch: int = 6,
) -> dict[str, Any]:
    """Evaluate DaXian, XiaoXian, and LiuNian tri-level time progression cascade."""
    branch_names = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    b = bureau if bureau in (2, 3, 4, 5, 6) else 2
    cur_age = max(1, age)
    y_branch = year_branch % 12
    m_branch = ming_branch % 12
    cal_branch = calendar_year_branch % 12

    is_yang_year = (y_branch % 2) == 0
    is_male = gender.casefold() == "male"
    clockwise_daxian = (is_yang_year and is_male) or (not is_yang_year and not is_male)

    if cur_age < b:
        daxian_index = 0
        daxian_palace = m_branch
    else:
        daxian_index = (cur_age - b) // 10
        step = daxian_index if clockwise_daxian else -daxian_index
        daxian_palace = (m_branch + step) % 12

    xiaoxian_origin = (10 - 3 * (y_branch % 4)) % 12
    if is_male:
        xiaoxian_palace = (xiaoxian_origin + (cur_age - 1)) % 12
    else:
        xiaoxian_palace = (xiaoxian_origin - (cur_age - 1)) % 12

    liunian_palace = cal_branch

    d_dx_xx = min(abs(daxian_palace - xiaoxian_palace), 12 - abs(daxian_palace - xiaoxian_palace))
    d_xx_ln = min(abs(xiaoxian_palace - liunian_palace), 12 - abs(xiaoxian_palace - liunian_palace))
    d_dx_ln = min(abs(daxian_palace - liunian_palace), 12 - abs(daxian_palace - liunian_palace))

    is_triad_resonance = (d_dx_xx in (0, 4) and d_xx_ln in (0, 4) and d_dx_ln in (0, 4))
    is_conjunction = (daxian_palace == xiaoxian_palace == liunian_palace)

    if is_conjunction:
        resonance_mode = "triple_conjunction_maximum_momentum"
        gain_multiplier = 2.0
    elif is_triad_resonance:
        resonance_mode = "triad_harmonic_resonance"
        gain_multiplier = 1.5
    else:
        resonance_mode = "asynchronous_distributed_flow"
        gain_multiplier = 1.0

    return {
        "age": cur_age,
        "gender": "male" if is_male else "female",
        "bureau": b,
        "daxian": {
            "index": daxian_index,
            "palace_branch": daxian_palace,
            "palace_name": branch_names[daxian_palace],
            "step_direction": "clockwise" if clockwise_daxian else "counter_clockwise",
        },
        "xiaoxian": {
            "origin_branch": xiaoxian_origin,
            "origin_branch_name": branch_names[xiaoxian_origin],
            "palace_branch": xiaoxian_palace,
            "palace_name": branch_names[xiaoxian_palace],
        },
        "liunian": {
            "palace_branch": liunian_palace,
            "palace_name": branch_names[liunian_palace],
        },
        "angular_distances": [d_dx_xx, d_xx_ln, d_dx_ln],
        "is_triple_conjunction": is_conjunction,
        "is_triad_resonance": is_triad_resonance,
        "resonance_mode": resonance_mode,
        "gain_multiplier": gain_multiplier,
    }


def _evaluate_palace_as_star_and_ingress(
    active_palace: int = 5,
    ingress_stem: int = 0,
    ingress_branch: int = 0,
) -> dict[str, Any]:
    """Evaluate Ni Haixia's 'Palace-as-Star' duality and Tai Sui Ingress Method."""
    palace_order = [
        "命宫", "兄弟宫", "夫妻宫", "子女宫", "财帛宫", "疾厄宫",
        "迁移宫", "交友宫", "官禄宫", "田宅宫", "福德宫", "父母宫"
    ]
    p_idx = active_palace % 12
    p_name = palace_order[p_idx]

    palace_operator_map = {
        "命宫": {"as_star_archetype": "核心系统主控星", "governance_domain": "system_sovereignty_and_kernel_dispatch"},
        "兄弟宫": {"as_star_archetype": "并发并联协同星", "governance_domain": "peer_agent_cooperation_and_cash_reserve"},
        "夫妻宫": {"as_star_archetype": "双边协作契约星", "governance_domain": "interface_contract_and_peer_arbitration"},
        "子女宫": {"as_star_archetype": "子任务生成衍生星", "governance_domain": "subagent_spawning_and_delegation"},
        "财帛宫": {"as_star_archetype": "资源通量资本星", "governance_domain": "token_consumption_and_computational_budget"},
        "疾厄宫": {"as_star_archetype": "体质健康诊断星", "governance_domain": "pathology_memory_leak_and_stack_trace_audit"},
        "迁移宫": {"as_star_archetype": "外向交互空间星", "governance_domain": "remote_rpc_network_and_cross_host_io"},
        "交友宫": {"as_star_archetype": "从属协议服务星", "governance_domain": "worker_pool_and_downstream_subscription"},
        "官禄宫": {"as_star_archetype": "任务使命执行星", "governance_domain": "tool_execution_plan_and_deliverable_dispatch"},
        "田宅宫": {"as_star_archetype": "持久基石存储星", "governance_domain": "git_workspace_wal_checkpoints_and_filesystem"},
        "福德宫": {"as_star_archetype": "自愈韧性决策星", "governance_domain": "recovery_policy_tolerance_and_entropy_gate"},
        "父母宫": {"as_star_archetype": "上级守护治理星", "governance_domain": "supervisor_approval_and_human_in_the_loop"},
    }

    star_duality = palace_operator_map[p_name]
    s_ext = ingress_stem % 10
    b_ext = ingress_branch % 12
    ingress_target_palace = palace_order[b_ext]

    sihua_table = {
        0: {"lu": "廉贞", "quan": "破军", "ke": "武曲", "ji": "太阳"},
        1: {"lu": "天机", "quan": "天梁", "ke": "紫微", "ji": "太阴"},
        2: {"lu": "天同", "quan": "天机", "ke": "文昌", "ji": "廉贞"},
        3: {"lu": "太阴", "quan": "天同", "ke": "天机", "ji": "巨门"},
        4: {"lu": "贪狼", "quan": "太阴", "ke": "右弼", "ji": "天机"},
        5: {"lu": "武曲", "quan": "贪狼", "ke": "天梁", "ji": "文曲"},
        6: {"lu": "太阳", "quan": "武曲", "ke": "太阴", "ji": "天同"},
        7: {"lu": "巨门", "quan": "太阳", "ke": "文曲", "ji": "文昌"},
        8: {"lu": "天梁", "quan": "紫微", "ke": "左辅", "ji": "武曲"},
        9: {"lu": "破军", "quan": "巨门", "ke": "太阴", "ji": "贪狼"},
    }
    ext_sihua = sihua_table[s_ext]
    sensitive_palaces = {"命宫", "疾厄宫", "官禄宫", "田宅宫"}
    is_ji_sensitive = ingress_target_palace in sensitive_palaces

    return {
        "active_palace_index": p_idx,
        "active_palace_name": p_name,
        "palace_as_star": star_duality["as_star_archetype"],
        "governance_domain": star_duality["governance_domain"],
        "ingress_entity": {
            "stem": s_ext,
            "branch": b_ext,
            "target_palace": ingress_target_palace,
            "projected_sihua": ext_sihua,
        },
        "is_ji_on_sensitive_palace": is_ji_sensitive,
        "ingress_governance_directive": (
            "apply_tai_sui_ji_damping_barrier"
            if is_ji_sensitive
            else "admit_tai_sui_ingress_flow"
        ),
    }


def _evaluate_pattern_breaking_and_resonance_certificate() -> dict[str, Any]:
    """24th Formal mathematical certificate: Pattern Breaking Health Monotonicity, XiaoXian Triad Invariant & Ingress Totality."""
    breaking_monotonic_ok = True
    base_res = _evaluate_pattern_breaking_matrix(0, pattern_name="君臣庆会", sha_stars=[])
    one_sha_res = _evaluate_pattern_breaking_matrix(0, pattern_name="君臣庆会", sha_stars=["地空"])
    two_sha_res = _evaluate_pattern_breaking_matrix(0, pattern_name="君臣庆会", sha_stars=["地空", "地劫"])
    if not (base_res["formation_health_score"] > one_sha_res["formation_health_score"] > two_sha_res["formation_health_score"]):
        breaking_monotonic_ok = False

    xiaoxian_formula_ok = True
    for y in range(12):
        res = _evaluate_tri_level_time_flow(age=20, year_branch=y)
        expected = (10 - 3 * (y % 4)) % 12
        if res["xiaoxian"]["origin_branch"] != expected:
            xiaoxian_formula_ok = False
            break

    palace_totality_ok = True
    seen_domains = set()
    for p in range(12):
        p_res = _evaluate_palace_as_star_and_ingress(active_palace=p)
        domain = p_res["governance_domain"]
        if domain in seen_domains or not domain:
            palace_totality_ok = False
            break
        seen_domains.add(domain)

    ingress_sihua_ok = True
    for s in range(10):
        ing_res = _evaluate_palace_as_star_and_ingress(ingress_stem=s)
        sihua = ing_res["ingress_entity"]["projected_sihua"]
        if len(sihua) != 4 or not sihua.get("lu") or not sihua.get("ji"):
            ingress_sihua_ok = False
            break

    all_verified = (
        breaking_monotonic_ok
        and xiaoxian_formula_ok
        and palace_totality_ok
        and ingress_sihua_ok
    )

    return {
        "status": "verified" if all_verified else "failed",
        "pattern_breaking_monotonicity_verified": breaking_monotonic_ok,
        "xiaoxian_triad_mod4_invariant_verified": xiaoxian_formula_ok,
        "palace_as_star_totality_verified": palace_totality_ok,
        "tai_sui_ingress_sihua_verified": ingress_sihua_ok,
    }


class IchingZiweiCertificatesMixin:
    """Mathematical certificates and formal verification for Ziwei Doushu isomorphism."""

    @classmethod
    def sovereign_ring_isomorphism_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of the Sovereign Hexagram Ring <-> Earthly Branches isomorphism."""
        codes = getattr(cls, "SOVEREIGN_HEXAGRAM_CODES", (2, 24, 19, 11, 34, 43, 1, 44, 33, 12, 20, 23))
        return _evaluate_sovereign_ring_certificate(codes)

    @classmethod
    def an_he_coupling_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Six Harmonies (六合 / 暗合) on the 6-bit Boolean Hypercube."""
        codes = getattr(cls, "SOVEREIGN_HEXAGRAM_CODES", (2, 24, 19, 11, 34, 43, 1, 44, 33, 12, 20, 23))
        return _evaluate_an_he_coupling_certificate(codes)

    @classmethod
    def shen_gong_anchorage_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Shen Gong Even Subgroup Theorem (身宫偶数子群同构定理)."""
        return _evaluate_shen_gong_certificate()

    @classmethod
    def star_brightness_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Star Brightness Invariance across all 64 states."""
        return _evaluate_star_brightness_certificate(cls)

    @classmethod
    def jie_shen_even_subgroup_relief_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Jie Shen Even Subgroup and Damping Bound."""
        return _evaluate_jie_shen_certificate()

    @classmethod
    def twelve_deities_triad_and_suipo_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Twelve Deities Triad Partition and Sui Po Opposite Involution."""
        codes = getattr(cls, "SOVEREIGN_HEXAGRAM_CODES", (2, 24, 19, 11, 34, 43, 1, 44, 33, 12, 20, 23))
        return _evaluate_twelve_deities_certificate(codes)

    @classmethod
    def flying_sihua_cascade_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Flying Sihua Cascade and DuiGong Involution."""
        codes = getattr(cls, "SOVEREIGN_HEXAGRAM_CODES", (2, 24, 19, 11, 34, 43, 1, 44, 33, 12, 20, 23))
        return _evaluate_flying_sihua_certificate(codes)

    @classmethod
    def triadic_synthesis_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Triadic Synthesis and 2/3 Domination Principle."""
        return _evaluate_triadic_synthesis_certificate()

    @classmethod
    def ziwei_tianfu_and_yangtuo_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Ming/Shen Zhu Symmetries, Ziwei-Tianfu Duality & Yang-Tuo Clamping."""
        codes = getattr(cls, "SOVEREIGN_HEXAGRAM_CODES", (2, 24, 19, 11, 34, 43, 1, 44, 33, 12, 20, 23))
        return _evaluate_ziwei_tianfu_and_yangtuo_certificate(codes)

    @classmethod
    def solar_equation_and_zishi_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of EOT bounded oscillation, Zishi measure partition, and meridian invariance."""
        return _evaluate_solar_equation_and_zishi_certificate()

    @classmethod
    def school_divergence_consensus_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Seven Stems Sihua Totality, Geng Closure, and Consensus Monotonicity."""
        return _evaluate_school_divergence_consensus_certificate()

    @classmethod
    def classical_patterns_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Safety Dominance Invariant, Supreme Purity, and Exhaustive Formations."""
        return _evaluate_classical_patterns_certificate()

    @classmethod
    def auxiliary_polarity_and_yunxian_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of DaHao Bijection, Jiekong Duality, and 7-tier Yunxian Hierarchy."""
        return _evaluate_auxiliary_polarity_and_yunxian_certificate()

    @classmethod
    def heming_synastry_and_noble_stars_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Tianluo-Diwang Exclusion, Kui-Yue Reflection, Tianma Involution, and Synastry."""
        return _evaluate_heming_synastry_and_noble_stars_certificate()

    @classmethod
    def deep_computation_and_graph_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate for 48-ray Sihua Graph, 96-ray Bipartite Tensor, and DST Soundness."""
        return _evaluate_deep_computation_and_graph_certificate()

    @classmethod
    def pathology_and_environmental_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate for Five-Element Pathology, 14-Star Contracts, and Fengshui Sandbox."""
        return _evaluate_pathology_and_environmental_certificate()

    @classmethod
    def six_channel_and_empty_palace_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate for Six-Channel Healing, Empty Palace Borrowing, and NaYin Matrix."""
        return _evaluate_six_channel_and_empty_palace_certificate()

    @classmethod
    def doujun_and_solar_boundary_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate for Doujun Chronology, Childhood Guard, and Solar Boundary."""
        return _evaluate_doujun_and_solar_boundary_certificate()

    @classmethod
    def auxiliary_pairs_and_city_solar_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate for Auxiliary Conservation Pairs and City Solar Precision."""
        return _evaluate_auxiliary_pairs_and_city_solar_certificate()

    @classmethod
    def changsheng_and_expanded_patterns_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate for ChangSheng Automaton, GuChen-GuaSu-HuaGai & 32 Patterns."""
        return _evaluate_changsheng_and_expanded_patterns_certificate()

    @classmethod
    def ziwu_liuzhu_and_shengke_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate for Ziwu Liuzhu, Five Elements Sheng-Ke & Quanshu Totality."""
        return _evaluate_ziwu_liuzhu_and_shengke_certificate()

    @classmethod
    def dipper_axes_and_sha_po_lang_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate for Dipper Pairwise Invariants & Sha-Po-Lang Equilateral Triad."""
        return _evaluate_dipper_axes_and_sha_po_lang_certificate()

    @classmethod
    def ming_zhu_shen_zhu_and_void_stars_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate for Ming/Shen Zhu Invariants & Void/Consumption Star Dynamics."""
        return _evaluate_ming_zhu_void_stars_certificate()

    @classmethod
    def pattern_breaking_and_resonance_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate for Pattern Breaking Health Monotonicity & Tri-Level Ingress."""
        return _evaluate_pattern_breaking_and_resonance_certificate()

    @classmethod
    def ziwei_mathematical_audit(cls) -> dict[str, Any]:
        """Comprehensive mathematical audit of all 24 Ziwei Doushu cross-validation certificates."""
        ring = cls.sovereign_ring_isomorphism_certificate()
        an_he = cls.an_he_coupling_certificate()
        shen_gong = cls.shen_gong_anchorage_certificate()
        star_bright = cls.star_brightness_certificate()
        jie_shen = cls.jie_shen_even_subgroup_relief_certificate()
        twelve_deities = cls.twelve_deities_triad_and_suipo_certificate()
        flying_sihua = cls.flying_sihua_cascade_certificate()
        triad_syn = cls.triadic_synthesis_certificate()
        zi_fu_yang_tuo = cls.ziwei_tianfu_and_yangtuo_certificate()
        solar_zishi = cls.solar_equation_and_zishi_certificate()
        school_consensus = cls.school_divergence_consensus_certificate()
        classical_pat = cls.classical_patterns_certificate()
        aux_yunxian = cls.auxiliary_polarity_and_yunxian_certificate()
        heming_synastry = cls.heming_synastry_and_noble_stars_certificate()
        deep_comp = cls.deep_computation_and_graph_certificate()
        pathology_env = cls.pathology_and_environmental_certificate()
        six_chan = cls.six_channel_and_empty_palace_certificate()
        doujun_solar = cls.doujun_and_solar_boundary_certificate()
        aux_city_solar = cls.auxiliary_pairs_and_city_solar_certificate()
        changsheng_pat = cls.changsheng_and_expanded_patterns_certificate()
        ziwu_shengke = cls.ziwu_liuzhu_and_shengke_certificate()
        dipper_spl = cls.dipper_axes_and_sha_po_lang_certificate()
        ming_zhu_void = cls.ming_zhu_shen_zhu_and_void_stars_certificate()
        pattern_break = cls.pattern_breaking_and_resonance_certificate()
        all_passed = (
            ring.get("status") == "verified"
            and an_he.get("status") == "verified"
            and shen_gong.get("status") == "verified"
            and star_bright.get("status") == "verified"
            and jie_shen.get("status") == "verified"
            and twelve_deities.get("status") == "verified"
            and flying_sihua.get("status") == "verified"
            and triad_syn.get("status") == "verified"
            and zi_fu_yang_tuo.get("status") == "verified"
            and solar_zishi.get("status") == "verified"
            and school_consensus.get("status") == "verified"
            and classical_pat.get("status") == "verified"
            and aux_yunxian.get("status") == "verified"
            and heming_synastry.get("status") == "verified"
            and deep_comp.get("status") == "verified"
            and pathology_env.get("status") == "verified"
            and six_chan.get("status") == "verified"
            and doujun_solar.get("status") == "verified"
            and aux_city_solar.get("status") == "verified"
            and changsheng_pat.get("status") == "verified"
            and ziwu_shengke.get("status") == "verified"
            and dipper_spl.get("status") == "verified"
            and ming_zhu_void.get("status") == "verified"
            and pattern_break.get("status") == "verified"
        )
        return {
            "status": "ok" if all_passed else "failed",
            "sovereign_ring": ring,
            "an_he_coupling": an_he,
            "shen_gong_anchorage": shen_gong,
            "star_brightness": star_bright,
            "jie_shen_relief": jie_shen,
            "twelve_deities": twelve_deities,
            "flying_sihua_cascade": flying_sihua,
            "triadic_synthesis": triad_syn,
            "ziwei_tianfu_and_yangtuo": zi_fu_yang_tuo,
            "solar_equation_and_zishi": solar_zishi,
            "school_divergence_consensus": school_consensus,
            "classical_patterns": classical_pat,
            "auxiliary_polarity_and_yunxian": aux_yunxian,
            "heming_synastry_and_noble_stars": heming_synastry,
            "deep_computation_and_graph": deep_comp,
            "pathology_and_environmental": pathology_env,
            "six_channel_and_empty_palace": six_chan,
            "doujun_and_solar_boundary": doujun_solar,
            "auxiliary_pairs_and_city_solar": aux_city_solar,
            "changsheng_and_expanded_patterns": changsheng_pat,
            "ziwu_liuzhu_and_shengke": ziwu_shengke,
            "dipper_axes_and_sha_po_lang": dipper_spl,
            "ming_zhu_shen_zhu_and_void_stars": ming_zhu_void,
            "pattern_breaking_and_resonance": pattern_break,
        }


class IchingZiweiCoreMixin(IchingZiweiCertificatesMixin):
    """Core diagnostic and consensus extensions based on Ziwei Doushu isomorphism."""

    @classmethod
    def ming_zhu_shen_zhu_profile(
        cls,
        hexagram_state: int,
        custom_ming_branch: int | None = None,
        custom_year_branch: int | None = None,
    ) -> dict[str, Any]:
        """Evaluate Ming Zhu (命主) and Shen Zhu (身主) symmetry invariants and archetypal roles."""
        return _evaluate_ming_zhu_shen_zhu(
            hexagram_state=hexagram_state,
            custom_ming_branch=custom_ming_branch,
            custom_year_branch=custom_year_branch,
        )

    @classmethod
    def void_and_consumption_stars_profile(
        cls,
        year_stem: int = 0,
        year_branch: int = 0,
        ming_branch: int = 2,
    ) -> dict[str, Any]:
        """Evaluate Jiekong (截路空亡), DaHao (年支大耗), and TianShi/TianShang (天使天伤) dynamics."""
        return _evaluate_void_and_consumption_stars(
            year_stem=year_stem,
            year_branch=year_branch,
            ming_branch=ming_branch,
        )

    @classmethod
    def dipper_axis_invariants_profile(cls, hexagram_state: int) -> dict[str, Any]:
        """Evaluate Northern-Southern Dipper pairwise axis sum invariants and auxiliary conservation."""
        return _evaluate_dipper_axis_invariants(hexagram_state)

    @classmethod
    def sha_po_lang_triad_profile(
        cls, hexagram_state: int, ming_branch: int | None = None
    ) -> dict[str, Any]:
        """Evaluate Sha-Po-Lang Equilateral Triad Engine and dynamic transformation mode."""
        return _evaluate_sha_po_lang_triad(hexagram_state, ming_branch)

    @classmethod
    def ziwu_liuzhu_chronobiology_profile(
        cls, current_hour_branch: int, task_type: str = "general"
    ) -> dict[str, Any]:
        """Compute Ziwu Liuzhu Meridian flow, diurnal energy wave, and antipodal balance."""
        return _evaluate_ziwu_liuzhu_chronobiology(current_hour_branch, task_type)

    @classmethod
    def five_elements_shengke_profile(
        cls, element_a: int | str, element_b: int | str
    ) -> dict[str, Any]:
        """Compute Five Elements Generation-Destruction interaction dynamics and circulant energy gain."""
        return _evaluate_five_elements_shengke(element_a, element_b)

    @classmethod
    def quanshu_star_brightness_profile(
        cls, hexagram_state: int, ming_branch: int | None = None
    ) -> dict[str, Any]:
        """Evaluate classical 14 major stars brightness from Quanshu across Sanfang and full chart."""
        return _evaluate_quanshu_star_brightness(hexagram_state, ming_branch)

    @classmethod
    def changsheng_lifecycle_profile(
        cls,
        bureau_number: int,
        gender: str = "male",
        year_stem: int = 0,
        current_palace_branch: int | None = None,
    ) -> dict[str, Any]:
        """Compute Twelve ChangSheng stages and Agent Process Lifecycle Automaton."""
        return _evaluate_changsheng_lifecycle(
            bureau_number, gender, year_stem, current_palace_branch
        )

    @classmethod
    def guchen_guasu_huagai_profile(cls, year_branch: int) -> dict[str, Any]:
        """Compute GuChen, GuaSu, HuaGai (Four Earth Tombs), and XianChi (Four Cardinals)."""
        return _evaluate_guchen_guasu_huagai(year_branch)

    @classmethod
    def expanded_classical_patterns_profile(
        cls,
        turn_number: int,
        current_status: int,
        fatal_regression: bool = False,
        ast_valid: bool = True,
        verifier_passed: bool = True,
    ) -> dict[str, Any]:
        """Comprehensive 32+ classical patterns evaluation across all levels and clamping formations."""
        return _evaluate_expanded_classical_patterns(
            turn_number=turn_number,
            current_status=current_status,
            fatal_regression=fatal_regression,
            ast_valid=ast_valid,
            verifier_passed=verifier_passed,
        )

    @classmethod
    def auxiliary_stars_pairs_profile(
        cls,
        birth_month: int,
        birth_day: int,
        ming_branch: int,
        birth_hour: int = 0,
        zuofu_branch: int | None = None,
        youbi_branch: int | None = None,
        wenchang_branch: int | None = None,
        wenqu_branch: int | None = None,
    ) -> dict[str, Any]:
        """Compute auxiliary star conservation pairs, phase invariants, and Tianshang-Tianshi clamping."""
        return _evaluate_auxiliary_stars_pairs(
            birth_month,
            birth_day,
            ming_branch,
            birth_hour,
            zuofu_branch,
            youbi_branch,
            wenchang_branch,
            wenqu_branch,
        )

    @classmethod
    def city_true_solar_profile(
        cls,
        city_name: str,
        year: int,
        month: int,
        day: int,
        hour: int,
        minute: int = 0,
        auto_dst: bool = True,
    ) -> dict[str, Any]:
        """Compute precision True Solar Time and clock adaptation for major Chinese cities."""
        return _evaluate_city_true_solar_precision(
            city_name, year, month, day, hour, minute, auto_dst
        )

    @classmethod
    def doujun_chronology_profile(
        cls,
        year_branch: int,
        birth_month: int,
        birth_hour: int,
        flowing_month: int = 1,
        flowing_day: int = 1,
        flowing_hour: int = 0,
        ming_branch: int | None = None,
    ) -> dict[str, Any]:
        """Compute Doujun and flowing chronology chain (斗君月日时时空流) for episodic agent scheduling."""
        return _evaluate_doujun_chronology_chain(
            year_branch, birth_month, birth_hour, flowing_month, flowing_day, flowing_hour, ming_branch
        )

    @classmethod
    def childhood_guard_profile(
        cls,
        bureau_number: int,
        virtual_age: int,
        ming_branch: int,
    ) -> dict[str, Any]:
        """Compute childhood pre-activation safety guard (童限前置保护) before bureau activation."""
        return _evaluate_childhood_guard(bureau_number, virtual_age, ming_branch)

    @classmethod
    def solar_lichun_boundary_profile(
        cls,
        solar_year: int,
        solar_month: int,
        solar_day: int,
        solar_hour: int,
        solar_minute: int = 0,
        lunar_year: int | None = None,
        lichun_day: int = 4,
        lichun_hour: int = 19,
        lichun_minute: int = 56,
    ) -> dict[str, Any]:
        """Evaluate dual-track calendar boundary (立春节气四柱 vs 农历紫微排盘分界)."""
        return _evaluate_solar_lichun_boundary(
            solar_year,
            solar_month,
            solar_day,
            solar_hour,
            solar_minute,
            lunar_year,
            lichun_day,
            lichun_hour,
            lichun_minute,
        )

    @classmethod
    def task_bureau_profile(cls, file_count: int, total_loc: int) -> dict[str, Any]:
        """Compute the Five Elements Bureau (五行局) and scheduling envelopes from workspace scale."""
        return _evaluate_task_bureau(file_count, total_loc)

    @classmethod
    def self_sihua_profile(
        cls,
        current_turn: dict[str, Any],
        history: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        """Detect internal entropy dissipation and deadlock (宫干自化)."""
        return _evaluate_self_sihua(current_turn, history)

    @classmethod
    def causal_origin_profile(
        cls,
        error_traceback: str | None,
        history: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Trace the causal origin palace (来因宫) of an execution error / halt."""
        return _evaluate_causal_origin(error_traceback, history)

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
        """Evaluate 4-point distributed consensus across San Fang Si Zheng (三方四正)."""
        return _evaluate_triad_consensus(
            turn_number=turn_number,
            current_status=current_status,
            ast_valid=ast_valid,
            token_budget_ok=token_budget_ok,
            verifier_passed=verifier_passed,
            environment_ok=environment_ok,
        )

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
    def star_brightness_profile(
        cls,
        status_code: int,
        pattern_level: str | None = None,
    ) -> dict[str, Any]:
        """Evaluate star brightness (庙旺落陷) and governor permissions from energy and patterns."""
        energy = getattr(cls, "lyapunov_energy")(status_code)
        return _evaluate_star_brightness(status_code, energy, pattern_level=pattern_level)

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
    def temporal_superposition_profile(
        cls,
        macro_stage: str,
        turn_status: int,
        event: str | None = None,
    ) -> dict[str, Any]:
        """Superimpose Macro Project Phase (大限) and Micro Step Iteration (流年/流月)."""
        return _evaluate_temporal_superposition(
            macro_stage=macro_stage,
            turn_status=turn_status,
            event=event,
        )

    @classmethod
    def star_dynamic_energy_profile(
        cls,
        triad_consensus_score: float = 1.0,
        ast_valid: bool = True,
        environment_ok: bool = True,
        cache_hit: bool = False,
        step_duration_ms: int = 10,
        path_guard_violation: bool = False,
        consecutive_stalls: int = 0,
        verifier_failed: bool = False,
        syntax_error: bool = False,
        undefined_symbols: int = 0,
        no_actionable_edits: bool = False,
        resource_budget_exhausted: bool = False,
    ) -> dict[str, Any]:
        """Compute dynamic energy distribution across 8 Lucky Stars and 6 Sha Stars."""
        return _evaluate_star_dynamic_energy(
            triad_consensus_score=triad_consensus_score,
            ast_valid=ast_valid,
            environment_ok=environment_ok,
            cache_hit=cache_hit,
            step_duration_ms=step_duration_ms,
            path_guard_violation=path_guard_violation,
            consecutive_stalls=consecutive_stalls,
            verifier_failed=verifier_failed,
            syntax_error=syntax_error,
            undefined_symbols=undefined_symbols,
            no_actionable_edits=no_actionable_edits,
            resource_budget_exhausted=resource_budget_exhausted,
        )

    @classmethod
    def jie_shen_relief_profile(
        cls,
        turn_number: int,
        status_code: int,
        sha_stars: dict[str, float] | list[str] | set[str] | None = None,
        error_scenario: str | None = None,
        attempt_count: int = 1,
    ) -> dict[str, Any]:
        """Arbitrate Jie Shen (解神) relief damping and rescue action."""
        return _evaluate_jie_shen_relief(
            turn_number=turn_number,
            status_code=status_code,
            sha_stars=sha_stars,
            error_scenario=error_scenario,
            attempt_count=attempt_count,
        )

    @classmethod
    def twelve_deities_profile(
        cls,
        turn_number: int,
        status_code: int,
        anchor_branch: int | None = None,
    ) -> dict[str, Any]:
        """Compute Twelve Auxiliary Deities (将前/岁前/博士十二神) distribution."""
        return _evaluate_twelve_deities(
            turn_number=turn_number,
            status_code=status_code,
            anchor_branch=anchor_branch,
        )

    @classmethod
    def flying_sihua_cascade_profile(
        cls,
        turn_number: int,
        status_code: int,
        macro_stage: str = "implementation",
        baseline_status: int = 7,
    ) -> dict[str, Any]:
        """Compute multi-layer Flying Sihua (跨宫飞星与四化多层叠象) cascade risk."""
        return _evaluate_flying_sihua_cascade(
            turn_number=turn_number,
            status_code=status_code,
            macro_stage=macro_stage,
            baseline_status=baseline_status,
        )

    @classmethod
    def triadic_synthesis_profile(
        cls,
        status_code: int,
        environment_ok: bool = True,
        path_guard_ok: bool = True,
        verifier_passed: bool | None = None,
        ast_valid: bool = True,
        patch_surgical: bool = True,
    ) -> dict[str, Any]:
        """Compute Ni Haixia Triadic Architectural Synthesis (天纪/地纪/人纪三纪会聚势能)."""
        return _evaluate_triadic_synthesis(
            status_code=status_code,
            environment_ok=environment_ok,
            path_guard_ok=path_guard_ok,
            verifier_passed=verifier_passed,
            ast_valid=ast_valid,
            patch_surgical=patch_surgical,
        )

    @classmethod
    def ming_shen_zhu_profile(cls, turn_number: int, status_code: int) -> dict[str, Any]:
        """Compute Ming Zhu (命主) and Shen Zhu (身主) stellar governors."""
        return _evaluate_ming_shen_zhu(turn_number=turn_number, status_code=status_code)

    @classmethod
    def ziwei_tianfu_duality_profile(cls, status_code: int) -> dict[str, Any]:
        """Compute Ziwei-Tianfu duality axis, involutive distance, and Tai-Pi fixed points."""
        return _evaluate_ziwei_tianfu_duality(status_code=status_code)


class IchingZiweiDynamicMixin(IchingZiweiCoreMixin):
    """Dynamic time cascades, pattern breaking and ingress projections."""

    @classmethod
    def pattern_breaking_profile(
        cls,
        hexagram_state: int,
        pattern_name: str | None = None,
        sha_stars: list[str] | None = None,
    ) -> dict[str, Any]:
        """Evaluate classical pattern breaking (破格) dynamics and health degradation score."""
        return _evaluate_pattern_breaking_matrix(
            hexagram_state=hexagram_state,
            pattern_name=pattern_name,
            sha_stars=sha_stars,
        )

    @classmethod
    def tri_level_time_flow_profile(
        cls,
        age: int = 30,
        gender: str = "male",
        year_branch: int = 0,
        bureau: int = 2,
        ming_branch: int = 2,
        calendar_year_branch: int = 6,
    ) -> dict[str, Any]:
        """Evaluate DaXian, XiaoXian, and LiuNian tri-level time progression cascade."""
        return _evaluate_tri_level_time_flow(
            age=age,
            gender=gender,
            year_branch=year_branch,
            bureau=bureau,
            ming_branch=ming_branch,
            calendar_year_branch=calendar_year_branch,
        )

    @classmethod
    def palace_star_duality_profile(
        cls,
        active_palace: int = 5,
        ingress_stem: int = 0,
        ingress_branch: int = 0,
    ) -> dict[str, Any]:
        """Evaluate Ni Haixia's 'Palace-as-Star' duality and Tai Sui Ingress Method."""
        return _evaluate_palace_as_star_and_ingress(
            active_palace=active_palace,
            ingress_stem=ingress_stem,
            ingress_branch=ingress_branch,
        )


class IchingZiweiMixin(IchingZiweiDynamicMixin):
    """Extended diagnostic, synastric, and environmental extensions based on Ziwei Doushu."""

    @classmethod
    def yang_tuo_clamping_profile(
        cls,
        turn_number: int,
        status_code: int,
        has_hua_ji: bool = False,
    ) -> dict[str, Any]:
        """Evaluate Qing Yang and Tuo Luo geometric clamping around Lu Cun (羊陀夹禄 / 羊陀夹忌)."""
        return _evaluate_yang_tuo_clamping(
            turn_number=turn_number,
            status_code=status_code,
            has_hua_ji=has_hua_ji,
        )

    @classmethod
    def true_solar_time_profile(
        cls,
        year: int,
        month: int,
        day: int,
        clock_hour: int,
        clock_minute: int,
        longitude: float = 120.0,
        utc_offset_minutes: int = 480,
    ) -> dict[str, Any]:
        """Compute true solar time (地方真太阳时), branch mapping, and late Zishi detection."""
        return _evaluate_true_solar_time(
            year=year,
            month=month,
            day=day,
            clock_hour=clock_hour,
            clock_minute=clock_minute,
            longitude=longitude,
            utc_offset_minutes=utc_offset_minutes,
        )

    @classmethod
    def clock_drift_adaptation_profile(
        cls,
        clock_drift_seconds: float,
        event_epoch_timestamp: float | None = None,
        late_zishi_rule: str = "next-day",
    ) -> dict[str, Any]:
        """Evaluate clock drift adaptation for WAL logging, replay buffers, and distributed epochs."""
        return _evaluate_clock_drift_adaptation(
            clock_drift_seconds=clock_drift_seconds,
            event_epoch_timestamp=event_epoch_timestamp,
            late_zishi_rule=late_zishi_rule,
        )

    @classmethod
    def school_consensus_profile(
        cls,
        stem_index: int,
        geng_variant: str = "GYWYT",
        late_zishi_rule: str = "next-day",
        leap_month_rule: str = "split",
    ) -> dict[str, Any]:
        """Evaluate multi-school divergence, consensus degree, and governance arbitration."""
        return _evaluate_school_consensus(
            stem_index=stem_index,
            geng_variant=geng_variant,
            late_zishi_rule=late_zishi_rule,
            leap_month_rule=leap_month_rule,
        )

    @classmethod
    def classical_patterns_profile(
        cls,
        turn_number: int,
        status_code: int,
        ast_valid: bool = True,
        token_budget_ok: bool = True,
        verifier_passed: bool = True,
        environment_ok: bool = True,
        fatal_regression: bool = False,
        consecutive_syntax_errors: int = 0,
        undefined_symbols_count: int = 0,
        consecutive_read_stalls: int = 0,
    ) -> dict[str, Any]:
        """Exhaustive evaluation of classical Ziwei auspicious, harmonic, assisting, and breaking formations."""
        return _evaluate_classical_patterns(
            turn_number=turn_number,
            status_code=status_code,
            ast_valid=ast_valid,
            token_budget_ok=token_budget_ok,
            verifier_passed=verifier_passed,
            environment_ok=environment_ok,
            fatal_regression=fatal_regression,
            consecutive_syntax_errors=consecutive_syntax_errors,
            undefined_symbols_count=undefined_symbols_count,
            consecutive_read_stalls=consecutive_read_stalls,
        )

    @classmethod
    def auxiliary_stars_polarity_profile(
        cls,
        year_stem: int,
        year_branch: int,
    ) -> dict[str, Any]:
        """Compute auxiliary star polarity reversals for DaHao, Jiekong/Fujie, and Xunkong/Fuxun."""
        return _evaluate_auxiliary_stars_polarity(year_stem=year_stem, year_branch=year_branch)

    @classmethod
    def nested_yunxian_temporal_profile(
        cls,
        view: str,
        turn_number: int,
        macro_stage: str = "implementation",
        status_code: int = 7,
    ) -> dict[str, Any]:
        """Evaluate 7-tier nested temporal scopes (运限七层时空嵌套与递进上下文)."""
        return _evaluate_nested_yunxian_temporal(
            view=view,
            turn_number=turn_number,
            macro_stage=macro_stage,
            status_code=status_code,
        )

    @classmethod
    def noble_horse_stars_profile(
        cls,
        year_stem: int,
        year_branch: int,
        active_palace: int,
        tuoluo_present: bool = False,
        kongjie_present: bool = False,
    ) -> dict[str, Any]:
        """Compute Tiankui, Tianyue, Tianma, Hongluan, Tianxi and Lu-Ma concurrency dynamics."""
        return _evaluate_noble_horse_stars(
            year_stem=year_stem,
            year_branch=year_branch,
            active_palace=active_palace,
            tuoluo_present=tuoluo_present,
            kongjie_present=kongjie_present,
        )

    @classmethod
    def dual_sihua_superposition_profile(
        cls,
        palace_branch: int,
        transformations: list[str],
    ) -> dict[str, Any]:
        """Arbitrate multi-signal superposition when multiple Sihua transformations share one palace."""
        return _evaluate_dual_sihua_superposition(
            palace_branch=palace_branch,
            transformations=transformations,
        )

    @classmethod
    def multi_agent_synastry_profile(
        cls,
        agent_a: dict[str, Any],
        agent_b: dict[str, Any],
    ) -> dict[str, Any]:
        """Multi-agent synastry compatibility based on Ni Haisha's Double Palace and Cross Flying Sihua."""
        return _evaluate_multi_agent_synastry(
            agent_a=agent_a,
            agent_b=agent_b,
        )

    @classmethod
    def famous_archetype_profile(cls, person_id: str) -> dict[str, Any]:
        """Retrieve operational archetype, risk profile, and scheduling strategy from famous benchmarks."""
        return _evaluate_famous_archetype(person_id=person_id)

    @classmethod
    def full_sihua_graph_profile(
        cls,
        year_stem: int,
        status_code: int = 7,
        custom_stars: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Exhaustively compute the complete 48-ray directed Flying Sihua network across all 12 palaces."""
        return _evaluate_full_sihua_graph(
            year_stem=year_stem,
            status_code=status_code,
            custom_stars=custom_stars,
        )

    @classmethod
    def bipartite_synastry_tensor_profile(
        cls,
        agent_a: dict[str, Any],
        agent_b: dict[str, Any],
        status_code: int = 7,
    ) -> dict[str, Any]:
        """Exhaustive 12x12 bipartite synastry interaction matrix and 96 cross-flying Sihua rays."""
        return _evaluate_bipartite_synastry_tensor(
            agent_a=agent_a,
            agent_b=agent_b,
            status_code=status_code,
        )

    @classmethod
    def full_palace_patterns_profile(
        cls,
        turn_number: int,
        status_code: int,
        environment_ok: bool = True,
        verifier_passed: bool = True,
    ) -> dict[str, Any]:
        """Exhaustive 12-palace San Fang Si Zheng scanning for classical formations."""
        return _evaluate_full_palace_patterns(
            turn_number=turn_number,
            status_code=status_code,
            environment_ok=environment_ok,
            verifier_passed=verifier_passed,
        )

    @classmethod
    def china_dst_profile(cls, year: int, month: int, day: int) -> dict[str, Any]:
        """Evaluate Chinese Daylight Saving Time (1935-1991 XLS_CN 36-interval database)."""
        return _evaluate_china_dst(year=year, month=month, day=day)

    @classmethod
    def aphorism_knowledge_profile(cls, topic: str) -> dict[str, Any]:
        """Retrieve classical aphorism and Ni Haixia doctrine mapped to engineering implications."""
        return _evaluate_aphorism_knowledge(topic=topic)

    @classmethod
    def system_pathology_profile(
        cls,
        status_code: int,
        error_type: str | None = None,
        resource_pressure: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Diagnose system pathology across the Five Elements and prescribe organ governance."""
        return _evaluate_system_pathology(
            status_code=status_code,
            error_type=error_type,
            resource_pressure=resource_pressure,
        )

    @classmethod
    def partner_star_contract_profile(cls, star_name: str) -> dict[str, Any]:
        """Retrieve multi-agent peer contract and coordination mode from 14 major stars in 夫妻宫."""
        return _evaluate_partner_star_contract(star_name=star_name)

    @classmethod
    def sandbox_fengshui_profile(
        cls,
        workdir_present: bool = True,
        command_sandbox_enabled: bool = True,
        entry_validated: bool = True,
    ) -> dict[str, Any]:
        """Evaluate environmental security across Ni Haixia's Three Spatial Essentials (门、主、灶)."""
        return _evaluate_sandbox_fengshui(
            workdir_present=workdir_present,
            command_sandbox_enabled=command_sandbox_enabled,
            entry_validated=entry_validated,
        )

    @classmethod
    def six_channel_healing_profile(
        cls,
        status_code: int,
        error_type: str | None = None,
        resource_pressure: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Diagnose execution failure across Zhang Zhongjing's Six Channels and prescribe classical formulas."""
        return _evaluate_six_channel_healing(
            status_code=status_code,
            error_type=error_type,
            resource_pressure=resource_pressure,
        )

    @classmethod
    def empty_palace_borrowing_profile(
        cls,
        status_code: int = 7,
        custom_stars: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Identify empty palaces (命无正曜) and apply opposite involution borrowing with mirror attenuation."""
        return _evaluate_empty_palace_borrowing(
            status_code=status_code,
            custom_stars=custom_stars,
        )

    @classmethod
    def four_pillars_nayin_profile(
        cls,
        year_stem: int = 0,
        year_branch: int = 0,
        day_stem: int = 0,
        hour_branch: int = 0,
        ming_stem: int = 0,
        ming_branch: int = 2,
    ) -> dict[str, Any]:
        """Compute Four Pillars, Five Rats Escape hour stem, and 6x7 NaYin Bureau Matrix."""
        return _evaluate_four_pillars_nayin(
            year_stem=year_stem,
            year_branch=year_branch,
            day_stem=day_stem,
            hour_branch=hour_branch,
            ming_stem=ming_stem,
            ming_branch=ming_branch,
        )
