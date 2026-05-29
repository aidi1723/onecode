from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib import request as urlrequest

from .tool_executor_registry import execute_registered_tool


class ReferenceAgentAdapter:
    """Small external-Agent reference loop guarded by the OneWord gateway."""

    def __init__(self, base_url: str, workspace: str | Path, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.workspace = Path(workspace).resolve()
        self.token = token

    def run(
        self,
        user_input: str,
        planned_tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        resolve = self._post("/v1/yizijue/resolve", {"input": user_input})
        active_code = str(resolve.get("active_code") or "")
        tools = planned_tools if planned_tools is not None else self._default_tools_for(active_code)
        tool_results: list[dict[str, Any]] = []

        for tool in tools:
            tool_name = str(tool.get("name") or "")
            arguments = tool.get("arguments", {})
            preflight = self._post(
                "/v1/yizijue/preflight-tool",
                {
                    "active_code": active_code,
                    "tool_name": tool_name,
                    "arguments": arguments,
                },
                authorized=True,
            )
            if preflight.get("allowed") is not True:
                result = {
                    "tool": tool_name,
                    "exit_code": 126,
                    "stdout": "",
                    "stderr": json.dumps(preflight.get("violations", []), ensure_ascii=False),
                    "preflight": preflight,
                }
                tool_results.append(result)
                self._submit_evidence(tool_name, result)
                return {
                    "status": "blocked",
                    "active_code": active_code,
                    "resolve": resolve,
                    "tool_results": tool_results,
                }

            result = self._execute_tool(tool_name, arguments)
            result["preflight"] = preflight
            tool_results.append(result)
            self._submit_evidence(tool_name, result)
            if int(result["exit_code"]) != 0:
                return {
                    "status": "failed",
                    "active_code": active_code,
                    "resolve": resolve,
                    "tool_results": tool_results,
                }

        return {
            "status": "completed",
            "active_code": active_code,
            "resolve": resolve,
            "tool_results": tool_results,
        }

    def _default_tools_for(self, active_code: str) -> list[dict[str, Any]]:
        if active_code == "查":
            return [{"name": "list_directory", "arguments": {"path": "."}}]
        if active_code == "测":
            return [{"name": "run_pytest", "arguments": {"command": "python3 -m unittest discover -s tests -v"}}]
        return []

    def _execute_tool(self, tool_name: str, arguments: Any) -> dict[str, Any]:
        return execute_registered_tool(tool_name, arguments, self.workspace)

    def _submit_evidence(self, tool_name: str, result: dict[str, Any]) -> dict[str, Any]:
        return self._post(
            "/v1/yizijue/submit-evidence",
            {
                "workspace": str(self.workspace),
                "source": "reference_agent",
                "session_id": "reference-agent-default",
                "command": f"reference_agent:{tool_name}",
                "exit_code": int(result.get("exit_code", 1)),
                "stdout": str(result.get("stdout", "")),
                "stderr": str(result.get("stderr", "")),
            },
            authorized=True,
        )

    def _post(self, path: str, payload: dict[str, Any], authorized: bool = False) -> dict[str, Any]:
        return _json_request(
            "POST",
            f"{self.base_url}{path}",
            payload=payload,
            token=self.token if authorized else None,
        )


def _json_request(method: str, url: str, payload: dict[str, Any], token: str | None = None) -> dict[str, Any]:
    headers = {"content-type": "application/json"}
    if token:
        headers["authorization"] = f"Bearer {token}"
    request = urlrequest.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method=method,
    )
    with urlrequest.urlopen(request, timeout=30) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"expected JSON object from {url}")
    return parsed


def main() -> str:
    parser = argparse.ArgumentParser(description="Run the reference external-Agent loop through a OneWord gateway.")
    parser.add_argument("input", help="User request to send through /resolve.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080", help="Gateway base URL.")
    parser.add_argument("--workspace", default=".", help="Workspace root.")
    parser.add_argument("--token", default=None, help="Optional ONEWORD_GATEWAY_TOKEN for evidence submission.")
    parser.add_argument(
        "--planned-tools-json",
        default=None,
        help="Optional JSON array of planned tool calls for adapter testing.",
    )
    args = parser.parse_args()

    planned_tools = json.loads(args.planned_tools_json) if args.planned_tools_json else None
    adapter = ReferenceAgentAdapter(args.base_url, args.workspace, token=args.token)
    result = adapter.run(args.input, planned_tools=planned_tools)
    output = json.dumps(result, ensure_ascii=False, sort_keys=True)
    print(output)
    return output


if __name__ == "__main__":
    main()
