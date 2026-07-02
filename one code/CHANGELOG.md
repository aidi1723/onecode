# Changelog

## 2026-07-02

### Fixed

- Prevented trace write-latency patching from mutating payload values that happen to equal the latency placeholder.
- Fixed aggregate trace gap metrics so cross-type aggregate windows are evaluated in timestamp order instead of file flush order.

### Tests

- Added regression coverage for payload placeholder collisions in `write_trace_event`.
- Added regression coverage for cross-type aggregate gap detection in `trace_evidence_metrics`.
