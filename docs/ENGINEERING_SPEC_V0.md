# Engineering Spec V0

This is the canonical human-readable implementation specification. It owns
command behavior, state/invalidation rules, acceptance requirements, and data
contract policy in addition to core engineering constraints.

Machine-readable field semantics are owned by Pydantic models under
`src/artist_portrait_editor/models/` and generated JSON Schemas under
`schemas/`. `generate-schema` plus schema-drift checks prevent those two
sources from diverging; do not maintain a third field-by-field Markdown mirror.

## Data Contract Policy

- Canonical ledgers and packets validate against typed Pydantic models.
- Committed JSON Schemas are generated artifacts and must match those models.
- JSON/JSONL artifacts reject unknown fields unless a model explicitly permits them.
- Canonical identity and provenance remain in data artifacts; reports and cache
  are rebuildable.
- Artifact readers must produce stable invalid-JSON diagnostics.
- Proposal, timeline, and BGM artifacts bind current upstream fingerprints.
- Absolute local paths, secrets, fabricated evidence, and unsupported model
  assertions are forbidden in portable artifacts.

## Command Contract

Implemented local commands:

```text
validate
init
status
doctor
generate-schema
scan
segment
transcribe
keyframes
analyze
map
propose
timeline
bgm import
bgm list
bgm fit
bgm review
preview
review --scope project|proposal|timeline|preview|all
```

Commands use fixed exit codes, project-relative paths, deterministic canonical
artifacts, atomic writes, and explicit prerequisites. `timeline` requires an
explicit proposal ID. `bgm fit` requires an explicit candidate ID. `preview`
renders only low-resolution local review media from the canonical timeline and
optional current BGM fit; `--width` and `--fps` are bounded review controls, not
final export settings. No command may silently select a proposal, music
candidate, remote provider, or secret.

## State And Invalidation

`.artist-portrait/state.json` is the canonical step ledger. Canonical data lives
under `.artist-portrait/data/`; rebuildable cache lives under
`.artist-portrait/cache/`; command audit records live under
`.artist-portrait/runs/`; human-readable outputs live under `output/`.

Invalidation flows downstream:

```text
sources -> clips/transcripts/keyframes/analysis/map/proposals/timeline/BGM fit
clips -> keyframes/analysis/map/proposals/timeline/BGM fit
analysis -> map/proposals/timeline/BGM fit
material map -> proposals/timeline/BGM fit
proposals -> timeline/BGM fit
timeline -> BGM fit
BGM candidates -> BGM fit
BGM fit -> preview
timeline -> preview
```

`status` reports artifacts and step states. `doctor` is read-only and reports
invalid JSON, missing output references, stale steps, missing dependencies, and
exact recovery commands. Derived keyframes and BGM WAV files are cache, not
canonical identity.

## Acceptance Contract

Every open capability must have deterministic contract and integration tests.
The full check entrypoint is:

```bash
.venv/bin/python run_checks.py
```

It must cover configuration, schemas, Skill/package metadata, source identity,
media probing, segmentation, gated local transcription, keyframes, analysis,
material map, Host-Agent proposal quarantine/promotion, proposal validation,
explicit timeline generation, multi-source BGM ingestion/fitting,
low-resolution preview rendering, state, invalidation, diagnostics, audit
records, and documentation governance.

Required negative coverage includes malformed artifacts, unknown references,
forbidden/restricted sources, unsafe paths, missing dependencies, invalid audio
streams/ranges, stale fingerprints, policy-disabled music, fake proposal
methods, hidden model/network activity, and failed writes that must not replace
valid canonical outputs.

Preview testing must use real local FFmpeg media generation/probing. Browser
automation is not required for low-resolution file output unless a future UI
preview surface opens.

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

Current V0-011 implementation scope additionally allows:

- local `output/proposal_agent_handoff.json`
- explicit `--agent-output` candidate import
- candidate quarantine before parsing
- ProposalSet schema and semantic validation
- atomic canonical `proposals.json` promotion
- no paid API, API key, or network dependency

Current V0-012 implementation scope additionally allows:

