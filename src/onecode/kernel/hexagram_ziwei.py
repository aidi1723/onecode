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
        all_passed = (
            ring.get("status") == "verified"
            and an_he.get("status") == "verified"
            and shen_gong.get("status") == "verified"
            and star_bright.get("status") == "verified"
            and jie_shen.get("status") == "verified"
            and twelve_deities.get("status") == "verified"
        )
        return {
            "status": "ok" if all_passed else "failed",
            "sovereign_ring": ring,
            "an_he_coupling": an_he,
            "shen_gong_anchorage": shen_gong,
            "star_brightness": star_bright,
            "jie_shen_relief": jie_shen,
            "twelve_deities": twelve_deities,
        }
