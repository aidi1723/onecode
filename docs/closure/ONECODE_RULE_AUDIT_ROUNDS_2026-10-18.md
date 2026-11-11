# Rule audit rounds, 2026-10-18

Three rounds compared the running kernel with the closeout reading at `8369b1f`. The same `hexagram.py`, `execution_engine.py`, and `verifier.py` were on the Mac and on n100 (`~/onecode-rule-check`). No new hexagram was added. Version stays 0.8.0. Nothing was pushed.

The reading under test:

- The transition and the task schedule are the same action.
- A tagged write, patch, command, read, or list follows that action. Reads stay open during discovery and yang rest.
- Siblings are judged separately. One hexagram, or several copies of it, stays on the trace. Different hexagrams combine by the aggregate. Entropy is evidence.
- A refusal reason classifies back to the family that produced it. A halted task exits nonzero.
- `verifier_failed` is Li/Kun (40), halt. A missing executor is Gen/Kun (32), checkpoint. A timeout is Kan/Zhen (17), checkpoint. A verifier failure replaces the cooled write code.

## Kernel rounds

Mac, three rounds, including a real write, read, and command for every hexagram: 0 mismatches. The rounds were identical. Writes allowed 30 and refused 34. Reads allowed 37 and refused 27. Schedule counts: discover 1, checkpoint 13, throttle 2, accelerate 8, activate 8, recover 10, continue 4, halt 9, prune 3, cooldown 6.

The same census on n100, three rounds, without launching a command container: the same counts and 0 mismatches.

Focused unit tests on the Mac, three times: 148 tests, OK each time. The Docker-free subset on n100, three times: 143 tests, OK each time.

Checked inside those rounds: earth damming water refuses while earth generating metal in the same layer writes; two pure-yin steps stay at 0; a mixed plan uses the aggregate and still records entropy; a cooled completion is code 39 and the next pressure is accelerate; discovery continues read-only; a dam, a verifier failure, and a missing executor stop, verify, or stay on their named hexagrams. A synthetic `verifier_failed` replaces code 39 with code 40, halt, and blocks delivery.

On the Mac, Docker is not up, so the command rounds used the designed host fallback. The ruling still matched. Those rounds did not enter a container.

## n100 sandbox rounds

`python:3.12-slim` on this host is an arm64 image. One unittest through that tag stopped at 8 seconds with `verifier_timeout`, code 17, action checkpoint. A native amd64 image was used for the rounds below, then the arm64 tag was put back.

Three rounds on the native image:

- A passing unittest stayed `passed` in about 1.5 seconds.
- A failing unittest was `verifier_failed`. Applied to a cooled write, the stored code became 40, action halt, delivery blocked.
- The container user was 65534, name resolution to the outside failed, and writing `/etc` failed because the root filesystem is read-only.
- One command from each schedule action, three times, followed `action_ruling`. Allowed commands printed `pong`. Refused commands kept the I Ching reason and did not print it.
- All 64 commands, one round, followed the same ruling. 0 mismatches.

A mode 700 workspace rejected a sandboxed `open('marker.txt')` with `PermissionError`. The same command on a mode 777 workspace wrote `ok`. A normal 755 project directory is in the first group: the hexagram can allow the command, and the sandbox user still cannot create the file. `write_text` and `patch_text` run as the host user, so those writes are not under this limit.

The built-in verifier command uses the host interpreter path. Inside the container that path is missing, exit 127, and the reason is `verifier_failed`, code 40, halt. The unittest did not run. The same command with `python3` did run.

Three tests encode the Mac host: `test_rule_task_variety` expects `sandbox_required` where this Docker host returns `verifier_failed`; `test_rule_action_tasks` and `test_rule_parallel_tasks` pass the host interpreter into the container, so an allowed command fails and the 64-command plan stops at 37 results.

## Verdict

The 64-state reading meets the closeout standard on both machines. The live sandbox on n100 meets that reading when the image is native and the verifier command is `python3`: pass stays deliverable, failure halts on Li/Kun, timeout checkpoints on Kan/Zhen, and every tagged command follows its hexagram.

Three gaps stay outside that match. The default image tag on this n100 is the wrong architecture. The default verifier command points at the host interpreter, so a failed start is recorded as a failed check. A sandboxed command cannot create a file in a 755 workspace.

Those three gaps were closed in the sandbox delivery. The later one-patch repair is [ONECODE_TASK_RULE_FOLLOWUP_2026-10-20.md](ONECODE_TASK_RULE_FOLLOWUP_2026-10-20.md).
