# Release Ledger

This file records only current publication state and recent release facts. Full release history is archived in [RELEASES_HISTORY.md](archive/RELEASES_HISTORY.md).

## Current Release State

- Latest published source baseline: `v0.40.0`
- Release commit: resolved by annotated tag `v0.40.0`
- Annotated tag: `v0.40.0`
- Publication ledger: `9013abc83455ea9bfbbd6a7fd8299920a924636b` records the
  post-refactor, single-root history baseline selected for remote publication.
- Published scope: V1 engineering substrate plus the V2 real-video aesthetic
  baseline from evidence fusion through second-cut candidates and benchmarks.
- Active local work: `V3-01 Multi-Version Creative Strategies`, completed locally.
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
- V2-05 generated exact 39/60/90-second plans for both real projects, preserved
  the explicit 60-second standard target, bounded hook/build/payoff budgets,
  and passed 243 tests plus all quality/package gates.
- V2-09 applies an explicit standard option into independent 60-second second
  cuts for the interview and stage projects. Both retain source audio and pass
  canvas/frame-rate/stream/duration QC without overwriting the canonical first
  cut. Missing transcript, candidate-specific reframes, fine pacing, and mature
  publishability remain unresolved by design.
- V2-10 adds one reproducible three-class real-video benchmark pack. Stage and
  interview bind valid first/second-cut loops; a new four-source, 189.74-second
  CC0 street-festival project provides the event/promo input baseline. The pack
  remains degraded because that third class has no second-cut loop yet.
- V2-11 freezes version `0.40.0`, adds two-phase release auditing, verifies the
  current hashes of both closed-loop second cuts, preserves the degraded/input-
  only benchmark truth, and validates local-only package/provider boundaries.
  Pre-tag validation passes 251 tests plus golden, BGM/rhythm, NLE, package,
  install, benchmark, release-candidate, and diff checks.
- V3-01 local validation generates emotional-arc, high-energy, narrative-
  clarity, and portrait-highlight strategies for both 60-second real projects.
  Each project has four distinct ordered range signatures; no strategy is
  selected, applied, rendered, or promoted beyond degraded evidence confidence.

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
| `v0.40.0` | V2 real-video aesthetic baseline | Current release |
| `v0.30.0` | Single-root V1 architecture baseline | Previous retained baseline |
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
