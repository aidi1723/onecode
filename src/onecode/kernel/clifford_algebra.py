"""64-Dimensional Clifford Geometric Algebra Cl(6,0) for holographic state dynamics.

In the mathematical duality between classical I-Ching (64 hexagrams) and modern
geometric control, the 6-dimensional continuous state vector q in R^6 naturally
generates a 64-dimensional Clifford multivector space Cl(6,0):
    dim Cl(6,0) = sum_{k=0}^6 binom(6, k) = 1 + 6 + 15 + 20 + 15 + 6 + 1 = 64.

Grades:
  Grade 0 (1 dim):  Scalar / Global base energy
  Grade 1 (6 dims): 1-vectors / 6D continuous configuration coordinates (q0..q5)
  Grade 2 (15 dims): 2-vectors / Bivector rotation and cross-coupling torque planes
  Grade 3 (20 dims): 3-vectors / Triadic non-linear Heaven-Earth-Man entanglement
  Grade 4 (15 dims): 4-vectors / Dual bivectors (Hodge star of Grade 2)
  Grade 5 (6 dims): 5-vectors / Dual vectors (Hodge star of Grade 1)
  Grade 6 (1 dim):  Pseudoscalar / Chiral volume element (e0 e1 e2 e3 e4 e5)
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

from onecode.kernel.hypercube_vector import StateVector6D, clamp

NUM_DIMENSIONS = 6
TOTAL_ALGEBRA_DIMENSION = 1 << NUM_DIMENSIONS  # 64

# Grade of each basis element from bitmask 0..63
_BASIS_GRADES: tuple[int, ...] = tuple(bin(k).count("1") for k in range(TOTAL_ALGEBRA_DIMENSION))

# Group basis indices by grade (0..6)
_GRADE_BASIS_INDICES: tuple[tuple[int, ...], ...] = tuple(
    tuple(idx for idx in range(TOTAL_ALGEBRA_DIMENSION) if _BASIS_GRADES[idx] == g)
    for g in range(NUM_DIMENSIONS + 1)
)

# Grade dimension distribution: (1, 6, 15, 20, 15, 6, 1)
GRADE_DIMENSIONS: tuple[int, ...] = tuple(len(indices) for indices in _GRADE_BASIS_INDICES)

# The 15 bivector coordinate pairs (i, j) with 0 <= i < j < 6
BIVECTOR_PAIRS: tuple[tuple[int, int], ...] = tuple(
    (i, j) for i in range(NUM_DIMENSIONS) for j in range(i + 1, NUM_DIMENSIONS)
)
# Map (i, j) to the 6-bit basis mask (1 << i) | (1 << j)
BIVECTOR_PAIR_TO_MASK: dict[tuple[int, int], int] = {
    (i, j): (1 << i) | (1 << j) for i, j in BIVECTOR_PAIRS
}
MASK_TO_BIVECTOR_INDEX: dict[int, int] = {
    (1 << i) | (1 << j): idx for idx, (i, j) in enumerate(BIVECTOR_PAIRS)
}

# Precomputed multiplication table for Clifford geometric product in Cl(6,0)
# e_A * e_B = _MULT_SIGN[A][B] * e_{A ^ B}
_MULT_SIGN: list[list[int]] = [[0] * TOTAL_ALGEBRA_DIMENSION for _ in range(TOTAL_ALGEBRA_DIMENSION)]

for _a in range(TOTAL_ALGEBRA_DIMENSION):
    for _b in range(TOTAL_ALGEBRA_DIMENSION):
        # Count generator swaps: each bit i in _a must jump over bits in _b below i
        swaps = 0
        for _i in range(NUM_DIMENSIONS):
            if (_a >> _i) & 1:
                swaps += bin(_b & ((1 << _i) - 1)).count("1")
        _MULT_SIGN[_a][_b] = -1 if (swaps & 1) else 1


@dataclass(frozen=True)
class CliffordMultivector64:
    """A full 64-dimensional Clifford multivector in Cl(6,0).

    Stored as a length-64 tuple of float coefficients corresponding to
    basis elements e_K where K is the bitmask in [0, 63].
    """

    components: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.components) != TOTAL_ALGEBRA_DIMENSION:
            raise ValueError(
                f"CliffordMultivector64 requires exactly {TOTAL_ALGEBRA_DIMENSION} components, "
                f"got {len(self.components)}"
            )

    @classmethod
    def zero(cls) -> CliffordMultivector64:
        """Return the zero multivector."""
        return cls(tuple(0.0 for _ in range(TOTAL_ALGEBRA_DIMENSION)))

    @classmethod
    def scalar(cls, value: float) -> CliffordMultivector64:
        """Return a pure Grade-0 scalar multivector."""
        comps = [0.0] * TOTAL_ALGEBRA_DIMENSION
        comps[0] = float(value)
        return cls(tuple(comps))

    @classmethod
    def basis(cls, mask: int, value: float = 1.0) -> CliffordMultivector64:
        """Return a single basis element e_mask with the given coefficient."""
        if not (0 <= mask < TOTAL_ALGEBRA_DIMENSION):
            raise ValueError(f"Basis mask must be in 0..{TOTAL_ALGEBRA_DIMENSION - 1}, got {mask}")
        comps = [0.0] * TOTAL_ALGEBRA_DIMENSION
        comps[mask] = float(value)
        return cls(tuple(comps))

    @classmethod
    def from_vector6d(cls, vec: StateVector6D) -> CliffordMultivector64:
        """Embed a 6D continuous configuration vector q into Grade-1 multivector space."""
        comps = [0.0] * TOTAL_ALGEBRA_DIMENSION
        for i, val in enumerate(vec.coords):
            comps[1 << i] = float(val)
        return cls(tuple(comps))

    def to_vector6d(self) -> StateVector6D:
        """Project the Grade-1 vector components back onto StateVector6D."""
        return StateVector6D(
            q0=clamp(self.components[1 << 0]),
            q1=clamp(self.components[1 << 1]),
            q2=clamp(self.components[1 << 2]),
            q3=clamp(self.components[1 << 3]),
            q4=clamp(self.components[1 << 4]),
            q5=clamp(self.components[1 << 5]),
        )

    def grade(self, g: int) -> CliffordMultivector64:
        """Extract only the Grade-g components of this multivector."""
        if not (0 <= g <= NUM_DIMENSIONS):
            raise ValueError(f"Grade must be in 0..{NUM_DIMENSIONS}, got {g}")
        comps = [0.0] * TOTAL_ALGEBRA_DIMENSION
        for idx in _GRADE_BASIS_INDICES[g]:
            comps[idx] = self.components[idx]
        return CliffordMultivector64(tuple(comps))

    def grade_norms(self) -> tuple[float, float, float, float, float, float, float]:
        """Return L2 norm for each grade (0 to 6)."""
        norms: list[float] = []
        for g in range(NUM_DIMENSIONS + 1):
            s = sum(self.components[idx] ** 2 for idx in _GRADE_BASIS_INDICES[g])
            norms.append(math.sqrt(s))
        return (norms[0], norms[1], norms[2], norms[3], norms[4], norms[5], norms[6])

    def total_norm(self) -> float:
        """Return global Euclidean L2 norm across all 64 dimensions."""
        return math.sqrt(sum(c * c for c in self.components))

    def __add__(self, other: CliffordMultivector64) -> CliffordMultivector64:
        return CliffordMultivector64(
            tuple(a + b for a, b in zip(self.components, other.components))
        )

    def __sub__(self, other: CliffordMultivector64) -> CliffordMultivector64:
        return CliffordMultivector64(
            tuple(a - b for a, b in zip(self.components, other.components))
        )

    def __mul__(self, other: float | int | CliffordMultivector64) -> CliffordMultivector64:
        if isinstance(other, (int, float)):
            scale = float(other)
            return CliffordMultivector64(tuple(c * scale for c in self.components))
        if isinstance(other, CliffordMultivector64):
            return self.geometric_product(other)
        return NotImplemented

    def __rmul__(self, other: float | int) -> CliffordMultivector64:
        return self.__mul__(other)

    def geometric_product(self, other: CliffordMultivector64) -> CliffordMultivector64:
        """Calculate Clifford geometric product C = A * B in Cl(6,0)."""
        res = [0.0] * TOTAL_ALGEBRA_DIMENSION
        # Sparse traversal over non-zero elements
        non_zero_a = [(idx, val) for idx, val in enumerate(self.components) if abs(val) > 1e-12]
        non_zero_b = [(idx, val) for idx, val in enumerate(other.components) if abs(val) > 1e-12]

        for idx_a, val_a in non_zero_a:
            sign_row = _MULT_SIGN[idx_a]
            for idx_b, val_b in non_zero_b:
                target_idx = idx_a ^ idx_b
                sign = sign_row[idx_b]
                res[target_idx] += sign * val_a * val_b
        return CliffordMultivector64(tuple(res))

    def wedge_product(self, other: CliffordMultivector64) -> CliffordMultivector64:
        """Calculate exterior wedge product C = A ^ B."""
        res = [0.0] * TOTAL_ALGEBRA_DIMENSION
        non_zero_a = [(idx, val) for idx, val in enumerate(self.components) if abs(val) > 1e-12]
        non_zero_b = [(idx, val) for idx, val in enumerate(other.components) if abs(val) > 1e-12]

        for idx_a, val_a in non_zero_a:
            sign_row = _MULT_SIGN[idx_a]
            for idx_b, val_b in non_zero_b:
                # Wedge product requires disjoint basis generators
                if (idx_a & idx_b) == 0:
                    target_idx = idx_a | idx_b
                    sign = sign_row[idx_b]
                    res[target_idx] += sign * val_a * val_b
        return CliffordMultivector64(tuple(res))

    def hodge_dual(self) -> CliffordMultivector64:
        """Calculate Hodge star dual *A = A * I_6^-1 in Cl(6,0)."""
        pseudoscalar_mask = 63  # 0b111111
        comps = [0.0] * TOTAL_ALGEBRA_DIMENSION
        for idx, val in enumerate(self.components):
            if abs(val) > 1e-12:
                dual_mask = pseudoscalar_mask ^ idx
                # Sign of e_idx * e_{63 ^ idx}
                sign = _MULT_SIGN[idx][dual_mask]
                comps[dual_mask] = sign * val
        return CliffordMultivector64(tuple(comps))

    def bivector_torque_matrix(self) -> list[list[float]]:
        """Extract the 15 Grade-2 bivector components into a 6x6 anti-symmetric torque matrix.

        Omega[i][j] = -Omega[j][i] = coefficient of (e_i ^ e_j).
        Represents the instantaneous shear/rotation planes across the 6 core coordinates.
        """
        matrix = [[0.0] * NUM_DIMENSIONS for _ in range(NUM_DIMENSIONS)]
        for i, j in BIVECTOR_PAIRS:
            mask = BIVECTOR_PAIR_TO_MASK[(i, j)]
            val = self.components[mask]
            matrix[i][j] = val
            matrix[j][i] = -val
        return matrix

    def to_bivector_15d_tuple(self) -> tuple[float, ...]:
        """Return the 15 bivector coefficients as an ordered tuple."""
        return tuple(self.components[BIVECTOR_PAIR_TO_MASK[pair]] for pair in BIVECTOR_PAIRS)
