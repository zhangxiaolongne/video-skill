# Release Ledger

This file records only current publication state and recent release facts. Full release history is archived in [RELEASES_HISTORY.md](archive/RELEASES_HISTORY.md).

## Current Release State

- Latest published source baseline: `v0.30.0`
- Release commit: `e80393915e0c850f119e9181d2bd5120f1504c4c`
- Annotated tag object: `7ed5f14b7b7bfd12a62d508d23abfc7ac9b7b6be`
- Publication ledger: this commit records the post-refactor, single-root
  history baseline before force-pushing the remote.
- Published scope: the V1 capability surface plus the complete architecture,
  JSON-governance, test, package-boundary, and history reset refactor.
- Active local work: `V2-01 Real Video Aesthetic Baseline`, not yet released.
- Publication policy: do not publish the next capability release until the
  release candidate has passed full local validation and the user approves it.

## Current Validation

- Architecture baseline validation passed on `2026-07-10`: `.venv/bin/python
  run_checks.py` completed successfully with `239 passed`, schema generation,
  skill validation, install simulation, release-candidate checks, and clean
  diff validation.
- The `v0.30.0` tag is the sole retained Git baseline. Detailed pre-reset
  release history remains readable in `docs/archive/RELEASES_HISTORY.md` but is
  intentionally not retained as Git object history.

## Recent Releases

| Release | Scope | Publication |
| --- | --- | --- |
| `v0.30.0` | Single-root architecture baseline | Current retained Git baseline |
| Pre-`v0.30.0` | Historical releases | Details retained as Markdown archive only |

## Release Closeout Requirements

Before a release is called publishable:

1. Close the named capability batch in `docs/CURRENT_BATCH.md`.
2. Record current validation and unresolved risks in this file.
3. Keep detailed historical notes in `docs/archive/RELEASES_HISTORY.md`, not in
   the current release summary.
4. Run the project validation command appropriate to the release risk.
5. Commit, tag, and push only after the user approves publication.

Do not recreate per-version readiness ledgers in separate files.
