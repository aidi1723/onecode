# OneCode Evidence Chain And Manifest Complexity Balance Design

## Problem

OneCode uses evidence-chain logging to make local agent work verifiable. That is necessary for Verifiable Outcomes, but it creates a predictable failure mode: if every API orchestration step, scheduler heartbeat, state transition, verifier observation, and local node handoff is recorded as full audit evidence, the metadata stream can become larger and more latency-sensitive than the work being executed.

The bias to avoid is treating "verifiable" as "record everything synchronously forever." That turns auditability into an I/O bottleneck and makes the local compute cluster less reliable under load.

There is a second, related failure mode: if OneCode is asked to own complex business state transitions directly, `manifest.json` can expand from a compact run evidence index into a business workflow configuration surface. Order, approval, settlement, fulfillment, callback, compensation, permission, and exception states can multiply until the manifest is no longer an audit manifest. It becomes a brittle process engine encoded as metadata.

These two problems share the same root cause: confusing proof of execution with ownership of all runtime and business semantics.

## Decision

OneCode should use risk-tiered evidence capture instead of full audit by default.

The invariant is: every externally meaningful outcome must remain provable. The system does not need full payload-level audit for every low-risk internal transition when a compact, hash-linked, replayable, or sampled record is enough to prove the transition class and preserve causal order.

OneCode should also keep `manifest.json` as an execution manifest, not a business state machine. Complex business flows must live in a domain model or workflow layer outside the manifest. The manifest records a minimal, verifiable projection of those flows: action identity, input/output digests, evidence references, state projection codes, policy identity, and recovery points.

## Non-Goals

This design does not:

- remove WAL, trace, checkpoint, manifest, or ledger evidence
- allow unrecorded unsafe writes, verifier execution, approval decisions, or workspace-boundary events
- weaken resume correctness for completed assets or task-level closure
- optimize by dropping evidence required for delivery, repair, or incident review
- introduce opaque sampling that makes a run impossible to explain
- turn `manifest.json` into a configurable business process engine
- encode domain-specific order, approval, settlement, or fulfillment state machines inside OneCode core
- make OneCode responsible for deciding business correctness beyond declared execution contracts

## Next Problems To Solve

OneCode should treat the following as explicit architecture work before adding richer orchestration or multi-node scheduling.

### Problem 1: Evidence Density Can Break Runtime Performance

Full evidence for every event gives a strong audit story, but it can overload local storage and add latency to the critical path. The solution is risk-tiered evidence capture:

- keep critical trust decisions full and commit-coupled
- compact normal internal transitions
- aggregate repeated low-risk liveness events
- defer bulky artifacts behind content hashes
- escalate to full evidence when anomalies appear

### Problem 2: Manifest Scope Can Explode Under Business Workflows

Complex business state flows can turn the manifest into a dumping ground for domain rules. The solution is a manifest boundary:

- business state machines own business semantics
- OneCode owns execution, evidence, recovery, verifier results, and delivery closure
- the manifest stores only the verifiable projection of a business decision
- large domain payloads are referenced by digest and schema id, not embedded as mutable branching config
- resume uses execution evidence, not inferred business workflow intent

These two solutions should be implemented together because both require explicit event classification, schema boundaries, and proof contracts.

## Risk Tiers

Evidence capture should classify runtime events into four tiers.

| Tier | Event examples | Required evidence | Write path |
| --- | --- | --- | --- |
| Critical | approval grant/deny, permission boundary decision, external side effect, asset write, patch application, verifier result, resume conflict, final delivery state | full structured event, payload digest, before/after hashes where applicable, actor, policy, trace id, run id, duration, status, hash-chain link | synchronous or commit-coupled |
| High | node ownership transfer, retry exhaustion, repair attempt, sandbox deny, model/tool boundary decision | structured event, compact payload, digest, causal parent, status, timing | synchronous for decision record, async for bulky tails |
| Medium | normal scheduler transition, successful internal API orchestration, cache hit/miss affecting execution, non-mutating inspection | compact envelope, state code, parent span, counters, payload digest, optional sampled detail | buffered async |
| Low | heartbeat, progress tick, repeated stable poll, idempotent no-op, local queue visibility update | aggregate counter, rolling digest, last timestamp, sample only on anomaly | coalesced or sampled |

Critical and high-risk records protect trust decisions. Medium and low-risk records protect observability without forcing the whole runtime to pay full audit cost.

## Evidence Modes

Each trace or WAL event should carry an evidence mode:

