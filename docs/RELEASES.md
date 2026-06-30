# Release Ledger

This is the only canonical human-readable release ledger. It records meaningful
version outcomes, current validation evidence, and Git publication state.
Historical version outcomes are consolidated here. Do not recreate per-version readiness,
gate-progress, or closeout fragments.

## Current Release State

- Capability gate: `V0-041`
- Active local batch: `V0-041 workflow repair evidence refresh guidance gate`
- Current release marker: tag `v0.25.0`
- Release date: `2026-06-30`
- Release commit subject: `Release artist portrait editor v0.25.0`
- Previous published baseline:
  `d7dcab6430db4f0a6845079cebcd22cfbb85e74e`
- Completed in release `v0.24.0`: V0-010n through V0-010t, V0-010 foundation
  consolidation, proposal review hardening, `DEV-GOV-001`, V0-011, V0-012,
  V0-013, V0-014, V0-015, V0-016, V0-017, V0-018, V0-020, V0-021, V0-022,
  V0-023, and V0-024
- Release target: `v0.25.0`
- Completed in release `v0.25.0`: V0-025 through V0-041
- Working-tree publication state: `v0.25.0` committed, tagged, and pushed
- Governance state: V0-041 completed with pre-implementation countability audit
  passed; V0-030 task accounting issue is resolved as `ISSUE-014`
- Latest published capability release tag: `v0.25.0`
- Remote freshness: peeled `v0.25.0` verified at
  `2920369ec4a6217d224cb061b8c84477c38355a2` after push; annotated tag object
  `e0b6a734b055ea7b3da32819de1d926c4e39e79c`; `main` contains the
  post-release publication ledger after tag publication
- Publication policy: do not publish the next capability release until its
  release candidate has passed full local validation

## Current Validation

Validation is updated only after the complete current working tree passes.

- Verified: `v0.25.0` release validation and remote publication completed on
  `2026-06-30`
- Full pytest: `285 passed`
- Project checks: `run_checks.py --skip-pytest` passed
- Skill validation: passed
- Schema drift: passed
- Media workflow: deterministic local workflow, real FFmpeg BGM analysis,
  BGM recommendation handoff/import, beat-engine evidence plumbing,
  recommendation-to-fit selection, recommendation-fit review, BGM fit controls,
  project acceptance reporting, preview/QC flow, final export flow, rhythm
  media QC over existing preview/final artifacts, rhythm-aware acceptance
  integration, rhythm manual repair planning, guided workflow planning, and
  workflow execution evidence review, workflow evidence repair planning,
  workflow repair approval/dry-run packaging, workflow repair execution
  evidence review, accumulated workflow/rhythm release hardening, and workflow
  repair evidence refresh guidance
  passed; proposal generation remained correctly blocked without paid API,
  API key, remote provider, or hidden network dependency
- Git diff check: passed

## Major Version History

### V0-041 Workflow Repair Evidence Refresh Guidance Gate

- Status: completed locally on `2026-06-30`
- Capability: `artist-portrait workflow --repair-refresh-plan` writes
  canonical `.artist-portrait/data/workflow_repair_refresh_plan.json`,
  `output/workflow_repair_refresh_plan.md`, and
  `output/workflow_repair_refresh_handoff.json`, mapping accepted repair
  execution evidence to ready-to-resubmit workflow evidence while preserving
  rejected, missing, and skipped evidence gaps
- Boundary: no command execution, no workflow-plan mutation, no workflow or
  pipeline auto-run, no media rendering, no edit-point movement, no automatic
  music selection, no automatic BGM fitting, no fabricated BPM or beat grids,
  no CLI model calls, no network access, no paid APIs, no remote providers, no
  image generation/editing, and no treating refreshed evidence as acceptance
  success
- Validation: `285 passed`; targeted V0-041 workflow repair refresh/schema/
  gate/progress tests passed with `17 passed`; project checks including
  generated real-media workflow repair refresh guidance, Skill validation, and
  schema drift passed; `git diff --check` passed
- Git: included in release `v0.25.0`; peeled tag verified at
  `2920369ec4a6217d224cb061b8c84477c38355a2`; `main` contains the
  post-release publication ledger

