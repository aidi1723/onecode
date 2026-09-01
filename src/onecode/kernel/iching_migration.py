from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from onecode.kernel.iching_encoding import (
    RULE_SCHEMA_V2,
    convert_status,
    convert_trigram,
    normalize_rule_schema,
    validate_status,
)


STATUS_FIELDS = ("iching_status_code", "global_status_code", "task_status_code", "status_code")


def audit_status_migration(status_code: int, source_schema: str | None = None) -> dict[str, Any]:
    source = normalize_rule_schema(source_schema)
    source_status = validate_status(status_code)
    source_inner = source_status & 0b111
    source_outer = (source_status >> 3) & 0b111
    target_inner = convert_trigram(source_inner, source, RULE_SCHEMA_V2)
    target_outer = convert_trigram(source_outer, source, RULE_SCHEMA_V2)
    target_status = convert_status(source_status, source, RULE_SCHEMA_V2)
    affected_scopes = []
    if source_inner != target_inner:
        affected_scopes.append("inner")
    if source_outer != target_outer:
        affected_scopes.append("outer")
    return {
        "source_schema": source,
        "target_schema": RULE_SCHEMA_V2,
        "source_status_code": source_status,
        "target_status_code": target_status,
        "source_binary": format(source_status, "06b"),
        "target_binary": format(target_status, "06b"),
        "source_inner_trigram": source_inner,
        "target_inner_trigram": target_inner,
        "source_outer_trigram": source_outer,
        "target_outer_trigram": target_outer,
        "affected_scopes": affected_scopes,
        "changed": source_status != target_status,
    }


def evidence_status(payload: dict[str, Any]) -> tuple[str, int]:
    for field in STATUS_FIELDS:
        if field in payload:
            return field, validate_status(payload[field])
    raise ValueError("I Ching evidence does not contain a supported status field")


def audit_evidence_file(path: Path) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    source_bytes = resolved.read_bytes()
    payload = json.loads(source_bytes.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("I Ching evidence file must contain a JSON object")
    source_schema = normalize_rule_schema(payload.get("rule_schema"))
    status_field, status_code = evidence_status(payload)
    return {
        "path": str(resolved),
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_schema": source_schema,
        "status_field": status_field,
        "migration": audit_status_migration(status_code, source_schema),
    }
