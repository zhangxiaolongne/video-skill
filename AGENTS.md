# AGENTS.md

Follow `artist_portrait_editor_revision5_optimized.md` as the governing V0
engineering-freeze document.

Current gate: V0-042 BGM rhythm intelligence gate.

V0-011 uses the active Codex/ChatGPT host Agent as the creative model. Do not
add paid APIs, API keys, remote provider dependencies, or hidden network calls.
The CLI may export an Agent handoff bundle and import an explicit candidate
file, but it must quarantine and validate the candidate before atomically
writing canonical proposals.

V0-012 requires explicit user selection of one canonical proposal before
deterministically generating and validating `output/timeline_draft.json`.
Timeline work may preserve an unresolved or policy-disabled music slot, but it
must not select tracks, analyze beats, extract/separate BGM, fit music, render
preview media, call paid APIs, or access the network.

V0-013 may import project-local audio, extract a selected audio stream/range
from project-local video, or reuse canonical source embedded audio. It may use
local FFmpeg/ffprobe for normalization and loudness analysis, retain multiple
candidates, and fit an explicitly selected candidate to the canonical timeline.
Within V0-013 it did not auto-recommend music, claim a video mix is clean BGM,
fabricate BPM when no mature beat engine exists, render preview media, or
access the network.

V0-014 may render local low-resolution preview media from the canonical
timeline and optional current BGM fit plan. It may use local FFmpeg/ffprobe to
extract timeline video ranges, assemble retained original audio, render fitted
BGM gain/fades/looping/ducking, mux `output/preview_lowres.mp4`, and write
preview manifest, validation, review, status, doctor, audit, and invalidation
artifacts. It must not render final-quality export, automatically select music,
fabricate beat alignment, call models, access the network, use image
generation/editing, or depend on paid APIs/API keys/remote providers.

V0-015 may add bounded preview render controls and deterministic preview QC for
duration, stream presence, dimensions, profile drift, status/doctor surfacing,
and review recovery guidance. It must not render final-quality export,
automatically select music, fabricate beat alignment, call models, access the
network, use image generation/editing, or depend on paid APIs/API keys/remote
providers.

V0-016 may render controlled local final MP4 exports from the canonical
timeline and optional current BGM fit plan. It may use local FFmpeg/ffprobe,
explicit user-selected profiles, retained original audio, fitted BGM
gain/fades/looping/ducking, final export manifests, validation, review,
status/doctor surfacing, run audit, and upstream invalidation. It must not
automatically select or recommend music, fabricate beat alignment, call models,
access the network, use image generation/editing, depend on paid APIs/API
keys/remote providers, or perform hidden Python-side model calls.

V0-017 may analyze project-local BGM candidates using local cache audio,
deterministic PCM energy windows, mature local beat-engine capability
detection, and canonical BGM analysis reports. It may bind BGM fit plans to
analysis evidence and surface analysis in status/doctor. It must not
automatically recommend or select music, fabricate BPM or beat grids when no
validated engine runs, call models, access the network, use image
generation/editing, depend on paid APIs/API keys/remote providers, or perform
hidden Python-side model calls.

V0-018 may prepare BGM recommendation handoff artifacts for the host Agent,
local models, or third-party tools, and may import an explicit recommendation
JSON candidate after byte-exact quarantine and validation. It may promote only
valid recommendation review artifacts. It must not automatically select or fit
music, invent candidate IDs, call models from the CLI, access the network, use
image generation/editing, depend on paid APIs/API keys/remote providers, or
perform hidden Python-side model calls.

V0-020 may detect mature local beat-engine packages, execute only validated
local beat-engine adapters, write canonical BGM beat-grid evidence, bind BPM and
beat-grid fingerprints into BGM analysis and fit plans, and surface beat
capability in status/doctor/review. If no validated local engine is installed,
BPM and beat grid must remain null/unavailable. It must not fabricate BPM or
beats from PCM energy windows, install packages, download models, call models,
access the network, use image generation/editing, automatically select music,
perform automatic beat-synced editing, or automatically move edit points to
beats.

