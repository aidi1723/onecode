import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch


class FakeTokenizer:
    def __init__(self) -> None:
        self.encoded_fragments: list[str] = []
        self.prompts: list[str] = []

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        self.encoded_fragments.append(text)
        mapping = {
            "RUN_VERIFIER_IN_SANDBOX": [41],
            "sandbox_required": [42],
            "verifier_requires_sandbox": [43],
            "ALLOW_ATOMIC_WRITE": [51],
            "ALLOW_PATCH_WITH_SHA": [52],
        }
        return mapping.get(text, [len(text) % 97])

    def __call__(self, prompt: str, return_tensors: str | None = None) -> dict:
        self.prompts.append(prompt)
        return {"input_ids": [[1, 2, 3]], "attention_mask": [[1, 1, 1]]}

    def decode(self, token_ids, skip_special_tokens: bool = True) -> str:
        return '{"output_type":"action_json","action":{"action":"RUN_VERIFIER_IN_SANDBOX"}}'


class FakeModel:
    def __init__(self) -> None:
        self.generate_kwargs: dict | None = None

    def generate(self, **kwargs):
        self.generate_kwargs = kwargs
        return [[1, 2, 3, 4, 5]]


class YiZiJueTransformersTests(unittest.TestCase):
    def test_generate_with_yizijue_logits_passes_state_processor_to_model(self):
        from onecode.kernel.yizijue_transformers import generate_with_yizijue_logits

        tokenizer = FakeTokenizer()
        model = FakeModel()
        basis = {
            "projection": "verification_request",
            "state": "010010",
            "state_label": "kan_sandbox_verifier",
            "transition": "sandbox_required",
            "rule": "verification commands must run in a sandbox",
        }

        result = generate_with_yizijue_logits(
            "运行 pytest 验证一下",
            basis=basis,
            tokenizer=tokenizer,
            model=model,
            max_new_tokens=24,
            preferred_bias=3.5,
        )

        self.assertIn("RUN_VERIFIER_IN_SANDBOX", result["text"])
        self.assertEqual(result["basis"]["state"], "010010")
        self.assertEqual(result["policy"]["state"], "010010")
        self.assertTrue(result["policy"]["preferred_token_ids"])
        self.assertTrue(result["policy"]["forbidden_token_ids"])
        self.assertEqual(model.generate_kwargs["max_new_tokens"], 24)
        self.assertEqual(model.generate_kwargs["do_sample"], False)
        self.assertEqual(len(model.generate_kwargs["logits_processor"]), 1)
        self.assertEqual(model.generate_kwargs["logits_processor"][0].policy["state"], "010010")
        self.assertIn("010010", tokenizer.prompts[0])
        self.assertIn("verification_request", tokenizer.prompts[0])
        self.assertIn("运行 pytest 验证一下", tokenizer.prompts[0])

    def test_build_yizijue_generation_prompt_embeds_input_and_basis(self):
        from onecode.kernel.yizijue_transformers import build_yizijue_generation_prompt

        prompt = build_yizijue_generation_prompt(
            "帮我改 README",
            basis={
                "projection": "safe_patch_request",
                "state": "111111",
                "state_label": "qian_safe_patch",
                "transition": "allow_patch_with_sha",
                "rule": "workspace relative patches require sha verification",
            },
        )

        self.assertIn("帮我改 README", prompt)
        self.assertIn('"state":"111111"', prompt)
        self.assertIn('"state_label":"qian_safe_patch"', prompt)
        self.assertIn("只输出 JSON", prompt)

    def test_cli_run_yizijue_lm_transformers_once_prints_generation_result(self):
        from onecode.cli import main

        basis = {
            "projection": "verification_request",
            "state": "010010",
            "state_label": "kan_sandbox_verifier",
            "transition": "sandbox_required",
            "rule": "verification commands must run in a sandbox",
        }

        with patch(
            "onecode.cli.load_transformers_causal_lm",
            return_value=(FakeTokenizer(), FakeModel()),
        ), patch("builtins.print") as print_mock:
            exit_code = main(
                [
                    "run-yizijue-lm-transformers-once",
                    "--input",
                    "运行 pytest 验证一下",
                    "--basis-json",
                    __import__("json").dumps(basis, ensure_ascii=False),
                    "--model",
                    "/models/qwen15b",
                    "--max-new-tokens",
                    "24",
                    "--preferred-bias",
                    "3.5",
                ]
            )

        payload = __import__("json").loads(print_mock.call_args.args[0])
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["basis"]["state"], "010010")
        self.assertIn("RUN_VERIFIER_IN_SANDBOX", payload["text"])

    def test_run_state_corpus_predictions_writes_jsonl_with_model_text(self):
        from onecode.kernel.yizijue_transformers import run_state_corpus_predictions_with_yizijue_logits

        rows = [
            {
                "id": "sample-1",
                "input": "运行 pytest 验证一下",
                "basis": {
                    "projection": "verification_request",
                    "state": "010010",
                    "state_label": "kan_sandbox_verifier",
                    "transition": "sandbox_required",
                    "rule": "verification commands must run in a sandbox",
                },
                "output_type": "action_json",
                "reply": "",
                "action": {
                    "facts": {
                        "intent_type": "execute_pytest",
                        "path_scope": "no_path",
                        "sandbox_state": "required",
                        "evidence_state": "required",
                    },
                    "yizijue_state": "010010",
                    "action": "RUN_VERIFIER_IN_SANDBOX",
                    "reason": "verifier_requires_sandbox",
                },
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            gold = Path(tmp) / "gold.jsonl"
            predictions = Path(tmp) / "predictions.jsonl"
            gold.write_text(__import__("json").dumps(rows[0], ensure_ascii=False) + "\n", encoding="utf-8")
            result = run_state_corpus_predictions_with_yizijue_logits(
                gold,
                predictions,
                tokenizer=FakeTokenizer(),
                model=FakeModel(),
                max_new_tokens=24,
                preferred_bias=3.5,
            )
            written = [
                __import__("json").loads(line)
                for line in predictions.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["sample_count"], 1)
        self.assertEqual(written[0]["id"], "sample-1")
        self.assertIn("RUN_VERIFIER_IN_SANDBOX", written[0]["prediction"])

    def test_cli_run_yizijue_lm_transformers_eval_writes_predictions(self):
        from onecode.cli import main

        row = {
            "id": "sample-1",
            "input": "运行 pytest 验证一下",
            "basis": {
                "projection": "verification_request",
                "state": "010010",
                "state_label": "kan_sandbox_verifier",
                "transition": "sandbox_required",
                "rule": "verification commands must run in a sandbox",
            },
            "output_type": "action_json",
            "reply": "",
            "action": {
                "facts": {
                    "intent_type": "execute_pytest",
                    "path_scope": "no_path",
                    "sandbox_state": "required",
                    "evidence_state": "required",
                },
                "yizijue_state": "010010",
                "action": "RUN_VERIFIER_IN_SANDBOX",
                "reason": "verifier_requires_sandbox",
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            gold = Path(tmp) / "gold.jsonl"
            output = Path(tmp) / "predictions.jsonl"
            gold.write_text(__import__("json").dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
            with patch(
                "onecode.cli.load_transformers_causal_lm",
                return_value=(FakeTokenizer(), FakeModel()),
            ), patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "run-yizijue-lm-transformers-eval",
                        "--gold",
                        str(gold),
                        "--output",
                        str(output),
                        "--model",
                        "/models/qwen15b",
                        "--max-new-tokens",
                        "24",
                        "--preferred-bias",
                        "3.5",
                    ]
                )
            payload = __import__("json").loads(print_mock.call_args.args[0])

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["sample_count"], 1)


if __name__ == "__main__":
    unittest.main()
