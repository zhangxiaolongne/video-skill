# State And Invalidation

Authoritative source: `artist_portrait_editor_revision5_optimized.md`.

The current V0-006 gate uses `.artist-portrait/state.json` as a step ledger,
not a single linear project state.

Current step statuses:

```text
pending
running
completed
completed_with_warnings
skipped
blocked
failed
invalidated
```

Current overall statuses:

```text
new
ready
running
degraded
blocked
```

Stage A initialized ledger entries for future V0 steps. V0-006 opens only the
media scan, fixed-window/PySceneDetect scene segmentation, and local
transcription foundation steps and leaves analysis, proposal, timeline,
preview, remote model, image, network, and BGM capabilities closed.

`segment` refreshes local capability detection before routing scene detection,
so installing or removing PySceneDetect after `init` is reflected in the state
ledger and current diagnostics.

`transcribe` refreshes local capability detection before routing transcription,
so installing or removing faster-whisper after `init` is reflected in the state
ledger and current diagnostics. `transcription: auto` may skip without writing
`transcripts.jsonl`; `transcription: required` fails when faster-whisper or a
local model is unavailable.

`status --json` is read-only. It reports the current ledger, local artifact
presence, source ledger summaries, clip ledger summaries, scan/clip report
presence, artifact consistency issues, and latest run metadata without
triggering scan, segment, transcribe, map, review, model calls, or network
access.

When `scan` writes a changed `.artist-portrait/data/sources.jsonl`, completed
`segment`, `transcribe`, `map`, and `review_project` steps whose input
fingerprints no longer match the source ledger are marked `invalidated`. When
`segment` writes a changed
`.artist-portrait/data/clips.jsonl`, completed `map` and `review_project` steps
whose input fingerprints no longer match are marked `invalidated`.
`doctor --json` reports those states as `segment_invalidated`,
`transcribe_invalidated`, `map_invalidated`, and `review_project_invalidated`.
It also reports `scene_detection_required_missing` when project config requires
PySceneDetect and the current environment cannot provide it.
It reports `transcription_required_missing` when project config requires
faster-whisper and the current environment cannot provide it.

`output/run_report.md` is a rebuildable status artifact. Foundation commands
that update the ledger refresh it after writing state.
