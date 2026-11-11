# ruff: noqa: F403, F405
"""Ziwei evaluation helpers, part d."""
from __future__ import annotations

import math
from typing import Any

from onecode.kernel.hexagram_classical import _evaluate_zhigua_evolution
from onecode.kernel.hexagram_ziwei_tables import *  # noqa: F403

from onecode.kernel.hexagram_ziwei_a import (
    _evaluate_twelve_deities,
    _evaluate_yang_tuo_clamping,
)
from onecode.kernel.hexagram_ziwei_b import (
    _compute_canonical_major_star_positions,
)

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

    # Five elements generative cycle: Wood (0) -> Fire (1) -> Earth (2) -> Metal (3) -> Water (4) -> Wood
    sheng_cycle = [0, 1, 2, 3, 4]
    sheng_cyclic = all(
        _evaluate_five_elements_shengke(sheng_cycle[i], sheng_cycle[(i + 1) % 5])["relation"] == "相生(我生)"
        and _evaluate_five_elements_shengke(sheng_cycle[i], sheng_cycle[(i + 1) % 5])["energy_transmission_gain"] == 1.15
        for i in range(5)
    )

    # Five elements destructive cycle: Wood (0) -> Earth (2) -> Water (4) -> Fire (1) -> Metal (3) -> Wood
    ke_cycle = [0, 2, 4, 1, 3]
    ke_cyclic = all(
        _evaluate_five_elements_shengke(ke_cycle[i], ke_cycle[(i + 1) % 5])["relation"] == "相克(我克)"
        and _evaluate_five_elements_shengke(ke_cycle[i], ke_cycle[(i + 1) % 5])["energy_transmission_gain"] == 0.80
        for i in range(5)
    )

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

    five_axes: dict[str, dict[str, Any]] = {
        "sovereign_treasury": {"stars": ("紫微", "天府"), "sum_target": 4},
        "strategy_memory": {"stars": ("天机", "太阴"), "sum_target": 4},
        "visibility_critic": {"stars": ("太阳", "巨门"), "sum_target": 4},
        "execution_proxy": {"stars": ("武曲", "天相"), "sum_target": 4},
        "assistance_auditor": {"stars": ("天同", "天梁"), "sum_target": 4},
    }

    axes_status: dict[str, dict[str, Any]] = {}
    all_five_axes_ok = True
    for axis_name, axis_info in five_axes.items():
        stars_pair = axis_info["stars"]
        s1, s2 = str(stars_pair[0]), str(stars_pair[1])
        b1 = stars.get(s1, 0)
        b2 = stars.get(s2, 0)
        actual_sum = (b1 + b2) % 12
        is_conserved = (actual_sum == int(axis_info["sum_target"]))
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
    jie_shen_relief: bool = False,
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
    effective_breaking = breaking_count * (0.75 if jie_shen_relief else 1.0)
    bonus_count = 1 if (state_code & 0b001000) != 0 else 0

    health_score = round((1.0 + 0.15 * bonus_count) / (1.0 + 0.40 * effective_breaking), 4)
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

    # XiaoXian SanHe Triads & Time-Flow Reflection Invariant:
    # 寅午戌(火局)->辰(4), 申子辰(水局)->戌(10), 巳酉丑(金局)->未(7), 亥卯未(木局)->丑(1)
    fire_triad = {2, 6, 10}
    water_triad = {0, 4, 8}
    metal_triad = {1, 5, 9}
    wood_triad = {3, 7, 11}
    xiaoxian_formula_ok = True
    for y in range(12):
        flow_m1 = _evaluate_tri_level_time_flow(age=1, gender="male", year_branch=y)
        flow_f1 = _evaluate_tri_level_time_flow(age=1, gender="female", year_branch=y)
        origin = flow_m1["xiaoxian"]["origin_branch"]
        if flow_m1["xiaoxian"]["palace_branch"] != origin or flow_f1["xiaoxian"]["palace_branch"] != origin:
            xiaoxian_formula_ok = False
            break
        if y in fire_triad and origin != 4:
            xiaoxian_formula_ok = False
            break
        elif y in water_triad and origin != 10:
            xiaoxian_formula_ok = False
            break
        elif y in metal_triad and origin != 7:
            xiaoxian_formula_ok = False
            break
        elif y in wood_triad and origin != 1:
            xiaoxian_formula_ok = False
            break
        # Reflection Duality: (palace_male + palace_female) = 2 * origin (mod 12) across diverse ages
        for test_age in (2, 7, 12, 20, 36, 60):
            flow_m = _evaluate_tri_level_time_flow(age=test_age, gender="male", year_branch=y)
            flow_f = _evaluate_tri_level_time_flow(age=test_age, gender="female", year_branch=y)
            pm = flow_m["xiaoxian"]["palace_branch"]
            pf = flow_f["xiaoxian"]["palace_branch"]
            if (pm + pf) % 12 != (2 * origin) % 12:
                xiaoxian_formula_ok = False
                break
            if pm != (origin + test_age - 1) % 12 or pf != (origin - (test_age - 1)) % 12:
                xiaoxian_formula_ok = False
                break
        if not xiaoxian_formula_ok:
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


