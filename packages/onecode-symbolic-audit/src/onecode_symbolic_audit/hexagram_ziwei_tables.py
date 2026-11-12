"""Shared Ziwei lookup tables."""
from __future__ import annotations

from typing import Any

_EARTHLY_BRANCH_NAMES = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")


_HEAVENLY_STEM_NAMES = ("甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸")


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


_STAGE_STEM_TABLE: dict[str, int] = {
    "exploration": 0,
    "implementation": 2,
    "verification": 6,
    "delivery": 8,
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


_CLASSICAL_QINGYANG_BY_STEM: tuple[int, ...] = (3, 4, 6, 7, 6, 7, 9, 10, 0, 1)


_CLASSICAL_TUOLUO_BY_STEM: tuple[int, ...] = (1, 2, 4, 5, 4, 5, 7, 8, 10, 11)


_CLASSICAL_TIANFU_OPPOSITION_AXIS: dict[int, int] = {
    0: 4, 1: 3, 2: 2, 3: 1, 4: 0, 5: 11,
    6: 10, 7: 9, 8: 8, 9: 7, 10: 6, 11: 5,
}


_GENG_SIHUA_VARIANTS: dict[str, tuple[str, str, str, str]] = {
    "GYWYT": ("太阳", "武曲", "太阴", "天同"),
    "GYWTY": ("太阳", "武曲", "天同", "太阴"),
    "GYWFT": ("太阳", "武曲", "天府", "天同"),
    "GYWFX": ("太阳", "武曲", "天府", "天相"),
    "GYWTX": ("太阳", "武曲", "天同", "天相"),
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


_CHILDHOOD_MING_OFFSET: dict[int, int] = {
    1: 0,
    2: -4,
    3: -5,
    4: -2,
    5: 2,
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


_CANONICAL_TIANFU_OPPOSITION_TABLE: dict[int, int] = {
    0: 4, 1: 3, 2: 2, 3: 1, 4: 0, 5: 11,
    6: 10, 7: 9, 8: 8, 9: 7, 10: 6, 11: 5,
}


_XIAOXIAN_ORIGIN_BY_BRANCH: dict[int, int] = {
    0: 10, 1: 7, 2: 4, 3: 1, 4: 10, 5: 7,
    6: 4, 7: 1, 8: 10, 9: 7, 10: 4, 11: 1,
}



__all__ = [
    "_EARTHLY_BRANCH_NAMES",
    "_HEAVENLY_STEM_NAMES",
    "_JIANG_QIAN_SHEN",
    "_SUI_QIAN_SHEN",
    "_BOSHI_SHEN",
    "_LUCUN_BRANCH_BY_STEM",
    "_SI_HUA_TABLE",
    "_STAR_CANONICAL_INDEX",
    "_STAGE_STEM_TABLE",
    "_MING_ZHU_TABLE",
    "_SHEN_ZHU_TABLE",
    "_CLASSICAL_QINGYANG_BY_STEM",
    "_CLASSICAL_TUOLUO_BY_STEM",
    "_CLASSICAL_TIANFU_OPPOSITION_AXIS",
    "_GENG_SIHUA_VARIANTS",
    "_TIANKUI_BY_STEM",
    "_TIANYUE_BY_STEM",
    "_TIANMA_BY_BRANCH",
    "_FAMOUS_ARCHETYPES",
    "_XLS_CN_TABLE",
    "_CLASSICAL_APHORISMS",
    "_PATHOLOGY_ELEMENTS",
    "_PARTNER_STAR_CONTRACTS",
    "_SIX_CHANNELS_DATA",
    "_WUXING_JU_MATRIX",
    "_JU_NUMBER_TO_NAME",
    "_CHILDHOOD_MING_OFFSET",
    "_MAJOR_CITIES_LONGITUDE",
    "_CHANGSHENG_STAGES",
    "_CHANGSHENG_ORIGIN",
    "_CHANGSHENG_LIFECYCLE_MAP",
    "_QUANSHU_FOURTEEN_STARS_BRIGHTNESS",
    "_QUANSHU_BRIGHTNESS_WEIGHTS",
    "_ZIWU_LIUZHU_MERIDIANS",
    "_FIVE_ELEMENTS_NAMES",
    "_FIVE_ELEMENTS_INDEX",
    "_CANONICAL_TIANFU_OPPOSITION_TABLE",
    "_XIAOXIAN_ORIGIN_BY_BRANCH",
]
