# Development Progress

This is the current-stage dashboard. It is not the task ledger, release ledger,
issue tracker, or master strategy document.

## Document Map

- Master strategy: `artist_portrait_editor_revision5_optimized.md`
- Current dashboard: `docs/DEVELOPMENT_PROGRESS.md`
- Current task ledger: `docs/CURRENT_BATCH.md`
- Issues and blockers: `docs/ISSUES.md`
- Active decisions: `docs/DECISIONS.md`
- Release state: `docs/RELEASES.md`
- Machine snapshot: `docs/current_progress.json`
- Historical decisions/releases: `docs/archive/`

## Current State

- Current active gate: V2-03 Transcript / Vision / Audio Evidence Fusion
- Gate state: completed locally; ready for one-version publication
- Completed published capability: `V2-02` Frame Composition And Reframing
- Current complete version: `V2-03 Transcript / Vision / Audio Evidence Fusion`
- Current batch: `V2-03` completed locally
- Latest published release baseline: `v0.30.0`
- Current published capability work: V1-08 revision promotion and V1 release
  packaging
- Current acceptance stage: `ACCEPTANCE-STAGE-07` completed locally with full
  checks and current real-project delivery acceptance
- Next release policy: no commit or push until complete V2-02 validation closes
  as one coherent capability version

## Capability Dashboard

V0/V1 proved the engineering substrate: package entry points, media scan,
segmentation, transcription/keyframe evidence, proposal/timeline generation,
BGM ingestion/fitting, preview/final export, editor package, FCPXML/NLE support,
acceptance checks, and revision promotion.

That is usable infrastructure, not a mature editor. The remaining gap is
creative judgment on real footage: duration choice, usable moments, weak-area
avoidance, final-frame composition/reframing, BGM fit, text timing, pacing,
transitions, and final taste.

V2 therefore starts with real-video aesthetic baselines instead of more
paperwork or isolated cleanup.

The supporting cleanup is now materially complete: redundant proposal,
workflow, acceptance, FCPXML, and BGM recommendation request chains have been
removed; their real outputs remain. Workspace diagnostics is independent from
the media/edit pipeline, and feature modules directly use state, record, and
error primitives. This is not a V2 capability outcome and does not advance any
V2-01 task by itself.

## Current Batch Focus

`ACCEPTANCE-STAGE-07` made the existing real-media pipeline truthful. V2-01 is
now complete locally, and its acceptance outcomes live only in `docs/CURRENT_BATCH.md`.
The recovered baseline now:

- owns exact aspect-aware preview and final canvases;
- normalizes mixed source dimensions before concatenation;
- renders supported timeline fades and records execution truth;
- treats every `mixed_audio=true` candidate as a sound risk;
- applies restricted-rights policy consistently;
- rejects blocked workspace state during acceptance;
- migrates superseded state steps;
- shares one public rendering boundary;
- rebuilds the primary real benchmark against current contracts;
- runs golden, BGM/rhythm, and NLE quality passes in full checks.
- binds all 8 real timeline/source ranges into one highlight/weak-area map with
  explicit visual/audio uncertainty;
- compares materially different `43.29s`, `72.15s`, and `115.44s` edit concepts
  without selecting one or mutating the timeline.
- judges source audio, BGM, speech/vocal, text, cuts, transitions, pauses,
  composition, and ending together instead of accepting isolated rhythm checks;
- records the technically valid first cut as aesthetically `not_publishable`
  at a `0.34` maturity baseline with six ranked second-cut problems.
- exposes an explicit second-cut concept-selection command and cross-domain
  candidate planner with a real user-selected candidate.
- records the user's `concept_emotional_short` choice in a real 60-second
  second-cut plan with 11 ordered actions and complete ownership of all ranked
  first-cut issues; actions remain unapplied.
- validates the same contracts against a user-provided 448.333-second actress
  interview without importing stage-specific crop or BGM assumptions;
- fixes configured-duration precedence, bounded short-platform recommendations,
  full downstream invalidation, and required-proposal clip ordering;
- passes 243 tests plus golden, BGM/rhythm, NLE, package/install, schema, release
  readiness, and diff validation.

## Long-Range Direction

- V2: real-video aesthetic editor, from baseline analysis to mature cut planning.
- V3: operator workflow, preview iteration, and NLE handoff quality.
- V4: director-level creative system with stronger taste, rhythm, and revision
  control.

The long-range roadmap belongs in the master document. This dashboard keeps only
the active gate and immediate development direction.

## BGM And Third-Party Policy

- Prefer Mature Third-Party Tools when they are free, local, public, or already
  available through the host environment.
- BGM must not be treated as a final decorative layer.
- Extracted video audio is a mixed audio track, not automatically a clean BGM.
- Do not fabricate BPM; if no validated beat evidence exists, say so.
- BGM review must account for subtitle entrances/exits, transitions, speech
  ducking under speech, scene rhythm, and emotional structure.

## Mandatory Batch Contract

- Keep at least ten independent version tasks for substantial capability work.
- Do not pad the batch with fields, schema edits, tests, file moves, local
  refactors, documentation-only changes, diagnostics, or incidental bug fixes.
- Those small items are valid supporting work only when they serve a named
  capability outcome.
- If the next work no longer fits the active gate, stop and promote the gate
  explicitly instead of pretending cleanup is progress.

## Principal Blockers

- The skill can run an end-to-end proof, but the edited output is still far from
  a mature human editor.
- Real BGM judgment remains limited until source-audio, candidate music, beat
  evidence, and visual pacing are evaluated together.
- The recovered primary benchmark passes technical delivery acceptance at exact
  `1080x1920`, but still preserves large source branding/layout bands around the
  performance. V2 must judge and alter frame usability before calling it an
  aesthetic result.
- V2-01 must use real footage evidence; synthetic fixtures alone no longer prove
  progress.

## Next Major Decision

Publish V2-03 as one version after its canonical maps passed synthetic media,
45-unit interview, and 50-unit stage validation. Both real maps remain honestly
degraded where transcript, detected scenes, and visual/audio semantics are
missing. Full validation passed with 243 tests and all quality/package checks.
V2-04 scoring is the next complete version and is not active in this batch.