- explicit `timeline --proposal` selection
- canonical `TimelineDraft` and `TimelineValidationReport`
- deterministic target-duration assembly from required clips
- atomic timeline, validation, and review outputs
- timeline state, diagnostics, run audit, and upstream invalidation
- unresolved or policy-disabled music slots without BGM processing

V0-013 BGM engineering models input mode independently from media kind.
Video-derived music requires deterministic ffmpeg/ffprobe stream selection,
project-relative provenance, extraction range, content hash, and rebuildable
audio cache. Extraction alone must not assert source separation or clean BGM.

Current V0-014 implementation scope additionally allows:

- `preview`
- local FFmpeg/ffprobe low-resolution MP4 rendering
- canonical `.artist-portrait/data/preview_manifest.json`
- canonical `.artist-portrait/data/preview_validation.json`
- deterministic `output/preview_review.md`
- rebuildable `.artist-portrait/cache/preview/`
- timeline video segment extraction and concatenation
- retained original source audio where timeline segments carry audio
- optional BGM fit rendering from the explicit current BGM fit plan
- BGM target gain, fade, loop/trim, and ducking application
- no-BGM preview with original audio or explicit silence
- preview status, doctor diagnostics, run audit, and upstream invalidation

V0-014 does not allow final-quality export, automatic BGM recommendation,
fabricated beat alignment, model calls, image generation/editing, or network
access.

Current V0-015 implementation scope additionally allows:

- bounded `preview --width` and `preview --fps`
- preview manifest expected/actual duration metrics
- preview video/audio stream presence validation
- preview dimension and frame-rate quality checks
- render profile and parameter drift detection
- preview review quality summary and recovery command
- status and doctor preview QC surfacing

V0-015 does not allow final-quality export, automatic BGM recommendation,
fabricated beat alignment, model calls, image generation/editing, or network
access.

Current V0-016 implementation scope additionally allows:

- `export --profile review_720p|delivery_1080p`
- local FFmpeg/ffprobe final MP4 rendering
- canonical `.artist-portrait/data/final_export_manifest.json`
- canonical `.artist-portrait/data/final_export_validation.json`
- deterministic `output/final_export_review.md`
- rebuildable `.artist-portrait/cache/final_export/`
- final export from canonical timeline source ranges
- retained original source audio and optional current BGM fit rendering
- BGM target gain, fade, loop/trim, and ducking application in final export
- no-BGM export with original audio or explicit silence
- final export duration, stream, width, frame-rate, profile, stale-input, and hash QC
- final export status, doctor diagnostics, run audit, and upstream invalidation

V0-016 does not allow automatic BGM recommendation, fabricated beat alignment,
model calls, image generation/editing, network access, paid APIs, API keys,
remote providers, or hidden Python-side model calls.

Current V0-017 implementation scope additionally allows:

- `bgm analyze`
- canonical `.artist-portrait/data/bgm_analysis.json`
- deterministic `output/bgm_analysis_report.md`
- local PCM energy-window analysis from cached BGM candidate audio
- RMS/peak window metrics and quiet/low/medium/high energy labels
- quiet head/tail and high-energy range detection
- loop-safe technical hints for human review
- mature local beat-engine package detection without beat-grid execution
- BGM fit binding to analysis reference and fingerprint
- BGM analysis status, doctor diagnostics, schema, run audit, and invalidation

V0-017 does not allow automatic BGM recommendation or selection, fabricated BPM
or beat-grid claims, source separation, model calls, image generation/editing,
network access, paid APIs, API keys, remote providers, or hidden Python-side
model calls.

Current V0-018 implementation scope additionally allows:

- `bgm recommend`
- canonical `.artist-portrait/data/bgm_recommendation_context.json`
- canonical `.artist-portrait/data/bgm_recommendation_request.json`
- deterministic `output/bgm_recommendation_agent_handoff.json`
- explicit host-Agent/local-model/third-party recommendation candidate import
- byte-exact `.artist-portrait/quarantine/bgm_recommendations/`
- canonical `.artist-portrait/data/bgm_recommendations.json`
- canonical `.artist-portrait/data/bgm_recommendation_validation.json`
- deterministic `output/bgm_recommendation_review.md`
- recommendation status, doctor diagnostics, schema, run audit, and invalidation

