"""Optional symbolic correspondence and audit certificate mixins for OneCode Kernel."""
from __future__ import annotations

from onecode_symbolic_audit.hexagram_classical import IchingClassicalMixin
from onecode_symbolic_audit.hexagram_ziwei import IchingZiweiMixin

SYMBOLIC_MIXINS = (IchingClassicalMixin, IchingZiweiMixin)

__all__ = [
    "IchingClassicalMixin",
    "IchingZiweiMixin",
    "SYMBOLIC_MIXINS",
]
