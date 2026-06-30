# Development Progress

This is the current-stage dashboard. It answers where the project is now, how
far it is from the final goal, what is blocked, and what decision comes next.
It is not the task ledger, issue ledger, decision history, or release archive.

## Document Map

| Canonical owner | Purpose |
|---|---|
| `artist_portrait_editor_revision5_optimized.md` | Product strategy, engineering freeze, capability boundaries, and long-term editing principles |
| `docs/DEVELOPMENT_PROGRESS.md` | Current stage, capability completion, principal blockers, and next major direction |
| `docs/CURRENT_BATCH.md` | Active batch, ten version tasks, task statuses, acceptance evidence, and closeout |
| `docs/ISSUES.md` | Open, blocked, accepted, resolved, and superseded issues and risks |
| `docs/DECISIONS.md` | Durable product, architecture, workflow, and release decisions |
| `docs/RELEASES.md` | Canonical release history, current validation evidence, and Git publication state |

Implementation behavior, CLI rules, invalidation, acceptance, and data-contract
policy are consolidated in `ENGINEERING_SPEC_V0.md`. Typed models and generated
Schemas own field-level contracts.

`docs/current_progress.json` mirrors the current state for automatic checks.
Historical version outcomes are consolidated in `RELEASES.md`; per-version
readiness and gate-progress fragments must not be recreated.

## Current State

- Branch: `main`
- Remote configured: `zhangxiaolongne/video-skill`
- Canonical skill: `artist-portrait-editor`
- Current local gate: V0-041 workflow repair evidence refresh guidance gate
- Current milestone: `V0-041 workflow repair evidence refresh guidance gate`
- Current batch: `V0-041`
- Batch status: `completed`
- Current release marker: tag `v0.25.0`
- Latest published baseline: `v0.25.0`
- Release publication state: `main` and peeled `v0.25.0` verified at
  `2920369ec4a6217d224cb061b8c84477c38355a2`
- Final usable Skill status: foundation, creative proposals, canonical timeline,
  BGM fitting, and local low-resolution preview rendering are substantial;
  preview quality review, render controls, controlled local final export, and
  local BGM technical intelligence, BGM recommendation review, beat-engine
  evidence plumbing, recommendation-to-fit selection, recommendation-fit
  review, explicit BGM fit controls, project acceptance reporting, and
  profile-specific acceptance gates, and generated real-media acceptance
  fixtures, deterministic acceptance repair plans, explicit repair approval
  artifacts, non-executing repair dry-run manifests, and manual repair
  execution handoff/evidence intake, BGM/edit rhythm planning, rhythm media QC,
  rhythm-aware acceptance integration, rhythm manual repair planning, guided
  workflow planning, workflow execution evidence review, workflow evidence
  repair planning, workflow repair approval/dry-run packaging, workflow repair
  execution evidence review, accumulated workflow/rhythm release hardening, and
  workflow repair evidence refresh guidance are
  substantial;
  latest published release is `v0.25.0`; installed-engine BPM extraction and
  automatic music selection remain undelivered

## Capability Dashboard