V0-018 does not allow automatic music selection, automatic fitting, invented
candidate IDs, fabricated BPM or beat-grid claims, source separation, CLI-side
model calls, image generation/editing, network access, paid APIs, API keys,
remote providers, or hidden Python-side model calls.

Current V0-020 implementation scope additionally allows:

- validated local beat-engine adapter capability discovery
- canonical `.artist-portrait/data/bgm_beat_grids/<music_candidate_id>.json`
- `BgmBeatGrid` schema with BPM, beat events, confidence, cache fingerprint,
  and no model/network/fabrication flags
- BGM analysis binding from successful adapter output into candidate ledgers
  and analysis reports
- BGM fit binding to beat-grid reference and fingerprint without automatic
  edit-point movement
- status/report surfacing for beat-engine capability, completed beat counts,
  and unavailable reasons
- stale beat-grid review diagnostics

V0-020 does not allow package installation, model download, network access,
paid APIs, API keys, remote providers, hidden model calls, image
generation/editing, source separation, automatic music selection, automatic
beat-synced editing, or fabricated BPM/beat grids from PCM energy windows.

Current V0-021 implementation scope additionally allows:

- `bgm select --recommendation-id <id>`
- `bgm select --rank <n>`
- canonical `.artist-portrait/data/bgm_recommendation_selection.json`
- deterministic `output/bgm_recommendation_selection_review.md`
- current recommendation/context freshness validation before selection
- explicit user selection binding from recommendation to BGM candidate
- deterministic `bgm_fit.json` generation for the selected recommendation
- downstream preview/final-export invalidation after selection changes
- selection status, doctor diagnostics, schema, run audit, and review surfacing

V0-021 does not allow automatic top-ranked selection, automatic fitting without
an explicit recommendation target, invented candidates, model calls, network
access, paid APIs, API keys, remote providers, hidden model calls, image
generation/editing, source separation, automatic beat-synced editing, or
automatic edit-point movement.

Current V0-022 implementation scope additionally allows:

- canonical `.artist-portrait/data/bgm_fit_review.json`
- deterministic `output/bgm_fit_review.md`
- `BgmRecommendationFitReview` schema
- `bgm review` recommendation-fit audit after explicit recommendation
  selection
- selection/recommendation/context freshness checks
- selected candidate versus current BGM fit validation
- BGM fit versus current timeline validation
- BGM analysis and beat-grid evidence fingerprint checks
- preview and final-export readiness/staleness checks against the current BGM
  fit fingerprint
- run audit, schema, and regression coverage for recommendation-fit review

V0-022 does not allow automatic music selection, automatic fitting without an
explicit target, automatic top-ranked selection, automatic beat-synced editing,
automatic edit-point movement, media rendering from review, model calls,
network access, paid APIs, API keys, remote providers, hidden model calls,
image generation/editing, source separation, or fabricated BPM/beat grids.

Current V0-023 implementation scope additionally allows:

- explicit `bgm fit` controls: `--fit-mode`, `--fade-in-seconds`,
  `--fade-out-seconds`, `--target-gain-db`, `--ducking-gain-db`,
  `--no-ducking`, and `--beat-align`
- the same explicit controls on `bgm select` after recommendation selection
- `BgmFitControls` embedded in canonical `.artist-portrait/data/bgm_fit.json`
- fit ID binding to current timeline, selected candidate, and fit controls
- deterministic validation of impossible fit-mode choices
- explicit ducking disablement and ducking gain control
- explicit fade and target gain control
- beat-alignment request recording without fabricated BPM or edit-point changes
- recommendation-fit review surfacing of fit control policy and request state
- downstream preview/final-export invalidation when controls change the fit plan

V0-023 does not allow automatic music selection, automatic top-ranked
selection, fitting without an explicit candidate or recommendation target,
automatic beat-synced editing, automatic edit-point movement, fabricated BPM or
beat grids, media rendering from controls, model calls, network access, paid
APIs, API keys, remote providers, hidden model calls, image generation/editing,
or source separation.

Current V0-024 implementation scope additionally allows:

