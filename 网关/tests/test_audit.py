import unittest
import json
from tempfile import TemporaryDirectory
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from agent_skill_dictionary.audit import (
    append_audit_record,
    build_evidence_record,
    read_audit_log,
    verify_audit_chain,
)


class AuditTest(unittest.TestCase):
    def test_build_evidence_record_hashes_stdout_and_stderr(self):
        record = build_evidence_record(
            command="python3 -m unittest",
            exit_code=0,
            stdout="OK\n",
            stderr="",
        )

        self.assertEqual(record["command"], "python3 -m unittest")
        self.assertEqual(record["exit_code"], 0)
        self.assertEqual(len(record["stdout_digest"]), 64)
        self.assertEqual(len(record["stderr_digest"]), 64)
        self.assertEqual(len(record["sha256"]), 64)
        self.assertIn("timestamp", record)

    def test_evidence_record_changes_when_output_changes(self):
        first = build_evidence_record("cmd", 0, "OK\n", "")
        second = build_evidence_record("cmd", 0, "FAIL\n", "")
        self.assertNotEqual(first["sha256"], second["sha256"])

    def test_append_audit_record_writes_jsonl_with_hash_chain(self):
        with TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log.jsonl"
            first = build_evidence_record("cmd1", 0, "OK\n", "")
            second = build_evidence_record("cmd2", 1, "", "FAIL\n")

            first_written = append_audit_record(log_path, first)
            second_written = append_audit_record(log_path, second)
            records = read_audit_log(log_path)

            self.assertEqual(len(records), 2)
            self.assertIsNone(first_written["previous_sha256"])
            self.assertEqual(second_written["previous_sha256"], first_written["sha256"])
            self.assertEqual(records[1]["sha256"], second_written["sha256"])

    def test_verify_audit_chain_accepts_valid_log(self):
        with TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log.jsonl"
            append_audit_record(log_path, build_evidence_record("cmd1", 0, "OK\n", ""))
            append_audit_record(log_path, build_evidence_record("cmd2", 0, "OK\n", ""))

            result = verify_audit_chain(log_path)

            self.assertTrue(result["valid"])
            self.assertEqual(result["count"], 2)
            self.assertEqual(result["errors"], [])

    def test_verify_audit_chain_rejects_tampered_log(self):
        with TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log.jsonl"
            append_audit_record(log_path, build_evidence_record("cmd1", 0, "OK\n", ""))
            records = read_audit_log(log_path)
            records[0]["exit_code"] = 9
            log_path.write_text(json.dumps(records[0], ensure_ascii=False) + "\n", encoding="utf-8")

            result = verify_audit_chain(log_path)

            self.assertFalse(result["valid"])
            self.assertEqual(result["count"], 1)
            self.assertEqual(result["errors"][0]["reason"], "sha256_mismatch")

    def test_append_audit_record_preserves_chain_under_concurrent_writes(self):
        with TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log.jsonl"

            def append(index):
                return append_audit_record(
                    log_path,
                    build_evidence_record(f"cmd{index}", 0, f"OK {index}\n", ""),
                )

            with ThreadPoolExecutor(max_workers=8) as executor:
                list(executor.map(append, range(40)))

            result = verify_audit_chain(log_path)

        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["count"], 40)


if __name__ == "__main__":
    unittest.main()
