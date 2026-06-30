---
name: artist-portrait-editor
description: Artist portrait video workflow. Use when Codex needs deterministic media ledgers, evidence analysis, analysis-led material map, Codex/ChatGPT host Agent proposals quarantined, validated, reviewed, and atomically promoted, explicit timeline generation, multi-source BGM fitting, BGM rhythm intelligence, preview/final export, acceptance reporting, repair handoff/evidence intake, BGM/edit rhythm planning, rhythm QC, guided workflow plans, workflow execution evidence review, workflow evidence repair planning, workflow repair approval/dry-run packaging, workflow repair execution evidence review, workflow repair evidence refresh guidance, or release hardening audits, all without paid APIs, API keys, or network calls. Covers validation, review/doctor, and boundaries before automatic music selection, beat-synced editing, vision, image tools, automatic repair execution, or rhythm-triggered edit mutation.
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

4. Ask for the guided workflow path when the next command is unclear:

   ```bash
   artist-portrait workflow --project ./project.yaml --target delivery --json
   ```

   The workflow command writes `.artist-portrait/data/workflow_plan.json`,
   `output/workflow_plan.md`, and `output/workflow_agent_handoff.json`. It
   orders explicit commands for `core`, `preview`, or `delivery` targets. It
   does not execute commands, render media, move edit points, select music, fit
   music, call models from the CLI, or access the network.

   To review explicit external workflow execution evidence, import a record
   candidate:

   ```bash
   artist-portrait workflow --project ./project.yaml --target delivery --execution-record ./workflow_execution_record.json --json
   ```

   This quarantines the candidate byte-for-byte, then writes
   `.artist-portrait/data/workflow_execution_review.json`,
   `output/workflow_execution_review.md`, and
   `output/workflow_execution_handoff.json`. It validates plan, step, command,
   and artifact evidence bindings. It does not execute commands or treat
   execution evidence as acceptance success.

   To convert rejected or missing workflow execution evidence into manual next
   commands:

   ```bash
   artist-portrait workflow --project ./project.yaml --target delivery --repair-plan --json
   ```

   This writes `.artist-portrait/data/workflow_repair_plan.json`,
   `output/workflow_repair_plan.md`, and
   `output/workflow_repair_handoff.json`. It does not execute repair commands
   or promote acceptance success.

   To request approval and build a dry-run manifest for workflow repair:

   ```bash
   artist-portrait workflow --project ./project.yaml --target delivery --approval-request --json
   artist-portrait workflow --project ./project.yaml --target delivery --approval-record ./workflow_repair_approval_record.json --json
   artist-portrait workflow --project ./project.yaml --target delivery --repair-dry-run --json
   ```

   These commands package approval and dry-run artifacts only. They do not
   execute repair commands or promote acceptance success.

   To review explicit external workflow repair execution evidence after a
   dry-run:

   ```bash
   artist-portrait workflow --project ./project.yaml --target delivery --repair-execution-record ./workflow_repair_execution_record.json --json
   ```

   This quarantines the candidate byte-for-byte, then writes
   `.artist-portrait/data/workflow_repair_execution_review.json`,
   `output/workflow_repair_execution_review.md`, and
   `output/workflow_repair_execution_handoff.json`. It validates dry-run,
   approval, repair-plan, action, command, and artifact evidence bindings. It
   does not execute repair commands or treat repair execution evidence as
   acceptance success.

   To package reviewed repair evidence for the next explicit workflow
   execution record:

   ```bash
   artist-portrait workflow --project ./project.yaml --target delivery --repair-refresh-plan --json
   ```

   This writes `.artist-portrait/data/workflow_repair_refresh_plan.json`,
   `output/workflow_repair_refresh_plan.md`, and
   `output/workflow_repair_refresh_handoff.json`. It does not execute workflow
   commands, mutate workflow plans, or treat refreshed evidence as acceptance
   success.

5. Before any local release, run release hardening:

   ```bash
   artist-portrait release-check --project ./project.yaml --json
   ```

   This writes `.artist-portrait/data/release_hardening_report.json` and
   `output/release_hardening_report.md`. It audits current-gate docs, git
   publication state, schema coverage, forbidden source surfaces,
   workflow/rhythm artifact coverage, and validation evidence. It does not
   commit, push, tag, render media, call models, access the network, execute
   repair commands, or mark acceptance success.

6. Scan local media only when `ffmpeg` and `ffprobe` are available:

   ```bash
   artist-portrait scan --project ./project.yaml
   ```

   This writes `.artist-portrait/data/sources.jsonl` and
   `output/scan_report.md`.

