import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from processor import MaterialProcessor


class MaterialProcessorTest(unittest.TestCase):
    def test_weight_calculation(self):
        proc = MaterialProcessor()

        self.assertEqual(proc.calculate_profile_weight(1.5, 2.7, 10), 40.5)

    def test_infinite_loop_trap(self):
        proc = MaterialProcessor()
        start_time = time.time()
        result = proc.calculate_profile_weight(1, 1, 1)

        if result is None:
            while True:
                if time.time() - start_time > 2:
                    raise TimeoutError("Triggered Exit Code 124")

    def test_supplier_import_blocks_path_traversal(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "supplier"
            workspace.mkdir()
            (workspace / "ok.csv").write_text("sku,length,density,count\nA,1.5,2.7,10\n", encoding="utf-8")

            proc = MaterialProcessor(workspace=str(workspace))

            self.assertIn("sku,length", proc.import_supplier_csv("ok.csv"))
            with self.assertRaises(FileNotFoundError):
                proc.import_supplier_csv("../../etc/passwd")


if __name__ == "__main__":
    unittest.main()
