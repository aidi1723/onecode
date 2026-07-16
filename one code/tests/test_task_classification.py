import unittest


class TaskClassificationTests(unittest.TestCase):
    def test_common_project_requests_are_classified_with_reasons(self):
        from onecode.kernel.task_classification import classify_task_with_reason

        cases = {
            "写一个 hello.txt": ("change_task", "mutation_action_with_path"),
            "写文件 hello.txt 内容是 hi": ("change_task", "mutation_action_with_path"),
            "在项目根目录写个文件": ("change_task", "mutation_action_with_project_object"),
            "fix bug in main.py": ("change_task", "mutation_action_with_path"),
            "把这个 bug 修一下": ("change_task", "mutation_action_with_project_object"),
            "运行一下测试": ("change_task", "mutation_action_with_project_object"),
            "帮我看看这个仓库": ("read_task", "read_action_with_project_object"),
            "看看 src": ("read_task", "read_action_with_project_object"),
            "分析一下代码": ("read_task", "read_action_with_project_object"),
        }

        for text, expected in cases.items():
            with self.subTest(text=text):
                result = classify_task_with_reason(text)
                self.assertEqual((result.mode, result.reason), expected)

    def test_ambiguous_explanations_remain_chat(self):
        from onecode.kernel.task_classification import classify_task_with_reason

        for text in (
            "什么是文件系统",
            "解释一下 fix 这个词",
            "Write a brief explanation of tests",
        ):
            with self.subTest(text=text):
                result = classify_task_with_reason(text)
                self.assertEqual((result.mode, result.reason), ("chat", "default_chat"))

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

    def test_english_imperative_with_modifiers_is_change_task(self):
        from onecode.kernel.task_classification import classify_task

        self.assertEqual(
            classify_task(
                "Create exactly one file named safe-agent-final-smoke-20260713.txt "
                "in the project root with exact content: final approval smoke."
            ),
            "change_task",
        )

    def test_english_writing_question_without_project_action_is_chat(self):
        from onecode.kernel.task_classification import classify_task

        self.assertEqual(classify_task("Write a brief explanation of Safe-Agent-Skills."), "chat")

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
