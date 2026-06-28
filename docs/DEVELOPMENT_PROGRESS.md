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
- Current local gate: V0-024 project acceptance gate
- Current milestone: `V0-024 project acceptance gate`
- Current batch: `V0-024`
- Batch status: `completed`
- Latest committed baseline: V0-010m
- Release publication target: `main` with capability tag `v0.24.0`
- Final usable Skill status: foundation, creative proposals, canonical timeline,
  BGM fitting, and local low-resolution preview rendering are substantial;
  preview quality review, render controls, controlled local final export, and
  local BGM technical intelligence, BGM recommendation review, beat-engine
  evidence plumbing, recommendation-to-fit selection, recommendation-fit
  review, explicit BGM fit controls, and project acceptance reporting are
  substantial;
  release publication target is `v0.24.0`; installed-engine BPM extraction and
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
| Preview and rendering | `completed` | Local low-resolution preview rendering from timeline plus optional BGM fit works |
| Preview quality review | `completed` | Bounded render controls and deterministic QC work before final export opens |
| Final export | `completed` | Bounded local MP4 final export from canonical timeline, retained audio, optional fitted BGM, manifest, QC, review, status, doctor, audit, and invalidation work |
| Development governance | `completed` | Six canonical owners and automatic drift checks are active |

## Current Hard Boundaries

V0-024 permits deterministic project acceptance reporting from existing
artifacts and state. It does not permit:

- paid API calls, API keys, remote provider execution, or network search
- Python-side hidden model calls or automatic paid fallback
- fake, template, mock, dummy, or model-free creative proposals
- automatic music selection
- automatic top-ranked recommendation selection
- automatic review-driven fitting or rendering
- automatic fit-control-driven edit-point movement
- automatic acceptance-driven repair or pipeline execution
- fabricated BPM/beat analysis when no validated local engine runs
- automatic beat-synced edit-point changes
- automatic final-export profile choice beyond explicit user CLI selection
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

V0-024 completed project acceptance reporting. The next major decision is
whether to do a larger release closeout, add real-media fixture acceptance, or
add phrase-level beat controls when validated beat evidence is present.
