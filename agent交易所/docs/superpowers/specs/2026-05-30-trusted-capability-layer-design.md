# Trusted Capability Trading Layer Design

Date: 2026-05-30
Project: A2A Capability Exchange
Status: approved for implementation planning

## Purpose

The project should move from a generic capability marketplace to a trusted
capability trading layer. The first useful product claim is not that agents can
list, search, and buy artifacts over HTTP. The useful claim is that a buyer
agent can inspect machine-readable evidence before purchase, lock the terms of
the purchase, and receive the artifact only after a controlled checkout flow.

The first version remains a local / isolated-network prototype. It is designed
to test the trust and transaction model, not to provide production-grade code
isolation or public-network security.

## First Trading Object

The first supported object is a Verified Python Capability:

- The seller submits Python source code as an artifact.
- The artifact must expose `run(input: dict) -> dict`.
- The seller submits a manifest with name, input schema, output schema, price,
  permission policy, and descriptive metadata.
- The seller submits an `eval_pack` containing replayable test cases.
- The exchange executes the eval pack before making the capability purchasable.

MCP servers, WASM modules, HTTP tools, full agent cores, real payment rails, and
public marketplace UI are explicitly out of scope for this version.

## Capability Model

`RegisterCapabilityRequest` contains:

- `manifest`: capability name, interface schema, price, and permission policy.
- `artifact`: Python source code string.
- `eval_pack`: test cases with `input` and `expected_output`.
- `sandbox_policy`: lightweight limits such as `network=false`, `timeout_ms`,
  and `max_cases`.

The exchange computes `artifact_sha256` from the submitted artifact. This hash is
the canonical version identifier and is used by quotes and checkout. Sellers do
not provide their own `capability_id`.

`Scorecard` contains:

- `verified`: true only when all required eval cases pass.
- `pass_rate`.
- `cases_total`.
- `cases_passed`.
- `avg_latency_ms`.
- `artifact_sha256`.
- per-case results with pass/fail, duration, and error text.

Only verified capabilities are returned as purchasable listings in the default
discovery path.

## Verification Flow

Registration is no longer a pure save operation:

1. Receive manifest, artifact, eval pack, and sandbox policy.
2. Compute `artifact_sha256`.
3. Confirm the artifact exposes a callable `run` entrypoint.
4. Execute each eval case in a subprocess with a timeout.
5. Compare the output to the expected output.
6. Generate a scorecard.
7. Store the capability and scorecard.
8. Mark it purchasable only when `verified=true`.

The subprocess executor is a lightweight boundary for the prototype. It is not a
security sandbox against malicious code. The design must keep the verifier
module isolated so a stronger executor can replace it later.

## Discovery Flow

`POST /discover` accepts filters such as:

- `required_input_keys`.
- `max_price`.
- `min_pass_rate`.
- `max_latency_ms`.
- `verified_only`, defaulting to true.

The response is `CapabilityListing[]`. A listing includes the capability id,
name, price, interface, scorecard, and permission policy. It must not include the
artifact.

This fixes the current prototype's main marketplace flaw: discovery cannot leak
the thing that checkout is supposed to unlock.

## Quote Flow

`POST /quote` accepts:

- `buyer_agent_id`.
- `capability_id`.

It returns a `Quote` with:

- `quote_id`.
- `buyer_agent_id`.
- `capability_id`.
- `artifact_sha256`.
- `price_tokens`.
- `scorecard_snapshot`.
- `expires_at`.

Checkout must use a quote instead of buying directly by `capability_id`. This
locks price, artifact version, and verified quality evidence for the buyer.

## Checkout and Escrow Flow

`POST /checkout` accepts `quote_id`.

The exchange:

1. Validates that the quote exists and has not expired.
2. Loads the exact capability version bound to the quote.
3. Debits the buyer's mock credit balance.
4. Creates an escrow record.
5. Returns the artifact, `escrow_id`, and remaining buyer balance.

The first version still uses mock credit, but the transaction semantics should
be escrow-shaped rather than a direct purchase. This keeps the model aligned
with future settlement, dispute, and refund behavior.

`POST /settle` accepts:

- `buyer_agent_id`.
- `escrow_id`.
- `accepted`.

If `accepted=true`, the escrow status becomes `released`. If `accepted=false`,
the status becomes `disputed`. The prototype does not perform real seller
settlement, arbitration, or refunds.

## API Surface

- `POST /register`: register and verify a capability.
- `POST /discover`: discover verified listings without artifact leakage.
- `POST /quote`: create a version-locked purchase quote.
- `POST /checkout`: debit mock credit, create escrow, and release artifact.
- `POST /settle`: mark escrow as released or disputed.
- `GET /balance/{agent_id}`: inspect mock buyer credit.
- `GET /healthz`: return service status plus listing, quote, and escrow counts.

## Module Boundaries

The implementation should keep modules small and replaceable:

- `manifest.py`: manifest, interface, policy, and scorecard models.
- `eval_pack.py`: eval case and eval pack models.
- `verifier.py`: subprocess execution of `artifact.run(input)` and scorecard
  generation.
- `registry.py`: storage for verified capabilities and their scorecards.
- `discovery.py`: listing filters and artifact-free discovery responses.
- `quote.py`: quote creation, expiration, and version locking.
- `escrow.py`: mock escrow state machine.
- `credit.py`: mock buyer credit debit.
- `app.py`: FastAPI routing and app factory wiring.

## Non-Goals

- No production sandboxing.
- No public-network authentication.
- No real payment provider.
- No seller balance ledger.
- No human marketplace UI.
- No MCP / A2A / WASM runtime support.
- No semantic embedding-based discovery.
- No reputation system beyond the generated scorecard.

## Required Tests

The implementation must cover:

- Successful registration creates a scorecard.
- A failing eval pack prevents the capability from being purchasable by default.
- Discovery never returns `artifact`.
- Discovery filters by price and scorecard constraints.
- Quotes lock price, artifact hash, and scorecard snapshot.
- Checkout requires a valid unexpired quote.
- Checkout debits buyer credit and returns the artifact only after debit.
- Settlement moves escrow to `released` or `disputed`.
- Empty or malformed artifacts cannot bypass verification.
- Re-registering a capability cannot invalidate an existing quote's locked
  artifact hash or price.

## Security Boundary

This version is safe only for local or isolated-network experimentation. It runs
untrusted Python in a subprocess with timeout controls, which is not a real
sandbox. The design intentionally keeps the verifier boundary explicit so later
versions can replace it with container, WASM, or microVM execution without
rewriting marketplace logic.