7. Generate deterministic local reports from `.artist-portrait/data/sources.jsonl`:

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

   `propose` prepares a self-contained host-Agent handoff:

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
   `.artist-portrait/data/proposal_execution_input_bundle.json`, writes
   `.artist-portrait/data/proposal_provider_call_dry_run.json`, writes
   `.artist-portrait/data/proposal_execution_authorization.json`, writes
   `.artist-portrait/data/proposal_provider_response_intake_plan.json`, writes
   `.artist-portrait/data/proposal_provider_output_quarantine.json`, writes
   `.artist-portrait/data/proposal_provider_response_validation_plan.json`,
   writes
   `.artist-portrait/data/proposal_promotion_authorization_plan.json`, writes
   `.artist-portrait/data/proposal_promotion_validation_report.json`, writes
   `.artist-portrait/data/proposal_canonical_write_transaction_plan.json`,
   writes
   `.artist-portrait/data/proposal_provider_result.json`, and
   `output/proposal_agent_handoff.json`.

   Read the handoff, use the current Codex/ChatGPT reasoning capability to
   create exactly one `ProposalSet` JSON object, write it to a local candidate
   file, then run:

   ```bash
   artist-portrait propose --project ./project.yaml \
     --agent-output ./proposal_candidate.json
   ```

   The CLI quarantines exact candidate bytes before parsing, validates schema,
   evidence, policy, proposal differentiation, and BGM strategy, then atomically
   writes `.artist-portrait/data/proposals.json` only when all error-level
   checks pass. Never request an API key or call a paid/remote model for this
   workflow.

   Existing proposals can be validated deterministically:

   ```bash
   artist-portrait review --project ./project.yaml --scope proposal
   ```

   This reads `.artist-portrait/data/proposal_context.json` and
   `.artist-portrait/data/proposals.json`, writes
   `.artist-portrait/data/proposal_validation.json` and
   `output/proposal_review.md`, and checks proposal IDs, clip refs, fact refs,
   forbidden sources, and BGM strategy fields. It does not generate proposals.

6. Use `review --scope all` only as a shallow project aggregate. Use the
   dedicated proposal, timeline, and preview scopes for canonical artifact
   validation.

7. After the user explicitly chooses one canonical proposal, generate and
   review the timeline:

   ```bash
   artist-portrait timeline --project ./project.yaml \
     --proposal proposal_safe
   artist-portrait review --project ./project.yaml --scope timeline
   ```

   Replace `proposal_safe` only with the user's selected
   `proposal_advanced` or `proposal_risky`. Never choose on the user's behalf.
   The command writes `output/timeline_draft.json`,
   `.artist-portrait/data/timeline_validation.json`, and
   `output/timeline_review.md`. It preserves an unresolved or policy-disabled
   music slot but performs no BGM selection, extraction, beat analysis, fitting,
   preview, final render, model call, or network request.

## BGM Workflow

V0-013 accepts music through these input modes:

- `direct_audio`: a directly uploaded complete or partial audio track
- `video_audio_extract`: a selected stream and range from an uploaded video
- `source_embedded_audio`: original audio or music already attached to source media
- `multiple_candidates`: multiple retained candidates for separate proposal/output evaluation
- `none_yet`: an unresolved music slot while rhythm and sound structure are planned

Every candidate must retain source identity, media kind, extraction range,
stream index, content hash, duration, rights status, user intent, analysis
status, and possible speech, vocal, environment, or sound-effect content.
Audio extracted from video is mixed audio unless explicit separation or
analysis proves otherwise. Never label extraction alone as clean BGM,
instrumental, or pure accompaniment. Extraction, transcoding, separation, and
analysis outputs belong in rebuildable cache; the original candidate remains
traceable.

Use:

```bash
artist-portrait bgm import --project ./project.yaml --file media/song.wav
artist-portrait bgm import --project ./project.yaml \
  --file media/source-video.mp4 --extract-in 0 --extract-out 30
artist-portrait bgm import --project ./project.yaml --source-id <source-id>
artist-portrait bgm list --project ./project.yaml
artist-portrait bgm recommend --project ./project.yaml
artist-portrait bgm rhythm --project ./project.yaml
artist-portrait bgm select --project ./project.yaml --recommendation-id <id>
artist-portrait bgm fit --project ./project.yaml --candidate <candidate-id> \
  --fit-mode auto --fade-in-seconds 0.5 --fade-out-seconds 1.0 \
  --ducking-gain-db -9
artist-portrait bgm review --project ./project.yaml
```

The user must select the candidate. The CLI may normalize/extract locally,
measure loudness, and create loop/trim/fade/ducking instructions. It must keep
BPM null when no validated beat engine exists and must not render final export
media.

`bgm fit` and `bgm select` may accept explicit controls for `--fit-mode`,
`--fade-in-seconds`, `--fade-out-seconds`, `--target-gain-db`,
`--ducking-gain-db`, `--no-ducking`, and `--beat-align`. These controls are
recorded in `BgmFitControls` inside `.artist-portrait/data/bgm_fit.json`; they
do not move timeline edit points or fabricate beat grids.

