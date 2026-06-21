# Development Progress

This file records project progress and non-negotiable design decisions that
must survive across implementation batches.

## Current State

- Branch: `main`
- Remote: `zhangxiaolongne/video-skill`
- Canonical skill name: `artist-portrait-editor`
- Canonical install directory: `artist-portrait-editor`
- Distribution repository: `video-skill`
- Current local gate: deterministic local foundation only

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

## Current Hard Boundaries

Do not implement these until the relevant gate is explicitly opened and tested:

- media segmentation
- transcription
- OpenCV or vision analysis
- embeddings
- creative proposals
- timeline generation
- preview rendering
- model calls
- network search
- image generation or image editing

## Non-Negotiable Future Constraints

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

V0-002r should simulate canonical installation by copying the repository to a
temporary `artist-portrait-editor/` folder and running skill validation and
package preflight there. The target result is zero package preflight warnings in
the simulated install shape.
