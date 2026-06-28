# Release Ledger

This is the only canonical human-readable release ledger. It records meaningful
version outcomes, current validation evidence, and Git publication state.
Historical version outcomes are consolidated here. Do not recreate per-version readiness,
gate-progress, or closeout fragments.

## Current Release State

- Capability gate: `V0-024`
- Active local batch: `V0-024 project acceptance gate`
- Latest committed local baseline:
  `19fc5abe33c22c52073f16d83a60ec05ad87ab56`
- Baseline commit date: `2026-06-23`
- Baseline commit subject: `Add V0-010m execution readiness plan`
- Completed in release `v0.24.0`: V0-010n through V0-010t, V0-010 foundation
  consolidation, proposal review hardening, `DEV-GOV-001`, V0-011, V0-012,
  V0-013, V0-014, V0-015, V0-016, V0-017, V0-018, V0-020, V0-021, V0-022,
  V0-023, and V0-024
- Working-tree publication state: release closeout prepared for commit, tag,
  and push as `v0.24.0`
- Latest published capability release tag: `v0.24.0`
- Remote freshness: verify `main` and peeled `v0.24.0` after push during
  release closeout
- Publication policy: publish V0-024 as the next large functional checkpoint

## Current Validation

Validation is updated only after the complete current working tree passes.

- Verified: `2026-06-28`
- Full pytest: `271 passed`
- Project checks: `.venv/bin/python run_checks.py --skip-pytest` passed
- Skill validation: passed
- Schema drift: passed
- Media workflow: deterministic local workflow, real FFmpeg BGM analysis,
  BGM recommendation handoff/import, beat-engine evidence plumbing,
  recommendation-to-fit selection, recommendation-fit review, BGM fit controls,
  project acceptance reporting, preview/QC flow, and final export flow
  passed; proposal generation remained correctly blocked without paid API,
  API key, remote provider, or hidden network dependency
- Git diff check: passed

## Major Version History

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
