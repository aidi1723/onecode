# Long-task notes, 2026-10-18

Three live rounds built a library circulation package with `claude-sonnet-4-6` and `max_repair_attempts=2`. Host unittest passed after every round: 16, then 30, then 37 tests. Each write finished as code 39, action `cooldown`. Usage was 33925 prompt tokens and 20241 completion tokens.

The sandbox verifier failed on all three rounds because the local Docker socket was not there. The Colima message was not recognized, so the reason was recorded as `verifier_failed` instead of `sandbox_required`. The stored hexagram stayed at 39 `cooldown`. The entropy reading of that same failure was code 56 `recover` / continue on the first round, and code 40 `halt` on the next two.

Rules added on the existing hexagrams:

- `verifier_failed` is Li/Kun (40), action halt.
- `sandbox_required` is Gen/Kun (32), action checkpoint.
- `verifier_timeout` is Kan/Zhen (17), action checkpoint.

A verifier failure now replaces the write's cooled code. The entropy mix stays evidence and does not choose the next action. A missing Docker socket, including the Colima dial error, is `sandbox_required`.

A later ward-census run used that rule. Three rounds passed 36, then 47, then 59 host tests. Each write stayed at code 39, action `cooldown`. Each verifier halt was `sandbox_required`, code 32, action `checkpoint`, dispatch stop. No further mismatch appeared. The same local-executor checkpoint also covers `docker_not_found` and `docker_daemon_unavailable`. A model timeout uses the same Kan/Zhen checkpoint as `http_timeout` and `verifier_timeout`. An operator refusal uses the same Li/Kun halt as `approval_required`. Usage for the ward run was 29314 prompt tokens and 11881 completion tokens.