### V0-040 Accumulated Workflow/Rhythm Release Hardening Gate

- Status: completed locally on `2026-06-30`
- Capability: `artist-portrait release-check --project <project.yaml>` writes
  canonical `.artist-portrait/data/release_hardening_report.json` and
  `output/release_hardening_report.md`, auditing current-gate consistency,
  local publication state, schema coverage, forbidden source surfaces,
  workflow/rhythm artifact chain, and validation evidence
- Boundary: no commit, no push, no tag, no command execution beyond local
  inspection, no workflow or pipeline auto-run, no media rendering, no
  edit-point movement, no automatic music selection, no automatic BGM fitting,
  no fabricated BPM or beat grids, no CLI model calls, no network access, no
  paid APIs, no remote providers, no image generation/editing, and no treating
  release hardening as acceptance success
- Validation: `285 passed`; targeted V0-040 release-hardening/schema/gate/
  progress tests passed with `16 passed`; project checks including generated
  real-media workflow/rhythm release hardening checks, Skill validation, and
  schema drift passed; `git diff --check` passed
- Git: local only; not committed, tagged, or pushed

### V0-039 Workflow Repair Execution Review Gate

- Status: completed locally on `2026-06-30`
- Capability: `artist-portrait workflow --repair-execution-record
  <candidate.json>` quarantines explicit external workflow repair execution
  records and writes canonical
  `.artist-portrait/data/workflow_repair_execution_review.json`,
  `output/workflow_repair_execution_review.md`, and
  `output/workflow_repair_execution_handoff.json`, validating dry-run,
  approval-record, repair-plan, target, action, command, and artifact evidence
  bindings
- Boundary: no command execution, no workflow or pipeline auto-run, no media
  rendering, no edit-point movement, no automatic music selection, no automatic
  BGM fitting, no fabricated BPM or beat grids, no CLI model calls, no network
  access, no paid APIs, no remote providers, no image generation/editing, and
  no treating repair execution evidence as acceptance success
- Validation: `284 passed`; targeted V0-039 workflow repair execution/schema/
  gate/progress tests passed with `16 passed`; project checks including
  generated real-media workflow repair execution review checks, Skill
  validation, and schema drift passed; `git diff --check` passed
- Git: local only; not committed, tagged, or pushed

### V0-038 Workflow Repair Approval Dry-Run Gate

- Status: completed locally on `2026-06-30`
- Capability: `artist-portrait workflow --approval-request`,
  `--approval-record <candidate.json>`, and `--repair-dry-run` write canonical
  approval request, approval record, and dry-run artifacts for workflow repair
  actions without executing commands
- Boundary: no command execution, no workflow or pipeline auto-run, no media
  rendering, no edit-point movement, no automatic music selection, no automatic
  BGM fitting, no fabricated BPM or beat grids, no CLI model calls, no network
  access, no paid APIs, no remote providers, no image generation/editing, and
  no treating approval/dry-run artifacts as acceptance success
- Validation: `284 passed`; targeted V0-038 workflow approval/schema/gate/
  progress tests passed with `16 passed`; project checks including generated
  real-media workflow repair approval/dry-run checks, Skill validation, and
  schema drift passed; `git diff --check` passed
- Git: local only; not committed, tagged, or pushed

### V0-037 Workflow Evidence Repair Planning Gate

- Status: completed locally on `2026-06-29`
- Capability: `artist-portrait workflow --repair-plan` writes canonical
  `.artist-portrait/data/workflow_repair_plan.json`,
  `output/workflow_repair_plan.md`, and `output/workflow_repair_handoff.json`,
  converting rejected, missing, and skipped workflow execution evidence into
  ordered required or optional manual repair actions
- Boundary: no command execution, no workflow or pipeline auto-run, no media
  rendering, no edit-point movement, no automatic music selection, no automatic
  BGM fitting, no fabricated BPM or beat grids, no CLI model calls, no network
  access, no paid APIs, no remote providers, no image generation/editing, and
  no treating repair guidance as acceptance success
- Validation: `284 passed`; targeted V0-037 workflow-repair/schema/gate/
  progress tests passed with `16 passed`; project checks including generated
  real-media workflow evidence repair planning checks, Skill validation, schema
  drift, and diff hygiene passed
