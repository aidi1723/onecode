from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.project_context import RulesImport


class _ParsedRulesImport(RulesImport):
    def __init__(self, mode: str, frameworks: tuple[str, ...] = ()) -> None:
        object.__setattr__(self, "_mode", mode)
        object.__setattr__(self, "_frameworks", frozenset(frameworks))
        object.__setattr__(self, "_framework_order", frameworks)

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def frameworks(self) -> tuple[str, ...]:
        return self._framework_order


def inspect_runtime_config(workspace: Path) -> dict:
    root = Path(workspace)
    merged: dict[str, Any] = {}
    files: list[dict[str, Any]] = []

    for rank, (source, path) in enumerate(_candidate_paths(root)):
        report = _inspect_config_file(source, path, rank)
        files.append(report)
        if report["loaded"]:
            merged.update(report["_payload"])
        report.pop("_payload", None)

    status = "warning" if any(item["status"] == "load_error" for item in files) else "ok"
    status_code = _status_code_for(status)
    transition = IchingKernel.transition(status_code)
    summary = {
        "loaded_count": sum(1 for item in files if item["status"] == "loaded"),
        "not_found_count": sum(1 for item in files if item["status"] == "not_found"),
        "load_error_count": sum(1 for item in files if item["status"] == "load_error"),
        "element": IchingKernel.TRIGRAM_ELEMENTS[IchingKernel.GEN],
        "yin_yang_pressure": "activate" if status == "warning" else "stable",
        "iching_status_code": status_code,
        "iching_transition_action": transition.action,
        "iching_transition_reason": transition.reason,
        "dispatch_decision": IchingKernel.dispatch_decision(transition),
    }

    effective = dict(merged)
    rules_import = parse_rules_import(effective)
    effective["rulesImport"] = _rules_import_effective_value(rules_import)

    return {
        "status": status,
        "files": files,
        "effective": effective,
        "summary": summary,
        "iching_status_code": status_code,
        "iching_transition_action": transition.action,
        "iching_transition_reason": transition.reason,
        "dispatch_decision": IchingKernel.dispatch_decision(transition),
    }


def parse_rules_import(config: dict) -> RulesImport:
    value = config.get("rulesImport") if isinstance(config, dict) else None
    if value is None:
        return _ParsedRulesImport("auto")
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "none":
            return _ParsedRulesImport("none")
        if normalized == "" or normalized == "auto":
            return _ParsedRulesImport("auto")
        return _ParsedRulesImport("list", (_normalize_framework(value),))
    if isinstance(value, list):
        frameworks = tuple(_normalize_framework(item) for item in value if isinstance(item, str) and item.strip())
        return _ParsedRulesImport("list", frameworks)
    return _ParsedRulesImport("auto")


def _candidate_paths(workspace: Path) -> tuple[tuple[str, Path], ...]:
    onecode_home = Path(os.getenv("ONECODE_HOME", "~/.onecode")).expanduser()
    return (
        ("onecode_home", onecode_home / "config.json"),
        ("project", workspace / ".onecode" / "config.json"),
        ("local", workspace / ".onecode" / "config.local.json"),
    )


def _inspect_config_file(source: str, path: Path, precedence_rank: int) -> dict[str, Any]:
    base: dict[str, Any] = {
        "source": source,
        "path": path.expanduser().as_posix(),
        "status": "not_found",
        "loaded": False,
        "reason": "optional_config_not_found",
        "detail": None,
        "precedence_rank": precedence_rank,
        "key_paths": [],
        "warnings": [],
        "_payload": {},
    }
    if not path.is_file():
        return base

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return base | {
            "status": "load_error",
            "reason": "invalid_json",
            "detail": str(exc),
        }
    except OSError as exc:
        return base | {
            "status": "load_error",
            "reason": "read_error",
            "detail": str(exc),
        }

    if not isinstance(payload, dict):
        return base | {
            "status": "load_error",
            "reason": "non_object_json",
            "detail": f"expected JSON object, got {type(payload).__name__}",
        }

    return base | {
        "status": "loaded",
        "loaded": True,
        "reason": "loaded",
        "detail": None,
        "key_paths": _key_paths(payload),
        "_payload": payload,
    }


def _key_paths(value: Any, prefix: str = "") -> list[str]:
    if not isinstance(value, dict):
        return []
    paths: list[str] = []
    for key in sorted(value):
        key_path = f"{prefix}.{key}" if prefix else str(key)
        paths.append(key_path)
        paths.extend(_key_paths(value[key], key_path))
    return paths


def _normalize_framework(value: str) -> str:
    return "_".join(value.strip().lower().replace("-", "_").split())


def _rules_import_effective_value(rules_import: RulesImport) -> str | list[str]:
    mode = rules_import.mode if isinstance(rules_import, _ParsedRulesImport) else rules_import._mode
    frameworks = rules_import.frameworks if isinstance(rules_import, _ParsedRulesImport) else tuple(sorted(rules_import._frameworks))
    if mode == "list":
        return list(frameworks)
    return mode


def _status_code_for(status: str) -> int:
    if status == "warning":
        return IchingKernel.compute_status(IchingKernel.GEN, IchingKernel.KAN)
    return IchingKernel.compute_status(IchingKernel.GEN, IchingKernel.KUN)
