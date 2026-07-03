from __future__ import annotations


def gateway_console_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OneCode Shell</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #101010;
      --panel: #171717;
      --panel-2: #202020;
      --text: #f2f0ec;
      --muted: #a8a29a;
      --accent: #f59e0b;
      --accent-2: #38bdf8;
      --danger: #fb7185;
      --border: #3f3a33;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.55 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
    main {
      width: min(980px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 32px 0;
    }
    .shell {
      border: 1px solid var(--accent);
      background: var(--panel);
      padding: 20px;
    }
    header {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      border-bottom: 1px solid var(--border);
      padding-bottom: 16px;
      margin-bottom: 18px;
    }
    h1 {
      margin: 0 0 6px;
      font-size: 22px;
      font-weight: 700;
      letter-spacing: 0;
    }
    .muted { color: var(--muted); }
    .badge {
      border: 1px solid var(--border);
      background: var(--panel-2);
      color: var(--accent);
      padding: 4px 8px;
      white-space: nowrap;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }
    label {
      display: block;
      color: var(--muted);
      margin-bottom: 6px;
    }
    textarea, pre {
      width: 100%;
      min-height: 170px;
      margin: 0;
      border: 1px solid var(--border);
      background: #0b0b0b;
      color: var(--text);
      padding: 12px;
      font: inherit;
      overflow: auto;
    }
    textarea { resize: vertical; }
    .actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin: 14px 0;
    }
    button, a.button {
      border: 1px solid var(--accent);
      background: var(--accent);
      color: #1c1203;
      padding: 9px 12px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      text-decoration: none;
    }
    button.secondary, a.button.secondary {
      background: transparent;
      color: var(--accent);
    }
    .status {
      min-height: 24px;
      color: var(--accent-2);
    }
    .danger { color: var(--danger); }
    @media (max-width: 760px) {
      header { display: block; }
      .badge { display: inline-block; margin-top: 10px; }
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main>
    <section class="shell">
      <header>
        <div>
          <h1>OneCode Shell</h1>
          <div class="muted">Bundled browser shell for the deterministic OneCode execution kernel.</div>
        </div>
        <div class="badge">service: ok</div>
      </header>
      <div class="grid">
        <div>
          <label for="input">Candidate input</label>
          <textarea id="input">User: handle this project safely
Model candidate: ALLOW_PATCH_WITH_SHA</textarea>
        </div>
        <div>
          <label for="result">Kernel result</label>
          <pre id="result">Click "Run demo adjudication" to inspect a deterministic kernel decision.</pre>
        </div>
      </div>
      <div class="actions">
        <button id="demo" type="button">Run demo adjudication</button>
        <a class="button secondary" href="/v1/onecode/gateway/adjudicate?demo=1">Open JSON demo</a>
        <a class="button secondary" href="/health">Health check</a>
      </div>
      <div id="status" class="status">POST /v1/onecode/gateway/adjudicate</div>
    </section>
  </main>
  <script>
    const result = document.getElementById('result');
    const status = document.getElementById('status');
    document.getElementById('demo').addEventListener('click', async () => {
      status.textContent = 'running...';
      try {
        const response = await fetch('/v1/onecode/gateway/adjudicate?demo=1');
        const payload = await response.json();
        result.textContent = JSON.stringify(payload, null, 2);
        status.textContent = payload.changed ? 'changed: true' : 'changed: false';
      } catch (error) {
        status.textContent = 'request failed';
        status.className = 'status danger';
        result.textContent = String(error);
      }
    });
  </script>
</body>
</html>
"""
