from dataclasses import dataclass


@dataclass(frozen=True)
class IchingTransition:
    status_code: int
    action: str
    reason: str | None


class IchingKernel:
    KUN = 0b000
    ZHEN = 0b001
    KAN = 0b010
    DUI = 0b011
    GEN = 0b100
    XUN = 0b101
    LI = 0b110
    QIAN = 0b111

    FOUR_SYMBOLS = {
        0b00: "tai_yin",
        0b01: "shao_yang",
        0b10: "shao_yin",
        0b11: "tai_yang",
    }

    @classmethod
    def compute_status(cls, outer_trigram: int, inner_trigram: int) -> int:
        return ((outer_trigram & 0b111) << 3) | (inner_trigram & 0b111)

    @classmethod
    def four_symbol_for_bits(cls, bits: int) -> str:
        return cls.FOUR_SYMBOLS[bits & 0b11]

    @classmethod
    def four_symbols(cls, status_code: int) -> list[dict[str, int | str]]:
        return [
            {
                "pair_index": pair_index,
                "bits": (status_code >> (pair_index * 2)) & 0b11,
                "symbol": cls.four_symbol_for_bits((status_code >> (pair_index * 2)) & 0b11),
            }
            for pair_index in range(3)
        ]

    @classmethod
    def yin_yang_profile(cls, status_code: int) -> dict[str, int | str]:
        yang_count = (status_code & 0b111111).bit_count()
        yin_count = 6 - yang_count
        if yang_count == 6:
            balance = "pure_yang"
        elif yang_count == 5:
            balance = "yang_excess"
        elif yang_count in {3, 4}:
            balance = "balanced"
        elif yang_count in {1, 2}:
            balance = "yin_excess"
        else:
            balance = "pure_yin"
        return {"yang_count": yang_count, "yin_count": yin_count, "balance": balance}

    @classmethod
    def should_skip(cls, status_code: int) -> bool:
        inner = status_code & 0b111
        outer = (status_code >> 3) & 0b111
        return inner == cls.DUI and outer != cls.LI

    @classmethod
    def classify_outcome(cls, status: str, reason: str | None) -> int:
        if reason == "sovereignty_breach":
            return cls.compute_status(cls.LI, cls.KUN)
        if reason == "http_timeout":
            return cls.compute_status(cls.KAN, cls.ZHEN)
        if status == "skipped":
            return cls.compute_status(cls.QIAN, cls.DUI)
        if status == "completed":
            return cls.compute_status(cls.QIAN, cls.QIAN)
        return cls.compute_status(cls.KUN, cls.KUN)

    @classmethod
    def classify_resume_audit(cls, status: str, reason: str | None) -> int:
        if status == "ready":
            return cls.compute_status(cls.QIAN, cls.DUI)
        if reason == "path_outside_workspace":
            return cls.compute_status(cls.LI, cls.KUN)
        if reason in {"missing_file", "sha256_mismatch"}:
            return cls.compute_status(cls.KAN, cls.ZHEN)
        return cls.compute_status(cls.KUN, cls.KUN)

    @classmethod
    def transition(cls, status_code: int) -> IchingTransition:
        inner = status_code & 0b111
        outer = (status_code >> 3) & 0b111

        if outer == cls.LI:
            return IchingTransition(
                status_code=cls.compute_status(cls.LI, cls.KUN),
                action="halt",
                reason="sovereignty_fire_suppresses_asset",
            )
        if outer == cls.KAN:
            return IchingTransition(
                status_code=status_code,
                action="checkpoint",
                reason="network_water_preserves_resume_seed",
            )
        profile = cls.yin_yang_profile(status_code)
        if profile["balance"] in {"pure_yang", "yang_excess"}:
            return IchingTransition(
                status_code=cls.compute_status(cls.GEN, inner),
                action="halt",
                reason="yang_overload_cooldown",
            )
        return IchingTransition(status_code=status_code, action="continue", reason=None)


def is_valid_hexagram_code(value: str) -> bool:
    return len(value) == 6 and all(char in "01" for char in value)


@dataclass(frozen=True)
class HexagramStatusCode:
    value: str

    def __post_init__(self) -> None:
        if not is_valid_hexagram_code(self.value):
            raise ValueError(f"invalid hexagram status code: {self.value!r}")

    def __str__(self) -> str:
        return self.value


BUILD_ENTRY = HexagramStatusCode("111111")
VERIFY_GATE = HexagramStatusCode("000001")
CORRECTION_GATE = HexagramStatusCode("110000")
INSPECT_GATE = HexagramStatusCode("101000")
COMPLETE = HexagramStatusCode("000000")
