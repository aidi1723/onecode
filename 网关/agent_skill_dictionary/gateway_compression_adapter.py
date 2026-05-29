from __future__ import annotations

import re
from typing import Any


STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "please",
    "thank",
    "thanks",
    "you",
    "successfully",
    "system",
    "has",
    "have",
    "had",
    "is",
    "are",
    "was",
    "were",
    "to",
    "for",
    "with",
    "that",
    "this",
    "into",
    "from",
}
PROTECTED_RE = re.compile(
    r"([A-Za-z0-9_.\-/]+/[A-Za-z0-9_.\-/]+|[a-fA-F0-9]{12,}|[A-Za-z_][A-Za-z0-9_]*\([^)]*\))"
)


def build_compression_record(text: str, mode: str = "internal_caveman") -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {
            "mode": "off",
            "compressed_summary": "",
            "raw_chars": 0,
            "compressed_chars": 0,
            "compression_ratio": 0.0,
            "preserved_tokens": [],
            "compression_rule": "raw_empty_no_compression",
        }

    preserved = _preserved_tokens(raw)
    compressed = _compress(raw)
    return {
        "mode": mode,
        "compressed_summary": compressed,
        "raw_chars": len(raw),
        "compressed_chars": len(compressed),
        "compression_ratio": round(1 - (len(compressed) / len(raw)), 4) if raw else 0.0,
        "preserved_tokens": preserved,
        "compression_rule": "drop_stopwords_keep_paths_hashes_symbols",
    }


def _compress(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.strip())
    words = []
    for token in normalized.split(" "):
        stripped = token.strip()
        if not stripped:
            continue
        core = stripped.strip(".,;:!?()[]{}")
        if core.lower() in STOPWORDS:
            continue
        words.append(stripped)
    return " ".join(words)


def _preserved_tokens(text: str) -> list[str]:
    seen = []
    for match in PROTECTED_RE.findall(text):
        if match not in seen:
            seen.append(match)
    return seen
