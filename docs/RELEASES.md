# Release Ledger

This file records only current publication state and recent release facts. Full release history is archived in [RELEASES_HISTORY.md](archive/RELEASES_HISTORY.md).

## Current Release State

- Latest published source baseline: `v0.30.0`
- Release commit: `e80393915e0c850f119e9181d2bd5120f1504c4c`
- Annotated tag object: `7ed5f14b7b7bfd12a62d508d23abfc7ac9b7b6be`
- Publication ledger: `9013abc83455ea9bfbbd6a7fd8299920a924636b` records the
  post-refactor, single-root history baseline selected for remote publication.
- Published scope: the V1 capability surface plus the complete architecture,
  JSON-governance, test, package-boundary, and history reset refactor.
- Active local work: `V2-04 Highlight, Hook, And Ending Scoring`, completed
  locally and ready for one-version publication.
  Its current prerequisite batch is `ACCEPTANCE-STAGE-07 Real Media
  Truthfulness And Baseline Recovery`.
- Publication policy: do not publish the next capability release until the
  release candidate has passed full local validation and the user approves it.

## Current Validation

- Real benchmark recovery on `2026-07-11`: the 240.5-second Chen Haoyu source
  rebuilt a 72.15-second, 8-segment timeline and exact `1080x1920 @ 30fps`
  delivery export. Delivery acceptance passed with score `0.929`, no failed
  stage, current preview/final/rhythm QC, and one explicit BGM review warning.
- V2-01 composition validation on `2026-07-11`: 9 bound real frames received a
  quarantined host-Agent composition review; center, left-close, right-profile,
  and conditional-wide crop classes produced review-only contact sheets. Full
  `run_checks.py` passed with `243 passed` plus golden, BGM/rhythm, NLE,
  package/install, release-candidate, schema, and diff checks.
- Range-map/concept-comparison work on `2026-07-11` initially had only syntax, exact
  artifact-binding, JSON/schema, and real-data static verification so far. Full
  regression and release validation are intentionally deferred to V2-01 close;
  the earlier `243 passed` result does not validate these newer changes.
- Audiovisual/first-cut work binds nine audiovisual domains and an honest first-cut
  review into the same aesthetic baseline. Static real-project validation marks
  the technically valid cut `not_publishable` at maturity `0.34`; these changes
  are also awaiting the deferred V2-01 full regression pass.
- The second-cut outcome has an explicit `second-cut --concept-id` supervised planning
  boundary. This is active capability work, not a release or applied edit.
- The user then selected `concept_emotional_short`; its real second-cut plan
  targets the project-configured 60 seconds, contains 11 ordered actions, and
  owns every ranked first-cut issue. No planned action has been applied, and the
  root edit-brief duration bug was subsequently resolved as `ISSUE-020`.
- V2-01 closeout on `2026-07-12` added the user-provided actress-interview
  contrast benchmark, fixed duration precedence/recommendation and required clip
  ordering, resolved `ISSUE-020`, and passed 243 tests plus golden, BGM/rhythm,
  NLE, package/install, schema, release-readiness, and diff validation. No commit,
  tag, or push was performed during local closeout; the complete capability was
  subsequently published to `main` as commit
  `bccf4fb0ca52d98c0404245e226f4c1b5afe3d83`.
- V2-02 local real-media validation rendered a 60-second `1280x720` interview
  no-op contrast with six explicit native-frame choices and a 72.10-second
  `1080x1920` stage playback with seven visible reframes plus one explicit
  promo-card preservation. Both retain audio and leave canonical final/timeline
  files untouched. Stage conditional performer and crop-jump risks remain
  warnings, not aesthetic acceptance claims.
- V2-03 local validation created one canonical evidence map per project. The
  interview map has 45 units with full keyframe/audio technical coverage; the
  stage map has 50 units with half keyframe and full audio technical coverage.
  Both correctly retain absent transcript, detected-scene, speech/music,
  applause, emotion, lyrics, and BPM evidence as degraded/unknown. Full checks
  passed with 243 tests and all quality/package gates.
- V2-04 local validation ranked 45 interview and 25 stage visual candidates
  independently for highlight, hook, and ending. It excluded 25 stage
  pure-audio/BGM units, applied no first/last position bonus, kept missing
  semantics neutral with zero confidence, and passed 243 tests plus all
  quality/package gates.

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
