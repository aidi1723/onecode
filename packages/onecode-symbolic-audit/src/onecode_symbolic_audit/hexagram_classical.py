"""OneCode Classical I Ching (周易) Canonical Alignment & Evolution Engine.

This module formalizes the exact correspondence between the OneCode 6-bit Boolean
Hypercube state space Q_6 and the classical Book of Changes (周易):
1. King Wen 64 Hexagram Sequence (文王六十四卦卦序、全卦名与卦象释义).
2. King Wen 32 Pairs Involution Theorem (二二相耦，非覆即变：28 综卦与 4 错卦严格对偶).
3. Jing Fang Eight Palaces System (京房八宫卦与世应次序).
4. Moving Lines (动爻) and Resulting Hexagram (之卦) temporal evolution dynamics.
5. Centrality & Line Correctness (当位与中正之道，水火既济最优解与火水未济穷变通久).
"""

from __future__ import annotations

from typing import Any


# Canonical trigrams in OneCode (RULE_SCHEMA_V2):
# kun: 0, zhen: 1, kan: 2, dui: 3, gen: 4, li: 5, xun: 6, qian: 7
_TRIGRAM_NAMES: dict[int, str] = {
    0: "坤", 1: "震", 2: "坎", 3: "兑", 4: "艮", 5: "离", 6: "巽", 7: "乾"
}

_TRIGRAM_SYMBOLS: dict[int, str] = {
    0: "地", 1: "雷", 2: "水", 3: "泽", 4: "山", 5: "火", 6: "风", 7: "天"
}

