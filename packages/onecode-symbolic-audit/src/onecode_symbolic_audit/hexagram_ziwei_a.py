# ruff: noqa: F403, F405
"""Ziwei evaluation helpers, part a."""
from __future__ import annotations

import math
from typing import Any

from onecode_symbolic_audit.hexagram_ziwei_tables import *  # noqa: F403


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
    consecutive_repair_stalls: int = 0,
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
    if verifier_passed is False and consecutive_repair_stalls >= 1:
        return {
            "pattern": "陀罗暗滞",
            "level": "caution",
            "action": "pivot_hypothesis",
            "remedy": "force_algorithmic_pivot",
            "description": "Tuo Luo stagnation: repair patch produced no test progression. Pivot away from previous hypothesis.",
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
    stages: dict[str, dict[str, Any]] = {
        "exploration": {"phase_code": 1, "element": "wood", "tolerance": 1.0, "default_action": "discover"},
        "implementation": {"phase_code": 15, "element": "fire", "tolerance": 0.5, "default_action": "continue"},
        "verification": {"phase_code": 31, "element": "metal", "tolerance": 0.2, "default_action": "checkpoint"},
        "delivery": {"phase_code": 63, "element": "metal", "tolerance": 0.0, "default_action": "halt"},
    }
    stage_cfg = stages.get(macro_stage.lower(), stages["implementation"])
    tolerance = float(stage_cfg["tolerance"])
    is_error = event in {"test_failure", "verifier_failed", "syntax_error", "timeout", "halt"} or ((turn_status & 0b111111) in {0, 32})

    if not is_error:
        superposition_state = "harmonious_progression"
        policy_action = stage_cfg["default_action"]
        risk_level = "low"
    else:
        if tolerance >= 0.8:
            superposition_state = "exploratory_feedback_tolerated"
            policy_action = "discover"
            risk_level = "tolerated"
        elif tolerance >= 0.4:
            superposition_state = "repairable_defect"
            policy_action = "repair"
            risk_level = "medium"
        else:
            superposition_state = "fatal_regression_in_delivery"
            policy_action = "rollback"
            risk_level = "critical"

    return {
        "macro_stage": macro_stage,
        "macro_tolerance": tolerance,
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
    # 1. Triad partition invariance: calling engine across all 12 anchor branches
    triad_partition_ok = True
    water_triad = {0, 4, 8}
    fire_triad = {2, 6, 10}
    metal_triad = {1, 5, 9}
    wood_triad = {3, 7, 11}
    triads = (water_triad, metal_triad, fire_triad, wood_triad)
    for b in range(12):
        if b not in triads[b % 4]:
            triad_partition_ok = False
            break
        emperor_b = (0, 9, 6, 3)[b % 4]
        res_emperor = _evaluate_twelve_deities(turn_number=1, status_code=emperor_b, anchor_branch=b)
        if res_emperor["jiang_qian_shen"] != "将星" or not res_emperor["momentum_accelerated"]:
            triad_partition_ok = False
            break
        res_non_emperor = _evaluate_twelve_deities(turn_number=1, status_code=(emperor_b + 3) % 12, anchor_branch=b)
        if res_non_emperor["jiang_qian_shen"] == "将星" or res_non_emperor["momentum_accelerated"]:
            triad_partition_ok = False
            break

    # 2. Sui Po Opposite Involution and Governance Directive
    suipo_opposite_involution_ok = True
    for b in range(12):
        suipo_b = (b + 6) % 12
        res_suipo = _evaluate_twelve_deities(turn_number=1, status_code=suipo_b, anchor_branch=b)
        res_suijian = _evaluate_twelve_deities(turn_number=1, status_code=b, anchor_branch=b)
        if not (res_suipo["suipo_clash"] is True and res_suipo["sui_qian_shen"] == "岁破"):
            suipo_opposite_involution_ok = False
            break
        if not (res_suijian["suipo_clash"] is False and res_suijian["sui_qian_shen"] == "岁建"):
            suipo_opposite_involution_ok = False
            break
        if res_suipo["governance_directive"] != "barrier_synchronization_isolate_subtask":
            suipo_opposite_involution_ok = False
            break
        code_b = sovereign_codes[b]
        code_suipo = sovereign_codes[suipo_b]
        if code_suipo != (code_b ^ 63):
            suipo_opposite_involution_ok = False
            break

    # 3. Tian De and Long De harmonic grace shelter & sextile parity invariance
    even_difference_ok = True
    for b in range(12):
        td_b = (b + 9) % 12
        ld_b = (b + 7) % 12
        res_td = _evaluate_twelve_deities(turn_number=1, status_code=td_b, anchor_branch=b)
        res_ld = _evaluate_twelve_deities(turn_number=1, status_code=ld_b, anchor_branch=b)
        if not (res_td["grace_shelter"] and res_ld["grace_shelter"]):
            even_difference_ok = False
            break
        if res_td["sui_qian_shen"] != "天德" or res_ld["sui_qian_shen"] != "龙德":
            even_difference_ok = False
            break
        if res_td["governance_directive"] != "baseline_guarded_continue" or res_ld["governance_directive"] != "baseline_guarded_continue":
            even_difference_ok = False
            break
        if (td_b - ld_b) % 12 != 2:
            even_difference_ok = False
            break

    status = (
        "verified"
        if (triad_partition_ok and suipo_opposite_involution_ok and even_difference_ok)
        else "failed"
    )

    return {
        "status": status,
        "triad_cardinal_points": [0, 3, 6, 9],
        "triad_partition_verified": triad_partition_ok,
        "suipo_opposite_involution_verified": suipo_opposite_involution_ok,
        "tian_de_long_de_even_coupling": even_difference_ok,
    }


def _evaluate_flying_sihua_cascade(
    turn_number: int,
    status_code: int,
    macro_stage: str = "implementation",
    baseline_status: int = 7,
) -> dict[str, Any]:
    """Evaluate multi-layer Flying Sihua (跨宫飞星与四化多层叠象) for cascade clash prevention."""
    t_native = baseline_status % 10
    stage_stems = _STAGE_STEM_TABLE
    t_stage = stage_stems.get(macro_stage, 2)
    t_turn = max(0, turn_number - 1) % 10

    active_p = status_code % 12
    opposite_p = (active_p + 6) % 12

    native_tf = _SI_HUA_TABLE[t_native]
    turn_tf = _SI_HUA_TABLE[t_turn]
    stage_tf = _SI_HUA_TABLE[t_stage]

    def star_branch(star_name: str) -> int:
        offset = _STAR_CANONICAL_INDEX.get(star_name, 0)
        return (active_p + offset) % 12

    turn_ji_branch = star_branch(turn_tf[3])
    stage_ji_branch = star_branch(stage_tf[3])
    native_ji_branch = star_branch(native_tf[3])
    turn_lu_branch = star_branch(turn_tf[0])
    turn_quan_branch = star_branch(turn_tf[1])
    turn_ke_branch = star_branch(turn_tf[2])

    opposite_clash = (turn_ji_branch == opposite_p or stage_ji_branch == opposite_p)
    self_ji = (turn_ji_branch == active_p)
    double_ji = (turn_ji_branch == stage_ji_branch)
    lu_chong_po = ((turn_lu_branch + 6) % 12 == turn_ji_branch)
    native_clash = (native_ji_branch == active_p or native_ji_branch == opposite_p)

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
        "native_ji_star": native_tf[3],
        "native_ji_branch": native_ji_branch,
        "native_clash": native_clash,
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

    # Test all 4 macro stages across stems for collision dynamics
    stages_tested_ok = True
    for stage_name, stage_stem in _STAGE_STEM_TABLE.items():
        turn_for_match = stage_stem + 1
        res_double = _evaluate_flying_sihua_cascade(turn_number=turn_for_match, status_code=0, macro_stage=stage_name)
        if not (res_double["double_ji"] and res_double["damping_factor"] == 0.25 and res_double["action"] == "cascade_halt_quarantine"):
            stages_tested_ok = False
            break
        turn_for_nom = ((stage_stem + 5) % 10) + 1
        res_nom = _evaluate_flying_sihua_cascade(turn_number=turn_for_nom, status_code=0, macro_stage=stage_name)
        if res_nom["double_ji"] or res_nom["damping_factor"] <= res_double["damping_factor"]:
            stages_tested_ok = False
            break

    status = "verified" if (totality_ok and involution_ok and stages_tested_ok) else "failed"

    return {
        "status": status,
        "sihua_totality_verified": totality_ok,
        "duigong_involution_verified": involution_ok,
        "damping_monotonic_verified": stages_tested_ok,
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
        f = _CANONICAL_TIANFU_OPPOSITION_TABLE[z]
        f_of_f = _CANONICAL_TIANFU_OPPOSITION_TABLE[f]
        if f_of_f != z or (z + f) % 12 != 4:
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
        res = _evaluate_yang_tuo_clamping(turn_number=t + 1, status_code=_LUCUN_BRANCH_BY_STEM[t])
        lucun = res["lucun_branch"]
        yang = res["qing_yang_branch"]
        tuo = res["tuo_luo_branch"]
        if yang != _CLASSICAL_QINGYANG_BY_STEM[t] or tuo != _CLASSICAL_TUOLUO_BY_STEM[t]:
            clamping_midpoint_ok = False
            break
        dist = (yang - tuo) % 12
        midpoint_sum = (yang + tuo) % 12
        if dist != 2 or midpoint_sum != (2 * lucun) % 12:
            clamping_midpoint_ok = False
            break

    tianfu_axis_ok = True
    for z in range(12):
        res_zf = _evaluate_ziwei_tianfu_duality(status_code=z)
        if (res_zf["ziwei_branch"] + res_zf["tianfu_branch"]) % 12 != 4:
            tianfu_axis_ok = False
            break
        if res_zf["co_habitation"] != (res_zf["ziwei_branch"] in {2, 8}):
            tianfu_axis_ok = False
            break
        if _CANONICAL_TIANFU_OPPOSITION_TABLE[_CANONICAL_TIANFU_OPPOSITION_TABLE[z]] != z:
            tianfu_axis_ok = False
            break
    if not (_evaluate_ziwei_tianfu_duality(7)["co_habitation"] and _evaluate_ziwei_tianfu_duality(56)["co_habitation"]):
        tianfu_axis_ok = False

    status = (
        "verified"
        if (meridian_ok and antipodal_ok and involution_ok and fixed_points_ok and fixed_points_match_tai_pi and clamping_midpoint_ok and tianfu_axis_ok)
        else "failed"
    )

    return {
        "status": status,
        "ming_zhu_meridian_reflection_verified": meridian_ok,
        "shen_zhu_antipodal_invariance_verified": antipodal_ok,
        "ziwei_tianfu_involution_verified": involution_ok,
        "tai_pi_fixed_points_verified": fixed_points_ok and fixed_points_match_tai_pi,
        "yang_tuo_clamping_midpoint_verified": clamping_midpoint_ok,
        "tianfu_canonical_axis_verified": tianfu_axis_ok,
    }



__all__ = [
    "_evaluate_task_bureau",
    "_evaluate_self_sihua",
    "_evaluate_causal_origin",
    "_evaluate_triad_consensus",
    "_evaluate_ziwei_pattern",
    "_evaluate_shen_gong_anchorage",
    "_evaluate_star_brightness",
    "_evaluate_temporal_superposition",
    "_evaluate_sovereign_ring_certificate",
    "_evaluate_an_he_coupling_certificate",
    "_evaluate_shen_gong_certificate",
    "_evaluate_star_brightness_certificate",
    "_evaluate_star_dynamic_energy",
    "_evaluate_jie_shen_relief",
    "_evaluate_jie_shen_certificate",
    "_evaluate_twelve_deities",
    "_evaluate_twelve_deities_certificate",
    "_evaluate_flying_sihua_cascade",
    "_evaluate_flying_sihua_certificate",
    "_evaluate_triadic_synthesis",
    "_evaluate_triadic_synthesis_certificate",
    "_evaluate_ming_shen_zhu",
    "_evaluate_ziwei_tianfu_duality",
    "_evaluate_yang_tuo_clamping",
    "_evaluate_ziwei_tianfu_and_yangtuo_certificate",
]
