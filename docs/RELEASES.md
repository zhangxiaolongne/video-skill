# Release Ledger

This file records only current publication state and recent release facts. Full release history is archived in [RELEASES_HISTORY.md](archive/RELEASES_HISTORY.md).

## Current Release State

- Latest published source baseline: `v0.50.0`
- Release commit: resolved by annotated tag `v0.50.0`
- Annotated tag: `v0.50.0`
- Publication ledger: `9013abc83455ea9bfbbd6a7fd8299920a924636b` records the
  post-refactor, single-root history baseline selected for remote publication.
- Published scope: V1 engineering substrate plus the V2 real-video aesthetic
  baseline from evidence fusion through second-cut candidates and benchmarks.
- Latest published capability work: `V3-08 V3 Release` as `v0.50.0`.
  It includes `V3-07 Personal/Subject Memory`.
  Its current prerequisite batch is `ACCEPTANCE-STAGE-07 Real Media
  Truthfulness And Baseline Recovery`.
- Publication policy: do not publish the next capability release until the
  release candidate has passed full local validation and the user approves it.

## Current Validation

- V2-01 through V2-08 recovered the stage benchmark, added the user interview
  contrast, established composition/evidence/ranking/39-60-90s structure/BGM/
  text/first-cut review, and preserved missing semantics as degraded rather than
  fabricated. Detailed per-gate validation now belongs to the historical ledger.
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
- V3-02 was reopened after rule review found that six source/output examples had
  been incorrectly frozen as the complete style space. The corrected local
  capability separates 16 content forms, 14 aesthetic styles, 10 creative
  techniques, 10 emotional arcs, and `follow/bend/break`; no combination is
  selected, applied, rendered, or allowed to invent semantics.
- V3-03 preserves compound natural-language feedback as multiple scoped,
  prioritized semantic clauses; maps clauses across style/rhythm/text/voice/BGM/
  transition/emotion/ending; detects contradictions; defines playback
  acceptance; and tracks clause outcomes through controlled revision
  application without mutating the canonical timeline or rendering media.
  Full local validation passes 264 tests plus schema, package/install, golden,
  BGM/rhythm, NLE, benchmark, release-audit, and diff checks.
- V3-04 compares canonical timeline, rendered second cut, and controlled
  revision candidates across seven domains, with artifact freshness,
  evidence-level separation, pairwise tradeoffs, and goal-specific advantages.
  It leaves the overall winner null and marks unsupported comparisons
  unavailable instead of ranking weak proxies as fact.
  Full local validation passes 267 tests plus schema, package/install, golden,
  BGM/rhythm, NLE, benchmark, release-audit, and diff checks.
- V3-05 writes one source-bound NLE package with editable FCPXML, EDL,
  Resolve/Premiere markers, cue sheet, relink manifest, version identity, and
  eight external acceptance checks. Real interview media links directly only
  after an exact hash match; missing fixture media remains visibly blocked.
  Full local validation passes 267 tests plus schema, package/install, golden,
  BGM/rhythm, legacy NLE/FCPXML, benchmark, release-audit, and diff checks.
- V3-06 assigns one of four exclusive tiers to every reviewed version and keeps
  media freshness, technical validity, first/second-cut aesthetics, BGM/voice,
  text, composition, transitions, ending, platform, and editable-delivery gaps
  visible. On the real interview project, both playable cuts require manual
  refinement, the plan-only revision is unusable, no version is publishable,
  and selected version remains null. Full local validation passes 274 tests plus
  schema, package/install, golden, BGM/rhythm, NLE, benchmark, release-audit,
  and diff checks.
- V3-07 creates one canonical project/subject creative memory with explicit
  identity, aliases, preferences, hard constraints, revision fulfillment,
  selected-style-only history, exact-identity local import, deduplication,
  unresolved conflicts, and advisory retrieval. The real interview project
  produces 13 truthful entries and preserves four revision clauses as
  `manual_only`; unselected style vocabulary is excluded. Full validation
  passes 283 tests via `.venv/bin/python -m pytest`; `.venv/bin/python
  run_checks.py` also passes schema, package/install, golden, BGM/rhythm, NLE,
  benchmark, release-audit, and diff checks.
- V3-08 binds V3-01 through V3-07 into exactly ten release outcomes against the
  current real interview project and three-class benchmark pack. Eight outcomes
  pass and two warn: all four human revision clauses remain `manual_only`, and
  all eight external NLE checks remain pending. Current real media hashes match,
  four strategy signatures differ, three versions are compared without a
  winner, publishability remains honest, memory is advisory, and audiovisual
  evidence remains coupled. The release claim is
  `mature_assistant_workflow`; mature-editor output is explicitly not claimed.
  Full project validation passes 286 tests via `.venv/bin/python -m pytest`;
  `.venv/bin/python run_checks.py` also passes Schema, Skill/package/install,
  golden, BGM/rhythm, NLE, real benchmark, release-candidate, and diff checks.

## Recent Releases

| Release | Scope | Publication |
| --- | --- | --- |
| `v0.50.0` | V3 mature assistant workflow | Current release |
| `v0.40.0` | V2 real-video aesthetic baseline | Previous release |
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
