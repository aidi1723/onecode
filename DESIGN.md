# OneWord Interface Design

Date: 2026-05-28
Scope: `src/onecode/tui`, `src/onecode/web`
Status: Approved visual direction

## Source

The TUI is inspired by the provided terminal welcome-screen references, but all product content must read as 一字诀 OneWord. The Web Gateway must use the same product language and shared dark terminal palette. Do not show Claude Code, Opus, CLAUDE.md, or `/buddy` copy in the OneWord interface.

## Visual Language

- Dark terminal canvas with warm orange accents and muted gray secondary text.
- Monospace-first typography, compact density, and rectangular terminal framing.
- Thin orange borders for the welcome frame and vertical divider.
- Welcome content should not use long horizontal divider rules inside the panel.
- Text should feel like a practical Chinese terminal tool, not a marketing page.
- The logo is a compact colorful circular ring made from terminal block characters.

## Startup Layout

The first screen should show a welcome panel at the top of the chat log:

- Header: `一字诀 OneWord v0.1.0-alpha`
- Left column: colorful circular ring logo.
- Right column: `接入大模型`, API-key status, `运行路径`, `快速开始`, and `最近活动`.
- Quick-start copy: `输入 /help 查看一字诀指令与接入工具集`.
- Empty activity copy: `暂无最近活动记录`.

## Chat Layout

- User messages use a leading prompt marker and bold/high-contrast text.
- Assistant messages use a quiet left border or framed terminal surface, not a heavy card.
- System/status messages remain muted and compact.
- Result summaries keep existing semantic colors for success, warning, and error.
- Chat behavior, command routing, model calls, kernel execution, and workspace semantics must remain unchanged.
- Missing API key warning: `提示: 未检测到 OPENAI_API_KEY。AI 对话功能已禁用，但本地接入命令仍可正常执行。`

## Responsive Behavior

The TUI must remain readable in narrow terminal widths. The welcome content can stack or truncate gracefully, but it must not break command input or hide the footer.

## Implementation Base

Use the existing Python Textual application. Restyle and extend the current widgets instead of replacing the TUI framework or changing kernel logic.

## Web Gateway

The local Web Gateway is a compact operator console, not a marketing page. It should use the shared dark terminal palette, warm orange primary accent, muted secondary text, rectangular surfaces, and monospace typography from the TUI.

- Keep the first viewport focused on the adjudication tool: input, result, actions, and service status.
- Use restrained borders and flat surfaces instead of card stacks, glow effects, or decorative gradients.
- Keep labels concise and operational. Copy should explain state and action, not advertise features.
- Preserve the current API behavior, route shape, authentication boundary, and local preview semantics.
- If HTML remains inline HTML inside `src/onecode/web/api.py`, keep the markup small and covered by tests. If it grows beyond a compact console, move the page to a dedicated template/static asset layer before adding more UI states.