`bgm rhythm` requires existing `.artist-portrait/data/bgm_analysis.json` and
writes `.artist-portrait/data/bgm_rhythm_intelligence.json`,
`output/bgm_rhythm_intelligence.md`, and `output/bgm_rhythm_handoff.json`. It
turns validated beat evidence into editing-facing beat quality, bar/phrase
hints, source-risk guidance, no-engine next actions, and mixed-video-audio
warnings. It does not select music, move edit points, fit music, render media,
call models, access the network, or fabricate BPM/beat grids.

`bgm review` writes `.artist-portrait/data/bgm_fit_review.json` and
`output/bgm_fit_review.md` when a recommendation-driven fit exists. It checks
selection, recommendation context, fit, timeline, analysis/beat evidence, and
preview/final-export readiness. It reports missing or stale rendered media but
does not render, select music, call models, access the network, or move edit
points.

## Preview Workflow

V0-014 can render low-resolution local review media after timeline generation.
It reads `output/timeline_draft.json` and, when present, the current
`.artist-portrait/data/bgm_fit.json`. It writes:

```text
output/preview_lowres.mp4
.artist-portrait/data/preview_manifest.json
.artist-portrait/data/preview_validation.json
output/preview_review.md
```

Use:

```bash
artist-portrait preview --project ./project.yaml --width 480 --fps 12
artist-portrait review --project ./project.yaml --scope preview
```

Preview rendering may use local FFmpeg/ffprobe to extract timeline video
ranges, retain original source audio, apply fitted BGM gain/fades/looping, and
duck BGM under retained original audio. It must not choose music, fabricate beat
alignment, render final delivery media, call models, access the network, or use
image generation/editing. Preview review validates expected duration against
actual ffprobe duration, video/audio stream presence, dimensions, frame rate,
profile drift, output hash, and upstream fingerprints.

## Acceptance Workflow

Use acceptance after the current project has at least reached timeline review,
or after preview/final export when checking delivery readiness:

```bash
artist-portrait acceptance --project ./project.yaml
artist-portrait acceptance --project ./project.yaml --profile core
artist-portrait acceptance --project ./project.yaml --profile preview
artist-portrait acceptance --project ./project.yaml --profile delivery
artist-portrait acceptance --project ./project.yaml --profile delivery --repair-plan
artist-portrait acceptance --project ./project.yaml --profile delivery --approval-request
artist-portrait acceptance --project ./project.yaml --profile delivery --approval-record ./approval_record.json
artist-portrait acceptance --project ./project.yaml --profile delivery --execution-dry-run
artist-portrait acceptance --project ./project.yaml --profile delivery --execution-bundle
artist-portrait acceptance --project ./project.yaml --profile delivery --execution-record ./execution_record.json
```

It writes `.artist-portrait/data/acceptance_report.json` and
`output/acceptance_report.md`. It audits existing artifacts and state for core
readiness, BGM readiness, rhythm-plan readiness, preview readiness,
final-export readiness, rhythm media QC readiness, and forbidden capability
flags. The default `standard` profile preserves the overall readiness report;
explicit `core`, `preview`, and `delivery` profiles turn the relevant readiness
level into the hard gate and exit code. `preview` requires existing rhythm plan,
preview, and rhythm media QC evidence. `delivery` requires existing rhythm
plan, preview, final export, and rhythm media QC evidence. It does not generate
proposals, choose music, fit music, run rhythm, run rhythm QC, render media,
call models, access the network, or repair missing artifacts.

`run_checks.py` includes a generated real-media acceptance fixture when local
FFmpeg/ffprobe are available. The fixture creates temporary video and BGM audio,
runs the local pipeline through proposal import, timeline, BGM fit/review,
rhythm planning, preview, rhythm QC, final export, refreshed rhythm QC, and
`core`/`preview`/`delivery` acceptance profiles, then
deletes the temporary workspace. It uses no downloaded media, network access,
CLI-side model calls, automatic music selection, or paid APIs.

With `--repair-plan`, acceptance also writes
`.artist-portrait/data/acceptance_repair_plan.json` and
`output/acceptance_repair_plan.md`. The plan orders next-action commands from
the current report and separates profile-required actions from optional
delivery gaps. It is guidance only: it does not execute commands, repair
artifacts, call models, choose music, fit music, render media, or access the
network.

With `--approval-request`, acceptance writes
`.artist-portrait/data/acceptance_repair_approval_request.json` and
`output/acceptance_repair_approval_request.md` from the current repair plan.
With `--approval-record <json>`, it validates and imports an explicit approval
record into `.artist-portrait/data/acceptance_repair_approval_record.json` and
`output/acceptance_repair_approval_record.md`. Approval records are audit
artifacts only; approved actions are not executed.

