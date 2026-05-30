# Trusted A2A Capability Exchange

An experimental trust layer for agent-to-agent capability exchange.

This project is not trying to be another plugin store. It explores a lower-level
question: **can an autonomous agent decide whether another agent capability is
trustworthy enough to buy and use?**

The current prototype focuses on verifiable Python capabilities. A seller submits
a Python artifact, a machine-readable manifest, and a replayable eval pack. The
exchange runs the eval pack, produces a scorecard, exposes artifact-free listings,
locks purchase terms through a quote, and releases the artifact only after mock
credit debit and mock escrow creation.

## Why This Exists

Future agent ecosystems will need agent cores, plugins, tools, and workflows to
move between agents. A simple marketplace is not enough. Autonomous buyers need
answers to three questions before purchase:

1. **Trust:** Does this capability actually do what it claims?
2. **Control:** Can its permissions, runtime behavior, and cost be bounded?
3. **Settlement:** Is payment tied to verified delivery rather than a black-box
   download?

This repository is a small prototype of that trust and settlement layer.

## Current Prototype

Supported in v0.2:

- Python capability artifacts with a fixed `run(input: dict) -> dict` entrypoint.
- Replayable eval packs submitted at registration time.
- Subprocess verification with timeout limits.
- Machine-readable scorecards.
- Artifact-free discovery responses.
- Quote-locked price, artifact hash, and scorecard snapshots.
- Single-use checkout quotes.
- Mock buyer credit.
- Mock escrow with `held`, `released`, and `disputed` states.
- FastAPI HTTP interface.

Out of scope for this prototype:

- Production sandboxing.
- Real authentication.
- Real payments or clearing.
- Seller balances.
- Human marketplace UI.
- MCP, A2A, WASM, or full agent-core runtime support.
- Reputation beyond the generated scorecard.

## Architecture

```
src/a2a_exchange/
  manifest.py    capability, policy, scorecard, and listing models
  eval_pack.py   replayable verification case models
  verifier.py    subprocess-based Python artifact verification
  registry.py    thread-safe in-memory capability registry
  discovery.py   artifact-free discovery filters
  quote.py       version-locked, single-use quote book
  escrow.py      mock escrow state machine
  credit.py      mock static credit guard
  app.py         FastAPI HTTP surface and app factory
  __main__.py    uvicorn launcher
tests/
  test_exchange.py   trusted exchange flow tests
```

## API

| Method | Path                  | Actor  | Purpose                                      |
|--------|-----------------------|--------|----------------------------------------------|
| POST   | `/register`           | seller | Verify and list a Python capability          |
| POST   | `/discover`           | buyer  | Discover verified listings without artifacts |
| POST   | `/quote`              | buyer  | Lock price, artifact hash, and scorecard     |
| POST   | `/checkout`           | buyer  | Debit mock credit and unlock artifact        |
| POST   | `/settle`             | buyer  | Release or dispute mock escrow               |
| GET    | `/balance/{agent_id}` | buyer  | Inspect mock credit                          |
| GET    | `/healthz`            | -      | Liveness plus listing, quote, escrow counts  |

## Quick Start

```bash
git clone <repo-url>
cd <repo-dir>
pip install -e '.[dev]'
python -m a2a_exchange
```

Open the interactive API docs:

```text
http://127.0.0.1:8000/docs
```

Run tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Example Capability

Register a simple capability that uppercases text:

```json
{
  "manifest": {
    "name": "uppercase-tool",
    "interface": {
      "input_schema": {
        "type": "object",
        "properties": {
          "text": { "type": "string" }
        },
        "required": ["text"]
      },
      "output_schema": {
        "type": "object",
        "properties": {
          "upper": { "type": "string" }
        },
        "required": ["upper"]
      }
    },
    "price_tokens": 500,
    "permission_policy": {
      "network": false,
      "filesystem": false
    },
    "description": "Converts text to uppercase."
  },
  "artifact": "def run(input):\n    return {\"upper\": input[\"text\"].upper()}",
  "eval_pack": {
    "cases": [
      {
        "name": "hello uppercase",
        "input": { "text": "hello" },
        "expected_output": { "upper": "HELLO" }
      }
    ]
  },
  "sandbox_policy": {
    "network": false,
    "timeout_ms": 1000,
    "max_cases": 5
  }
}
```

The exchange verifies the artifact and returns a scorecard. Buyers discover the
listing without receiving the artifact, create a quote, then checkout with the
quote ID.

## Security Boundary

This project is **not safe for public execution of untrusted code**.

The verifier runs submitted Python in a subprocess with timeout controls. That is
useful for local experiments, but it is not a real sandbox. Run only locally or
on an isolated network.

Known prototype limitations:

- No authentication. `agent_id` is self-reported.
- Mock credit can be minted by claiming a new agent ID.
- Mock escrow records settlement state but does not transfer real value.
- Python artifacts are plain source strings.
- The verifier blocks network and filesystem only by policy declaration, not by
  a hardened runtime boundary.

## Roadmap

Near-term:

- Stronger execution isolation: container, WASM, or microVM verifier.
- Persistent registry, quote, and escrow storage.
- API-key or token authentication.
- Human governance console for publishing, review, budgets, and risk policy.

Research direction:

- Capability provenance and identity.
- Reputation from verified usage outcomes.
- Escrow release tied to post-purchase acceptance tests.
- MCP/A2A adapter support.
- Cost and permission proofs that buyer agents can evaluate automatically.

## Project Status

Prototype. The goal is to test the trust model, not to provide production
infrastructure.
