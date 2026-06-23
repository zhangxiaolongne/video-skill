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
- Current local gate: V0-010j proposal provider output quarantine gate only

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
- V0-006a: `TranscriptRecord` schema and committed JSON Schema.
- V0-006b: `transcribe` CLI with `features.transcription` routing for `off`,
  `auto`, and `required`.
- V0-006c: local-only faster-whisper adapter, transcript ledger validation,
  status/doctor diagnostics, and source-ledger invalidation.
- V0-007a: `KeyframeRecord` schema and committed JSON Schema.
- V0-007b: `keyframes` CLI with deterministic ffmpeg midpoint extraction for
  video clips.
- V0-007c: rebuildable keyframe cache diagnostics, audio-only handling, and
  source/clip invalidation.
- V0-008a: `AnalysisRecord` schema and committed JSON Schema.
- V0-008b: `analyze` CLI with evidence-only source/clip/transcript/keyframe
  aggregation.
- V0-008c: canonical `.artist-portrait/data/analysis.jsonl`, rebuildable
  `output/analysis_report.md`, status/doctor diagnostics, and invalidation
  from source, clip, transcript, and keyframe ledgers.
- V0-009a: `map` now requires current `analysis.jsonl`.
- V0-009b: `material_map.md` renders source and analysis distributions,
  deterministic priority review queue, pending confirmation fields, and risk
  sections.
- V0-009c: tests and `run_checks.py` now cover the analysis-led map chain.
- V0-010a: `ProposalSet` Pydantic model and committed JSON Schema.
- V0-010b: `propose` readiness command now requires `material_map.md`, blocks
  without an approved text model, records run metadata, and writes no fake
  `proposals.json` or `proposals.md`.
- V0-010c: proposal artifact status, doctor diagnostics, schema drift checks,
  and upstream invalidation coverage.
- V0-010d: `ProposalContext` schema and committed JSON Schema.
- V0-010e: blocked `propose` now writes deterministic
  `.artist-portrait/data/proposal_context.json` from local source, clip,
  analysis, and material-map evidence before returning the text-model
  dependency error.
- V0-010f: proposal context status, doctor diagnostics, BGM requirements, and
  `run_checks.py` coverage.
- V0-010g: `TextModelGate` schema and committed JSON Schema.
- V0-010h: blocked `propose` now writes deterministic
  `.artist-portrait/data/text_model_gate.json` with policy/capability reasons.
- V0-010i: even a ready text-model gate remains blocked until ProposalSet
  generation is explicitly opened and tested.
- V0-010j: `ProposalValidationReport` schema and committed JSON Schema.
- V0-010k: `review --scope proposal` now validates existing
  `.artist-portrait/data/proposals.json` against deterministic
  `.artist-portrait/data/proposal_context.json`.
- V0-010l: proposal validation writes
  `.artist-portrait/data/proposal_validation.json` and
  `output/proposal_review.md`, checking required clips, forbidden sources,
  fact references, material-map fingerprints, and BGM strategy fields.
- V0-010m: `ProposalRequestPacket` schema and committed JSON Schema.
- V0-010n: blocked `propose` now writes deterministic
  `.artist-portrait/data/proposal_request.json` after proposal context and
  text-model gate packets.
- V0-010o: proposal request status/doctor diagnostics and `run_checks.py`
  coverage without model calls or proposal generation.
- V0-010p: `ProposalAdapterCheck` schema and committed JSON Schema.
- V0-010q: blocked `propose` now writes deterministic
  `.artist-portrait/data/proposal_adapter_check.json` after proposal request.
- V0-010r: adapter preflight records no model call, no network access, allowed
  future secret sources, and plaintext secret leakage issues.
- V0-010s: `ProposalProviderRegistry` schema and committed JSON Schema.
- V0-010t: blocked `propose` now writes deterministic
  `.artist-portrait/data/proposal_provider_registry.json` with the local
  `local_mock` provider and generation closed.
- V0-010u: `ProposalMockAdapterHandshake` schema and committed JSON Schema.
- V0-010v: blocked `propose` now writes deterministic
  `.artist-portrait/data/proposal_mock_adapter_handshake.json` to validate the
  future response contract while recording no model call, no network access,
  and no generated proposal content.
- V0-010w: `ProposalProviderResultEnvelope` schema and committed JSON Schema.
- V0-010x: blocked `propose` now writes deterministic
  `.artist-portrait/data/proposal_provider_result.json` as a dry-run provider
  result envelope, recording no payload generation, no validation, no model
  call, no network access, and no generated proposal content.
- V0-010y: `ProposalExecutionAuthorization` schema and committed JSON Schema.
- V0-010z: blocked `propose` now writes deterministic
  `.artist-portrait/data/proposal_execution_authorization.json`, recording no
  approved execution gate, no user approval, no credentials, no model calls, no
  network access, no execution, no generated proposal content, and quarantine
  required for any future provider output.
- V0-010aa: `ProposalProviderOutputQuarantine` schema and committed JSON
  Schema.
- V0-010ab: blocked `propose` now writes deterministic
  `.artist-portrait/data/proposal_provider_output_quarantine.json`, recording
  no raw output capture, no parsed payload, no promotion to proposals, no
  validation, no model calls, no network access, and no generated proposal
  content.

## Current Hard Boundaries

Do not implement these until the relevant gate is explicitly opened and tested:

- OpenCV or vision analysis
- embeddings
- remote ASR, model downloads, or ungrounded text classification
- visual classification beyond explicit evidence placeholders
- keyframe interpretation beyond raw evidence references
- fake, template, or model-free creative proposals
- full creative proposal generation
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
- keep current V0-010j bounded to existing local ledgers plus proposal
  readiness, proposal request, adapter preflight, provider registry, mock
  adapter handshake, execution authorization, provider output quarantine,
  provider result envelope, and proposal validation checks; keyframes are
  visual evidence references, not visual classification

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

Next action should plan the controlled provider execution gate without
confusing it with full proposal generation. The big-version direction is
evidence-grounded creative proposals that account for BGM strategy, target
output, text, pacing, transitions, and evidence traceability. The next small
batch should define explicit execution approval and local secret-source
selection while keeping model output captured into quarantine before any
parsing, validation, or promotion to `proposals.json`. Do not open timeline,
BGM fitting, preview, OpenCV, vision, image generation/editing, API-key setup,
or model-free template proposal gates by accident.
