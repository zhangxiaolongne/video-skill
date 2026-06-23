---
name: artist-portrait-editor
description: Local workflow for artist portrait video projects. Use when Codex needs to validate config, init state, scan media into source ledger and scan report, segment into a fixed-window or PySceneDetect-gated clip ledger, transcribe through a local transcript ledger, extract keyframe ledger/cache, run evidence-only analysis ledger/report, generate an analysis-led material map, prepare ProposalContext schema, run the blocked propose gate with TextModelGate schema, ProposalRequestPacket schemas, ProposalAdapterCheck schema, ProposalProviderRegistry schema, ProposalMockAdapterHandshake schema, ProposalExecutionApprovalRequest/Record schema, ProposalExecutionReadinessPlan schema, ProposalExecutionAuthorization schema, ProposalProviderOutputQuarantine schema, ProposalProviderResultEnvelope schema, validate existing ProposalSet schema outputs with ProposalValidationReport schema, run review/doctor, preserve boundaries before BGM selection, timeline generation, preview rendering, model calls, image tools, network search.
---

# Artist Portrait Editor

Use this skill to operate the local `artist-portrait` CLI for deterministic
artist portrait project preparation and audit work.

## Operating Order

1. Read `project.yaml` and run validation:

   ```bash
   artist-portrait validate --project ./project.yaml
   ```

2. Initialize local state before any other workspace command:

   ```bash
   artist-portrait init --project ./project.yaml
   ```

3. Inspect current state and diagnostics:

   ```bash
   artist-portrait status --project ./project.yaml --json
   artist-portrait doctor --project ./project.yaml --json
   ```

4. Scan local media only when `ffmpeg` and `ffprobe` are available:

   ```bash
   artist-portrait scan --project ./project.yaml
   ```

   This writes `.artist-portrait/data/sources.jsonl` and
   `output/scan_report.md`.

5. Generate deterministic local reports from `.artist-portrait/data/sources.jsonl`:

   ```bash
   artist-portrait segment --project ./project.yaml
   artist-portrait transcribe --project ./project.yaml
   artist-portrait keyframes --project ./project.yaml
   artist-portrait analyze --project ./project.yaml
   artist-portrait map --project ./project.yaml
   artist-portrait review --project ./project.yaml --scope project
   ```

   `segment` writes `.artist-portrait/data/clips.jsonl` and
   `output/clip_report.md`. Videos use `features.scene_detection`:
   `off` keeps fixed-window segmentation, `auto` uses PySceneDetect when
   available and falls back to fixed-window with a warning, and `required`
   fails with exit code 4 when PySceneDetect is missing or fails. Audio always
   uses fixed-window segmentation.

   `transcribe` writes `.artist-portrait/data/transcripts.jsonl` only when
   `features.transcription` allows it and local faster-whisper plus a local
   model are available. `off` marks the step skipped, `auto` skips with a
   warning when faster-whisper is unavailable or local model loading fails, and
   `required` fails with exit code 4 in those cases. It must not download
   models or invent transcript text.

   `keyframes` reads `.artist-portrait/data/clips.jsonl`, extracts one
   deterministic midpoint frame for each video clip via ffmpeg, writes
   `.artist-portrait/data/keyframes.jsonl`, and stores images under
   `.artist-portrait/cache/keyframes/`. Audio clips do not require keyframes.
   Cache files may be deleted and rebuilt; the JSONL manifest is the canonical
   record.

   `analyze` reads `.artist-portrait/data/clips.jsonl` and optionally uses
   existing `transcripts.jsonl` and `keyframes.jsonl` as evidence. It writes
   `.artist-portrait/data/analysis.jsonl` and `output/analysis_report.md`.
   Current analysis is evidence-only: media/material type and original audio
   usability are recorded from existing ledgers, while shot size, camera
   motion, emotion, action, and visual quality remain null or empty candidates.

   `map` requires a current `.artist-portrait/data/analysis.jsonl`. It writes
   `output/material_map.md` with material distributions, a deterministic
   priority review queue, pending confirmation fields, and risk sections. It
   does not generate creative recommendations.

   `propose` is currently a readiness gate only:

   ```bash
   artist-portrait propose --project ./project.yaml
   ```

   It requires `output/material_map.md`, writes deterministic
   `.artist-portrait/data/proposal_context.json`, writes
   `.artist-portrait/data/text_model_gate.json`, writes
   `.artist-portrait/data/proposal_request.json`, writes
   `.artist-portrait/data/proposal_adapter_check.json`, writes
   `.artist-portrait/data/proposal_provider_registry.json`, writes
   `.artist-portrait/data/proposal_mock_adapter_handshake.json`, writes
   `.artist-portrait/data/proposal_execution_approval_request.json`, writes
   `.artist-portrait/data/proposal_execution_approval_record.json`, writes
   `.artist-portrait/data/proposal_execution_readiness_plan.json`, writes
   `.artist-portrait/data/proposal_execution_authorization.json`, writes
   `.artist-portrait/data/proposal_provider_output_quarantine.json`, writes
   `.artist-portrait/data/proposal_provider_result.json`, and then requires an
   approved text-model gate plus an explicitly opened generation gate. Current
   generation remains closed even when the gate is ready. It records `propose`
   as blocked, returns exit code 4, and writes no fake
   `.artist-portrait/data/proposals.json` or `output/proposals.md`.

   Existing proposals can be validated deterministically:

   ```bash
   artist-portrait review --project ./project.yaml --scope proposal
   ```

   This reads `.artist-portrait/data/proposal_context.json` and
   `.artist-portrait/data/proposals.json`, writes
   `.artist-portrait/data/proposal_validation.json` and
   `output/proposal_review.md`, and checks proposal IDs, clip refs, fact refs,
   forbidden sources, and BGM strategy fields. It does not generate proposals.