- Git: local only; not committed, tagged, or pushed

### V0-036 Workflow Execution Evidence Review Gate

- Status: completed locally on `2026-06-29`
- Capability: `artist-portrait workflow --execution-record <candidate.json>`
  quarantines explicit external workflow execution records and writes canonical
  `.artist-portrait/data/workflow_execution_review.json`,
  `output/workflow_execution_review.md`, and
  `output/workflow_execution_handoff.json`, validating project, target,
  workflow-plan, step, command, and artifact evidence bindings
- Boundary: no command execution, no workflow or pipeline auto-run, no media
  rendering, no edit-point movement, no automatic music selection, no automatic
  BGM fitting, no fabricated BPM or beat grids, no CLI model calls, no network
  access, no paid APIs, no remote providers, no image generation/editing, and
  no treating execution evidence as acceptance success
- Validation: `284 passed`; targeted V0-036
  workflow-execution/schema/gate/progress tests passed with `16 passed`;
  project checks including generated real-media workflow execution evidence
  review checks, Skill validation, schema drift, and diff hygiene passed
- Git: local only; not committed, tagged, or pushed

### V0-035 Guided Workflow Planning Gate

- Status: completed locally on `2026-06-29`
- Capability: `artist-portrait workflow --target core|preview|delivery` writes
  canonical `.artist-portrait/data/workflow_plan.json`,
  `output/workflow_plan.md`, and `output/workflow_agent_handoff.json`,
  deriving a state-aware next command and explicit command path from existing
  project state, canonical artifacts, acceptance reports, and rhythm repair
  plans
- Boundary: no command execution, no pipeline auto-run, no media rendering, no
  edit-point movement, no automatic music selection, no automatic BGM fitting,
  no fabricated BPM or beat grids, no CLI model calls, no network access, no
  paid APIs, no remote providers, and no image generation/editing
- Validation: `283 passed`; targeted V0-035 workflow/schema/gate/progress tests
  passed with `16 passed`; project checks including generated real-media
  workflow checks, Skill validation, schema drift, and diff hygiene passed
- Git: local only; not committed, tagged, or pushed

### V0-034 Rhythm Manual Repair Planning Gate

- Status: completed locally on `2026-06-29`
- Capability: `artist-portrait rhythm --repair-plan` writes canonical
  `.artist-portrait/data/rhythm_repair_plan.json`,
  `output/rhythm_repair_plan.md`, and `output/rhythm_repair_handoff.json`,
  ordering manual next commands by acceptance profile from existing rhythm,
  rhythm-QC, acceptance, preview, final-export, and BGM evidence
- Boundary: no command execution, no rhythm/rhythm-QC auto-run, no media
  rendering, no edit-point movement, no automatic music selection, no
  automatic BGM fitting, no fabricated BPM or beat grids, no CLI model calls,
  no network access, no paid APIs, no remote providers, and no image
  generation/editing
- Validation: `282 passed`; targeted V0-034 rhythm/schema/gate/progress tests
  passed with `16 passed`; project checks including generated real-media rhythm
  repair-plan checks, Skill validation, schema drift, and diff hygiene passed
- Git: local only; not committed, tagged, or pushed

### V0-033 Rhythm Acceptance Integration Gate

- Status: completed locally on `2026-06-29`
- Capability: acceptance reports now include `rhythm_plan` and
  `rhythm_media_qc` stages; preview/delivery profiles require existing rhythm
  evidence; repair plans surface rhythm-specific next commands; generated
  real-media acceptance fixtures explicitly run rhythm and rhythm QC before the
  relevant profile checks
- Boundary: no acceptance-driven rhythm execution, no rhythm-QC auto-run, no
  preview/final rendering by acceptance, no repair command execution, no
  edit-point movement, no automatic music selection, no automatic BGM fitting,
  no fabricated BPM or beat grids, no CLI model calls, no network access, no
  paid APIs, no remote providers, and no image generation/editing
- Validation: `282 passed`; targeted V0-033 acceptance/governance tests passed
  with `16 passed`; project checks including generated real-media
  rhythm-aware preview/delivery acceptance, Skill validation, schema drift, and
  diff hygiene passed