- `acceptance`
- canonical `.artist-portrait/data/acceptance_report.json`
- deterministic `output/acceptance_report.md`
- `ProjectAcceptanceReport` schema
- core readiness evaluation for init, source scan, segmentation, analysis,
  proposal validation, and timeline validation
- delivery readiness evaluation for BGM fit/review, preview validation, and
  final-export validation
- forbidden-capability audit of existing canonical artifacts
- acceptance run audit and state ledger entry
- deterministic failed/warning/passed status and next-action guidance

V0-024 does not allow automatic pipeline repair, proposal generation, music
selection, BGM fitting, timeline mutation, preview/final media rendering, model
calls, network access, paid APIs, API keys, remote providers, hidden model
calls, image generation/editing, source separation, or fabricated BPM/beat
grids.

Current V0-025 implementation scope additionally allows:

- `acceptance --profile standard|core|preview|delivery`
- profile-specific required-stage evaluation
- profile pass/fail fields in `ProjectAcceptanceReport`
- required-stage IDs in canonical JSON/Markdown acceptance reports
- profile-aware acceptance exit codes
- acceptance state/run audit recording of the selected profile

V0-025 does not allow automatic pipeline repair, proposal generation, music
selection, BGM fitting, timeline mutation, preview/final media rendering, model
calls, network access, paid APIs, API keys, remote providers, hidden model
calls, image generation/editing, source separation, fabricated BPM/beat grids,
or automatic conversion from failed profile to remediation actions.

Current V0-026 implementation scope additionally allows:

- deterministic real-media acceptance fixture generation in tests and
  `run_checks.py`
- locally generated temporary MP4 video and WAV BGM audio
- fixture execution through scan, segment, keyframes, analyze, map, proposal
  handoff, candidate quarantine/import, timeline, BGM import/fit/review,
  preview, final export, and acceptance profiles
- fixture assertions for core, preview, and delivery acceptance profile success
- fixture assertions that BGM readiness and forbidden-capability audit remain
  grounded in local artifacts

V0-026 does not allow downloaded media, network access, remote search,
CLI-side model calls, automatic music selection, automatic top-ranked
recommendation selection, fabricated BPM or beat grids, automatic edit timing
changes, paid APIs, API keys, remote providers, hidden model calls, image
generation/editing, source separation, or durable binary fixture media.

Current V0-027 implementation scope additionally allows:

- `acceptance --repair-plan`
- canonical `.artist-portrait/data/acceptance_repair_plan.json`
- deterministic `output/acceptance_repair_plan.md`
- `AcceptanceRepairPlan` schema
- required versus optional repair action classification by acceptance profile
- deterministic command ordering from existing acceptance next actions
- repair-plan state/run audit refs and no-execution flags

V0-027 does not allow automatic repair execution, automatic pipeline reruns,
proposal generation by CLI, music selection, automatic BGM fitting, timeline
mutation, preview/final media rendering, model calls, network access, paid
APIs, API keys, remote providers, hidden model calls, image generation/editing,
source separation, fabricated BPM/beat grids, or automatic conversion from a
repair plan into performed actions.

Current V0-028 implementation scope additionally allows:

- `acceptance --approval-request`
- `acceptance --approval-record <json>`
- canonical `.artist-portrait/data/acceptance_repair_approval_request.json`
- deterministic `output/acceptance_repair_approval_request.md`
- canonical `.artist-portrait/data/acceptance_repair_approval_record.json`
- deterministic `output/acceptance_repair_approval_record.md`
- `AcceptanceRepairApprovalRequest` and `AcceptanceRepairApprovalRecord`
  schemas
- deterministic validation of project, profile, repair-plan, action, command,
  duplicate, pending-decision, and missing-required-action bindings

V0-028 does not allow executing approved actions, automatic repair execution,
automatic pipeline reruns, proposal generation by CLI, music selection,
automatic BGM fitting, timeline mutation, preview/final media rendering, model
calls, network access, paid APIs, API keys, remote providers, hidden model
calls, image generation/editing, source separation, fabricated BPM/beat grids,
or automatic conversion from approval records into performed actions.

Current V0-029 implementation scope additionally allows:

