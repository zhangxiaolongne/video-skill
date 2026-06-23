# Data Contracts

Authoritative source: `artist_portrait_editor_revision5_optimized.md`.

Pydantic models are the schema truth source. JSON Schema must be generated from
Pydantic, not manually maintained as an independent contract.

Current committed schemas:

- `schemas/analysis_record.schema.json`
- `schemas/clip_record.schema.json`
- `schemas/keyframe_record.schema.json`
- `schemas/project_config.schema.json`
- `schemas/project_state.schema.json`
- `schemas/proposal_context.schema.json`
- `schemas/proposal_request_packet.schema.json`
- `schemas/proposal_validation_report.schema.json`
- `schemas/proposal_set.schema.json`
- `schemas/source_record.schema.json`
- `schemas/text_model_gate.schema.json`
- `schemas/transcript_record.schema.json`

Current contract tests assert that committed schemas match live Pydantic schema
generation.

`SourceRecord` is implemented for the media scan foundation and is written as
JSON Lines to `.artist-portrait/data/sources.jsonl` by `scan`.

`output/scan_report.md` is a rebuildable report rendered from the current
source ledger, local content hashes, `sources.csv` metadata, and ffprobe-derived
media facts. It is not canonical data; `sources.jsonl` remains the canonical
source ledger.

`ClipRecord` is implemented for the segmentation foundation and is written as
JSON Lines to `.artist-portrait/data/clips.jsonl` by `segment`. Current method
values are `fixed_window` and `pyscenedetect`.

`output/clip_report.md` is a rebuildable report rendered from the current clip
ledger and selected segmentation output. It is not canonical data; `clips.jsonl`
remains the canonical clip ledger.

`TranscriptRecord` is implemented for the local transcription gate and is
written as JSON Lines to `.artist-portrait/data/transcripts.jsonl` by
`transcribe`. It records audible text candidates with source identity,
timestamps, method, method version, confidence, evidence, and optional word
timestamps. `text_type` remains `null` unless a later gate or user confirmation
classifies the transcript as interview, lyrics, role dialogue, captions, or
another text type.

`KeyframeRecord` is implemented for the keyframe cache gate and is written as
JSON Lines to `.artist-portrait/data/keyframes.jsonl` by `keyframes`. It records
clip/source identity, source hash, clip fingerprint, timestamp, cache image
path, method, method version, and evidence. Cached image files under
`.artist-portrait/cache/keyframes/` are rebuildable; the JSONL manifest is the
canonical data.

`AnalysisRecord` is implemented for the V0-008 basic evidence analysis gate and
is written as JSON Lines to `.artist-portrait/data/analysis.jsonl` by
`analyze`. It records clip/source identity, clip and analysis fingerprints,
material type, original audio usability, transcript refs, keyframe refs, and
risk flags. Shot size, camera motion, emotion candidates, action candidates,
and visual quality use the common assertion structure but remain `null` or
empty candidates with `method: not_run_current_gate` until a later visual
analysis gate opens.

`output/analysis_report.md` is a rebuildable report rendered from
`analysis.jsonl`; the JSONL ledger is canonical.

`output/material_map.md` is implemented for the V0-009 analysis-led material map
gate. It is rendered from `sources.jsonl` and `analysis.jsonl`, includes
distribution, priority review, pending confirmation, and risk sections, and is
not canonical data.

`ProposalContext` is implemented for the V0-010b proposal context gate and has
a committed schema at `schemas/proposal_context.schema.json`. It is written to
`.artist-portrait/data/proposal_context.json` by `propose` before text-model
generation is attempted. It contains deterministic project brief, content
policy, source/clip/analysis summaries, evidence refs, required proposal IDs,
BGM requirements, and blocked capabilities. It is not a creative proposal.

`TextModelGate` is implemented for the V0-010c text model gate contract and has
a committed schema at `schemas/text_model_gate.schema.json`. It is written to
`.artist-portrait/data/text_model_gate.json` by `propose` after
`proposal_context.json`. It records project text-model policy, detected
text-model capability, absolute-path policy, status, blocking reasons, and
required next steps. It does not execute or authorize a model call by itself.

`ProposalRequestPacket` is implemented for the V0-010e proposal request gate
and has a committed schema at `schemas/proposal_request_packet.schema.json`.
It is written to `.artist-portrait/data/proposal_request.json` by `propose`
after `proposal_context.json` and `text_model_gate.json`. It defines the
future model adapter request contract, prompt strings, required proposal IDs,
BGM requirements, validation requirements, blocking reasons, and target
`ProposalSet` schema reference. It is not sent to a model in the current gate.

`ProposalSet` is implemented for the V0-010a proposal readiness gate and has a
committed schema at `schemas/proposal_set.schema.json`. A future approved
proposal generation gate may write `.artist-portrait/data/proposals.json`, but
the current gate only validates the contract and diagnoses invalid proposal
artifacts if they already exist. `propose` must not create fake
`proposals.json` or `output/proposals.md` when no approved text model is
available.

`ProposalValidationReport` is implemented for the V0-010d proposal validation
gate and has a committed schema at
`schemas/proposal_validation_report.schema.json`. It is written to
`.artist-portrait/data/proposal_validation.json` by
`review --scope proposal`, alongside rebuildable `output/proposal_review.md`.
It records deterministic validation issues for existing proposal sets and does
not generate, repair, rank, or creatively improve proposals.

Diagnostic issues are plain JSON objects used by `status`, `review`, and
`doctor`. Current common fields:

- `scope`: issue domain, such as `source`, `artifact`, `workspace`, or
  `review_scope`
- `code`: stable machine-readable issue code
- `severity`: `info`, `warning`, or `error`
- `detail`: human-readable explanation
- `next_action`: optional command or remediation hint

Scope-specific fields are allowed when needed, including `source_id`,
`location`, `step`, `ref`, and `review_scope`.

Current stable diagnostic codes include:

- `missing_output_ref`
- `source_ledger_invalid`
- `map_pending`
- `segment_pending`
- `review_project_pending`
- `clips_invalid`
- `transcripts_invalid`
- `keyframes_invalid`
- `keyframe_cache_missing`
- `analysis_invalid`
- `proposal_context_invalid`
- `text_model_gate_invalid`
- `proposal_request_invalid`
- `proposals_invalid`
- `proposal_unknown_clip_id`
- `proposal_unknown_fact_ref`
- `proposal_missing_bgm_strategy`
- `propose_text_model_missing`
- `scene_detection_required_missing`
- `transcription_required_missing`
- `segment_invalidated`
- `transcribe_invalidated`
- `keyframes_invalidated`
- `analyze_invalidated`
- `map_invalidated`
- `review_project_invalidated`
- `review_scope_skipped`

Canonical contracts such as `relations.jsonl` remain specified in the master
document but intentionally not implemented yet. `proposals.json` has a schema
contract, but full generation remains closed until the text-model proposal gate
opens.