V0-021 may turn an already imported and validated BGM recommendation into a BGM
fit plan only after explicit user selection by recommendation ID or rank. It
may write canonical selection review artifacts, validate current recommendation
and context freshness, trigger deterministic BGM fitting for the selected
candidate, and invalidate downstream preview/final-export artifacts. It must
not automatically select the top-ranked recommendation, fit music without an
explicit user target, call models, access the network, use image
generation/editing, or change edit timing automatically.

V0-022 may review an explicit BGM recommendation selection against the current
BGM fit plan, timeline, recommendation context, analysis/beat evidence,
preview, and final-export readiness. It may write canonical recommendation-fit
review artifacts and surface stale/missing downstream media state. It must not
automatically select music, automatically fit music without an explicit target,
move edit points to beats, render media, call models, access the network, use
image generation/editing, or depend on paid APIs/API keys/remote providers.

V0-023 may apply explicit user BGM fit controls for fit mode, fades, target
gain, ducking gain/disablement, and beat-alignment request state when building
the current BGM fit plan from either `bgm fit` or `bgm select`. It may record
controls in canonical fit/review artifacts and invalidate downstream media. It
must not automatically select music, automatically choose top-ranked
recommendations, move timeline edit points, fabricate BPM/beat grids, render
media from fit controls, call models, access the network, use image
generation/editing, or depend on paid APIs/API keys/remote providers.

V0-024 may generate a deterministic project acceptance report from existing
workspace artifacts and state. It may evaluate core readiness, delivery
readiness, BGM readiness, preview readiness, final-export readiness, and
forbidden-capability flags, then write canonical acceptance JSON/Markdown and
run audit artifacts. It must not generate proposals, select music, change the
timeline, fit music, render media, call models, access the network, use image
generation/editing, or depend on paid APIs/API keys/remote providers.

V0-025 may add explicit acceptance profiles for `standard`, `core`, `preview`,
and `delivery`. It may make `acceptance --profile core|preview|delivery`
deterministically evaluate profile-specific required stages, write profile
status into canonical JSON/Markdown reports, update state/run audit, and return
profile-appropriate exit codes. It must not auto-run missing pipeline stages,
generate proposals, select music, fit music, change timelines, render media,
call models, access the network, use image generation/editing, or depend on
paid APIs/API keys/remote providers.

V0-026 may add deterministic real-media acceptance fixtures and checks using
locally generated temporary audio/video. It may run ffmpeg/ffprobe-backed
scan, segment, keyframes, analyze, map, host-Agent candidate quarantine/import,
timeline, BGM import/fit/review, preview, final export, and core/preview/
delivery acceptance profiles inside tests or `run_checks.py`. It must not
download media, access the network, call models from the CLI, automatically
select music, fabricate beat grids, change edit timing automatically, or
depend on paid APIs/API keys/remote providers.

V0-027 may generate deterministic acceptance repair plans from the current
acceptance report. It may write canonical JSON/Markdown repair-plan artifacts,
classify required versus optional actions by acceptance profile, order
next-action commands, and record the plan in state/run audit. It must not
execute repair commands, auto-run pipeline steps, generate proposals, select or
fit music automatically, render media, call models, access the network, use
image generation/editing, or depend on paid APIs/API keys/remote providers.

V0-028 may generate deterministic acceptance repair approval requests and
validate/import explicit approval records against the current repair plan. It
may write canonical JSON/Markdown approval request and approval record
artifacts, verify project/profile/plan/action bindings, and record approval
artifacts in state/run audit. It must not execute approved actions, auto-run
pipeline steps, generate proposals, select or fit music automatically, render
media, call models, access the network, use image generation/editing, or depend
on paid APIs/API keys/remote providers.

V0-029 may generate deterministic repair execution dry-run manifests from the
current repair plan and a valid approval record. It may enumerate approved and
rejected repair actions, commands, ordering, and blocking reasons, then write
canonical JSON/Markdown artifacts and state/run audit refs. It must not execute
commands, auto-run pipeline steps, generate proposals, select or fit music
automatically, render media, call models, access the network, use image
generation/editing, or depend on paid APIs/API keys/remote providers.

