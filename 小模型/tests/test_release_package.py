import hashlib
import unittest
from pathlib import Path


RELEASE_ROOT = Path("release/yizijue-lm-public")
STALE_RELEASE_MARKERS = (
    "Ran 39 tests OK",
    "Ran 43 tests OK",
    "Ran 45 tests OK",
    "sample_count: 300",
    "json_valid_rate: 1.0",
    "action_match_rate: 0.8113207547169812",
    "2026-06-04-yizijue-qwen06b-v5-final.tar.gz",
    "eb1a019765c87e99d91b689ca30bf561b63cd07bda968b3df0a58f6ca426c8d1",
)


class ReleasePackageTest(unittest.TestCase):
    def test_verify_script_checks_negative_gate_failure_reason(self):
        verify_script = Path("scripts/verify.sh").read_text(encoding="utf-8")

        self.assertIn("yizijue-review-full-report-should-fail.stderr", verify_script)
        self.assertIn("missing_prediction_count", verify_script)

    def test_verify_script_runs_release_tests_from_release_directory(self):
        verify_script = Path("scripts/verify.sh").read_text(encoding="utf-8")

        self.assertIn("(cd release/yizijue-lm-public && python3 -m unittest discover -s tests)", verify_script)

    def test_verify_script_cleans_python_cache_before_tests(self):
        verify_script = Path("scripts/verify.sh").read_text(encoding="utf-8")

        self.assertIn("-name __pycache__", verify_script)
        self.assertIn("-name '*.pyc'", verify_script)

    def test_release_tree_has_no_vcs_or_python_cache_artifacts(self):
        forbidden = []
        for path in RELEASE_ROOT.rglob("*"):
            if path.name == ".git" or path.name == "__pycache__" or path.suffix == ".pyc":
                forbidden.append(str(path))

        self.assertEqual(forbidden, [])

    def test_release_docs_do_not_reference_stale_artifacts_or_metrics(self):
        offenders = []
        for path in RELEASE_ROOT.rglob("*"):
            if not path.is_file() or path.suffix not in {".md", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8")
            for marker in STALE_RELEASE_MARKERS:
                if marker in text:
                    offenders.append(f"{path}: {marker}")

        self.assertEqual(offenders, [])

    def test_release_checksums_match_included_files(self):
        checksum_path = RELEASE_ROOT / "release" / "checksums.txt"
        failures = []
        for line in checksum_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            expected, relative_path = line.split(maxsplit=1)
            target = RELEASE_ROOT / relative_path
            if not target.exists():
                failures.append(f"missing {relative_path}")
                continue
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            if actual != expected:
                failures.append(f"{relative_path}: {actual} != {expected}")

        self.assertEqual(failures, [])

    def test_release_package_includes_self_verify_script(self):
        verify_script = RELEASE_ROOT / "scripts" / "verify_release.sh"

        self.assertTrue(verify_script.exists())
        text = verify_script.read_text(encoding="utf-8")
        self.assertIn("python3 -m unittest discover -s tests", text)
        self.assertIn("scripts/check_release_checksums.py", text)
        self.assertNotIn("..", text)


if __name__ == "__main__":
    unittest.main()
