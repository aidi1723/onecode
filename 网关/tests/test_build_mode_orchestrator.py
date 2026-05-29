import tempfile
import unittest
from pathlib import Path

from agent_skill_dictionary.build_mode_orchestrator import (
    CLUSTER_STATE_SYNC_ARTIFACTS,
    EPHEMERAL_MESH_KV_ARTIFACTS,
    SECURE_RPC_MESH_ARTIFACTS,
    artifact_plan_for_request,
    build_next_artifact_instruction,
    detect_artifact_gaps,
    ensure_support_files,
)


class BuildModeOrchestratorTest(unittest.TestCase):
    def test_secure_rpc_mesh_plan_has_required_files_in_order(self):
        plan = artifact_plan_for_request("请实现 secure-rpc-mesh")

        self.assertEqual(
            [artifact.path for artifact in plan.artifacts],
            [
                "core/crypto.py",
                "api/server.py",
                "tests/test_mesh.py",
                "README.md",
            ],
        )
        self.assertEqual(plan.artifacts, SECURE_RPC_MESH_ARTIFACTS)

    def test_cluster_state_sync_plan_has_required_files_in_order(self):
        plan = artifact_plan_for_request("请实现 cluster-state-sync")

        self.assertEqual(
            [artifact.path for artifact in plan.artifacts],
            [
                "sync/models.py",
                "sync/engine.py",
                "api/server.py",
                "tests/test_sync.py",
                "README.md",
            ],
        )
        self.assertEqual(plan.artifacts, CLUSTER_STATE_SYNC_ARTIFACTS)

    def test_sync_node_repair_plan_locks_to_existing_bug_file(self):
        plan = artifact_plan_for_request("修复 sync_node.py 同步死锁 Bug，跑测试，输出总结")

        self.assertEqual(plan.project_name, "secure-b2b-ledger-sync-repair")
        self.assertEqual([artifact.path for artifact in plan.artifacts], ["sync_node.py"])
        self.assertIn("sync_inventory", plan.artifacts[0].required_symbols)

    def test_ephemeral_mesh_kv_plan_has_three_required_assets_only(self):
        plan = artifact_plan_for_request("实现 ephemeral-mesh-kv 三节点 TTL Mesh 热数据缓存环")

        self.assertEqual(plan.project_name, "ephemeral-mesh-kv")
        self.assertEqual(
            [artifact.path for artifact in plan.artifacts],
            ["mesh_node.py", "consensus.py", "tests/test_mesh.py"],
        )
        self.assertEqual(plan.artifacts, EPHEMERAL_MESH_KV_ARTIFACTS)
        self.assertIn("MeshNode", plan.artifacts[0].required_symbols)
        self.assertIn("broadcast_put", plan.artifacts[1].required_symbols)
        self.assertIn("test_ttl", " ".join(plan.artifacts[2].required_symbols))

    def test_ephemeral_mesh_kv_support_files_only_add_tests_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            written = ensure_support_files(tmp, artifact_plan_for_request("ephemeral-mesh-kv"))

            self.assertEqual(written, ("tests/__init__.py",))
            self.assertTrue((Path(tmp) / "tests" / "__init__.py").exists())

    def test_cluster_state_sync_instruction_mentions_poison_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            gap = detect_artifact_gaps(tmp, artifact_plan_for_request("cluster-state-sync"))
            instruction = build_next_artifact_instruction(gap)

        self.assertIn("sync/models.py", instruction)
        self.assertIn("SQLModel", instruction)
        self.assertIn("kill -9", instruction)
        self.assertIn("拒绝", instruction)

    def test_gap_detector_returns_first_missing_required_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            gap = detect_artifact_gaps(tmp, artifact_plan_for_request("secure-rpc-mesh"))

        self.assertEqual(gap.next_artifact.path, "core/crypto.py")
        self.assertEqual(gap.missing_paths[0], "core/crypto.py")
        self.assertFalse(gap.complete)

    def test_gap_detector_skips_existing_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "core").mkdir()
            (root / "core" / "crypto.py").write_text("def generate_keypair():\n    pass\n", encoding="utf-8")

            gap = detect_artifact_gaps(tmp, artifact_plan_for_request("secure-rpc-mesh"))

        self.assertEqual(gap.next_artifact.path, "api/server.py")
        self.assertIn("api/server.py", gap.missing_paths)
        self.assertNotIn("core/crypto.py", gap.missing_paths)

    def test_next_artifact_instruction_locks_model_to_one_write_file_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            gap = detect_artifact_gaps(tmp, artifact_plan_for_request("secure-rpc-mesh"))
            instruction = build_next_artifact_instruction(gap)

        self.assertIn("本轮只写一个文件", instruction)
        self.assertIn("core/crypto.py", instruction)
        self.assertIn("write_file", instruction)
        self.assertIn("generate_keypair", instruction)
        self.assertNotIn("api/server.py", instruction.split("禁止")[0])

    def test_complete_plan_has_no_next_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for artifact in SECURE_RPC_MESH_ARTIFACTS:
                path = root / artifact.path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("ok\n", encoding="utf-8")

            gap = detect_artifact_gaps(tmp, artifact_plan_for_request("secure-rpc-mesh"))

        self.assertTrue(gap.complete)
        self.assertIsNone(gap.next_artifact)

    def test_ensure_support_files_adds_python_package_initializers(self):
        with tempfile.TemporaryDirectory() as tmp:
            written = ensure_support_files(tmp, artifact_plan_for_request("secure-rpc-mesh"))

            self.assertEqual(written, ("api/__init__.py", "core/__init__.py", "tests/__init__.py"))
            self.assertTrue((Path(tmp) / "api" / "__init__.py").exists())
            self.assertTrue((Path(tmp) / "core" / "__init__.py").exists())
            self.assertTrue((Path(tmp) / "tests" / "__init__.py").exists())


if __name__ == "__main__":
    unittest.main()