V0-030 may generate deterministic manual repair execution bundle artifacts from
the current repair execution dry-run and may import explicit external execution
record candidates. It may validate project/profile/plan/approval/dry-run/step/
command bindings, classify succeeded/failed/skipped external evidence, and
write canonical JSON/Markdown bundle and record artifacts with state/run audit
refs. It must not execute commands, auto-run pipeline steps, trust execution
evidence as acceptance success, generate proposals, select or fit music
automatically, render media, call models, access the network, use image
generation/editing, or depend on paid APIs/API keys/remote providers.

V0-031 may generate deterministic BGM/edit rhythm planning artifacts from the
current canonical timeline, optional current BGM fit, optional BGM analysis,
explicit rhythm intent JSON, and optional external rhythm candidate JSON. It
may write canonical rhythm plan JSON, human rhythm report Markdown, host-Agent
rhythm handoff JSON, and state/run audit refs covering timeline rhythm, BGM
rhythm, compatibility, intent, cut/cue, transition, text, ducking/silence,
ending, and candidate validation. It must not move edit points, select music,
fit music automatically, render media, fabricate BPM or beat grids, call models
from the CLI, access the network, use image generation/editing, or depend on
paid APIs/API keys/remote providers.

V0-032 may generate deterministic rhythm media QC artifacts from the current
rhythm plan and existing preview/final-export manifests and validation reports.
It may write canonical rhythm media QC JSON, Markdown, and handoff artifacts
covering preview binding, final export binding, timeline freshness, BGM
freshness, preview duration, final duration, audio expectation, ducking render,
ending render, and media-QC summary. It must not render preview/final media,
move edit points, select music, fit music automatically, call models from the
CLI, access the network, use image generation/editing, fabricate BPM/beat
grids, or depend on paid APIs/API keys/remote providers.

V0-033 may integrate existing rhythm plan and rhythm media QC artifacts into
acceptance profiles, repair plans, approval requests, dry-run manifests, manual
execution bundles, reports, and generated real-media acceptance checks. It may
make preview and delivery profiles require current rhythm evidence and may
surface rhythm-specific next commands. It must not auto-run rhythm, auto-run
rhythm QC, render media, execute repair commands, move edit points, select or
fit music automatically, call models from the CLI, access the network, use
image generation/editing, fabricate BPM/beat grids, or depend on paid APIs/API
keys/remote providers.

V0-034 may generate deterministic rhythm manual repair plans from existing
rhythm, rhythm-QC, acceptance, preview, final-export, and BGM evidence. It may
write canonical JSON, Markdown, and handoff artifacts with ordered manual next
commands by acceptance profile. It must not execute commands, auto-run rhythm
or rhythm QC, render media, move edit points, select or fit music
automatically, call models from the CLI, access the network, use image
generation/editing, fabricate BPM/beat grids, or depend on paid APIs/API
keys/remote providers.

V0-035 may generate deterministic guided workflow plans from existing project
state and artifacts for `core`, `preview`, and `delivery` targets. It may write
canonical workflow JSON, Markdown runbook, and handoff artifacts with ordered
explicit commands and current next command. It must not execute commands,
auto-run pipeline stages, render media, move edit points, select or fit music
automatically, call models from the CLI, access the network, use image
generation/editing, fabricate BPM/beat grids, or depend on paid APIs/API
keys/remote providers.

V0-036 may import and review explicit external workflow execution record
candidates after byte-exact quarantine. It may validate project, target,
workflow-plan, step, command, and artifact evidence bindings; classify step
evidence as accepted, rejected, missing, or skipped; and write canonical JSON,
Markdown, handoff, state, and run-audit artifacts. It must not execute
commands, auto-run workflow steps, render media, move edit points, select or
fit music automatically, call models from the CLI, access the network, use
image generation/editing, fabricate BPM/beat grids, depend on paid APIs/API
keys/remote providers, or treat execution evidence as acceptance success.

V0-037 may generate deterministic workflow evidence repair plans from the
current workflow plan and workflow execution review. It may classify rejected,
missing, and skipped workflow evidence into required or optional manual repair
actions, order actions by workflow step order, and write canonical JSON,
Markdown, handoff, state, and run-audit artifacts. It must not execute repair
commands, auto-run workflow or pipeline steps, render media, move edit points,
select or fit music automatically, call models from the CLI, access the
network, use image generation/editing, fabricate BPM/beat grids, depend on paid
APIs/API keys/remote providers, or treat repair guidance as acceptance success.

