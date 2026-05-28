import json
import tempfile
import unittest
from pathlib import Path

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
            self.assertEqual(ledger["iching_status_code"], expected)
            self.assertEqual(manifest["iching_status_code"], expected)
            self.assertEqual(manifest["checkpoints"][-1]["iching_status_code"], expected)
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
            self.assertEqual(manifest["iching_status_code"], expected)
            self.assertEqual(manifest["checkpoints"][-1]["iching_status_code"], expected)
            self.assertFalse((workspace / "src" / "c.py").exists())

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
            self.assertEqual(manifest["iching_status_code"], expected)
            self.assertEqual(manifest["checkpoints"][-1]["iching_status_code"], expected)


if __name__ == "__main__":
    unittest.main()
