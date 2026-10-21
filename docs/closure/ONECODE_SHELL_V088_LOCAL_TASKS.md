# Local agent tasks, 2026-10-21

This is a scripted local record for `benchmarks/tasks/agent/`. It is not a SWE-bench score. `claims_mainstream_parity` stays false.

## Command

```bash
PYTHONPATH=src .venv/bin/python -c "from pathlib import Path; from onecode.benchmark import agent_pass_rate_record, load_benchmark_tasks, run_benchmark_tasks; tasks = load_benchmark_tasks(Path('benchmarks/tasks/agent')); report = run_benchmark_tasks(tasks, workspace_root=Path('/tmp/onecode-agent-local-tasks')); print(agent_pass_rate_record(report))"
```

The runner is `scripted_oracle` through `run_benchmark_task`. No model was called.

## Result

| Field | Value |
| --- | --- |
| Tasks | 30 |
| Passed | 30 |
| Pass rate | 1.0 |
| Failed | none |
| `claims_mainstream_parity` | false |

Stop reasons present in the record: completed with no reason, `permission_denied`, `resource_budget_exceeded`, and `sovereignty_breach`. Those stops are expected task outcomes, and the assertions still passed.

## Gate

`bash scripts/verify.sh` on this working tree passed: 1242 tests, 1 skipped, coverage 86%, doctor status `ok`. The skip is `test_global_onecode_command_points_to_project_entrypoint` because `ONECODE_GLOBAL_COMMAND` is not set. On this Mac, doctor reports `docker_ready` false. n100 remains the sandbox acceptance host.

The launcher now expects LibreChat `v0.8.8` at community commit `e8f3be08623663d4ad7f7241e693c94469b63bb0`. The integrated fork is branch `feature/onecode-shell-v088` in `/Users/aidi/大字典/onecode-librechat`, HEAD `37e6b8454`. It is not the sibling path `../onecode-librechat`, and it has not been pushed. LibreChat's own frontend tests have not been run.
