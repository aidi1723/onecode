# Changelog

## 2026-07-05

### Fixed

- Evaluation gates now fail when predictions are missing from the gold set.
- Local service startup no longer uses a machine-specific adapter default.
- Local service request handling now rejects oversized bodies and out-of-range `max_tokens` before model generation.
- Release package no longer includes `.git`, `__pycache__`, or `.pyc` files.
- Release checksum now validates the included guarded full-test report.
- Release tests now assert they import the release script copy, preventing accidental testing of the parent workspace scripts.
- Release self-check uses `scripts/check_release_checksums.py` for SHA-256 checksum validation instead of platform-specific checksum tooling.
- Release checksum validation now rejects empty checksum files, malformed checksum rows, and paths that escape the release root.
- Local service `/predict` now rejects missing or negative `Content-Length` before reading request bodies or invoking generation.
- Prediction generation CLI now rejects non-positive `--limit` and `--max-tokens` values during argument parsing.
- Evaluation now rejects duplicate prediction IDs instead of silently letting later rows overwrite earlier predictions.
- Hardened dataset building now rejects invalid split ratios and replay multipliers before writing train/valid/test files.
- Evaluation now rejects duplicate gold IDs before computing metrics, preventing repeated counting of one prediction.
- Hardened dataset building now rejects duplicate source IDs before splitting or hard-negative indexing.
- Hardened dataset building now rejects missing or empty source IDs before grouping rows.
- Evaluation now rejects missing or empty gold and prediction IDs with explicit errors.
- Evaluation now reports unexpected prediction IDs and fails the gate when predictions contain IDs outside the gold set.
- Evaluation now rejects prediction rows that omit the `prediction` field instead of treating them as empty model output.
- Evaluation JSONL readers now reject non-object rows with line-numbered errors.
- Evaluation JSONL readers now wrap malformed JSON lines with file and line-numbered `ValueError` messages.
- Evaluation now rejects non-string `prediction` fields instead of coercing structured values into text.
- Evaluation now rejects non-string gold and prediction IDs instead of coercing them with `str()`.
- Evaluation CLI now rejects acceptance-rate thresholds outside the 0..1 interval.
- Local service `/predict` now rejects JSON request bodies that are not objects before accessing fields.
- Local service `/predict` now rejects non-canonical `Content-Length` values instead of relying on permissive integer parsing.
- Local service `/predict` now rejects boolean `max_tokens` values instead of treating them as integers.
- Local service CLI now rejects ports outside `0..65535` during argument parsing.
- Release checksum validation now requires every release file to be listed in the manifest, excluding the checksum file itself.
- Release checksum validation now rejects duplicate manifest paths.
- Release checksum validation now rejects manifest paths that resolve to directories.
- Release checksum validation now rejects non-canonical relative paths such as `./README.md`.
- Release checksum validation now rejects non-lowercase SHA-256 digests in the manifest.
- Release checksum validation now rejects backslash-separated manifest paths.
- Release checksum validation now rejects control characters in manifest paths.
- Release checksum validation now rejects manifest lines with leading spaces and requires canonical `digest  path` formatting.
- Release checksum validation now rejects manifests that list `release/checksums.txt` itself.
- Release checksum validation now rejects symlinks anywhere in the release tree, including unlisted dangling links.
- Evaluation now rejects empty gold row sets before computing metrics.
- Evaluation now rejects gold rows without a parseable assistant action, preventing `None == None` matches from inflating action-match rates.
- Hardened dataset building now rejects non-string source IDs instead of coercing them with `str()`.
- Hardened dataset building now rejects source IDs containing whitespace or control characters.
- Hardened dataset building now rejects empty source row sets before writing split files.
- Hardened dataset building now rejects source rows without a parseable assistant gold action.
- Hardened dataset building now rejects duplicate hard-negative replay IDs before augmentation.
- Hardened dataset building now rejects unknown recovery action names instead of silently producing no recovery upsample.
- Prediction generation JSONL input now rejects non-object rows, missing/empty/non-string IDs, and duplicate IDs before writing prediction files.
- Prediction generation CLI now reports input validation errors before importing MLX runtime dependencies.
- Prediction generation JSONL input now rejects empty input files, malformed `messages` fields, and rows without a user message before building prompts.
- Release documentation now reflects the current release self-check count and checksum-backed handoff status.

### Added

- `logs/guarded-full-report.json` with the current guarded full-test report.
- `requirements.txt` for MLX runtime dependency visibility.
- `scripts/verify_release.sh` for release-local self verification.
- Additional release tests for HTTP request-boundary handling and startup token bounds. Request-boundary tests call the handler directly and do not bind local ports.
- Release-local checksum validation tests for manifest self-listing and symlink rejection.

### Verification

- Release tests: 86 tests OK.
- Guarded full-test report: `sample_count=212`, `missing_prediction_count=0`, `json_valid_rate=0.9858490566037735`, `action_match_rate=0.8254716981132075`, `unsafe_allow_count=0`, `unknown_action_count=0`.
- `scripts/check_release_checksums.py` checksum validation: OK.