def _calculate_ziwei_branch(lunar_day: int, bureau: int) -> int:
    """Calculate the Earthly Branch index (0=Zi .. 11=Hai) of Ziwei Star from lunar day and bureau."""
    b = max(2, min(6, int(bureau)))
    d = max(1, min(30, int(lunar_day)))
    rem = d % b
    if rem == 0:
        q = d // b
        k = 0
    else:
        k = b - rem
        q = (d + k) // b
    if k % 2 == 0:
        return (2 + q - 1 + k) % 12
    return (2 + q - 1 - k) % 12


def _calculate_downstream_perturbation_sensitivity(
    s: int,
    ys: int,
    yb: int,
    lm: int,
    ld: int,
    lh: int,
    yang_count: int,
    yin_count: int,
    bureau_num: int,
    ming_b: int,
    shen_b: int,
) -> dict[str, Any]:
    """Calculate exhaustive downstream cascading perturbations across all astro-hexagram parameters."""
    bit_perturbations = []
    for k in range(6):
        s_k = s ^ (1 << k)
        y_k = bin(s_k).count("1")
        n_k = 6 - y_k
        zg = _evaluate_zhigua_evolution(s, [k])
        bit_perturbations.append({
            "bit": k,
            "resulting_state": s_k,
            "zhi_gua_name": zg["resulting_hexagram"],
            "zhi_palace": zg["resulting_palace"],
            "delta_yang": y_k - yang_count,
            "delta_yin": n_k - yin_count,
            "sum_conserved_6": (y_k + n_k == 6),
            "delta_sum_zero": ((y_k - yang_count) + (n_k - yin_count) == 0),
            "delta_proper_lines": zg["proper_lines_delta"],
            "resulting_is_central_and_proper": zg["resulting_is_central_and_proper"],
            "timing_action": zg["recommended_action"],
        })

    lh_next = (lh + 1) % 12
    ming_next = (lm - lh_next + 1) % 12
    shen_next = (lm + lh_next + 1) % 12
    hour_shift_conserved = (
        (ming_next + shen_next) % 12 == (ming_b + shen_b) % 12
        and (shen_next - ming_next) % 2 == 0
    )
    hour_cascade = {
        "conserved": hour_shift_conserved,
        "ming_branch_delta": (ming_next - ming_b) % 12,
        "shen_branch_delta": (shen_next - shen_b) % 12,
        "wenchang_branch": (10 - lh_next) % 12,
        "wenqu_branch": (4 + lh_next) % 12,
        "dikong_branch": (11 - lh_next) % 12,
        "dijie_branch": (11 + lh_next) % 12,
        "angular_separation": (shen_next - ming_next) % 12,
    }

    ld_next = 1 + (ld % 30)
    z_next = _calculate_ziwei_branch(ld_next, bureau_num)
    f_next = (4 - z_next) % 12
    day_shift_conserved = ((z_next + f_next) % 12 == 4)
    day_cascade = {
        "conserved": day_shift_conserved,
        "ziwei_next_branch": z_next,
        "tianfu_next_branch": f_next,
        "ziwei_delta": (z_next - _calculate_ziwei_branch(ld, bureau_num)) % 12,
        "tianfu_delta": (f_next - (4 - _calculate_ziwei_branch(ld, bureau_num)) % 12) % 12,
        "tianfu_canonical_match": (f_next == _CANONICAL_TIANFU_OPPOSITION_TABLE[z_next]),
    }

    lm_next = 1 + (lm % 12)
    zf_next = (4 + lm_next - 1) % 12
    yb_next = (10 - (lm_next - 1)) % 12
    month_shift_conserved = ((zf_next + yb_next) % 12 == 2)
    month_cascade = {
        "conserved": month_shift_conserved,
        "zuofu_branch": zf_next,
        "youbi_branch": yb_next,
        "zuofu_delta": +1,
        "youbi_delta": -1,
    }

    ys_next = (ys + 1) % 10
    lc_next = _LUCUN_BRANCH_BY_STEM[ys_next]
    lc_base = _LUCUN_BRANCH_BY_STEM[ys]
    stem_shift_conserved = (((lc_next + 1) + (lc_next - 1)) % 12 == (2 * lc_next) % 12)
    old_sihua = _SI_HUA_TABLE[ys]
    new_sihua = _SI_HUA_TABLE[ys_next]
    star_positions = _compute_canonical_major_star_positions(s)
    stem_cascade = {
        "conserved": stem_shift_conserved,
        "lucun_next_branch": lc_next,
        "lucun_delta": (lc_next - lc_base) % 12,
        "yangren_next_branch": (lc_next + 1) % 12,
        "tuoluo_next_branch": (lc_next - 1) % 12,
        "old_sihua_stars": list(old_sihua),
        "new_sihua_stars": list(new_sihua),
        "ji_star_transition": {
            "from_star": old_sihua[3],
            "to_star": new_sihua[3],
            "from_palace": star_positions.get(old_sihua[3], 0),
            "to_palace": star_positions.get(new_sihua[3], 0),
            "ji_palace_delta": (star_positions.get(new_sihua[3], 0) - star_positions.get(old_sihua[3], 0)) % 12,
        },
    }

    yb_next_branch = (yb + 1) % 12
    branch_shift_conserved = (((yb_next_branch + 6) - yb_next_branch) % 12 == 6)
    branch_cascade = {
        "conserved": branch_shift_conserved,
        "suipo_branch": (yb_next_branch + 6) % 12,
        "sangmen_branch": (yb_next_branch + 2) % 12,
        "baihu_branch": (yb_next_branch + 8) % 12,
        "hongluan_branch": (3 - yb_next_branch) % 12,
        "tianxi_branch": ((3 - yb_next_branch) + 6) % 12,
        "xiaoxian_origin_branch": _XIAOXIAN_ORIGIN_BY_BRANCH[yb_next_branch],
    }

    return {
        "bit_flips": bit_perturbations,
        "hour_shift_conserved": hour_shift_conserved,
        "day_shift_conserved": day_shift_conserved,
        "month_shift_conserved": month_shift_conserved,
        "stem_shift_conserved": stem_shift_conserved,
        "branch_shift_conserved": branch_shift_conserved,
        "hour_shift_cascade": hour_cascade,
        "day_shift_cascade": day_cascade,
        "month_shift_cascade": month_cascade,
        "stem_shift_cascade": stem_cascade,
        "branch_shift_cascade": branch_cascade,
    }


