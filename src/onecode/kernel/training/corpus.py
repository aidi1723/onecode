"""Corpus building, export, and I/O operations for training data.

This module provides functions for building training corpora, exporting to
LlamaFactory and Axolotl formats, writing training configs, and generating
coverage and readiness reports.
"""

import json
from pathlib import Path
from typing import Any

from onecode.kernel.gateway_engine import validate_assistant_content
from onecode.kernel.training.core import (
    MODEL_REPOSITORY,
    REQUIRED_ACTION_COVERAGE,
    REQUIRED_DIMENSION_COVERAGE,
    YIZIJUE_LM_SYSTEM_PROMPT,
    TrainingSample,
    validate_training_sample,
    validate_yizijue_lm_sample,
    validate_yizijue_lm_state_sample,
    write_jsonl,
    yizijue_lm_state_rows_from_lm_rows,
)
from onecode.kernel.training.evaluation import (
    evaluate_training_predictions,
    evaluate_training_quality,
    training_samples_from_rows,
)
from onecode.kernel.training.samples import (
    _dedupe_samples,
    iching_rule_lm_samples,
    natural_language_rule_lm_samples,
    yizijue_lm_base_samples,
    yizijue_lm_eval_samples,
)


def build_yizijue_lm_evalset(path: Path) -> dict[str, Any]:
    rows = yizijue_lm_eval_samples()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(validate_yizijue_lm_sample(row), ensure_ascii=False, sort_keys=True) + "\n")
    return {"status": "completed", "path": str(path), "sample_count": len(rows)}


def yizijue_lm_rows_from_training_samples(samples: list[TrainingSample]) -> list[dict[str, Any]]:
    rows = yizijue_lm_base_samples() + natural_language_rule_lm_samples() + iching_rule_lm_samples()
    for sample in samples:
        payload = validate_assistant_content(sample.to_dict()["messages"][2]["content"])
        rows.append(
            {
                "id": f"lm-action-{sample.id}",
                "input": sample.user,
                "output_type": "action_json",
                "reply": "",
                "rule_schema": sample.rule_schema,
                "action": payload,
            }
        )
    return [validate_yizijue_lm_sample(row) for row in rows]


def build_yizijue_lm_corpus(path: Path, samples: list[TrainingSample]) -> dict[str, Any]:
    rows = yizijue_lm_rows_from_training_samples(samples)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(validate_yizijue_lm_sample(row), ensure_ascii=False, sort_keys=True) + "\n")
    return {"status": "completed", "path": str(path), "sample_count": len(rows)}


def build_yizijue_lm_state_corpus(path: Path, samples: list[TrainingSample]) -> dict[str, Any]:
    rows = yizijue_lm_state_rows_from_lm_rows(yizijue_lm_rows_from_training_samples(samples))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(validate_yizijue_lm_state_sample(row), ensure_ascii=False, sort_keys=True) + "\n")
    return {"status": "completed", "path": str(path), "sample_count": len(rows)}


def sample_dicts(samples: list[TrainingSample]) -> list[dict[str, Any]]:
    return [validate_training_sample(sample.to_dict()) for sample in samples]


def export_llamafactory_bundle(output_dir: Path, samples: list[TrainingSample]) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = output_dir / "yizijue_qwen15b.json"
    info_path = output_dir / "dataset_info.json"
    rows = []
    for sample in sample_dicts(samples):
        messages = sample["messages"]
        rows.append(
            {
                "id": sample["id"],
                "rule_schema": sample["rule_schema"],
                "conversations": [
                    {"from": "system", "value": messages[0]["content"]},
                    {"from": "human", "value": messages[1]["content"]},
                    {"from": "gpt", "value": messages[2]["content"]},
                ],
            }
        )
    dataset_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    info = {
        "yizijue_qwen15b": {
            "file_name": dataset_path.name,
            "formatting": "sharegpt",
            "columns": {"messages": "conversations"},
            "tags": {
                "role_tag": "from",
                "content_tag": "value",
                "user_tag": "human",
                "assistant_tag": "gpt",
                "system_tag": "system",
            },
        }
    }
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "status": "completed",
        "format": "llamafactory",
        "dataset_path": str(dataset_path),
        "dataset_info_path": str(info_path),
        "sample_count": len(rows),
    }


