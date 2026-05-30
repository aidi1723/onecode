"""CLI entry point: launch the exchange HTTP server.

    python -m a2a_exchange            # serve on 127.0.0.1:8000
    A2A_HOST=0.0.0.0 A2A_PORT=9000 python -m a2a_exchange
"""
from __future__ import annotations

import os


def main() -> None:
    import uvicorn

    host = os.environ.get("A2A_HOST", "127.0.0.1")
    port = int(os.environ.get("A2A_PORT", "8000"))
    # SECURITY: binding to 0.0.0.0 exposes an unauthenticated exchange.
    uvicorn.run("a2a_exchange.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
