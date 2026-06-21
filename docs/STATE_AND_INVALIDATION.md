# State And Invalidation

Authoritative source: `artist_portrait_editor_revision5_optimized.md`.

The current V0-004 gate uses `.artist-portrait/state.json` as a step ledger,
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

Stage A initialized ledger entries for future V0 steps. V0-004 opens only the
media scan and fixed-window segmentation foundation steps and leaves
scene-detection segmentation, transcription, analysis, proposal, timeline,
preview, model, image, network, and BGM capabilities closed.

`status --json` is read-only. It reports the current ledger, local artifact
presence, source ledger summaries, clip ledger summaries, scan/clip report
presence, artifact consistency issues, and latest run metadata without
triggering scan, segment, map, review, model calls, or network access.

When `scan` writes a changed `.artist-portrait/data/sources.jsonl`, completed
`map` and `review_project` steps whose input fingerprints no longer match the
source ledger are marked `invalidated`. When `segment` writes a changed
`.artist-portrait/data/clips.jsonl`, completed `map` and `review_project` steps
whose input fingerprints no longer match are marked `invalidated`.
`doctor --json` reports those states as `segment_invalidated`,
`map_invalidated`, and `review_project_invalidated`.

`output/run_report.md` is a rebuildable status artifact. Foundation commands
that update the ledger refresh it after writing state.
