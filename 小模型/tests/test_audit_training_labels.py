import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.audit_training_labels import audit_rows


def training_row(sample_id: str, user: str, action: str, reason: str = "ok") -> dict:
    return {
        "id": sample_id,
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": user},
            {
                "role": "assistant",
                "content": json.dumps(
                    {
                        "action": {
                            "action": action,
                            "reason": reason,
                        }
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    }


class AuditTrainingLabelsTest(unittest.TestCase):
    def test_flags_schema_out_of_contract_workspace_writes(self):
        rows = [
            training_row(
                "bad-write",
                "请将工作区下的./test/config.json文件写入以下内容：{\"key\": \"value\"}",
                "DENY_AND_LEDGER",
                "schema_out_of_contract",
            ),
            training_row(
                "safe-write",
                "请将以下内容写入工作区的config/settings.json: {\"debug\": false}",
                "ALLOW_ATOMIC_WRITE",
            ),
            training_row(
                "vague",
                "帮我优化一下这个系统，你随便处理吧",
                "DENY_AND_LEDGER",
                "schema_out_of_contract",
            ),
        ]

        report = audit_rows(rows)

        self.assertEqual(report["sample_count"], 3)
        self.assertEqual(report["suspicious_schema_write_count"], 1)
        self.assertEqual(report["suspicious_schema_write_ids"], ["bad-write"])

    def test_flags_schema_out_of_contract_write_to_relative_path(self):
        rows = [
            training_row(
                "bad-relative-write",
                "请将文件 paths/config.yaml 的内容更新为 `version: 2.0`。",
                "DENY_AND_LEDGER",
                "schema_out_of_contract",
            )
        ]

        report = audit_rows(rows)

        self.assertEqual(report["suspicious_schema_write_ids"], ["bad-relative-write"])

    def test_writes_report_from_cli(self):
        rows = [
            training_row(
                "bad-write",
                "请在workspace目录下将文件src/config.txt写入内容'version=1.0'。",
                "DENY_AND_LEDGER",
                "schema_out_of_contract",
            )
        ]

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "input.jsonl"
            output_path = tmp_path / "report.json"
            input_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )

            from scripts.audit_training_labels import main

            result = main(["--input", str(input_path), "--output", str(output_path)])

            report = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(result, 0)
        self.assertEqual(report["suspicious_schema_write_ids"], ["bad-write"])

    def test_cli_can_write_clean_jsonl_without_suspicious_rows(self):
        rows = [
            training_row(
                "bad-write",
                "请将工作区下的./test/config.json文件写入以下内容：{\"key\": \"value\"}",
                "DENY_AND_LEDGER",
                "schema_out_of_contract",
            ),
            training_row("safe-write", "请将'Hello World'写入工作区内的test.txt文件", "ALLOW_ATOMIC_WRITE"),
        ]

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "input.jsonl"
            output_path = tmp_path / "report.json"
            clean_path = tmp_path / "clean.jsonl"
            input_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )

            from scripts.audit_training_labels import main

            result = main(
                [
                    "--input",
                    str(input_path),
                    "--output",
                    str(output_path),
                    "--clean-output",
                    str(clean_path),
                ]
            )

            clean_rows = [
                json.loads(line)
                for line in clean_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(result, 0)
        self.assertEqual([row["id"] for row in clean_rows], ["safe-write"])

    def test_direct_script_execution_writes_report(self):
        row = training_row(
            "bad-write",
            "请将字符串 'Hello, world!' 写入工作区中的 ./logs/log.txt 文件",
            "DENY_AND_LEDGER",
            "schema_out_of_contract",
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "input.jsonl"
            output_path = tmp_path / "report.json"
            input_path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/audit_training_labels.py",
                    "--input",
                    str(input_path),
                    "--output",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
