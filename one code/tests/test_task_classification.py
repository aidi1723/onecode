import unittest


class TaskClassificationTests(unittest.TestCase):
    def test_natural_project_check_is_read_task(self):
        from onecode.kernel.task_classification import classify_task

        self.assertEqual(classify_task("检查当前项目是否集成了 safe-agent-skills"), "read_task")

    def test_question_requesting_inspection_is_read_task(self):
        from onecode.kernel.task_classification import classify_task

        self.assertEqual(classify_task("你能检查一下 src/onecode 吗？"), "read_task")

    def test_mutation_and_install_are_change_tasks(self):
        from onecode.kernel.task_classification import classify_task

        self.assertEqual(classify_task("修改 README.md"), "change_task")
        self.assertEqual(classify_task("安装项目依赖"), "change_task")

    def test_explanatory_question_is_chat(self):
        from onecode.kernel.task_classification import classify_task

        self.assertEqual(classify_task("什么是 Safe-Agent-Skills？"), "chat")

    def test_explicit_valid_mode_overrides_inference(self):
        from onecode.kernel.task_classification import classify_task

        self.assertEqual(classify_task("解释 README.md", explicit_mode="chat"), "chat")

    def test_invalid_explicit_mode_is_rejected(self):
        from onecode.kernel.task_classification import classify_task

        with self.assertRaisesRegex(ValueError, "onecode_mode"):
            classify_task("检查项目", explicit_mode="automatic")


if __name__ == "__main__":
    unittest.main()
