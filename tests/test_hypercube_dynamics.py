from __future__ import annotations

import time
import unittest

from onecode.kernel.hypercube_vector import PhaseSpaceState12D, StateVector6D


class TestHypercubeDynamics(unittest.TestCase):
    def test_phase_space_trajectory_convergence(self) -> None:
        """Verify that a 12D phase space trajectory smoothly converges to low energy."""
        # Initial high-energy disturbed state: failing tests, messy diff
        initial_q = StateVector6D(q0=-0.6, q1=-0.8, q2=-0.5, q3=0.8, q4=1.0, q5=-0.7)
        initial_p = (0.2, 0.4, 0.1, -0.1, 0.0, 0.3)
        state = PhaseSpaceState12D(
            q=initial_q,
            p0=initial_p[0],
            p1=initial_p[1],
            p2=initial_p[2],
            p3=initial_p[3],
            p4=initial_p[4],
            p5=initial_p[5],
        )

        initial_energy = state.q.lyapunov_energy()
        trajectory: list[PhaseSpaceState12D] = [state]

        # Evolve for 25 steps under dissipative leapfrog
        damping = (0.8, 0.8, 0.8, 0.8, 0.8, 0.8)
        for _ in range(25):
            state = state.leapfrog_step(delta_t=0.5, damping=damping)
            trajectory.append(state)

        final_state = trajectory[-1]
        final_energy = final_state.q.lyapunov_energy()

        # Final energy should be significantly lower than initial
        self.assertLess(final_energy, initial_energy)
        # Final kinetic energy should be suppressed by damping
        self.assertLess(final_state.kinetic_energy(), 0.05)

    def test_oscillation_suppression_under_periodic_forcing(self) -> None:
        """Verify that five-phase damping eliminates cyclical bouncing between states."""
        q = StateVector6D(q0=0.1, q1=-0.1, q2=0.0, q3=0.5, q4=1.0, q5=0.2)
        state = PhaseSpaceState12D(q=q, p0=0.9, p1=-0.9, p2=0.5, p3=-0.2, p4=0.0, p5=0.1)
        initial_norm = sum(p * p for p in state.p_tuple()) ** 0.5

        for _ in range(15):
            state = state.leapfrog_step(delta_t=0.5, damping=(0.8, 0.8, 0.8, 0.8, 0.8, 0.8))

        final_norm = sum(p * p for p in state.p_tuple()) ** 0.5
        # Velocity norm should decay under damping
        self.assertLess(final_norm, initial_norm * 0.5)

    def test_spatiotemporal_worldline_causality_chain(self) -> None:
        """Verify that successive steps along the worldline respect the causal speed limit c=1.0."""
        q_current = StateVector6D(q0=0.0, q1=0.0, q2=0.0, q3=0.5, q4=1.0, q5=0.0)
        state = PhaseSpaceState12D(q=q_current, p0=0.1, p1=0.2, p2=0.05, p3=-0.05, p4=0.0, p5=0.1)

        c = 1.0
        delta_tau = 1.0  # 1 turn step
        for turn in range(1, 10):
            next_state = state.leapfrog_step(delta_t=1.0)
            # Spatial displacement per turn
            is_valid = next_state.q.is_causally_valid(state.q, delta_tau=delta_tau, c=c)
            self.assertTrue(
                is_valid,
                msg=f"Causal violation at turn {turn}: dist={next_state.q.distance_to(state.q)} > c*tau",
            )
            state = next_state

    def test_schlegel_projection_3d_continuity(self) -> None:
        """Verify that smooth continuous 6D trajectory projects to continuous 3D points."""
        q0 = StateVector6D(0.2, -0.4, 0.1, 0.8, 1.0, -0.3)
        state = PhaseSpaceState12D(q=q0, p0=0.05, p1=0.08, p2=0.02, p3=-0.02, p4=0.0, p5=0.04)

        prev_proj = state.q.project_3d(lambda_factor=0.35)
        for _ in range(10):
            state = state.leapfrog_step(delta_t=0.5)
            curr_proj = state.q.project_3d(lambda_factor=0.35)
            # 3D Euclidean displacement between half-steps should be small (< 0.5)
            dist_3d = sum((a - b) ** 2 for a, b in zip(curr_proj, prev_proj)) ** 0.5
            self.assertLess(dist_3d, 0.5)
            prev_proj = curr_proj

    def test_latency_and_throughput_benchmark(self) -> None:
        """Benchmark 1,000 steps of 12D Phase Space Leapfrog integration."""
        q = StateVector6D(0.1, 0.2, -0.3, 0.4, 0.9, -0.1)
        state = PhaseSpaceState12D(q=q, p0=0.1, p1=0.2, p2=-0.1, p3=0.05, p4=0.0, p5=0.1)

        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            state = state.leapfrog_step(delta_t=1.0)
        elapsed = time.perf_counter() - start

        steps_per_sec = iterations / max(1e-6, elapsed)
        latency_us = (elapsed / iterations) * 1e6

        # Must comfortably exceed 200 steps/sec on low-power edge IoT (Intel N100 / ARM)
        # and < 5,000 us (5 ms) per step, which is < 0.2% of a typical 2s LLM turn
        self.assertGreater(steps_per_sec, 200.0)
        self.assertLess(latency_us, 5000.0)


if __name__ == "__main__":
    unittest.main()