6. Use `review --scope all` only as a shallow aggregate. It runs project review
   and marks timeline review as skipped; proposal review is available only as a
   deterministic validation pass over existing proposal artifacts.

## Diagnostics

- Use `doctor --json` before deciding the next command.
- Treat `recommended_commands` as guidance, not automatic repair.
- Treat `missing_output_ref` as a rebuild signal for the step that produced the
  missing artifact.
- Treat `source_ledger_invalid` as a stop condition until
  `.artist-portrait/data/sources.jsonl` is fixed or regenerated.
- Treat `map_invalidated` and `review_project_invalidated` as rebuild signals
  after a newer scan changes the source ledger.
- Treat `segment_invalidated` as a rebuild signal after a newer scan changes
  the source ledger.
- Treat `clips_invalid` as a stop condition until `.artist-portrait/data/clips.jsonl`
  is fixed or regenerated.
- Treat `scene_detection_required_missing` as a dependency stop condition:
  install PySceneDetect or change `features.scene_detection` to `auto`/`off`.
- Treat `transcripts_invalid` as a stop condition until
  `.artist-portrait/data/transcripts.jsonl` is fixed or regenerated.
- Treat `transcription_required_missing` as a dependency stop condition:
  install faster-whisper/local model or change `features.transcription` to
  `auto`/`off`.
- Treat `transcribe_invalidated` as a rebuild signal after a newer scan changes
  the source ledger.
- Treat `keyframes_invalid` as a stop condition until
  `.artist-portrait/data/keyframes.jsonl` is fixed or regenerated.
- Treat `keyframe_cache_missing` as a rebuild signal for
  `.artist-portrait/cache/keyframes/`.
- Treat `keyframes_invalidated` as a rebuild signal after a newer scan or
  segment changes upstream ledgers.
- Treat `analysis_invalid` as a stop condition until
  `.artist-portrait/data/analysis.jsonl` is fixed or regenerated.
- Treat `analysis_pending` as a signal to run
  `artist-portrait analyze --project ./project.yaml` after clips exist.
- Treat `analyze_invalidated` as a rebuild signal after newer source, clip,
  transcript, or keyframe ledgers change.
- Treat `map_pending` as a signal to run
  `artist-portrait map --project ./project.yaml` after analysis exists.
- Treat `map_invalidated` as a rebuild signal after newer source, clip,
  transcript, keyframe, or analysis ledgers change.
- Treat `proposals_invalid` as a stop condition until
  `.artist-portrait/data/proposals.json` is fixed or regenerated by a later
  approved proposal generation gate.
- Treat `proposal_context_invalid` as a stop condition until
  `.artist-portrait/data/proposal_context.json` is fixed or regenerated.
- Treat `text_model_gate_invalid` as a stop condition until
  `.artist-portrait/data/text_model_gate.json` is fixed or regenerated.
- Treat `propose_text_model_missing` as a dependency stop condition. Do not
  produce fake proposals; open the approved text-model proposal gate first.
- Treat `proposal_provider_registry_invalid` as a stop condition until
  `.artist-portrait/data/proposal_provider_registry.json` is fixed or
  regenerated.
- Treat `proposal_mock_adapter_handshake_invalid` as a stop condition until
  `.artist-portrait/data/proposal_mock_adapter_handshake.json` is fixed or
  regenerated.
- Treat `proposal_execution_approval_request_invalid` as a stop condition until
  `.artist-portrait/data/proposal_execution_approval_request.json` is fixed or
  regenerated.
- Treat `proposal_execution_approval_record_invalid` as a stop condition until
  `.artist-portrait/data/proposal_execution_approval_record.json` is fixed or
  regenerated.
- Treat `proposal_execution_readiness_plan_invalid` as a stop condition until
  `.artist-portrait/data/proposal_execution_readiness_plan.json` is fixed or
  regenerated.
- Treat `proposal_provider_result_invalid` as a stop condition until
  `.artist-portrait/data/proposal_provider_result.json` is fixed or
  regenerated.
- Treat `proposal_execution_authorization_invalid` as a stop condition until
  `.artist-portrait/data/proposal_execution_authorization.json` is fixed or
  regenerated.
- Treat `proposal_provider_output_quarantine_invalid` as a stop condition until
  `.artist-portrait/data/proposal_provider_output_quarantine.json` is fixed or
  regenerated.

## Hard Boundaries

Do not perform these actions through this skill in the current local foundation
gate. A later validated gate may use mature third-party tools, installed Codex
skills, plugins, search, image generation/editing tools, models, or media
libraries instead of rebuilding those capabilities from scratch:

- remote ASR, model-downloading transcription, or ungrounded text classification
- OpenCV, visual analysis, or visual classification
- embeddings
- visual classification beyond explicit evidence placeholders
- BGM selection, beat analysis, music recommendation, or music/timeline fitting
- fake, template, or model-free creative proposals
- full creative proposal generation
- timeline generation
- preview rendering
- model calls
- network search
- image generation or image editing

Keep all current foundation outputs local and deterministic.
