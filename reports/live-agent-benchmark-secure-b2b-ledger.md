# Live Agent Benchmark

- runner_mode: `real-http`
- model: `same-model`
- task_id: `SECURE_B2B_LEDGER_SYNC_REPAIR`
- ok: `False`
- winner: `tie`
- winner_reason: `no_material_delta`
- token_savings: `0`
- token_savings_ratio: `0.0`

| group | success | turns | total_tokens | wall_time_seconds | final_trace | quality_score |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| bare | False | 1 | 0 | 8.6e-05 | `bare` | 0.0 |
| guarded | False | 1 | 0 | 8e-05 | `guarded` | 0.0 |

## Quality Breakdown

| group | conformance | sandbox_pass | summary_density | convergence | vuln_count | has_timeout | penalties |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| bare | 0.0 | 0.0 | 0.0 | 0.0 | 0 | False | `http_transport_failure` |
| guarded | 0.0 | 0.0 | 0.0 | 0.0 | 0 | False | `http_transport_failure` |

## Notes

Real-http mode records same-model HTTP metrics, executes returned registered tools, submits guarded evidence, and scores quality with the Quality Core matrix.