V0-038 may generate workflow repair approval requests, import explicit approval
record candidates after byte-exact quarantine, validate repair-plan/action
bindings, and generate workflow repair dry-run manifests for approved and
rejected manual actions. It must not execute repair commands, auto-run workflow
or pipeline steps, render media, move edit points, select or fit music
automatically, call models from the CLI, access the network, use image
generation/editing, fabricate BPM/beat grids, depend on paid APIs/API
keys/remote providers, or treat approval/dry-run artifacts as acceptance
success.

V0-039 may import explicit external workflow repair execution record candidates
after byte-exact quarantine and validate them against the current workflow
repair dry-run, approval record, repair plan, target, action ids, commands, and
expected artifact evidence. It may classify action evidence as accepted,
rejected, missing, or skipped, and write canonical JSON, Markdown, handoff,
state, and run-audit artifacts. It must not execute repair commands, auto-run
workflow or pipeline steps, render media, move edit points, select or fit music
automatically, call models from the CLI, access the network, use image
generation/editing, fabricate BPM/beat grids, depend on paid APIs/API
keys/remote providers, or treat repair execution evidence as acceptance
success.

V0-040 may generate deterministic release hardening reports for the accumulated
workflow/rhythm gates. It may audit current-gate documentation consistency,
local git publication state, schema coverage, forbidden provider surfaces,
workflow/rhythm artifact documentation, and validation evidence, then write
canonical JSON/Markdown artifacts. It must not commit, push, tag, render media,
execute repair commands, auto-run workflow or pipeline steps, move edit
points, select or fit music automatically, call models from the CLI, access the
network, use image generation/editing, fabricate BPM/beat grids, depend on paid
APIs/API keys/remote providers, or treat release hardening as acceptance
success.

V0-041 may generate deterministic workflow repair refresh plans from the
current workflow repair execution review. It may map accepted repair evidence
to ready-to-resubmit workflow execution evidence, preserve rejected/missing/
skipped repair evidence as explicit gaps, and write canonical JSON, Markdown,
handoff, state, and run-audit artifacts. It must not execute workflow commands,
mutate workflow plans, auto-run pipeline steps, render media, move edit points,
select or fit music automatically, call models from the CLI, access the
network, use image generation/editing, fabricate BPM/beat grids, depend on paid
APIs/API keys/remote providers, or treat refreshed evidence as acceptance
success.

V0-042 may generate deterministic BGM rhythm intelligence from the current BGM
candidate ledger and BGM analysis report. It may write canonical JSON,
Markdown, and handoff artifacts for beat-quality scoring, source-provenance
rhythm risk, no-engine guidance, mixed-video-audio contamination warnings,
bar/phrase timing hints derived only from validated BPM, and rhythm-plan/QC
freshness binding. It must not select music, move edit points, fit music
automatically, render media, fabricate BPM or beat grids, infer BPM from PCM
energy windows, call models from the CLI, access the network, use image
generation/editing, depend on paid APIs/API keys/remote providers, or treat
mixed extracted video audio as clean BGM.

Future BGM work must support direct audio uploads, audio extracted from uploaded
video, embedded source audio, multiple candidates, and no-file-yet planning.
Never treat an extracted video mix as clean BGM without explicit separation or
analysis evidence; preserve source/video/stream/range/hash provenance.

## Documentation Governance

Each project fact has one canonical human-readable owner:

- `artist_portrait_editor_revision5_optimized.md`: strategy, engineering freeze,
  capability boundaries, and long-term editing principles
- `docs/DEVELOPMENT_PROGRESS.md`: current stage dashboard and next major direction
- `docs/CURRENT_BATCH.md`: active batch, version tasks, statuses, acceptance
  evidence, and closeout
- `docs/ISSUES.md`: open, blocked, accepted, resolved, and superseded issues
- `docs/DECISIONS.md`: durable product, architecture, workflow, and release decisions
- `docs/RELEASES.md`: canonical release history, current validation, and Git state