With `--execution-dry-run`, acceptance reads the current canonical approval
record and writes `.artist-portrait/data/acceptance_repair_execution_dry_run.json`
and `output/acceptance_repair_execution_dry_run.md`. It enumerates approved and
rejected commands but keeps every step non-executing (`would_execute=false`,
`commands_executed=false`).

With `--execution-bundle`, acceptance reads the current canonical dry-run and
writes `.artist-portrait/data/acceptance_repair_execution_bundle.json` and
`output/acceptance_repair_execution_bundle.md`. The bundle is a manual handoff:
commands are listed with `manual_execution_required=true` and
`executable_by_cli=false`.

With `--execution-record <json>`, acceptance imports explicit external
execution evidence into
`.artist-portrait/data/acceptance_repair_execution_record.json` and
`output/acceptance_repair_execution_record.md`. It validates project, profile,
repair plan, approval record, dry-run, step, action, and command bindings, then
classifies evidence as succeeded, failed, or skipped. It does not execute
commands and does not treat evidence as acceptance success.

## Rhythm Planning Workflow

Use rhythm planning after timeline generation, and preferably after explicit
BGM fitting when music is part of the edit:

```bash
artist-portrait rhythm --project ./project.yaml
artist-portrait rhythm --project ./project.yaml --intent ./rhythm_intent.json
artist-portrait rhythm --project ./project.yaml --intent ./rhythm_intent.json --agent-output ./rhythm_candidate.json
artist-portrait rhythm --project ./project.yaml --qc
artist-portrait rhythm --project ./project.yaml --repair-plan --acceptance-profile delivery
```

It writes `.artist-portrait/data/rhythm_plan.json`,
`output/rhythm_report.md`, and `output/rhythm_agent_handoff.json`. The report
audits timeline rhythm, BGM rhythm, compatibility, explicit intent, cut/cue
alignment, transitions, text/subtitle readiness, ducking/silence, ending shape,
and optional external rhythm recommendations. It does not move edit points,
select music, fit music automatically, render media, call models from the CLI,
access the network, or fabricate BPM/beat grids.

With `--qc`, rhythm planning reads the current rhythm plan plus existing
preview/final-export manifests and validation reports, then writes
`.artist-portrait/data/rhythm_media_qc.json`,
`output/rhythm_media_qc.md`, and `output/rhythm_media_qc_handoff.json`. It
checks preview/final binding, timeline and BGM freshness, duration drift, audio
expectations, ducking render state, ending render state, and media-QC summary.
It does not render preview/final media or mutate timeline/music artifacts.

With `--repair-plan`, rhythm reads existing rhythm, rhythm-QC, acceptance,
preview, final-export, and BGM evidence, then writes
`.artist-portrait/data/rhythm_repair_plan.json`,
`output/rhythm_repair_plan.md`, and `output/rhythm_repair_handoff.json`. It
orders manual next commands by acceptance profile. It does not execute commands,
render media, move edit points, select music, fit music, call models from the
CLI, or access the network.

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
- Treat `proposal_agent_handoff_pending` as a signal to run `propose`.
- Treat `proposal_agent_candidate_pending` as a signal for the current
  Codex/ChatGPT host Agent to generate one ProposalSet candidate from
  `output/proposal_agent_handoff.json`, then import it with `--agent-output`.
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
- Treat `proposal_execution_input_bundle_invalid` as a stop condition until
  `.artist-portrait/data/proposal_execution_input_bundle.json` is fixed or
  regenerated.
- Treat `proposal_provider_call_dry_run_invalid` as a stop condition until
  `.artist-portrait/data/proposal_provider_call_dry_run.json` is fixed or
  regenerated.
- Treat `proposal_provider_response_intake_plan_invalid` as a stop condition until
  `.artist-portrait/data/proposal_provider_response_intake_plan.json` is fixed or
  regenerated.
- Treat `proposal_provider_response_validation_plan_invalid` as a stop condition
  until `.artist-portrait/data/proposal_provider_response_validation_plan.json`
  is fixed or regenerated.
- Treat `proposal_promotion_authorization_plan_invalid` as a stop condition
  until `.artist-portrait/data/proposal_promotion_authorization_plan.json` is
  fixed or regenerated.
- Treat `proposal_promotion_validation_report_invalid` as a stop condition
  until `.artist-portrait/data/proposal_promotion_validation_report.json` is
  fixed or regenerated.
- Treat `proposal_canonical_write_transaction_plan_invalid` as a stop condition
  until `.artist-portrait/data/proposal_canonical_write_transaction_plan.json`
  is fixed or regenerated.
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
- automatic BGM recommendation or candidate selection
- fabricated BPM or beat-grid analysis
- fake, template, or model-free creative proposals
- paid or remote-provider creative proposal generation
- model calls
- network search
- image generation or image editing

Keep all current foundation outputs local and deterministic.
