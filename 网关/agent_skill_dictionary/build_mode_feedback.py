from __future__ import annotations

import json
from typing import Iterator

from .build_mode_types import (
    FeedbackEvidence,
    HEX_CORRECT,
    HEX_CREATE,
    HEX_HALT,
    HEX_INSPECT,
    SandboxEvidence,
    ViolationEvidence,
    dto_to_dict,
)


def rewrite_to_soft_payload(raw_error: SandboxEvidence | ViolationEvidence) -> dict[str, object]:
    feedback = _feedback_from_error(raw_error)
    return {
        "http_status": 200,
        "stderr": "",
        "response_mode": "soft_rewrite",
        "feedback": dto_to_dict(feedback),
        "message": _message_text(feedback),
    }


def rewrite_empty_patch_retry_payload(raw_error: ViolationEvidence) -> dict[str, object]:
    feedback = FeedbackEvidence(
        status="needs_retry",
        source_hexagram=HEX_CORRECT,
        next_hexagram=HEX_CREATE,
        summary=(
            "apply_patch was empty and cannot satisfy the Build Mode evidence gate. "
            "Retry by calling write_file with workspace-relative path and full file content."
        ),
    )
    return {
        "http_status": 200,
        "stderr": "",
        "response_mode": "soft_retry",
        "feedback": dto_to_dict(feedback),
        "message": _message_text(feedback),
        "violation": dto_to_dict(raw_error),
    }


def build_sse_soft_chunks(raw_error: SandboxEvidence | ViolationEvidence) -> Iterator[str]:
    payload = rewrite_to_soft_payload(raw_error)
    chunk = {
        "choices": [
            {
                "delta": {"content": payload["message"]},
                "finish_reason": None,
                "index": 0,
            }
        ],
        "object": "chat.completion.chunk",
    }
    yield "data: " + json.dumps(chunk, ensure_ascii=False) + "\n\n"
    done = {
        "choices": [{"delta": {}, "finish_reason": "stop", "index": 0}],
        "object": "chat.completion.chunk",
    }
    yield "data: " + json.dumps(done, ensure_ascii=False) + "\n\n"
    yield "data: [DONE]\n\n"


def _feedback_from_error(raw_error: SandboxEvidence | ViolationEvidence) -> FeedbackEvidence:
    if isinstance(raw_error, ViolationEvidence):
        return FeedbackEvidence(
            status="blocked",
            source_hexagram=HEX_HALT,
            next_hexagram=HEX_INSPECT,
            summary=f"Action blocked by Build Mode: {raw_error.reason}. Use scoped workspace actions only.",
        )
    return FeedbackEvidence(
        status="needs_fix",
        source_hexagram=HEX_CORRECT,
        next_hexagram=HEX_INSPECT,
        summary=f"Sandbox verification failed with exit_code={raw_error.exit_code}, status={raw_error.pytest_status}.",
    )


def _message_text(feedback: FeedbackEvidence) -> str:
    return (
        "Kernel Notice: Build Mode converted a blocked or failed action into structured feedback. "
        f"Status={feedback.status}; next_state={feedback.next_hexagram}; summary={feedback.summary}"
    )
