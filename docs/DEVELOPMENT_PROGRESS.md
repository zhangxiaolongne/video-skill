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

- Current active gate: V2-01 Real Video Aesthetic Baseline
- Current batch: `V2-01` Real Video Aesthetic Baseline, status `planned`
- Latest published release: `v0.29.0`
- Current published capability work: V1-08 revision promotion and V1 release
  packaging
- Current acceptance stage: `ACCEPTANCE-STAGE-06` completed and published in
  `v0.29.0`
- Next release policy: no commit, tag, or push until V2-01 closes as a real
  capability version and the user approves publication

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

`V2-01` must produce a real-video aesthetic baseline from actual footage. The
countable tasks live only in `docs/CURRENT_BATCH.md`; this dashboard summarizes
the outcome:

- bind a real benchmark source;
- recommend duration from evidence;
- map highlights and weak areas;
- audit final-frame composition, source-layout intrusion, and safe reframing;
- plan multiple edit concepts;
- define hook/build/payoff;
- pair BGM and source audio with rhythm;
- plan subtitle/text timing and transitions;
- review the first-cut aesthetic gap;
- produce a second-cut candidate plan;
- write a real-video acceptance report.

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
- The primary benchmark currently preserves large source branding/layout bands
  around the performance in its portrait output; V2 must judge frame usability
  before treating an MP4 as an aesthetic result.
- V2-01 must use real footage evidence; synthetic fixtures alone no longer prove
  progress.

## Next Major Decision

Proceed with `V2-01 Real Video Aesthetic Baseline`. Do not open another release
preparation loop until V2-01 has real aesthetic evidence and a validated
candidate direction.
