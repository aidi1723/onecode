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


class ZiweiAnchorageAndAuditTests(unittest.TestCase):
    def test_shen_gong_subgroup_theorem_and_certificate(self):
        """Test Shen Gong Even Subgroup Theorem (身宫偶数子群同构定理 2*Z_12 ~= Z_6)."""
        cert = IchingKernel.shen_gong_anchorage_certificate()
        self.assertEqual(cert["status"], "verified")
        self.assertEqual(cert["image"], [0, 2, 4, 6, 8, 10])
        self.assertEqual(cert["image_cardinality"], 6)
        self.assertEqual(cert["kernel"], [0, 6])
        self.assertTrue(cert["antipodal_symmetry_verified"])
        self.assertTrue(cert["odd_palace_exclusion_verified"])
        self.assertEqual(cert["subgroup_isomorphism"], "2Z_12 ~= Z_6")

    def test_shen_gong_anchorage_profile_modes(self):
        """Test active anchorage resolution across different engineering pressures."""
        # 1. Verifier failure -> 官禄宫
        p_guan = IchingKernel.shen_gong_anchorage_profile(
            turn_number=2, current_status=32, verifier_passed=False
        )
        self.assertEqual(p_guan["active_index"], 8)
        self.assertEqual(p_guan["palace_name"], "官禄宫")
        self.assertEqual(p_guan["anchorage_mode"], "verifier_driven")
        self.assertIn("Anchor to test verifier", p_guan["shelter_guidance"])

        # 2. Token pressure / truncation -> 财帛宫
        p_cai = IchingKernel.shen_gong_anchorage_profile(
            turn_number=1, current_status=32, token_budget_ok=False
        )
        self.assertEqual(p_cai["active_index"], 4)
        self.assertEqual(p_cai["palace_name"], "财帛宫")
        self.assertEqual(p_cai["anchorage_mode"], "token_minimal_diff")

        # 3. Environment incident -> 迁移宫
        p_qian = IchingKernel.shen_gong_anchorage_profile(
            turn_number=3, current_status=32, environment_ok=False
        )
        self.assertEqual(p_qian["active_index"], 6)
        self.assertEqual(p_qian["palace_name"], "迁移宫")
        self.assertEqual(p_qian["anchorage_mode"], "environment_adaptive")

        # 4. Architectural risk -> 福德宫
        p_fu = IchingKernel.shen_gong_anchorage_profile(
            turn_number=4, current_status=15, architectural_risk=True
        )
        self.assertEqual(p_fu["active_index"], 10)
        self.assertEqual(p_fu["palace_name"], "福德宫")
        self.assertEqual(p_fu["anchorage_mode"], "architectural_integrity")

        # 5. Interop risk -> 夫妻宫
        p_qi = IchingKernel.shen_gong_anchorage_profile(
            turn_number=5, current_status=31, interop_risk=True
        )
        self.assertEqual(p_qi["active_index"], 2)
        self.assertEqual(p_qi["palace_name"], "夫妻宫")
        self.assertEqual(p_qi["anchorage_mode"], "interop_compatible")

        # 6. Baseline specification -> 命宫
        p_ming = IchingKernel.shen_gong_anchorage_profile(
            turn_number=1, current_status=1
        )
        self.assertEqual(p_ming["active_index"], 0)
        self.assertEqual(p_ming["palace_name"], "命宫")
        self.assertEqual(p_ming["anchorage_mode"], "contract_spec_driven")

    def test_ziwei_mathematical_audit_full_certification(self):
        """Test unified mathematical audit certifies all 3 Ziwei theorems."""
        audit = IchingKernel.ziwei_mathematical_audit()
        self.assertEqual(audit["status"], "ok")
        self.assertEqual(audit["sovereign_ring"]["status"], "verified")
        self.assertEqual(audit["an_he_coupling"]["status"], "verified")
        self.assertEqual(audit["shen_gong_anchorage"]["status"], "verified")

    def test_checkpoint_includes_shen_gong_telemetry(self):
        """Verify checkpoint telemetry records shen_gong_anchorage."""
        with tempfile.TemporaryDirectory() as tmp:
            evidence_root = Path(tmp)
            context = create_context(evidence_root, run_id="test-run-sg")
            chk_path = write_checkpoint(
                context=context,
                payload={"op": "write_text", "path": "app.py"},
                next_state=15,
                status="completed",
                partial=False,
                reason=None,
                iching_status_code=15,
            )
            data = json.loads(chk_path.read_text(encoding="utf-8"))
            telemetry = data["telemetry"]
            self.assertIn("shen_gong_anchorage", telemetry)
            self.assertIn("full_sihua_graph", telemetry)
            self.assertIn("system_pathology", telemetry)
            self.assertIn("six_channel_healing", telemetry)
            self.assertIn("doujun_chronology", telemetry)
            self.assertIn("auxiliary_stars_pairs", telemetry)
            self.assertIn("changsheng_lifecycle", telemetry)
            self.assertIn("guchen_guasu_huagai", telemetry)
            sg = telemetry["shen_gong_anchorage"]
            self.assertIn("active_index", sg)
            self.assertIn("palace_name", sg)
            self.assertEqual(sg["subgroup_parity"], "even_subgroup_2z12")

    def test_repair_guidance_injects_shen_gong_shelter(self):
        """Test repair guidance includes 身宫寄托 shelter directive."""
        from onecode.kernel.model_loop import _format_ziwei_repair_guidance

        res = {"status": "halted", "verifier_results": [{"reason": "verifier_failed"}]}
        guidance = _format_ziwei_repair_guidance(res, ["verifier_failed"])
        self.assertTrue(any("身宫寄托" in line for line in guidance))
        self.assertTrue(any("官禄宫" in line for line in guidance))

    def test_star_brightness_profile_and_governance(self):
        """Test star brightness (庙旺落陷) energy and throttle factor mapping."""
        # 1. Ground state 7 (泰) -> 庙旺
        b_ground = IchingKernel.star_brightness_profile(7)
        self.assertEqual(b_ground["brightness_label"], "庙旺")
        self.assertEqual(b_ground["governance_mode"], "autonomous")
        self.assertEqual(b_ground["throttle_factor"], 1.0)
        self.assertIn("commit", b_ground["permitted_actions"])

        # 2. Halt state 0 (坤) -> 落陷
        b_halt = IchingKernel.star_brightness_profile(0)
        self.assertEqual(b_halt["brightness_label"], "落陷")
        self.assertEqual(b_halt["governance_mode"], "degraded")
        self.assertEqual(b_halt["throttle_factor"], 0.25)
        self.assertNotIn("commit", b_halt["permitted_actions"])

        # 3. Broken pattern forces 落陷
        b_broken = IchingKernel.star_brightness_profile(15, pattern_level="broken")
        self.assertEqual(b_broken["brightness_label"], "落陷")
        self.assertEqual(b_broken["governance_mode"], "degraded")

        # 4. Certificate
        cert = IchingKernel.star_brightness_certificate()
        self.assertEqual(cert["status"], "verified")
        self.assertTrue(cert["boundary_soundness"])

    def test_repair_guidance_robust_against_none_and_injects_brightness(self):
        """Verify _format_ziwei_repair_guidance handles None task_status_code safely."""
        from onecode.kernel.model_loop import _format_ziwei_repair_guidance

        # Both task_status_code and iching_status_code are None
        res = {"status": "halted", "task_status_code": None, "iching_status_code": None}
        guidance = _format_ziwei_repair_guidance(res, ["verifier_failed"])
        self.assertTrue(any("星曜落陷" in line for line in guidance))
        self.assertTrue(any("Degraded protection mode" in line for line in guidance))

    def test_workspace_scale_stats_caching(self):
        """Verify workspace_scale_stats is memoized and resilient to missing paths."""
        from onecode.kernel.model_loop import workspace_scale_stats

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "a.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
            count, loc = workspace_scale_stats(ws)
            self.assertEqual(count, 1)
            self.assertEqual(loc, 2)

            # Second call should be instant from cache
            count2, loc2 = workspace_scale_stats(ws)
            self.assertEqual(count2, 1)
            self.assertEqual(loc2, 2)

    def test_executor_degraded_mode_blocks_full_file_rewrite(self):
        """Verify executor mechanically intercepts full-file rewrites when in degraded mode (落陷)."""
        from onecode.kernel.model_loop import execute_model_plan
        from onecode.kernel.model_provider import ModelPlan, ModelPlanAsset, ModelPlanPatch, ModelExecutionStep, ModelToolCall

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            target = ws / "module.py"
            target.write_text("INITIAL_CONTENT = True\n", encoding="utf-8")

            # 1. Full-file rewrite via assets in degraded mode must be mechanically rejected
            rewrite_plan = ModelPlan(
                task="rewrite module",
                assets=[ModelPlanAsset(path="module.py", content="NEW_CONTENT = False\n")],
            )
            halted_res = execute_model_plan(
                rewrite_plan,
                workspace=ws,
                http_timeout_seconds=5,
                run_id="degraded-asset-rewrite",
                resume_from_run_id=None,
                run_metadata={"governance_mode": "degraded"},
            )
            self.assertEqual(halted_res["status"], "halted")
            self.assertEqual(halted_res["reason"], "degraded_mode_disallows_full_file_rewrite")
            self.assertEqual(target.read_text(encoding="utf-8"), "INITIAL_CONTENT = True\n")

            # 2. Full-file rewrite via execution steps write_text in degraded mode
            step_plan = ModelPlan(
                task="rewrite via step",
                execution_steps=[
                    ModelExecutionStep(
                        id="step-1",
                        description="overwrite file",
                        tool_calls=[ModelToolCall(tool_name="write_text", params={"path": "module.py", "content": "FAIL"})],
                    )
                ],
            )
            halted_step = execute_model_plan(
                step_plan,
                workspace=ws,
                http_timeout_seconds=5,
                run_id="degraded-step-rewrite",
                resume_from_run_id=None,
                run_metadata={"governance_mode": "degraded"},
            )
            self.assertEqual(halted_step["status"], "halted")
            self.assertEqual(halted_step["reason"], "degraded_mode_disallows_full_file_rewrite")

            # 3. Patching in degraded mode is permitted
            patch_plan = ModelPlan(
                task="surgical patch",
                patches=[ModelPlanPatch(path="module.py", search_block="INITIAL_CONTENT = True\n", replace_block="INITIAL_CONTENT = False\n")],
            )
            ok_res = execute_model_plan(
                patch_plan,
                workspace=ws,
                http_timeout_seconds=5,
                run_id="degraded-patch-allowed",
                resume_from_run_id=None,
                run_metadata={"governance_mode": "degraded"},
                require_explicit_approval=False,
            )
            self.assertEqual(ok_res["status"], "completed")
            self.assertIn("INITIAL_CONTENT = False", target.read_text(encoding="utf-8"))

    def test_agent_cycle_bureau_turn_budget_adaptation(self):
        """Verify run_agent_cycle modulates default turn limit based on Five Elements Bureau."""
        from onecode.kernel.agent_cycle import run_agent_cycle

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "main.py").write_text("print('hello')\n", encoding="utf-8")
            # Small workspace -> 水二局 -> turn_budget = 3
            calls = []
            def propose(hist, allowed):
                calls.append(len(hist))
                return [{"tool_name": "read_text", "params": {"path": f"f{len(hist)}.txt"}}]
            def execute(t, p):
                return {"status": "completed", "reason": None, "content": "sample"}

            result = run_agent_cycle(propose=propose, execute=execute, workspace=ws)
            self.assertEqual(result["turn_budget"], 3)
            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "resource_budget_exceeded")
            self.assertEqual(result["turn_count"], 3)

    def test_star_dynamic_energy_profile_lucky_and_sha_balance(self):
        """Verify dynamic energy profile across 8 Lucky Stars and 6 Sha Stars."""
        # Dominant lucky state
        dominant = IchingKernel.star_dynamic_energy_profile(
            triad_consensus_score=1.0,
            ast_valid=True,
            environment_ok=True,
            cache_hit=True,
            step_duration_ms=5,
        )
        self.assertEqual(dominant["energy_state"], "harmonic_dominance")
        self.assertGreaterEqual(dominant["energy_differential"], 1.0)
        self.assertIn("zuo_you", dominant["lucky_stars"])
        self.assertIn("chang_qu", dominant["lucky_stars"])
        self.assertIn("kui_yue", dominant["lucky_stars"])
        self.assertIn("lu_ma", dominant["lucky_stars"])

        # Sha overload state (deadlock + syntax error + resource exhaustion)
        overload = IchingKernel.star_dynamic_energy_profile(
            triad_consensus_score=0.2,
            ast_valid=False,
            syntax_error=True,
            consecutive_stalls=2,
            resource_budget_exhausted=True,
        )
        self.assertEqual(overload["energy_state"], "sha_overload")
        self.assertLess(overload["energy_differential"], -0.5)
        self.assertIn("tuo_luo", overload["sha_stars"])
        self.assertIn("ling_xing", overload["sha_stars"])
        self.assertIn("di_jie", overload["sha_stars"])

    def test_jie_shen_relief_profile_and_recovery_policy_integration(self):
        """Verify Jie Shen (解神) relief arbitration and recovery policy integration."""
        from onecode.kernel.recovery_policy import recovery_status

        # 1. Deadlock (Tuo Luo) relief converts action to force_micro_patch
        relief_tuoluo = IchingKernel.jie_shen_relief_profile(
            turn_number=1,
            status_code=32,
            sha_stars=["tuo_luo"],
            attempt_count=1,
        )
        self.assertTrue(relief_tuoluo["relief_effective"])
        self.assertEqual(relief_tuoluo["recommended_action"], "force_micro_patch")
        self.assertIn(relief_tuoluo["jieshen_branch"], [0, 2, 4, 6, 8, 10])

        # 2. Recovery policy status payload includes Jie Shen relief
        status = recovery_status("verifier_failure", attempt_count=1)
        self.assertIn("jie_shen_relief", status)
        self.assertTrue(status["jie_shen_relief"]["relief_effective"])
        self.assertEqual(status["jie_shen_relief"]["recommended_action"], "cooldown_and_retry")

    def test_jie_shen_even_subgroup_theorem_and_certificate(self):
        """Verify Jie Shen Even Subgroup Theorem (Image in 2Z_12 ~= Z_6)."""
        cert = IchingKernel.jie_shen_even_subgroup_relief_certificate()
        self.assertEqual(cert["status"], "verified")
        self.assertEqual(cert["subgroup_isomorphism"], "2Z_12 ~= Z_6")
        self.assertEqual(cert["image"], [0, 2, 4, 6, 8, 10])
        self.assertTrue(cert["odd_palace_exclusion_verified"])
        self.assertTrue(cert["damping_bounded"])
        self.assertTrue(cert["shengong_dual_harmonic_coupling_verified"])

    def test_twelve_deities_triad_partition_and_suipo_involution_certificate(self):
        """Verify Twelve Auxiliary Deities Triad Partition and Sui Po Opposite Involution Theorem."""
        cert = IchingKernel.twelve_deities_triad_and_suipo_certificate()
        self.assertEqual(cert["status"], "verified")
        self.assertEqual(cert["triad_cardinal_points"], [0, 3, 6, 9])
        self.assertTrue(cert["triad_partition_verified"])
        self.assertTrue(cert["suipo_opposite_involution_verified"])
        self.assertTrue(cert["tian_de_long_de_even_coupling"])

    def test_twelve_deities_profile_and_governance_directives(self):
        """Verify Twelve Auxiliary Deities (将前/岁前/博士) profile and runtime governance."""
        from onecode.kernel.recovery_policy import recovery_status

        # 1. Opposite palace clash triggers Sui Po (岁破)
        # Turn 1 -> anchor_b = 0 (子). If active palace is 6 (午), sui_idx = 6 -> 岁破
        res_suipo = IchingKernel.twelve_deities_profile(turn_number=1, status_code=6)
        self.assertTrue(res_suipo["suipo_clash"])
        self.assertEqual(res_suipo["sui_qian_shen"], "岁破")
        self.assertEqual(res_suipo["governance_directive"], "barrier_synchronization_isolate_subtask")

        # 2. Tian De (天德) at (b + 9) % 12 -> active palace 9
        res_tiande = IchingKernel.twelve_deities_profile(turn_number=1, status_code=9)
        self.assertTrue(res_tiande["grace_shelter"])
        self.assertEqual(res_tiande["sui_qian_shen"], "天德")
        self.assertEqual(res_tiande["governance_directive"], "baseline_guarded_continue")

        # 3. Bai Hu (白虎) at (b + 8) % 12 -> active palace 8
        res_baihu = IchingKernel.twelve_deities_profile(turn_number=1, status_code=8)
        self.assertTrue(res_baihu["panic_risk"])
        self.assertEqual(res_baihu["sui_qian_shen"], "白虎")
        self.assertEqual(res_baihu["governance_directive"], "exception_quarantine_rollback")

        # 4. Jiang Xing (将星) momentum
        # Turn 1 -> anchor_b = 0 (Water Triad) -> jiang_start = 0 -> active palace 0 -> 将星
        res_jiang = IchingKernel.twelve_deities_profile(turn_number=1, status_code=0)
        self.assertTrue(res_jiang["momentum_accelerated"])
        self.assertEqual(res_jiang["jiang_qian_shen"], "将星")

        # 5. Recovery policy includes twelve_deities telemetry
        status = recovery_status("provider_failure", attempt_count=0)
        self.assertIn("twelve_deities", status)
        self.assertIn("sui_qian_shen", status["twelve_deities"])
        self.assertIn("jiang_qian_shen", status["twelve_deities"])

    def test_flying_sihua_cascade_profile_modes(self):
        """Verify Flying Sihua Cascade (跨宫飞星与四化多层叠象) collision detection."""
        # 1. Double Ji collision: Turn 3 (stem 2, Bing -> LianZhen Ji) in implementation stage (stem 2, LianZhen Ji)
        res_double_ji = IchingKernel.flying_sihua_cascade_profile(
            turn_number=3,
            status_code=7,
            macro_stage="implementation",
        )
        self.assertTrue(res_double_ji["double_ji"])
        self.assertEqual(res_double_ji["risk_level"], "critical")
        self.assertEqual(res_double_ji["damping_factor"], 0.25)
        self.assertEqual(res_double_ji["action"], "cascade_halt_quarantine")

        # 2. Opposite clash or stable envelope
        res_turn1 = IchingKernel.flying_sihua_cascade_profile(
            turn_number=1,
            status_code=7,
            macro_stage="implementation",
        )
        self.assertIn(res_turn1["risk_level"], {"elevated", "moderate", "stable", "minimal"})
        self.assertGreaterEqual(res_turn1["damping_factor"], 0.50)

    def test_flying_sihua_cascade_certificate(self):
        """Verify Flying Sihua Cascade & DuiGong Involution Mathematical Certificate."""
        cert = IchingKernel.flying_sihua_cascade_certificate()
        self.assertEqual(cert["status"], "verified")
        self.assertTrue(cert["sihua_totality_verified"])
        self.assertTrue(cert["duigong_involution_verified"])
        self.assertTrue(cert["damping_monotonic_verified"])

    def test_triadic_synthesis_profile_and_regimes(self):
        """Verify Ni Haixia Triadic Architectural Synthesis (天/地/人三纪会聚势能)."""
        # 1. Triadic harmony: Clean verification, safe environment, valid AST
        res_harmony = IchingKernel.triadic_synthesis_profile(
            status_code=7,
            environment_ok=True,
            path_guard_ok=True,
            verifier_passed=True,
            ast_valid=True,
        )
        self.assertEqual(res_harmony["regime"], "triadic_harmony")
        self.assertGreaterEqual(res_harmony["triadic_potential"], 0.80)
        self.assertTrue(res_harmony["domination_satisfied"])

        # 2. Physical minimal remediation: Verifier failed and environmental issues
        res_remedy = IchingKernel.triadic_synthesis_profile(
            status_code=32,
            environment_ok=False,
            path_guard_ok=False,
            verifier_passed=False,
            ast_valid=False,
        )
        self.assertEqual(res_remedy["regime"], "physical_remediation")
        self.assertLess(res_remedy["triadic_potential"], 0.55)
        self.assertEqual(res_remedy["governance"], "surgical_minimal_remedy")

    def test_triadic_synthesis_certificate(self):
        """Verify Triadic Synthesis and 2/3 Domination Mathematical Certificate."""
        cert = IchingKernel.triadic_synthesis_certificate()
        self.assertEqual(cert["status"], "verified")
        self.assertTrue(cert["convex_bounds_verified"])
        self.assertTrue(cert["two_thirds_domination_verified"])
        self.assertTrue(cert["physical_remediation_boundary_verified"])

    def test_ming_shen_zhu_symmetries(self):
        """Verify Ming Zhu and Shen Zhu symmetry profiles."""
        res_0 = IchingKernel.ming_shen_zhu_profile(turn_number=1, status_code=0)
        self.assertEqual(res_0["ming_zhu"], "贪狼")
        self.assertEqual(res_0["shen_zhu"], "火星")

        res_2 = IchingKernel.ming_shen_zhu_profile(turn_number=1, status_code=2)
        res_10 = IchingKernel.ming_shen_zhu_profile(turn_number=1, status_code=10)
        # Meridian mirror symmetry
        self.assertEqual(res_2["ming_zhu"], res_10["ming_zhu"])
        self.assertEqual(res_2["ming_zhu"], "禄存")

        res_8 = IchingKernel.ming_shen_zhu_profile(turn_number=1, status_code=8)
        # Antipodal invariance (2 + 6 = 8)
        self.assertEqual(res_2["shen_zhu"], res_8["shen_zhu"])
        self.assertEqual(res_2["shen_zhu"], "天梁")

    def test_ziwei_tianfu_duality_and_fixed_points(self):
        """Verify Ziwei-Tianfu duality axis and Tai-Pi fixed point cohabitation."""
        # Tai (code 7, branch 2, Yin) is fixed point
        res_tai = IchingKernel.ziwei_tianfu_duality_profile(status_code=7)
        self.assertTrue(res_tai["is_fixed_point"])
        self.assertTrue(res_tai["co_habitation"])
        self.assertEqual(res_tai["ziwei_branch"], 2)  # branch 2 (寅)
        # At branch 2 (寅):
        res_yin = IchingKernel.ziwei_tianfu_duality_profile(status_code=2)
        self.assertTrue(res_yin["is_fixed_point"])
        self.assertTrue(res_yin["co_habitation"])
        self.assertEqual(res_yin["axis_state"], "ziwei_tianfu_cohabitation")

        # Opposite polarity check
        res_opp = IchingKernel.ziwei_tianfu_duality_profile(status_code=11)  # Ziwei in Hai(11), Tianfu in Si(5)
        self.assertEqual(res_opp["circular_distance"], 6)
        self.assertEqual(res_opp["axis_state"], "ziwei_tianfu_opposite_polarity")

    def test_yang_tuo_clamping_and_midpoint(self):
        """Verify Qing Yang and Tuo Luo geometric clamping around Lu Cun."""
        # Turn 1 -> stem 0 (Jia) -> Lu Cun in Yin (2), Yang in Mao (3), Tuo in Chou (1)
        res_clamp = IchingKernel.yang_tuo_clamping_profile(turn_number=1, status_code=2, has_hua_ji=True)
        self.assertTrue(res_clamp["clamped_at_lucun"])
        self.assertTrue(res_clamp["yang_tuo_jia_ji"])
        self.assertEqual(res_clamp["action"], "break_deadlock_clamp_with_micro_patch")
        self.assertEqual(res_clamp["risk_level"], "critical")

        # Leading edge friction on Qing Yang
        res_yang = IchingKernel.yang_tuo_clamping_profile(turn_number=1, status_code=3)
        self.assertTrue(res_yang["on_yang_edge"])
        self.assertEqual(res_yang["action"], "suppress_cutting_edge_overwrite")

    def test_ziwei_tianfu_and_yangtuo_certificate(self):
        """Verify Ziwei-Tianfu Duality and Yang-Tuo Clamping Mathematical Certificate."""
        cert = IchingKernel.ziwei_tianfu_and_yangtuo_certificate()
        self.assertEqual(cert["status"], "verified")
        self.assertTrue(cert["ming_zhu_meridian_reflection_verified"])
        self.assertTrue(cert["shen_zhu_antipodal_invariance_verified"])
        self.assertTrue(cert["ziwei_tianfu_involution_verified"])
        self.assertTrue(cert["tai_pi_fixed_points_verified"])
        self.assertTrue(cert["yang_tuo_clamping_midpoint_verified"])

    def test_true_solar_time_and_zishi_boundary(self):
        """Verify True Solar Time computation, meridian shifts, and Zishi boundaries."""
        # Noon at reference 120 deg meridian
        res_noon = IchingKernel.true_solar_time_profile(2026, 6, 15, 12, 0, longitude=120.0)
        self.assertEqual(res_noon["branch"], 6)  # Wu (午)
        self.assertEqual(res_noon["branch_name"], "午")
        self.assertEqual(res_noon["longitude_correction_minutes"], 0.0)

        # Early Zishi (00:30)
        res_early = IchingKernel.true_solar_time_profile(2026, 1, 1, 0, 30, longitude=120.0)
        self.assertEqual(res_early["branch"], 0)  # Zi (子)
        self.assertTrue(res_early["is_early_zishi"])
        self.assertFalse(res_early["is_late_zishi"])

        # Late Zishi (23:45)
        res_late = IchingKernel.true_solar_time_profile(2026, 1, 1, 23, 45, longitude=120.0)
        self.assertEqual(res_late["branch"], 0)  # Zi (子)
        self.assertTrue(res_late["is_late_zishi"])
        self.assertFalse(res_late["is_early_zishi"])

        # Meridian shift: Urumqi (87.6 deg) is (87.6 - 120) * 4 = -129.6 minutes behind
        res_urumqi = IchingKernel.true_solar_time_profile(2026, 6, 15, 12, 0, longitude=87.6)
        self.assertAlmostEqual(res_urumqi["longitude_correction_minutes"], -129.6, places=1)
        self.assertNotEqual(res_urumqi["branch"], res_noon["branch"])

    def test_clock_drift_adaptation_regimes(self):
        """Verify clock drift classification into nominal, moderate, and critical WAL regimes."""
        res_nom = IchingKernel.clock_drift_adaptation_profile(clock_drift_seconds=5.0)
        self.assertEqual(res_nom["drift_severity"], "nominal")
        self.assertEqual(res_nom["wal_action"], "standard_append")

        res_mod = IchingKernel.clock_drift_adaptation_profile(clock_drift_seconds=120.0)
        self.assertEqual(res_mod["drift_severity"], "moderate_drift")
        self.assertEqual(res_mod["wal_action"], "append_skew_metadata")

        res_crit = IchingKernel.clock_drift_adaptation_profile(clock_drift_seconds=-1200.0)
        self.assertEqual(res_crit["drift_severity"], "critical_drift")
        self.assertEqual(res_crit["wal_action"], "barrier_wal_rotate")
        self.assertEqual(res_crit["governance_directive"], "clock_resync_rebase_epoch")

    def test_solar_equation_and_zishi_certificate(self):
        """Verify Solar Equation and Zishi Measure Partition Mathematical Certificate."""
        cert = IchingKernel.solar_equation_and_zishi_certificate()
        self.assertEqual(cert["status"], "verified")
        self.assertTrue(cert["eot_bounded_oscillation_verified"])
        self.assertTrue(cert["zishi_measure_partition_verified"])
        self.assertTrue(cert["meridian_linear_invariance_verified"])
        self.assertEqual(len(cert["branch_minute_counts"]), 12)
        self.assertTrue(all(cnt == 120 for cnt in cert["branch_minute_counts"]))

    def test_school_consensus_profile_stems(self):
        """Verify multi-school divergence arbitration across stems and Geng variants."""
        # Jia (stem 0) is unanimous
        res_jia = IchingKernel.school_consensus_profile(stem_index=0)
        self.assertFalse(res_jia["is_divergent"])
        self.assertEqual(res_jia["consensus_score"], 1.00)
        self.assertEqual(res_jia["governance_directive"], "unanimous_consensus_fastpath")

        # Geng (stem 6) default GYWYT
        res_geng = IchingKernel.school_consensus_profile(stem_index=6, geng_variant="GYWYT")
        self.assertTrue(res_geng["is_divergent"])
        self.assertEqual(res_geng["consensus_score"], 0.60)
        self.assertEqual(res_geng["governance_directive"], "majority_consensus_guarded")
        self.assertEqual(res_geng["active_sihua"], ["太阳", "武曲", "太阴", "天同"])

        # Geng (stem 6) variant GYWTY (Ke-Ji swap)
        res_swap = IchingKernel.school_consensus_profile(stem_index=6, geng_variant="GYWTY")
        self.assertEqual(res_swap["active_sihua"], ["太阳", "武曲", "天同", "太阴"])

    def test_school_divergence_consensus_certificate(self):
        """Verify Seven Stems Sihua Totality and Consensus Monotonicity Mathematical Certificate."""
        cert = IchingKernel.school_divergence_consensus_certificate()
        self.assertEqual(cert["status"], "verified")
        self.assertTrue(cert["seven_stems_unanimous_verified"])
        self.assertEqual(cert["unanimous_stem_indices"], [0, 1, 2, 3, 4, 5, 9])
        self.assertTrue(cert["geng_closure_verified"])
        self.assertTrue(cert["consensus_monotonicity_verified"])

    def test_classical_patterns_safety_dominance_and_tiers(self):
        """Verify 3-tier conditions and safety dominance of classical formation engine."""
        # Breaking pattern forces caution even with high status code
        res_breaking = IchingKernel.classical_patterns_profile(
            turn_number=1, status_code=63, fatal_regression=True
        )
        self.assertEqual(res_breaking["composite_pattern_level"], "caution")
        self.assertTrue(res_breaking["safety_dominance_active"])
        self.assertEqual(res_breaking["engineering_directive"], "defensive_minimal_diff_and_step_freeze")
        self.assertTrue(any(p["name"] == "铃昌陀武" for p in res_breaking["active_patterns"]))

        # Supreme Zi Fu cohabitation
        res_supreme = IchingKernel.classical_patterns_profile(
            turn_number=3, status_code=7, ast_valid=True, token_budget_ok=True, verifier_passed=True, environment_ok=True
        )
        self.assertEqual(res_supreme["composite_pattern_level"], "excellent")
        self.assertFalse(res_supreme["safety_dominance_active"])
        self.assertEqual(res_supreme["engineering_directive"], "high_speed_autonomous_pipeline")
        self.assertTrue(any(p["name"] == "紫府同宫" for p in res_supreme["active_patterns"]))

    def test_classical_patterns_certificate(self):
        """Verify Classical Formations Safety Dominance and Supreme Purity Mathematical Certificate."""
        cert = IchingKernel.classical_patterns_certificate()
        self.assertEqual(cert["status"], "verified")
        self.assertTrue(cert["safety_dominance_verified"])
        self.assertTrue(cert["supreme_purity_verified"])
        self.assertTrue(cert["formation_classification_verified"])

    def test_auxiliary_stars_polarity_profile(self):
        """Verify auxiliary stars polarity reversal across Yang/Yin stems and branches."""
        # Jia (stem 0, Yang) and Zi (branch 0, Yang)
        res_jia_zi = IchingKernel.auxiliary_stars_polarity_profile(year_stem=0, year_branch=0)
        self.assertEqual(res_jia_zi["stem_polarity"], "yang")
        self.assertEqual(res_jia_zi["branch_polarity"], "yang")
        # DaHao for Yang branch: (0 + 6 + 1) % 12 = 7 (午)
        self.assertEqual(res_jia_zi["dahao_branch"], 7)
        self.assertEqual(res_jia_zi["dahao_branch_name"], "未")
        # Jiekong for Jia (Yang stem): Shen (8, Yang), Fujie: You (9, Yin)
        self.assertEqual(res_jia_zi["jiekong_branch"], 8)
        self.assertEqual(res_jia_zi["fujie_branch"], 9)

        # Yi (stem 1, Yin) inverts Jiekong/Fujie polarity
        res_yi = IchingKernel.auxiliary_stars_polarity_profile(year_stem=1, year_branch=0)
        self.assertEqual(res_yi["stem_polarity"], "yin")
        # For Yi: pair is Wu(6)/Wei(7). Jiekong is in Yin branch (Wei 7), Fujie in Yang branch (Wu 6)
        self.assertEqual(res_yi["jiekong_branch"], 7)
        self.assertEqual(res_yi["fujie_branch"], 6)

    def test_nested_yunxian_temporal_profile(self):
        """Verify 7-tier nested temporal scopes and containment policies."""
        res_ming = IchingKernel.nested_yunxian_temporal_profile(view="mingpan", turn_number=1)
        self.assertEqual(res_ming["scope_rank"], 0)
        self.assertEqual(res_ming["containment_level"], "macro_governance")

        res_liu = IchingKernel.nested_yunxian_temporal_profile(view="liunian", turn_number=3)
        self.assertEqual(res_liu["scope_rank"], 2)
        self.assertEqual(res_liu["containment_level"], "cycle_governance")

        res_shi = IchingKernel.nested_yunxian_temporal_profile(view="liushi", turn_number=1)
        self.assertEqual(res_shi["scope_rank"], 6)
        self.assertEqual(res_shi["containment_level"], "micro_action")
        self.assertEqual(res_shi["isolation_policy"], "atomic_rollback_on_failure")

    def test_auxiliary_polarity_and_yunxian_certificate(self):
        """Verify DaHao Bijection, Jiekong Duality, and 7-tier Yunxian Hierarchy Certificate."""
        cert = IchingKernel.auxiliary_polarity_and_yunxian_certificate()
        self.assertEqual(cert["status"], "verified")
        self.assertTrue(cert["dahao_bijection_verified"])
        self.assertTrue(cert["jiekong_stem_duality_verified"])
        self.assertTrue(cert["yunxian_7_tier_hierarchy_verified"])

    def test_noble_horse_stars_profile(self):
        """Test Tiankui, Tianyue, Tianma, Hongluan, Tianxi and concurrency dynamics."""
        # Year Stem 0 (甲) -> Kui 1 (丑), Yue 7 (未), Lucun 2 (寅)
        # Year Branch 0 (子) -> Ma 2 (寅), Hongluan 3 (卯), Tianxi 9 (酉)
        res_kui = IchingKernel.noble_horse_stars_profile(year_stem=0, year_branch=0, active_palace=1)
        self.assertEqual(res_kui["tiankui_branch"], 1)
        self.assertEqual(res_kui["tianyue_branch"], 7)
        self.assertTrue(res_kui["kui_present"])
        self.assertEqual(res_kui["directive"], "noble_guardian_guided_pass")
        self.assertEqual(res_kui["throughput_multiplier"], 1.10)

        # Lu-Ma Jiao-Chi at branch 2 (寅) where both Lucun (2) and Tianma (2) meet!
        res_luma = IchingKernel.noble_horse_stars_profile(year_stem=0, year_branch=0, active_palace=2)
        self.assertTrue(res_luma["lu_ma_jiaochi"])
        self.assertEqual(res_luma["directive"], "lu_ma_jiaochi_accelerated_concurrency")
        self.assertEqual(res_luma["throughput_multiplier"], 1.25)

        # Broken leg horse
        res_broken = IchingKernel.noble_horse_stars_profile(year_stem=0, year_branch=0, active_palace=2, tuoluo_present=True)
        self.assertTrue(res_broken["broken_leg_horse"])
        self.assertEqual(res_broken["directive"], "broken_leg_horse_throttle")
        self.assertEqual(res_broken["throughput_multiplier"], 0.5)

        # Tianluo Diwang at branch 4 (辰) without Kui/Yue
        res_tianluo = IchingKernel.noble_horse_stars_profile(year_stem=0, year_branch=0, active_palace=4)
        self.assertTrue(res_tianluo["in_tianluo_diwang"])
        self.assertEqual(res_tianluo["directive"], "tianluo_diwang_cautious_step")
        self.assertEqual(res_tianluo["throughput_multiplier"], 0.75)

    def test_dual_sihua_superposition_profile(self):
        """Test dual-sihua same palace tensor arbitration."""
        # Quan + Ji (权忌同宫) -> Guarded authority
        res_qj = IchingKernel.dual_sihua_superposition_profile(0, ["化忌", "化权"])
        self.assertEqual(res_qj["composite_action"], "guarded_authority_verification")
        self.assertTrue(res_qj["write_permission"])
        self.assertTrue(res_qj["mandatory_audit"])

        # Lu + Ke (禄科同宫) -> Accelerated audited
        res_lk = IchingKernel.dual_sihua_superposition_profile(0, ["化禄", "化科"])
        self.assertEqual(res_lk["composite_action"], "accelerated_audited_execution")
        self.assertTrue(res_lk["write_permission"])
        self.assertFalse(res_lk["mandatory_audit"])

        # Lu + Quan (禄权同宫) -> Decisive expansion
        res_lq = IchingKernel.dual_sihua_superposition_profile(0, ["化禄", "化权"])
        self.assertEqual(res_lq["composite_action"], "decisive_expansion")

        # Ke + Ji (科忌同宫) -> Defensive verification
        res_kj = IchingKernel.dual_sihua_superposition_profile(0, ["化科", "化忌"])
        self.assertEqual(res_kj["composite_action"], "defensive_verification")
        self.assertFalse(res_kj["write_permission"])

        # Lu + Ji (禄忌相冲) -> Entropy dissipation
        res_lj = IchingKernel.dual_sihua_superposition_profile(0, ["化禄", "化忌"])
        self.assertEqual(res_lj["composite_action"], "entropy_dissipation_remediation")

    def test_multi_agent_synastry_and_famous_archetypes(self):
        """Test Ni Haisha Double Palace Synastry and Famous Historical Benchmarks."""
        # Mutual Ji clash triggers quarantined arbitration
        agent_a = {"stem": 0, "ming_branch": 0, "force_mutual_ji": True}
        agent_b = {"stem": 1, "ming_branch": 4, "force_mutual_ji": True}
        res_clash = IchingKernel.multi_agent_synastry_profile(agent_a, agent_b)
        self.assertEqual(res_clash["score"], "one_star")
        self.assertTrue(res_clash["isolation_required"])
        self.assertEqual(res_clash["coordination_mode"], "quarantined_arbitration_boundary")

        # Compromised deep invariant (Fude)
        agent_c = {"stem": 0, "ming_branch": 0, "fude_broken": True}
        agent_d = {"stem": 1, "ming_branch": 4}
        res_fude = IchingKernel.multi_agent_synastry_profile(agent_c, agent_d)
        self.assertEqual(res_fude["score"], "two_stars")
        self.assertEqual(res_fude["coordination_mode"], "guarded_contract_short_leash")

        # Tian-Zuo-Zhi-He mutual match (A fuqi matches B ming, B fuqi matches A ming)
        # A ming=2 -> fuqi=(2-2)%12=0; B ming=0 -> fuqi=(0-2)%12=10
        # If A ming=0 -> fuqi=10; B ming=10 -> fuqi=8 (unidirectional)
        # For bidirectional: A ming=0, fuqi=2; B ming=2, fuqi=0
        agent_e = {"stem": 0, "ming_branch": 0, "fuqi_branch": 2}
        agent_f = {"stem": 1, "ming_branch": 2, "fuqi_branch": 0}
        res_pair = IchingKernel.multi_agent_synastry_profile(agent_e, agent_f)
        self.assertEqual(res_pair["score"], "five_stars")
        self.assertEqual(res_pair["coordination_mode"], "high_bandwidth_synergistic_pair")

        # Famous benchmark archetypes
        mayun = IchingKernel.famous_archetype_profile("ma-yun")
        self.assertEqual(mayun["archetype"], "po_ge_chong_jian")
        self.assertEqual(mayun["recommended_strategy"], "high_entropy_refactoring")

        li = IchingKernel.famous_archetype_profile("li-jiacheng")
        self.assertEqual(li["archetype"], "lu_cun_shou_cai")

        ren = IchingKernel.famous_archetype_profile("ren-zhengfei")
        self.assertEqual(ren["archetype"], "qi_sha_ru_ming")

        jobs = IchingKernel.famous_archetype_profile("steve-jobs")
        self.assertEqual(jobs["archetype"], "po_jun_ru_ming")

        musk = IchingKernel.famous_archetype_profile("elon-musk")
        self.assertEqual(musk["archetype"], "sha_po_lang_tianma")

    def test_heming_synastry_and_noble_stars_certificate(self):
        """Formal mathematical certificate of Tianluo-Diwang Exclusion, Kui-Yue Reflection, Tianma Involution, and Synastry."""
        cert = IchingKernel.heming_synastry_and_noble_stars_certificate()
        self.assertEqual(cert["status"], "verified")
        self.assertTrue(cert["tianluo_diwang_exclusion_verified"])
        self.assertTrue(cert["kui_yue_symmetry_verified"])
        self.assertTrue(cert["tianma_corner_involution_verified"])
        self.assertTrue(cert["hongluan_derangement_verified"])
        self.assertTrue(cert["mutual_ji_deadlock_breaker_verified"])

    def test_full_sihua_graph_and_conservation(self):
        """Direction K: Full 48-Ray Directed Sihua Graph and Degree Conservation."""
        graph = IchingKernel.full_sihua_graph_profile(year_stem=0)
        self.assertEqual(len(graph["edges"]), 48)
        self.assertEqual(graph["total_edges"], 48)
        # Out-degree regularity: each of the 12 palaces has exactly 4 outgoing transformations
        self.assertEqual(len(graph["out_degrees"]), 12)
        for out_deg in graph["out_degrees"]:
            self.assertEqual(out_deg, 4)

        # In-degree sum must equal out-degree sum = 48
        self.assertEqual(len(graph["in_degrees"]), 12)
        self.assertEqual(sum(graph["in_degrees"]), 48)

        # Five Tigers stem distribution: exactly 2 stems appear twice, 8 stems appear once (surjection)
        counts = {}
        for stem in graph["palace_stems"]:
            counts[stem] = counts.get(stem, 0) + 1
        two_count = sum(1 for c in counts.values() if c == 2)
        one_count = sum(1 for c in counts.values() if c == 1)
        self.assertEqual(two_count, 2)
        self.assertEqual(one_count, 8)

        # Verify self-transformations, opposite projections, and cycle detection
        self.assertIsInstance(graph["self_transformations"], list)
        self.assertIsInstance(graph["opposite_projections"], list)
        self.assertIsInstance(graph["ji_cycles"], list)

    def test_bipartite_synastry_tensor_and_deadlocks(self):
        """Direction K: 144-Cell Bipartite Synastry Tensor and 96 Cross-Flying Rays."""
        agent_a = {"stem": 0, "ming_branch": 0, "fuqi_branch": 2}
        agent_b = {"stem": 1, "ming_branch": 6, "fuqi_branch": 8}
        syn = IchingKernel.bipartite_synastry_tensor_profile(agent_a, agent_b)

        # 144-cell tensor
        self.assertEqual(len(syn["tensor_12x12"]), 12)
        self.assertTrue(all(len(row) == 12 for row in syn["tensor_12x12"]))
        total_cells = sum(len(row) for row in syn["tensor_12x12"])
        self.assertEqual(total_cells, 144)

        # 96 cross-flying rays (48 A->B and 48 B->A)
        self.assertEqual(syn["total_cross_rays"], 96)
        self.assertEqual(syn["rays_a_to_b_count"], 48)
        self.assertEqual(syn["rays_b_to_a_count"], 48)

        # Deadlock detection and consensus metrics
        self.assertIn("cross_deadlocks", syn)
        self.assertIn("has_cross_deadlock", syn)
        self.assertIn("mean_alignment", syn)
        self.assertIn("coordination_directive", syn)

    def test_full_palace_patterns_profile(self):
        """Direction K: Exhaustive 12-Palace San Fang Si Zheng Quad-Chord Scanning."""
        chart_res = IchingKernel.full_palace_patterns_profile(
            turn_number=1,
            status_code=7,
        )
        self.assertEqual(chart_res["total_palaces_scanned"], 12)
        self.assertEqual(len(chart_res["palace_reports"]), 12)
        self.assertIn("breaking_palaces_count", chart_res)
        self.assertIn("auspicious_palaces_count", chart_res)
        self.assertIn("system_equilibrium", chart_res)

    def test_china_dst_and_aphorism_knowledge(self):
        """Direction K: Historical China DST Database (1935-1991) and Classical Aphorisms."""
        # 1988 summer: DST active
        dst_1988 = IchingKernel.china_dst_profile(1988, 6, 1)
        self.assertTrue(dst_1988["is_dst"])
        self.assertEqual(dst_1988["clock_adjustment_hours"], 1)

        # 1988 winter: DST inactive
        dst_1988_winter = IchingKernel.china_dst_profile(1988, 1, 1)
        self.assertFalse(dst_1988_winter["is_dst"])
        self.assertEqual(dst_1988_winter["clock_adjustment_hours"], 0)

        # Modern era (2026): DST abolished
        dst_2026 = IchingKernel.china_dst_profile(2026, 6, 1)
        self.assertFalse(dst_2026["is_dst"])
        self.assertEqual(dst_2026["clock_adjustment_hours"], 0)

        # Classical Aphorisms Retrieval
        aph_zifu = IchingKernel.aphorism_knowledge_profile("紫微在子")
        self.assertTrue(aph_zifu["found"])
        self.assertIn("孤君无辅", aph_zifu["quote"])

        aph_rm = IchingKernel.aphorism_knowledge_profile("日月并明")
        self.assertTrue(aph_rm["found"])
        self.assertIn("明珠出海", aph_rm["quote"])

        aph_jc = IchingKernel.aphorism_knowledge_profile("君臣庆会")
        self.assertTrue(aph_jc["found"])
        self.assertIn("君臣庆会", aph_jc["quote"])

    def test_deep_computation_and_graph_certificate(self):
        """Direction K: Formal Mathematical Certificate of 48-Ray Graph, 144-Cell Bipartite Tensor & China DST."""
        cert = IchingKernel.deep_computation_and_graph_certificate()
        self.assertEqual(cert["status"], "verified")
        self.assertTrue(cert["sihua_48_rays_conservation_verified"])
        self.assertTrue(cert["five_tigers_ten_to_twelve_duality_verified"])
        self.assertTrue(cert["bipartite_96_rays_conservation_verified"])
        self.assertTrue(cert["cross_deadlock_decidability_verified"])
        self.assertTrue(cert["full_12_palace_patterns_verified"])
        self.assertTrue(cert["china_dst_soundness_verified"])
        self.assertTrue(cert["aphorism_knowledge_coverage_verified"])

    def test_system_pathology_and_five_elements_governance(self):
        """Direction L: Five Elements System Pathology & Organ Governance Engine."""
        # 1. Syntax fracture -> Metal (肺)
        p_metal = IchingKernel.system_pathology_profile(status_code=0, error_type="SyntaxError: invalid syntax")
        self.assertEqual(p_metal["element"], "metal")
        self.assertEqual(p_metal["organ"], "肺")
        self.assertEqual(p_metal["damping_factor"], 0.25)
        self.assertEqual(p_metal["remedy_directive"], "ast_prevalidation_and_surgical_rollback")

        # 2. Concurrency deadlock -> Wood (肝)
        p_wood = IchingKernel.system_pathology_profile(status_code=49, error_type="Deadlock: lock acquisition timeout")
        self.assertEqual(p_wood["element"], "wood")
        self.assertEqual(p_wood["organ"], "肝")
        self.assertEqual(p_wood["damping_factor"], 0.40)
        self.assertEqual(p_wood["remedy_directive"], "channel_serialization_and_mutex_release")

        # 3. Resource leak / network flood -> Water (肾)
        p_water = IchingKernel.system_pathology_profile(status_code=17, error_type="MemoryLeak: memory limit exceeded")
        self.assertEqual(p_water["element"], "water")
        self.assertEqual(p_water["organ"], "肾")
        self.assertEqual(p_water["damping_factor"], 0.35)

        # 4. CPU loop flame -> Fire (心)
        p_fire = IchingKernel.system_pathology_profile(status_code=40, error_type="RateLimit: spin thrashing")
        self.assertEqual(p_fire["element"], "fire")
        self.assertEqual(p_fire["organ"], "心")
        self.assertEqual(p_fire["damping_factor"], 0.50)

        # 5. Cache pollution -> Earth (脾)
        p_earth = IchingKernel.system_pathology_profile(status_code=32, error_type="CachePollution: stale token context")
        self.assertEqual(p_earth["element"], "earth")
        self.assertEqual(p_earth["organ"], "脾")
        self.assertEqual(p_earth["damping_factor"], 0.60)

        # 6. Tai Ground state 7 -> Optimal harmony
        p_ground = IchingKernel.system_pathology_profile(status_code=7)
        self.assertFalse(p_ground["has_pathology"])
        self.assertEqual(p_ground["element"], "balanced")
        self.assertEqual(p_ground["damping_factor"], 1.0)
        self.assertEqual(p_ground["system_equilibrium"], "optimal")

    def test_partner_star_contracts_and_14_stars_completeness(self):
        """Direction L: 14 Major Stars Partner Contracts in 夫妻宫 (Multi-Agent Swarm)."""
        stars_14 = [
            ("紫微", "sovereign", "high_autonomy_macro_contract"),
            ("天机", "agile_adaptor", "agile_rapid_adaptive_sync"),
            ("太阳", "public_broadcaster", "transparent_broadcast_logging"),
            ("武曲", "strict_executor", "deterministic_strict_accounting"),
            ("天同", "cooperative_assistant", "cooperative_forgiving_assist"),
            ("廉贞", "security_sentinel", "security_sandboxed_quarantine"),
            ("天府", "reliable_steward", "conservative_snapshot_archive"),
            ("太阴", "deep_memory_manager", "persistent_deep_state_cache"),
            ("贪狼", "exploratory_pioneer", "exploratory_bounded_sandbox"),
            ("巨门", "critical_linter", "critical_audit_and_linter"),
            ("天相", "orchestration_proxy", "bilateral_proxy_arbitration"),
            ("天梁", "architectural_auditor", "architectural_guidance_veto"),
            ("七杀", "single_shot_striker", "isolated_single_shot_strike"),
            ("破军", "refactoring_innovator", "transactional_refactor_sandbox"),
        ]

        for star, expected_role, expected_mode in stars_14:
            contract = IchingKernel.partner_star_contract_profile(star)
            self.assertTrue(contract["found"], f"Star {star} must be found")
            self.assertEqual(contract["role"], expected_role)
            self.assertEqual(contract["coordination_mode"], expected_mode)
            self.assertGreater(contract["concurrency_limit"], 0)
            self.assertIn("guidance", contract)
            self.assertIn("ni_quote", contract)

        # Fallback for unknown star
        unknown = IchingKernel.partner_star_contract_profile("未知星曜")
        self.assertFalse(unknown["found"])
        self.assertEqual(unknown["role"], "general_peer")

    def test_sandbox_fengshui_and_three_essentials(self):
        """Direction L: Environmental Security across Three Essentials (门、主、灶)."""
        # All 3 intact
        s_all = IchingKernel.sandbox_fengshui_profile(True, True, True)
        self.assertEqual(s_all["fengshui_safety_level"], "auspicious_secure")
        self.assertEqual(s_all["passed_essentials_count"], 3)
        self.assertEqual(s_all["governance_action"], "full_throughput_unrestricted")

        # 1 breach (2/3)
        s_warn = IchingKernel.sandbox_fengshui_profile(True, False, True)
        self.assertEqual(s_warn["fengshui_safety_level"], "guarded_warning")
        self.assertEqual(s_warn["passed_essentials_count"], 2)
        self.assertEqual(s_warn["governance_action"], "subtask_sandbox_confinement")

        # 2 breaches (1/3)
        s_crit = IchingKernel.sandbox_fengshui_profile(False, False, True)
        self.assertEqual(s_crit["fengshui_safety_level"], "breached_critical")
        self.assertEqual(s_crit["passed_essentials_count"], 1)
        self.assertEqual(s_crit["governance_action"], "emergency_environment_quarantine_halt")

    def test_pathology_and_environmental_certificate(self):
        """Direction L: Formal Mathematical Certificate of Pathology, 14-Star Contracts, and Three Essentials."""
        cert = IchingKernel.pathology_and_environmental_certificate()
        self.assertEqual(cert["status"], "verified")
        self.assertTrue(cert["five_element_pathology_totality_verified"])
        self.assertTrue(cert["pathology_damping_monotonicity_verified"])
        self.assertTrue(cert["fourteen_partner_stars_contract_verified"])
        self.assertTrue(cert["sandbox_three_essentials_verified"])

    def test_six_channel_healing_and_prescriptions(self):
        """Direction M: Zhang Zhongjing Six Channels & Classical Prescriptions Self-Healing."""
        # 1. Taiyang (Surface)
        res_ty = IchingKernel.six_channel_healing_profile(status_code=0, error_type="PromptBoundaryError: header missing")
        self.assertEqual(res_ty["channel"], "taiyang")
        self.assertEqual(res_ty["channel_name"], "太阳")
        self.assertEqual(res_ty["damping_factor"], 0.85)
        self.assertIn("桂枝汤", res_ty["classic_formula"])

        # 2. Yangming (Interior Excess Heat)
        res_ym = IchingKernel.six_channel_healing_profile(status_code=40, error_type="CPUOverload: memory surge and loop hot")
        self.assertEqual(res_ym["channel"], "yangming")
        self.assertEqual(res_ym["channel_name"], "阳明")
        self.assertEqual(res_ym["damping_factor"], 0.50)
        self.assertIn("白虎汤", res_ym["classic_formula"])

        # 3. Shaoyang (Half-surface Half-interior)
        res_sy = IchingKernel.six_channel_healing_profile(status_code=15, error_type="AgentRPCLatency: bridge synchronization skew")
        self.assertEqual(res_sy["channel"], "shaoyang")
        self.assertEqual(res_sy["channel_name"], "少阳")
        self.assertEqual(res_sy["damping_factor"], 0.70)
        self.assertIn("小柴胡汤", res_sy["classic_formula"])

        # 4. Taiyin (Interior Deficiency)
        res_ti = IchingKernel.six_channel_healing_profile(status_code=32, error_type="WorkerStarvation: empty response queue stalled")
        self.assertEqual(res_ti["channel"], "taiyin")
        self.assertEqual(res_ti["channel_name"], "太阴")
        self.assertEqual(res_ti["damping_factor"], 0.60)
        self.assertIn("理中汤", res_ti["classic_formula"])

        # 5. Shaoyin (Deep State Failing)
        res_si = IchingKernel.six_channel_healing_profile(status_code=42, error_type="FatalPanic: heartbeat aborted")
        self.assertEqual(res_si["channel"], "shaoyin")
        self.assertEqual(res_si["channel_name"], "少阴")
        self.assertEqual(res_si["damping_factor"], 0.30)
        self.assertIn("四逆汤", res_si["classic_formula"])

        # 6. Jueyin (Conflicting Paradoxical Deadlock)
        res_jy = IchingKernel.six_channel_healing_profile(status_code=63, error_type="DeadlockConflict: spin mutex thrashing")
        self.assertEqual(res_jy["channel"], "jueyin")
        self.assertEqual(res_jy["channel_name"], "厥阴")
        self.assertEqual(res_jy["damping_factor"], 0.20)
        self.assertIn("乌梅丸", res_jy["classic_formula"])

        # 7. Ground state 7 (Nominal Balance)
        res_nom = IchingKernel.six_channel_healing_profile(status_code=7)
        self.assertFalse(res_nom["has_pathology"])
        self.assertEqual(res_nom["channel_name"], "营卫和合")
        self.assertEqual(res_nom["damping_factor"], 1.0)
        self.assertEqual(res_nom["system_equilibrium"], "optimal")

    def test_empty_palace_borrowing_and_involution(self):
        """Direction M: Empty Palace (命无正曜) Opposite Borrowing and Involution Attenuation."""
        # Test for status_code 0 (z=0): empty branches exist (1, 3)
        res_0 = IchingKernel.empty_palace_borrowing_profile(status_code=0)
        self.assertGreater(res_0["empty_palaces_count"], 0)
        self.assertTrue(res_0["opposite_involution_preserved"])
        self.assertTrue(res_0["full_coverage_restored"])

        # Empty palaces borrow from opposite with 0.75 attenuation
        for rep in res_0["reports"]:
            if rep["is_empty"]:
                self.assertEqual(rep["attenuation_factor"], 0.75)
                self.assertGreater(len(rep["borrowed_stars"]), 0)
                self.assertEqual(rep["opposite_branch"], (rep["palace_index"] + 6) % 12)
            else:
                self.assertEqual(rep["attenuation_factor"], 1.0)
                self.assertGreater(len(rep["native_stars"]), 0)

        # Test for ground state 7 (z=2, Tai): all 12 palaces have native stars
        res_7 = IchingKernel.empty_palace_borrowing_profile(status_code=7)
        self.assertEqual(res_7["empty_palaces_count"], 0)
        self.assertTrue(all(not r["is_empty"] for r in res_7["reports"]))

    def test_four_pillars_nayin_and_five_rats(self):
        """Direction M: Four Pillars, Five Rats Escape hour stem, and NaYin Bureau Lookup."""
        # 1. Five Rats Escape: Jia day (stem 0) at Zi hour (0) -> Jia-Zi (0)
        fp_jia_zi = IchingKernel.four_pillars_nayin_profile(year_stem=0, year_branch=0, day_stem=0, hour_branch=0, ming_stem=0, ming_branch=0)
        self.assertEqual(fp_jia_zi["time_stem"], 0)
        self.assertEqual(fp_jia_zi["four_pillars"]["hour"], "甲子")
        self.assertTrue(fp_jia_zi["five_rats_periodicity_ok"])

        # 2. Five Rats Escape: Yi day (stem 1) at Zi hour (0) -> Bing-Zi (2)
        fp_yi_zi = IchingKernel.four_pillars_nayin_profile(year_stem=0, year_branch=0, day_stem=1, hour_branch=0, ming_stem=1, ming_branch=0)
        self.assertEqual(fp_yi_zi["time_stem"], 2)
        self.assertEqual(fp_yi_zi["four_pillars"]["hour"], "丙子")

        # 3. NaYin Bureau: Jia-Zi (stem 0, branch 0) -> gs=1, gb=1 -> Water 2 Bureau
        self.assertEqual(fp_jia_zi["bureau_number"], 2)
        self.assertEqual(fp_jia_zi["bureau_name"], "水二局")

        # 4. NaYin Bureau: Jia-Yin (stem 0, branch 2) -> gs=1, gb=2 -> Fire 6 Bureau
        fp_jia_yin = IchingKernel.four_pillars_nayin_profile(year_stem=0, year_branch=0, day_stem=0, hour_branch=0, ming_stem=0, ming_branch=2)
        self.assertEqual(fp_jia_yin["bureau_number"], 6)
        self.assertEqual(fp_jia_yin["bureau_name"], "火六局")

    def test_six_channel_and_empty_palace_certificate(self):
        """Direction M: Formal Mathematical Certificate of Six Channels, Empty Palace Borrowing & NaYin Equipartition."""
        cert = IchingKernel.six_channel_and_empty_palace_certificate()
        self.assertEqual(cert["status"], "verified")
        self.assertTrue(cert["six_channel_transmission_order_verified"])
        self.assertTrue(cert["six_channel_damping_monotonicity_verified"])
        self.assertTrue(cert["empty_palace_opposite_involution_verified"])
        self.assertTrue(cert["no_dual_empty_palaces_verified"])
        self.assertTrue(cert["empty_palace_full_coverage_verified"])
        self.assertTrue(cert["nayin_60_jiazi_equipartition_verified"])
        self.assertTrue(cert["five_rats_escape_periodicity_verified"])
        self.assertTrue(cert["tianji_tianliang_chen_xu_invariant_verified"])
        self.assertTrue(cert["reverse_clockwise_12_palace_topology_verified"])

    def test_doujun_chronology_chain_stepping(self):
        """Direction N: Doujun (斗君) and Flowing Chronology Chain Stepping."""
        # Year branch 0 (子), birth month 1 (正月), birth hour 0 (子时)
        # doujun = (0 + 1 - 1 - 0) % 12 = 0 (子)
        d_zi = IchingKernel.doujun_chronology_profile(
            year_branch=0, birth_month=1, birth_hour=0, flowing_month=1, flowing_day=1, flowing_hour=0, ming_branch=0
        )
        self.assertEqual(d_zi["doujun_branch"], 0)
        self.assertEqual(d_zi["doujun_branch_name"], "子")
        self.assertEqual(d_zi["flowing_month_branch"], 0)
        self.assertEqual(d_zi["flowing_day_branch"], 0)
        self.assertEqual(d_zi["flowing_hour_branch"], 0)
        self.assertEqual(d_zi["resonance_state"], "direct_anchor_focus")
        self.assertEqual(d_zi["damping_factor"], 1.0)

        # Flowing day 13 -> 12-day periodicity wraps to Day 1 branch
        d_day13 = IchingKernel.doujun_chronology_profile(
            year_branch=0, birth_month=1, birth_hour=0, flowing_month=1, flowing_day=13, flowing_hour=0, ming_branch=0
        )
        self.assertEqual(d_day13["flowing_day_branch"], d_zi["flowing_day_branch"])

        # Opposite clash when flowing_hour is opposite to ming_branch
        # ming_branch = 0 (子), flowing_hour = 6 (午)
        d_clash = IchingKernel.doujun_chronology_profile(
            year_branch=0, birth_month=1, birth_hour=0, flowing_month=1, flowing_day=1, flowing_hour=6, ming_branch=0
        )
        self.assertEqual(d_clash["flowing_hour_branch"], 6)
        self.assertEqual(d_clash["resonance_state"], "opposite_clash_suipo")
        self.assertEqual(d_clash["damping_factor"], 0.50)
        self.assertEqual(d_clash["execution_cadence"], "isolated_sandbox_verification")

        # Triad harmony when flowing_hour is at trine (4 or 8)
        d_triad = IchingKernel.doujun_chronology_profile(
            year_branch=0, birth_month=1, birth_hour=0, flowing_month=1, flowing_day=1, flowing_hour=4, ming_branch=0
        )
        self.assertEqual(d_triad["resonance_state"], "triad_harmony_resonance")
        self.assertEqual(d_triad["damping_factor"], 0.90)

    def test_childhood_guard_pre_activation(self):
        """Direction N: Childhood Pre-Activation Guard (童限前置保护) before bureau activation."""
        # For Water 2 Bureau (bureau_number=2):
        # Age 1: childhood active, offset 0
        g1 = IchingKernel.childhood_guard_profile(bureau_number=2, virtual_age=1, ming_branch=2)
        self.assertTrue(g1["is_childhood_active"])
        self.assertEqual(g1["offset"], 0)
        self.assertEqual(g1["active_branch"], 2)
        self.assertEqual(g1["damping_factor"], 0.50)

        # Age 2: native bureau fully operational
        g2 = IchingKernel.childhood_guard_profile(bureau_number=2, virtual_age=2, ming_branch=2)
        self.assertFalse(g2["is_childhood_active"])
        self.assertEqual(g2["offset"], 0)
        self.assertEqual(g2["damping_factor"], 1.0)
        self.assertEqual(g2["guard_directive"], "native_bureau_fully_operational")

        # For Fire 6 Bureau (bureau_number=6):
        # Ages 1..5 are childhood with canonical offsets {1: 0, 2: -4, 3: -5, 4: -2, 5: 2}
        expected_offsets = {1: 0, 2: -4, 3: -5, 4: -2, 5: 2}
        for age, exp_off in expected_offsets.items():
            g = IchingKernel.childhood_guard_profile(bureau_number=6, virtual_age=age, ming_branch=0)
            self.assertTrue(g["is_childhood_active"])
            self.assertEqual(g["offset"], exp_off)
            self.assertEqual(g["active_branch"], (0 + exp_off) % 12)

    def test_solar_lichun_boundary_dual_track(self):
        """Direction N: Solar Lichun Boundary (立春节气交界时刻精确判定)."""
        # Member Case from regression: 2004-02-04 02:40 (Chou hour, before 19:56) -> prior solar year 2003
        pre_lichun = IchingKernel.solar_lichun_boundary_profile(
            solar_year=2004, solar_month=2, solar_day=4, solar_hour=2, solar_minute=40, lunar_year=2004
        )
        self.assertTrue(pre_lichun["is_prior_solar_year"])
        self.assertEqual(pre_lichun["effective_solar_year"], 2003)
        self.assertEqual(pre_lichun["track_skew"], -1)
        self.assertEqual(pre_lichun["reconciliation_mode"], "dual_track_quarantine_reconciled")

        # Post Lichun on the same day: 2004-02-04 22:00 (Hai hour, after 19:56) -> current year 2004
        post_lichun = IchingKernel.solar_lichun_boundary_profile(
            solar_year=2004, solar_month=2, solar_day=4, solar_hour=22, solar_minute=0, lunar_year=2004
        )
        self.assertFalse(post_lichun["is_prior_solar_year"])
        self.assertEqual(post_lichun["effective_solar_year"], 2004)
        self.assertEqual(post_lichun["track_skew"], 0)
        self.assertEqual(post_lichun["reconciliation_mode"], "unified_synchronous_track")

        # Day before Lichun: 2004-02-03 -> prior solar year
        day_before = IchingKernel.solar_lichun_boundary_profile(
            solar_year=2004, solar_month=2, solar_day=3, solar_hour=12, solar_minute=0, lunar_year=2004
        )
        self.assertTrue(day_before["is_prior_solar_year"])
        self.assertEqual(day_before["effective_solar_year"], 2003)

        # Day after Lichun: 2004-02-05 -> current solar year
        day_after = IchingKernel.solar_lichun_boundary_profile(
            solar_year=2004, solar_month=2, solar_day=5, solar_hour=12, solar_minute=0, lunar_year=2004
        )
        self.assertFalse(day_after["is_prior_solar_year"])
        self.assertEqual(day_after["effective_solar_year"], 2004)

    def test_doujun_and_solar_boundary_certificate(self):
        """Direction N: Formal Mathematical Certificate of Doujun Chronology, Childhood Guard & Solar Boundary."""
        cert = IchingKernel.doujun_and_solar_boundary_certificate()
        self.assertEqual(cert["status"], "verified")
        self.assertTrue(cert["doujun_surjective_coverage_verified"])
        self.assertTrue(cert["doujun_chronology_homomorphism_verified"])
        self.assertTrue(cert["flowing_chronology_periodicity_verified"])
        self.assertTrue(cert["childhood_guard_boundary_verified"])
        self.assertTrue(cert["solar_lichun_boundary_switch_verified"])
        self.assertTrue(cert["solar_lunar_skew_boundedness_verified"])

    def test_auxiliary_stars_pairs_and_invariants(self):
        """Direction O: Auxiliary Stars Conservation Pairs, Phase Invariants & Tianshang-Tianshi Clamping."""
        # 1. Tianxing-Tianyao constant phase difference 8 across all 12 months
        for m in range(1, 13):
            p = IchingKernel.auxiliary_stars_pairs_profile(birth_month=m, birth_day=1, ming_branch=0)
            self.assertTrue(p["phase_difference_invariant_verified"])
            self.assertEqual(p["tianxing_tianyao_phase_difference"], 8)

        # 2. Santai-Bazuo sum conservation across day changes
        p_d1 = IchingKernel.auxiliary_stars_pairs_profile(birth_month=1, birth_day=1, ming_branch=0)
        p_d15 = IchingKernel.auxiliary_stars_pairs_profile(birth_month=1, birth_day=15, ming_branch=0)
        self.assertTrue(p_d1["santai_bazuo_sum_conserved"])
        self.assertTrue(p_d15["santai_bazuo_sum_conserved"])
        self.assertEqual(p_d1["santai_bazuo_sum"], p_d15["santai_bazuo_sum"])

        # 3. Enguang-Tiangui difference conservation
        p_eg1 = IchingKernel.auxiliary_stars_pairs_profile(birth_month=1, birth_day=1, ming_branch=0, birth_hour=0)
        p_eg15 = IchingKernel.auxiliary_stars_pairs_profile(birth_month=1, birth_day=15, ming_branch=0, birth_hour=0)
        self.assertTrue(p_eg1["enguang_tiangui_diff_conserved"])
        self.assertTrue(p_eg15["enguang_tiangui_diff_conserved"])
        self.assertEqual(p_eg1["enguang_tiangui_diff"], p_eg15["enguang_tiangui_diff"])

        # 4. Tianshang & Tianshi strictly sandwich Migration Palace (迁移宫)
        for mb in range(12):
            p_clamp = IchingKernel.auxiliary_stars_pairs_profile(birth_month=1, birth_day=1, ming_branch=mb)
            self.assertTrue(p_clamp["migration_sandwiched"])
            self.assertEqual(p_clamp["migration_branch"], (mb - 6) % 12)
            self.assertEqual((p_clamp["tianshi_branch"] - p_clamp["tianshang_branch"]) % 12, 2)

    def test_city_true_solar_precision_and_dst(self):
        """Direction O: Major Cities Longitude Auto-Resolution and Historical DST Precision."""
        # 1. Beijing (116.4 E)
        bj = IchingKernel.city_true_solar_profile("北京", 2026, 6, 15, 12, 0, auto_dst=False)
        self.assertTrue(bj["city_known"])
        self.assertEqual(bj["longitude"], 116.4)
        # Offset (116.4 - 120.0) * 4 = -14.4 min
        self.assertAlmostEqual(bj["drift_minutes"], -14.4, delta=1.0)

        # 2. Shanghai (121.5 E)
        sh = IchingKernel.city_true_solar_profile("上海", 2026, 6, 15, 12, 0, auto_dst=False)
        self.assertEqual(sh["longitude"], 121.5)
        # Offset (121.5 - 120.0) * 4 = +6.0 min
        self.assertAlmostEqual(sh["drift_minutes"], 6.0, delta=1.0)

        # 3. Urumqi (87.6 E) - westernmost major city
        wq = IchingKernel.city_true_solar_profile("乌鲁木齐", 2026, 6, 15, 12, 0, auto_dst=False)
        self.assertEqual(wq["longitude"], 87.6)
        # Offset (87.6 - 120.0) * 4 = -129.6 min
        self.assertAlmostEqual(wq["drift_minutes"], -129.6, delta=2.0)

        # 4. Automatic DST Detection in 1988 Summer (Beijing)
        bj_dst = IchingKernel.city_true_solar_profile("北京", 1988, 6, 1, 12, 0, auto_dst=True)
        self.assertTrue(bj_dst["dst_active"])
        self.assertEqual(bj_dst["dst_shift_minutes"], -60)
        self.assertEqual(bj_dst["standard_clock_time"], "11:00")

    def test_auxiliary_pairs_and_city_solar_certificate(self):
        """Direction O: Formal Mathematical Certificate of Auxiliary Pairs & City Solar Precision."""
        cert = IchingKernel.auxiliary_pairs_and_city_solar_certificate()
        self.assertEqual(cert["status"], "verified")
        self.assertTrue(cert["tianxing_tianyao_constant_phase_verified"])
        self.assertTrue(cert["santai_bazuo_sum_conservation_verified"])
        self.assertTrue(cert["enguang_tiangui_difference_conservation_verified"])
        self.assertTrue(cert["tianshang_tianshi_migration_sandwiching_verified"])
        self.assertTrue(cert["major_cities_geodetic_bounds_verified"])
        self.assertTrue(cert["china_dst_automatic_shift_verified"])

    def test_changsheng_lifecycle_automaton(self):
        """Direction P: Twelve ChangSheng Process Automaton and bureau origins."""
        # 1. Bureau Origins: Water 2 & Earth 5 -> 8 (申), Wood 3 -> 11 (亥), Metal 4 -> 5 (巳), Fire 6 -> 2 (寅)
        w2 = IchingKernel.changsheng_lifecycle_profile(2, "male", 0, 8)
        self.assertEqual(w2["origin_branch"], 8)
        self.assertEqual(w2["origin_branch_name"], "申")
        self.assertEqual(w2["current_stage"], "长生")
        self.assertEqual(w2["phase_type"], "init_session")

        e5 = IchingKernel.changsheng_lifecycle_profile(5, "male", 0, 8)
        self.assertEqual(e5["origin_branch"], 8)
        self.assertEqual(e5["origin_branch_name"], "申")

        m3 = IchingKernel.changsheng_lifecycle_profile(3, "male", 0, 11)
        self.assertEqual(m3["origin_branch"], 11)
        self.assertEqual(m3["origin_branch_name"], "亥")

        g4 = IchingKernel.changsheng_lifecycle_profile(4, "male", 0, 5)
        self.assertEqual(g4["origin_branch"], 5)
        self.assertEqual(g4["origin_branch_name"], "巳")

        f6 = IchingKernel.changsheng_lifecycle_profile(6, "male", 0, 2)
        self.assertEqual(f6["origin_branch"], 2)
        self.assertEqual(f6["origin_branch_name"], "寅")

        # 2. Yang Male (stem 0, Yang) -> Clockwise progression
        # Fire 6: 寅(2)=长生, 卯(3)=沐浴, 辰(4)=冠带, 巳(5)=临官, 午(6)=帝旺
        f6_wu = IchingKernel.changsheng_lifecycle_profile(6, "male", 0, 6)
        self.assertEqual(f6_wu["current_stage"], "帝旺")
        self.assertEqual(f6_wu["phase_type"], "peak_execution_throughput")
        self.assertEqual(f6_wu["step_direction"], 1)

        # 3. Yin Male (stem 1, Yin) -> Counter-Clockwise progression
        f6_yin_male = IchingKernel.changsheng_lifecycle_profile(6, "male", 1, 1)
        self.assertEqual(f6_yin_male["step_direction"], -1)
        self.assertEqual(f6_yin_male["current_stage"], "沐浴")

        # 4. Palaces distribution is a strict 12-stage permutation
        self.assertEqual(len(set(w2["palace_stages_distribution"].values())), 12)

    def test_guchen_guasu_and_huagai_invariants(self):
        """Direction P: GuChen-GuaSu Trine Distance and HuaGai/XianChi Invariants."""
        four_horses = {2, 5, 8, 11}
        four_tombs = {1, 4, 7, 10}
        four_cardinals = {0, 3, 6, 9}

        for yb in range(12):
            res = IchingKernel.guchen_guasu_huagai_profile(yb)
            self.assertTrue(res["angular_distance_invariant_verified"])
            self.assertEqual(res["angular_distance"], 4)
            self.assertIn(res["guchen_branch"], four_horses)
            self.assertIn(res["guasu_branch"], four_tombs)
            self.assertTrue(res["huagai_in_four_tombs"])
            self.assertIn(res["huagai_branch"], four_tombs)
            self.assertTrue(res["xianchi_in_four_cardinals"])
            self.assertIn(res["xianchi_branch"], four_cardinals)

    def test_expanded_classical_patterns(self):
        """Direction P: Expanded 32+ Classical Patterns, clamping, and safety dominance."""
        # 1. Breaking pattern safety dominance
        pat_breaking = IchingKernel.expanded_classical_patterns_profile(turn_number=1, current_status=0, fatal_regression=True)
        self.assertTrue(pat_breaking["has_breaking"])
        self.assertEqual(pat_breaking["safety_level"], "caution")

        # 2. Auspicious formation with ground purity
        pat_ground = IchingKernel.expanded_classical_patterns_profile(turn_number=1, current_status=7, fatal_regression=False, ast_valid=True, verifier_passed=True)
        self.assertFalse(pat_ground["has_breaking"])
        self.assertIn(pat_ground["safety_level"], ("good", "excellent"))

        # 3. Special pattern detection: 阳梁昌禄
        pat_ylcl = IchingKernel.expanded_classical_patterns_profile(turn_number=4, current_status=7, fatal_regression=False)
        pat_names = [p["name"] for p in pat_ylcl["patterns"]]
        self.assertIn("阳梁昌禄", pat_names)

        # 4. Clamping formation: 辅弼夹命
        # turn 5: zf=(3+5)%12=8, yb=(11-5)%12=6. If ming_branch=7, prev=6, next=8 -> clamped!
        pat_fb = IchingKernel.expanded_classical_patterns_profile(turn_number=8, current_status=7)
        self.assertIsInstance(pat_fb["patterns"], list)

    def test_changsheng_and_expanded_patterns_certificate(self):
        """Direction P: Formal Mathematical Certificate for ChangSheng & 32 Patterns."""
        cert = IchingKernel.changsheng_and_expanded_patterns_certificate()
        self.assertEqual(cert["status"], "verified")
        self.assertTrue(cert["changsheng_origins_four_horses_verified"])
        self.assertTrue(cert["guchen_guasu_angular_distance_4_verified"])
        self.assertTrue(cert["huagai_four_earth_tombs_verified"])
        self.assertTrue(cert["xianchi_four_cardinals_verified"])
        self.assertTrue(cert["expanded_patterns_safety_dominance_verified"])
        self.assertTrue(cert["expanded_patterns_ground_purity_verified"])


if __name__ == "__main__":
    unittest.main()