- Git: local only; not committed, tagged, or pushed

### V0-032 Rhythm Media QC Gate

- Status: completed locally on `2026-06-29`
- Capability: `artist-portrait rhythm --qc` writes canonical
  `.artist-portrait/data/rhythm_media_qc.json`, `output/rhythm_media_qc.md`,
  and `output/rhythm_media_qc_handoff.json`, checking existing preview/final
  artifacts against the current rhythm plan
- Boundary: no preview/final rendering by QC, no edit-point movement, no
  automatic music selection, no automatic BGM fitting, no media mutation, no
  fabricated BPM or beat grids, no CLI model calls, no network access, no paid
  APIs, no remote providers, and no image generation/editing
- Validation: `282 passed`; targeted V0-032/schema/gate/progress tests passed
  with `16 passed`; project checks including generated real-media
  preview/final/rhythm-QC flow, Skill validation, schema drift, and diff hygiene
  passed
- Git: local only; not committed, tagged, or pushed

### V0-031 BGM/Edit Rhythm Planning Gate

- Status: completed locally on `2026-06-28`
- Capability: `artist-portrait rhythm` writes canonical
  `.artist-portrait/data/rhythm_plan.json`, `output/rhythm_report.md`, and
  `output/rhythm_agent_handoff.json`, auditing timeline rhythm, BGM rhythm,
  compatibility, explicit intent, cut/cue, transition, text, ducking/silence,
  ending, and optional external rhythm candidate validity
- Boundary: no edit-point movement, no automatic music selection, no automatic
  BGM fitting, no media rendering, no fabricated BPM or beat grids, no CLI
  model calls, no network access, no paid APIs, no remote providers, and no
  image generation/editing
- Validation: `282 passed`; targeted V0-031/schema/gate/progress tests passed
  with `16 passed`; project checks including generated real-media acceptance
  fixture, rhythm-planning assertions, Skill validation, schema drift, and diff
  hygiene passed
- Git: local only; not committed, tagged, or pushed

### V0-030 Repair Execution Handoff Gate

- Status: completed locally on `2026-06-28`
- Capability: `artist-portrait acceptance --execution-bundle` writes canonical
  `.artist-portrait/data/acceptance_repair_execution_bundle.json` and
  `output/acceptance_repair_execution_bundle.md` from approved dry-run steps,
  and `--execution-record <json>` validates external evidence into canonical
  `.artist-portrait/data/acceptance_repair_execution_record.json` and
  `output/acceptance_repair_execution_record.md`
- Boundary: no command execution by the CLI, no automatic repair, no pipeline
  reruns, no treating execution evidence as acceptance success, no proposal
  generation by CLI, no automatic music selection, no automatic BGM fitting, no
  timeline mutation, no media rendering, no model calls, no network access, no
  paid APIs, no remote providers, no fabricated beat grids, and no image
  generation/editing
- Validation: `281 passed`; targeted V0-030/schema/gate/progress tests passed
  with `17 passed`; project checks including generated real-media acceptance
  fixture, repair-plan assertions, approval-request assertions, execution
  dry-run assertions, execution bundle assertions, execution record assertions,
  Skill validation, schema drift, and diff hygiene passed
- Governance caveat: batch contract audit failed after completion; V0-030
  should not be used as precedent for satisfying the ten-task rule
- Git: local only; not committed, tagged, or pushed

### V0-029 Repair Execution Dry-Run Gate

- Status: completed locally on `2026-06-28`
- Capability: `artist-portrait acceptance --execution-dry-run` writes
  canonical `.artist-portrait/data/acceptance_repair_execution_dry_run.json`
  and `output/acceptance_repair_execution_dry_run.md`, enumerating approved and
  rejected repair actions without executing commands
- Boundary: no command execution, no automatic repair, no pipeline reruns, no
  proposal generation by CLI, no automatic music selection, no automatic BGM
  fitting, no timeline mutation, no media rendering, no model calls, no network
  access, no paid APIs, no remote providers, no fabricated beat grids, and no
  image generation/editing
- Validation: `280 passed`; targeted V0-029/schema/gate/progress tests passed
  with `16 passed`; project checks including generated real-media acceptance
  fixture, repair-plan assertions, approval-request assertions, execution
  dry-run assertions, Skill validation, schema drift, and diff hygiene passed
