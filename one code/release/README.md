# one code Public Release Pack

This directory contains public-facing release material for one code.

It is intentionally separate from the local development documentation. The
development tree may keep internal research names, historical terms, and
experimental notes. Public release files should describe one code with neutral
engineering terminology so users can evaluate it as a deterministic local agent
kernel for trusted industrial AI workflows.

Use this directory when preparing:

- GitHub release descriptions
- package registry descriptions
- public project pages
- external technical summaries
- third-party integration briefs

Do not treat this directory as the source of runtime behavior. The source of
truth for implementation remains `src/`, `tests/`, and the normal project
documentation.

## Files

- `PUBLIC_README.md` - concise public project overview.
- `TERMINOLOGY.md` - public terminology mapping and terms to avoid in release copy.
- `RELEASE_NOTES.md` - current release summary written with engineering terms.
- `BENCHMARK_RESULTS.md` - benchmark metric definitions and verified result slots.
