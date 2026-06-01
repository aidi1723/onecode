# OneWord Terminal TUI Design

Date: 2026-05-28
Project root: `/Users/aidi/大字典/one code`
Status: Approved for implementation planning

## Goal

Restyle the Textual chat interface so the startup screen and message flow match the provided Chinese OneWord terminal layout while preserving command routing and kernel behavior.

## Boundary

This change is UI-only. It may modify `src/onecode/tui/app.py`, `src/onecode/tui/styles.tcss`, and focused tests/docs. It must not change kernel execution, command routing, model provider behavior, path permissions, or run evidence formats.

## Design Source

Use `DESIGN.md` as the visual contract. The reference defines the layout rhythm: dark terminal canvas, orange welcome frame, colorful circular ring logo, Chinese startup copy, horizontal prompt separators, muted helper text, and compact monospace density. Product copy must be 一字诀 OneWord-specific.

## Architecture

The implementation remains a Python Textual app. Add focused widgets/helpers for the welcome panel, then style them through `styles.tcss`.

Planned UI units:

- `WelcomePanel`: a static startup frame containing OneWord version, colorful circular ring logo, workspace, model/API status, quick-start copy, and recent activity.
- Existing message widgets: keep `UserMessage`, `AssistantMessage`, `SystemMessage`, and `Divider`, but restyle them to match the terminal surface.

## Data Flow

On mount:

```text
OneCodeApp.on_mount()
  -> mount WelcomePanel into #chat-log
  -> show missing API key warning only if needed
  -> focus input
```

On user input:

```text
submitted text
  -> append UserMessage
  -> route through existing command/chat/task handlers
  -> append AssistantMessage or SystemMessage from existing result handlers
```

## Error Handling

Existing error handling remains. API-key warnings and worker errors should use `SystemMessage` with warning/error styling and should not replace or remove the welcome panel.

## Testing

Add focused tests that instantiate `OneCodeApp` and verify:

- startup state creates a `WelcomePanel` containing OneWord-specific Chinese copy, the model, colorful circular ring logo, and workspace;
- startup does not mount a prompt suggestion block or `/buddy` copy;
- no startup helper copy references Claude Code, Opus, or CLAUDE.md.

Existing TUI model routing tests must continue to pass.

## Acceptance Criteria

- `python3 -m unittest tests.test_tui_layout -v` passes.
- `python3 -m unittest tests.test_tui_model_closure -v` passes.
- `python3 -m compileall src tests` passes.
- The startup screen visually follows the approved OneWord Chinese terminal direction.
- Existing chat, command, and kernel behaviors are preserved.
