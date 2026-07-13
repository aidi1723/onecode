import json
import subprocess
import unittest


def valid_task_pack() -> dict:
    return {
        "schema_version": 2,
        "routing_status": "complete",
        "route_id": "sha256:route",
        "registry_verification": {
            "status": "ok",
            "skill_count": 172,
            "trusted_count": 166,
            "tampered_count": 0,
            "unknown_provenance_count": 0,
        },
        "selected_scenarios": [{"scenario_id": "skill-router-quality-review"}],
        "selected_skills": [
            {
                "name": "code-test-regression",
                "status": "trusted",
                "verifier_expectations": "- targeted test run\n- failure coverage",
                "safe_workflow": "private workflow body",
            }
        ],
        "execution_graph": {
            "status": "ready",
            "nodes": [
                {
                    "id": "skill:i1:code-test-regression",
                    "skill": "code-test-regression",
                    "stage": "verification",
                }
            ],
            "edges": [],
        },
        "host_execution_protocol": {
            "mode": "method_only",
            "runtime_boundary": "The host runtime controls permissions and execution.",
        },
    }


def completed_runner(payload: dict, *, returncode: int = 0):
    def run(*_args, **_kwargs):
        return subprocess.CompletedProcess([], returncode, json.dumps(payload), "")

    return run


class SafeAgentRouterTests(unittest.TestCase):
    def test_routes_schema_v2_trusted_task_pack(self):
        from onecode.kernel.safe_agent_router import route_safe_agent_task

        route = route_safe_agent_task("检查项目", runner=completed_runner(valid_task_pack()))

        self.assertEqual(route.status, "ok")
        self.assertEqual(route.schema_version, 2)
        self.assertEqual(route.selected_scenarios, ("skill-router-quality-review",))
        self.assertEqual(route.selected_skills, ("code-test-regression",))
        self.assertEqual(route.execution_order, ("code-test-regression",))
        context = route.to_planning_context()
        self.assertEqual(context["safety_boundary"], "method_only")
        self.assertNotIn("safe_workflow", json.dumps(context))

    def test_rejects_tampered_registry(self):
        from onecode.kernel.safe_agent_router import route_safe_agent_task

        pack = valid_task_pack()
        pack["registry_verification"]["tampered_count"] = 1

        route = route_safe_agent_task("检查项目", runner=completed_runner(pack))

        self.assertEqual((route.status, route.reason), ("invalid", "registry_verification_failed"))

    def test_rejects_non_trusted_selected_skill(self):
        from onecode.kernel.safe_agent_router import route_safe_agent_task

        pack = valid_task_pack()
        pack["selected_skills"][0]["status"] = "review_required"

        route = route_safe_agent_task("检查项目", runner=completed_runner(pack))

        self.assertEqual((route.status, route.reason), ("invalid", "untrusted_skill_selected"))

    def test_missing_router_is_explicit(self):
        from onecode.kernel.safe_agent_router import route_safe_agent_task

        def missing(*_args, **_kwargs):
            raise FileNotFoundError

        route = route_safe_agent_task("检查项目", runner=missing)

        self.assertEqual((route.status, route.reason), ("unavailable", "router_command_not_found"))

    def test_rejects_oversized_router_output(self):
        from onecode.kernel.safe_agent_router import route_safe_agent_task

        route = route_safe_agent_task(
            "检查项目",
            runner=completed_runner(valid_task_pack()),
            max_output_bytes=8,
        )

        self.assertEqual((route.status, route.reason), ("invalid", "router_output_too_large"))


if __name__ == "__main__":
    unittest.main()
