import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts.check_release_checksums import check_checksums


class CheckReleaseChecksumsTest(unittest.TestCase):
    def test_check_checksums_accepts_matching_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = root / "logs" / "report.json"
            payload.parent.mkdir()
            payload.write_text(json.dumps({"ok": True}), encoding="utf-8")
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            checksum_file = root / "release" / "checksums.txt"
            checksum_file.parent.mkdir()
            checksum_file.write_text(f"{digest}  logs/report.json\n", encoding="utf-8")

            result = check_checksums(root=root, checksum_path=checksum_file)

        self.assertEqual(result, ["logs/report.json: OK"])

    def test_check_checksums_reports_unlisted_release_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = root / "logs" / "report.json"
            payload.parent.mkdir()
            payload.write_text("listed", encoding="utf-8")
            extra = root / "README.md"
            extra.write_text("unlisted", encoding="utf-8")
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            checksum_file = root / "release" / "checksums.txt"
            checksum_file.parent.mkdir()
            checksum_file.write_text(f"{digest}  logs/report.json\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "unlisted README.md"):
                check_checksums(root=root, checksum_path=checksum_file)

    def test_check_checksums_reports_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checksum_file = root / "release" / "checksums.txt"
            checksum_file.parent.mkdir()
            checksum_file.write_text("0" * 64 + "  logs/missing.json\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "missing logs/missing.json"):
                check_checksums(root=root, checksum_path=checksum_file)

    def test_check_checksums_reports_digest_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = root / "logs" / "report.json"
            payload.parent.mkdir()
            payload.write_text("actual", encoding="utf-8")
            checksum_file = root / "release" / "checksums.txt"
            checksum_file.parent.mkdir()
            checksum_file.write_text("0" * 64 + "  logs/report.json\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "logs/report.json"):
                check_checksums(root=root, checksum_path=checksum_file)

    def test_check_checksums_rejects_duplicate_manifest_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = root / "logs" / "report.json"
            payload.parent.mkdir()
            payload.write_text("actual", encoding="utf-8")
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            checksum_file = root / "release" / "checksums.txt"
            checksum_file.parent.mkdir()
            checksum_file.write_text(
                f"{digest}  logs/report.json\n{digest}  logs/report.json\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "duplicate checksum path: logs/report.json"):
                check_checksums(root=root, checksum_path=checksum_file)

    def test_check_checksums_rejects_directory_manifest_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            logs.mkdir()
            checksum_file = root / "release" / "checksums.txt"
            checksum_file.parent.mkdir()
            checksum_file.write_text("0" * 64 + "  logs\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "not a file logs"):
                check_checksums(root=root, checksum_path=checksum_file)

    def test_check_checksums_rejects_empty_checksum_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checksum_file = root / "release" / "checksums.txt"
            checksum_file.parent.mkdir()
            checksum_file.write_text("\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "no checksum entries"):
                check_checksums(root=root, checksum_path=checksum_file)

    def test_check_checksums_rejects_manifest_listing_itself(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checksum_file = root / "release" / "checksums.txt"
            checksum_file.parent.mkdir()
            checksum_file.write_text("0" * 64 + "  release/checksums.txt\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "checksum manifest cannot list itself"):
                check_checksums(root=root, checksum_path=checksum_file)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_check_checksums_rejects_unlisted_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = root / "README.md"
            payload.write_text("readme", encoding="utf-8")
            (root / "dangling-link").symlink_to("missing-target")
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            checksum_file = root / "release" / "checksums.txt"
            checksum_file.parent.mkdir()
            checksum_file.write_text(f"{digest}  README.md\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "symlink not allowed dangling-link"):
                check_checksums(root=root, checksum_path=checksum_file)

    def test_check_checksums_reports_malformed_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checksum_file = root / "release" / "checksums.txt"
            checksum_file.parent.mkdir()
            checksum_file.write_text("not-a-valid-checksum-line\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "malformed checksum line 1"):
                check_checksums(root=root, checksum_path=checksum_file)

    def test_check_checksums_rejects_leading_space(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = root / "README.md"
            payload.write_text("readme", encoding="utf-8")
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            checksum_file = root / "release" / "checksums.txt"
            checksum_file.parent.mkdir()
            checksum_file.write_text(f" {digest}  README.md\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "malformed checksum line 1"):
                check_checksums(root=root, checksum_path=checksum_file)

    def test_check_checksums_rejects_uppercase_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = root / "README.md"
            payload.write_text("readme", encoding="utf-8")
            digest = hashlib.sha256(payload.read_bytes()).hexdigest().upper()
            checksum_file = root / "release" / "checksums.txt"
            checksum_file.parent.mkdir()
            checksum_file.write_text(f"{digest}  README.md\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "malformed checksum line 1"):
                check_checksums(root=root, checksum_path=checksum_file)

    def test_check_checksums_rejects_paths_outside_release_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            root = parent / "release-root"
            root.mkdir()
            outside = parent / "outside.json"
            outside.write_text("outside", encoding="utf-8")
            digest = hashlib.sha256(outside.read_bytes()).hexdigest()
            checksum_file = root / "release" / "checksums.txt"
            checksum_file.parent.mkdir()
            checksum_file.write_text(f"{digest}  ../outside.json\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "escapes release root"):
                check_checksums(root=root, checksum_path=checksum_file)

    def test_check_checksums_rejects_non_canonical_relative_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = root / "README.md"
            payload.write_text("readme", encoding="utf-8")
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            checksum_file = root / "release" / "checksums.txt"
            checksum_file.parent.mkdir()
            checksum_file.write_text(f"{digest}  ./README.md\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "non-canonical path ./README.md"):
                check_checksums(root=root, checksum_path=checksum_file)

    def test_check_checksums_rejects_backslash_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = root / "docs" / "readme.md"
            payload.parent.mkdir()
            payload.write_text("readme", encoding="utf-8")
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            checksum_file = root / "release" / "checksums.txt"
            checksum_file.parent.mkdir()
            checksum_file.write_text(f"{digest}  docs\\readme.md\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, r"non-posix path docs\\readme.md"):
                check_checksums(root=root, checksum_path=checksum_file)

    def test_check_checksums_rejects_control_characters_in_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = root / "README.md"
            payload.write_text("readme", encoding="utf-8")
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            checksum_file = root / "release" / "checksums.txt"
            checksum_file.parent.mkdir()
            checksum_file.write_text(f"{digest}  README.md\t\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "path contains control characters"):
                check_checksums(root=root, checksum_path=checksum_file)


if __name__ == "__main__":
    unittest.main()
