from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MacroChain:
    name: str
    codes: list[str]
    root_opcodes: list[str]
    reason: str
    summary: str


ROOT_BY_CODE = {
    "查": "查",
    "造": "修",
    "测": "测",
    "修": "修",
    "卫": "卫",
    "停": "停",
    "问": "问",
    "记": "记",
    "总": "总",
}


def compile_macro_chain(user_message: str) -> MacroChain:
    message = user_message.lower()
    if _looks_like_security_meltdown(message):
        return _build_chain(
            name="security_meltdown_closed_loop",
            codes=["卫", "停", "问", "查", "总"],
            reason="security_risk_or_halt_requested",
        )

    if _looks_like_feature_development(message):
        return _build_chain(
            name="feature_development_closed_loop",
            codes=["查", "造", "测", "修", "记", "总"],
            reason="feature_or_build_request",
        )

    return _build_chain(
        name="default_inspect_closed_loop",
        codes=["查", "总"],
        reason="fallback_to_readonly_inspection",
    )


def macro_chain_to_dict(chain: MacroChain) -> dict[str, object]:
    return {
        "name": chain.name,
        "codes": chain.codes,
        "root_opcodes": chain.root_opcodes,
        "reason": chain.reason,
        "summary": chain.summary,
        "initial_active_code": chain.codes[0],
    }


def _build_chain(name: str, codes: list[str], reason: str) -> MacroChain:
    root_opcodes = [ROOT_BY_CODE[code] for code in codes]
    return MacroChain(
        name=name,
        codes=codes,
        root_opcodes=root_opcodes,
        reason=reason,
        summary=" -> ".join(codes),
    )


def _looks_like_feature_development(message: str) -> bool:
    feature_markers = (
        "实现",
        "新增",
        "写一个",
        "做一个",
        "新接口",
        "新功能",
        "模块",
        "组件",
        "build",
        "feature",
    )
    verification_markers = ("测试", "验证", "确保", "不会", "覆盖", "记录", "文档")
    return any(marker in message for marker in feature_markers) and any(
        marker in message for marker in verification_markers
    )


def _looks_like_security_meltdown(message: str) -> bool:
    security_markers = (
        "rm -rf",
        "危险",
        "高危",
        "安全",
        "未知外联",
        "外联",
        "注入",
        "熔断",
        "越界",
    )
    return any(marker in message for marker in security_markers)
