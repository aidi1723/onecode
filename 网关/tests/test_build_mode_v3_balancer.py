import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_skill_dictionary.build_mode_v3_balancer import (
    BAGUA_ELEMENT_MAP,
    FiveElementsDynamicBalancer,
    YinYangFiveElementsEngine,
    element_profile,
)


class FiveElementsDynamicBalancerTest(unittest.TestCase):
    def test_bagua_element_map_covers_all_eight_hexagrams(self):
        self.assertEqual(set(BAGUA_ELEMENT_MAP), {"000", "001", "010", "011", "100", "101", "110", "111"})
        self.assertEqual(element_profile("001").element, "木")
        self.assertEqual(element_profile("011").resource_role, "derivative_watchdog")
        self.assertEqual(element_profile("101").element, "火")
        self.assertEqual(element_profile("000").resource_role, "archive_lockdown")
        self.assertEqual(element_profile("100").resource_role, "hard_stop")
        self.assertEqual(element_profile("111").element, "金")
        self.assertEqual(element_profile("110").resource_role, "soft_rewrite")
        self.assertEqual(element_profile("010").resource_role, "stream_relay")

    def test_yinyang_engine_is_compatible_entrypoint_for_balancer(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = YinYangFiveElementsEngine(required_artifacts=["sync_node.py"])

            payload, hexagram, action = engine.enforce_balance_flow(
                payload={"messages": []},
                workspace=root,
                current_hexagram="000",
                last_pytest_output="",
            )

        self.assertEqual(payload["messages"], [])
        self.assertEqual(hexagram, "111")
        self.assertEqual(action, "scoped_writer")

    def test_fire_filter_dehydrates_long_pytest_output_to_causal_fingerprint(self):
        raw_log = "\n".join(
            [
                "Traceback (most recent call last):",
                '  File "/tmp/work/sync_node.py", line 40, in sync_inventory',
                "    response = httpx.post(endpoint, json=snapshot, timeout=2.0)",
                "httpx.ConnectError: manila node unavailable",
                *("DEBUG noisy repeated ledger trace" for _ in range(500)),
                "FAILED tests/test_sync.py::SyncNodeTest::test_retry_budget - httpx.ConnectError: manila node unavailable",
                "1 failed in 5.01s",
            ]
        )
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sync_node.py").write_text(
                "def sync_inventory(endpoint, snapshot):\n"
                "    return None\n",
                encoding="utf-8",
            )
            balancer = FiveElementsDynamicBalancer(required_artifacts=["sync_node.py"])

            digest = balancer.fire_digest(root, raw_log, max_chars=700)

        self.assertLessEqual(len(digest.text), 700)
        self.assertIn("httpx.ConnectError", digest.text)
        self.assertIn("sync_node.py:40", digest.text)
        self.assertIn("def sync_inventory(endpoint, snapshot)", digest.text)
        self.assertNotIn("DEBUG noisy repeated ledger trace", digest.text)

    def test_wood_watchdog_marks_repeated_failure_as_handoff_candidate(self):
        balancer = FiveElementsDynamicBalancer(required_artifacts=["sync_node.py"])
        previous = "FAILED tests/test_sync.py::test_retry - httpx.ConnectError: manila node unavailable"
        current = "FAILED tests/test_sync.py::test_retry - httpx.ConnectError: manila node unavailable"

        decision = balancer.align(
            payload={},
            workspace=".",
            current_hexagram="110",
            pytest_log=current,
            previous_failure_summary=previous,
        )

        self.assertEqual(decision.hexagram, "100")
        self.assertEqual(decision.action, "expert_handoff")
        self.assertEqual(decision.element, "木")
        self.assertTrue(decision.metadata["decay"]["deadlock_suspected"])

    def test_soil_gap_routes_to_create_and_complete_workspace_routes_to_verify(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            balancer = FiveElementsDynamicBalancer(required_artifacts=["sync_node.py"])

            missing = balancer.align(payload={}, workspace=root, current_hexagram="000", pytest_log="")
            (root / "sync_node.py").write_text("VALUE = 1\n", encoding="utf-8")
            complete = balancer.align(payload={}, workspace=root, current_hexagram="111", pytest_log="")

        self.assertEqual(missing.hexagram, "111")
        self.assertEqual(missing.action, "scoped_writer")
        self.assertEqual(missing.element, "土")
        self.assertEqual(missing.metadata["cosmology"]["force"], "yang")
        self.assertEqual(missing.metadata["cosmology"]["scope_name"], "太阳")
        self.assertEqual(missing.metadata["cosmology"]["element"], "金")
        self.assertEqual(complete.hexagram, "001")
        self.assertEqual(complete.action, "canonical_tester")
        self.assertEqual(complete.element, "金")
        self.assertEqual(complete.metadata["cosmology"]["resource_role"], "active_test_motion")


if __name__ == "__main__":
    unittest.main()
