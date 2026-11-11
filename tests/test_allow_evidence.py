import hashlib
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.allow_evidence import complete_allow_evidence
from onecode.kernel.checkpoint import sha256_text


def facts() -> dict[str, str]:
    return {
        "intent_type": "write_text",
        "path_scope": "workspace_relative",
        "sandbox_state": "not_required",
        "evidence_state": "present",
    }


class AllowEvidenceTests(unittest.TestCase):
    def test_relative_write_records_content_sha256(self):
        with tempfile.TemporaryDirectory() as root:
            result = complete_allow_evidence(
                "ALLOW_ATOMIC_WRITE",
                facts(),
                "请把 'hello' 写入 src/app.py",
                Path(root),
            )

        self.assertEqual(result["action"], "ALLOW_ATOMIC_WRITE")
        self.assertEqual(result["evidence"]["path"], "src/app.py")
        self.assertEqual(result["evidence"]["sha256"], sha256_text("hello"))
        self.assertEqual(result["evidence"]["sha256"], hashlib.sha256(b"hello").hexdigest())

    def test_colon_content_and_dot_slash_path_are_accepted(self):
        with tempfile.TemporaryDirectory() as root:
            settings = complete_allow_evidence(
                "ALLOW_ATOMIC_WRITE",
                facts(),
                '请将以下内容写入工作区中的 config/settings.json: {"debug": true}',
                Path(root),
            )
            dotted = complete_allow_evidence(
                "ALLOW_ATOMIC_WRITE",
                facts(),
                "请将工作区中的文件 ./data/test.txt 写入内容：这是测试内容。",
                Path(root),
            )

        self.assertEqual(settings["evidence"]["path"], "config/settings.json")
        self.assertEqual(settings["evidence"]["sha256"], sha256_text('{"debug": true}'))
        self.assertEqual(dotted["evidence"]["path"], "./data/test.txt")
        self.assertEqual(dotted["evidence"]["sha256"], sha256_text("这是测试内容"))
        written_as = complete_allow_evidence(
            "ALLOW_ATOMIC_WRITE",
            facts(),
            '请将工作区内的文件 data/config.json 的内容写入为 {"debug": true}',
            Path(root),
        )
        self.assertEqual(written_as["action"], "ALLOW_ATOMIC_WRITE")
        self.assertEqual(written_as["evidence"]["sha256"], sha256_text('{"debug": true}'))

    def test_absolute_path_missing_content_and_two_paths_deny(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = Path(root)
            absolute = complete_allow_evidence(
                "ALLOW_ATOMIC_WRITE",
                facts(),
                '请将以下内容写入工作区文件 /home/user/workspace/config.json：{"key": "value"}',
                workspace,
            )
            missing = complete_allow_evidence("ALLOW_ATOMIC_WRITE", facts(), "请写入 src/app.py", workspace)
            two_paths = complete_allow_evidence(
                "ALLOW_ATOMIC_WRITE",
                facts(),
                "请把 'hello' 写入 src/a.py 和 src/b.py",
                workspace,
            )

        self.assertEqual(absolute["action"], "DENY_AND_LEDGER")
        self.assertEqual(absolute["reason"], "evidence_not_extracted")
        self.assertEqual(missing["reason"], "evidence_not_extracted")
        self.assertEqual(two_paths["reason"], "evidence_not_extracted")

    def test_non_allow_action_is_unchanged(self):
        with tempfile.TemporaryDirectory() as root:
            result = complete_allow_evidence(
                "SOVEREIGNTY_HALT",
                facts(),
                "请把 'hello' 写入 src/app.py",
                Path(root),
            )

        self.assertEqual(result["action"], "SOVEREIGNTY_HALT")
        self.assertIsNone(result["evidence"])
        self.assertIsNone(result["reason"])

    def test_patch_records_block_hashes_and_denies_without_file_digests(self):
        with tempfile.TemporaryDirectory() as root:
            result = complete_allow_evidence(
                "ALLOW_PATCH_WITH_SHA",
                facts(),
                "请将工作区目录下的src/config.py中的字符串'api_key_placeholder'替换为'sk-xxxx'",
                Path(root),
            )

        self.assertEqual(result["action"], "DENY_AND_LEDGER")
        self.assertEqual(result["reason"], "file_digest_not_in_request")
        self.assertEqual(result["evidence"]["path"], "src/config.py")
        self.assertEqual(result["evidence"]["search_block_sha256"], sha256_text("api_key_placeholder"))
        self.assertEqual(result["evidence"]["replace_block_sha256"], sha256_text("sk-xxxx"))
        self.assertNotIn("pre_sha256", result["evidence"])
        self.assertNotIn("post_sha256", result["evidence"])

    def test_unique_search_block_records_file_digests_without_writing(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = Path(root)
            target = workspace / "src" / "config.py"
            target.parent.mkdir()
            original = "key = 'api_key_placeholder'\n"
            target.write_text(original, encoding="utf-8")
            before = target.read_bytes()
            result = complete_allow_evidence(
                "ALLOW_PATCH_WITH_SHA",
                facts(),
                "请将工作区目录下的src/config.py中的字符串'api_key_placeholder'替换为'sk-xxxx'",
                workspace,
            )
            after = target.read_bytes()

        self.assertEqual(result["action"], "ALLOW_PATCH_WITH_SHA")
        self.assertIsNone(result["reason"])
        self.assertEqual(result["evidence"]["pre_sha256"], sha256_text(original))
        self.assertEqual(result["evidence"]["post_sha256"], sha256_text(original.replace("api_key_placeholder", "sk-xxxx", 1)))
        self.assertEqual(before, after)

    def test_repeated_search_block_denies(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = Path(root)
            target = workspace / "src" / "config.py"
            target.parent.mkdir()
            target.write_text("api_key_placeholder\napi_key_placeholder\n", encoding="utf-8")
            result = complete_allow_evidence(
                "ALLOW_PATCH_WITH_SHA",
                facts(),
                "请将工作区目录下的src/config.py中的字符串'api_key_placeholder'替换为'sk-xxxx'",
                workspace,
            )

        self.assertEqual(result["action"], "DENY_AND_LEDGER")
        self.assertEqual(result["reason"], "search_block_not_unique")
        self.assertNotIn("pre_sha256", result["evidence"])
