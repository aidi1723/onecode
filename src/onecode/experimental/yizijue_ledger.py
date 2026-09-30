"""Record a YiZiJue decision in the workspace ledger without executing it."""

import json
import os
from pathlib import Path

from onecode.kernel.gateway_engine import ALLOWED_ACTIONS, ALLOWED_STATES


NON_EXECUTION_REASONS = {
    "entropy_observe",
    "kun_deny_ledger",
    "sha_mismatch",
    "verifier_unconfirmed",
    "command_rejected",
    "gateway_mismatch",
    "gateway_unread",
    "not_write",
    "not_verifier",
    "withheld",
    "path_rejected",
    "already_executed",
    "evidence_missing",
    "generation_not_a_cast",
    "effect_not_recorded",
    "yizijue_admission_rejected",
}

EXECUTION_FIELDS = ("yizijue_state", "action", "reason", "cycle", "executed", "facts", "evidence")


def execution_view(entry: dict) -> dict:
    """Fields the verifier and write gates may read. A moving cast is not one of them."""
    if not isinstance(entry, dict):
        return {}
    return {key: entry[key] for key in EXECUTION_FIELDS if key in entry}


def yizijue_ledger_entry(record: dict) -> dict:
    if "kind" in record:
        raise ValueError("a copied ledger line cannot be admitted")
    state = record.get("yizijue_state")
    action = record.get("action")
    reason = record.get("reason")
    if state not in ALLOWED_STATES:
        raise ValueError("yizijue_state must be a hexagram")
    if action not in ALLOWED_ACTIONS:
        raise ValueError("action must be a gateway action")
    if reason == "entropy_observe" and (state == "000000" or str(action).startswith("ALLOW_")):
        raise ValueError("entropy_observe cannot be kun or an allow")
    if reason == "kun_deny_ledger" and (state != "000000" or action != "DENY_AND_LEDGER"):
        raise ValueError("kun ledger is only the kun deny")
    moving = accepted_moving_cast(state, record.get("moving_cast"))
    if action == "RUN_VERIFIER_IN_SANDBOX":
        cycle = "verify"
    else:
        cycle = "stop"
    return {
        "kind": "yizijue_decision",
        "yizijue_state": state,
        "action": action,
        "reason": reason,
        "symbolic_transition": symbolic_transition(state),
        "moving_cast": moving,
        "cycle": cycle,
        "executed": False,
    }


def accepted_moving_cast(state: object, moving: object) -> dict | None:
    """Keep a moving cast only when its changed hexagram is the kernel's."""
    if not isinstance(state, str) or state not in ALLOWED_STATES or not isinstance(moving, dict):
        return None
    before = moving.get("before")
    after = moving.get("after")
    lines = moving.get("moving")
    if before != state or not isinstance(after, str) or after not in ALLOWED_STATES:
        return None
    if not isinstance(lines, list) or any(type(index) is not int or not 0 <= index <= 5 for index in lines):
        return None
    if len(set(lines)) != len(lines):
        return None
    from onecode.kernel.hexagram import IchingKernel

    expected = format(IchingKernel.mutate_lines(int(before, 2), lines), "06b")
    if after != expected:
        return None
    values = moving.get("values")
    if values is not None:
        from onecode.experimental.moving_cast import cast_from_lines

        try:
            cast = cast_from_lines(values)
        except ValueError:
            return None
        if (
            format(int(cast["before"]), "06b") != before
            or format(int(cast["after"]), "06b") != after
            or list(cast["moving"]) != list(lines)
        ):
            return None
        return {"values": list(cast["values"]), "before": before, "after": after, "moving": list(lines)}
    return {"before": before, "after": after, "moving": list(lines)}


def symbolic_transition(state: str) -> dict:
    """Read the kernel's symbolic transition. It does not choose the gateway action."""
    from onecode.kernel.hexagram import IchingKernel

    transition = IchingKernel.transition(int(state, 2))
    return {
        "action": transition.action,
        "reason": transition.reason,
        "status_code": format(transition.status_code, "06b"),
    }


def append_yizijue_ledger(workspace: Path, record: dict) -> Path:
    entry = yizijue_ledger_entry(record)
    path = _ledger_path(workspace)
    _append(path, entry)
    _mirror_service(path, entry)
    return path


