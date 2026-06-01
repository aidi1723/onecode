# OneCode v0.2 Maturity Hardening Closure Checklist

- [x] Docker sandbox adapter exists and has tests.
- [x] Sandbox smoke test has completed on a machine with Docker.
- [x] Trace event writer exists, has tests, and is emitted by runner/model/verifier paths.
- [x] Human approval records exist and have tests.
- [x] Benchmark harness exists, can execute tasks, and writes a report.
- [x] Benchmark harness has at least 20 task definitions.
- [x] Security and contribution governance files exist.
- [x] LICENSE exists after project owner and license type are confirmed.
- [x] CI verify workflow exists.
- [x] `bash scripts/verify.sh` passes after this hardening pass.
- [x] Browser smoke still confirms OneCode Console opens.
- [x] No gateway dependency has been introduced by this v0.2 hardening pass.

## Notes

This phase adds the v0.2 foundations for sandboxing, observability, human
approval evidence, benchmark definitions, and release governance. It does not
yet make every kernel execution path run inside Docker. The project license is
currently proprietary, all rights reserved, with copyright assigned to `aidi`.

## Verification

- `PYTHONPATH=src python3 -m unittest tests.test_sandbox tests.test_readme`
  passed with 8 tests.
- `PYTHONPATH=src python3 -m onecode.cli benchmark` loaded 20 benchmark tasks
  and returned `status: ready`.
- `PYTHONPATH=src python3 -m onecode.cli benchmark --run --workspace-root /private/tmp/onecode-benchmark-v021 --report /private/tmp/onecode-benchmark-v021-report.json`
  ran 20 benchmark tasks and returned `passed_count: 20`.
- `bash scripts/verify.sh` passed with 355 unittest tests and `doctor`
  returned `status: ok`.
- `bash scripts/verify.sh` passed after the Docker smoke diagnostic update
  with 356 unittest tests and `doctor` returned `status: ok`.
- `docker version` passed against Colima Docker Engine:
  client `29.5.2`, server `29.2.1`, context `colima`.
- `PYTHONPATH=src python3 -m onecode.cli sandbox-smoke --workspace /private/tmp/onecode-sandbox-smoke --report /private/tmp/onecode-sandbox-smoke/report.json`
  returned exit code `1` with `status: failed` and
  `reason: sandbox_mount_not_propagated`; the container exited `0` and printed
  `True`, but the marker file did not appear on the
  host path. This indicates Colima did not propagate writes for that
  `/private/tmp` workspace mount.
- `PYTHONPATH=src python3 -m onecode.cli sandbox-smoke --workspace /Users/aidi/大字典/one\ code/.onecode/sandbox-smoke --report /Users/aidi/大字典/one\ code/.onecode/sandbox-smoke/report.json`
  returned exit code `0` with `status: completed`, `exit_code: 0`,
  `stdout_tail: "True\n"`, and marker path
  `/Users/aidi/大字典/one code/.onecode/sandbox-smoke/sandbox-smoke.txt`.
- LibreChat browser smoke passed after rebuilding the frontend and restarting
  the shell: Playwright reached `/c/new`, page title was `one code`, selected
  model was `onecode-agent`, and the OneCode project button was visible.