# The 64 Hexagrams in the classical King Wen sequence:
# (King Wen Order 1..64, Outer Trigram, Inner Trigram, Traditional Name, Da Xiang / Judgement)
KING_WEN_CANONICAL_TABLE: tuple[tuple[int, int, int, str, str], ...] = (
    (1, 7, 7, "乾为天", "天行健，君子以自强不息"),
    (2, 0, 0, "坤为地", "地势坤，君子以厚德载物"),
    (3, 2, 1, "水雷屯", "云雷屯，君子以经纶"),
    (4, 4, 2, "山水蒙", "山下出泉蒙，君子以果行育德"),
    (5, 2, 7, "水天需", "云上于天需，君子以饮食宴乐"),
    (6, 7, 2, "天水讼", "天与水违行讼，君子以作事谋始"),
    (7, 0, 2, "地水师", "地中有水师，君子以容民畜众"),
    (8, 2, 0, "水地比", "地上有水比，先王以建万国亲诸侯"),
    (9, 6, 7, "风天小畜", "风行天上小畜，君子以懿文德"),
    (10, 7, 3, "天泽履", "上天下泽履，君子以辨上下定民志"),
    (11, 0, 7, "地天泰", "天地交泰，后以财成天地之道"),
    (12, 7, 0, "天地否", "天地不交否，君子以俭德辟难"),
    (13, 7, 5, "天火同人", "天与火同人，君子以类族辨物"),
    (14, 5, 7, "火天大有", "火在天上大有，君子以遏恶扬善"),
    (15, 0, 4, "地山谦", "地中有山谦，君子以裒多益寡"),
    (16, 1, 0, "雷地豫", "雷出地奋豫，先王以作乐崇德"),
    (17, 3, 1, "泽雷随", "泽中有雷随，君子以向晦入宴息"),
    (18, 4, 6, "山风蛊", "山下有风蛊，君子以振民育德"),
    (19, 0, 3, "地泽临", "泽上有地临，君子以教思无穷"),
    (20, 6, 0, "风地观", "风行地上观，先王以省方观民设教"),
    (21, 5, 1, "火雷噬嗑", "雷电噬嗑，先王以明罚敕法"),
    (22, 4, 5, "山火贲", "山下有火贲，君子以明庶政无敢折狱"),
    (23, 4, 0, "山地剥", "山附于地剥，上以厚下安宅"),
    (24, 0, 1, "地雷复", "雷在地中复，先王以至日闭关"),
    (25, 7, 1, "天雷无妄", "天下雷行物与无妄，先王以茂对时育万物"),
    (26, 4, 7, "山天大畜", "天在山中大畜，君子以多识前言往行"),
    (27, 4, 1, "山雷颐", "山下有雷颐，君子以慎言语节饮食"),
    (28, 3, 6, "泽风大过", "泽灭木大过，君子以独立不惧"),
    (29, 2, 2, "坎为水", "水洊至习坎，君子以常德行习教事"),
    (30, 5, 5, "离为火", "明两作离，大人以继明照于四方"),
    (31, 3, 4, "泽山咸", "山上有泽咸，君子以虚受人"),
    (32, 1, 6, "雷风恒", "雷风恒，君子以立不易方"),
    (33, 7, 4, "天山遁", "天下有山遁，君子以远小人"),
    (34, 1, 7, "雷天大壮", "雷在天上大壮，君子以非礼弗履"),
    (35, 5, 0, "火地晋", "明出地上晋，君子以自昭明德"),
    (36, 0, 5, "地火明夷", "明入地中明夷，君子以莅众用晦而明"),
    (37, 6, 5, "风火家人", "风自火出家人，君子以言有物而行有恒"),
    (38, 5, 3, "火泽睽", "上火下泽睽，君子以同而异"),
    (39, 2, 4, "水山蹇", "山上有水蹇，君子以反身修德"),
    (40, 1, 2, "雷水解", "雷雨作解，君子以赦过宥罪"),
    (41, 4, 3, "山泽损", "山下有泽损，君子以惩忿窒欲"),
    (42, 6, 1, "风雷益", "风雷益，君子以见善则迁有过则改"),
    (43, 3, 7, "泽天夬", "泽上于天夬，君子以施禄及下"),
    (44, 7, 6, "天风姤", "天下有风姤，后以施命诰四方"),
    (45, 3, 0, "泽地萃", "泽上于地萃，君子以除戎器戒不虞"),
    (46, 0, 6, "地风升", "地中生木升，君子以顺德积小以高大"),
    (47, 3, 2, "泽水困", "泽无水困，君子以致命遂志"),
    (48, 2, 6, "水风井", "木上有水井，君子以劳民劝相"),
    (49, 3, 5, "泽火革", "泽中有火革，君子以治历明时"),
    (50, 5, 6, "火风鼎", "木上有火鼎，君子以正位凝命"),
    (51, 1, 1, "震为雷", "洊雷震，君子以恐惧修省"),
    (52, 4, 4, "艮为山", "兼山艮，君子以思不出其位"),
    (53, 6, 4, "风山渐", "山上有木渐，君子以居贤德善俗"),
    (54, 1, 3, "雷泽归妹", "泽上有雷归妹，君子以永终知敝"),
    (55, 1, 5, "雷火丰", "雷电皆至丰，君子以折狱致刑"),
    (56, 5, 4, "火山旅", "山上有火旅，君子以明慎用刑而不留狱"),
    (57, 6, 6, "巽为风", "随风巽，君子以申命行事"),
    (58, 3, 3, "兑为泽", "丽泽兑，君子以朋友讲习"),
    (59, 6, 2, "风水涣", "风行水上涣，先王以享于上帝立庙"),
    (60, 2, 3, "水泽节", "泽上有水节，君子以制数度议德行"),
    (61, 6, 3, "风泽中孚", "泽上有风中孚，君子以议狱缓死"),
    (62, 1, 4, "雷山小过", "山上有雷小过，君子以行过乎恭"),
    (63, 2, 5, "水火既济", "水在火上既济，君子以思患而预防之"),
    (64, 5, 2, "火水未济", "火在水上未济，君子以慎辨物居方"),
)

# Build status code to King Wen record map
_CODE_TO_KING_WEN: dict[int, dict[str, Any]] = {}
_ORDER_TO_KING_WEN: dict[int, dict[str, Any]] = {}

