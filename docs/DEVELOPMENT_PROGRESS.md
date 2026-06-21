# Development Progress

This file records project progress and non-negotiable design decisions that
must survive across implementation batches.

## Relationship To Master Document

The master document `artist_portrait_editor_revision5_optimized.md` owns
strategy:

- product direction
- capability boundaries
- data contracts
- creative principles
- long-term design constraints

This development document owns tactics:

- completed local batches
- current implementation state
- known packaging or validation risks
- next likely batch
- tactical reminders that must be carried into implementation

When a user requirement changes long-term product behavior, update both files:

- record the strategic principle in the master document
- record the implementation status, current gate, and next tactical step here

## Current State

- Branch: `main`
- Remote: `zhangxiaolongne/video-skill`
- Canonical skill name: `artist-portrait-editor`
- Canonical install directory: `artist-portrait-editor`
- Distribution repository: `video-skill`
- Current local gate: V0-005 PySceneDetect scene segmentation gate only

## Completed Local Versions

- V0-002a: media scan data contract and initial scan ledger.
- V0-002b: media scan acceptance checks.
- V0-002c: `sources.csv` metadata import.
- V0-002d: rescan identity for moved files.
- V0-002e: supersedes tracking for same-location content changes.
- V0-002f: minimal deterministic material map.
- V0-002g: minimal project risk review.
- V0-002h: status dashboard.
- V0-002i: run report refresh after state mutations.
- V0-002j: expanded foundation checks.
- V0-002k: invalid source ledger handling.
- V0-002l: atomic writes for rebuildable report outputs.
- V0-002m: artifact consistency checks.
- V0-002n: read-only `doctor` diagnostics.
- V0-002o: root `SKILL.md` and `agents/openai.yaml` metadata.
- V0-002p: skill package preflight.
- V0-002q: skill package policy.
- V0-002r: canonical install simulation.
- V0-002s: release readiness for the unpushed local batch.
- V0-003a: gate reconciliation from Stage A-only to media scan foundation.
- V0-003b: deterministic scan report and scan artifact status.
- V0-003c: downstream map/review invalidation after source ledger changes.
- V0-004a: clip record schema and committed JSON Schema.
- V0-004b: deterministic fixed-window `segment`.
- V0-004c: canonical `clips.jsonl` and rebuildable `clip_report.md`.
- V0-004d: clip status, doctor diagnostics, and invalidation chain.
- V0-005a: `features.scene_detection` routing for `off`, `auto`, and
  `required`.
- V0-005b: optional PySceneDetect adapter and scene-clip method records.
- V0-005c: fixed-window fallback diagnostics and required-dependency failure
  handling.

## Current Hard Boundaries

Do not implement these until the relevant gate is explicitly opened and tested:

- transcription
- OpenCV or vision analysis
- embeddings
- creative proposals
- timeline generation
- preview rendering
- BGM selection, beat analysis, or music/timeline fitting
- model calls
- network search
- image generation or image editing

## Non-Negotiable Future Constraints

### Prefer Mature Third-Party Tools

Future implementation batches may use third-party tools directly when the gate
allows it. Do not rebuild capabilities that stable tools, installed Codex
skills, plugins, search, image generation/editing tools, OpenAI models, ffmpeg,
ffprobe, PySceneDetect, Whisper, OpenCV, or similar libraries already provide.

Tactical rule for future batches:

- check available tools, skills, plugins, and libraries before implementing a
  capability from scratch
- use third-party outputs as evidence with provenance, not unreviewed truth
- keep config gates, failure modes, and review rules around every non-local or
  model-backed capability
- keep current V0-005 scene segmentation local and bounded to PySceneDetect;
  third-party outputs are evidence, not unreviewed truth

### BGM Is Part Of Editing Logic

BGM must not be treated as a final decorative layer. Different video outputs
need different BGM strategies, and the selected BGM must coordinate with text,
source video rhythm, pacing, transitions, and audio mix.

Future proposal/timeline work must account for:

- BGM metadata: mood, genre, BPM, section structure, build/drop points, loop
  points, ending behavior, and rights status.
- Beat and phrase alignment: cuts, transitions, subtitle entrances/exits, and
  highlight moments should be able to align to beats, bars, drops, breaks, or
  intentional off-beat pauses.
- Output-specific music strategy:
  - high-energy short edits need stronger beat/drop alignment and faster cuts
  - portrait narratives need controlled emotional build and release
  - interview/documentary outputs need low-interference music and voice-first
    mixing
  - stage/performance outputs need careful handling of original performance
    audio versus added BGM
- Audio timeline requirements: BGM in/out points, fades, ducking under speech,
  retained original audio, transition sounds, and intentional silence.
- Review requirements: generated proposals and timelines should explain why a
  BGM choice fits the target output and where music structure drives edit
  decisions.

This constraint is not implemented in the current local foundation. It must be
carried into the future proposal, timeline, review, and preview gates.

## Next Likely Batch

Next action should finish V0-005 release readiness: run the full local
validation set, record the release checkpoint, commit the batch locally, and
push only after the batch is reviewed.
