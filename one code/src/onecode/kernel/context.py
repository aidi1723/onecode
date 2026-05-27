from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from onecode.kernel.hexagram import BUILD_ENTRY, HexagramStatusCode
from onecode.kernel.resumption import ResumeState, load_resume_state


@dataclass(frozen=True)
class OneCodeContext:
    run_id: str
    workspace_root: Path
    evidence_root: Path
    state: HexagramStatusCode
    turn_index: int
    manifest_path: Path
    http_timeout_seconds: float
    resume_from_run_id: str | None = None
    resume_state: ResumeState | None = None


def create_context(
    workspace_root: Path,
    http_timeout_seconds: float = 60,
    run_id: str | None = None,
    resume_from_run_id: str | None = None,
) -> OneCodeContext:
    if http_timeout_seconds <= 0:
        raise ValueError("http_timeout_seconds must be greater than zero")

    resolved_workspace = workspace_root.resolve()
    resolved_workspace.mkdir(parents=True, exist_ok=True)
    selected_run_id = run_id or uuid4().hex
    evidence_root = resolved_workspace / ".onecode" / "runs" / selected_run_id
    checkpoints_root = evidence_root / "checkpoints"
    checkpoints_root.mkdir(parents=True, exist_ok=True)
    resume_state = load_resume_state(resolved_workspace, resume_from_run_id) if resume_from_run_id else None

    return OneCodeContext(
        run_id=selected_run_id,
        workspace_root=resolved_workspace,
        evidence_root=evidence_root,
        state=BUILD_ENTRY,
        turn_index=0,
        manifest_path=evidence_root / "manifest.json",
        http_timeout_seconds=http_timeout_seconds,
        resume_from_run_id=resume_from_run_id,
        resume_state=resume_state,
    )
