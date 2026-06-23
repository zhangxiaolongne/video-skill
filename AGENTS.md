# AGENTS.md

Follow `artist_portrait_editor_revision5_optimized.md` as the governing V0
engineering-freeze document.

Current gate: V0-010i proposal execution authorization gate only.

Allowed:

- `validate`
- `init`
- `status`
- `doctor`
- `scan`
- deterministic `ffmpeg` / `ffprobe` media probing
- media content hashing
- canonical `sources.jsonl`
- deterministic `scan_report.md`
- source identity, moved-file, duplicate-file, and supersedes tracking
- downstream artifact invalidation when `sources.jsonl` changes
- deterministic fixed-window `segment`
- optional PySceneDetect scene segmentation for video only when
  `features.scene_detection` is `auto` or `required`
- fixed-window fallback when `features.scene_detection: auto` and PySceneDetect
  is missing or fails
- canonical `clips.jsonl`
- deterministic `clip_report.md`
- downstream artifact invalidation when `clips.jsonl` changes
- `transcribe`
- `features.transcription` gate handling for `off`, `auto`, and `required`
- optional local-only faster-whisper transcription when available
- canonical `transcripts.jsonl`
- transcript status, doctor diagnostics, and source-ledger invalidation
- `keyframes`
- deterministic ffmpeg midpoint keyframe extraction for video clips
- canonical `keyframes.jsonl`
- rebuildable `.artist-portrait/cache/keyframes/`
- keyframe status, doctor diagnostics, and source/clip invalidation
- `analyze`
- deterministic `.artist-portrait/data/analysis.jsonl`
- deterministic `output/analysis_report.md`
- level_0/1/2 evidence-only analysis fields with null visual assertions
- analysis status, doctor diagnostics, and upstream invalidation
- `map`
- `map` requires current `analysis.jsonl`
- deterministic `output/material_map.md` rendered from source and analysis ledgers
- priority review queue, pending confirmation, and risk sections without creative recommendations
- `propose` readiness gate
- canonical `.artist-portrait/data/proposal_context.json`
- `ProposalContext` Pydantic model and generated JSON Schema
- canonical `.artist-portrait/data/text_model_gate.json`
- `TextModelGate` Pydantic model and generated JSON Schema
- canonical `.artist-portrait/data/proposal_request.json`
- `ProposalRequestPacket` Pydantic model and generated JSON Schema
- deterministic proposal model request packet construction without model calls
- canonical `.artist-portrait/data/proposal_adapter_check.json`
- `ProposalAdapterCheck` Pydantic model and generated JSON Schema
- deterministic provider/secret/model-call preflight without model calls
- canonical `.artist-portrait/data/proposal_provider_registry.json`
- canonical `.artist-portrait/data/proposal_mock_adapter_handshake.json`
- `ProposalProviderRegistry` and `ProposalMockAdapterHandshake` Pydantic models and generated JSON Schema
- deterministic local mock adapter handshake without model calls or proposal content
- canonical `.artist-portrait/data/proposal_provider_result.json`
- `ProposalProviderResultEnvelope` Pydantic model and generated JSON Schema
- deterministic provider result envelope without payload generation, validation, model calls, network access, or proposal content
- canonical `.artist-portrait/data/proposal_execution_authorization.json`
- `ProposalExecutionAuthorization` Pydantic model and generated JSON Schema
- deterministic provider execution authorization packet without credentials, user approval, model calls, network access, execution, or proposal content
- `ProposalSet` Pydantic model and generated JSON Schema
- canonical `.artist-portrait/data/proposal_validation.json`
- deterministic `output/proposal_review.md`
- `ProposalValidationReport` Pydantic model and generated JSON Schema
- `review --scope proposal` for deterministic validation of existing proposals
- proposal artifact status and doctor diagnostics
- text-model gate status and doctor diagnostics
- blocked `propose` behavior that writes proposal context but no proposals
- blocked `propose` behavior that writes text-model gate reasons but no model call
- blocked `propose` behavior when no approved text model is available
- `review --scope project`
- `review --scope all` only as project review plus skipped future scopes
- repository skeleton
- Pydantic models
- generated JSON Schema
- CLI framework
- state ledger
- capability detection
- fixed exit codes
- Stage A and media-scan fixtures

Forbidden before the next gate explicitly opens:

- remote ASR, model-downloading transcription, or ungrounded text classification
- OpenCV analysis
- embeddings
- vision models
- visual classification beyond explicit evidence placeholders
- fake, template, or model-free creative proposals
- full creative proposal generation
- timeline generation
- preview rendering
- BGM selection, beat analysis, music recommendation, or music/timeline fitting
- network search
- image generation or image editing
- model calls
