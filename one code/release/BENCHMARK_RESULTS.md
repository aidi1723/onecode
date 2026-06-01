# one code Benchmark Results

one code is not a general-purpose autonomous assistant. It is a deterministic
execution kernel for reducing model error propagation in local coding workflows.

This document records the public benchmark metrics used to evaluate safety,
task success, task quality, runtime overhead, and token efficiency.

## Verified Gates

The current release has the following verified local gates:

| Gate | Result |
| --- | --- |
| Core verification | 185 tests OK |
| Doctor smoke check | status: ok |
| Web API focused suite | 48 tests OK |
| Benchmark task definitions | 20 executable local tasks |
| Release audit | no tracked changes, no untracked release candidates |
| License | Apache License 2.0 |

## Metric Definitions

| Metric | Meaning | Measurement |
| --- | --- | --- |
| Invalid-action rate | Model output references invalid tools, invalid schemas, unsafe paths, or unsupported execution modes. | Count invalid candidate actions over total task attempts. |
| Unsafe-write prevention | Candidate writes that are blocked before mutating protected or out-of-scope files. | Count blocked unsafe writes over unsafe write attempts. |
| Verified task success | Tasks that complete and satisfy expected file, verifier, or evidence assertions. | Count verified completions over total tasks. |
| Task quality score | Weighted score for correct file content, no extra writes, verifier success, evidence completeness, and resume correctness. | Benchmark scorer output. |
| Repair-loop reduction | Reduction in repeated correction attempts needed to reach a verified result. | Baseline retry count compared with one code retry count. |
| Time saved | Wall-clock reduction from fewer failed retries and deterministic resume skips. | Median and P95 task duration comparison. |
| Token saved | Token reduction from fewer repair prompts, repeated context, and failed follow-up attempts. | Total prompt plus completion tokens per benchmark run. |
| Evidence overhead | Disk bytes written for run evidence. | Full evidence versus WAL-only relaxed evidence size. |
| Resume correctness | Correct skip, apply, halt, or tamper response when re-running a task. | Resume benchmark assertions. |

## A/B Result Matrix

The table below is the release slot for measured A/B results. Do not fill it
with estimates. Only publish numbers after running the same task set against the
same model, prompt, workspace, and verification rules.

| Metric | Baseline agent | one code | Delta |
| --- | ---: | ---: | ---: |
| Invalid-action rate | TBD | TBD | TBD |
| Unsafe-write prevention | TBD | TBD | TBD |
| Verified task success | TBD | TBD | TBD |
| Task quality score | TBD | TBD | TBD |
| Median task time | TBD | TBD | TBD |
| P95 task time | TBD | TBD | TBD |
| Average tokens per task | TBD | TBD | TBD |
| Total tokens per benchmark run | TBD | TBD | TBD |
| Evidence bytes per completed task | TBD | TBD | TBD |
| Resume correctness | TBD | TBD | TBD |

## Reporting Guidance

When A/B data is available, public copy may use language like:

```text
In local benchmark tasks, one code reduced invalid action propagation by X%,
improved verified task completion by Y%, and reduced repeated repair token usage
by Z%.
```

Do not claim hallucination, success-rate, quality, time, or token improvements
without attaching the benchmark task set, environment, model, and scoring rules.

## Current Positioning

one code should be described as:

```text
a trusted industrial AI kernel for enterprise-grade local agent workflows
```

It should not be described as:

```text
a fully autonomous general-purpose assistant
```

