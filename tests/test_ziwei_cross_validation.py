import json
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.checkpoint import write_checkpoint
from onecode.kernel.context import create_context
from onecode.kernel.hexagram import IchingKernel


class ZiweiCrossValidationTests(unittest.TestCase):
    def test_sovereign_branches_isomorphism_and_opposition(self):
        """Theorem 1 & 2: Bijective mapping and DuiGong == Opposite (错卦)."""
        branches = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")
        codes = IchingKernel.SOVEREIGN_HEXAGRAM_CODES
        names = IchingKernel.SOVEREIGN_HEXAGRAM_NAMES
        self.assertEqual(len(codes), 12)
        self.assertEqual(len(names), 12)

        for b_idx in range(12):
            code = codes[b_idx]
            opp_code = IchingKernel.opposite_hexagram(code)
            expected_opp_branch = (b_idx + 6) % 12
            expected_opp_code = codes[expected_opp_branch]
            self.assertEqual(
                opp_code,
                expected_opp_code,
                f"Branch {b_idx} ({branches[b_idx]}) opposite {opp_code} != expected {expected_opp_code}",
            )

    def test_triad_hypercube_symmetry(self):
        """Theorem 3: Triad harmony symmetry on Q_6."""
        codes = IchingKernel.SOVEREIGN_HEXAGRAM_CODES
        # Water: Shen(8), Zi(0), Chen(4) -> [56, 1, 31]
        water_codes = [codes[8], codes[0], codes[4]]
        water_yang = sum((c & 0b111111).bit_count() for c in water_codes)
        self.assertEqual(water_yang, 9)
        self.assertEqual(water_yang / 3.0, 3.0)

        # Fire: Yin(2), Wu(6), Xu(10) -> [7, 62, 32]
        fire_codes = [codes[2], codes[6], codes[10]]
        fire_yang = sum((c & 0b111111).bit_count() for c in fire_codes)
        self.assertEqual(fire_yang, 9)
        self.assertEqual(fire_yang / 3.0, 3.0)

        # Metal & Wood duals
        metal_codes = [codes[5], codes[9], codes[1]]
        wood_codes = [codes[11], codes[3], codes[7]]
        metal_yang = sum((c & 0b111111).bit_count() for c in metal_codes)
        wood_yang = sum((c & 0b111111).bit_count() for c in wood_codes)
        self.assertEqual(metal_yang, 10)
        self.assertEqual(wood_yang, 8)
        self.assertEqual((metal_yang + wood_yang) / 6.0, 3.0)

    def test_task_bureau_profile_scaling(self):
        """Test Five Elements Bureau (五行局) scale computation."""
        # Lightweight single-file
        b2 = IchingKernel.task_bureau_profile(file_count=1, total_loc=40)
        self.assertEqual(b2["bureau"], 2)
        self.assertEqual(b2["bureau_name"], "水二局")
        self.assertEqual(b2["turn_budget"], 3)
        self.assertEqual(b2["patch_strategy"], "surgical_diff_only")
        self.assertEqual(b2["preview_limit_chars"], 4000)
        self.assertEqual(b2["repair_file_limit"], 6)

        # Medium feature
        b3 = IchingKernel.task_bureau_profile(file_count=2, total_loc=90)
        self.assertEqual(b3["bureau"], 3)
        self.assertEqual(b3["bureau_name"], "木三局")
        self.assertEqual(b3["turn_budget"], 4)
        self.assertEqual(b3["preview_limit_chars"], 6000)
        self.assertEqual(b3["repair_file_limit"], 8)

        # Refactoring
        b4 = IchingKernel.task_bureau_profile(file_count=5, total_loc=400)
        self.assertEqual(b4["bureau"], 4)
        self.assertEqual(b4["bureau_name"], "金四局")
        self.assertEqual(b4["turn_budget"], 5)
        self.assertEqual(b4["preview_limit_chars"], 8000)
        self.assertEqual(b4["repair_file_limit"], 10)

        # Large persistence schema
        b5 = IchingKernel.task_bureau_profile(file_count=6, total_loc=650)
        self.assertEqual(b5["bureau"], 5)
        self.assertEqual(b5["bureau_name"], "土五局")
        self.assertEqual(b5["turn_budget"], 6)
        self.assertEqual(b5["preview_limit_chars"], 10000)
        self.assertEqual(b5["repair_file_limit"], 12)

        # Massive architecture evolution
        b6 = IchingKernel.task_bureau_profile(file_count=14, total_loc=2800)
        self.assertEqual(b6["bureau"], 6)
        self.assertEqual(b6["bureau_name"], "火六局")
        self.assertEqual(b6["turn_budget"], 8)
        self.assertEqual(b6["timeout_sec"], 180)
        self.assertEqual(b6["preview_limit_chars"], 14000)
        self.assertEqual(b6["repair_file_limit"], 16)

    def test_self_sihua_profile_detection(self):
        """Test detection of internal dissipation (自化忌 / 自化禄 / 自化权 / 自化科)."""
        # Circular read hesitation (自化忌)
        h1 = {"modified_files": [], "has_test_run": False}
        current_read = {"modified_files": [], "has_test_run": False}
        tags_ji = IchingKernel.self_sihua_profile(current_read, history=[h1])
        self.assertIn("自化忌:circular_read_hesitation", tags_ji)

        # Phantom completion without proof (自化禄)
        current_phantom = {"action": "complete", "modified_files": [], "test_passed": False}
        tags_lu = IchingKernel.self_sihua_profile(current_phantom, history=[])
        self.assertIn("自化禄:phantom_completion_without_verifier", tags_lu)

        # Scope explosion (自化权)
        current_scope = {"modified_files": [f"file_{i}.py" for i in range(10)]}
        tags_quan = IchingKernel.self_sihua_profile(current_scope, history=[])
        self.assertIn("自化权:excessive_scope_expansion", tags_quan)

        # Clean self-audit (自化科)
        current_audit = {"action": "audit", "read_files": ["tests/test_x.py"], "error_traceback": None}
        tags_ke = IchingKernel.self_sihua_profile(current_audit, history=[])
        self.assertIn("自化科:pre_execution_self_audit", tags_ke)

    def test_causal_origin_profile_tracing(self):
        """Test tracing causal origin palace (来因宫)."""
        history = [
            {"turn_id": 1, "branch_name": "子", "modified_files": []},
            {"turn_id": 2, "branch_name": "丑", "modified_files": ["src/planner.py"]},
            {"turn_id": 3, "branch_name": "寅", "modified_files": ["src/core_engine.py"]},
            {"turn_id": 4, "branch_name": "卯", "modified_files": ["tests/test_core.py"]},
        ]
        traceback = 'File "src/core_engine.py", line 42, in execute: NameError: undefined symbol'
        cause = IchingKernel.causal_origin_profile(traceback, history)
        self.assertIsNotNone(cause)
        self.assertEqual(cause["incoming_turn_id"], 3)
        self.assertEqual(cause["incoming_branch"], "寅")
        self.assertEqual(cause["culprit_file"], "src/core_engine.py")
        self.assertEqual(cause["target_rollback_point"], 2)

    def test_triad_consensus_profile_formations(self):
        """Test 4-point distributed consensus (三方四正) pattern formations."""
        # Deadlock (羊陀夹忌): Verifier fails while resource is truncated
        deadlock = IchingKernel.triad_consensus_profile(
            turn_number=5,
            current_status=1,
            ast_valid=True,
            token_budget_ok=False,
            verifier_passed=False,
            environment_ok=True,
        )
        self.assertEqual(deadlock["pattern"], "羊陀夹忌")
        self.assertEqual(deadlock["pattern_level"], "broken")
        self.assertEqual(deadlock["recommended_remedy"], "switch_to_surgical_unified_diff")

        # Full consensus (三奇加会): All 4 dimensions valid
        success = IchingKernel.triad_consensus_profile(
            turn_number=6,
            current_status=63,
            ast_valid=True,
            token_budget_ok=True,
            verifier_passed=True,
            environment_ok=True,
        )
        self.assertEqual(success["pattern"], "三奇加会")
        self.assertEqual(success["pattern_level"], "excellent")
        self.assertEqual(success["recommended_remedy"], "proceed_to_commit")

        # Verified patch (科权双会)
        verified = IchingKernel.triad_consensus_profile(
            turn_number=3,
            current_status=7,
            ast_valid=True,
            token_budget_ok=False,
            verifier_passed=True,
            environment_ok=True,
        )
        self.assertEqual(verified["pattern"], "科权双会")
        self.assertEqual(verified["pattern_level"], "reinforced")

        # External Gateway failure (化忌入迁移)
        gw_failure = IchingKernel.triad_consensus_profile(
            turn_number=1,
            current_status=1,
            ast_valid=True,
            token_budget_ok=True,
            verifier_passed=True,
            environment_ok=False,
        )
        self.assertEqual(gw_failure["pattern"], "化忌入迁移")
        self.assertEqual(gw_failure["pattern_level"], "caution")
        self.assertEqual(gw_failure["recommended_remedy"], "retry_with_system_embedding_and_backoff")

    def test_checkpoint_telemetry_includes_triad_consensus(self):
        """Test that write_checkpoint telemetry contains triad_consensus seamlessly."""
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="ziwei-checkpoint-test")
            checkpoint_path = write_checkpoint(
                context=context,
                payload={"task": "ziwei consensus check", "status": "checkpoint"},
                next_state="000001",
                status="checkpoint",
                partial=False,
                reason=None,
                iching_status_code=1,
            )
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            telemetry = checkpoint["telemetry"]

            # Standard keys preserved
            self.assertEqual(telemetry["cycle_phase"], "复")
            self.assertEqual(telemetry["pattern_name"], "成格")
            self.assertIn("sihua", telemetry)

            # New triad_consensus present
            self.assertIn("triad_consensus", telemetry)
            consensus = telemetry["triad_consensus"]
            self.assertEqual(consensus["turn_number"], 1)
            self.assertEqual(consensus["branch"], "子")
            self.assertEqual(consensus["pattern"], "三奇加会")
            self.assertEqual(consensus["pattern_level"], "excellent")

            # New temporal_superposition present
            self.assertIn("temporal_superposition", telemetry)
            superposition = telemetry["temporal_superposition"]
            self.assertEqual(superposition["macro_stage"], "implementation")
            self.assertEqual(superposition["superposition_state"], "harmonious_progression")
            self.assertEqual(superposition["risk_level"], "low")

    def test_resolve_task_bureau_for_workspace(self):
        """Test resolve_task_bureau computes bureau from workspace files."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "a.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
            (ws / "b.py").write_text("z = 3\n", encoding="utf-8")

            from onecode.kernel.model_loop import resolve_task_bureau, workspace_scale_stats

            fc, loc = workspace_scale_stats(ws)
            self.assertEqual(fc, 2)
            self.assertEqual(loc, 3)

            bureau = resolve_task_bureau(ws)
            self.assertEqual(bureau["bureau"], 2)
            self.assertEqual(bureau["bureau_name"], "水二局")
            self.assertEqual(bureau["patch_strategy"], "surgical_diff_only")

    def test_repair_prompt_injects_causal_root_trace_and_deadlock_guidance(self):
        """Test repair_prompt dynamically injects Ziwei causal trace and deadlock alerts."""
        from onecode.kernel.model_loop import repair_prompt

        failed_with_deadlock = {
            "status": "failed",
            "reason": "verifier_failed",
            "execution_trace": {
                "runner_results": [
                    {"reason": "model response was truncated: exceeded 4096 tokens"}
                ]
            },
            "verifier_results": [
                {"stderr_tail": "AssertionError: expected 42 but got None in test_flow.py", "reason": "assertion_error"}
            ],
            "turn_history": [
                {"turn_id": 1, "branch_name": "子", "modified_files": []},
                {"turn_id": 2, "branch_name": "丑", "modified_files": ["src/calculator.py"]},
            ],
        }

        # The error traceback mentions test_flow.py, but let's test when traceback mentions calculator.py
        failed_with_causal_root = {
            "status": "failed",
            "reason": "verifier_failed",
            "execution_trace": {},
            "verifier_results": [
                {
                    "stderr_tail": 'File "src/calculator.py", line 12: ZeroDivisionError',
                    "reason": "crash",
                }
            ],
            "turn_history": [
                {"turn_id": 1, "branch_name": "子", "modified_files": []},
                {"turn_id": 2, "branch_name": "丑", "modified_files": ["src/calculator.py"]},
            ],
        }

        # Deadlock prompt check
        deadlock_prompt = repair_prompt("fix calculation", failed_with_deadlock)
        self.assertIn("Deadlock alert (羊陀夹忌)", deadlock_prompt)
        self.assertIn("surgical search_block/replace_block patches", deadlock_prompt)

        # Causal root trace prompt check
        causal_prompt = repair_prompt("fix calculation", failed_with_causal_root)
        self.assertIn("Causal root trace (来因宫 丑)", causal_prompt)
        self.assertIn("src/calculator.py", causal_prompt)

    def test_ziwei_mathematical_audit_certificates(self):
        """Test the formal mathematical audit certificates for Ziwei isomorphism and coupling."""
        ring = IchingKernel.sovereign_ring_isomorphism_certificate()
        self.assertEqual(ring["status"], "verified")
        self.assertTrue(ring["opposition_involution_verified"])
        self.assertTrue(ring["triad_balance_verified"])
        self.assertEqual(ring["mean_yang_water"], 3.0)
        self.assertEqual(ring["mean_yang_fire"], 3.0)
        self.assertEqual(ring["dual_axis_mean"], 3.0)

        an_he = IchingKernel.an_he_coupling_certificate()
        self.assertEqual(an_he["status"], "verified")
        self.assertTrue(an_he["distance_palindrome_verified"])
        self.assertTrue(an_he["dual_sums_constant_12"])
        self.assertEqual(an_he["hamming_distances"], [1, 3, 5, 5, 3, 1])
        self.assertEqual(an_he["yang_sums"], [3, 3, 5, 7, 9, 9])
        self.assertEqual(an_he["mean_yang_per_pair"], 3.0)

        audit = IchingKernel.ziwei_mathematical_audit()
        self.assertEqual(audit["status"], "ok")
        self.assertIn("sovereign_ring", audit)
        self.assertIn("an_he_coupling", audit)

    def test_cli_math_audit_includes_ziwei_audit(self):
        """Test CLI math-audit includes ziwei_audit in its payload."""
        import os
        import subprocess
        import sys

        env = os.environ.copy()
        env["PYTHONPATH"] = "src"
        completed = subprocess.run(
            [sys.executable, "-m", "onecode.cli", "math-audit"],
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )
        data = json.loads(completed.stdout)
        self.assertIn("ziwei_audit", data)
        self.assertEqual(data["ziwei_audit"]["status"], "ok")
        self.assertIn("ziwei_isomorphism_and_coupling", data["accepted_mappings"])

    def test_temporal_superposition_profile(self):
        """Test macro stage and micro turn superposition (大限流年叠宫)."""
        # Exploration: test failure is tolerated as exploratory learning
        exp = IchingKernel.temporal_superposition_profile("exploration", 1, "test_failure")
        self.assertEqual(exp["superposition_state"], "exploratory_feedback_tolerated")
        self.assertEqual(exp["policy_action"], "discover")
        self.assertEqual(exp["risk_level"], "tolerated")

        # Implementation: test failure triggers repair
        imp = IchingKernel.temporal_superposition_profile("implementation", 1, "test_failure")
        self.assertEqual(imp["superposition_state"], "repairable_defect")
        self.assertEqual(imp["policy_action"], "repair")
        self.assertEqual(imp["risk_level"], "medium")

        # Delivery: test failure is fatal regression -> immediate rollback
        deliv = IchingKernel.temporal_superposition_profile("delivery", 1, "test_failure")
        self.assertEqual(deliv["superposition_state"], "fatal_regression_in_delivery")
        self.assertEqual(deliv["policy_action"], "rollback")
        self.assertEqual(deliv["risk_level"], "critical")

        # Success in any stage -> harmonious progression
        ok = IchingKernel.temporal_superposition_profile("delivery", 63, "completed")
        self.assertEqual(ok["superposition_state"], "harmonious_progression")
        self.assertEqual(ok["risk_level"], "low")

    def test_bureau_scaled_file_repair_preview_and_tokens(self):
        """Test bureau scaling dynamically adjusts preview truncation limits and token expansion."""
        from onecode.kernel.model_loop import _src_files_for_repair
        from onecode.web.api import _task_tokens

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            src_dir = ws / "src"
            src_dir.mkdir()
            large_file = src_dir / "service.py"
            large_file.write_text("A" * 6000, encoding="utf-8")

            # Default bureau on tiny workspace is 水二局 (preview_limit=4000)
            res = _src_files_for_repair(ws)
            self.assertIn("src/service.py", res)
            self.assertIn("TRUNCATED: preview limited to 4000", res["src/service.py"])

            # Explicit preview limit expansion (e.g. 火六局)
            res_expanded = _src_files_for_repair(ws, preview_limit=8000)
            self.assertNotIn("TRUNCATED", res_expanded["src/service.py"])
            self.assertEqual(len(res_expanded["src/service.py"]), 6000)

        # Chinese task token extraction & 3-character token retention
        task = "按文件内容加载配置，不依赖 env 前缀"
        tokens = _task_tokens(task)
        self.assertIn("config", tokens)
        self.assertIn("load", tokens)
        self.assertIn("env", tokens)
        self.assertIn("prefix", tokens)

    def test_ziwei_pattern_matrix_formations(self):
        """Test comprehensive classification across classical Ziwei formations."""
        # 1. 羊陀夹忌 (Deadlock pinch)
        p_deadlock = IchingKernel.ziwei_pattern_matrix_profile(
            turn_number=1, current_status=32, verifier_passed=False, token_budget_ok=False
        )
        self.assertEqual(p_deadlock["pattern"], "羊陀夹忌")
        self.assertEqual(p_deadlock["level"], "broken")
        self.assertEqual(p_deadlock["remedy"], "switch_to_surgical_unified_diff")

        # 2. 铃昌陀武 (Fatal regression)
        p_fatal = IchingKernel.ziwei_pattern_matrix_profile(
            turn_number=2, current_status=32, fatal_regression=True
        )
        self.assertEqual(p_fatal["pattern"], "铃昌陀武")
        self.assertEqual(p_fatal["level"], "critical")
        self.assertEqual(p_fatal["action"], "rollback")

        # 3. 火铃夹命 (Frantic syntax churn)
        p_frantic = IchingKernel.ziwei_pattern_matrix_profile(
            turn_number=3, current_status=32, verifier_passed=False, consecutive_syntax_errors=2
        )
        self.assertEqual(p_frantic["pattern"], "火铃夹命")
        self.assertEqual(p_frantic["action"], "cooldown")

        # 4. 空劫夹命 (Hallucinated symbols)
        p_halluc = IchingKernel.ziwei_pattern_matrix_profile(
            turn_number=1, current_status=32, undefined_symbols_count=1
        )
        self.assertEqual(p_halluc["pattern"], "空劫夹命")
        self.assertEqual(p_halluc["action"], "reanchor")

        # 5. 化忌入迁移 (Gateway / environment failure)
        p_env = IchingKernel.ziwei_pattern_matrix_profile(
            turn_number=1, current_status=32, environment_ok=False
        )
        self.assertEqual(p_env["pattern"], "化忌入迁移")
        self.assertEqual(p_env["action"], "retry")

        # 6. 自化忌 (Circular read hesitation)
        p_read = IchingKernel.ziwei_pattern_matrix_profile(
            turn_number=4, current_status=32, consecutive_read_stalls=2
        )
        self.assertEqual(p_read["pattern"], "自化忌")
        self.assertEqual(p_read["action"], "synthesize")

        # 7. 化忌入官禄 (Test assertion failure)
        p_guan = IchingKernel.ziwei_pattern_matrix_profile(
            turn_number=2, current_status=32, verifier_passed=False
        )
        self.assertEqual(p_guan["pattern"], "化忌入官禄")
        self.assertEqual(p_guan["action"], "repair")

        # 8. 三奇加会 (Pure yang 63, all clean)
        p_sanqi = IchingKernel.ziwei_pattern_matrix_profile(
            turn_number=5, current_status=63, ast_valid=True, token_budget_ok=True, verifier_passed=True, environment_ok=True
        )
        self.assertEqual(p_sanqi["pattern"], "三奇加会")
        self.assertEqual(p_sanqi["level"], "excellent")
        self.assertEqual(p_sanqi["action"], "commit")

        # 9. 科权双会 (Syntax & test passing)
        p_kequan = IchingKernel.ziwei_pattern_matrix_profile(
            turn_number=3, current_status=31, ast_valid=True, verifier_passed=True, token_budget_ok=True
        )
        self.assertEqual(p_kequan["pattern"], "科权双会")
        self.assertEqual(p_kequan["level"], "reinforced")

        # 10. 机月同梁 (Methodical execution)
        p_jiyue = IchingKernel.ziwei_pattern_matrix_profile(
            turn_number=2, current_status=15, ast_valid=True, token_budget_ok=True
        )
        self.assertEqual(p_jiyue["pattern"], "机月同梁")
        self.assertEqual(p_jiyue["level"], "balanced")

    def test_repair_guidance_ziwei_pattern_injection(self):
        """Test repair guidance injects patterns into repair prompt."""
        from onecode.kernel.model_loop import _format_ziwei_repair_guidance

        # Deadlock
        res1 = {"status": "halted", "verifier_results": [{"reason": "verifier_failed"}]}
        g1 = _format_ziwei_repair_guidance(res1, ["verifier_failed", "truncated source preview"])
        self.assertTrue(any("羊陀夹忌" in line for line in g1))

        # Frantic retry
        res2 = {"status": "halted"}
        g2 = _format_ziwei_repair_guidance(res2, ["SyntaxError: invalid syntax", "patch_mismatch"])
        self.assertTrue(any("火铃夹命" in line for line in g2))

        # Hallucination
        res3 = {"status": "halted"}
        g3 = _format_ziwei_repair_guidance(res3, ["NameError: name 'MissingFoo' is not defined"])
        self.assertTrue(any("空劫夹命" in line for line in g3))


if __name__ == "__main__":
    unittest.main()