for order, outer, inner, name, summary in KING_WEN_CANONICAL_TABLE:
    code = ((outer & 0b111) << 3) | (inner & 0b111)
    record = {
        "status_code": code,
        "king_wen_order": order,
        "hexagram_name": name,
        "outer_trigram": outer,
        "outer_trigram_name": _TRIGRAM_NAMES[outer],
        "outer_symbol": _TRIGRAM_SYMBOLS[outer],
        "inner_trigram": inner,
        "inner_trigram_name": _TRIGRAM_NAMES[inner],
        "inner_symbol": _TRIGRAM_SYMBOLS[inner],
        "guaci_summary": summary,
        "binary": format(code, "06b"),
    }
    _CODE_TO_KING_WEN[code] = record
    _ORDER_TO_KING_WEN[order] = record

# Build King Wen 32 Pairs and Pair Types (综卦 vs 错卦)
_KING_WEN_PAIRS: dict[int, dict[str, Any]] = {}
for i in range(0, 64, 2):
    rec1 = KING_WEN_CANONICAL_TABLE[i]
    rec2 = KING_WEN_CANONICAL_TABLE[i + 1]
    code1 = ((rec1[1] & 0b111) << 3) | (rec1[2] & 0b111)
    code2 = ((rec2[1] & 0b111) << 3) | (rec2[2] & 0b111)
    # Check bit reversal (综卦 / FanDui)
    bits1 = [(code1 >> bit) & 1 for bit in range(6)]
    reversed_code1 = sum(b << bit for bit, b in enumerate(reversed(bits1)))
    if reversed_code1 == code2:
        pair_type = "inverse_hexagram_fandui"
        pair_label = "综卦(反对)"
    else:
        pair_type = "opposite_hexagram_pangtong"
        pair_label = "错卦(旁通)"
    pair_info1 = {
        "paired_order": rec2[0],
        "paired_name": rec2[3],
        "paired_status_code": code2,
        "pair_type": pair_type,
        "pair_label": pair_label,
    }
    pair_info2 = {
        "paired_order": rec1[0],
        "paired_name": rec1[3],
        "paired_status_code": code1,
        "pair_type": pair_type,
        "pair_label": pair_label,
    }
    _KING_WEN_PAIRS[code1] = pair_info1
    _KING_WEN_PAIRS[code2] = pair_info2


# Jing Fang 8 Palaces System (京房八宫卦)
_JING_FANG_PALACE_CONFIGS: tuple[tuple[str, int, str], ...] = (
    ("乾宫", 7, "metal"),
    ("坎宫", 2, "water"),
    ("艮宫", 4, "earth"),
    ("震宫", 1, "wood"),
    ("巽宫", 6, "wood"),
    ("离宫", 5, "fire"),
    ("坤宫", 0, "earth"),
    ("兑宫", 3, "metal"),
)

_CODE_TO_JING_FANG: dict[int, dict[str, Any]] = {}

for palace_name, root, element in _JING_FANG_PALACE_CONFIGS:
    h0 = (root << 3) | root
    h1 = h0 ^ (1 << 0)
    h2 = h1 ^ (1 << 1)
    h3 = h2 ^ (1 << 2)
    h4 = h3 ^ (1 << 3)
    h5 = h4 ^ (1 << 4)
    h6 = h5 ^ (1 << 3)
    h7 = (h6 & 0b111000) | (h0 & 0b000111)
    ranks = [
        (h0, "本宫纯卦", 5, 2, "本宫"),
        (h1, "一世卦", 0, 3, "一世"),
        (h2, "二世卦", 1, 4, "二世"),
        (h3, "三世卦", 2, 5, "三世"),
        (h4, "四世卦", 3, 0, "四世"),
        (h5, "五世卦", 4, 1, "五世"),
        (h6, "游魂卦", 3, 0, "游魂"),
        (h7, "归魂卦", 2, 5, "归魂"),
    ]
    for h, rank_full, shi, ying, rank_short in ranks:
        _CODE_TO_JING_FANG[h] = {
            "status_code": h,
            "palace_name": palace_name,
            "palace_element": element,
            "palace_root_trigram": root,
            "rank_name": rank_full,
            "rank_short": rank_short,
            "shi_line": shi,
            "ying_line": ying,
            "shi_line_name": f"爻{shi + 1}",
            "ying_line_name": f"爻{ying + 1}",
        }


