from __future__ import annotations

from dataclasses import dataclass, field
import json
import subprocess
from typing import Any, Callable


DEFAULT_ROUTER_TIMEOUT_SECONDS = 15.0
DEFAULT_MAX_ROUTER_OUTPUT_BYTES = 1_000_000


@dataclass(frozen=True)
class SafeAgentRoute:
    status: str
    reason: str | None
    schema_version: int | None = None
    route_id: str | None = None
    selected_scenarios: tuple[str, ...] = ()
    selected_skills: tuple[str, ...] = ()
    execution_order: tuple[str, ...] = ()
    verifier_expectations: tuple[str, ...] = ()
    registry_summary: dict[str, int | str] = field(default_factory=dict)

    def to_planning_context(self) -> dict[str, object]:
        return {
            "status": self.status,
            "reason": self.reason,
            "schema_version": self.schema_version,
            "route_id": self.route_id,
            "selected_scenarios": list(self.selected_scenarios),
            "selected_skills": list(self.selected_skills),
            "execution_order": list(self.execution_order),
            "verifier_expectations": list(self.verifier_expectations),
            "registry_verification": dict(self.registry_summary),
            "safety_boundary": "method_only",
        }


RouterRunner = Callable[..., subprocess.CompletedProcess[str]]


def route_safe_agent_task(
    task: str,
    *,
    runner: RouterRunner = subprocess.run,
    timeout_seconds: float = DEFAULT_ROUTER_TIMEOUT_SECONDS,
    max_output_bytes: int = DEFAULT_MAX_ROUTER_OUTPUT_BYTES,
) -> SafeAgentRoute:
    if not isinstance(task, str) or not task.strip():
        return SafeAgentRoute("invalid", "invalid_task")
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if isinstance(max_output_bytes, bool) or not isinstance(max_output_bytes, int) or max_output_bytes <= 0:
        raise ValueError("max_output_bytes must be positive")
    try:
        completed = runner(
            ["safe-agent-router-task-pack", task, "--format", "json"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        return SafeAgentRoute("unavailable", "router_command_not_found")
    except subprocess.TimeoutExpired:
        return SafeAgentRoute("unavailable", "router_timeout")
    except OSError:
        return SafeAgentRoute("unavailable", "router_execution_failed")
    return _route_from_completed(completed, max_output_bytes=max_output_bytes)


def _route_from_completed(
    completed: subprocess.CompletedProcess[str],
    *,
    max_output_bytes: int,
) -> SafeAgentRoute:
    stdout = completed.stdout if isinstance(completed.stdout, str) else ""
    if len(stdout.encode("utf-8")) > max_output_bytes:
        return SafeAgentRoute("invalid", "router_output_too_large")
    if completed.returncode != 0:
        return SafeAgentRoute("unavailable", "router_nonzero_exit")
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return SafeAgentRoute("invalid", "router_invalid_json")
    if not isinstance(payload, dict):
        return SafeAgentRoute("invalid", "router_invalid_payload")
    return _validate_task_pack(payload)


def _validate_task_pack(payload: dict[str, Any]) -> SafeAgentRoute:
    if payload.get("schema_version") != 2:
        return SafeAgentRoute("invalid", "unsupported_router_schema")

    registry = payload.get("registry_verification")
    if not isinstance(registry, dict):
        return SafeAgentRoute("invalid", "registry_verification_missing")
    if (
        registry.get("status") != "ok"
        or registry.get("tampered_count") != 0
        or _strict_nonnegative_int(registry.get("unknown_provenance_count")) not in {0, None}
    ):
        return SafeAgentRoute("invalid", "registry_verification_failed")

    routing_status = payload.get("routing_status")
    if routing_status != "complete":
        if routing_status == "incomplete":
            return SafeAgentRoute("no_match", "no_matching_scenario", schema_version=2)
        return SafeAgentRoute("invalid", "routing_incomplete")

    selected_skills_payload = payload.get("selected_skills")
    if not isinstance(selected_skills_payload, list):
        return SafeAgentRoute("invalid", "selected_skills_invalid")
    selected_skills: list[str] = []
    verifier_expectations: list[str] = []
    for item in selected_skills_payload:
        if not isinstance(item, dict) or item.get("status") != "trusted":
            return SafeAgentRoute("invalid", "untrusted_skill_selected")
        name = item.get("name")
        if not isinstance(name, str) or not name:
            return SafeAgentRoute("invalid", "selected_skill_name_invalid")
        selected_skills.append(name)
        expectations = item.get("verifier_expectations")
        if isinstance(expectations, str) and expectations.strip():
            verifier_expectations.extend(
                line.removeprefix("- ").strip()
                for line in expectations.splitlines()
                if line.strip()
            )

    selected_scenarios_payload = payload.get("selected_scenarios")
    if not isinstance(selected_scenarios_payload, list):
        return SafeAgentRoute("invalid", "selected_scenarios_invalid")
    selected_scenarios = tuple(
        item["scenario_id"]
        for item in selected_scenarios_payload
        if isinstance(item, dict) and isinstance(item.get("scenario_id"), str)
    )

    graph = payload.get("execution_graph")
    nodes = graph.get("nodes") if isinstance(graph, dict) else []
    execution_order = tuple(
        item["skill"]
        for item in nodes
        if isinstance(item, dict)
        and isinstance(item.get("skill"), str)
        and item["skill"] in selected_skills
    )
    registry_summary: dict[str, int | str] = {"status": "ok"}
    for key in ("skill_count", "trusted_count", "tampered_count", "unknown_provenance_count"):
        value = _strict_nonnegative_int(registry.get(key))
        if value is not None:
            registry_summary[key] = value

    route_id = payload.get("route_id") if isinstance(payload.get("route_id"), str) else None
    return SafeAgentRoute(
        status="ok",
        reason=None,
        schema_version=2,
        route_id=route_id,
        selected_scenarios=selected_scenarios,
        selected_skills=tuple(selected_skills),
        execution_order=execution_order,
        verifier_expectations=tuple(dict.fromkeys(verifier_expectations)),
        registry_summary=registry_summary,
    )


def _strict_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value
