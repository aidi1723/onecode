
import unittest
import os
import json
import tempfile
from pathlib import Path
from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.checkpoint import write_checkpoint

BASELINE_64 = {
    "0": {
        "action": "discover",
        "reason": "rule_gap_requires_discovery",
        "dispatch": "stop",
        "bandwidth": 1.0
    },
    "1": {
        "action": "checkpoint",
        "reason": "controlled_by_relation_requires_verifier",
        "dispatch": "stop",
        "bandwidth": 1.0
    },
    "2": {
        "action": "throttle",
        "reason": "earth_dams_water_flow",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "3": {
        "action": "accelerate",
        "reason": "generating_relation_accelerates_execution",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "4": {
        "action": "activate",
        "reason": "yin_excess_requires_activation",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "5": {
        "action": "recover",
        "reason": "generated_by_relation_recovers_execution",
        "dispatch": "continue",
        "bandwidth": 0.0
    },
    "6": {
        "action": "checkpoint",
        "reason": "controlled_by_relation_requires_verifier",
        "dispatch": "stop",
        "bandwidth": 1.0
    },
    "7": {
        "action": "accelerate",
        "reason": "generating_relation_accelerates_execution",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "8": {
        "action": "activate",
        "reason": "wood_breaks_inert_ground",
        "dispatch": "continue",
        "bandwidth": 0.0
    },
    "9": {
        "action": "activate",
        "reason": "yin_excess_requires_activation",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "10": {
        "action": "recover",
        "reason": "generated_by_relation_recovers_execution",
        "dispatch": "continue",
        "bandwidth": 0.0
    },
    "11": {
        "action": "checkpoint",
        "reason": "controlled_by_relation_requires_verifier",
        "dispatch": "stop",
        "bandwidth": 1.0
    },
    "12": {
        "action": "activate",
        "reason": "wood_breaks_inert_ground",
        "dispatch": "continue",
        "bandwidth": 0.0
    },
    "13": {
        "action": "accelerate",
        "reason": "generating_relation_accelerates_execution",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "14": {
        "action": "continue",
        "reason": None,
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "15": {
        "action": "checkpoint",
        "reason": "controlled_by_relation_requires_verifier",
        "dispatch": "stop",
        "bandwidth": 1.0
    },
    "16": {
        "action": "checkpoint",
        "reason": "controlled_by_relation_requires_verifier",
        "dispatch": "stop",
        "bandwidth": 1.0
    },
    "17": {
        "action": "checkpoint",
        "reason": "network_water_preserves_resume_seed",
        "dispatch": "stop",
        "bandwidth": 1.0
    },
    "18": {
        "action": "activate",
        "reason": "yin_excess_requires_activation",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "19": {
        "action": "recover",
        "reason": "generated_by_relation_recovers_execution",
        "dispatch": "continue",
        "bandwidth": 0.0
    },
    "20": {
        "action": "checkpoint",
        "reason": "controlled_by_relation_requires_verifier",
        "dispatch": "stop",
        "bandwidth": 1.0
    },
    "21": {
        "action": "halt",
        "reason": "water_quenches_fire_boundary",
        "dispatch": "stop",
        "bandwidth": 0.0
    },
    "22": {
        "action": "checkpoint",
        "reason": "network_water_preserves_resume_seed",
        "dispatch": "stop",
        "bandwidth": 1.0
    },
    "23": {
        "action": "recover",
        "reason": "generated_by_relation_recovers_execution",
        "dispatch": "continue",
        "bandwidth": 0.0
    },
    "24": {
        "action": "recover",
        "reason": "generated_by_relation_recovers_execution",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "25": {
        "action": "prune",
        "reason": "metal_prunes_wood_scope",
        "dispatch": "continue",
        "bandwidth": 0.0
    },
    "26": {
        "action": "accelerate",
        "reason": "generating_relation_accelerates_execution",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "27": {
        "action": "continue",
        "reason": None,
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "28": {
        "action": "recover",
        "reason": "generated_by_relation_recovers_execution",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "29": {
        "action": "checkpoint",
        "reason": "controlled_by_relation_requires_verifier",
        "dispatch": "stop",
        "bandwidth": 1.0
    },
    "30": {
        "action": "prune",
        "reason": "metal_prunes_wood_scope",
        "dispatch": "continue",
        "bandwidth": 0.0
    },
    "31": {
        "action": "cooldown",
        "reason": "yang_overload_cooldown",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "32": {
        "action": "checkpoint",
        "reason": "mountain_contains_local_executor_fault",
        "dispatch": "stop",
        "bandwidth": 1.0
    },
    "33": {
        "action": "checkpoint",
        "reason": "controlled_by_relation_requires_verifier",
        "dispatch": "stop",
        "bandwidth": 1.0
    },
    "34": {
        "action": "throttle",
        "reason": "earth_dams_water_flow",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "35": {
        "action": "accelerate",
        "reason": "generating_relation_accelerates_execution",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "36": {
        "action": "activate",
        "reason": "yin_excess_requires_activation",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "37": {
        "action": "recover",
        "reason": "generated_by_relation_recovers_execution",
        "dispatch": "continue",
        "bandwidth": 0.0
    },
    "38": {
        "action": "checkpoint",
        "reason": "controlled_by_relation_requires_verifier",
        "dispatch": "stop",
        "bandwidth": 1.0
    },
    "39": {
        "action": "accelerate",
        "reason": "generating_relation_accelerates_execution",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "40": {
        "action": "halt",
        "reason": "sovereignty_fire_boundary_halt",
        "dispatch": "stop",
        "bandwidth": 1.0
    },
    "41": {
        "action": "halt",
        "reason": "sovereignty_fire_boundary_halt",
        "dispatch": "stop",
        "bandwidth": 1.0
    },
    "42": {
        "action": "halt",
        "reason": "sovereignty_fire_boundary_halt",
        "dispatch": "stop",
        "bandwidth": 1.0
    },
    "43": {
        "action": "halt",
        "reason": "sovereignty_fire_suppresses_asset",
        "dispatch": "stop",
        "bandwidth": 0.0
    },
    "44": {
        "action": "halt",
        "reason": "sovereignty_fire_boundary_halt",
        "dispatch": "stop",
        "bandwidth": 1.0
    },
    "45": {
        "action": "halt",
        "reason": "sovereignty_fire_boundary_halt",
        "dispatch": "stop",
        "bandwidth": 1.0
    },
    "46": {
        "action": "halt",
        "reason": "sovereignty_fire_boundary_halt",
        "dispatch": "stop",
        "bandwidth": 1.0
    },
    "47": {
        "action": "halt",
        "reason": "sovereignty_fire_suppresses_asset",
        "dispatch": "stop",
        "bandwidth": 0.0
    },
    "48": {
        "action": "activate",
        "reason": "wood_breaks_inert_ground",
        "dispatch": "continue",
        "bandwidth": 0.0
    },
    "49": {
        "action": "continue",
        "reason": None,
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "50": {
        "action": "recover",
        "reason": "generated_by_relation_recovers_execution",
        "dispatch": "continue",
        "bandwidth": 0.0
    },
    "51": {
        "action": "checkpoint",
        "reason": "controlled_by_relation_requires_verifier",
        "dispatch": "stop",
        "bandwidth": 1.0
    },
    "52": {
        "action": "activate",
        "reason": "wood_breaks_inert_ground",
        "dispatch": "continue",
        "bandwidth": 0.0
    },
    "53": {
        "action": "accelerate",
        "reason": "generating_relation_accelerates_execution",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "54": {
        "action": "continue",
        "reason": None,
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "55": {
        "action": "cooldown",
        "reason": "yang_overload_cooldown",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "56": {
        "action": "recover",
        "reason": "generated_by_relation_recovers_execution",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "57": {
        "action": "prune",
        "reason": "metal_prunes_wood_scope",
        "dispatch": "continue",
        "bandwidth": 0.0
    },
    "58": {
        "action": "accelerate",
        "reason": "generating_relation_accelerates_execution",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "59": {
        "action": "cooldown",
        "reason": "yang_overload_cooldown",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "60": {
        "action": "recover",
        "reason": "generated_by_relation_recovers_execution",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "61": {
        "action": "cooldown",
        "reason": "yang_overload_cooldown",
        "dispatch": "continue",
        "bandwidth": 1.0
    },
    "62": {
        "action": "cooldown",
        "reason": "yang_overload_cooldown",
        "dispatch": "continue",
        "bandwidth": 0.0
    },
    "63": {
        "action": "cooldown",
        "reason": "yang_overload_cooldown",
        "dispatch": "continue",
        "bandwidth": 1.0
    }
}


WEN_WANG_SEQUENCE = [
    # Fixed 1-64 mapping for King Wen sequence
    "乾", "坤", "屯", "蒙", "需", "讼", "师", "比",
    "小畜", "履", "泰", "否", "同人", "大有", "谦", "豫",
    "随", "蛊", "临", "观", "噬嗑", "贲", "剥", "复",
    "无妄", "大畜", "颐", "大过", "坎", "离", "咸", "恒",
    "遁", "大壮", "晋", "明夷", "家人", "睽", "蹇", "解",
    "损", "益", "夬", "姤", "萃", "升", "困", "井",
    "革", "鼎", "震", "艮", "渐", "归妹", "丰", "旅",
    "巽", "兑", "涣", "节", "中孚", "小过", "既济", "未济"
]

def _control_snapshot(status_code: int) -> tuple[object, ...]:
    transition = IchingKernel.transition(status_code)
    return (
        transition.status_code,
        transition.action,
        transition.reason,
        IchingKernel.dispatch_decision(transition),
        IchingKernel.execution_bandwidth(status_code),
    )


class IchingObservabilityTests(unittest.TestCase):
    def test_pure_read_only_telemetry_baseline_64(self) -> None:
        # User requested: "用改动前的固定结果对照全部 64 个状态的 transition、dispatch 和带宽"
        for i in range(64):
            trans = IchingKernel.transition(i)
            disp = IchingKernel.dispatch_decision(trans)
            bw = IchingKernel.execution_bandwidth(i)
            base = BASELINE_64[str(i)]
            
            self.assertEqual(trans.action, base["action"])
            self.assertEqual(trans.reason, base["reason"])
            self.assertEqual(disp, base["dispatch"])
            self.assertEqual(bw, base["bandwidth"])
            
            # Ensure calculating telemetry has zero side-effects
            moving = IchingKernel.moving_lines(0, i)
            relations = IchingKernel.micro_relations(i)
            self.assertIsInstance(moving, list)
            self.assertIsInstance(relations, dict)

    def test_soft_miss_observability_does_not_change_control(self) -> None:
        reasons = ("search_miss", "path_not_found", "read_target_not_file", "list_target_not_found")
        for reason in reasons:
            with self.subTest(reason=reason):
                status_code = IchingKernel.classify_outcome("halted", reason)
                before = _control_snapshot(status_code)
                IchingKernel.moving_lines(0, status_code)
                IchingKernel.micro_relations(status_code)
                IchingKernel.cycle_phase(1)
                self.assertEqual(_control_snapshot(status_code), before)

    def test_micro_relations_qian_and_jiji(self) -> None:
        # User requested: 把比改成相邻同性、应改成对应位异性，并用乾卦（比 5、应 0）和既济（应 3）锁住
        
        # 乾卦 (Qian): 63 (111111 in binary)
        qian_relations = IchingKernel.micro_relations(63)
        self.assertEqual(qian_relations["bi"], 5, "Qian must have bi=5 (all 5 adjacent pairs are same)")
        self.assertEqual(qian_relations["ying"], 0, "Qian must have ying=0 (no opposite resonant lines)")
        
        # 既济 (Ji Ji): 21 (010101 in binary) -> Wait, Ji Ji is Yin Yang Yin Yang Yin Yang?
        # Actually bottom up: Yang(1) Yin(0) Yang(1) Yin(0) Yang(1) Yin(0) -> 010101 in binary is 21!
        jiji_relations = IchingKernel.micro_relations(21)
        self.assertEqual(jiji_relations["ying"], 3, "Ji Ji must have ying=3 (all 3 resonant pairs are opposite)")
        self.assertEqual(jiji_relations["bi"], 0, "Ji Ji must have bi=0 (no adjacent lines are the same)")

    def test_real_checkpoint_contains_second_round_moving_lines_and_manifest(self) -> None:
        # User requested: "最后读一次真实检查点，断言第二轮的 moving_lines" AND manifest
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            from onecode.kernel.context import create_context
            ctx = create_context(workspace_root=root, run_id="test-run")
            # override evidence_root since create_context might put it in .onecode
            import dataclasses
            ctx = dataclasses.replace(ctx, evidence_root=root / ".onecode", manifest_path=root / ".onecode" / "manifest.json")
            os.makedirs(ctx.evidence_root / "checkpoints")
            
            # Round 1
            path1 = write_checkpoint(
                ctx, {"hello": "world"}, next_state=0, status="completed", partial=False, reason=None,
                iching_status_code=63 # Qian
            )
            data1 = json.loads(path1.read_text())
            self.assertEqual(data1["telemetry"]["moving_lines"], [])
            
            # Read manifest
            manifest = json.loads((ctx.evidence_root / "manifest.json").read_text())
            self.assertEqual(manifest["checkpoints"][-1]["telemetry"]["moving_lines"], [])
            
            # Round 2
            path2 = write_checkpoint(
                ctx, {"hello": "world2"}, next_state=0, status="completed", partial=False, reason=None,
                iching_status_code=62 # Flipped bit 0 (from 1 to 0)
            )
            data2 = json.loads(path2.read_text())
            self.assertEqual(data2["telemetry"]["moving_lines"], [0])
            
            # Read manifest again
            manifest2 = json.loads((ctx.evidence_root / "manifest.json").read_text())
            self.assertEqual(manifest2["checkpoints"][-1]["telemetry"]["moving_lines"], [0])
            self.assertEqual(manifest2["checkpoints"][-1]["telemetry"]["cycle_phase"], "临") # Round 2 -> index 1 -> 临
            
    def test_wen_wang_sequence_hardcoded(self) -> None:
        self.assertEqual(len(WEN_WANG_SEQUENCE), 64)
        self.assertEqual(WEN_WANG_SEQUENCE[0], "乾")
        self.assertEqual(WEN_WANG_SEQUENCE[-1], "未济")
        self.assertEqual(WEN_WANG_SEQUENCE[10], "泰")
        self.assertEqual(WEN_WANG_SEQUENCE[18], "临")
        self.assertEqual(WEN_WANG_SEQUENCE[23], "复")