- Git: local only; not committed, tagged, or pushed

### V0-028 Acceptance Repair Approval Gate

- Status: completed locally on `2026-06-28`
- Capability: `artist-portrait acceptance --approval-request` writes canonical
  approval request JSON/Markdown from the current repair plan, and
  `--approval-record <json>` validates/imports explicit approval records
  against the current project, profile, repair plan, action IDs, and commands
- Boundary: approval artifacts do not execute approved actions, rerun pipeline
  steps, generate proposals, select or fit music, mutate timelines, render
  media, call models, access the network, use paid APIs, use remote providers,
  fabricate beat grids, or use image generation/editing
- Validation: `279 passed`; targeted V0-028/schema/gate/progress tests passed
  with `17 passed`; project checks including generated real-media acceptance
  fixture, repair-plan assertions, approval-request assertions, Skill
  validation, schema drift, and diff hygiene passed
- Git: local only; not committed, tagged, or pushed

### V0-027 Acceptance Repair-Plan Gate

- Status: completed locally on `2026-06-28`
- Capability: `artist-portrait acceptance --repair-plan` writes canonical
  `.artist-portrait/data/acceptance_repair_plan.json` and
  `output/acceptance_repair_plan.md`, separates profile-required actions from
  optional gaps, orders next commands, records blocked stages, and preserves
  no-execution flags
- Boundary: no automatic repair execution, no pipeline reruns, no proposal
  generation by CLI, no automatic music selection, no automatic BGM fitting, no
  timeline mutation, no media rendering, no model calls, no network access, no
  paid APIs, no remote providers, no fabricated beat grids, and no image
  generation/editing
- Validation: `277 passed`; targeted V0-027/schema/gate/progress tests passed
  with `17 passed`; project checks including generated real-media acceptance
  fixture and repair-plan assertions, Skill validation, schema drift, and diff
  hygiene passed
- Git: local only; not committed, tagged, or pushed

### V0-026 Real-Media Acceptance Fixture Gate

- Status: completed locally on `2026-06-28`
- Capability: `run_checks.py` and integration tests generate temporary local
  video/BGM media, run the project through scan, segment, keyframes, analyze,
  map, proposal handoff/import, timeline, BGM import/fit/review, preview, final
  export, and prove `core`, `preview`, and `delivery` acceptance profiles
- Boundary: no downloaded media, no network access, no CLI-side model calls, no
  automatic music selection, no automatic edit timing changes, no fabricated
  beat grids, no paid APIs, no remote providers, no durable binary fixtures,
  and no image generation/editing
- Validation: `275 passed`; targeted V0-026/gate/profile tests passed with
  `19 passed`; project checks including generated real-media acceptance fixture,
  Skill validation, schema drift, and diff hygiene passed
- Git: local only; not committed, tagged, or pushed

### V0-025 Acceptance Profile Gate

- Status: completed locally on `2026-06-28`
- Capability: `artist-portrait acceptance --profile
  standard|core|preview|delivery` records the selected profile, profile
  pass/fail state, and required stage IDs while preserving the V0-024 default
  comprehensive report behavior
- Boundary: no automatic repair, no proposal generation, no music selection, no
  BGM fitting, no timeline mutation, no media rendering, no model calls, no
  network access, no paid APIs, no remote providers, no fabricated beat grids,
  and no image generation/editing
- Validation: `274 passed`; targeted acceptance/gate/schema/progress tests
  passed with `20 passed`; project checks, Skill validation, schema drift, and
  diff hygiene passed
- Git: local only; not committed, tagged, or pushed

### V0-024 Project Acceptance Gate

- Status: completed locally on `2026-06-28`
- Capability: `artist-portrait acceptance` writes canonical
  `.artist-portrait/data/acceptance_report.json` and
  `output/acceptance_report.md`, evaluates core readiness, BGM readiness,
  preview readiness, final-export readiness, forbidden-capability flags,
  next actions, state ledger, and run audit
- Boundary: no automatic repair, no proposal generation, no music selection, no
  BGM fitting, no timeline mutation, no media rendering, no model calls, no
  network access, no paid APIs, no remote providers, no fabricated beat grids,
  and no image generation/editing