`docs/current_progress.json` is the machine-readable mirror. Historical outcomes
are consolidated in `docs/RELEASES.md`; do not recreate per-version readiness,
gate-progress, acceptance, or closeout fragments. Do not create a second task
list, issue list, decision log, or release ledger elsewhere.

## Mandatory Development Batch Contract

Every implementation batch must advance a named product, capability, or
release milestone toward the final usable video-editing skill.

Before editing:

- plan the next big-version direction, not only the next local change
- define at least ten independent version tasks for the batch
- state the expected before/after change in final-goal completion

A version task counts when it independently adds at least one of:

- runnable end-to-end pipeline behavior
- user-visible workflow behavior
- a newly opened and tested capability gate
- closure of a concrete final-goal acceptance gap
- a release-level contract, quality, architecture, or hardening outcome

Fields, schemas, tests, refactors, and bug fixes are classified by scope, not
forbidden by work type. Incremental or supporting instances do not count:

- adding or changing isolated fields
- adding an isolated schema, model, packet, manifest, or blocked artifact
- adding individual tests, fixtures, documentation, or validation commands
- local refactors, file moves, registries, wrappers, naming, formatting, or cleanup
- incidental bug fixes discovered inside another task
- isolated status/doctor diagnostics or additional review rules

These work types may count as major-version tasks only when all conditions hold:

- the work belongs to a named major-version milestone
- it has independent, release-level acceptance criteria
- its scope is substantial, cross-cutting, or release-critical
- it changes capability readiness, release safety, or final-goal completion
- it is not fragmented into trivial field, schema, test, refactor, or bug items

Examples of countable major-version tasks include a versioned data-contract
migration, a comprehensive acceptance/evaluation program, an architectural
refactor that enables the next capability, and a major defect-closure or
release-hardening program. A single field, test, file move, or incidental bug
does not count. Necessary supporting work remains inside the task that requires
it.

If the current gate does not permit ten meaningful version tasks:

- do not pad the batch with fields, packets, tests, docs, refactors, or review rules
- stop implementation
- present the exact gate promotion required and the next real capability milestone
- wait for explicit gate approval before implementing forbidden behavior

