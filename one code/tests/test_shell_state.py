import stat
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from onecode.shell_state import load_or_create_shell_secrets


class ShellStateTests(unittest.TestCase):
    def test_auth_secrets_are_reused_for_the_same_state_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "state"
            first = load_or_create_shell_secrets(root)
            second = load_or_create_shell_secrets(root)

        self.assertEqual(first, second)

    def test_state_permissions_are_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "state"
            load_or_create_shell_secrets(root)

            self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
            self.assertEqual(
                stat.S_IMODE((root / "auth-secrets.json").stat().st_mode), 0o600
            )

    def test_corrupt_secret_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "state"
            root.mkdir(mode=0o700)
            (root / "auth-secrets.json").write_text("{}", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "invalid shell secret state"):
                load_or_create_shell_secrets(root)

    def test_concurrent_initialization_returns_one_secret_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "state"
            with ThreadPoolExecutor(max_workers=8) as pool:
                values = list(
                    pool.map(lambda _: load_or_create_shell_secrets(root), range(16))
                )

        self.assertEqual(len(set(values)), 1)


if __name__ == "__main__":
    unittest.main()
