import hashlib
import os
import tempfile
import unittest
from pathlib import Path

from scripts.check_release_checksums import check_checksums


class CheckReleaseChecksumsTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