V0-010 foundation and proposal review are closed for ordinary expansion. Do not
add more V0-010 packets, schemas, review rules, or diagnostics unless fixing a
critical regression/security issue or the user explicitly requests that exact
change. The next normal milestone must promote a real capability gate.

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
- canonical `.artist-portrait/data/proposal_provider_output_quarantine.json`
- `ProposalProviderOutputQuarantine` Pydantic model and generated JSON Schema
- deterministic provider output quarantine packet without raw output capture, parsing, validation, promotion, model calls, network access, or proposal content
- canonical `.artist-portrait/data/proposal_execution_approval_request.json`
- `ProposalExecutionApprovalRequest` Pydantic model and generated JSON Schema
- deterministic provider execution approval request packet without recorded approval, secret selection, credential reading, model calls, network access, execution, or proposal content
- canonical `.artist-portrait/data/proposal_execution_approval_record.json`
- `ProposalExecutionApprovalRecord` Pydantic model and generated JSON Schema
- deterministic provider execution approval record packet without granted approval, secret selection, credential reading, model calls, network access, execution, or proposal content
- canonical `.artist-portrait/data/proposal_execution_readiness_plan.json`
- `ProposalExecutionReadinessPlan` Pydantic model and generated JSON Schema
- deterministic provider execution readiness plan covering secret-source selection, credential access, execution planning, provider call preflight, and output capture planning without secret selection, credential reading, model calls, network access, execution, raw output capture, or proposal content
- canonical `.artist-portrait/data/proposal_execution_input_bundle.json`
- `ProposalExecutionInputBundle` Pydantic model and generated JSON Schema
- deterministic provider execution input bundle covering ten blocked input sub-items: provider identity, request packet, prompt contract, schema contract, approval chain, secret reference, credential access policy, network policy, quarantine target, and output routing without secret selection, credential reading, model calls, network access, execution, raw output capture, prompt embedding, or proposal content
- canonical `.artist-portrait/data/proposal_provider_call_dry_run.json`
- `ProposalProviderCallDryRun` Pydantic model and generated JSON Schema
- deterministic provider call dry-run manifest covering ten blocked call sub-items: endpoint reference, auth header policy, request body reference, timeout policy, retry policy, rate-limit policy, idempotency policy, network egress policy, response capture policy, and failure handling policy without endpoint resolution, auth header materialization, request body materialization, credential reading, model calls, network access, execution, request sending, raw output capture, or proposal content
- canonical `.artist-portrait/data/proposal_provider_response_intake_plan.json`
- `ProposalProviderResponseIntakePlan` Pydantic model and generated JSON Schema
- deterministic provider response intake plan covering ten blocked response sub-items: response channel, raw output location, content-type policy, size-limit policy, checksum policy, redaction policy, parser selection, validation queue, promotion gate, and audit trail without opening a response channel, materializing raw output storage, validating content type, computing checksums, redacting, selecting parsers, enqueuing validation, allowing promotion, writing audit events, capturing raw output, parsing payloads, validating output, promoting proposals, model calls, network access, or proposal content
- canonical `.artist-portrait/data/proposal_provider_response_validation_plan.json`
- `ProposalProviderResponseValidationPlan` Pydantic model and generated JSON Schema
- deterministic provider response validation plan covering ten blocked validation sub-items: quarantine input binding, content-type check, size-limit check, checksum verification, redaction verification, parser contract, JSON syntax validation, schema validation, semantic validation, and promotion decision without reading raw output, selecting parsers, parsing payloads, executing validation, making promotion decisions, writing audit events, promoting proposals, model calls, network access, or proposal content
- canonical `.artist-portrait/data/proposal_promotion_authorization_plan.json`
- `ProposalPromotionAuthorizationPlan` Pydantic model and generated JSON Schema
- deterministic proposal promotion authorization plan covering ten blocked conditions: validation report binding, schema validation requirement, semantic validation requirement, evidence validation requirement, risk acceptance requirement, proposal identity requirement, overwrite policy, atomic write policy, provenance binding, and final promotion authorization without binding validation reports, declaring validation success, accepting risk, authorizing or performing promotion, writing proposals, model calls, network access, or proposal content
- canonical `.artist-portrait/data/proposal_promotion_validation_report.json`
- `ProposalPromotionValidationReport` Pydantic model and generated JSON Schema
- deterministic promotion validation report covering ten blocked report domains without reading provider output, performing or passing checks, recommending or authorizing promotion, writing proposals, model calls, network access, or proposal content
- canonical `.artist-portrait/data/proposal_canonical_write_transaction_plan.json`
- `ProposalCanonicalWriteTransactionPlan` Pydantic model and generated JSON Schema
- deterministic canonical proposal write transaction plan covering ten blocked stages without acquiring locks, creating snapshots or temporary files, running schema prewrite checks, fsync, atomic replacement, conflict detection, rollback, audit commit, postcommit verification, writing proposals, model calls, network access, or proposal content
- `ProposalSet` Pydantic model and generated JSON Schema
- canonical `.artist-portrait/data/proposal_validation.json`
- deterministic `output/proposal_review.md`
- `ProposalValidationReport` Pydantic model and generated JSON Schema
- `review --scope proposal` for deterministic validation of existing proposals
- `output/proposal_agent_handoff.json` for the active Codex/ChatGPT host Agent
- explicit local `--agent-output` ProposalSet candidate import
- byte-exact host-Agent candidate quarantine before parsing
- ProposalSet schema, evidence, policy, differentiation, and BGM validation
- atomic canonical `proposals.json` promotion after validation
- proposal artifact status and doctor diagnostics
- text-model gate status and doctor diagnostics
- handoff-preparation `propose` behavior that writes proposal context and
  `proposal_agent_handoff.json` but no canonical proposals