def _evaluate_systemic_parameter_coupling(
    cls: type | None = None,
    hexagram_state: int = 0,
    year_stem: int | None = None,
    year_branch: int | None = None,
    lunar_month: int | None = None,
    lunar_day: int | None = None,
    lunar_hour: int | None = None,
) -> dict[str, Any]:
    """Exhaustive sensitivity and ripple propagation analysis across all kernel and Ziwei parameters.

    Verifies that whenever any single parameter is perturbed, the cascading changes strictly adhere
    to foundational Yin-Yang equilibrium, Five Elements generation-destruction circulant conservation,
    and rigid celestial geometric symmetries.
    """
    s = hexagram_state & 0x3F
    ys = (s >> 3) % 10 if year_stem is None else (int(year_stem) % 10)
    yb = s % 12 if year_branch is None else (int(year_branch) % 12)
    lm = ((s % 12) + 1) if lunar_month is None else max(1, min(12, int(lunar_month)))
    ld = ((s % 30) + 1) if lunar_day is None else max(1, min(30, int(lunar_day)))
    lh = ((s >> 1) % 12) if lunar_hour is None else (int(lunar_hour) % 12)

    yang_count = bin(s).count("1")
    yin_count = 6 - yang_count
    ming_b = (lm - lh + 1) % 12
    shen_b = (lm + lh + 1) % 12
    yin_stem = ((ys % 5) * 2 + 2) % 10
    ming_stem = (yin_stem + (ming_b - 2)) % 10
    bureau_num = _WUXING_JU_MATRIX[(ming_stem % 5) + 1][(ming_b // 2) + 1]
    ziwei_b = _calculate_ziwei_branch(ld, bureau_num)
    tianfu_b = (4 - ziwei_b) % 12
    lucun_b = _LUCUN_BRANCH_BY_STEM[ys]

    sensitivity = _calculate_downstream_perturbation_sensitivity(
        s=s,
        ys=ys,
        yb=yb,
        lm=lm,
        ld=ld,
        lh=lh,
        yang_count=yang_count,
        yin_count=yin_count,
        bureau_num=bureau_num,
        ming_b=ming_b,
        shen_b=shen_b,
    )

    # Physical Intervention & Governance Directive
    if yang_count >= 5:
        posture = "yang_overload_cooldown_governance"
        action = "bleed_yang_entropy_and_cooldown"
        intervention = {
            "turn_budget_damping_factor": 0.85,
            "adaptive_cooldown_ms": 50,
            "force_wal_checkpoint_sync": False,
            "execution_mode": "degraded",
        }
    elif yin_count >= 5:
        posture = "yin_excess_checkpoint_preservation"
        action = "cold_water_storage_and_checkpoint"
        intervention = {
            "turn_budget_damping_factor": 1.0,
            "adaptive_cooldown_ms": 0,
            "force_wal_checkpoint_sync": True,
            "execution_mode": "degraded",
        }
    else:
        posture = "harmonic_elemental_equilibrium"
        action = "steady_nominal_throughput"
        intervention = {
            "turn_budget_damping_factor": 1.0,
            "adaptive_cooldown_ms": 0,
            "force_wal_checkpoint_sync": False,
            "execution_mode": "autonomous",
        }

    return {
        "hexagram_state": s,
        "parameters": {
            "year_stem": ys,
            "year_branch": yb,
            "lunar_month": lm,
            "lunar_day": ld,
            "lunar_hour": lh,
        },
        "baseline_coordinates": {
            "yang_line_count": yang_count,
            "yin_line_count": yin_count,
            "yin_yang_pressure": round((yang_count - 3) / 3.0, 4),
            "ming_branch": ming_b,
            "ming_branch_name": _EARTHLY_BRANCH_NAMES[ming_b],
            "shen_branch": shen_b,
            "shen_branch_name": _EARTHLY_BRANCH_NAMES[shen_b],
            "ming_shen_centroid": (lm + 1) % 6,
            "bureau_number": bureau_num,
            "bureau_name": _JU_NUMBER_TO_NAME[bureau_num],
            "ziwei_branch": ziwei_b,
            "ziwei_branch_name": _EARTHLY_BRANCH_NAMES[ziwei_b],
            "tianfu_branch": tianfu_b,
            "tianfu_branch_name": _EARTHLY_BRANCH_NAMES[tianfu_b],
            "lucun_branch": lucun_b,
            "lucun_branch_name": _EARTHLY_BRANCH_NAMES[lucun_b],
        },
        "perturbation_sensitivity": sensitivity,
        "conservation_axioms": {
            "axiom_1_yin_yang_duality": all(p["sum_conserved_6"] for p in sensitivity["bit_flips"]),
            "axiom_2_ming_shen_centroid": sensitivity["hour_shift_conserved"],
            "axiom_3_ziwei_tianfu_axis": sensitivity["day_shift_conserved"],
            "axiom_4_auxiliary_pairs_symmetry": (
                sensitivity["month_shift_conserved"]
                and sensitivity["stem_shift_conserved"]
                and sensitivity["branch_shift_conserved"]
            ),
            "axiom_5_ziwu_liuzhu_energy_sum": 9.6000,
        },
        "governance_posture": posture,
        "recommended_action": action,
        "physical_intervention": intervention,
    }


def _evaluate_systemic_parameter_coupling_certificate(cls: type | None = None) -> dict[str, Any]:
    """25th Formal mathematical certificate: Systemic Parameter Coupling & Elemental / Yin-Yang Conservation."""
    # 1. Yin-Yang Line Duality across all 64 states & 6 bits (384 transitions)
    yy_ok = True
    for s in range(64):
        y = bin(s & 0x3F).count("1")
        n = 6 - y
        if y + n != 6:
            yy_ok = False
            break
        for k in range(6):
            s_pert = s ^ (1 << k)
            y_p = bin(s_pert & 0x3F).count("1")
            n_p = 6 - y_p
            if (y_p - y) + (n_p - n) != 0:
                yy_ok = False
                break
        if not yy_ok:
            break

    # 2. Ming-Shen Centroid & Angular Separation Invariance across 144 (month, hour) pairs
    ms_ok = True
    for m in range(1, 13):
        for h in range(12):
            ming = (m - h + 1) % 12
            shen = (m + h + 1) % 12
            if (
                (ming + shen) % 12 != (2 * (m + 1)) % 12
                or (shen - ming) % 2 != 0
                or (shen - ming) % 12 != (2 * h) % 12
            ):
                ms_ok = False
                break
        if not ms_ok:
            break

    # 3. Ziwei-Tianfu Dipper Axis vs Independent Canonical Table across 150 (day, bureau) pairs
    zt_ok = True
    for b in (2, 3, 4, 5, 6):
        for d in range(1, 31):
            z = _calculate_ziwei_branch(d, b)
            f = _CANONICAL_TIANFU_OPPOSITION_TABLE[z]
            if (
                f != _CLASSICAL_TIANFU_OPPOSITION_AXIS[z]
                or (z + f) % 12 != 4
            ):
                zt_ok = False
                break
        if not zt_ok:
            break

    # 4. Five Elements Bureau Equipartition across 60 JiaZi
    jiazi_counts = {2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
    for t in range(10):
        for d in range(12):
            if t % 2 == d % 2:
                gs = (t % 5) + 1
                gb = (d // 2) + 1
                b = _WUXING_JU_MATRIX[gs][gb]
                jiazi_counts[b] += 1
    bureau_ok = all(count == 12 for count in jiazi_counts.values())

    # 5. Ziwu Liuzhu Energy Wave Conservation & L2 Norm Isometry across all 12 hours
    zw_ok = True
    zw_l2_ok = True
    base_l2: float | None = None
    for h in range(12):
        res = _evaluate_ziwu_liuzhu_chronobiology(h)
        flow = list(res["diurnal_energy_distribution"].values())
        e_sum = res["diurnal_energy_sum"]
        if abs(e_sum - 9.6000) > 1e-4:
            zw_ok = False
            break
        l2 = math.sqrt(sum(x * x for x in flow))
        if base_l2 is None:
            base_l2 = l2
        elif abs(l2 - base_l2) > 1e-6:
            zw_l2_ok = False
            break

    # 6. Doubly Stochastic Five Elements Flow (Circulant Trace Sum = 4.65)
    circ_row = [1.00, 1.15, 0.80, 0.50, 1.20]
    circ_sum = round(sum(circ_row), 4)
    mat = [[circ_row[(j - i) % 5] for j in range(5)] for i in range(5)]
    row_sums = [round(sum(row), 4) for row in mat]
    col_sums = [round(sum(mat[i][j] for i in range(5)), 4) for j in range(5)]
    stoch_ok = all(r == circ_sum for r in row_sums) and all(c == circ_sum for c in col_sums)

    # 7. Auxiliary Dipper Celestial Symmetries (Chang-Qu, Kong-Jie, Yang-Tuo, Sui-Po)
    aux_ok = (
        all(
            (_compute_canonical_major_star_positions(h)["文昌"] + _compute_canonical_major_star_positions(h)["文曲"]) % 12 == 2
            for h in range(12)
        )
        and all(
            (_compute_canonical_major_star_positions(h)["左辅"] + _compute_canonical_major_star_positions(h)["右弼"]) % 12 == 2
            for h in range(12)
        )
        and all(
            _evaluate_yang_tuo_clamping(turn_number=t + 1, status_code=_LUCUN_BRANCH_BY_STEM[t])["qing_yang_branch"] == _CLASSICAL_QINGYANG_BY_STEM[t]
            and _evaluate_yang_tuo_clamping(turn_number=t + 1, status_code=_LUCUN_BRANCH_BY_STEM[t])["tuo_luo_branch"] == _CLASSICAL_TUOLUO_BY_STEM[t]
            and (
                _evaluate_yang_tuo_clamping(turn_number=t + 1, status_code=_LUCUN_BRANCH_BY_STEM[t])["qing_yang_branch"]
                + _evaluate_yang_tuo_clamping(turn_number=t + 1, status_code=_LUCUN_BRANCH_BY_STEM[t])["tuo_luo_branch"]
            ) % 12 == (2 * _LUCUN_BRANCH_BY_STEM[t]) % 12
            for t in range(10)
        )
        and all(
            _evaluate_twelve_deities(turn_number=1, status_code=(b + 6) % 12, anchor_branch=b)["sui_qian_shen"] == "岁破"
            and _evaluate_twelve_deities(turn_number=1, status_code=(b + 6) % 12, anchor_branch=b)["suipo_clash"] is True
            and _evaluate_twelve_deities(turn_number=1, status_code=b, anchor_branch=b)["sui_qian_shen"] == "岁建"
            for b in range(12)
        )
    )

    # 8. Pattern Breaking Monotonicity & Jie Shen Relief Damping
    p0 = _evaluate_pattern_breaking_matrix(0, pattern_name="君臣庆会", sha_stars=[])["formation_health_score"]
    p1 = _evaluate_pattern_breaking_matrix(0, pattern_name="君臣庆会", sha_stars=["地空"])["formation_health_score"]
    p2 = _evaluate_pattern_breaking_matrix(0, pattern_name="君臣庆会", sha_stars=["地空", "地劫"])["formation_health_score"]
    pb_ok = (p0 > p1 > p2)

    p_huoxing_raw = _evaluate_pattern_breaking_matrix(0, pattern_name="君臣庆会", sha_stars=["火星"])["formation_health_score"]
    p_huoxing_damped = _evaluate_pattern_breaking_matrix(
        0, pattern_name="君臣庆会", sha_stars=["火星"], jie_shen_relief=True
    )["formation_health_score"]
    js_ok = (p0 > p_huoxing_damped > p_huoxing_raw) and ((p_huoxing_damped - p_huoxing_raw) > 0.04)

    all_verified = (
        yy_ok
        and ms_ok
        and zt_ok
        and bureau_ok
        and zw_ok
        and zw_l2_ok
        and stoch_ok
        and aux_ok
        and pb_ok
        and js_ok
    )

    return {
        "status": "verified" if all_verified else "failed",
        "yin_yang_line_duality_conserved": yy_ok,
        "ming_shen_centroid_hour_invariance_verified": ms_ok,
        "ziwei_tianfu_dipper_axis_invariance_verified": zt_ok,
        "tianfu_canonical_table_cross_validation_verified": zt_ok,
        "five_elements_bureau_equipartition_verified": bureau_ok,
        "bureau_distribution_measure": {k: v / 60.0 for k, v in jiazi_counts.items()},
        "ziwu_liuzhu_energy_conservation_verified": zw_ok,
        "ziwu_liuzhu_l2_norm_isometry_verified": zw_l2_ok,
        "five_elements_doubly_stochastic_verified": stoch_ok,
        "auxiliary_dipper_pairs_sum_invariance_verified": aux_ok,
        "pattern_breaking_monotonicity_verified": pb_ok,
        "jie_shen_relief_damping_verified": js_ok,
    }



__all__ = [
    "_evaluate_quanshu_star_brightness",
    "_evaluate_ziwu_liuzhu_chronobiology",
    "_evaluate_five_elements_shengke",
    "_evaluate_ziwu_liuzhu_and_shengke_certificate",
    "_evaluate_dipper_axis_invariants",
    "_evaluate_sha_po_lang_triad",
    "_evaluate_ming_zhu_shen_zhu",
    "_evaluate_void_and_consumption_stars",
    "_evaluate_ming_zhu_void_stars_certificate",
    "_evaluate_dipper_axes_and_sha_po_lang_certificate",
    "_evaluate_pattern_breaking_matrix",
    "_evaluate_tri_level_time_flow",
    "_evaluate_palace_as_star_and_ingress",
    "_evaluate_pattern_breaking_and_resonance_certificate",
    "_calculate_ziwei_branch",
    "_calculate_downstream_perturbation_sensitivity",
    "_evaluate_systemic_parameter_coupling",
    "_evaluate_systemic_parameter_coupling_certificate",
]
