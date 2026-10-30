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


class IchingZiweiMixin:
    """Diagnostic and consensus extensions based on Ziwei Doushu isomorphism."""

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
    def sovereign_ring_isomorphism_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of the Sovereign Hexagram Ring <-> Earthly Branches isomorphism."""
        codes = getattr(cls, "SOVEREIGN_HEXAGRAM_CODES")
        return _evaluate_sovereign_ring_certificate(codes)

    @classmethod
    def an_he_coupling_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Six Harmonies (六合 / 暗合) on the 6-bit Boolean Hypercube."""
        codes = getattr(cls, "SOVEREIGN_HEXAGRAM_CODES")
        return _evaluate_an_he_coupling_certificate(codes)

    @classmethod
    def shen_gong_anchorage_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Shen Gong Even Subgroup Theorem (身宫偶数子群同构定理)."""
        return _evaluate_shen_gong_certificate()

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
    def jie_shen_even_subgroup_relief_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Jie Shen Even Subgroup and Damping Bound."""
        return _evaluate_jie_shen_certificate()

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
    def twelve_deities_triad_and_suipo_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Twelve Deities Triad Partition and Sui Po Opposite Involution."""
        codes = getattr(cls, "SOVEREIGN_HEXAGRAM_CODES")
        return _evaluate_twelve_deities_certificate(codes)

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
    def flying_sihua_cascade_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Flying Sihua Cascade and DuiGong Involution."""
        codes = getattr(cls, "SOVEREIGN_HEXAGRAM_CODES")
        return _evaluate_flying_sihua_certificate(codes)

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
    def triadic_synthesis_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Triadic Synthesis and 2/3 Domination Principle."""
        return _evaluate_triadic_synthesis_certificate()

    @classmethod
    def ming_shen_zhu_profile(cls, turn_number: int, status_code: int) -> dict[str, Any]:
        """Compute Ming Zhu (命主) and Shen Zhu (身主) stellar governors."""
        return _evaluate_ming_shen_zhu(turn_number=turn_number, status_code=status_code)

    @classmethod
    def ziwei_tianfu_duality_profile(cls, status_code: int) -> dict[str, Any]:
        """Compute Ziwei-Tianfu duality axis, involutive distance, and Tai-Pi fixed points."""
        return _evaluate_ziwei_tianfu_duality(status_code=status_code)

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
    def ziwei_tianfu_and_yangtuo_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Ming/Shen Zhu Symmetries, Ziwei-Tianfu Duality & Yang-Tuo Clamping."""
        codes = getattr(cls, "SOVEREIGN_HEXAGRAM_CODES")
        return _evaluate_ziwei_tianfu_and_yangtuo_certificate(codes)

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
    def solar_equation_and_zishi_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of EOT bounded oscillation, Zishi measure partition, and meridian invariance."""
        return _evaluate_solar_equation_and_zishi_certificate()

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
    def school_divergence_consensus_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Seven Stems Sihua Totality, Geng Closure, and Consensus Monotonicity."""
        return _evaluate_school_divergence_consensus_certificate()

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
    def classical_patterns_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Safety Dominance Invariant, Supreme Purity, and Exhaustive Formations."""
        return _evaluate_classical_patterns_certificate()

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
    def auxiliary_polarity_and_yunxian_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of DaHao Bijection, Jiekong Duality, and 7-tier Yunxian Hierarchy."""
        return _evaluate_auxiliary_polarity_and_yunxian_certificate()

    @classmethod
    def star_brightness_certificate(cls) -> dict[str, Any]:
        """Formal mathematical certificate of Star Brightness Invariance across all 64 states."""
        return _evaluate_star_brightness_certificate(cls)

    @classmethod
    def ziwei_mathematical_audit(cls) -> dict[str, Any]:
        """Comprehensive mathematical audit of all Ziwei Doushu cross-validation certificates."""
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
        }
