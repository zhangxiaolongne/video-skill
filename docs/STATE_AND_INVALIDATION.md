# State And Invalidation

Authoritative source: `artist_portrait_editor_revision5_optimized.md`.

The current V0-010h gate uses `.artist-portrait/state.json` as a step ledger,
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

Stage A initialized ledger entries for future V0 steps. V0-010h opens only the
media scan, fixed-window/PySceneDetect scene segmentation, local transcription,
keyframe cache, evidence-only basic analysis, and analysis-led material map
foundation steps plus proposal readiness checks, deterministic proposal request
packet construction, deterministic proposal adapter preflight, and deterministic
provider registry/mock handshake, dry-run provider result envelope, and
deterministic validation of existing proposal sets. It leaves visual
classification, full proposal generation, timeline, preview, remote model,
image, network, and BGM capabilities closed.

`segment` refreshes local capability detection before routing scene detection,
so installing or removing PySceneDetect after `init` is reflected in the state
ledger and current diagnostics.

`transcribe` refreshes local capability detection before routing transcription,
so installing or removing faster-whisper after `init` is reflected in the state
ledger and current diagnostics. `transcription: auto` may skip without writing
`transcripts.jsonl`; `transcription: required` fails when faster-whisper or a
local model is unavailable.

`keyframes` refreshes local capability detection before extracting video
keyframes. Video clips require ffmpeg. Audio-only clip ledgers produce an empty
keyframe manifest with a warning. Cached images are rebuildable, while
`.artist-portrait/data/keyframes.jsonl` is canonical.

`analyze` reads the current clip ledger and optionally consumes existing
transcript and keyframe ledgers. It writes canonical
`.artist-portrait/data/analysis.jsonl` and rebuildable
`output/analysis_report.md`. It does not run OpenCV, vision models, embeddings,
text models, BGM logic, proposals, timelines, previews, image tools, or network
search.

`map` requires current `.artist-portrait/data/analysis.jsonl` and writes
rebuildable `output/material_map.md`. It is a deterministic reporting step and
does not create canonical data.

`propose` currently requires `output/material_map.md`, writes deterministic
`.artist-portrait/data/proposal_context.json`, writes deterministic
`.artist-portrait/data/text_model_gate.json`, writes deterministic
`.artist-portrait/data/proposal_request.json`, writes deterministic
`.artist-portrait/data/proposal_adapter_check.json`, writes deterministic
`.artist-portrait/data/proposal_provider_registry.json`, writes deterministic
`.artist-portrait/data/proposal_mock_adapter_handshake.json`, writes
deterministic `.artist-portrait/data/proposal_provider_result.json`, and then
requires an explicitly opened generation gate. Without that gate it marks the `propose` step
`blocked`, records run metadata, returns dependency exit code 4, and writes no
fake `proposals.json` or `proposals.md`.

`status --json` is read-only. It reports the current ledger, local artifact
presence, source ledger summaries, clip ledger summaries, scan/clip report
presence, analysis summaries, proposal summaries, artifact consistency issues,
and latest run metadata without triggering scan, segment, transcribe,
keyframes, analyze, map, propose, review, model calls, or network access.

When `scan` writes a changed `.artist-portrait/data/sources.jsonl`, completed
`segment`, `transcribe`, `keyframes`, `analyze`, `map`, and `review_project`
steps whose input fingerprints no longer match the source ledger are marked
`invalidated`. When `segment` writes a changed
`.artist-portrait/data/clips.jsonl`, completed `keyframes`, `analyze`, `map`,
and `review_project` steps whose input fingerprints no longer match are marked
`invalidated`. When transcript or keyframe ledgers change, completed `analyze`,
`map`, `propose`, and `review_project` steps that depended on older evidence
are marked `invalidated`. When `analysis.jsonl` changes, completed `map`,
`propose`, and `review_project` steps are marked `invalidated`. When
`material_map.md` changes, old completed or blocked `propose` state is marked
`invalidated`.

`review --scope proposal` requires current `proposal_context.json` and
`proposals.json`, writes canonical
`.artist-portrait/data/proposal_validation.json`, writes rebuildable
`output/proposal_review.md`, and records `review_proposal` as completed or
completed with warnings. It validates references and BGM strategy fields only;
it does not call models, select music, or create proposal content.

`doctor --json` reports those states as `segment_invalidated`,
`transcribe_invalidated`, `keyframes_invalidated`, `analyze_invalidated`,
`map_invalidated`, and `review_project_invalidated`.
It also reports `scene_detection_required_missing` when project config requires
PySceneDetect and the current environment cannot provide it.
It reports `transcription_required_missing` when project config requires
faster-whisper and the current environment cannot provide it.
It reports `keyframes_invalid` for malformed keyframe manifests and
`keyframe_cache_missing` when rebuildable cache images referenced by the
manifest are absent.
It reports `analysis_invalid` for malformed analysis manifests and
`analysis_pending` when clips exist but analysis has not been generated.
It reports `proposal_context_invalid` for malformed proposal context packets,
`text_model_gate_invalid` for malformed text-model gate packets,
`proposal_request_invalid` for malformed proposal request packets,
`proposal_adapter_check_invalid` for malformed adapter preflight packets,
`proposal_provider_registry_invalid` for malformed provider registry packets,
`proposal_mock_adapter_handshake_invalid` for malformed mock handshake packets,
`proposal_provider_result_invalid` for malformed provider result envelopes,
`proposals_invalid` for malformed proposal sets, and
`propose_text_model_missing` when a material map exists but the text-model
proposal gate is unavailable.

`output/run_report.md` is a rebuildable status artifact. Foundation commands
that update the ledger refresh it after writing state.
