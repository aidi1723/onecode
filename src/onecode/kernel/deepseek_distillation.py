import json
import os
import platform
import re
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Protocol

from onecode.kernel.gateway_engine import adjudicate_gateway_prediction, validate_assistant_content
from onecode.kernel.training_data import state_basis_for_lm_row, validate_yizijue_lm_state_sample


DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"


class DistillationClient(Protocol):
    def generate(self, prompt: str) -> str:
        ...


class DeepSeekChatClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = DEFAULT_DEEPSEEK_BASE_URL,
        model: str = DEFAULT_DEEPSEEK_MODEL,
        timeout_seconds: float = 60.0,
        max_tokens: int = 512,
        chat_completions_path: str = "/v1/chat/completions",
    ) -> None:
        if not api_key:
            raise ValueError("api_key must be non-empty")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self.chat_completions_path = "/" + chat_completions_path.strip("/")

    def generate(self, prompt: str) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You generate strict JSON only."},
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
                "max_tokens": self.max_tokens,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{self.chat_completions_path}",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"DeepSeek request failed: {exc.reason}") from exc
        except (TimeoutError, socket.timeout, ConnectionResetError) as exc:
            raise RuntimeError(f"DeepSeek request failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("DeepSeek response envelope was not JSON") from exc
        choices = payload.get("choices") if isinstance(payload, dict) else None
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("DeepSeek response missing choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content:
            raise RuntimeError("DeepSeek response missing message content")
        return content


BALANCED_SCENARIOS = [
    "安全工作区文件写入：用户明确给出 workspace-relative 路径和写入内容，应输出 ALLOW_ATOMIC_WRITE。",
    "安全补丁修改：用户明确给出工作区文件和替换目标，应输出 ALLOW_PATCH_WITH_SHA。",
    "pytest 验证：用户只请求运行 pytest 或测试，应输出 RUN_VERIFIER_IN_SANDBOX。",
    "模糊任务：用户说随便处理、优化一下但没有目标边界，应输出 DENY_AND_LEDGER。",
    "危险宿主机命令：用户要求宿主机执行、外部路径、rm -rf、curl bash、清理痕迹，应输出 SOVEREIGNTY_HALT。",
]


def build_deepseek_distillation_prompt(index: int, *, profile: str = "security") -> str:
    if profile not in {"security", "balanced"}:
        raise ValueError(f"unknown distillation profile: {profile}")
    scenario = ""
    if profile == "balanced":
        scenario = f"本条必须属于以下场景：{BALANCED_SCENARIOS[(index - 1) % len(BALANCED_SCENARIOS)]}\n"
    return (
        "为 YiZiJue-Controlled LM 生成一条自动化运维安全训练样本。\n"
        "场景覆盖：文件写入、补丁修改、pytest 验证、危险宿主机命令、模糊任务、提示词注入。\n"
        f"{scenario}"
        "只输出 JSON，不要 markdown，不要 <think>。\n"
        "JSON 格式："
        '{"user":"自然语言指令","prediction":{"facts":{"intent_type":"write_text|patch_text|execute_pytest|bash_execution|invalid_intent",'
        '"path_scope":"workspace_relative|outside_workspace|no_path","sandbox_state":"required|not_required|missing",'
        '"evidence_state":"required|present|failed"},"yizijue_state":"6-bit","action":"ALLOW_ATOMIC_WRITE|ALLOW_PATCH_WITH_SHA|RUN_VERIFIER_IN_SANDBOX|DENY_AND_LEDGER|SOVEREIGNTY_HALT","reason":"snake_case"}}。\n'
        f"样本序号：{index}"
    )


def generate_raw_distillation_samples(
    output_path: Path,
    *,
    client: DistillationClient,
    count: int,
    model: str = DEFAULT_DEEPSEEK_MODEL,
    api_key_label: str = "DEEPSEEK_API_KEY",
    request_interval_seconds: float = 0.0,
    profile: str = "security",
    continue_on_error: bool = False,
    error_path: Path | None = None,
) -> dict[str, Any]:
    if count <= 0:
        raise ValueError("count must be positive")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    errors = 0
    start_index = next_distillation_index(output_path)
    with output_path.open("a", encoding="utf-8") as handle:
        for offset in range(count):
            index = start_index + offset
            prompt = build_deepseek_distillation_prompt(index, profile=profile)
            try:
                text = client.generate(prompt)
                raw = extract_json_object(text)
            except (RuntimeError, ValueError) as exc:
                if not continue_on_error:
                    raise
                errors += 1
                if error_path is not None:
                    append_error_row(error_path, index=index, model=model, error=str(exc), prompt=prompt)
                continue
            row = {
                "id": f"distill-{index:06d}",
                "teacher": model,
                "raw": raw,
            }
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            written += 1
            if request_interval_seconds > 0 and offset < count - 1:
                time.sleep(request_interval_seconds)
    return {
        "status": "completed",
        "path": str(output_path),
        "sample_count": written,
        "error_count": errors,
        "teacher": model,
    }


def append_error_row(error_path: Path, *, index: int, model: str, error: str, prompt: str) -> None:
    error_path.parent.mkdir(parents=True, exist_ok=True)
    with error_path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "id": f"distill-{index:06d}",
                    "teacher": model,
                    "error": error,
                    "prompt_tail": prompt[-500:],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        )


def next_distillation_index(path: Path) -> int:
    if not path.exists():
        return 1
    max_index = 0
    pattern = re.compile(r"^distill-(\d+)$")
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        sample_id = row.get("id") if isinstance(row, dict) else None
        match = pattern.fullmatch(sample_id) if isinstance(sample_id, str) else None
        if match is not None:
            max_index = max(max_index, int(match.group(1)))
    return max_index + 1


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = strip_think_blocks(text).strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("teacher output did not contain JSON object")
        value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("teacher output JSON must be an object")
    return value


def strip_think_blocks(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)


def filter_raw_distillation_samples(
    raw_path: Path,
    *,
    accepted_path: Path,
    corrected_path: Path,
    rejected_path: Path,
    train_path: Path,
) -> dict[str, Any]:
    rows = read_raw_distillation_rows(raw_path)
    accepted_rows = []
    corrected_rows = []
    rejected_rows = []
    train_rows = []
    for row in rows:
        try:
            train_row, changed = adjudicate_raw_distillation_row(row)
        except ValueError as exc:
            rejected_rows.append({**row, "reject_reason": str(exc)})
            continue
        output_row = {
            "id": row["id"],
            "teacher": row.get("teacher"),
            "user": row["raw"]["user"],
            "raw_prediction": row["raw"].get("prediction"),
            "adjudicated_prediction": train_row["action"],
            "basis": train_row["basis"],
        }
        if changed:
            corrected_rows.append(output_row)
        else:
            accepted_rows.append(output_row)
        train_rows.append(train_row)

    write_rows(accepted_path, accepted_rows)
    write_rows(corrected_path, corrected_rows)
    write_rows(rejected_path, rejected_rows)
    write_rows(train_path, train_rows)
    return {
        "status": "completed",
        "raw_count": len(rows),
        "accepted_count": len(accepted_rows),
        "corrected_count": len(corrected_rows),
        "rejected_count": len(rejected_rows),
        "train_count": len(train_rows),
        "accepted_path": str(accepted_path),
        "corrected_path": str(corrected_path),
        "rejected_path": str(rejected_path),
        "train_path": str(train_path),
    }


def adjudicate_raw_distillation_row(row: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    raw = row.get("raw")
    if not isinstance(raw, dict):
        raise ValueError("raw must be an object")
    user = raw.get("user")
    prediction = raw.get("prediction")
    if not isinstance(user, str) or not user:
        raise ValueError("raw.user must be a non-empty string")
    if not isinstance(prediction, dict):
        raise ValueError("raw.prediction must be an object")
    prediction_text = json.dumps(prediction, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    try:
        raw_prediction = validate_assistant_content(prediction_text)
    except ValueError:
        raw_prediction = None
    adjudicated = canonicalize_adjudicated_prediction(adjudicate_gateway_prediction(user, prediction_text))
    changed = raw_prediction != adjudicated
    lm_row = {
        "id": row["id"],
        "input": user,
        "output_type": "action_json",
        "reply": "",
        "action": adjudicated,
    }
    train_row = validate_yizijue_lm_state_sample({**lm_row, "basis": state_basis_for_lm_row(lm_row)})
    return train_row, changed


def canonicalize_adjudicated_prediction(payload: dict[str, Any]) -> dict[str, Any]:
    action = payload.get("action")
    canonical_states = {
        "ALLOW_ATOMIC_WRITE": "111111",
        "ALLOW_PATCH_WITH_SHA": "111111",
        "RUN_VERIFIER_IN_SANDBOX": "010010",
        "SOVEREIGNTY_HALT": "100001",
        "DENY_AND_LEDGER": "000000",
    }
    if action not in canonical_states:
        return payload
    return validate_assistant_content(
        json.dumps(
            {**payload, "yizijue_state": canonical_states[action]},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )


def read_raw_distillation_rows(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_number}: invalid JSON") from exc
        if not isinstance(value, dict):
            raise ValueError(f"line {line_number}: row must be an object")
        rows.append(value)
    return rows


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_train_launcher(
    output_path: Path,
    *,
    system: str | None = None,
    train_data_path: str = "data/train_data.jsonl",
    model_name: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct",
    output_dir: str = "models/yizijue-controlled-1.5b-lora",
) -> dict[str, Any]:
    detected = system or platform.system()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if detected == "Darwin":
        content = mlx_train_launcher(train_data_path, model_name, output_dir)
    else:
        content = llamafactory_train_launcher(train_data_path, model_name, output_dir)
    output_path.write_text(content, encoding="utf-8")
    output_path.chmod(0o755)
    return {"status": "completed", "path": str(output_path), "system": detected}


def mlx_train_launcher(train_data_path: str, model_name: str, output_dir: str) -> str:
    return (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"TRAIN_DATA=${{TRAIN_DATA:-{train_data_path}}}\n"
        f"MODEL=${{MODEL:-{model_name}}}\n"
        f"OUTPUT_DIR=${{OUTPUT_DIR:-{output_dir}}}\n"
        "test -f \"$TRAIN_DATA\"\n"
        "python -m mlx_lm.lora \\\n"
        "  --model \"$MODEL\" \\\n"
        "  --train \\\n"
        "  --data \"$TRAIN_DATA\" \\\n"
        "  --adapter-path \"$OUTPUT_DIR\" \\\n"
        "  --iters \"${ITERS:-800}\" \\\n"
        "  --batch-size \"${BATCH_SIZE:-2}\" \\\n"
        "  --learning-rate \"${LEARNING_RATE:-1e-5}\"\n"
    )


def llamafactory_train_launcher(train_data_path: str, model_name: str, output_dir: str) -> str:
    return (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"TRAIN_DATA=${{TRAIN_DATA:-{train_data_path}}}\n"
        f"MODEL=${{MODEL:-{model_name}}}\n"
        f"OUTPUT_DIR=${{OUTPUT_DIR:-{output_dir}}}\n"
        "test -f \"$TRAIN_DATA\"\n"
        "llamafactory-cli train \\\n"
        "  --stage sft \\\n"
        "  --do_train true \\\n"
        "  --model_name_or_path \"$MODEL\" \\\n"
        "  --dataset_dir \"$(dirname \"$TRAIN_DATA\")\" \\\n"
        "  --output_dir \"$OUTPUT_DIR\" \\\n"
        "  --finetuning_type lora \\\n"
        "  --lora_target q_proj,v_proj\n"
    )


def build_client_from_env(timeout_seconds: float = 60.0, max_tokens: int = 512) -> DeepSeekChatClient:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL)
    model = os.environ.get("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL)
    chat_completions_path = os.environ.get("DEEPSEEK_CHAT_COMPLETIONS_PATH", "/v1/chat/completions")
    return DeepSeekChatClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout_seconds,
        max_tokens=max_tokens,
        chat_completions_path=chat_completions_path,
    )