- host-Agent candidate import that requires explicit provenance and quarantine
- failed candidate behavior that leaves canonical proposals untouched
- `timeline --proposal proposal_safe|proposal_advanced|proposal_risky`
- explicit user proposal selection without automatic ranking or selection
- canonical `output/timeline_draft.json`
- `TimelineDraft` Pydantic model and generated JSON Schema
- deterministic selected-proposal clip assembly within target duration
- source/timeline range, media-role, transition, evidence, and risk preservation
- unresolved or policy-disabled music slot without requiring a BGM file
- deterministic timeline validation and `review --scope timeline`
- timeline status, doctor diagnostics, run audit, and upstream invalidation
- `bgm import` for project-local audio/video or canonical source audio
- canonical `.artist-portrait/data/bgm_candidates.json`
- rebuildable `.artist-portrait/cache/bgm/`
- explicit video audio stream/range extraction with mixed-audio provenance
- deterministic FFmpeg/ffprobe duration and EBU R128 loudness analysis
- explicit user candidate selection without automatic recommendation
- canonical `.artist-portrait/data/bgm_fit.json`
- loop/trim/fade/ducking fit planning bound to the canonical timeline
- BGM status, doctor diagnostics, review, run audit, and invalidation
- `preview`
- canonical `output/preview_lowres.mp4`
- canonical `.artist-portrait/data/preview_manifest.json`
- canonical `.artist-portrait/data/preview_validation.json`
- deterministic `output/preview_review.md`
- rebuildable `.artist-portrait/cache/preview/`
- low-resolution FFmpeg preview video assembly from timeline ranges
- retained original source audio, optional fitted BGM, fades, and ducking
- preview status, doctor diagnostics, review, run audit, and invalidation
- bounded `preview --width` and `preview --fps` controls
- preview duration, stream, dimension, profile, and audio expectation QC
- `export --profile review_720p|delivery_1080p`
- canonical `output/final_export.mp4`
- canonical `.artist-portrait/data/final_export_manifest.json`
- canonical `.artist-portrait/data/final_export_validation.json`
- deterministic `output/final_export_review.md`
- rebuildable `.artist-portrait/cache/final_export/`
- local final MP4 assembly from canonical timeline ranges
- retained original source audio and optional fitted BGM rendering in final export
- final export duration, stream, width, frame-rate, profile, stale-input, and hash QC
- final export status, doctor diagnostics, review, run audit, and invalidation
- `bgm analyze`
- canonical `.artist-portrait/data/bgm_analysis.json`
- canonical `.artist-portrait/data/bgm_beat_grids/<music_candidate_id>.json`
- deterministic `output/bgm_analysis_report.md`
- local BGM candidate RMS/peak energy windows
- quiet head/tail and high-energy range detection
- beat-engine capability detection and validated local beat-engine adapter
  execution when available
- BGM fit analysis and beat-grid evidence binding
- `bgm rhythm`
- canonical `.artist-portrait/data/bgm_rhythm_intelligence.json`
- deterministic `output/bgm_rhythm_intelligence.md`
- deterministic `output/bgm_rhythm_handoff.json`
- BGM rhythm intelligence binding into rhythm plans and rhythm media QC
- BGM analysis status, doctor diagnostics, schema, run audit, and invalidation
- `bgm recommend`
- canonical `.artist-portrait/data/bgm_recommendation_context.json`
- canonical `.artist-portrait/data/bgm_recommendation_request.json`
- deterministic `output/bgm_recommendation_agent_handoff.json`
- explicit BGM recommendation candidate quarantine and validation
- canonical `.artist-portrait/data/bgm_recommendations.json`
- deterministic `output/bgm_recommendation_review.md`
- `bgm select --recommendation-id <id>` or `bgm select --rank <n>`
- canonical `.artist-portrait/data/bgm_recommendation_selection.json`
- deterministic `output/bgm_recommendation_selection_review.md`
- `review --scope project`
- canonical `.artist-portrait/data/bgm_fit_review.json`
- deterministic `output/bgm_fit_review.md`
- `bgm review` recommendation-fit audit
- explicit `bgm fit` and `bgm select` controls for fit mode, fades, target
  gain, ducking, and beat-alignment request state
- canonical `BgmFitControls` embedded in `.artist-portrait/data/bgm_fit.json`
- `acceptance`
- `acceptance --profile standard|core|preview|delivery`
- deterministic generated real-media acceptance fixture checks
- deterministic acceptance repair-plan artifacts without automatic execution
- deterministic acceptance repair approval request/record artifacts without execution
- deterministic repair execution dry-run artifacts without command execution
- deterministic manual repair execution bundle and execution record artifacts
  without command execution
