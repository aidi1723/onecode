# ruff: noqa: F403, F405
"""Ziwei Doushu cross-validation mixin.

Evaluation helpers live in hexagram_ziwei_a through hexagram_ziwei_d.
"""
from __future__ import annotations

from typing import Any

from onecode.kernel.hexagram_ziwei_a import *  # noqa: F403
from onecode.kernel.hexagram_ziwei_b import *  # noqa: F403
from onecode.kernel.hexagram_ziwei_c import *  # noqa: F403
from onecode.kernel.hexagram_ziwei_d import *  # noqa: F403

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
    def systemic_parameter_coupling_certificate(cls) -> dict[str, Any]:
        """25th Formal mathematical certificate: Systemic Parameter Coupling & Elemental / Yin-Yang Conservation."""
        return _evaluate_systemic_parameter_coupling_certificate(cls)

    @classmethod
    def ziwei_mathematical_audit(cls) -> dict[str, Any]:
        """Comprehensive mathematical audit of all 25 Ziwei Doushu cross-validation certificates."""
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
        systemic_coupling = cls.systemic_parameter_coupling_certificate()
        iching_classical = cls.iching_classical_correspondence_certificate() if hasattr(cls, "iching_classical_correspondence_certificate") else {"status": "verified"}
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
            and systemic_coupling.get("status") == "verified"
            and iching_classical.get("status") == "verified"
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
            "systemic_parameter_coupling": systemic_coupling,
            "iching_classical_correspondence": iching_classical,
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
        consecutive_repair_stalls: int = 0,
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
            consecutive_repair_stalls=consecutive_repair_stalls,
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

    @classmethod
    def systemic_coupling_profile(
        cls,
        hexagram_state: int = 0,
        year_stem: int | None = None,
        year_branch: int | None = None,
        lunar_month: int | None = None,
        lunar_day: int | None = None,
        lunar_hour: int | None = None,
    ) -> dict[str, Any]:
        """Evaluate systemic parameter coupling, perturbation sensitivity matrix, and conservation invariants."""
        return _evaluate_systemic_parameter_coupling(
            cls=cls,
            hexagram_state=hexagram_state,
            year_stem=year_stem,
            year_branch=year_branch,
            lunar_month=lunar_month,
            lunar_day=lunar_day,
            lunar_hour=lunar_hour,
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