| Capability | Status | Current meaning |
|---|---|---|
| Project/config foundation | `completed` | Validation, initialization, state, diagnostics, and package checks work |
| Media scan and identity | `completed` | Canonical source ledger and invalidation work |
| Segmentation | `completed` | Fixed-window and optional scene segmentation work |
| Local transcription | `completed` | Gated faster-whisper path and canonical ledger work |
| Keyframes | `completed` | Deterministic extraction and rebuildable cache work |
| Evidence analysis | `completed` | Deterministic evidence-only analysis works |
| Material map | `completed` | Analysis-led review map works |
| Proposal contracts and review | `completed` | Deterministic contracts and review of existing proposals work |
| Real proposal generation | `completed` | Codex/ChatGPT host Agent generates; CLI quarantines, validates, and promotes |
| Paid or remote provider execution | `forbidden` | No paid API, API key, or network dependency |
| Timeline generation | `completed` | Explicit proposal selection, canonical draft, validation, review, diagnostics, and invalidation work |
| BGM ingestion and fitting | `completed` | Multi-source candidates, explicit selection, loudness analysis, technical energy analysis, and fit planning work |
| BGM technical intelligence | `completed` | Local candidate energy windows, quiet head/tail, high-energy range, loop-safe hints, beat-engine detection, and fit evidence binding work |
| Beat-engine evidence | `completed` | Validated local beat-engine adapter gate, canonical beat-grid evidence contract, unavailable semantics, and fit-plan beat evidence binding work |
| BGM recommendation review | `completed` | Host-Agent/local-model/third-party handoff, explicit candidate import, quarantine, validation, promotion, review, and no-auto-selection boundaries work |
| Recommendation-to-fit selection | `completed` | Explicit user selection from imported BGM recommendations can generate the current BGM fit plan without auto-picking rank 1 |
| Recommendation-fit review | `completed` | Selected BGM recommendations can be audited against the current fit, timeline, analysis/beat evidence, preview, and final-export readiness |
| BGM fit controls | `completed` | Users can explicitly control fit mode, fades, gain, ducking, and beat-alignment request state without automatic edit-point movement |
| Project acceptance | `completed` | Project-level acceptance reports evaluate core, BGM, preview, final export, and forbidden-capability readiness without auto-repair |
| Acceptance profiles | `completed` | Explicit core, preview, and delivery profiles turn readiness levels into deterministic profile gates and exit codes |
| Real-media acceptance fixtures | `completed` | Generated temporary video/BGM fixtures prove core, preview, and delivery acceptance profiles against FFmpeg-backed media artifacts |
| Acceptance repair plans | `completed` | Failed or warning acceptance reports can produce deterministic required/optional next-command plans without executing repairs |
| Acceptance repair approvals | `completed` | Repair approval requests and explicit approval record imports are canonicalized without executing approved actions |
| Repair execution dry-runs | `completed` | Approved repair actions can be enumerated in canonical dry-run manifests with commands_executed=false |
| Repair execution handoffs | `completed` | Approved dry-run commands can be packaged for manual execution and explicit external execution records can be validated without CLI execution |
| BGM/edit rhythm planning | `completed` | Timeline rhythm, BGM rhythm, compatibility, intent, cut/cue, transition, text, ducking/silence, ending, and external rhythm recommendations can be audited without edit mutation |
| Rhythm media QC | `completed` | Existing preview/final artifacts can be checked against the rhythm plan for binding, freshness, duration, audio, ducking, and ending evidence without rendering |
| Rhythm acceptance integration | `completed` | Acceptance profiles now surface rhythm plan and rhythm media QC stages, require rhythm evidence for preview/delivery, and generate rhythm-specific repair commands without execution |
| Rhythm manual repair planning | `completed` | Rhythm readiness failures can be turned into ordered profile-aware manual next-command plans and handoff artifacts without execution |
| Guided workflow planning | `completed` | Core, preview, and delivery command paths can be generated from current project evidence with next-command guidance, runbook, and handoff artifacts |
| Workflow execution evidence review | `completed` | Explicit external workflow execution records can be quarantined and reviewed against workflow plan, command, and artifact evidence without CLI execution |
| Workflow evidence repair planning | `completed` | Rejected, missing, and skipped workflow evidence can be turned into ordered required/optional manual repair actions without execution |
| Workflow repair approval/dry-run | `completed` | Workflow repair actions can be packaged into approval requests, approval records, and dry-run manifests without execution |
| Workflow repair execution review | `completed` | Explicit external repair execution records can be quarantined and reviewed against dry-run action, command, and artifact evidence without CLI execution |
| Release hardening | `completed` | Current gate, publication state, schema coverage, forbidden surfaces, artifact chain, and validation evidence can be audited before release |
| Workflow repair refresh guidance | `completed` | Reviewed repair evidence can be packaged into the next explicit workflow execution-record guidance without workflow mutation |
| Preview and rendering | `completed` | Local low-resolution preview rendering from timeline plus optional BGM fit works |
| Preview quality review | `completed` | Bounded render controls and deterministic QC work before final export opens |
| Final export | `completed` | Bounded local MP4 final export from canonical timeline, retained audio, optional fitted BGM, manifest, QC, review, status, doctor, audit, and invalidation work |
| Development governance | `completed` | Six canonical owners and automatic drift checks are active; V0-041 passed pre-implementation countability audit |

## Current Hard Boundaries

V0-041 permits deterministic workflow repair evidence refresh guidance from the
current workflow repair execution review. It does not permit:

- paid API calls, API keys, remote provider execution, or network search
- Python-side hidden model calls or automatic paid fallback
- fake, template, mock, dummy, or model-free creative proposals
- automatic music selection
- automatic top-ranked recommendation selection
- automatic review-driven fitting or rendering
- automatic fit-control-driven edit-point movement
- automatic acceptance-driven repair or pipeline execution
- automatic repair-plan execution
- automatic approval-record execution
- dry-run command execution
- execution-bundle command execution by the CLI
- treating external execution records as acceptance success
- rhythm planning that moves edit points, selects music, fits music, renders
  media, calls models from the CLI, or accesses the network
- rhythm media QC that renders preview/final media, mutates timeline/music, or
  auto-repairs QC issues
- acceptance that auto-runs rhythm/rhythm QC, renders missing media, repairs
  rhythm-QC gaps, or treats manual execution evidence as acceptance success
- rhythm repair planning that executes commands, renders media, mutates
  timeline/music, or treats guidance as acceptance success
