from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib import request as urlrequest

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_skill_dictionary.reference_agent_adapter import ReferenceAgentAdapter


def run_smoke(base_url: str, workspace: str = ".", token: str | None = None) -> dict[str, Any]:
    base_url = base_url.rstrip("/")
    checks: dict[str, str] = {}
    details: dict[str, Any] = {}

    protocol = _json_request("GET", f"{base_url}/v1/yizijue/protocol")
    checks["protocol"] = "pass" if protocol.get("compatibility") == "agent-agnostic" else "fail"
    details["protocol"] = {"compatibility": protocol.get("compatibility")}

    resolve = _json_request(
        "POST",
        f"{base_url}/v1/yizijue/resolve",
        json={"input": "查：看看项目结构"},
    )
    checks["resolve"] = "pass" if resolve.get("active_code") == "查" else "fail"
    details["resolve"] = {
        "active_code": resolve.get("active_code"),
        "binary_trigram": resolve.get("binary_trigram"),
    }

    preflight = _json_request(
        "POST",
        f"{base_url}/v1/yizijue/preflight-tool",
        json={
            "active_code": "查",
            "tool_name": "write_file",
            "arguments": {"path": "app.py"},
        },
        token=token,
    )
    checks["preflight_blocks_write"] = "pass" if preflight.get("allowed") is False else "fail"
    details["preflight"] = {
        "allowed": preflight.get("allowed"),
        "violations": preflight.get("violations", []),
    }

    evidence = _json_request(
        "POST",
        f"{base_url}/v1/yizijue/submit-evidence",
        json={
            "workspace": workspace,
            "command": "http_gateway_smoke_external_evidence",
            "exit_code": 0,
            "stdout": "smoke-ok",
            "stderr": "",
        },
        token=token,
    )
    checks["submit_evidence"] = "pass" if evidence.get("status") == "accepted" else "fail"
    details["submit_evidence"] = {
        "status": evidence.get("status"),
        "audit_log_path": evidence.get("audit_log_path"),
    }

    build_tool = _json_request(
        "POST",
        f"{base_url}/v1/yizijue/build-tool",
        json={
            "workspace": workspace,
            "tool_name": "write_file",
            "arguments": {
                "path": "smoke_build/main.py",
                "content": "VALUE = 1\n",
            },
        },
        token=token,
    )
    checks["build_tool_scoped_write"] = (
        "pass"
        if build_tool.get("status") == "ok" and build_tool.get("next_hexagram") == "001"
        else "fail"
    )
    details["build_tool_scoped_write"] = {
        "status": build_tool.get("status"),
        "next_hexagram": build_tool.get("next_hexagram"),
    }

    adapter = ReferenceAgentAdapter(base_url=base_url, workspace=workspace, token=token)
    adapter_result = adapter.run("查：看看项目结构")
    checks["reference_agent_adapter"] = "pass" if adapter_result.get("status") == "completed" else "fail"
    details["reference_agent_adapter"] = {
        "status": adapter_result.get("status"),
        "active_code": adapter_result.get("active_code"),
        "tools": [item.get("tool") for item in adapter_result.get("tool_results", [])],
    }

    run = _json_request(
        "POST",
        f"{base_url}/v1/yizijue/run",
        json={"input": "帮我看看项目结构", "workspace": workspace},
        token=token,
    )
    checks["run"] = "pass" if run.get("status") == "completed" and run.get("trace") == ["查", "总"] else "fail"
    details["run"] = {
        "status": run.get("status"),
        "trace": run.get("trace"),
        "audit_log_path": run.get("audit_log_path"),
    }

    return {
        "ok": all(value == "pass" for value in checks.values()),
        "base_url": base_url,
        "checks": checks,
        "details": details,
    }


def _json_request(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    headers = {"content-type": "application/json"}
    token = kwargs.pop("token", None)
    if token:
        headers["authorization"] = f"Bearer {token}"
    data = None
    if "json" in kwargs:
        data = json.dumps(kwargs["json"]).encode("utf-8")
    request = urlrequest.Request(url, data=data, headers=headers, method=method)
    with urlrequest.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object from {url}")
    return payload


def main() -> dict[str, Any]:
    parser = argparse.ArgumentParser(description="Smoke test a running OneWord HTTP gateway.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8080",
        help="Gateway base URL, without /v1 suffix.",
    )
    parser.add_argument("--workspace", default=".", help="Workspace path passed to /v1/yizijue/run.")
    parser.add_argument("--token", default=None, help="Optional ONEWORD_GATEWAY_TOKEN for protected /run checks.")
    args = parser.parse_args()

    payload = run_smoke(args.base_url, workspace=args.workspace, token=args.token)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return payload


if __name__ == "__main__":
    main()
