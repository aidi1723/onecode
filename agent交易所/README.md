# Trusted A2A Capability Exchange (v0.2 prototype)

A machine-first trusted capability trading layer where autonomous agents can
publish Python capabilities with replayable eval packs, receive a machine-readable
scorecard, and sell access through quote-locked checkout and mock escrow.

This is not a production sandbox or public marketplace. It is a local prototype
for testing whether buyer agents can evaluate capability evidence before paying.

## Layout

```
src/a2a_exchange/
  manifest.py    capability, policy, scorecard, and listing models
  eval_pack.py   replayable verification case models
  verifier.py    subprocess-based Python artifact verification
  registry.py    thread-safe in-memory capability registry
  discovery.py   artifact-free discovery filters
  quote.py       version-locked quote book
  escrow.py      mock escrow state machine
  credit.py      mock static credit guard
  app.py         FastAPI HTTP surface + app factory
  __main__.py    uvicorn launcher
tests/
  test_exchange.py   trusted exchange flow tests
```

## Endpoints

| Method | Path                  | Actor  | Purpose                                      |
|--------|-----------------------|--------|----------------------------------------------|
| POST   | `/register`           | seller | verify and list a Python capability          |
| POST   | `/discover`           | buyer  | discover verified listings without artifacts |
| POST   | `/quote`              | buyer  | lock price, artifact hash, and scorecard     |
| POST   | `/checkout`           | buyer  | debit mock credit and unlock artifact        |
| POST   | `/settle`             | buyer  | release or dispute mock escrow               |
| GET    | `/balance/{agent_id}` | buyer  | inspect mock credit                          |
| GET    | `/healthz`            | -      | liveness plus listing, quote, escrow counts  |

## Run

```bash
pip install -e .
python -m a2a_exchange
# A2A_HOST=0.0.0.0 A2A_PORT=9000 python -m a2a_exchange
```

Interactive schema docs are available at `http://127.0.0.1:8000/docs`.

## Test

```bash
pip install -e '.[dev]'
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Security status

The verifier runs untrusted Python in a subprocess with timeouts. This is not a
security sandbox. Run only locally or on an isolated network.

- **No authentication.** `agent_id` is self-reported; any caller can mint a fresh
  mock balance by claiming a new ID.
- Mock credit and mock escrow are prototype transaction semantics, not real
  settlement.
- Discovery responses do not include artifacts; checkout releases artifacts only
  after quote validation, debit, and escrow creation.
