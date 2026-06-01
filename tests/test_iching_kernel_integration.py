import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from onecode.kernel.checkpoint import canonical_json_line, ensure_profile_registry_entry, profile_sha256, sha256_text
from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.runner import run_task


class IchingKernelIntegrationTests(unittest.TestCase):
    def test_multi_asset_path_breach_records_li_kun_status_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = run_task(
                "path breach",
                workspace=workspace,
                run_id="li-kun-run",
                write_texts=[
                    "src/a.py=a = 1\n",
                    "src/b.py=b = 1\n",
                    "../outside.py=blocked\n",
                    "src/after.py=after = 1\n",
                ],
            )

            manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
            ledger = json.loads(Path(result["ledger_path"]).read_text(encoding="utf-8"))
            expected = IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN)

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "sovereignty_breach")
            self.assertEqual(result["iching_status_code"], expected)
            self.assertEqual(result["iching_profile"]["status_code"], expected)
            self.assertEqual(result["iching_profile"]["outer_element"], "fire")
            self.assertIn("transition", result["iching_profile"]["rule_layers"]["onecode_runtime"])
            self.assertIn("global_entropy", result["iching_profile"]["rule_layers"]["onecode_runtime"])
            self.assertIn("lyapunov_energy", result["iching_profile"]["rule_layers"]["onecode_runtime"])
            self.assertIn("polarity_index", result["iching_profile"]["rule_layers"]["bit_derived"])
            self.assertIn("evolved_element_modulation", result["iching_profile"]["rule_layers"]["correspondence_derived"])
            self.assertEqual(ledger["iching_status_code"], expected)
            self.assertEqual(ledger["iching_profile"]["status_code"], expected)
            self.assertEqual(manifest["iching_status_code"], expected)
            self.assertEqual(manifest["iching_profile"]["status_code"], expected)
            self.assertEqual(manifest["checkpoints"][-1]["iching_status_code"], expected)
            self.assertEqual(manifest["checkpoints"][-1]["iching_profile"]["status_code"], expected)
            self.assertFalse((workspace / "src" / "after.py").exists())

    def test_multi_asset_timeout_records_kan_zhen_status_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            run_task(
                "source ready assets",
                workspace=workspace,
                run_id="source-run",
                write_texts=[
                    "src/a.py=a = 1\n",
                    "src/b.py=b = 1\n",
                ],
            )

            result = run_task(
                "timeout third asset",
                workspace=workspace,
                run_id="kan-zhen-run",
                resume_from_run_id="source-run",
                http_timeout_seconds=0.01,
                simulated_action_seconds=0.05,
                write_texts=[
                    "src/a.py=a = rewritten\n",
                    "src/b.py=b = rewritten\n",
                    "src/c.py=c = 1\n",
                ],
            )

            manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
            expected = IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.ZHEN)

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "http_timeout")
            self.assertEqual(result["iching_status_code"], expected)
            self.assertEqual(result["iching_profile"]["status_code"], expected)
            self.assertEqual(result["iching_profile"]["element_dynamics"]["modulation"], "recovery_seed")
            self.assertEqual(result["iching_profile"]["yin_yang"]["pressure"], "activate")
            self.assertEqual(manifest["iching_status_code"], expected)
            self.assertEqual(manifest["iching_profile"]["status_code"], expected)
            self.assertEqual(manifest["checkpoints"][-1]["iching_status_code"], expected)
            self.assertEqual(manifest["checkpoints"][-1]["iching_profile"]["status_code"], expected)
            self.assertFalse((workspace / "src" / "c.py").exists())

    def test_denied_tool_records_li_kun_status_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = run_task(
                "denied tool",
                workspace=workspace,
                run_id="denied-li-kun-run",
                intent_type="bash_execution",
                command="echo blocked",
            )

            manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
            expected = IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN)

            self.assertEqual(result["status"], "denied")
            self.assertEqual(result["reason"], "permission_denied")
            self.assertEqual(result["iching_status_code"], expected)
            self.assertEqual(result["iching_transition_action"], "halt")
            self.assertEqual(result["iching_transition_reason"], "sovereignty_fire_boundary_halt")
            self.assertEqual(manifest["iching_status_code"], expected)
            self.assertEqual(manifest["iching_transition_action"], "halt")
            self.assertEqual(manifest["checkpoints"][-1]["iching_status_code"], expected)
            self.assertEqual(manifest["checkpoints"][-1]["iching_transition_reason"], "sovereignty_fire_boundary_halt")

    def test_completed_multi_asset_run_records_gen_qian_status_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = run_task(
                "completed assets",
                workspace=workspace,
                run_id="qian-qian-run",
                write_texts=[
                    "src/a.py=a = 1\n",
                    "src/b.py=b = 1\n",
                ],
            )

            manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
            expected = IchingKernel.compute_status(IchingKernel.GEN, IchingKernel.QIAN)

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["iching_status_code"], expected)
            self.assertEqual(result["iching_transition_action"], "cooldown")
            self.assertEqual(result["iching_transition_reason"], "yang_overload_cooldown")
            self.assertEqual(result["iching_profile"]["status_code"], expected)
            self.assertEqual(result["iching_profile"]["yin_yang"]["pressure"], "stable")
            self.assertEqual(manifest["iching_status_code"], expected)
            self.assertEqual(manifest["iching_transition_action"], "cooldown")
            self.assertEqual(manifest["iching_transition_reason"], "yang_overload_cooldown")
            self.assertEqual(manifest["iching_profile"]["status_code"], expected)
            self.assertEqual(manifest["checkpoints"][-1]["iching_status_code"], expected)
            self.assertEqual(manifest["checkpoints"][-1]["iching_transition_action"], "cooldown")
            self.assertEqual(manifest["checkpoints"][-1]["iching_transition_reason"], "yang_overload_cooldown")
            self.assertEqual(manifest["checkpoints"][-1]["iching_profile"]["status_code"], expected)

    def test_completed_run_persists_compact_profiles_without_dropping_return_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_task(
                "compact normal evidence",
                workspace=Path(tmp),
                run_id="compact-normal",
                write_path="src/a.py",
                write_content="a = 1\n",
            )

            ledger = json.loads(Path(result["ledger_path"]).read_text(encoding="utf-8"))
            manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))

            self.assertIn("element_matrix", result["iching_profile"])
            self.assertIn("profile_sha256", ledger["iching_profile"])
            self.assertIn("profile_sha256", manifest["iching_profile"])
            self.assertIn("profile_sha256", manifest["checkpoints"][-1]["iching_profile"])
            self.assertNotIn("element_matrix", ledger["iching_profile"])
            self.assertNotIn("element_matrix", manifest["iching_profile"])
            self.assertNotIn("element_matrix", manifest["checkpoints"][-1]["iching_profile"])
            self.assertEqual(ledger["iching_profile"]["status_code"], result["iching_profile"]["status_code"])
            self.assertEqual(manifest["iching_profile"]["status_code"], result["iching_profile"]["status_code"])

    def test_completed_runs_register_full_profile_once_for_hash_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            first = run_task(
                "register profile one",
                workspace=workspace,
                run_id="registry-one",
                write_path="src/a.py",
                write_content="a = 1\n",
            )
            second = run_task(
                "register profile two",
                workspace=workspace,
                run_id="registry-two",
                write_path="src/b.py",
                write_content="b = 1\n",
            )

            first_ledger = json.loads(Path(first["ledger_path"]).read_text(encoding="utf-8"))
            second_manifest = json.loads(Path(second["manifest_path"]).read_text(encoding="utf-8"))
            profile_ref = first_ledger["iching_profile"]["profile_registry_ref"]
            profile_hash = first_ledger["iching_profile"]["profile_sha256"]
            registry_path = workspace / profile_ref
            registry_files = list((workspace / ".onecode" / "profile-registry").glob("*.json"))
            registry_profile = json.loads(registry_path.read_text(encoding="utf-8"))

            self.assertEqual(profile_hash, sha256_text(canonical_json_line(first["iching_profile"])))
            self.assertEqual(profile_hash, sha256_text(canonical_json_line(registry_profile)))
            self.assertIn("element_matrix", registry_profile)
            self.assertEqual(first["iching_profile"]["status_code"], registry_profile["status_code"])
            self.assertEqual(profile_hash, second_manifest["iching_profile"]["profile_sha256"])
            self.assertEqual(profile_ref, second_manifest["iching_profile"]["profile_registry_ref"])
            self.assertEqual(len(registry_files), 1)

    def test_completed_run_appends_compact_global_wal_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = run_task(
                "wal index",
                workspace=workspace,
                run_id="wal-index",
                write_path="src/a.py",
                write_content="a = 1\n",
            )

            wal_path = workspace / ".onecode" / "global-ledger.jsonl"
            entries = [
                json.loads(line)
                for line in wal_path.read_text(encoding="utf-8").splitlines()
                if line
            ]

            self.assertEqual(len(entries), 1)
            self.assertLess(len(wal_path.read_bytes()), 700)
            self.assertEqual(entries[0]["v"], 1)
            self.assertEqual(entries[0]["rid"], "wal-index")
            self.assertEqual(entries[0]["st"], "completed")
            self.assertEqual(entries[0]["cc"], 1)
            self.assertEqual(entries[0]["fc"], 0)
            self.assertEqual(entries[0]["ph"], profile_sha256(result["iching_profile"]))
            self.assertEqual(entries[0]["lp"], ".onecode/runs/wal-index/ledger.json")
            self.assertEqual(entries[0]["mp"], ".onecode/runs/wal-index/manifest.json")

    def test_single_completed_run_can_use_wal_only_evidence_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = run_task(
                "wal only",
                workspace=workspace,
                run_id="wal-only",
                write_path="src/a.py",
                write_content="a = 1\n",
                completed_evidence_mode="wal",
            )
            wal_path = workspace / ".onecode" / "global-ledger.jsonl"
            entries = [
                json.loads(line)
                for line in wal_path.read_text(encoding="utf-8").splitlines()
                if line
            ]
            metadata_bytes = sum(
                path.stat().st_size
                for path in (workspace / ".onecode").glob("**/*")
                if path.is_file()
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["evidence_mode"], "wal")
            self.assertIsNone(result["ledger_path"])
            self.assertIsNone(result["manifest_path"])
            self.assertIsNone(result["trace_path"])
            self.assertEqual(result["wal_path"], str(wal_path.resolve()))
            self.assertTrue(Path(result["wal_path"]).exists())
            self.assertFalse((workspace / ".onecode" / "runs" / "wal-only").exists())
            self.assertEqual(entries[0]["rid"], "wal-only")
            self.assertEqual(entries[0]["em"], "wal")
            self.assertIsNone(entries[0]["lp"])
            self.assertIsNone(entries[0]["mp"])
            self.assertLess(metadata_bytes, 31000)

    def test_wal_only_completed_run_does_not_create_per_run_evidence_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            original_mkdir = Path.mkdir
            mkdir_paths = []

            def spy_mkdir(path: Path, *args, **kwargs):
                mkdir_paths.append(path)
                return original_mkdir(path, *args, **kwargs)

            with patch("pathlib.Path.mkdir", new=spy_mkdir):
                result = run_task(
                    "wal lazy dirs",
                    workspace=workspace,
                    run_id="wal-lazy-dirs",
                    completed_evidence_mode="wal",
                )

            created_paths = {path.resolve() for path in mkdir_paths}
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["evidence_mode"], "wal")
            self.assertNotIn((workspace / ".onecode" / "runs" / "wal-lazy-dirs").resolve(), created_paths)
            self.assertNotIn((workspace / ".onecode" / "runs" / "wal-lazy-dirs" / "checkpoints").resolve(), created_paths)

    def test_wal_only_relaxed_durability_skips_fsync_for_normal_completed_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            run_task(
                "registry warmup",
                workspace=workspace,
                run_id="wal-relaxed-warmup",
                completed_evidence_mode="wal",
            )

            with patch("onecode.kernel.checkpoint.os.fsync") as fsync:
                result = run_task(
                    "wal relaxed",
                    workspace=workspace,
                    run_id="wal-relaxed",
                    completed_evidence_mode="wal",
                    evidence_durability="relaxed",
                )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["evidence_mode"], "wal")
            fsync.assert_not_called()

    def test_wal_only_strict_durability_fsyncs_normal_completed_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            run_task(
                "registry warmup",
                workspace=workspace,
                run_id="wal-strict-warmup",
                completed_evidence_mode="wal",
            )

            with patch("onecode.kernel.checkpoint.os.fsync") as fsync:
                result = run_task(
                    "wal strict",
                    workspace=workspace,
                    run_id="wal-strict",
                    completed_evidence_mode="wal",
                    evidence_durability="strict",
                )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["evidence_mode"], "wal")
            self.assertGreaterEqual(fsync.call_count, 1)

    def test_wal_only_relaxed_durability_keeps_denied_fallback_strict(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("onecode.kernel.checkpoint.os.fsync") as fsync:
                result = run_task(
                    "wal relaxed denied",
                    workspace=Path(tmp),
                    run_id="wal-relaxed-denied",
                    intent_type="bash_execution",
                    command="echo blocked",
                    completed_evidence_mode="wal",
                    evidence_durability="relaxed",
                )

            self.assertEqual(result["status"], "denied")
            self.assertEqual(result["evidence_mode"], "full")
            self.assertGreaterEqual(fsync.call_count, 1)

    def test_rejects_unknown_evidence_durability(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            with self.assertRaisesRegex(ValueError, "evidence_durability"):
                run_task(
                    "bad durability",
                    workspace=workspace,
                    run_id="bad-durability",
                    evidence_durability="unsafe",
                )
            self.assertFalse((workspace / ".onecode").exists())

    def test_rejects_unknown_completed_evidence_mode_without_creating_evidence_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            with self.assertRaisesRegex(ValueError, "completed_evidence_mode"):
                run_task(
                    "bad evidence mode",
                    workspace=workspace,
                    run_id="bad-evidence-mode",
                    completed_evidence_mode="unknown",
                )
            self.assertFalse((workspace / ".onecode").exists())

    def test_wal_only_mode_falls_back_to_full_evidence_for_denied_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_task(
                "wal only denied",
                workspace=Path(tmp),
                run_id="wal-denied",
                intent_type="bash_execution",
                command="echo blocked",
                completed_evidence_mode="wal",
            )

            self.assertEqual(result["status"], "denied")
            self.assertEqual(result["evidence_mode"], "full")
            self.assertTrue(Path(result["ledger_path"]).exists())
            self.assertTrue(Path(result["manifest_path"]).exists())

    def test_profile_registry_writes_shadow_copy_and_uses_workspace_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            profile = IchingKernel.cross_cutting_profile(
                IchingKernel.compute_status(IchingKernel.GEN, IchingKernel.QIAN)
            )
            expected_ref = f".onecode/profile-registry/{profile_sha256(profile)}.json"

            with patch("onecode.kernel.checkpoint.file_lock") as lock:
                lock.return_value.__enter__.return_value = None
                lock.return_value.__exit__.return_value = None
                ref = ensure_profile_registry_entry(workspace, profile)

            registry_path = workspace / expected_ref
            self.assertEqual(ref, expected_ref)
            self.assertEqual(lock.call_args.args[0], workspace / ".onecode" / "profile-registry" / ".registry.lock")
            self.assertTrue(registry_path.exists())
            self.assertTrue(registry_path.with_suffix(".json.bak").exists())

    def test_profile_hash_ignores_dynamic_runtime_fields(self):
        profile = IchingKernel.cross_cutting_profile(
            IchingKernel.compute_status(IchingKernel.GEN, IchingKernel.QIAN)
        )
        dynamic_profile = {
            **profile,
            "generated_at": "2026-06-01T00:00:00Z",
            "token_count": 42,
            "runtime_weight": 0.7,
            "dynamic_runtime": {"latency_ms": 12},
        }

        self.assertEqual(profile_sha256(profile), profile_sha256(dynamic_profile))

    def test_halted_run_persists_full_profile_for_forensics(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_task(
                "keep forensic profile",
                workspace=Path(tmp),
                run_id="full-forensics",
                intent_type="bash_execution",
                command="echo blocked",
            )

            ledger = json.loads(Path(result["ledger_path"]).read_text(encoding="utf-8"))
            manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))

            self.assertEqual(result["status"], "denied")
            self.assertIn("element_matrix", ledger["iching_profile"])
            self.assertIn("element_matrix", manifest["iching_profile"])
            self.assertIn("element_matrix", manifest["checkpoints"][-1]["iching_profile"])


if __name__ == "__main__":
    unittest.main()
