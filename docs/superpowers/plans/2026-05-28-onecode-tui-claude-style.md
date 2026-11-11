# OneCode Claude-Style TUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a OneCode-branded Textual chat interface that matches the approved Claude Code-style startup and message layout.

**Architecture:** Keep the existing Textual app and kernel routing intact. Add small presentational helpers/widgets in `src/onecode/tui/app.py`, restyle them in `src/onecode/tui/styles.tcss`, and cover the startup copy/layout contract with focused unit tests.

**Tech Stack:** Python 3.11+, Textual, unittest.

---

## File Structure

- Modify `src/onecode/tui/app.py`: add `APP_VERSION`, `WelcomePanel`, helper methods for startup text, and mount the welcome panel from `on_mount`.
- Modify `src/onecode/tui/styles.tcss`: define the dark terminal canvas, orange welcome frame, and refined message styles.
- Create `tests/test_tui_layout.py`: verify startup copy, OneWord branding, omitted prompt-suggestion block, and forbidden screenshot-brand copy exclusions.
- Create `DESIGN.md`: visual source of truth for future UI changes.
- Create `docs/superpowers/specs/2026-05-28-onecode-tui-claude-style-design.md`: approved design specification.

## Task 1: Startup Layout Contract

**Files:**
- Create: `tests/test_tui_layout.py`
- Modify: `src/onecode/tui/app.py`

- [ ] **Step 1: Write the failing test**

```python
import tempfile
import unittest
from pathlib import Path

from onecode.tui.app import OneCodeApp, WelcomePanel


class TuiLayoutTests(unittest.TestCase):
    def test_welcome_panel_uses_onecode_branding_and_runtime_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = OneCodeApp(workspace=Path(tmp), model="test-model")

            panel = WelcomePanel(app)
            text = str(panel.renderable)

            self.assertIn("OneCode v0.1.0-alpha", text)
            self.assertIn("Welcome back!", text)
            self.assertIn("test-model", text)
            self.assertIn(str(Path(tmp).resolve()), text)
            self.assertIn("Tips for getting started", text)
            self.assertIn("Recent activity", text)
            self.assertIn("No recent activity", text)
            self.assertNotIn("Claude Code", text)
            self.assertNotIn("Opus", text)
            self.assertNotIn("CLAUDE.md", text)

    def test_startup_copy_omits_prompt_suggestion_block(self):
        text = str(WelcomePanel(OneCodeApp()).renderable)

        self.assertNotIn('尝试输入 "重构 cli.py"', text)
        self.assertNotIn("输入 ? 查看快捷键", text)
        self.assertNotIn("/buddy", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m unittest tests.test_tui_layout -v`

Expected: FAIL with missing or outdated welcome-panel copy.

- [ ] **Step 3: Write minimal implementation**

Add `APP_VERSION = "0.1.0-alpha"` near the TUI config. Add a `WelcomePanel` class that inherits `Static` and renders OneWord-specific copy. Mount it at the start of `on_mount` before warnings. Keep all existing handlers unchanged.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python3 -m unittest tests.test_tui_layout -v`

Expected: PASS.

## Task 2: Terminal Styling

**Files:**
- Modify: `src/onecode/tui/styles.tcss`
- Test: `tests/test_tui_layout.py`

- [ ] **Step 1: Write the failing test**

Extend `tests/test_tui_layout.py` with:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m unittest tests.test_tui_layout -v`

Expected: FAIL because `WelcomePanel` or the target color tokens are not in the stylesheet.

- [ ] **Step 3: Write minimal implementation**

Update `styles.tcss` so `Screen`, `#chat-log`, `WelcomePanel`, messages, input, and footer use the approved dark terminal palette, orange borders, compact spacing, visible focus, and muted status text.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python3 -m unittest tests.test_tui_layout -v`

Expected: PASS.

## Task 3: Preserve Existing TUI Behavior

**Files:**
- Modify: `src/onecode/tui/app.py`
- Test: `tests/test_tui_model_closure.py`

- [ ] **Step 1: Run existing focused behavior test**

Run: `PYTHONPATH=src python3 -m unittest tests.test_tui_model_closure -v`

Expected: PASS. If it fails, fix only regressions introduced by the layout change.

- [ ] **Step 2: Run compile check**

Run: `python3 -m compileall src tests`

Expected: PASS.

- [ ] **Step 3: Run full local verification if focused checks pass**

Run: `bash scripts/verify.sh`

Expected: PASS.

## Self-Review

- Spec coverage: tasks cover startup panel, omitted prompt-suggestion block, chat message styling, forbidden screenshot-brand copy, and behavior preservation.
- Placeholder scan: no placeholders or deferred implementation notes remain.
- Type consistency: tests import `WelcomePanel`, planned as a `Static` subclass with renderable text.
