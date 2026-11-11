#!/usr/bin/env python3
import json

from onecode.kernel.action_intent import ActionIntent
from onecode.kernel.hexagram import HexagramStatusCode, IchingKernel
from onecode.kernel.permission_matrix import PermissionMatrix
from onecode.kernel.project_gateway import project_gateway


def sample_intents() -> dict[str, ActionIntent]:
    return {
        "noop": ActionIntent.noop(),
        "write_text": ActionIntent.write_text("src/a.py", "x"),
        "patch_text": ActionIntent.patch_text("src/a.py", "old", "new"),
        "execute_pytest": ActionIntent.execute_pytest("tests"),
        "bash_execution": ActionIntent.bash_execution("echo no"),
        "invalid_intent": ActionIntent.invalid_intent("invalid_intent"),
    }


def permission_row(status_code: int) -> dict[str, str]:
    matrix = PermissionMatrix()
    state = HexagramStatusCode(format(status_code, "06b"))
    return {
        name: matrix.evaluate(state, intent).decision.value
        for name, intent in sample_intents().items()
    }


def code_row(status_code: int) -> dict[str, object]:
    symbolic = IchingKernel.transition(status_code)
    dispatch = IchingKernel.dispatch_decision(symbolic)
    return {
        "status_code": status_code,
        "binary": format(status_code, "06b"),
        "inner_trigram": status_code & 0b111,
        "outer_trigram": (status_code >> 3) & 0b111,
        "symbolic_action": symbolic.action,
        "symbolic_reason": symbolic.reason,
        "symbolic_status_code": symbolic.status_code,
        "symbolic_status_rewritten": symbolic.status_code != status_code,
        "dispatch": dispatch,
        "permission": permission_row(status_code),
    }


def pinned_gateway_rows() -> list[dict[str, object]]:
    rows = [
        ("100001", {"intent_type": "bash_execution", "path_scope": "outside_workspace", "sandbox_state": "missing", "evidence_state": "required"}),
        ("000000", {"intent_type": "invalid_intent", "path_scope": "no_path", "sandbox_state": "not_required", "evidence_state": "required"}),
        ("111111", {"intent_type": "write_text", "path_scope": "workspace_relative", "sandbox_state": "not_required", "evidence_state": "present"}),
        ("111111", {"intent_type": "patch_text", "path_scope": "workspace_relative", "sandbox_state": "required", "evidence_state": "present"}),
        ("010010", {"intent_type": "execute_pytest", "path_scope": "no_path", "sandbox_state": "required", "evidence_state": "required"}),
    ]
    projected = []
    for binary, fact_row in rows:
        projected.append(
            {
                "binary": binary,
                "facts": fact_row,
                "action": project_gateway(int(binary, 2), fact_row),
            }
        )
    return projected


def main() -> int:
    report = {
        "codes": [code_row(status_code) for status_code in range(64)],
        "pinned_gateway": pinned_gateway_rows(),
    }
    if len(report["codes"]) != 64:
        raise SystemExit("expected 64 codes")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