- `rhythm`
- canonical `.artist-portrait/data/rhythm_plan.json`
- deterministic `output/rhythm_report.md`
- deterministic `output/rhythm_agent_handoff.json`
- deterministic BGM/edit rhythm planning without edit-point movement,
  automatic music selection, media rendering, model calls, or network access
- canonical `.artist-portrait/data/rhythm_media_qc.json`
- deterministic `output/rhythm_media_qc.md`
- deterministic `output/rhythm_media_qc_handoff.json`
- deterministic rhythm media QC over existing preview/final artifacts without
  rendering media or mutating timeline/music
- acceptance profile integration for existing rhythm plan and rhythm media QC
  artifacts without auto-running rhythm, rhythm QC, rendering, repair execution,
  or timeline/music mutation
- `rhythm --repair-plan`
- canonical `.artist-portrait/data/rhythm_repair_plan.json`
- deterministic `output/rhythm_repair_plan.md`
- deterministic `output/rhythm_repair_handoff.json`
- deterministic rhythm manual repair planning without command execution,
  rendering, edit-point movement, automatic music selection, or automatic BGM
  fitting
- `workflow --target core|preview|delivery`
- canonical `.artist-portrait/data/workflow_plan.json`
- deterministic `output/workflow_plan.md`
- deterministic `output/workflow_agent_handoff.json`
- deterministic guided workflow planning without command execution, rendering,
  edit-point movement, automatic music selection, or automatic BGM fitting
- `workflow --execution-record <candidate.json>`
- canonical `.artist-portrait/data/workflow_execution_record_quarantine.json`
- canonical `.artist-portrait/data/workflow_execution_review.json`
- deterministic `output/workflow_execution_review.md`
- deterministic `output/workflow_execution_handoff.json`
- deterministic external workflow execution evidence review without command
  execution, rendering, edit-point movement, automatic music selection,
  automatic BGM fitting, or acceptance success promotion
- `workflow --repair-plan`
- canonical `.artist-portrait/data/workflow_repair_plan.json`
- deterministic `output/workflow_repair_plan.md`
- deterministic `output/workflow_repair_handoff.json`
- deterministic workflow evidence repair planning without command execution,
  rendering, edit-point movement, automatic music selection, automatic BGM
  fitting, or acceptance success promotion
- `workflow --approval-request`
- `workflow --approval-record <candidate.json>`
- `workflow --repair-dry-run`
- canonical workflow repair approval request, approval record, and dry-run
  artifacts without command execution or acceptance success promotion
- `workflow --repair-execution-record <candidate.json>`
- canonical `.artist-portrait/data/workflow_repair_execution_record_quarantine.json`
- canonical `.artist-portrait/data/workflow_repair_execution_review.json`
- deterministic `output/workflow_repair_execution_review.md`
- deterministic `output/workflow_repair_execution_handoff.json`
- deterministic workflow repair execution evidence review without command
  execution, rendering, edit-point movement, automatic music selection,
  automatic BGM fitting, or acceptance success promotion
- `release-check --project <project.yaml>`
- canonical `.artist-portrait/data/release_hardening_report.json`
- deterministic `output/release_hardening_report.md`
- deterministic release hardening audit without commit, push, tag, network
  access, model calls, media rendering, repair execution, or acceptance success
  promotion
- `workflow --repair-refresh-plan`
- canonical `.artist-portrait/data/workflow_repair_refresh_plan.json`
- deterministic `output/workflow_repair_refresh_plan.md`
- deterministic `output/workflow_repair_refresh_handoff.json`
- deterministic workflow repair evidence refresh guidance without command
  execution, workflow mutation, media rendering, model calls, network access,
  or acceptance success promotion
- canonical `.artist-portrait/data/acceptance_report.json`
- deterministic `output/acceptance_report.md`
- `ProjectAcceptanceReport` schema
- acceptance profile, profile-passed, and required-stage reporting
- `review --scope preview`
- `review --scope all` as project review plus implemented timeline/preview review when available
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
- automatic music recommendation or candidate selection
- automatic selection of top-ranked recommendations
- fabricated BPM or beat-grid analysis; completed BPM/beat grids require
  validated local beat-engine adapter output
- network search
- image generation or image editing
- paid API calls, API keys, remote provider calls, or hidden Python-side model calls
