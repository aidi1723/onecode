"""Integration tests verifying optional `onecode-symbolic-audit` plugin attachment."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PKG_SRC = Path(__file__).resolve().parent.parent / "src"
for candidate in (str(REPO_ROOT / "src"), str(PKG_SRC)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from onecode.kernel.hexagram import IchingKernel  # noqa: E402
from onecode.kernel.symbolic_telemetry import (  # noqa: E402
    attach_symbolic_extension,
    symbolic_extension_loaded,
)

attach_symbolic_extension(IchingKernel, force=True)


class SymbolicPluginIntegrationTests(unittest.TestCase):
    def test_symbolic_extension_is_attached_to_iching_kernel(self) -> None:
        self.assertTrue(symbolic_extension_loaded())
        self.assertTrue(hasattr(IchingKernel, "ziwei_mathematical_audit"))
        self.assertTrue(hasattr(IchingKernel, "king_wen_hexagram_record"))

    def test_recovery_status_emits_symbolic_payload_when_opted_in(self) -> None:
        from onecode.kernel.recovery_policy import recovery_status

        with patch.dict(os.environ, {"ONECODE_SYMBOLIC_TELEMETRY": "1"}):
            sym_40 = recovery_status("verifier_failure", status_code=40, attempt_count=1)
            self.assertIn("jie_shen_relief", sym_40)
            self.assertIn("twelve_deities", sym_40)
            self.assertTrue(sym_40["jie_shen_relief"]["relief_effective"])
            self.assertEqual(sym_40["jie_shen_relief"]["damping_factor"], 0.75)

            sym_47 = recovery_status("verifier_failure", status_code=47, attempt_count=2)
            self.assertEqual(sym_47["jie_shen_relief"]["damping_factor"], 0.60)

    def test_enrich_bureau_and_brightness_metadata_with_extension_and_toggle(self) -> None:
        from onecode.kernel.model_repair import _enrich_bureau_and_brightness_metadata

        sym_meta = {"iching_status_code": 39}
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {"ONECODE_SYMBOLIC_TELEMETRY": "1"}):
            p = Path(td)
            (p / "app.py").write_text("print('test')\n", encoding="utf-8")
            _enrich_bureau_and_brightness_metadata(p, sym_meta)

        self.assertIn("pattern_breaking", sym_meta)
        self.assertIn("tri_level_time_flow", sym_meta)
        self.assertIn("palace_star_duality", sym_meta)
        self.assertIn("governance_mode", sym_meta)
        self.assertEqual(sym_meta["task_bureau"], "水二局")

    def test_format_ziwei_repair_guidance_alerts_with_extension(self) -> None:
        from onecode.kernel.model_loop import _format_ziwei_repair_guidance, _recovery_defense_alerts

        failed_res = {
            "status": "failed",
            "task_status_code": 1,
            "turn_history": [{"turn": 1}],
            "turn": 2,
        }
        guidance = _format_ziwei_repair_guidance(failed_res, ["syntax error"])
        guidance_text = " ".join(guidance)
        self.assertIn("Formation broken alert", guidance_text)
        self.assertIn("Active operational domain", guidance_text)

        failed_assert = {
            "status": "failed",
            "reason": "verifier_failed",
            "verifier_results": [
                {
                    "stderr_tail": "Traceback:\n  File test_foo.py, line 10\nAssertionError: 42 != 100\n",
                    "reason": "assertion_error",
                }
            ],
            "turn_history": [
                {"turn_id": 1, "branch_name": "子", "modified_files": ["src/calculator.py"]},
            ],
        }
        assert_guidance = " ".join(_format_ziwei_repair_guidance(failed_assert, ["assertion_error"]))
        self.assertIn("Precision assertion target (水生木·精准断言)", assert_guidance)
        self.assertIn("AssertionError: 42 != 100", assert_guidance)

        with patch.dict(os.environ, {"ONECODE_SYMBOLIC_TELEMETRY": "1"}):
            alerts = _recovery_defense_alerts(
                has_verifier_fail=True,
                turn_history=[{"turn_id": 1}],
                resolved_status=40,
            )
            self.assertTrue(any("Jie Shen relief active" in a for a in alerts))

        failed_stagnation = {
            "status": "halted",
            "reason": "verifier_failed",
            "verifier_results": [
                {
                    "stderr_tail": "KeyError: 'invoice_id'\n",
                    "stdout_tail": "- [FAIL] missing age filled\n- [FAIL] bad age filled\n- [FAIL] age low/high clipped\n",
                    "reason": "verifier_failed",
                }
            ],
            "turn_history": [
                {"turn_id": 1, "branch_name": "子", "modified_files": ["app/clean.py"], "reason": "verifier_failed"},
                {"turn_id": 2, "branch_name": "丑", "modified_files": ["app/clean.py"], "reason": "verifier_failed"},
            ],
        }
        stag_text = " ".join(_format_ziwei_repair_guidance(failed_stagnation, ["verifier_failed"]))
        self.assertIn("陀罗暗滞·化权破滞", stag_text)
        self.assertIn("铃星隐煞·天相印信昭明", stag_text)
        self.assertIn("三方四正·全量断言照会", stag_text)
        self.assertIn("KeyError: 'invoice_id'", stag_text)


if __name__ == "__main__":
    unittest.main()