def _evaluate_king_wen_hexagram(status_code: int) -> dict[str, Any]:
    """Retrieve full King Wen canon record for a 6-bit hexagram state code."""
    code = status_code & 0x3F
    rec = _CODE_TO_KING_WEN.get(code, {})
    pair = _KING_WEN_PAIRS.get(code, {})
    return {**rec, **pair}


def _evaluate_jing_fang_palace(status_code: int) -> dict[str, Any]:
    """Retrieve Jing Fang Eight Palaces record for a 6-bit hexagram state code."""
    code = status_code & 0x3F
    return _CODE_TO_JING_FANG.get(code, {})


def _evaluate_zhigua_evolution(
    status_code: int,
    moving_lines: list[int] | None = None,
) -> dict[str, Any]:
    """Evaluate temporal ZhiGua (之卦 / 变卦) state evolution and Shi Zhong (时中) timing."""
    ben_code = status_code & 0x3F
    ben_king_wen = _evaluate_king_wen_hexagram(ben_code)
    ben_palace = _evaluate_jing_fang_palace(ben_code)

    m_lines = sorted(set(int(l) for l in (moving_lines or []) if 0 <= int(l) <= 5))
    mutation_mask = sum(1 << l for l in m_lines)
    zhi_code = ben_code ^ mutation_mask
    zhi_king_wen = _evaluate_king_wen_hexagram(zhi_code)
    zhi_palace = _evaluate_jing_fang_palace(zhi_code)

    # Line Properness (当位) before and after
    expected_lines = [1, 0, 1, 0, 1, 0]  # 初/三/五阳, 二/四/上阴
    ben_lines = [(ben_code >> i) & 1 for i in range(6)]
    zhi_lines = [(zhi_code >> i) & 1 for i in range(6)]
    ben_proper = sum(ben_lines[i] == expected_lines[i] for i in range(6))
    zhi_proper = sum(zhi_lines[i] == expected_lines[i] for i in range(6))

    # Center lines (二爻, 五爻) properness (中正)
    ben_central_proper = (ben_lines[1] == 0) and (ben_lines[4] == 1)
    zhi_central_proper = (zhi_lines[1] == 0) and (zhi_lines[4] == 1)

    # Shi Zhong Timing Directive (时中治理决断)
    outer_zhi = (zhi_code >> 3) & 0b111
    if outer_zhi in (4, 2):  # 艮止或坎险
        shi_zhong = "时止则止·收敛防险"
        recommended_action = "checkpoint"
    elif outer_zhi == 5:  # 离明
        shi_zhong = "审辨明晰·审查边界"
        recommended_action = "inspect"
    elif outer_zhi in (7, 1):  # 乾健或震动
        shi_zhong = "时行则行·奋发精进"
        recommended_action = "accelerate"
    else:
        shi_zhong = "顺时承应·安常处顺"
        recommended_action = "continue"

    return {
        "source_status_code": ben_code,
        "source_hexagram": ben_king_wen,
        "source_palace": ben_palace,
        "moving_lines": m_lines,
        "moving_lines_count": len(m_lines),
        "resulting_status_code": zhi_code,
        "resulting_hexagram": zhi_king_wen,
        "resulting_palace": zhi_palace,
        "proper_lines_delta": zhi_proper - ben_proper,
        "source_proper_count": ben_proper,
        "resulting_proper_count": zhi_proper,
        "source_is_central_and_proper": ben_central_proper,
        "resulting_is_central_and_proper": zhi_central_proper,
        "shi_zhong_directive": shi_zhong,
        "recommended_action": recommended_action,
    }