- `full`: complete structured event body with all required audit fields.
- `compact`: schema-stable envelope plus hashes or digests of bulky fields.
- `aggregate`: count, first timestamp, last timestamp, status distribution, and rolling digest for repeated equivalent events.
- `sampled`: compact record for every event plus full detail only for deterministic sampling windows or anomaly triggers.
- `deferred`: full detail is written out-of-band and referenced by digest from the synchronous record.

The mode must be explicit in the event. A reader should never have to infer whether missing fields were intentionally compacted or accidentally omitted.

## Default Policy

Default capture policy:

| Event family | Default mode | Escalation trigger |
| --- | --- | --- |
| approvals and permission matrix decisions | `full` | always full |
| path guard, sandbox, and sovereignty decisions | `full` | always full |
| physical writes and patches | `full` | always full |
| verifier execution result | `full` for exit code, hashes, timing; `deferred` for long output tails | non-zero exit, timeout, policy mismatch |
| task finalization and resume classification | `full` | always full |
| model/tool dispatch decision | `compact` | denial, retry, repair, policy boundary |
| scheduler state transition | `compact` | repeated failure, latency threshold, ownership transfer |
| heartbeat and progress tick | `aggregate` | missed heartbeat, stalled duration, status flip |
| repeated successful non-mutating inspection | `sampled` | new path, hash mismatch, unexpected output |

The runtime should fail closed when it cannot classify an event. Unknown event families are recorded as `full` until policy is updated.

## Runtime Shape

The implementation should keep the synchronous path short:

1. Classify the event family and risk tier before writing.
2. Write critical trust evidence synchronously to the WAL or run ledger.
3. For compact events, write a schema-stable envelope with `event_type`, `risk_tier`, `evidence_mode`, `trace_id`, `run_id`, `span_id`, `parent_span_id`, `status`, `duration_ms`, `payload_digest`, and the minimal state payload.
4. Coalesce low-risk repeated events in memory and flush aggregate records on interval, status change, run completion, or process shutdown.
5. Store bulky verifier output, model observations, and diagnostic tails as deferred artifacts referenced by content hash.
6. Escalate future records for a run from `compact` or `aggregate` to `full` when anomaly triggers fire.

This keeps the proof chain intact while preventing metadata from dominating local disk I/O.

## Manifest Boundary

`manifest.json` should remain a run-level evidence index. Its job is to answer:

- what run produced this evidence
- which checkpoints and artifacts exist
- which assets were written, patched, skipped, or resumed
- which verifier and policy decisions were used
- which trace, WAL, and ledger records prove the run
- what final execution state was reached

It should not answer:

- what all possible business states are
- which business transition is legal in every domain scenario
- how compensation, settlement, fulfillment, or approval workflows branch
- how external systems should interpret domain-specific lifecycle meaning

The manifest may record a business state projection, but only as bounded evidence:

```json
{
  "domain_projection": {
    "schema_id": "order-workflow/v3",
    "entity_id_hash": "sha256:...",
    "from_state": "payment_authorized",
    "to_state": "fulfillment_requested",
    "decision_id": "workflow-decision-018",
    "decision_hash": "sha256:...",
    "evidence_refs": [
      "trace:span-123",
      "wal:global-ledger:456"
    ]
  }
}
```

The manifest records that OneCode executed and proved a declared transition. It does not define the transition matrix.

## Layered Solution

The durable architecture should separate three layers.

| Layer | Owns | Must not own |
| --- | --- | --- |
| Business domain / workflow layer | domain states, transition legality, compensation rules, external lifecycle semantics | local execution proof, checkpoint storage, WAL hash-chain integrity |
| OneCode execution layer | actions, permissions, tool calls, checkpoints, verifier results, recovery, evidence modes | domain-specific process policy |
| Manifest projection layer | compact run summary, artifact refs, digests, state projections, delivery closure | full business workflow graph or large mutable domain payloads |

This keeps OneCode useful for complex business systems without making OneCode core absorb every business rule.

## Manifest Complexity Guardrails

The manifest should have hard design limits:

- It stores references and digests for large payloads, not full domain documents.
- It stores current projection and evidence references, not all possible transitions.
- It uses schema ids for domain projections so old manifests remain interpretable.
- It records policy identity and decision hash, not the full policy source unless that policy is an execution policy.
- It keeps append-only checkpoint references separate from domain workflow history.
- It rejects unknown manifest sections unless they are namespaced under an explicit extension key.
- It keeps resume-critical fields stable and independent from optional domain projections.

If a new feature needs dozens of business states or branch-specific fields in the manifest, that feature belongs in a workflow/domain schema and should only project a compact proof into OneCode.