- Validation: `271 passed`; targeted V0-024/gate/schema tests passed with
  `41 passed`; project checks, Skill validation, schema drift, and diff hygiene
  passed
- Git: included in release `v0.24.0`

### V0-023 BGM Fit Controls Gate

- Status: completed locally on `2026-06-28`
- Capability: explicit `bgm fit` and `bgm select` controls for fit mode,
  fade-in/out, target gain, ducking gain/disablement, and beat-alignment
  request state; canonical `BgmFitControls` embedded in `bgm_fit.json`;
  control-bound fit IDs; recommendation-fit review surfacing of control policy
  and request state
- Boundary: no automatic music selection, no automatic top-ranked selection, no
  fitting without explicit target, no fabricated BPM/beat grids, no automatic
  edit-point movement, no media rendering from controls, no model calls, no
  network access, no paid APIs, no remote providers, and no image
  generation/editing
- Validation: `269 passed`; targeted V0-023 tests passed with `61 passed`;
  project checks, Skill validation, schema drift, and diff hygiene passed
- Git: included in release `v0.24.0`

### V0-022 Recommendation-Fit Review Gate

- Status: completed locally on `2026-06-28`
- Capability: `artist-portrait bgm review` writes canonical
  `.artist-portrait/data/bgm_fit_review.json` and `output/bgm_fit_review.md`,
  validates explicit selection freshness, recommendation identity, current BGM
  fit binding, timeline binding, analysis/beat evidence freshness, and
  preview/final-export readiness against the current fit fingerprint
- Boundary: no automatic music selection, no automatic top-ranked selection, no
  automatic fitting without explicit target, no review-driven media rendering,
  no model calls, no network access, no paid APIs, no remote providers, no
  image generation/editing, and no automatic beat-synced edit timing
- Validation: `267 passed`; targeted V0-022 tests passed with `49 passed`;
  project checks, Skill validation, schema drift, and diff hygiene passed
- Git: included in release `v0.24.0`

### V0-021 Recommendation-To-Fit Selection Gate

- Status: completed locally on `2026-06-28`
- Capability: explicit `bgm select --recommendation-id <id>` or `--rank <n>`,
  canonical BGM recommendation selection artifact, deterministic selection
  review, current recommendation/context validation, BGM fit generation for the
  selected candidate, status/doctor surfacing, schema, tests, and downstream
  preview/final-export invalidation
- Boundary: no automatic top-ranked selection, no fitting without explicit
  target, no invented candidates, no model calls, no network access, no paid
  APIs, no remote providers, no image generation/editing, and no automatic
  beat-synced edit timing
- Validation: `264 passed`; targeted V0-021 tests passed; project checks,
  Skill validation, schema drift, and diff hygiene passed
- Git: included in release `v0.24.0`

### V0-020 Beat-Engine Adapter And Evidence Gate

- Status: completed locally on `2026-06-28`
- Capability: validated local beat-engine adapter contract, canonical
  `BgmBeatGrid`, beat-engine capability discovery, BGM analysis/ledger BPM and
  beat-grid binding, fit-plan beat evidence binding, and unavailable semantics
  when no validated engine runs
- Boundary: no package installation, model download, network access, paid APIs,
  API keys, remote providers, hidden model calls, image generation/editing,
  automatic music selection, automatic beat-synced editing, source separation,
  or fabricated BPM/beat grids from energy windows
- Validation: `261 passed`; V0-020 targeted tests passed; project checks and
  Skill validation passed
- Git: local only; not committed, pushed, or tagged

### V0-019 Release Publication Closeout

- Status: completed on `2026-06-27`
- Capability published: accumulated local V0-018 capability release, including
  host-Agent proposal generation import, canonical timeline, multi-source BGM
  fitting, local preview/QC, controlled final export, local BGM technical
  intelligence, and BGM recommendation review
- Boundary: this release batch does not open new editing behavior, automatic
  music selection, beat extraction, model calls, image generation/editing,
  remote providers, paid APIs, API keys, or CLI-side network access
- Validation: `260 passed`; `.venv/bin/python run_checks.py --skip-pytest`
  passed; `git diff --check` passed; `workspace.py` remained at `8399` lines
