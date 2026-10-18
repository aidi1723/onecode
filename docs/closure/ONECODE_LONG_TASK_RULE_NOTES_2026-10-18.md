# Long-task notes, 2026-10-18

Three live rounds built a library circulation package with `claude-sonnet-4-6` and `max_repair_attempts=2`. Host unittest passed after every round: 16, then 30, then 37 tests. Each write finished as code 39, action `cooldown`. Usage was 33925 prompt tokens and 20241 completion tokens.

The sandbox verifier failed on all three rounds because the local Docker socket was not there. The Colima message was not recognized, so the reason was recorded as `verifier_failed` instead of `sandbox_required`. The stored hexagram stayed at 39 `cooldown`. The entropy reading of that same failure was code 56 `recover` / continue on the first round, and code 40 `halt` on the next two.

Rules added on the existing hexagrams:

- `verifier_failed` is Li/Kun (40), action halt.
- `sandbox_required` is Gen/Kun (32), action checkpoint.
- `verifier_timeout` is Kan/Zhen (17), action checkpoint.

A verifier failure now replaces the write's cooled code. The entropy mix stays evidence and does not choose the next action. A missing Docker socket, including the Colima dial error, is `sandbox_required`.

A later ward-census run used that rule. Three rounds passed 36, then 47, then 59 host tests. Each write stayed at code 39, action `cooldown`. Each verifier halt was `sandbox_required`, code 32, action `checkpoint`, dispatch stop. No further mismatch appeared. The same local-executor checkpoint also covers `docker_not_found` and `docker_daemon_unavailable`. A model timeout uses the same Kan/Zhen checkpoint as `http_timeout` and `verifier_timeout`. An operator refusal uses the same Li/Kun halt as `approval_required`. Usage for the ward run was 29314 prompt tokens and 11881 completion tokens.

Across the 64 states, excess yin was hiding generation and control: earth damming water transitioned as `activate` instead of `throttle`, and earth generating metal did the same instead of `accelerate`. The hexagram transition baseline stays in place. The task schedule now restores those five-element actions when the only reason for `activate` is excess yin. A write carrying the dam schedule is refused with `earth_dams_water_flow`. A completed write still cools, and the landed Gen/Qian state records the next pressure as `accelerate` because earth generates metal.

Three rounds then ran every restored pair as a real write. Throttle and checkpoint schedules refused the file. Accelerate, recover, and wood breaking earth wrote the file, including pairs whose raw bandwidth is zero. A following dam still stopped after a nourishing write. The cooled model write stayed at code 39, action `cooldown`, with the next pressure `accelerate`. The same signatures repeated on each round.

Refusal reasons now classify back to the hexagram family that produced them. `earth_dams_water_flow` is Kun/Kan throttle, not a generic Li/Kun halt. A halted task still exits nonzero. The agent cycle stops on throttle and prune.

Zero bandwidth no longer replaces the I Ching reason. Fire over metal is `sovereignty_fire_suppresses_asset`. Metal pruning wood keeps the prune reason. A single tagged step's trace keeps that hexagram. Several steps of the same hexagram also keep it: two pure-yin refusals stay at 0, discover, and two earth-dam refusals stay Kun/Kan throttle. Different hexagrams in one plan still pass through the entropy record.

Patches and commands were then run once for every hexagram. Each matched the write ruling. Two siblings in one layer are judged apart: earth generating metal writes, and earth damming water in the same layer still refuses, without cancelling the write.

Reads and lists follow the same hexagram. Pure yin and yang rest may look; halt, control, prune, and checkpoint may not. Commands and patches use the write ruling: earth damming water does not run or patch, earth generating metal does. Every hexagram was read once under that rule.

Every hexagram now has one write ruling. Pure yang and excess yang cool and refuse the tagged write, except outer fire, which still halts. Pure yin discovers and refuses. Control, checkpoint, and halt refuse. Generation, recovery, activation, and continuation write. Two rounds executed all 64 tagged writes and matched that ruling.

A later variety run repeated three times. A normal write cooled and the next pressure was accelerate. A write without approval, a truncated plan, and an empty asset halted on Li/Kun. A search miss stayed on Kun/Kun and continued read-only. An HTTP timeout checkpointed on Kan/Zhen. A missing command checkpointed on Gen/Kun. Earth damming water and a controlled-by pair refused the write. Earth generating metal, fire generating earth, and wood breaking earth wrote. Fire over metal stopped on zero bandwidth. A verifier with no Docker socket checkpointed on Gen/Kun. No rule mismatch appeared.
