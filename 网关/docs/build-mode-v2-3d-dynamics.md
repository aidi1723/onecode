# Build Mode V2 3D Dynamics

Build Mode V2 models each 3-bit hexagram as a coordinate in a cube:

- bit 1: tool/action bandwidth
- bit 2: context/memory bandwidth
- bit 3: boundary/sandbox exposure

Normal state transitions must move along cube edges. A transition that changes multiple bits is decomposed into a `TransitionPlanEvidence.edge_path`. Emergency halt transitions may bypass edge walking only when backed by hard evidence such as `ViolationEvidence` or `BehaviorFingerprintEvidence`.

V2 also adds:

- behavioral fingerprint audit for text/tool mismatch and destructive hidden intent
- entropy decay gates for repeated pytest failures
- signed evidence envelopes for future multi-node state synchronization