- Git: publish on `main` with capability tag `v0.18.0`; final local and remote
  hashes are verified by Git commands during publication

### V0-018 BGM Recommendation Review Gate

- Status: completed locally on `2026-06-27`
- Capability: `artist-portrait bgm recommend`, BGM recommendation context,
  request, handoff, explicit candidate quarantine, validation, canonical
  recommendations, review report, schema, status/doctor surfacing, and
  downstream invalidation
- Boundary: automatic music selection, automatic fitting, fabricated BPM/beat
  grids, source separation, CLI-side model calls, image generation/editing,
  paid APIs, API keys, remote providers, and network access remain closed
- Validation: `260 passed`; project checks and Skill validation passed
- Git: included in release `v0.24.0`

### V0-017 Local BGM Technical Intelligence

- Status: completed locally on `2026-06-27`
- Capability: `artist-portrait bgm analyze`, canonical BGM analysis JSON,
  deterministic BGM analysis report, local PCM energy windows, quiet head/tail,
  high-energy range, loop-safe technical hints, beat-engine package detection,
  BGM fit analysis evidence binding, status/doctor/schema surfacing, and
  downstream invalidation
- Boundary: automatic music recommendation, automatic candidate selection,
  fabricated BPM/beat grids, source separation, model calls, image
  generation/editing, paid APIs, API keys, remote providers, and network access
  remain closed
- Validation: `256 passed`; project checks and Skill validation passed
- Git: not committed, pushed, or tagged

### V0-016 Controlled Local Final Export

- Status: completed locally on `2026-06-27`
- Capability: bounded `artist-portrait export` profiles, local FFmpeg/ffprobe
  final MP4 rendering from the canonical timeline, retained original audio,
  optional current BGM fit mixing, final export manifest, validation, review,
  status/doctor surfacing, run audit, and upstream invalidation
- Boundary: automatic BGM recommendation, fabricated beat alignment, model
  calls, image generation/editing, paid APIs, API keys, remote providers, and
  network access remain closed
- Validation: `253 passed`; project checks and Skill validation passed
- Git: not committed, pushed, or tagged

### V0-014 Low-Resolution Preview Rendering

- Status: completed locally on `2026-06-27`
- Capability: local FFmpeg/ffprobe low-resolution preview rendering from the
  canonical timeline, retained original audio, optional fitted BGM, gain/fade,
  loop/trim, ducking, manifest, validation, review, status/doctor, audit, and
  upstream invalidation
- Boundary: final-quality export, automatic BGM recommendation, fabricated beat
  alignment, model calls, image generation/editing, paid APIs, API keys, remote
  providers, and network access remain closed
- Validation: `244 passed`; project checks and Skill validation passed
- Git: not committed, pushed, or tagged

### V0-015 Preview Quality Review And Render Controls

- Status: completed locally on `2026-06-27`
- Capability: bounded `preview --width` and `preview --fps`, expected/actual
  duration QC, video/audio stream presence validation, dimension and frame-rate
  checks, profile drift detection, enriched preview review, status/doctor QC
  surfacing, and local-only no-final-export audit evidence
- Boundary: final-quality export, automatic BGM recommendation, fabricated beat
  alignment, model calls, image generation/editing, paid APIs, API keys, remote
  providers, and network access remain closed
- Validation: `247 passed`; project checks and Skill validation passed
- Git: not committed, pushed, or tagged

### Documentation Consolidation

- Status: completed locally on `2026-06-25`
- Outcome: removed 73 obsolete V0/Stage-A fragments, four redundant
  product/model wrappers, and four duplicate implementation specifications;
  historical outcomes now live only in this release ledger
- Current documentation footprint: six Markdown documents plus
  `current_progress.json`
- Validation impact: removed tests whose only purpose was asserting deleted
  historical Markdown content; functional coverage remains active
- Current validation: `240 passed`; full project checks passed
- Git: not committed, pushed, or tagged

### V0-013 Multi-Source BGM Ingestion And Fitting

- Status: completed locally on `2026-06-25`
- Capability: direct audio, uploaded-video extraction, canonical source audio,
  multi-candidate ledger, loudness analysis, explicit selection, and
  loop/trim/fade/ducking fitting
