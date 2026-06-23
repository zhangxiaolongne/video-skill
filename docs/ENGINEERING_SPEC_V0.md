# Engineering Spec V0

Authoritative source: `artist_portrait_editor_revision5_optimized.md`.

Stage A historical implementation scope:

- repository skeleton
- Pydantic models
- generated JSON Schema
- CLI framework
- state ledger
- capability detection
- fixed exit codes
- Stage A fixtures
- `validate`
- `init`
- `status`

Required Stage A properties:

- `validate` can run before initialization and does not write project files.
- `init` validates config before creating a workspace.
- `init` does not read or analyze media.
- `init` does not create business artifacts such as `sources.jsonl`,
  `clips.jsonl`, `material_map.md`, `proposals.md`, or `timeline_draft.json`.
- missing FFmpeg/ffprobe is a warning for `init`, not a fatal error.
- state and run records are auditable.
- repeated `init` does not cross the Stage A boundary.

Current V0-010m implementation scope additionally allows:

- `scan`
- deterministic `sources.jsonl`
- deterministic `scan_report.md`
- fixed-window `segment`
- optional PySceneDetect video scene segmentation through
  `features.scene_detection`
- fixed-window fallback for `scene_detection: auto`
- deterministic `clips.jsonl`
- deterministic `clip_report.md`
- local-only faster-whisper gated `transcribe`
- deterministic `transcripts.jsonl`
- deterministic `keyframes`
- canonical `keyframes.jsonl`
- rebuildable `.artist-portrait/cache/keyframes/`
- deterministic evidence-only `analyze`
- canonical `analysis.jsonl`
- rebuildable `analysis_report.md`
- analysis-led `map`
- `material_map.md` rendered from source and analysis ledgers
- `ProposalContext` Pydantic model and generated JSON Schema
- deterministic `.artist-portrait/data/proposal_context.json`
- `TextModelGate` Pydantic model and generated JSON Schema
- deterministic `.artist-portrait/data/text_model_gate.json`
- blocked text-model gate diagnostics without model calls
- `ProposalRequestPacket` Pydantic model and generated JSON Schema
- deterministic `.artist-portrait/data/proposal_request.json`
- proposal model request packet construction without model calls
- `ProposalAdapterCheck` Pydantic model and generated JSON Schema
- deterministic `.artist-portrait/data/proposal_adapter_check.json`
- provider/secret/model-call preflight without model calls or network
- `ProposalProviderRegistry` Pydantic model and generated JSON Schema
- `ProposalMockAdapterHandshake` Pydantic model and generated JSON Schema
- deterministic `.artist-portrait/data/proposal_provider_registry.json`
- deterministic `.artist-portrait/data/proposal_mock_adapter_handshake.json`
- local mock adapter handshake without model calls or proposal content
- `ProposalExecutionApprovalRequest` Pydantic model and generated JSON Schema
- deterministic `.artist-portrait/data/proposal_execution_approval_request.json`
- execution approval request packet without recorded approval, selected secret
  source, credential reading, model calls, network access, execution, or
  proposal content
- `ProposalExecutionApprovalRecord` Pydantic model and generated JSON Schema
- deterministic `.artist-portrait/data/proposal_execution_approval_record.json`
- execution approval record packet without granted approval, selected secret
  source, credential reading, model calls, network access, execution allowance,
  execution, or proposal content
- `ProposalExecutionReadinessPlan` Pydantic model and generated JSON Schema
- deterministic `.artist-portrait/data/proposal_execution_readiness_plan.json`
- execution readiness plan packet covering secret-source selection, credential
  access, execution planning, provider call preflight, and output capture
  planning without selected secrets, credential reads, model calls, network
  access, execution allowance, execution, raw output capture, or proposal
  content
- `ProposalExecutionAuthorization` Pydantic model and generated JSON Schema
- deterministic `.artist-portrait/data/proposal_execution_authorization.json`
- execution authorization packet without credentials, user approval, model
  calls, network access, execution, or proposal content
- `ProposalProviderOutputQuarantine` Pydantic model and generated JSON Schema
- deterministic `.artist-portrait/data/proposal_provider_output_quarantine.json`
- provider output quarantine packet without raw output capture, payload
  parsing, proposal promotion, validation, model calls, network access, or
  proposal content
- `ProposalProviderResultEnvelope` Pydantic model and generated JSON Schema
- deterministic `.artist-portrait/data/proposal_provider_result.json`
- dry-run provider result envelope without payload generation, validation,
  model calls, network access, or proposal content
- `ProposalSet` Pydantic model and generated JSON Schema
- `propose` readiness gate requiring `material_map.md`
- blocked `propose` state when no approved text model is available
- proposal artifact status and doctor diagnostics
- `ProposalValidationReport` Pydantic model and generated JSON Schema
- deterministic `.artist-portrait/data/proposal_validation.json`
- deterministic `output/proposal_review.md`
- `review --scope proposal` validation of existing proposal sets against the
  prepared proposal context
- minimal `review --scope project`
- read-only `doctor`
- source, clip, transcript, keyframe, analysis, map, and proposal invalidation
  diagnostics