- `acceptance --execution-dry-run`
- canonical `.artist-portrait/data/acceptance_repair_execution_dry_run.json`
- deterministic `output/acceptance_repair_execution_dry_run.md`
- `AcceptanceRepairExecutionDryRun` schema
- dry-run enumeration of approved and rejected repair actions from a valid
  approval record
- command ordering, blocked reason, `would_execute=false`, and
  `commands_executed=false` evidence

V0-029 does not allow executing dry-run commands, automatic repair execution,
automatic pipeline reruns, proposal generation by CLI, music selection,
automatic BGM fitting, timeline mutation, preview/final media rendering, model
calls, network access, paid APIs, API keys, remote providers, hidden model
calls, image generation/editing, source separation, fabricated BPM/beat grids,
or automatic conversion from dry-run manifests into performed actions.

Current V0-030 implementation scope additionally allows:

- `acceptance --execution-bundle`
- `acceptance --execution-record <json>`
- canonical `.artist-portrait/data/acceptance_repair_execution_bundle.json`
- deterministic `output/acceptance_repair_execution_bundle.md`
- canonical `.artist-portrait/data/acceptance_repair_execution_record.json`
- deterministic `output/acceptance_repair_execution_record.md`
- `AcceptanceRepairExecutionBundle` and `AcceptanceRepairExecutionRecord`
  schemas
- manual execution handoff commands derived only from approved dry-run steps
- explicit external execution evidence intake with project, profile,
  repair-plan, approval-record, dry-run, step, action, and command binding
  validation
- succeeded, failed, and skipped evidence classification without changing
  acceptance readiness

V0-030 does not allow command execution by the CLI, automatic repair execution,
automatic pipeline reruns, trusting execution evidence as acceptance success,
proposal generation by CLI, music selection, automatic BGM fitting, timeline
mutation, preview/final media rendering, model calls, network access, paid
APIs, API keys, remote providers, hidden model calls, image generation/editing,
source separation, fabricated BPM/beat grids, or automatic conversion from
execution records into repaired project state.

Current V0-031 implementation scope additionally allows:

- `rhythm`
- `rhythm --intent <json>`
- `rhythm --agent-output <json>`
- canonical `.artist-portrait/data/rhythm_plan.json`
- deterministic `output/rhythm_report.md`
- deterministic `output/rhythm_agent_handoff.json`
- `RhythmPlan`, `RhythmIntent`, and `RhythmAgentCandidate` schemas
- deterministic timeline rhythm profile, BGM rhythm profile, compatibility
  audit, explicit intent audit, cut/cue audit, transition audit, text readiness
  audit, ducking/silence audit, ending audit, and external rhythm candidate
  validation

V0-031 does not allow moving edit points, automatic beat-synced editing,
automatic music selection, automatic BGM fitting, timeline mutation,
preview/final media rendering, fabricated BPM or beat grids, model calls,
network access, paid APIs, API keys, remote providers, hidden model calls,
image generation/editing, or source separation.

Current V0-032 implementation scope additionally allows:

- `rhythm --qc`
- canonical `.artist-portrait/data/rhythm_media_qc.json`
- deterministic `output/rhythm_media_qc.md`
- deterministic `output/rhythm_media_qc_handoff.json`
- `RhythmMediaQcReport` schema
- deterministic preview binding, final export binding, timeline freshness, BGM
  freshness, preview duration, final duration, audio expectation, ducking
  render, ending render, and media-QC summary checks over existing artifacts

V0-032 does not allow rendering preview/final media, moving edit points,
automatic beat-synced editing, automatic music selection, automatic BGM
fitting, timeline mutation, fabricated BPM or beat grids, model calls, network
access, paid APIs, API keys, remote providers, hidden model calls, image
generation/editing, source separation, or automatic repair of rhythm/QC issues.

Current V0-033 implementation scope additionally allows:

- acceptance `rhythm_plan` stage over existing
  `.artist-portrait/data/rhythm_plan.json`
- acceptance `rhythm_media_qc` stage over existing
  `.artist-portrait/data/rhythm_media_qc.json`
- preview profile required stages for existing rhythm plan, preview, and rhythm
  media QC evidence
