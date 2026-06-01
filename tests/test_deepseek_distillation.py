import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class FakeDeepSeekClient:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.outputs.pop(0)


class FlakyDeepSeekClient:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary upstream timeout")
        return '{"user":"运行 pytest","prediction":{"facts":{"intent_type":"execute_pytest","path_scope":"no_path","sandbox_state":"required","evidence_state":"required"},"yizijue_state":"010010","action":"RUN_VERIFIER_IN_SANDBOX","reason":"verifier_requires_sandbox"}}'


class InspectingSecondCallClient:
    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        if self.calls == 2:
            visible_rows = self.output_path.read_text(encoding="utf-8").splitlines()
            if len(visible_rows) != 1:
                raise RuntimeError(f"expected one flushed row, saw {len(visible_rows)}")
        return '{"user":"运行 pytest","prediction":{"facts":{"intent_type":"execute_pytest","path_scope":"no_path","sandbox_state":"required","evidence_state":"required"},"yizijue_state":"010010","action":"RUN_VERIFIER_IN_SANDBOX","reason":"verifier_requires_sandbox"}}'


class DeepSeekDistillationTests(unittest.TestCase):
    def test_generate_raw_distillation_samples_writes_jsonl_without_api_key_leak(self):
        from onecode.kernel.deepseek_distillation import generate_raw_distillation_samples

        client = FakeDeepSeekClient(
            [
                '{"user":"运行 pytest 验证一下","prediction":{"facts":{"intent_type":"execute_pytest","path_scope":"no_path","sandbox_state":"required","evidence_state":"required"},"yizijue_state":"010010","action":"RUN_VERIFIER_IN_SANDBOX","reason":"verifier_requires_sandbox"}}'
            ]
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "raw.jsonl"
            result = generate_raw_distillation_samples(
                output,
                client=client,
                count=1,
                model="deepseek-v4-flash",
                api_key_label="DEEPSEEK_API_KEY",
            )
            row = json.loads(output.read_text(encoding="utf-8").splitlines()[0])

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["sample_count"], 1)
        self.assertEqual(row["teacher"], "deepseek-v4-flash")
        self.assertEqual(row["raw"]["user"], "运行 pytest 验证一下")
        self.assertNotIn("api_key", json.dumps(row, ensure_ascii=False).lower())
        self.assertIn("自动化运维", client.prompts[0])

    def test_generate_raw_distillation_samples_continues_ids_when_appending(self):
        from onecode.kernel.deepseek_distillation import generate_raw_distillation_samples

        client = FakeDeepSeekClient(
            [
                '{"user":"运行 pytest","prediction":{"facts":{"intent_type":"execute_pytest","path_scope":"no_path","sandbox_state":"required","evidence_state":"required"},"yizijue_state":"010010","action":"RUN_VERIFIER_IN_SANDBOX","reason":"verifier_requires_sandbox"}}'
            ]
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "raw.jsonl"
            output.write_text(
                json.dumps({"id": "distill-000007", "teacher": "deepseek-v4-flash", "raw": {"user": "old"}})
                + "\n",
                encoding="utf-8",
            )
            generate_raw_distillation_samples(output, client=client, count=1)
            ids = [json.loads(line)["id"] for line in output.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(ids, ["distill-000007", "distill-000008"])

    def test_generate_raw_distillation_samples_can_continue_after_error(self):
        from onecode.kernel.deepseek_distillation import generate_raw_distillation_samples

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "raw.jsonl"
            errors = Path(tmp) / "errors.jsonl"
            result = generate_raw_distillation_samples(
                output,
                client=FlakyDeepSeekClient(),
                count=2,
                continue_on_error=True,
                error_path=errors,
            )
            rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            error_rows = [json.loads(line) for line in errors.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(result["sample_count"], 1)
        self.assertEqual(result["error_count"], 1)
        self.assertEqual(rows[0]["id"], "distill-000002")
        self.assertEqual(error_rows[0]["id"], "distill-000001")

    def test_generate_raw_distillation_samples_flushes_each_row_before_next_request(self):
        from onecode.kernel.deepseek_distillation import generate_raw_distillation_samples

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "raw.jsonl"
            result = generate_raw_distillation_samples(
                output,
                client=InspectingSecondCallClient(output),
                count=2,
            )

        self.assertEqual(result["sample_count"], 2)

    def test_deepseek_chat_client_sends_max_tokens_limit(self):
        from onecode.kernel.deepseek_distillation import DeepSeekChatClient

        captured: dict[str, object] = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(
                    {"choices": [{"message": {"content": '{"ok":true}'}}]},
                    ensure_ascii=False,
                ).encode("utf-8")

        def fake_urlopen(request, timeout):
            captured["timeout"] = timeout
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        client = DeepSeekChatClient(
            api_key="test-key",
            base_url="http://example.test",
            model="deepseek-v4-flash",
            timeout_seconds=7,
            max_tokens=192,
        )
        with patch("urllib.request.urlopen", fake_urlopen):
            content = client.generate("只输出 JSON")

        self.assertEqual(content, '{"ok":true}')
        self.assertEqual(captured["timeout"], 7)
        self.assertEqual(captured["url"], "http://example.test/v1/chat/completions")
        self.assertEqual(captured["body"]["max_tokens"], 192)

    def test_deepseek_chat_client_can_use_custom_chat_completions_path(self):
        from onecode.kernel.deepseek_distillation import DeepSeekChatClient

        captured: dict[str, object] = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps({"choices": [{"message": {"content": '{"ok":true}'}}]}).encode("utf-8")

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            return FakeResponse()

        client = DeepSeekChatClient(
            api_key="test-key",
            base_url="http://example.test/api",
            chat_completions_path="/chat/completions",
        )
        with patch("urllib.request.urlopen", fake_urlopen):
            client.generate("只输出 JSON")

        self.assertEqual(captured["url"], "http://example.test/api/chat/completions")

    def test_deepseek_chat_client_wraps_socket_timeout_as_runtime_error(self):
        from onecode.kernel.deepseek_distillation import DeepSeekChatClient

        def fake_urlopen(request, timeout):
            raise TimeoutError("timed out")

        client = DeepSeekChatClient(api_key="test-key", base_url="http://example.test")
        with patch("urllib.request.urlopen", fake_urlopen):
            with self.assertRaisesRegex(RuntimeError, "DeepSeek request failed"):
                client.generate("只输出 JSON")

    def test_deepseek_chat_client_wraps_connection_reset_as_runtime_error(self):
        from onecode.kernel.deepseek_distillation import DeepSeekChatClient

        def fake_urlopen(request, timeout):
            raise ConnectionResetError("connection reset by peer")

        client = DeepSeekChatClient(api_key="test-key", base_url="http://example.test")
        with patch("urllib.request.urlopen", fake_urlopen):
            with self.assertRaisesRegex(RuntimeError, "DeepSeek request failed"):
                client.generate("只输出 JSON")

    def test_balanced_prompt_cycles_safe_and_danger_scenarios(self):
        from onecode.kernel.deepseek_distillation import build_deepseek_distillation_prompt

        prompts = [build_deepseek_distillation_prompt(index, profile="balanced") for index in range(1, 6)]

        self.assertIn("安全工作区文件写入", prompts[0])
        self.assertIn("安全补丁修改", prompts[1])
        self.assertIn("pytest", prompts[2])
        self.assertIn("模糊任务", prompts[3])
        self.assertIn("危险宿主机命令", prompts[4])

    def test_filter_raw_distillation_samples_corrects_with_onecode_gateway(self):
        from onecode.kernel.deepseek_distillation import filter_raw_distillation_samples

        raw_row = {
            "id": "distill-000001",
            "teacher": "deepseek-v4-flash",
            "raw": {
                "user": "随便处理一下这个项目",
                "prediction": {
                    "facts": {
                        "intent_type": "patch_text",
                        "path_scope": "workspace_relative",
                        "sandbox_state": "not_required",
                        "evidence_state": "required",
                    },
                    "yizijue_state": "111111",
                    "action": "ALLOW_PATCH_WITH_SHA",
                    "reason": "safe_workspace_patch",
                },
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.jsonl"
            accepted = Path(tmp) / "accepted.jsonl"
            corrected = Path(tmp) / "corrected.jsonl"
            rejected = Path(tmp) / "rejected.jsonl"
            train = Path(tmp) / "train_data.jsonl"
            raw.write_text(json.dumps(raw_row, ensure_ascii=False) + "\n", encoding="utf-8")

            result = filter_raw_distillation_samples(
                raw,
                accepted_path=accepted,
                corrected_path=corrected,
                rejected_path=rejected,
                train_path=train,
            )
            corrected_row = json.loads(corrected.read_text(encoding="utf-8").splitlines()[0])
            train_row = json.loads(train.read_text(encoding="utf-8").splitlines()[0])

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["raw_count"], 1)
        self.assertEqual(result["corrected_count"], 1)
        self.assertEqual(result["accepted_count"], 0)
        self.assertEqual(result["rejected_count"], 0)
        self.assertEqual(corrected_row["adjudicated_prediction"]["action"], "DENY_AND_LEDGER")
        self.assertEqual(train_row["basis"]["state"], "000000")
        self.assertEqual(train_row["output_type"], "action_json")

    def test_filter_raw_distillation_samples_normalizes_safe_action_states(self):
        from onecode.kernel.deepseek_distillation import filter_raw_distillation_samples

        raw_row = {
            "id": "distill-000001",
            "teacher": "deepseek-v4-flash",
            "raw": {
                "user": "请将 hello 写入工作区 docs/a.md",
                "prediction": {
                    "facts": {
                        "intent_type": "write_text",
                        "path_scope": "workspace_relative",
                        "sandbox_state": "not_required",
                        "evidence_state": "present",
                    },
                    "yizijue_state": "100100",
                    "action": "ALLOW_ATOMIC_WRITE",
                    "reason": "safe_workspace_write",
                },
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.jsonl"
            train = Path(tmp) / "train_data.jsonl"
            raw.write_text(json.dumps(raw_row, ensure_ascii=False) + "\n", encoding="utf-8")
            filter_raw_distillation_samples(
                raw,
                accepted_path=Path(tmp) / "accepted.jsonl",
                corrected_path=Path(tmp) / "corrected.jsonl",
                rejected_path=Path(tmp) / "rejected.jsonl",
                train_path=train,
            )
            train_row = json.loads(train.read_text(encoding="utf-8").splitlines()[0])

        self.assertEqual(train_row["action"]["yizijue_state"], "111111")
        self.assertEqual(train_row["basis"]["state"], "111111")

    def test_write_train_launcher_selects_mlx_on_darwin(self):
        from onecode.kernel.deepseek_distillation import write_train_launcher

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "train_launcher.sh"
            result = write_train_launcher(
                output,
                system="Darwin",
                train_data_path="data/train_data.jsonl",
                model_name="Qwen/Qwen2.5-Coder-1.5B-Instruct",
                output_dir="models/yizijue-controlled-1.5b-lora",
            )
            content = output.read_text(encoding="utf-8")

        self.assertEqual(result["status"], "completed")
        self.assertIn("mlx_lm.lora", content)
        self.assertIn("Qwen/Qwen2.5-Coder-1.5B-Instruct", content)
        self.assertIn("data/train_data.jsonl", content)


if __name__ == "__main__":
    unittest.main()
