"""Replayable eval packs submitted with capabilities."""
from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    name: str = Field(..., min_length=1)
    input: Dict[str, Any]
    expected_output: Dict[str, Any]


class EvalPack(BaseModel):
    cases: List[EvalCase] = Field(..., min_length=1)