def export_axolotl_jsonl(output_dir: Path, samples: list[TrainingSample]) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = output_dir / "yizijue_qwen15b.jsonl"
    config_path = output_dir / "dataset.yml"
    rows = sample_dicts(samples)
    with dataset_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(
                    {"messages": row["messages"], "rule_schema": row["rule_schema"]},
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )
    config = (
        "datasets:\n"
        f"  - path: {dataset_path.name}\n"
        "    type: chat_template\n"
        "    field_messages: messages\n"
        "chat_template: qwen_25\n"
    )
    config_path.write_text(config, encoding="utf-8")
    return {
        "status": "completed",
        "format": "axolotl",
        "dataset_path": str(dataset_path),
        "config_path": str(config_path),
        "sample_count": len(rows),
    }


def distilled_state_rows_to_qwen_messages(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    messages = []
    for row in rows:
        sample = validate_yizijue_lm_state_sample(row)
        if sample["output_type"] == "action_json":
            assistant_content = json.dumps(
                {"output_type": "action_json", "action": sample["action"], "basis": sample["basis"]},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        else:
            assistant_content = json.dumps(
                {
                    "output_type": sample["output_type"],
                    "reply": sample["reply"],
                    "basis": sample["basis"],
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        messages.append(
            {
                "id": sample["id"],
                "messages": [
                    {"role": "system", "content": YIZIJUE_LM_SYSTEM_PROMPT},
                    {"role": "user", "content": sample["input"]},
                    {"role": "assistant", "content": assistant_content},
                ],
            }
        )
    return messages


def llamafactory_config(train_path: Path, eval_path: Path) -> str:
    return (
        f"model_name_or_path: {MODEL_REPOSITORY}\n"
        "stage: sft\n"
        "do_train: true\n"
        "finetuning_type: lora\n"
        "adapter: lora\n"
        "lora_target: all\n"
        "template: qwen\n"
        "dataset: yizijue_qwen15b_train\n"
        f"dataset_dir: {train_path.parent.as_posix()}\n"
        "cutoff_len: 4096\n"
        "learning_rate: 2.0e-4\n"
        "num_train_epochs: 3.0\n"
        "per_device_train_batch_size: 2\n"
        "gradient_accumulation_steps: 8\n"
        "lr_scheduler_type: cosine\n"
        "warmup_ratio: 0.03\n"
        "bf16: true\n"
        "logging_steps: 5\n"
        "save_steps: 50\n"
        "eval_steps: 50\n"
        "evaluation_strategy: steps\n"
        f"val_file: {eval_path.as_posix()}\n"
        "output_dir: saves/yizijue-qwen15b-lora\n"
    )


def axolotl_config(train_path: Path, eval_path: Path) -> str:
    return (
        f"base_model: {MODEL_REPOSITORY}\n"
        "model_type: AutoModelForCausalLM\n"
        "tokenizer_type: AutoTokenizer\n"
        "is_qwen_derived_model: true\n"
        "chat_template: qwen_25\n"
        "sequence_len: 4096\n"
        "sample_packing: true\n"
        "pad_to_sequence_len: true\n"
        "adapter: lora\n"
        "lora_r: 16\n"
        "lora_alpha: 32\n"
        "lora_dropout: 0.05\n"
        "lora_target_linear: true\n"
        "datasets:\n"
        f"  - path: {train_path.as_posix()}\n"
        "    type: chat_template\n"
        "    field_messages: messages\n"
        "test_datasets:\n"
        f"  - path: {eval_path.as_posix()}\n"
        "    type: chat_template\n"
        "    field_messages: messages\n"
        "output_dir: ./outputs/yizijue-qwen15b-lora\n"
        "learning_rate: 0.0002\n"
        "num_epochs: 3\n"
        "micro_batch_size: 2\n"
        "gradient_accumulation_steps: 8\n"
        "optimizer: adamw_torch\n"
        "lr_scheduler: cosine\n"
        "bf16: auto\n"
    )


def write_training_configs(output_dir: Path, corpus_dir: Path) -> dict[str, Any]:
    train_path = corpus_dir / "train.jsonl"
    eval_path = corpus_dir / "eval.jsonl"
    if not train_path.exists():
        raise ValueError(f"missing training corpus file: {train_path}")
    if not eval_path.exists():
        raise ValueError(f"missing eval corpus file: {eval_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    llamafactory_path = output_dir / "llamafactory_qwen15b_lora.yaml"
    axolotl_path = output_dir / "axolotl_qwen15b_lora.yml"
    llamafactory_path.write_text(llamafactory_config(train_path, eval_path), encoding="utf-8")
    axolotl_path.write_text(axolotl_config(train_path, eval_path), encoding="utf-8")
    return {
        "status": "completed",
        "model": MODEL_REPOSITORY,
        "llamafactory_config_path": str(llamafactory_path),
        "axolotl_config_path": str(axolotl_path),
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_number}: invalid JSON") from exc
        try:
            rows.append(validate_training_sample(value))
        except ValueError as exc:
            raise ValueError(f"line {line_number}: {exc}") from exc
    return rows


def validate_jsonl(path: Path) -> dict[str, Any]:
    rows = read_jsonl(path)
    action_counts: dict[str, int] = {}
    state_counts: dict[str, int] = {}
    ids = set()
    for line_number, row in enumerate(rows, start=1):
        sample_id = row["id"]
        if sample_id in ids:
            raise ValueError(f"line {line_number}: duplicate sample id: {sample_id}")
        ids.add(sample_id)
        payload = validate_assistant_content(row["messages"][2]["content"])
        action = payload["action"]
        state = payload["yizijue_state"]
        action_counts[action] = action_counts.get(action, 0) + 1
        state_counts[state] = state_counts.get(state, 0) + 1
    return {
        "status": "ok",
        "path": str(path),
        "sample_count": len(rows),
        "action_counts": dict(sorted(action_counts.items())),
        "state_counts": dict(sorted(state_counts.items())),
    }


def increment_dimension(dimensions: dict[str, dict[str, int]], dimension: str, value: str) -> None:
    dimensions[dimension][value] = dimensions[dimension].get(value, 0) + 1


def generate_coverage_report(samples: list[TrainingSample]) -> dict[str, Any]:
    dimensions: dict[str, dict[str, int]] = {
        "intent_type": {},
        "path_scope": {},
        "sandbox_state": {},
        "evidence_state": {},
        "action": {},
        "yizijue_state": {},
    }
    invalid_sample_count = 0
    for sample in samples:
        try:
            payload = validate_assistant_content(sample.to_dict()["messages"][2]["content"])
        except ValueError:
            invalid_sample_count += 1
            continue
        facts = payload["facts"]
        increment_dimension(dimensions, "intent_type", facts["intent_type"])
        increment_dimension(dimensions, "path_scope", facts["path_scope"])
        increment_dimension(dimensions, "sandbox_state", facts["sandbox_state"])
        increment_dimension(dimensions, "evidence_state", facts["evidence_state"])
        increment_dimension(dimensions, "action", payload["action"])
        increment_dimension(dimensions, "yizijue_state", payload["yizijue_state"])

    missing: dict[str, list[str]] = {}
    for dimension, required_values in REQUIRED_DIMENSION_COVERAGE.items():
        present_values = set(dimensions[dimension])
        absent = sorted(required_values - present_values)
        if absent:
            missing[dimension] = absent

    return {
        "status": "incomplete" if missing or invalid_sample_count else "ok",
        "sample_count": len(samples),
        "invalid_sample_count": invalid_sample_count,
        "dimensions": {
            dimension: dict(sorted(counts.items()))
            for dimension, counts in dimensions.items()
        },
        "missing_required_dimensions": missing,
    }


def rank_samples(samples: list[TrainingSample]) -> list[TrainingSample]:
    return sorted(samples, key=lambda sample: (sum(ord(char) for char in sample.id) % 997, sample.id))


def sample_dimension_value(sample: TrainingSample, dimension: str) -> str:
    payload = validate_assistant_content(sample.to_dict()["messages"][2]["content"])
    if dimension in {"intent_type", "path_scope", "sandbox_state", "evidence_state"}:
        return payload["facts"][dimension]
    return payload[dimension]


def eval_ids_cover_dimension(samples: list[TrainingSample], selected_ids: set[str], dimension: str, value: str) -> bool:
    return any(sample.id in selected_ids and sample_dimension_value(sample, dimension) == value for sample in samples)


def first_sample_covering_dimension(
    samples: list[TrainingSample],
    selected_ids: set[str],
    dimension: str,
    value: str,
) -> TrainingSample | None:
    for sample in rank_samples(samples):
        if sample.id not in selected_ids and sample_dimension_value(sample, dimension) == value:
            return sample
    return None


def deterministic_eval_ids(samples: list[TrainingSample], eval_count: int) -> set[str]:
    by_action: dict[str, list[TrainingSample]] = {}
    for sample in samples:
        payload = validate_assistant_content(sample.to_dict()["messages"][2]["content"])
        action = payload["action"]
        by_action.setdefault(action, []).append(sample)

    selected: list[TrainingSample] = []
    for action in sorted(REQUIRED_ACTION_COVERAGE):
        candidates = by_action.get(action, [])
        if candidates:
            selected.append(rank_samples(candidates)[0])

    selected_ids = {sample.id for sample in selected}
    for dimension, required_values in sorted(REQUIRED_DIMENSION_COVERAGE.items()):
        for required_value in sorted(required_values):
            if eval_ids_cover_dimension(samples, selected_ids, dimension, required_value):
                continue
            candidate = first_sample_covering_dimension(samples, selected_ids, dimension, required_value)
            if candidate is not None:
                selected_ids.add(candidate.id)

    remaining = [sample for sample in rank_samples(samples) if sample.id not in selected_ids]
    for sample in remaining:
        if len(selected_ids) >= eval_count:
            break
        selected_ids.add(sample.id)
    return selected_ids


def build_training_corpus(
    output_dir: Path,
    samples: list[TrainingSample],
    eval_ratio: float = 0.1,
) -> dict[str, Any]:
    if not 0.0 < eval_ratio < 0.5:
        raise ValueError("eval_ratio must be greater than 0 and less than 0.5")
    deduped = _dedupe_samples(samples)
    quality = evaluate_training_quality(deduped)
    if quality["status"] != "ok":
        raise ValueError("training corpus quality gate failed: " + "; ".join(quality["failures"]))

    eval_count = max(1, int(len(deduped) * eval_ratio))
    eval_ids = deterministic_eval_ids(deduped, eval_count)
    train_samples = [sample for sample in deduped if sample.id not in eval_ids]
    eval_samples = [sample for sample in deduped if sample.id in eval_ids]

    output_dir.mkdir(parents=True, exist_ok=True)
    train_path = output_dir / "train.jsonl"
    eval_path = output_dir / "eval.jsonl"
    report_path = output_dir / "quality_report.json"
    write_jsonl(train_path, train_samples)
    write_jsonl(eval_path, eval_samples)
    report = {
        **quality,
        "train_count": len(train_samples),
        "eval_count": len(eval_samples),
        "train_path": str(train_path),
        "eval_path": str(eval_path),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "status": "completed",
        "output_dir": str(output_dir),
        "train_path": str(train_path),
        "eval_path": str(eval_path),
        "quality_report_path": str(report_path),
        "train_count": len(train_samples),
        "eval_count": len(eval_samples),
    }


def generate_pretraining_readiness_report(corpus_dir: Path, configs_dir: Path) -> dict[str, Any]:
    train_path = corpus_dir / "train.jsonl"
    eval_path = corpus_dir / "eval.jsonl"
    quality_path = corpus_dir / "quality_report.json"
    llamafactory_config_path = configs_dir / "llamafactory_qwen15b_lora.yaml"
    axolotl_config_path = configs_dir / "axolotl_qwen15b_lora.yml"

    train_samples = training_samples_from_rows(read_jsonl(train_path))
    eval_samples = training_samples_from_rows(read_jsonl(eval_path))
    all_samples = train_samples + eval_samples

    quality = evaluate_training_quality(all_samples)
    train_coverage = generate_coverage_report(train_samples)
    eval_coverage = generate_coverage_report(eval_samples)
    gold_predictions = {
        sample.id: sample.to_dict()["messages"][2]["content"]
        for sample in eval_samples
    }
    prediction_gate = evaluate_training_predictions(eval_samples, gold_predictions)
    config_status = {
        "status": "ok" if llamafactory_config_path.exists() and axolotl_config_path.exists() else "missing",
        "llamafactory_config_path": str(llamafactory_config_path),
        "axolotl_config_path": str(axolotl_config_path),
    }
    quality_artifact = {
        "status": "ok" if quality_path.exists() else "missing",
        "path": str(quality_path),
    }

    gate_statuses = [
        quality["status"],
        train_coverage["status"],
        eval_coverage["status"],
        prediction_gate["status"],
        config_status["status"],
        quality_artifact["status"],
    ]
    ready = all(status == "ok" for status in gate_statuses)
    return {
        "status": "ready" if ready else "blocked",
        "decision": "allowed_to_start_cleaning" if ready else "do_not_start_cleaning",
        "model": MODEL_REPOSITORY,
        "corpus_dir": str(corpus_dir),
        "configs_dir": str(configs_dir),
        "quality": quality,
        "quality_artifact": quality_artifact,
        "train_coverage": train_coverage,
        "eval_coverage": eval_coverage,
        "prediction_gate": prediction_gate,
        "config_status": config_status,
    }
