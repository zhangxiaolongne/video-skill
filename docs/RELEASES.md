# Release Ledger

This file records only current publication state and recent release facts. Full release history is archived in [RELEASES_HISTORY.md](archive/RELEASES_HISTORY.md).

## Current Release State

- Latest published capability release: `v0.29.0`
- Release commit: `fb723b2d13114b5b2885a19c1a06bdccd4cf02ca`
- Annotated tag object: `84ab1f9cc60e1445447badd6858a62031b57133c`
- Remote main publication ledger: `4bd44ca793755689689689c2fa100113b9f09a80f88`
- Published scope: V1-01 through V1-08, including duration/edit brief,
  aesthetic timeline, revision planning/application/promotion, revised render
  readiness, and V1 release packaging.
- Active local work: `V2-01 Real Video Aesthetic Baseline`, not yet released.
- Publication policy: do not publish the next capability release until the
  release candidate has passed full local validation and the user approves it.

## Current Validation

- V1-08 full project validation passed on `2026-07-04`: `.venv/bin/python -m
  pytest` reported `305 passed`.
- Release-candidate validation passed on `2026-07-04`: `.venv/bin/python
  scripts/run_release_candidate.py --allow-dirty --json` passed with the
  expected dirty warning from visible local `runs/` evidence.
- Project check passed on `2026-07-04`: `.venv/bin/python run_checks.py
  --skip-pytest`.
- V2 audit support validation passed on `2026-07-10`: `.venv/bin/python -m
  pytest` reported `305 passed`; `.venv/bin/python run_checks.py --skip-pytest`
  also passed. This is local verification only, not a capability release.
- Current doc-governance follow-up validation is local only until the next
  substantial capability version closes.

## Recent Releases

| Release | Scope | Publication |
| --- | --- | --- |
| `v0.29.0` | V1 aesthetic editing baseline and revision promotion | Published at `fb723b2d13114b5b2885a19c1a06bdccd4cf02ca` |
| `v0.28.0` | Acceptance Stage 1-6, including release candidate publication | Published at `d3f5e7379620325132be0b0586551dffc3c21291` |
| `v0.27.0` | V0-043 phrase-level manual edit guidance | Published; full details archived |
| `v0.26.0` | V0-042 BGM rhythm intelligence | Published; full details archived |
| `v0.25.0` | V0-025 through V0-041 acceptance/workflow hardening | Published; full details archived |
| `v0.24.0` | V0-010n through V0-024 foundation and acceptance gates | Published; full details archived |

## Release Closeout Requirements

Before a release is called publishable:

1. Close the named capability batch in `docs/CURRENT_BATCH.md`.
2. Record current validation and unresolved risks in this file.
3. Keep detailed historical notes in `docs/archive/RELEASES_HISTORY.md`, not in
   the current release summary.
4. Run the project validation command appropriate to the release risk.
5. Commit, tag, and push only after the user approves publication.

Do not recreate per-version readiness ledgers in separate files.