- workflow planning that executes commands, auto-runs pipeline stages, renders
  media, mutates timeline/music, selects music, fits music, calls models from
  the CLI, accesses the network, or treats guidance as acceptance success
- workflow execution evidence review that executes commands, auto-runs
  workflow or pipeline stages, renders media, mutates timeline/music, selects
  music, fits music, calls models from the CLI, accesses the network, or treats
  execution evidence as acceptance success
- workflow repair planning that executes commands, auto-runs workflow or
  pipeline stages, renders media, mutates timeline/music, selects music, fits
  music, calls models from the CLI, accesses the network, or treats repair
  guidance as acceptance success
- workflow repair approval/dry-run packaging that executes commands, auto-runs
  workflow or pipeline stages, renders media, mutates timeline/music, selects
  music, fits music, calls models from the CLI, accesses the network, or treats
  approval/dry-run artifacts as acceptance success
- workflow repair execution review that executes repair commands, auto-runs
  workflow or pipeline stages, renders media, mutates timeline/music, selects
  music, fits music, calls models from the CLI, accesses the network, or treats
  repair execution evidence as acceptance success
- workflow repair refresh planning that executes workflow commands, mutates
  workflow plans, auto-runs workflow or pipeline stages, renders media, mutates
  timeline/music, calls models from the CLI, accesses the network, or treats
  refreshed evidence as acceptance success
- release hardening that commits, pushes, tags, renders media, executes repair
  commands, auto-runs workflow or pipeline stages, mutates timeline/music,
  calls models from the CLI, accesses the network, or treats readiness as
  acceptance success
- fabricated BPM/beat analysis when no validated local engine runs
- automatic beat-synced edit-point changes
- automatic final-export profile choice beyond explicit user CLI selection
- automatic conversion from failed acceptance profile to remediation actions
- downloaded media or durable binary fixture media
- OpenCV, embeddings, vision classification, or image generation/editing

## Mandatory Batch Contract

- Plan the next big-version direction before implementation.
- Start an implementation batch only with at least ten independent version tasks.
- Count outcomes, not fields, files, tests, or edit quantity.
- Isolated fields/schemas, individual tests, local refactors, incidental bug
  fixes, docs-only changes, diagnostics, and review-rule additions are support.
- A release-level contract migration, comprehensive acceptance program,
  capability-enabling architecture refactor, or major hardening program may
  count when it has independent acceptance criteria, substantial impact, and a
  measurable final-goal delta.
- If the current gate cannot support ten real outcomes, stop and request the
  exact capability-gate promotion. Do not pad the batch.
- V0-010 foundation and proposal review are closed for ordinary expansion.

The enforceable task list lives in `CURRENT_BATCH.md`; machine-readable rules
live in `current_progress.json`.

## Non-Negotiable Implementation Principles

### Prefer Mature Third-Party Tools

Check available tools, Skills, plugins, search, image generation/editing,
models, local models, remote models, ffmpeg, ffprobe, PySceneDetect, Whisper,
OpenCV, beat-analysis libraries, and stable third-party libraries before
building a commodity capability from scratch. A validated gate may use mature
third-party tools directly, but their outputs require provenance, validation,
failure handling, and replaceable adapter boundaries.

### BGM Is Part Of Editing Logic

BGM must not be treated as a final decorative layer. Future proposal, timeline,
review, and preview gates must coordinate music with:

- multiple input modes: direct audio upload, audio extracted from an uploaded
  video, embedded source audio, multiple candidates, or no file yet
- output type, mood, genre, BPM, phrases, sections, drops, loops, and endings
- source-video rhythm, cuts, transitions, subtitle entrances/exits, and pauses
- speech-first mixing, ducking under speech, fades, retained original audio,
  transition sounds, and intentional silence
- rights status and a written explanation of why the music strategy fits

Video extraction produces a mixed audio track, not automatically a clean BGM.
Future processing must preserve the source video, extraction range, audio stream
index, hash, and contamination flags for speech, vocals, environment, and
effects. Video used as a music source must remain distinct from video used as
picture material with retained original sound.

The current gate can analyze local BGM energy structure, validate imported
recommendations, bind validated local beat-grid evidence when available, and
convert an explicit recommendation target into a BGM fit plan. Source
separation, automatic music-to-edit synchronization, automatic top-ranked
selection, and automatic edit timing changes remain unimplemented.

## Principal Blockers

- `ISSUE-008`: the current environment has no installed mature beat engine, so
  BPM output remains unavailable unless a validated local adapter succeeds.

Full status and resolution conditions live in `ISSUES.md`.

## Next Major Decision

V0-041 completed workflow repair evidence refresh guidance. The next major
decision is whether to prepare a local release with explicit approval, or move
to the next media intelligence gate.
