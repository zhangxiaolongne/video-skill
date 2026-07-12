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
- Active local work: `V3-02 Style Templates`, completed locally.
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
- V3-02 local validation provides six complete style templates. Specialized
  matching selects stage portrait, interview portrait, and event montage as the
  unique best matches for the three real project classes; no template is
  selected, applied, rendered, or allowed to invent source classification.

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
