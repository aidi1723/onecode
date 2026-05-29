import unittest

from agent_skill_dictionary.build_mode_permissions import canonical_tool_schema, filter_tools_schema, map_shadow_tool, write_file_fallback_schema
from agent_skill_dictionary.build_mode_types import HEX_CREATE, HEX_HALT, HEX_INSPECT, HEX_PROMPT, HEX_VERIFY


def tool(name):
    return {"type": "function", "function": {"name": name, "description": "long description"}}


def response_tool(name):
    return {"type": "function", "name": name, "description": "long description"}


class BuildModePermissionsTest(unittest.TestCase):
    def test_prompt_clears_tools(self):
        self.assertEqual(filter_tools_schema(HEX_PROMPT, [tool("write_file")]), [])

    def test_inspect_keeps_only_native_inspect_card(self):
        result = filter_tools_schema(HEX_INSPECT, [tool("grep"), tool("native_inspect_card"), tool("write_file")])
        self.assertEqual([t["function"]["name"] for t in result], ["native_inspect_card"])

    def test_create_keeps_write_tools_only(self):
        result = filter_tools_schema(HEX_CREATE, [tool("write_file"), tool("run_pytest"), tool("grep")])
        self.assertEqual([t["function"]["name"] for t in result], ["write_file"])

    def test_verify_keeps_test_tools_only(self):
        result = filter_tools_schema(HEX_VERIFY, [tool("write_file"), tool("run_pytest")])
        self.assertEqual([t["function"]["name"] for t in result], ["run_pytest"])

    def test_halt_clears_tools(self):
        self.assertEqual(filter_tools_schema(HEX_HALT, [tool("run_pytest")]), [])

    def test_shadow_maps_bash_pytest_to_verify(self):
        mapped = map_shadow_tool("bash", {"command": "python -m pytest -q"})
        self.assertEqual(mapped.hexagram, HEX_VERIFY)
        self.assertEqual(mapped.shadow_action, "sandbox_runner")

    def test_shadow_maps_rm_to_halt(self):
        mapped = map_shadow_tool("bash", {"command": "rm -rf /tmp/x"})
        self.assertEqual(mapped.hexagram, HEX_HALT)
        self.assertEqual(mapped.shadow_action, "halt")


    def test_canonical_verify_tool_injects_chat_run_pytest_schema(self):
        result = canonical_tool_schema(HEX_VERIFY, [tool("apply_patch")])

        self.assertEqual(result[0]["function"]["name"], "run_pytest")
        self.assertEqual(result[0]["function"]["parameters"]["required"], ["command"])
        command = result[0]["function"]["parameters"]["properties"]["command"]
        self.assertEqual(command["default"], "python3 -m unittest discover -s tests -v")

    def test_canonical_verify_tool_injects_responses_run_pytest_schema(self):
        result = canonical_tool_schema(HEX_VERIFY, [response_tool("apply_patch")])

        self.assertEqual(result[0]["name"], "run_pytest")
        self.assertEqual(result[0]["parameters"]["required"], ["command"])
        self.assertEqual(
            result[0]["parameters"]["properties"]["command"]["default"],
            "python3 -m unittest discover -s tests -v",
        )
        self.assertNotIn("function", result[0])

    def test_write_file_fallback_schema_exposes_only_full_file_write(self):
        result = write_file_fallback_schema([tool("apply_patch"), tool("write_file"), tool("run_pytest")])

        self.assertEqual([t["function"]["name"] for t in result], ["write_file"])
        parameters = result[0]["function"]["parameters"]
        self.assertEqual(parameters["required"], ["path", "content"])
        self.assertNotIn("patch", parameters["properties"])

    def test_write_file_fallback_schema_injects_responses_shape_when_missing(self):
        result = write_file_fallback_schema([response_tool("apply_patch")])

        self.assertEqual(result[0]["type"], "function")
        self.assertEqual(result[0]["name"], "write_file")
        self.assertEqual(result[0]["parameters"]["required"], ["path", "content"])
        self.assertNotIn("function", result[0])

    def test_write_file_fallback_schema_injects_chat_shape_when_missing(self):
        result = write_file_fallback_schema([tool("apply_patch")])

        self.assertEqual(result[0]["type"], "function")
        self.assertEqual(result[0]["function"]["name"], "write_file")
        self.assertEqual(result[0]["function"]["parameters"]["required"], ["path", "content"])


if __name__ == "__main__":
    unittest.main()
