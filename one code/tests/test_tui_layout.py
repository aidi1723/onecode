import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from onecode.tui.app import (
    API_KEY_WARNING,
    DEFAULT_ENDPOINT,
    DEFAULT_MODEL,
    DEFAULT_WORKSPACE,
    OneCodeApp,
    WelcomePanel,
)


class TuiLayoutTests(unittest.TestCase):
    def test_tui_defaults_support_single_command_startup(self):
        app = OneCodeApp()

        self.assertEqual(app.workspace, DEFAULT_WORKSPACE.resolve())
        self.assertEqual(app.model, DEFAULT_MODEL)
        self.assertEqual(app.endpoint, DEFAULT_ENDPOINT)

    def test_tui_can_select_domestic_provider_from_environment(self):
        with patch.dict(
            "os.environ",
            {
                "ONECODE_PROVIDER": "qwen",
                "DASHSCOPE_API_KEY": "dashscope-key",
            },
            clear=True,
        ):
            app = OneCodeApp()

        self.assertEqual(app.provider_kind, "qwen")
        self.assertEqual(app.model, "qwen-plus")
        self.assertEqual(
            app.endpoint,
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        )
        self.assertEqual(app.api_key, "dashscope-key")

    def test_welcome_panel_uses_onecode_branding_and_runtime_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {}, clear=True):
                app = OneCodeApp(workspace=Path(tmp), model="test-model")

            panel = WelcomePanel(app)
            text = str(panel.renderable)

            self.assertIn("一字诀 OneWord v0.1.0-alpha", text)
            self.assertIn("test-model", text)
            self.assertIn("接入大模型", text)
            self.assertIn("状态: 未配置 API 密钥", text)
            self.assertIn("运行路径", text)
            self.assertIn(str(Path(tmp).resolve()), text)
            self.assertIn("▄████▄", text)
            self.assertIn("○", text)
            self.assertIn("▀████▀", text)
            self.assertIn("快速开始", text)
            self.assertIn("输入 /help 查看一字诀指令与接入工具集", text)
            self.assertIn("最近活动", text)
            self.assertIn("暂无最近活动记录", text)
            self.assertNotIn("----", text)
            self.assertNotIn("--------------------------------------------------------------------------------", text)
            self.assertNotIn("Welcome back!", text)
            self.assertNotIn("#", text)
            self.assertNotIn("Claude Code", text)
            self.assertNotIn("Opus", text)
            self.assertNotIn("CLAUDE.md", text)

    def test_startup_copy_omits_prompt_suggestion_block(self):
        text = str(WelcomePanel(OneCodeApp()).renderable)

        self.assertNotIn('尝试输入 "重构 cli.py"', text)
        self.assertNotIn("输入 ? 查看快捷键", text)
        self.assertNotIn("/buddy", text)

    def test_missing_api_key_warning_uses_chinese_product_copy(self):
        self.assertEqual(
            API_KEY_WARNING,
            "提示: 未检测到 OPENAI_API_KEY。AI 对话功能已禁用，但本地接入命令仍可正常执行。",
        )

    def test_styles_define_startup_and_message_surfaces(self):
        css = Path("src/onecode/tui/styles.tcss").read_text(encoding="utf-8")

        for selector in [
            "WelcomePanel",
            "UserMessage",
            "AssistantMessage",
            "SystemMessage",
        ]:
            self.assertIn(selector, css)

        self.assertIn("#1f2633", css)
        self.assertIn("#f27954", css)
        self.assertIn("border", css)


class TuiRuntimeLayoutTests(unittest.IsolatedAsyncioTestCase):
    async def test_startup_widgets_mount_in_textual_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = OneCodeApp(workspace=Path(tmp), model="test-model")

            async with app.run_test() as pilot:
                self.assertTrue(app.query(WelcomePanel))
                self.assertFalse(app.query("PromptGuide"))
                self.assertIsNotNone(app.query_one("#input"))
                await pilot.pause()


if __name__ == "__main__":
    unittest.main()
