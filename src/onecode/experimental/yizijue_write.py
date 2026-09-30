"""Write a workspace file only for a qian allow decision with matching evidence."""

from pathlib import Path
from typing import Callable

from onecode.experimental.yizijue_ledger import NON_EXECUTION_REASONS, execution_view
from onecode.kernel.checkpoint import sha256_text
from onecode.kernel.project_gateway import gateway_disagreement
from onecode.kernel.path_guard import PathGuard, PathGuardError

PINNED_WRITE_STATE = "111111"
WRITE_ACTIONS = {"ALLOW_ATOMIC_WRITE", "ALLOW_PATCH_WITH_SHA"}
WITHHELD_REASONS = NON_EXECUTION_REASONS
Writer = Callable[[Path, str, str], dict]


def write_block_reason(entry: dict) -> str | None:
    entry = execution_view(entry)
    if entry.get("executed") is True:
        return "already_executed"
    if entry.get("reason") in WITHHELD_REASONS:
        return "withheld"
    if entry.get("yizijue_state") != PINNED_WRITE_STATE or entry.get("action") not in WRITE_ACTIONS:
        return "not_write"
    if entry.get("cycle") not in {None, "stop"}:
        return "not_write"
    evidence = entry.get("evidence")
    if not isinstance(evidence, dict) or not isinstance(evidence.get("path"), str) or evidence["path"] == "":
        return "evidence_missing"
    if ".." in Path(evidence["path"]).parts or evidence["path"].startswith(("/", "\\")):
        return "path_rejected"
    digest_field = "sha256" if entry["action"] == "ALLOW_ATOMIC_WRITE" else "post_sha256"
    if not isinstance(evidence.get(digest_field), str) or evidence[digest_field] == "":
        return "evidence_missing"
    return gateway_disagreement(entry.get("yizijue_state"), entry.get("facts"), entry.get("action"))


def run_pinned_write(workspace: Path, entry: dict, content: str, writer: Writer) -> dict:
    entry = execution_view(entry)
    blocked = write_block_reason(entry)
    if blocked is not None:
        return {"ran": False, "executed": False, "reason": blocked}
    evidence = entry["evidence"]
    digest_field = "sha256" if entry["action"] == "ALLOW_ATOMIC_WRITE" else "post_sha256"
    if sha256_text(content) != evidence[digest_field]:
        return {"ran": False, "executed": False, "reason": "sha_mismatch"}
    try:
        result = writer(workspace, evidence["path"], content)
    except PathGuardError:
        return {"ran": False, "executed": False, "reason": "path_rejected"}
    try:
        written = PathGuard.resolve_target(workspace, evidence["path"]).read_text(encoding="utf-8")
    except (OSError, UnicodeError, PathGuardError):
        written = None
    if written is None or sha256_text(written) != evidence[digest_field]:
        return {"ran": False, "executed": False, "reason": "sha_mismatch", "path": evidence["path"], "result": result}
    return {
        "ran": True,
        "executed": True,
        "path": evidence["path"],
        "sha256": sha256_text(written),
        "result": result,
    }


def unique_patch_text(workspace: Path, relative_path: str, search: str, replace: str) -> str | None:
    if search == "" or ".." in Path(relative_path).parts or relative_path.startswith(("/", "\\")):
        return None
    try:
        original = PathGuard.resolve_target(workspace, relative_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError, PathGuardError):
        return None
    if original.count(search) != 1:
        return None
    return original.replace(search, replace, 1)


def workspace_writer(workspace: Path, relative_path: str, content: str) -> dict:
    written = PathGuard.write_text(workspace, relative_path, content)
    return {"path": relative_path, "sha256": written["sha256"]}
