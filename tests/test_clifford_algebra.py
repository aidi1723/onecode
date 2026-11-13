"""Unit tests and benchmarks for 64-Dimensional Clifford Geometric Algebra Cl(6,0)."""
from __future__ import annotations

import math
import time
import unittest

from onecode.kernel.clifford_algebra import (
    BIVECTOR_PAIRS,
    CliffordMultivector64,
    GRADE_DIMENSIONS,
    NUM_DIMENSIONS,
    TOTAL_ALGEBRA_DIMENSION,
)
from onecode.kernel.hypercube_vector import StateVector6D


class TestCliffordAlgebra64(unittest.TestCase):
    def test_grade_dimension_distribution(self) -> None:
        """Verify exact binomial dimension distribution (1, 6, 15, 20, 15, 6, 1) summing to 64."""
        self.assertEqual(TOTAL_ALGEBRA_DIMENSION, 64)
        self.assertEqual(NUM_DIMENSIONS, 6)
        self.assertEqual(GRADE_DIMENSIONS, (1, 6, 15, 20, 15, 6, 1))
        self.assertEqual(sum(GRADE_DIMENSIONS), 64)
        self.assertEqual(len(BIVECTOR_PAIRS), 15)

    def test_basis_squaring_and_anticommutation(self) -> None:
        """Verify fundamental Clifford algebra relations e_i^2 = 1 and e_i e_j = -e_j e_i (i != j)."""
        bases = [CliffordMultivector64.basis(1 << i) for i in range(NUM_DIMENSIONS)]

        # 1. e_i^2 = 1 (Euclidean metric)
        for i, e_i in enumerate(bases):
            prod = e_i * e_i
            self.assertAlmostEqual(prod.components[0], 1.0, places=9)
            self.assertAlmostEqual(prod.total_norm(), 1.0, places=9)

        # 2. e_i e_j = - e_j e_i for i != j
        for i in range(NUM_DIMENSIONS):
            for j in range(NUM_DIMENSIONS):
                if i == j:
                    continue
                e_ij = bases[i] * bases[j]
                e_ji = bases[j] * bases[i]
                sum_anticomm = e_ij + e_ji
                self.assertAlmostEqual(sum_anticomm.total_norm(), 0.0, places=9)

        # 3. For orthogonal vectors, geometric product equals wedge product
        for i in range(NUM_DIMENSIONS):
            for j in range(i + 1, NUM_DIMENSIONS):
                e_geom = bases[i] * bases[j]
                e_wedge = bases[i].wedge_product(bases[j])
                diff = e_geom - e_wedge
                self.assertAlmostEqual(diff.total_norm(), 0.0, places=9)

    def test_hodge_dual_and_grade_reflection(self) -> None:
        """Verify Hodge dual maps Grade k to Grade (6 - k)."""
        for g in range(NUM_DIMENSIONS + 1):
            for mask in range(TOTAL_ALGEBRA_DIMENSION):
                if bin(mask).count("1") != g:
                    continue
                basis_k = CliffordMultivector64.basis(mask)
                dual_k = basis_k.hodge_dual()
                dual_grade = bin(dual_k.components.index(1.0) if 1.0 in dual_k.components else dual_k.components.index(-1.0)).count("1")
                self.assertEqual(dual_grade, NUM_DIMENSIONS - g)
                self.assertAlmostEqual(dual_k.total_norm(), 1.0, places=9)

    def test_embedding_and_projection_fidelity(self) -> None:
        """Verify lossless 6D StateVector6D embedding into Grade 1 and projection back."""
        q_original = StateVector6D(
            q0=0.75,
            q1=-0.50,
            q2=0.333,
            q3=-0.80,
            q4=1.00,
            q5=-0.125,
        )
        mv = CliffordMultivector64.from_vector6d(q_original)

        # Only Grade 1 should have non-zero norm
        norms = mv.grade_norms()
        self.assertAlmostEqual(norms[0], 0.0, places=9)
        self.assertGreater(norms[1], 0.0)
        self.assertAlmostEqual(sum(norms[2:]), 0.0, places=9)

        # Projection back must match original exactly
        q_restored = mv.to_vector6d()
        for c_orig, c_rest in zip(q_original.coords, q_restored.coords):
            self.assertAlmostEqual(c_orig, c_rest, places=9)

    def test_bivector_cross_coupling_torque_matrix(self) -> None:
        """Verify 15-dimensional bivector shear/rotation matrix Omega is anti-symmetric."""
        q1 = StateVector6D(1.0, 0.0, -0.5, 0.5, 1.0, -1.0)
        q2 = StateVector6D(0.0, 1.0, 0.5, -0.5, 1.0, 1.0)

        mv1 = CliffordMultivector64.from_vector6d(q1)
        mv2 = CliffordMultivector64.from_vector6d(q2)

        # Wedge product generates 15-dimensional bivector plane
        wedge = mv1.wedge_product(mv2)
        bivector_15d = wedge.to_bivector_15d_tuple()
        self.assertEqual(len(bivector_15d), 15)

        # Torque matrix Omega must be 6x6 anti-symmetric
        omega = wedge.bivector_torque_matrix()
        self.assertEqual(len(omega), 6)
        for i in range(6):
            self.assertEqual(len(omega[i]), 6)
            self.assertAlmostEqual(omega[i][i], 0.0, places=9)
            for j in range(6):
                self.assertAlmostEqual(omega[i][j], -omega[j][i], places=9)

    def test_performance_microbenchmark(self) -> None:
        """Benchmark 64-dimensional Clifford multivector geometric product throughput."""
        q1 = StateVector6D(0.1, -0.2, 0.3, -0.4, 0.5, -0.6)
        q2 = StateVector6D(-0.6, 0.5, -0.4, 0.3, -0.2, 0.1)

        mv1 = CliffordMultivector64.from_vector6d(q1)
        mv2 = CliffordMultivector64.from_vector6d(q2)

        iterations = 2000
        start = time.perf_counter()
        curr = mv1
        for _ in range(iterations):
            curr = curr * mv2
        elapsed = time.perf_counter() - start

        ops_per_sec = iterations / max(1e-6, elapsed)
        latency_us = (elapsed / iterations) * 1e6

        # Must comfortably exceed 10,000 ops/sec (< 100 us per operation)
        self.assertGreater(ops_per_sec, 10000.0)
        self.assertLess(latency_us, 100.0)


if __name__ == "__main__":
    unittest.main()
