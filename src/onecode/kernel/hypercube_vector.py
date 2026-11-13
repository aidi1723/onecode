from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from onecode.kernel.hexagram import IchingKernel


def clamp(val: float, low: float = -1.0, high: float = 1.0) -> float:
    """Clamp a floating point value to the closed interval [low, high]."""
    if math.isnan(val):
        return 0.0
    return max(low, min(high, val))


def is_high_dim_enabled() -> bool:
    """Check if the high-dimensional spatial dynamics engine is enabled via environment."""
    return os.environ.get("ONECODE_HIGH_DIM_DYNAMICS", "0").lower() in {"1", "true", "yes", "on"}


# Precomputed discrete Lyapunov energies for all 64 hexagram states (0..63)
_HEXAGRAM_DISCRETE_ENERGIES: tuple[float, ...] = tuple(
    float(IchingKernel.lyapunov_energy(k)) for k in range(64)
)


@dataclass(frozen=True)
class StateVector6D:
    """Continuous 6-dimensional state vector q in [-1.0, 1.0]^6 representing agent configuration.

    Dimension mappings:
    - q0 (初爻): AST syntax clean ratio & structural validity [-1.0, 1.0]
    - q1 (二爻): Verifier assertion pass rate [-1.0, 1.0]
    - q2 (三爻): Patch surgical locality & isolation degree [-1.0, 1.0]
    - q3 (四爻): Turns & token budget headroom [-1.0, 1.0]
    - q4 (五爻): Sandbox compliance & pathguard boundary invariance [-1.0, 1.0]
    - q5 (上爻): Goal completion & task closure confidence [-1.0, 1.0]
    """

    q0: float
    q1: float
    q2: float
    q3: float
    q4: float
    q5: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "q0", clamp(self.q0))
        object.__setattr__(self, "q1", clamp(self.q1))
        object.__setattr__(self, "q2", clamp(self.q2))
        object.__setattr__(self, "q3", clamp(self.q3))
        object.__setattr__(self, "q4", clamp(self.q4))
        object.__setattr__(self, "q5", clamp(self.q5))

    @property
    def coords(self) -> tuple[float, float, float, float, float, float]:
        """Return the 6 coordinates as a tuple."""
        return (self.q0, self.q1, self.q2, self.q3, self.q4, self.q5)

    def to_discrete_status_code(self) -> int:
        """Quantum projection operator Pi_Q(q) mapping [-1, 1]^6 to integer status code in {0..63}."""
        code = 0
        for i, val in enumerate(self.coords):
            if val >= 0.0:
                code |= 1 << i
        return code

    @classmethod
    def from_discrete_code(cls, status_code: int) -> StateVector6D:
        """Create a StateVector6D corresponding to a discrete 6-bit vertex."""
        normalized = status_code & 0b111111
        coords = [1.0 if ((normalized >> i) & 1) == 1 else -1.0 for i in range(6)]
        return cls(*coords)

    @classmethod
    def from_evidence(
        cls,
        evidence: Mapping[str, Any] | None = None,
        *,
        ast_valid_files: int = 1,
        total_files: int = 1,
        passed_assertions: int = 0,
        total_assertions: int = 0,
        diff_files: int = 0,
        workspace_files: int = 1,
        turns_used: int = 0,
        max_turns: int = 30,
        boundary_breaches: int = 0,
        goal_progress: float = 0.0,
    ) -> StateVector6D:
        """Extract continuous 6D coordinates from verified execution facts and evidence."""
        data = dict(evidence) if evidence else {}

        # 1. AST syntax validity (q0)
        v_files = int(data.get("ast_valid_files", ast_valid_files))
        t_files = max(1, int(data.get("total_files", total_files)))
        q0 = 2.0 * (v_files / t_files) - 1.0

        # 2. Verifier assertion pass rate (q1)
        p_assert = int(data.get("passed_assertions", passed_assertions))
        t_assert = int(data.get("total_assertions", total_assertions))
        q1 = (2.0 * (p_assert / t_assert) - 1.0) if t_assert > 0 else 0.0

        # 3. Patch surgical locality (q2)
        d_files = int(data.get("diff_files", diff_files))
        w_files = max(1, int(data.get("workspace_files", workspace_files)))
        q2 = 1.0 - 2.0 * (d_files / w_files)

        # 4. Turn and token headroom (q3)
        u_turns = int(data.get("turns_used", turns_used))
        m_turns = max(1, int(data.get("max_turns", max_turns)))
        q3 = 2.0 * (1.0 - min(1.0, u_turns / m_turns)) - 1.0

        # 5. Sandbox boundary invariance (q4)
        breaches = int(data.get("boundary_breaches", boundary_breaches))
        q4 = 1.0 - 2.0 * breaches

        # 6. Task completion confidence (q5)
        goal = float(data.get("goal_progress", goal_progress))
        q5 = goal

        return cls(q0=q0, q1=q1, q2=q2, q3=q3, q4=q4, q5=q5)

    def lyapunov_energy(self) -> float:
        """Calculate continuous Lyapunov potential energy V(q) via multilinear relaxation.

        Matches discrete lyapunov_energy exactly at all 64 hypercube vertices.
        """
        u = [(1.0 + x) * 0.5 for x in self.coords]
        total_energy = 0.0
        for k, e_k in enumerate(_HEXAGRAM_DISCRETE_ENERGIES):
            w = 1.0
            for i in range(6):
                bit = (k >> i) & 1
                w *= u[i] if bit == 1 else (1.0 - u[i])
            total_energy += w * e_k
        return total_energy

    def lyapunov_gradient(self) -> tuple[float, float, float, float, float, float]:
        """Calculate exact analytic gradient nabla V(q) = (dV/dq0, ..., dV/dq5)."""
        u = [(1.0 + x) * 0.5 for x in self.coords]
        grad = [0.0] * 6
        for i in range(6):
            d_total = 0.0
            for k, e_k in enumerate(_HEXAGRAM_DISCRETE_ENERGIES):
                bit = (k >> i) & 1
                dw_dqi = 0.5 if bit == 1 else -0.5
                for j in range(6):
                    if j == i:
                        continue
                    b_j = (k >> j) & 1
                    dw_dqi *= u[j] if b_j == 1 else (1.0 - u[j])
                d_total += dw_dqi * e_k
            grad[i] = d_total
        return (grad[0], grad[1], grad[2], grad[3], grad[4], grad[5])

    def project_3d(self, lambda_factor: float = 0.35) -> tuple[float, float, float]:
        """Project 6D coordinate onto 3D space using Schlegel-like nested cube projection."""
        lf = clamp(lambda_factor, 0.0, 1.0)
        outer_weight = 1.0 + lf
        inner_weight = 1.0 - lf
        x = self.q3 * outer_weight + self.q0 * inner_weight
        y = self.q4 * outer_weight + self.q1 * inner_weight
        z = self.q5 * outer_weight + self.q2 * inner_weight
        return (round(x, 4), round(y, 4), round(z, 4))

    def distance_to(self, other: StateVector6D) -> float:
        """Calculate Euclidean distance ||q - q'|| in 6D space."""
        diff_sq = sum((a - b) ** 2 for a, b in zip(self.coords, other.coords))
        return math.sqrt(diff_sq)

    def spatiotemporal_interval(self, other: StateVector6D, delta_tau: float, c: float = 1.0) -> float:
        """Calculate Minkowski-like spacetime interval delta s^2 = ||delta q||^2 - c^2 * delta tau^2."""
        spatial_dist = self.distance_to(other)
        return (spatial_dist ** 2) - (c ** 2) * (delta_tau ** 2)

    def is_causally_valid(self, other: StateVector6D, delta_tau: float, c: float = 1.0) -> bool:
        """Return True if transition from other to self respects causal velocity limit (delta s^2 <= 0)."""
        if delta_tau <= 0.0:
            return False
        return self.spatiotemporal_interval(other, delta_tau, c) <= 1e-9