- delivery profile required stages for existing rhythm plan, preview, final
  export, and rhythm media QC evidence
- standard and core profile non-blocking rhythm/QC warnings when rhythm evidence
  has not yet been produced
- repair plans, approval requests, dry-run manifests, manual execution bundles,
  and execution-record intake that carry rhythm-specific next commands without
  executing them
- generated real-media acceptance checks that explicitly run rhythm and rhythm
  QC before preview/delivery acceptance evaluation

V0-033 does not allow acceptance to auto-run rhythm, auto-run rhythm QC,
auto-render preview/final media, execute repair commands, auto-generate missing
pipeline artifacts, move edit points, automatically select music,
automatically fit music, fabricate BPM or beat grids, call models, access the
network, depend on paid APIs/API keys/remote providers, use hidden model calls,
use image generation/editing, perform source separation, or treat external
execution records as acceptance success.

Current V0-034 implementation scope additionally allows:

- `rhythm --repair-plan`
- `rhythm --repair-plan --acceptance-profile standard|core|preview|delivery`
- canonical `.artist-portrait/data/rhythm_repair_plan.json`
- deterministic `output/rhythm_repair_plan.md`
- deterministic `output/rhythm_repair_handoff.json`
- `RhythmRepairPlan` and `RhythmRepairAction` schemas
- profile-aware manual next-command ordering for missing/stale rhythm plan,
  preview, final export, BGM, and rhythm-QC evidence
- generated real-media checks that prove rhythm repair plans list commands
  without executing them

V0-034 does not allow rhythm repair plans to execute commands, auto-run rhythm
or rhythm QC, render preview/final media, auto-generate missing artifacts, move
edit points, automatically select music, automatically fit music, fabricate BPM
or beat grids, call models, access the network, depend on paid APIs/API
keys/remote providers, use hidden model calls, use image generation/editing,
perform source separation, or treat repair guidance as acceptance success.

Current V0-035 implementation scope additionally allows:

- `workflow --target core|preview|delivery`
- canonical `.artist-portrait/data/workflow_plan.json`
- deterministic `output/workflow_plan.md`
- deterministic `output/workflow_agent_handoff.json`
- `WorkflowPlan` and `WorkflowStep` schemas
- deterministic next-command selection from existing project state and
  artifacts
- integration of acceptance and rhythm repair guidance as blocked/optional
  workflow steps
- preservation of existing rhythm acceptance and rhythm-aware acceptance
  boundaries while planning workflow next commands

V0-035 does not allow workflow planning to execute commands, auto-run pipeline
stages, render media, generate proposals, import candidates, move edit points,
automatically select music, automatically fit music, fabricate BPM or beat
grids, call models, access the network, depend on paid APIs/API keys/remote
providers, use hidden model calls, use image generation/editing, perform source
separation, or treat workflow guidance as acceptance success.

Current V0-036 implementation scope additionally allows:

- `workflow --execution-record <candidate.json>`
- byte-exact quarantine to
  `.artist-portrait/data/workflow_execution_record_quarantine.json`
- canonical `.artist-portrait/data/workflow_execution_review.json`
- deterministic `output/workflow_execution_review.md`
- deterministic `output/workflow_execution_handoff.json`
- `WorkflowExecutionRecord`, `WorkflowExecutionStepRecord`,
  `WorkflowExecutionReview`, and `WorkflowExecutionStepReview` schemas
- validation of project, target, workflow-plan, step, command, and artifact
  evidence bindings
- accepted, rejected, missing, and skipped step evidence classification
- generated real-media workflow execution evidence review checks

V0-036 does not allow workflow execution review to execute commands, auto-run
workflow or pipeline stages, render media, generate proposals, import proposal
or rhythm candidates, move edit points, automatically select music,
automatically fit music, fabricate BPM or beat grids, call models, access the
network, depend on paid APIs/API keys/remote providers, use hidden model calls,
use image generation/editing, perform source separation, or treat execution
evidence as acceptance success.

Current V0-037 implementation scope additionally allows:

