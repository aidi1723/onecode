from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.hypercube_vector import (
    ChannelState8D,
    PhaseSpaceState12D,
    StateVector6D,
    clamp,
    is_high_dim_enabled,
    safe_resolve_status_code,
)


class TestHypercubeVector(unittest.TestCase):
    def test_clamp_standard_and_extreme_values(self) -> None:
        self.assertEqual(clamp(0.5), 0.5)
        self.assertEqual(clamp(2.5), 1.0)
        self.assertEqual(clamp(-3.0), -1.0)
        self.assertEqual(clamp(float("nan")), 0.0)
        self.assertEqual(clamp(1.0), 1.0)
        self.assertEqual(clamp(-1.0), -1.0)

    def test_roundtrip_all_64_hypercube_vertices(self) -> None:
        for code in range(64):
            vec = StateVector6D.from_discrete_code(code)
            projected = vec.to_discrete_status_code()
            self.assertEqual(projected, code)
            for i in range(6):
                expected_coord = 1.0 if ((code >> i) & 1) == 1 else -1.0
                self.assertEqual(vec.coords[i], expected_coord)

    def test_from_evidence_clamping_and_zero_division_guard(self) -> None:
        # Zero division guard
        vec_zero = StateVector6D.from_evidence(
            ast_valid_files=0,
            total_files=0,
            passed_assertions=0,
            total_assertions=0,
            diff_files=0,
            workspace_files=0,
            turns_used=0,
            max_turns=0,
        )
        self.assertEqual(vec_zero.q0, -1.0)
        self.assertEqual(vec_zero.q1, 0.0)
        self.assertEqual(vec_zero.q2, 1.0)
        self.assertEqual(vec_zero.q3, 1.0)

        # Extreme breach clamping
        vec_breach = StateVector6D.from_evidence(boundary_breaches=10)
        self.assertEqual(vec_breach.q4, -1.0)

        # Normal evidence
        vec_normal = StateVector6D.from_evidence(
            ast_valid_files=10,
            total_files=10,
            passed_assertions=5,
            total_assertions=5,
            diff_files=1,
            workspace_files=10,
            turns_used=6,
            max_turns=30,
            boundary_breaches=0,
            goal_progress=0.8,
        )
        self.assertEqual(vec_normal.q0, 1.0)
        self.assertEqual(vec_normal.q1, 1.0)
        self.assertAlmostEqual(vec_normal.q2, 0.8)
        self.assertAlmostEqual(vec_normal.q3, 0.6)
        self.assertEqual(vec_normal.q4, 1.0)
        self.assertEqual(vec_normal.q5, 0.8)

    def test_lyapunov_energy_matches_discrete_at_all_64_vertices(self) -> None:
        for code in range(64):
            expected = IchingKernel.lyapunov_energy(code)
            vec = StateVector6D.from_discrete_code(code)
            continuous = vec.lyapunov_energy()
            self.assertAlmostEqual(
                continuous,
                expected,
                places=6,
                msg=f"Discrepancy at hexagram vertex {code}",
            )

    def test_lyapunov_analytic_gradient_vs_numerical_finite_diff(self) -> None:
        test_points = [
            (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
            (0.5, -0.3, 0.8, -0.6, 0.2, -0.1),
            (-0.7, 0.4, -0.2, 0.9, -0.5, 0.3),
        ]
        eps = 1e-6
        for point in test_points:
            vec = StateVector6D(*point)
            analytic_grad = vec.lyapunov_gradient()

            numerical_grad = []
            for i in range(6):
                plus_coords = list(point)
                minus_coords = list(point)
                plus_coords[i] += eps
                minus_coords[i] -= eps
                v_plus = StateVector6D(*plus_coords).lyapunov_energy()
                v_minus = StateVector6D(*minus_coords).lyapunov_energy()
                numerical_grad.append((v_plus - v_minus) / (2.0 * eps))

            for i in range(6):
                self.assertAlmostEqual(
                    analytic_grad[i],
                    numerical_grad[i],
                    places=5,
                    msg=f"Gradient discrepancy at dim {i} for {point}",
                )

    def test_spatiotemporal_causal_invariance(self) -> None:
        origin = StateVector6D(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        target_subluminal = StateVector6D(0.3, 0.2, 0.1, 0.0, 0.0, 0.0)
        target_superluminal = StateVector6D(1.0, 1.0, 1.0, 1.0, 1.0, 1.0)

        # delta_tau = 1.0, c = 1.0
        self.assertTrue(target_subluminal.is_causally_valid(origin, delta_tau=1.0, c=1.0))
        self.assertFalse(target_superluminal.is_causally_valid(origin, delta_tau=1.0, c=1.0))
        self.assertFalse(target_subluminal.is_causally_valid(origin, delta_tau=0.0, c=1.0))

    def test_project_3d_coordinates(self) -> None:
        vec = StateVector6D(0.5, -0.5, 0.0, 1.0, -1.0, 0.5)
        x, y, z = vec.project_3d(lambda_factor=0.35)
        self.assertEqual(x, round(1.0 * 1.35 + 0.5 * 0.65, 4))
        self.assertEqual(y, round(-1.0 * 1.35 - 0.5 * 0.65, 4))
        self.assertEqual(z, round(0.5 * 1.35 + 0.0 * 0.65, 4))

    def test_channel_state_8d_byte_quantization(self) -> None:
        core = StateVector6D.from_discrete_code(42)  # 0b101010
        # Both channels positive -> bits 6 and 7 set
        state_both_on = ChannelState8D(core=core, q6_network_io=0.5, q7_sovereign_gate=0.8)
        self.assertEqual(state_both_on.to_byte_code(), 42 | (1 << 6) | (1 << 7))

        # Channel 6 negative, 7 positive -> only bit 7 set
        state_one_on = ChannelState8D(core=core, q6_network_io=-0.4, q7_sovereign_gate=0.1)
        self.assertEqual(state_one_on.to_byte_code(), 42 | (1 << 7))

        # Both channels negative -> unchanged from core code
        state_none_on = ChannelState8D(core=core, q6_network_io=-0.9, q7_sovereign_gate=-0.2)
        self.assertEqual(state_none_on.to_byte_code(), 42)

    def test_phase_space_12d_kinetic_energy_and_hamiltonian(self) -> None:
        q = StateVector6D.from_discrete_code(0)
        p = (1.0, 2.0, -1.0, 0.5, -0.5, 0.0)
        phase = PhaseSpaceState12D(q=q, p0=p[0], p1=p[1], p2=p[2], p3=p[3], p4=p[4], p5=p[5])

        mass = (1.0, 2.0, 1.0, 1.0, 1.0, 1.0)
        # T = 0.5 * (1^2/1 + 2^2/2 + (-1)^2/1 + 0.5^2/1 + (-0.5)^2/1 + 0^2/1)
        #   = 0.5 * (1 + 2 + 1 + 0.25 + 0.25 + 0) = 0.5 * 4.5 = 2.25
        self.assertEqual(phase.kinetic_energy(mass), 2.25)
        self.assertEqual(phase.hamiltonian(mass), 2.25 + q.lyapunov_energy())

    def test_phase_space_leapfrog_damping_reduces_momentum(self) -> None:
        q = StateVector6D.from_discrete_code(49)  # Code 49 has minimum lyapunov energy
        phase = PhaseSpaceState12D(q=q, p0=0.8, p1=0.8, p2=0.8, p3=0.8, p4=0.8, p5=0.8)

        # High damping step
        stepped = phase.leapfrog_step(delta_t=1.0, damping=(1.5, 1.5, 1.5, 1.5, 1.5, 1.5))
        # After damped step near local minimum, kinetic energy should drop
        self.assertLess(stepped.kinetic_energy(), phase.kinetic_energy())

    def test_jiao_yanshou_dual_codes(self) -> None:
        q = StateVector6D.from_discrete_code(0)  # All negative (-1.0)
        # Momentum pushes q0 and q2 positive
        phase = PhaseSpaceState12D(q=q, p0=1.5, p1=0.0, p2=1.5, p3=0.0, p4=0.0, p5=0.0)
        src, dst = phase.to_jiao_yanshou_dual_codes()
        self.assertEqual(src, 0)
        self.assertEqual(dst, (1 << 0) | (1 << 2))

    def test_safe_resolve_status_code_fallback(self) -> None:
        self.assertEqual(safe_resolve_status_code(None, fallback_code=35), 35)
        vec = StateVector6D.from_discrete_code(14)
        self.assertEqual(safe_resolve_status_code(vec, fallback_code=35), 14)

    def test_is_high_dim_enabled_environment_toggle(self) -> None:
        with patch.dict(os.environ, {"ONECODE_HIGH_DIM_DYNAMICS": "1"}):
            self.assertTrue(is_high_dim_enabled())
        with patch.dict(os.environ, {"ONECODE_HIGH_DIM_DYNAMICS": "0"}):
            self.assertFalse(is_high_dim_enabled())
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_high_dim_enabled())


if __name__ == "__main__":
    unittest.main()