@dataclass(frozen=True)
class ChannelState8D:
    """8-dimensional channel state vector w in [-1.0, 1.0]^8.

    Comprises the core 6D kernel vector plus 2 external channel dimensions:
    - q6_network_io: external network & API channel health [-1.0, 1.0]
    - q7_sovereign_gate: human supervisor authority & approval trust [-1.0, 1.0]
    """

    core: StateVector6D
    q6_network_io: float
    q7_sovereign_gate: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "q6_network_io", clamp(self.q6_network_io))
        object.__setattr__(self, "q7_sovereign_gate", clamp(self.q7_sovereign_gate))

    @property
    def coords(self) -> tuple[float, float, float, float, float, float, float, float]:
        """Return the 8 coordinates as a tuple."""
        return (*self.core.coords, self.q6_network_io, self.q7_sovereign_gate)

    def to_byte_code(self) -> int:
        """Quantize into 8-bit byte state in {0..255} aligned with Cl_8 Bott periodicity."""
        code = self.core.to_discrete_status_code()
        if self.q6_network_io >= 0.0:
            code |= 1 << 6
        if self.q7_sovereign_gate >= 0.0:
            code |= 1 << 7
        return code


@dataclass(frozen=True)
class PhaseSpaceState12D:
    """12-dimensional Hamiltonian phase space state Z = (q, p) in R^12.

    Comprises 6D position q (current state) and 6D momentum/velocity p (rate of change).
    Maps topologically to Western Han Dynasty Jiao Yanshou's 4,096 hexagram transition grid.
    """

    q: StateVector6D
    p0: float
    p1: float
    p2: float
    p3: float
    p4: float
    p5: float

    def __post_init__(self) -> None:
        # Momentum can exceed 1.0 (velocity is not strictly bounded to [-1, 1])
        # but guard against NaN / Inf
        for i, val in enumerate(self.p_tuple()):
            if math.isnan(val) or math.isinf(val):
                object.__setattr__(self, f"p{i}", 0.0)

    def p_tuple(self) -> tuple[float, float, float, float, float, float]:
        """Return momentum vector as a tuple."""
        return (self.p0, self.p1, self.p2, self.p3, self.p4, self.p5)

    def kinetic_energy(self, mass: Sequence[float] | None = None) -> float:
        """Calculate kinetic energy T = 1/2 * p^T * M^-1 * p with diagonal inertia matrix."""
        m = mass or (1.0, 1.5, 0.8, 0.5, 2.5, 1.2)
        total_ke = 0.0
        for p_i, m_i in zip(self.p_tuple(), m):
            effective_m = max(1e-4, float(m_i))
            total_ke += (p_i * p_i) / effective_m
        return 0.5 * total_ke

    def hamiltonian(self, mass: Sequence[float] | None = None) -> float:
        """Calculate total phase space Hamiltonian energy H(q, p) = T(p) + V(q)."""
        return self.kinetic_energy(mass) + self.q.lyapunov_energy()

    def to_jiao_yanshou_dual_codes(self) -> tuple[int, int]:
        """Calculate (source_code, predicted_target_code) in Jiao Yanshou's 4,096 dual grid."""
        source_code = self.q.to_discrete_status_code()
        predicted_coords = [
            clamp(q_i + p_i)
            for q_i, p_i in zip(self.q.coords, self.p_tuple())
        ]
        target_code = 0
        for i, val in enumerate(predicted_coords):
            if val >= 0.0:
                target_code |= 1 << i
        return (source_code, target_code)

    def leapfrog_step(
        self,
        delta_t: float = 1.0,
        damping: Sequence[float] | None = None,
        mass: Sequence[float] | None = None,
    ) -> PhaseSpaceState12D:
        """Perform one step of dissipative conformal Leapfrog integration.

        Uses exponential conformal damping decay exp(-0.5 * gamma * dt) and inelastic
        boundary wall absorption to guarantee unconditional numerical stability.
        """
        dt = max(1e-4, delta_t)
        gamma = damping or (0.35, 0.35, 0.35, 0.35, 0.35, 0.35)
        m = mass or (1.0, 1.5, 0.8, 0.5, 2.5, 1.2)

        grad_v0 = self.q.lyapunov_gradient()

        # 1. Half step momentum update with conformal exponential dissipation
        half_p: list[float] = []
        for p_i, g_i, gam_i in zip(self.p_tuple(), grad_v0, gamma):
            decay = math.exp(-0.5 * max(0.0, gam_i) * dt)
            hp = decay * p_i - 0.5 * dt * g_i
            half_p.append(hp)

        # 2. Full step position update: q(t + dt) = q(t) + dt * M^-1 * p(t + dt/2)
        new_q_coords: list[float] = []
        for q_i, hp_i, m_i in zip(self.q.coords, half_p, m):
            effective_m = max(1e-4, float(m_i))
            nq = clamp(q_i + dt * (hp_i / effective_m))
            new_q_coords.append(nq)

        new_q = StateVector6D(
            new_q_coords[0],
            new_q_coords[1],
            new_q_coords[2],
            new_q_coords[3],
            new_q_coords[4],
            new_q_coords[5],
        )

        # 3. Final half step momentum update with conformal dissipation and boundary wall absorption
        grad_v1 = new_q.lyapunov_gradient()
        final_p: list[float] = []
        for hp_i, g_i, gam_i, q_i in zip(half_p, grad_v1, gamma, new_q_coords):
            decay = math.exp(-0.5 * max(0.0, gam_i) * dt)
            fp = decay * (hp_i - 0.5 * dt * g_i)
            # Inelastic wall collision: absorb momentum directed outside [-1.0, 1.0]
            if (q_i >= 1.0 and fp > 0.0) or (q_i <= -1.0 and fp < 0.0):
                fp = 0.0
            final_p.append(fp)

        return PhaseSpaceState12D(
            q=new_q,
            p0=final_p[0],
            p1=final_p[1],
            p2=final_p[2],
            p3=final_p[3],
            p4=final_p[4],
            p5=final_p[5],
        )


def safe_resolve_status_code(
    vector: StateVector6D | None,
    fallback_code: int = 49,
) -> int:
    """Safely resolve an integer status code with instant fallback on error or disabled mode."""
    if vector is None:
        return fallback_code & 0b111111
    try:
        return vector.to_discrete_status_code()
    except Exception:
        return fallback_code & 0b111111
