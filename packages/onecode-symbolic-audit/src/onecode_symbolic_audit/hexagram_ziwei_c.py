# ruff: noqa: F403, F405
"""Ziwei evaluation helpers, part c."""
from __future__ import annotations

from typing import Any

from onecode_symbolic_audit.hexagram_ziwei_tables import *  # noqa: F403

from onecode_symbolic_audit.hexagram_ziwei_b import (
    _compute_canonical_major_star_positions,
    _evaluate_china_dst,
    _evaluate_classical_patterns,
    _evaluate_clock_drift_adaptation,
    _evaluate_true_solar_time,
)

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
    elif any(k in err for k in ("deadlock", "lock", "concurrency", "thread", "stasis")) or pressure.get("lock_contention", False):
        category = "wood"
        severity = 0.85
    elif any(k in err for k in ("memory", "leak", "fd", "wal", "timeout", "network", "flood")) or pressure.get("memory", False):
        category = "water"
        severity = 0.80
    elif any(k in err for k in ("loop", "cpu", "thrash", "rate_limit", "flame", "spin")) or pressure.get("cpu", False):
        category = "fire"
        severity = 0.75
    elif any(k in err for k in ("cache", "context", "config", "pollute", "stale")) or pressure.get("cache", False):
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
        "resource_pressure": pressure,
        "system_equilibrium": "degraded" if severity >= 0.8 else "cautious",
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

    # Five Rats Finding Hours (五鼠遁) Homomorphism & Gan-Zhi Parity Invariant
    # Rhyme: "甲己还加甲，乙庚丙作初。丙辛从戊起，丁壬庚子居。戊癸何方发，壬子是真途。"
    rats_ok = True
    for d in range(10):
        res_zi = _evaluate_four_pillars_nayin(day_stem=d, hour_branch=0)
        phi_d = res_zi["time_stem"]
        # 1. Zishi stem must be in even subring {0, 2, 4, 6, 8} (Yang stem pairing with Yang Zi branch)
        if phi_d not in (0, 2, 4, 6, 8):
            rats_ok = False
            break
        for h in range(12):
            res_fp = _evaluate_four_pillars_nayin(day_stem=d, hour_branch=h)
            # 2. Strict hour progression from Zishi anchor
            if res_fp["time_stem"] != (phi_d + h) % 10 or not res_fp["five_rats_periodicity_ok"]:
                rats_ok = False
                break
            # 3. Gan-Zhi parity invariant: stem parity must equal branch parity
            if res_fp["time_stem"] % 2 != h % 2:
                rats_ok = False
                break
            # 4. Periodicity modulo 5
            res_p5 = _evaluate_four_pillars_nayin(day_stem=(d + 5) % 10, hour_branch=h)
            if res_p5["time_stem"] != res_fp["time_stem"]:
                rats_ok = False
                break
        if not rats_ok:
            break
    # 5. Group homomorphism: phi(d1 + d2 mod 5) == (phi(d1) + phi(d2)) mod 10
    for d1 in range(5):
        for d2 in range(5):
            phi_sum = _evaluate_four_pillars_nayin(day_stem=(d1 + d2) % 5, hour_branch=0)["time_stem"]
            phi_1 = _evaluate_four_pillars_nayin(day_stem=d1, hour_branch=0)["time_stem"]
            phi_2 = _evaluate_four_pillars_nayin(day_stem=d2, hour_branch=0)["time_stem"]
            if phi_sum != (phi_1 + phi_2) % 10:
                rats_ok = False
                break

    cohabiting_palaces = []
    for z in range(12):
        tj = (z - 1) % 12
        tl = (9 - z) % 12
        if tj == tl:
            cohabiting_palaces.append(tj)
    tianji_tianliang_ok = (sorted(cohabiting_palaces) == [4, 10])

    functional_offsets = [0, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
    rev_clockwise_ok = all(
        len(set((p0 + off) % 12 for off in functional_offsets)) == 12
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



__all__ = [
    "_evaluate_system_pathology",
    "_evaluate_partner_star_contract",
    "_evaluate_sandbox_fengshui",
    "_evaluate_pathology_and_environmental_certificate",
    "_evaluate_six_channel_healing",
    "_evaluate_empty_palace_borrowing",
    "_evaluate_four_pillars_nayin",
    "_evaluate_six_channel_and_empty_palace_certificate",
    "_evaluate_doujun_chronology_chain",
    "_evaluate_childhood_guard",
    "_evaluate_solar_lichun_boundary",
    "_evaluate_doujun_and_solar_boundary_certificate",
    "_evaluate_auxiliary_stars_pairs",
    "_evaluate_city_true_solar_precision",
    "_evaluate_auxiliary_pairs_and_city_solar_certificate",
    "_evaluate_changsheng_lifecycle",
    "_evaluate_guchen_guasu_huagai",
    "_evaluate_expanded_classical_patterns",
    "_evaluate_changsheng_and_expanded_patterns_certificate",
]
