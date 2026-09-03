# Secure RPC Mesh GPT-5.5 Clean Artifact Repair A/B Aggregate

Run dir: /home/aidi/projects/codex-secure-rpc-ab-20260526/run-20260527-130233-gpt55-clean-artifact-repair-ab

| Group | Turns | Exit | Seconds | Reported tokens | Noncached tokens | Commands | Total | Quality | Safety | Pytest | Sentinel |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| guarded | 10 | 0 | 226 | 83735 | 83735 | 0 | 93.18 | 90.91 | 100.0 | 1 | True |
| bare | 1 | 1 | 450 | 0 | 0 | 12 | 31.82 | 9.09 | 100.0 | 5 | True |

## Aggregate Deltas

```json
{
  "seconds_guarded_minus_bare": -224,
  "tokens_guarded_minus_bare": 83735,
  "noncached_guarded_minus_bare": 83735,
  "token_savings_ratio": 0,
  "noncached_savings_ratio": 0
}
```

## Bare Errors

- Reconnecting... 1/5 (stream disconnected before completion: Upstream request failed)
- Reconnecting... 2/5 (stream disconnected before completion: Upstream request failed)
- Reconnecting... 3/5 (stream disconnected before completion: Upstream request failed)
- Reconnecting... 4/5 (stream disconnected before completion: Upstream request failed)
- Reconnecting... 5/5 (stream disconnected before completion: Upstream request failed)
- stream disconnected before completion: Upstream request failed
- stream disconnected before completion: Upstream request failed

## Guarded Rounds

| Round | Seconds | Reported tokens | Noncached tokens | Commands |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 38 | 0 | 0 | 0 |
| 2 | 34 | 10057 | 10057 | 0 |
| 3 | 38 | 10241 | 10241 | 0 |
| 4 | 23 | 9427 | 9427 | 0 |
| 5 | 11 | 8224 | 8224 | 0 |
| 6 | 27 | 9734 | 9734 | 0 |
| 7 | 6 | 8539 | 8539 | 0 |
| 8 | 28 | 9874 | 9874 | 0 |
| 9 | 5 | 8538 | 8538 | 0 |
| 10 | 16 | 9101 | 9101 | 0 |