- Boundary: BPM and beat grid unavailable without a mature local engine; no
  automatic recommendation or preview rendering
- Validation: `270 passed`; full project checks and Skill validation passed
- Git: not committed, pushed, or tagged

### V0-012 Selected-Proposal Canonical Timeline

- Status: completed locally on `2026-06-25`
- Capability: explicit proposal selection, deterministic canonical timeline,
  validation/review, unresolved or policy-disabled music slot, state/doctor,
  run audit, and upstream invalidation
- Boundaries: no automatic proposal choice, BGM selection/fitting, preview,
  rendering, paid API, API key, remote provider, or network access
- Validation: `263 passed`; full project checks and Skill validation passed
- Git: not committed, pushed, or tagged

### Stage A: Engineering Foundation

- Status: completed
- Outcome: repository skeleton, Pydantic models, generated JSON Schema, CLI
  framework, state ledger, capability detection, fixed exit codes, and fixtures

### V0-002: Source And Package Foundation

- Status: completed
- Outcome: media scan ledger, source identity and supersession, deterministic
  reports, project review, status/doctor diagnostics, atomic report writes,
  package metadata, preflight, and install simulation

### V0-003: Media Scan Gate

- Status: completed
- Outcome: deterministic media discovery, probing, hashing, canonical
  `sources.jsonl`, scan report, and invalidation

### V0-004: Segmentation Foundation

- Status: completed
- Outcome: deterministic fixed-window segmentation, canonical `clips.jsonl`,
  clip report, diagnostics, and invalidation

### V0-005: Scene Segmentation Gate

- Status: completed
- Outcome: optional PySceneDetect routing with required/auto/off behavior and
  deterministic fallback

### V0-006: Transcription Gate

- Status: completed
- Outcome: optional local-only faster-whisper transcription, canonical
  `transcripts.jsonl`, diagnostics, and invalidation

### V0-007: Keyframe Cache Gate

- Status: completed
- Outcome: deterministic midpoint keyframe extraction, canonical ledger,
  rebuildable cache, diagnostics, and invalidation

### V0-008: Evidence Analysis Gate

- Status: completed
- Outcome: deterministic evidence-only analysis ledger and report without
  unsupported visual assertions

### V0-009: Material Map Gate

- Status: completed
- Outcome: analysis-led material map, review priority, pending confirmation,
  and risk sections without creative recommendations

### V0-010: Proposal Foundation

- Status: deterministic local foundation completed; real generation remains closed
- Outcome: proposal context, model gate, request and provider contracts,
  execution authorization and quarantine planning, response validation,
  promotion controls, canonical-write transaction planning, and deterministic
  review of existing proposals
- Hardening: centralized proposal artifact registry and IO, cross-artifact
  integrity, evidence closure, creative-brief consistency, policy/provenance
  checks, and BGM strategy validation
- Not delivered: model/provider execution, raw response capture, real proposal
  generation, proposal promotion, timeline, BGM fitting, preview, or rendering

### DEV-GOV-001: Development Governance Consolidation

- Status: completed locally
- Outcome: six canonical document owners, current batch ledger, issue ledger,
  decision ledger, release ledger, concise progress dashboard, machine-readable
  ownership, and drift checks
- Validation: `248 passed`; project checks and Skill validation passed
- Publication: local only

### V0-011: Host-Agent Evidence-Grounded Proposal Generation

- Status: completed locally
- Outcome: self-contained Codex/ChatGPT handoff, explicit candidate import,
  byte-exact quarantine, size/path/provenance controls, ProposalSet and semantic
  validation, atomic canonical promotion, status/doctor visibility, and run audit
- Cost boundary: no paid API, API key, remote provider, or network dependency
- Validation: `256 passed`; full project checks and Skill validation passed
- Publication: local only

## Release Closeout Requirements

Before a release is called publishable:

1. Complete or explicitly disposition every current batch task.
2. Resolve or accept every release-blocking issue.
3. Run the canonical full validation command.
4. Record exact current validation evidence in this file.
5. Record commit, tag, and push state without guessing remote freshness.
6. Move the completed batch outcome into the history above.
7. Open the next batch only after naming its major-version outcome.