## Combined Data Flow

The intended flow for complex business orchestration is:

1. The business workflow layer decides the desired transition and emits a decision id, schema id, and digestable decision payload.
2. OneCode validates the requested execution contract, permissions, paths, tools, verifier policy, and risk tier.
3. OneCode executes the bounded local action.
4. Critical execution evidence is recorded in full; low-risk internal runtime evidence follows the risk-tiered evidence policy.
5. The manifest receives checkpoint refs, artifact hashes, final execution state, and an optional domain projection.
6. Resume reads manifest and WAL evidence to decide execution recovery, then asks the business layer to revalidate domain intent when business meaning is required.

This prevents both metadata I/O overload and manifest business-rule overload.

## Resume And Audit Semantics

Resume logic must only depend on evidence that is guaranteed to exist:

- asset writes and patches use full checkpoint and hash evidence
- verifier outcomes use full status, command identity, cwd, exit code, duration, and output hash evidence
- task finalization uses full transition and delivery evidence
- compact scheduler events can explain ordering but must not be the only proof that a mutation completed
- aggregate heartbeat records can prove liveness windows but not semantic completion

If resume needs a field that was compacted away, the event was assigned the wrong tier. The fix is to reclassify the event family, not to teach resume to guess.

## Backpressure

Evidence logging needs explicit backpressure behavior:

- Critical evidence writes block the operation they prove.
- High-risk evidence can block the risk decision but should defer bulky artifacts.
- Medium-risk buffers have byte and time limits; overflow escalates to compact lossless envelopes, not silent drops.
- Low-risk aggregates may drop individual samples after preserving count, time range, status distribution, and rolling digest.
- If WAL or ledger writes fail for critical evidence, execution halts before claiming completion.

This makes the failure mode visible and prevents false Verifiable Outcomes.

## Schema Evolution

Both evidence events and manifest projections need explicit schema evolution:

- `manifest_schema_version` covers OneCode execution evidence shape.
- `domain_projection.schema_id` covers external business meaning.
- Critical resume fields stay backward-compatible across minor versions.
- Unknown domain projections are preserved for audit display but ignored for execution recovery.
- A migration may add derived indexes, but it must not rewrite historical proof fields without preserving original hashes.

This gives old runs a stable audit meaning even when business workflows change.

## Metrics

The runtime should expose or record these metrics per run:

- evidence bytes written by risk tier and evidence mode
- synchronous evidence write latency p50, p95, and max
- number of compacted, aggregated, sampled, and deferred events
- number of escalation triggers
- dropped low-risk samples with preserved aggregate counts
- WAL and ledger fsync/write failures
- resume decisions that required full evidence
- manifest size by section
- number of domain projection entries
- largest manifest field and largest deferred artifact
- ratio of embedded payload bytes to referenced artifact bytes

These metrics are the guardrail against both extremes: over-auditing and under-recording.

## Acceptance Criteria

The solution is acceptable when:

- Critical trust events still have full evidence and remain hash-verifiable.
- Low-risk repeated transitions can be coalesced without breaking trace causality.
- Resume and final delivery never depend on sampled-only or aggregate-only evidence.
- Anomaly triggers raise evidence detail for the affected run.
- Evidence write overhead is measurable by tier and mode.
- A full audit explanation can distinguish intentional compaction from missing data.
- Manifest remains an execution evidence index, not a business workflow configuration file.
- Business state is represented through bounded projections with schema ids and digests.
- Adding a complex business workflow does not require adding branch-specific fields to OneCode core manifest logic.

## Implementation Direction

The likely implementation path is:

1. Add an `EvidenceMode` and `RiskTier` model near trace/WAL code.
2. Add a small event classification policy mapping event families to default mode and escalation triggers.
3. Extend trace events and WAL entries with explicit `risk_tier`, `evidence_mode`, and optional `payload_digest`.
4. Keep current full evidence behavior for critical events.
5. Add manifest extension boundaries for `domain_projection` with schema id, entity hash, decision hash, and evidence refs.
6. Add manifest size and section metrics before adding any new orchestration features.
7. Add compact/aggregate handling only for low-risk event families after tests prove resume and delivery still use full evidence.
8. Add tests that verify unknown events default to full evidence and critical events cannot be downgraded.
9. Add tests that verify business workflow data stays in bounded domain projections and does not become resume-critical manifest structure.

This should be implemented incrementally. The first milestone is explicit classification with no behavior reduction. Only after that should the runtime start coalescing low-risk records.