- `workflow --repair-plan`
- canonical `.artist-portrait/data/workflow_repair_plan.json`
- deterministic `output/workflow_repair_plan.md`
- deterministic `output/workflow_repair_handoff.json`
- `WorkflowRepairPlan` and `WorkflowRepairAction` schemas
- conversion of rejected, missing, and skipped workflow execution evidence into
  required or optional manual repair actions
- workflow-order repair action ordering and first-required-command surfacing
- generated real-media workflow evidence repair planning checks

V0-037 does not allow workflow repair planning to execute commands, auto-run
workflow or pipeline stages, render media, generate proposals, import proposal
or rhythm candidates, move edit points, automatically select music,
automatically fit music, fabricate BPM or beat grids, call models, access the
network, depend on paid APIs/API keys/remote providers, use hidden model calls,
use image generation/editing, perform source separation, or treat repair
guidance as acceptance success.

Current V0-038 implementation scope additionally allows:

- `workflow --approval-request`
- `workflow --approval-record <candidate.json>`
- `workflow --repair-dry-run`
- canonical workflow repair approval request, approval record, and dry-run
  JSON/Markdown artifacts
- byte-exact approval record quarantine
- validation of repair-plan, workflow-plan, execution-review, target, and
  action-id bindings
- approved and rejected manual repair action enumeration without execution

V0-038 does not allow workflow repair approval or dry-run packaging to execute
commands, auto-run workflow or pipeline stages, render media, generate
proposals, import proposal or rhythm candidates, move edit points,
automatically select music, automatically fit music, fabricate BPM or beat
grids, call models, access the network, depend on paid APIs/API keys/remote
providers, use hidden model calls, use image generation/editing, perform source
separation, or treat approval/dry-run artifacts as acceptance success.

Current V0-039 implementation scope additionally allows:

- `workflow --repair-execution-record <candidate.json>`
- canonical `.artist-portrait/data/workflow_repair_execution_record_quarantine.json`
- canonical `.artist-portrait/data/workflow_repair_execution_review.json`
- deterministic `output/workflow_repair_execution_review.md`
- deterministic `output/workflow_repair_execution_handoff.json`
- byte-exact workflow repair execution record quarantine
- validation of repair-plan, approval-record, dry-run, target, action-id,
  command, and expected-artifact bindings
- classification of repair execution action evidence as accepted, rejected,
  missing, or skipped without execution

V0-039 does not allow workflow repair execution review to execute commands,
auto-run workflow or pipeline stages, render media, generate proposals, import
proposal or rhythm candidates, move edit points, automatically select music,
automatically fit music, fabricate BPM or beat grids, call models, access the
network, depend on paid APIs/API keys/remote providers, use hidden model calls,
use image generation/editing, perform source separation, or treat repair
execution evidence as acceptance success.

Current V0-040 implementation scope additionally allows:

- `release-check --project <project.yaml>`
- canonical `.artist-portrait/data/release_hardening_report.json`
- deterministic `output/release_hardening_report.md`
- current-gate documentation consistency audit
- local git publication-state audit without commit, push, or tag
- release-critical schema coverage audit
- forbidden paid/network provider source-surface audit
- workflow/rhythm artifact chain documentation audit
- current validation evidence audit
- readiness classification as `ready_for_local_release`, `warning`, or
  `blocked`

V0-040 does not allow release hardening to commit, push, tag, execute repair
commands, auto-run workflow or pipeline stages, render media, generate
proposals, import proposal or rhythm candidates, move edit points,
automatically select music, automatically fit music, fabricate BPM or beat
grids, call models, access the network, depend on paid APIs/API keys/remote
providers, use hidden model calls, use image generation/editing, perform source
separation, or treat release readiness as acceptance success.

Current V0-041 implementation scope additionally allows:

- `workflow --repair-refresh-plan`
- canonical `.artist-portrait/data/workflow_repair_refresh_plan.json`
- deterministic `output/workflow_repair_refresh_plan.md`
- deterministic `output/workflow_repair_refresh_handoff.json`
- mapping accepted workflow repair execution evidence to
  `ready_to_resubmit`
- preserving rejected, missing, and skipped repair execution evidence as
  explicit gaps
- next explicit workflow execution-record command guidance without execution

