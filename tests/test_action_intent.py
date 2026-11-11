import unittest

from onecode.kernel.action_intent import ActionIntent, ActionType


class ActionIntentTests(unittest.TestCase):
    def test_noop_intent_has_empty_payload(self):
        intent = ActionIntent.noop()

        self.assertEqual(intent.action_type, ActionType.NOOP)
        self.assertEqual(intent.payload, {})

    def test_invalid_intent_preserves_unmapped_intent_type(self):
        intent = ActionIntent.invalid_intent("teleport_asset")

        self.assertEqual(intent.action_type, ActionType.INVALID_INTENT)
        self.assertEqual(intent.payload, {"intent_type": "teleport_asset"})

    def test_write_text_requires_path_and_content(self):
        intent = ActionIntent.write_text("src/generated.py", "print('ok')\n")

        self.assertEqual(intent.action_type, ActionType.WRITE_TEXT)
        self.assertEqual(intent.payload["path"], "src/generated.py")
        self.assertEqual(intent.payload["content"], "print('ok')\n")

    def test_write_text_rejects_missing_path_or_content(self):
        with self.assertRaises(ValueError):
            ActionIntent(ActionType.WRITE_TEXT, {"path": "src/generated.py"})
        with self.assertRaises(ValueError):
            ActionIntent(ActionType.WRITE_TEXT, {"content": "x"})

    def test_patch_text_requires_path_search_and_replace_blocks(self):
        intent = ActionIntent.patch_text("src/generated.py", "old", "new")

        self.assertEqual(intent.action_type, ActionType.PATCH_TEXT)
        self.assertEqual(intent.payload["path"], "src/generated.py")
        self.assertEqual(intent.payload["search_block"], "old")
        self.assertEqual(intent.payload["replace_block"], "new")

    def test_patch_text_rejects_missing_required_fields(self):
        with self.assertRaises(ValueError):
            ActionIntent(ActionType.PATCH_TEXT, {"path": "src/generated.py", "search_block": "old"})
        with self.assertRaises(ValueError):
            ActionIntent(ActionType.PATCH_TEXT, {"path": "src/generated.py", "replace_block": "new"})
        with self.assertRaises(ValueError):
            ActionIntent(ActionType.PATCH_TEXT, {"search_block": "old", "replace_block": "new"})

    def test_rejects_unknown_action_type(self):
        with self.assertRaises(ValueError):
            ActionIntent("unknown", {})

    def test_bash_execution_intent_records_command_without_execution(self):
        intent = ActionIntent.bash_execution("rm -rf /")

        self.assertEqual(intent.action_type, ActionType.BASH_EXECUTION)
        self.assertEqual(intent.payload["command"], "rm -rf /")


if __name__ == "__main__":
    unittest.main()
