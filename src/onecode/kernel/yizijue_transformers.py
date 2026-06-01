import json
from pathlib import Path
from typing import Any

from onecode.kernel.training_data import validate_yizijue_lm_state_sample
from onecode.kernel.yizijue_logits import YiZiJueLogitsProcessor, token_id_policy_for_basis


def build_yizijue_generation_prompt(input_text: str, *, basis: dict[str, Any]) -> str:
    if not isinstance(input_text, str) or not input_text.strip():
        raise ValueError("input_text must be a non-empty string")
    if not isinstance(basis, dict):
        raise ValueError("basis must be an object")
    basis_json = json.dumps(basis, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (
        "你是 YiZiJue-LM，一字诀受控小语言模型。\n"
        "根据用户自然语言和 YiZiJue basis 推理下一步回复。\n"
        "只输出 JSON，不输出解释。\n"
        f"用户输入: {input_text}\n"
        f"YiZiJue basis: {basis_json}\n"
        "输出格式: {\"basis\":{...},\"output_type\":\"chat_reply|clarify|action_json\","
        "\"reply\":\"...\",\"action\":null|{...}}\n"
    )


def generate_with_yizijue_logits(
    input_text: str,
    *,
    basis: dict[str, Any],
    tokenizer: Any,
    model: Any,
    max_new_tokens: int = 128,
    preferred_bias: float = 2.0,
    do_sample: bool = False,
) -> dict[str, Any]:
    if not isinstance(max_new_tokens, int) or max_new_tokens <= 0:
        raise ValueError("max_new_tokens must be a positive integer")
    prompt = build_yizijue_generation_prompt(input_text, basis=basis)
    policy = token_id_policy_for_basis(basis, tokenizer)
    processor = YiZiJueLogitsProcessor(policy, preferred_bias=preferred_bias)
    encoded = tokenizer(prompt, return_tensors="pt")
    if not isinstance(encoded, dict):
        raise ValueError("tokenizer must return a mapping")
    output_ids = model.generate(
        **encoded,
        logits_processor=build_logits_processor_list([processor]),
        max_new_tokens=max_new_tokens,
        do_sample=do_sample,
    )
    first_output = first_generated_sequence(output_ids)
    text = tokenizer.decode(first_output, skip_special_tokens=True)
    return {
        "status": "ok",
        "text": text,
        "basis": dict(basis),
        "policy": policy,
        "prompt": prompt,
    }


def run_state_corpus_predictions_with_yizijue_logits(
    gold_path: Path,
    output_path: Path,
    *,
    tokenizer: Any,
    model: Any,
    max_new_tokens: int = 128,
    preferred_bias: float = 2.0,
    do_sample: bool = False,
) -> dict[str, Any]:
    rows = read_yizijue_lm_state_rows(gold_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            result = generate_with_yizijue_logits(
                row["input"],
                basis=row["basis"],
                tokenizer=tokenizer,
                model=model,
                max_new_tokens=max_new_tokens,
                preferred_bias=preferred_bias,
                do_sample=do_sample,
            )
            handle.write(
                json.dumps(
                    {
                        "id": row["id"],
                        "prediction": result["text"],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )
    return {
        "status": "completed",
        "sample_count": len(rows),
        "gold_path": str(gold_path),
        "output_path": str(output_path),
    }


def read_yizijue_lm_state_rows(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_number}: invalid JSON") from exc
        try:
            rows.append(validate_yizijue_lm_state_sample(value))
        except ValueError as exc:
            raise ValueError(f"line {line_number}: {exc}") from exc
    return rows


def build_logits_processor_list(processors: list[Any]) -> Any:
    try:
        from transformers import LogitsProcessorList  # type: ignore
    except ImportError:
        return processors
    return LogitsProcessorList(processors)


def first_generated_sequence(output_ids: Any) -> Any:
    if hasattr(output_ids, "tolist"):
        output_ids = output_ids.tolist()
    if isinstance(output_ids, list) and output_ids and isinstance(output_ids[0], list):
        return output_ids[0]
    return output_ids


def load_transformers_causal_lm(model_name_or_path: str, **model_kwargs: Any) -> tuple[Any, Any]:
    if not isinstance(model_name_or_path, str) or not model_name_or_path.strip():
        raise ValueError("model_name_or_path must be a non-empty string")
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
    except ImportError as exc:
        raise RuntimeError("transformers is required for local YiZiJue-LM inference") from exc
    tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(model_name_or_path, trust_remote_code=True, **model_kwargs)
    return tokenizer, model