V0-041 does not allow workflow repair refresh planning to execute commands,
mutate workflow plans, auto-run workflow or pipeline stages, render media,
generate proposals, import proposal or rhythm candidates, move edit points,
automatically select music, automatically fit music, fabricate BPM or beat
grids, call models, access the network, depend on paid APIs/API keys/remote
providers, use hidden model calls, use image generation/editing, perform source
separation, or treat refreshed evidence as acceptance success.

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
- `ProposalExecutionInputBundle` Pydantic model and generated JSON Schema
- deterministic `.artist-portrait/data/proposal_execution_input_bundle.json`
- execution input bundle packet covering ten blocked input sub-items: provider
  identity, request packet, prompt contract, schema contract, approval chain,
  secret reference, credential access policy, network policy, quarantine
  target, and output routing without selected secrets, credential reads, model
  calls, network access, execution allowance, execution, raw output capture,
  prompt embedding, or proposal content
- `ProposalProviderCallDryRun` Pydantic model and generated JSON Schema
- deterministic `.artist-portrait/data/proposal_provider_call_dry_run.json`
- provider call dry-run manifest covering ten blocked call sub-items: endpoint
  reference, auth header policy, request body reference, timeout policy, retry
  policy, rate-limit policy, idempotency policy, network egress policy,
  response capture policy, and failure handling policy without endpoint
  resolution, auth header materialization, request body materialization,
  credential reads, model calls, network access, execution allowance,
  execution, request sending, raw output capture, or proposal content
- `ProposalExecutionAuthorization` Pydantic model and generated JSON Schema
- deterministic `.artist-portrait/data/proposal_execution_authorization.json`
- execution authorization packet without credentials, user approval, model
  calls, network access, execution, or proposal content
- `ProposalProviderResponseIntakePlan` Pydantic model and generated JSON Schema
- deterministic `.artist-portrait/data/proposal_provider_response_intake_plan.json`
- provider response intake plan covering ten blocked response sub-items:
  response channel, raw output location, content-type policy, size-limit
  policy, checksum policy, redaction policy, parser selection, validation
  queue, promotion gate, and audit trail without opening response channels,
  materializing raw output storage, validating content type, computing
  checksums, redacting, selecting parsers, enqueuing validation, allowing
  promotion, writing audit events, capturing raw output, parsing payloads,
  validating output, promoting proposals, model calls, network access, or
  proposal content
- `ProposalProviderOutputQuarantine` Pydantic model and generated JSON Schema
- deterministic `.artist-portrait/data/proposal_provider_output_quarantine.json`
- provider output quarantine packet without raw output capture, payload
  parsing, proposal promotion, validation, model calls, network access, or
  proposal content
- `ProposalProviderResponseValidationPlan` Pydantic model and generated JSON
  Schema
- deterministic
  `.artist-portrait/data/proposal_provider_response_validation_plan.json`
- provider response validation plan covering ten blocked validation sub-items:
  quarantine input binding, content-type check, size-limit check, checksum
  verification, redaction verification, parser contract, JSON syntax
  validation, schema validation, semantic validation, and promotion decision
  without raw output reads, parsing, validation execution, promotion, model
  calls, network access, or proposal content
- `ProposalPromotionAuthorizationPlan` Pydantic model and generated JSON Schema
- deterministic `.artist-portrait/data/proposal_promotion_authorization_plan.json`
- ten blocked promotion conditions without validation success assertions, risk
  acceptance, overwrite permission, canonical write preparation, promotion
  authorization, promotion execution, model calls, network access, or proposal
  content
- `ProposalPromotionValidationReport` Pydantic model and generated JSON Schema
- deterministic `.artist-portrait/data/proposal_promotion_validation_report.json`
- ten blocked, unperformed report domains with zero pass counters and no
  promotion recommendation, authorization, execution, canonical write, model
  call, network access, or proposal content
- `ProposalCanonicalWriteTransactionPlan` Pydantic model and generated JSON
  Schema
- deterministic
  `.artist-portrait/data/proposal_canonical_write_transaction_plan.json`
- ten blocked transaction stages without locks, snapshots, temporary files,
  fsync, replacement, rollback, commit, canonical proposal writes, model calls,
  network access, or proposal content
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