def yizijue_effect_entry(effect: dict) -> dict:
    kind = effect.get("effect")
    if kind not in {"verifier", "write"}:
        raise ValueError("effect must be verifier or write")
    ran = effect.get("ran") is True
    state = effect.get("yizijue_state")
    action = effect.get("action")
    if ran and kind == "verifier" and (state != "010010" or action != "RUN_VERIFIER_IN_SANDBOX"):
        raise ValueError("only the kan verifier may be executed")
    if ran and kind == "write" and (state != "111111" or action not in {"ALLOW_ATOMIC_WRITE", "ALLOW_PATCH_WITH_SHA"}):
        raise ValueError("only a qian allow may be executed")
    if effect.get("reason") in NON_EXECUTION_REASONS and ran:
        raise ValueError("a blocked decision cannot execute")
    command = _effect_command(effect.get("command"))
    path = _effect_path(effect.get("path"))
    digest = _effect_digest(effect.get("sha256"))
    if effect.get("command") is not None and command is None:
        raise ValueError("verifier execution must name the pinned command")
    if effect.get("path") is not None and path is None:
        raise ValueError("write execution must name a workspace path")
    if effect.get("sha256") is not None and digest is None:
        raise ValueError("write execution must name the file hash")
    if ran and kind == "verifier" and command is None:
        raise ValueError("verifier execution must name the pinned command")
    if ran and kind == "write" and (path is None or digest is None):
        raise ValueError("write execution must name the path and file hash")
    entry = {
        "kind": "yizijue_effect",
        "effect": kind,
        "yizijue_state": state,
        "action": action,
        "reason": effect.get("reason"),
        "ran": ran,
        "executed": ran,
    }
    if command is not None:
        entry["command"] = command
    if path is not None:
        entry["path"] = path
    if digest is not None:
        entry["sha256"] = digest
    return entry


def confirmed_proof(outcome: dict) -> dict:
    """Proof fields that may be shown or stored after a confirmed execution."""
    proof = {}
    command = _effect_command(outcome.get("command"))
    path = _effect_path(outcome.get("path"))
    digest = _effect_digest(outcome.get("sha256"))
    if command is not None:
        proof["command"] = command
    if path is not None:
        proof["path"] = path
    if digest is not None:
        proof["sha256"] = digest
    return proof


def _effect_command(command: object) -> list[str] | None:
    from onecode.experimental.yizijue_verifier import pinned_verifier_command

    try:
        reported = list(command) if command is not None else None
    except TypeError:
        return None
    if reported is None:
        return None
    if reported != pinned_verifier_command():
        return None
    return reported


def _effect_path(path: object) -> str | None:
    if not isinstance(path, str) or path == "":
        return None
    if ".." in Path(path).parts or path.startswith(("/", "\\")):
        return None
    return path


def _effect_digest(digest: object) -> str | None:
    if not isinstance(digest, str) or len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        return None
    return digest


def rejected_ledger_entry(record: dict) -> dict:
    return {
        "kind": "yizijue_decision",
        "yizijue_state": record.get("yizijue_state"),
        "action": record.get("action"),
        "reason": "yizijue_admission_rejected",
        "executed": False,
    }


def append_rejected_ledger_entry(workspace: Path, record: dict) -> Path:
    entry = rejected_ledger_entry(record)
    path = _ledger_path(workspace)
    _append(path, entry)
    _mirror_service(path, entry)
    return path


def append_yizijue_effect(workspace: Path, effect: dict) -> Path:
    entry = yizijue_effect_entry(effect)
    path = _ledger_path(workspace)
    _append(path, entry)
    _mirror_service(path, entry)
    return path


def _mirror_service(workspace_ledger: Path, entry: dict) -> None:
    service_ledger = os.environ.get("YIZIJUE_LEDGER")
    if not service_ledger:
        return
    service = Path(service_ledger)
    if service.resolve() == workspace_ledger.resolve():
        return
    _append(service, entry)


def _ledger_path(workspace: Path) -> Path:
    return workspace / ".onecode" / "yizijue-ledger.jsonl"


def _append(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
