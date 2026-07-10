# OneCode GPL v3 Relicensing Closure

Date: 2026-07-10

## Decision

OneCode is relicensed from Apache License 2.0 to the GNU General Public License,
Version 3 only. The SPDX expression is:

```text
GPL-3.0-only
```

This is intentionally different from `GPL-3.0-or-later`: recipients may use
the project under GPL version 3, not an unspecified future GPL version.

## Changed Records

- `LICENSE` now contains the unmodified official GNU GPL v3 text.
  Its SHA-256 is
  `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986`.
- `pyproject.toml` declares the PEP 639 license expression `GPL-3.0-only`.
  The superseded License classifier is intentionally omitted because current
  setuptools rejects combining it with a license expression.
- `README.md` states the current license and copyleft/source obligations.
- `CHANGELOG.md` records the licensing change.
- Historical closure documents identify Apache-2.0 only as their original,
  dated license posture and point to this migration.
- `tests/test_license.py` prevents the public declarations from drifting.

## Rights and Provenance Review

The local repository history for this project shows author identities belonging
to the same project operator (`aidi` / `OneCode`) and no distinct external
contributor identity. No project `NOTICE`, alternate `COPYING`, or bundled
third-party source-license file was found.

This technical review is not legal advice. If copyright in any contribution is
owned by another person or organization despite the recorded identities, their
permission may still be required for relicensing that contribution.

## Effect

GPL v3 permits use, study, modification, and redistribution. Distribution of
the program or derivative works must follow GPL v3 requirements, including
preserving notices, licensing covered derivatives under GPL v3, and providing
corresponding source in the circumstances required by the license.

The licensing change does not alter OneCode runtime behavior, I Ching formulas,
yin/yang balance, five-element relations, transition, dispatch, safety gates,
evidence authority, or public data contracts.

## Publication Boundary

This record documents the local source migration. A GitHub push, branch merge,
GitHub Release, package publication, or production deployment requires a
separate explicit publication action and verification record.

## Verification Record

```text
License RED test: failed against the prior Apache declarations
License consistency test: passed
Full verification: 825 passed, 1 environment-dependent skip
Doctor: ok
Source quality: ok
git diff --check: passed
Wheel: onecode-0.8.0-py3-none-any.whl
Wheel License-Expression: GPL-3.0-only
Wheel License-File: LICENSE
Wheel assets: ok
Publish action: not performed
```