def _evaluate_iching_classical_correspondence_certificate() -> dict[str, Any]:
    """26th Formal mathematical certificate: King Wen 64 Hexagrams & Jing Fang Palaces Isomorphism."""
    # 1. King Wen Bijection across all 64 states
    king_wen_orders = set()
    king_wen_codes = set()
    for code, rec in _CODE_TO_KING_WEN.items():
        king_wen_orders.add(rec["king_wen_order"])
        king_wen_codes.add(code)
    bijection_ok = (len(king_wen_orders) == 64 and king_wen_codes == set(range(64)))

    # 2. King Wen 32 Pairs '非覆即变' Invariant (28 综卦, 4 错卦)
    inverse_count = 0
    opposite_count = 0
    pair_theorem_ok = True
    for i in range(0, 64, 2):
        rec1 = KING_WEN_CANONICAL_TABLE[i]
        rec2 = KING_WEN_CANONICAL_TABLE[i + 1]
        c1 = ((rec1[1] & 0b111) << 3) | (rec1[2] & 0b111)
        c2 = ((rec2[1] & 0b111) << 3) | (rec2[2] & 0b111)
        bits1 = [(c1 >> b) & 1 for b in range(6)]
        rev1 = sum(b << bit for bit, b in enumerate(reversed(bits1)))
        opp1 = c1 ^ 0x3F
        if rev1 == c2:
            inverse_count += 1
        elif opp1 == c2:
            opposite_count += 1
        else:
            pair_theorem_ok = False
            break
    pair_counts_ok = (inverse_count == 28 and opposite_count == 4 and pair_theorem_ok)

    # 3. Jing Fang 8 Palaces Bijection & Distance = 3
    jf_codes = set(_CODE_TO_JING_FANG.keys())
    jf_bijection_ok = (len(jf_codes) == 64 and jf_codes == set(range(64)))
    shi_ying_ok = all(
        ((rec["shi_line"] + 3) % 6 == rec["ying_line"])
        for rec in _CODE_TO_JING_FANG.values()
    )

    # 4. JiJi (21) & WeiJi (42) Cardinal Line Placement Theorem
    expected = [1, 0, 1, 0, 1, 0]
    proper_counts = {
        s: sum(((s >> i) & 1) == expected[i] for i in range(6))
        for s in range(64)
    }
    jiji_unique_ok = (proper_counts[21] == 6 and sum(c == 6 for c in proper_counts.values()) == 1)
    weiji_unique_ok = (proper_counts[42] == 0 and sum(c == 0 for c in proper_counts.values()) == 1)

    all_verified = (
        bijection_ok
        and pair_counts_ok
        and jf_bijection_ok
        and shi_ying_ok
        and jiji_unique_ok
        and weiji_unique_ok
    )

    return {
        "status": "verified" if all_verified else "failed",
        "king_wen_bijection_verified": bijection_ok,
        "king_wen_pairs_invariant_verified": pair_counts_ok,
        "inverse_pairs_count": inverse_count,
        "opposite_pairs_count": opposite_count,
        "jing_fang_palaces_bijection_verified": jf_bijection_ok,
        "shi_ying_triadic_distance_verified": shi_ying_ok,
        "jiji_optimal_centrality_verified": jiji_unique_ok,
        "weiji_ultimate_potential_verified": weiji_unique_ok,
    }


class IchingClassicalMixin:
    """Classical I Ching (周易) King Wen canon, Jing Fang palaces and ZhiGua evolution mixin."""

    @classmethod
    def king_wen_hexagram_record(cls, status_code: int) -> dict[str, Any]:
        """Retrieve full King Wen canon record for a 6-bit hexagram state code."""
        return _evaluate_king_wen_hexagram(status_code)

    @classmethod
    def king_wen_sequence_record(cls, order: int) -> dict[str, Any]:
        """Retrieve King Wen hexagram record by order number (1..64)."""
        o = max(1, min(64, int(order)))
        return _ORDER_TO_KING_WEN.get(o, {})

    @classmethod
    def jing_fang_palace_record(cls, status_code: int) -> dict[str, Any]:
        """Retrieve Jing Fang Eight Palaces record for a 6-bit hexagram state code."""
        return _evaluate_jing_fang_palace(status_code)

    @classmethod
    def zhigua_profile(
        cls,
        status_code: int,
        moving_lines: list[int] | None = None,
    ) -> dict[str, Any]:
        """Evaluate temporal ZhiGua (之卦 / 变卦) state evolution and Shi Zhong (时中) timing."""
        return _evaluate_zhigua_evolution(status_code=status_code, moving_lines=moving_lines)

    @classmethod
    def iching_classical_correspondence_certificate(cls) -> dict[str, Any]:
        """26th Formal mathematical certificate: King Wen 64 Hexagrams & Jing Fang Palaces Isomorphism."""
        return _evaluate_iching_classical_correspondence_certificate()
