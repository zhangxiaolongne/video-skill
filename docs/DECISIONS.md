# Decision Ledger

This is the canonical record of durable product, architecture, workflow, and
release decisions. Record why a choice was made and what would justify changing
it. Do not use this file as a task list.

## Decision Status

- `active`: currently binding
- `superseded`: replaced by a named later decision
- `retired`: no longer relevant because the affected system was removed

## Active Decisions

### DEC-001: Separate strategy from execution records

- Recorded: `2026-06-25`
- Status: `active`
- Decision: the master document owns stable product strategy and capability
  boundaries; tactical state is split among dedicated development ledgers
- Rationale: mixing long-term intent with volatile task and validation state
  makes both unreliable
- Consequence: strategic changes update the master; ordinary execution updates
  must not inflate it
- Revisit when: the project moves beyond V0 and adopts a new governing spec

### DEC-002: Use six canonical human-readable document owners

- Recorded: `2026-06-25`
- Status: `active`
- Decision:
  - master: strategy and engineering freeze
  - `DEVELOPMENT_PROGRESS.md`: current stage dashboard
  - `CURRENT_BATCH.md`: active batch and task status
  - `ISSUES.md`: unresolved and resolved issue ledger
  - `DECISIONS.md`: durable decisions
  - `RELEASES.md`: canonical release and validation history
- Rationale: each fact should have one owner and may be linked elsewhere rather
  than copied
- Consequence: old readiness files remain evidence but cannot claim current state
- Revisit when: one owner becomes too large or two owners prove inseparable

### DEC-003: Count work by release outcome, not work type or edit count

- Recorded: `2026-06-25`
- Status: `active`
- Decision: isolated fields, schemas, tests, refactors, and incidental bug fixes
  do not count as tasks; release-level migrations, acceptance programs,
  architectural refactors, and hardening programs may count when independently
  scoped and accepted
- Rationale: prevents task inflation without banning legitimate engineering work
- Consequence: every batch records at least ten independent version outcomes
- Revisit when: the batch-size policy itself is explicitly changed

### DEC-004: Prefer mature third-party capabilities behind explicit gates

- Recorded: `2026-06-25`
- Status: `active`
- Decision: use installed Skills, plugins, search, image tools, models, ffmpeg,
  PySceneDetect, Whisper, OpenCV, and other mature tools when the relevant gate
  permits them
- Rationale: project value lies in editing logic, evidence, review, and
  orchestration, not rebuilding commodity engines
- Consequence: third-party output requires provenance, validation, failure
  handling, and a replaceable adapter boundary
- Revisit when: a dependency fails reliability, licensing, or quality needs

### DEC-005: Treat BGM as editing structure

- Recorded: `2026-06-25`
- Status: `active`
- Decision: music strategy must coordinate with text, source rhythm, pacing,
  transitions, original audio, speech ducking, and intentional silence
- Rationale: BGM cannot be selected as a decorative final layer without
  degrading editorial coherence
- Consequence: future proposal, timeline, review, and preview gates must carry
  music metadata and synchronization evidence
- Revisit when: never for the general rule; output-specific policy may vary

### DEC-006: Never fabricate creative proposal success

- Recorded: `2026-06-25`
- Status: `active`
- Decision: when no approved model/provider path exists, `propose` remains
  blocked and may write only deterministic readiness and validation artifacts
- Rationale: fake, template, mock, or model-free proposals would misrepresent
  capability and break evidence provenance
- Consequence: V0-010t cannot call models, use network access, capture provider
  output, promote proposals, or write canonical proposals
- Revisit when: an evidence-grounded proposal-generation gate is explicitly opened

### DEC-007: Commit and push only meaningful large functional versions

- Recorded: `2026-06-25`
- Status: `active`
- Decision: do not commit or push after small fixes or minor batches; accumulate
  coherent local work and publish only after a substantial functional milestone
- Rationale: excessive micro-commits and pushes obscure product progress
- Consequence: the release ledger must clearly distinguish committed baseline
  from completed local working-tree work
- Revisit when: the user explicitly requests a different release cadence

### DEC-008: Use the Codex/ChatGPT host Agent as the creative model

- Recorded: `2026-06-25`
- Status: `active`
- Decision: this single-user Skill uses the active Codex/ChatGPT host Agent to
  generate `ProposalSet` candidates; the Python CLI does not call a paid API or
  require a local model runtime
- Rationale: the user already operates the Skill through a capable host Agent,
  and any mandatory paid dependency would violate the open-source requirement
- Consequence: the CLI exports canonical evidence and accepts an explicit
  candidate file, then quarantines, validates, reviews, and atomically promotes
  only valid output
- Revisit when: a free local runtime such as Ollama or llama.cpp is installed
  and an optional adapter provides equal or better audited behavior

### DEC-009: Support multiple BGM input modes

- Recorded: `2026-06-25`
- Status: `active`
- Decision: BGM may arrive as direct audio, audio extracted from an uploaded
  video, embedded audio from existing source media, multiple candidates, or no
  concrete file yet
- Rationale: real editing workflows do not provide music through one fixed file
  type or at one fixed stage
- Consequence: future music/timeline gates must preserve source identity,
  extraction range, stream index, content hash, rights status, and possible
  speech/vocal/environment/effect contamination for every candidate
- Revisit when: input modes expand; never collapse video audio extraction into
  an assumption that the result is clean instrumental BGM

### DEC-010: Require explicit proposal selection before timeline generation

- Recorded: `2026-06-25`
- Status: `active`
- Decision: the user selects `proposal_safe`, `proposal_advanced`, or
  `proposal_risky`; the CLI never ranks or silently chooses a proposal
- Rationale: proposal selection is an editorial decision, while canonical
  timeline construction from that decision can be deterministic and auditable
- Consequence: `timeline --proposal` binds every draft to one canonical
  ProposalSet, current clips/sources, target duration, and input fingerprint
- Revisit when: an optional recommendation feature is explicitly opened; even
  then, recommendation must remain distinct from user selection

### DEC-011: Separate BGM ingestion, selection, fitting, and rendering

- Recorded: `2026-06-25`
- Status: `active`
- Decision: users may import multiple candidates and explicitly select one;
  the CLI performs technical analysis and fit planning, while recommendation
  and preview/final rendering remain separate capabilities
- Rationale: file ingestion, editorial choice, timing fit, and media rendering
  have different evidence and failure boundaries
- Consequence: V0-013 writes canonical candidate and fit artifacts but does not
  pretend that a fit plan is an audible rendered mix
- Revisit when: preview rendering opens

### DEC-012: Do not fabricate BPM without a mature local engine

- Recorded: `2026-06-25`
- Status: `active`
- Decision: when librosa, aubio, Essentia, or an equivalent validated local
  engine is unavailable, BPM and beat grid remain null/unavailable
- Rationale: a hand-written energy heuristic would create false editing precision
- Consequence: V0-013 supports duration/loudness-based loop, trim, fade, and
  ducking plans; beat-aligned fitting is deferred
- Revisit when: a mature free local beat engine is installed and tested

### DEC-013: Consolidate historical development fragments

- Recorded: `2026-06-25`
- Status: `active`
- Decision: historical version outcomes live only in `RELEASES.md`; do not
  recreate per-version gate, readiness, acceptance, or closeout Markdown files
- Rationale: dozens of fragments duplicated current state, created dead links,
  and forced tests to protect obsolete prose rather than product behavior
- Consequence: long-term specs and six canonical governance owners remain; gate
  consistency tests assert that historical fragments stay absent
- Revisit when: never for ordinary development; use Git history for raw detail

### DEC-014: Consolidate implementation specifications

- Recorded: `2026-06-25`
- Status: `active`
- Decision: `ENGINEERING_SPEC_V0.md` owns CLI behavior, state/invalidation,
  acceptance, and data-contract policy; typed models and generated Schemas own
  field-level contracts
- Rationale: separate CLI, state, acceptance, and field-mirror documents
  repeated the same capability boundaries and drifted behind code
- Consequence: deleted four product/model wrapper specs and four implementation
  mirrors; the docs directory now has six Markdown owners plus one machine snapshot
- Revisit when: split only if one independently owned contract becomes too large

### DEC-015: Preview is local review media, not final export

- Recorded: `2026-06-27`
- Status: `active`
- Decision: V0-014 opens only low-resolution local preview rendering from the
  canonical timeline and optional current BGM fit plan
- Rationale: the next real product gap is human-visible and audible review, but
  final export requires a separate quality, settings, and release-readiness gate
- Consequence: preview may use local FFmpeg/ffprobe to render H.264 review MP4,
  assemble original audio, apply fitted BGM gain/fades/ducking, and write a
  manifest; it may not auto-select music, call models, access the network, or
  claim final delivery quality
- Revisit when: V0-014 closes and the project chooses between preview quality
  review and final export

### DEC-016: Require preview QC before final export

- Recorded: `2026-06-27`
- Status: `active`
- Decision: before opening final export, preview must support bounded render
  controls and deterministic quality checks for duration, streams, dimensions,
  profile drift, and local-only provenance
- Rationale: a watchable preview is not enough; final export should not open on
  top of media whose duration, audio/video streams, or render parameters cannot
  be verified
- Consequence: V0-015 may expand preview manifests, validation reports, review
  output, status, doctor, and tests, but it still may not render final delivery
  media or use network/model calls
- Revisit when: V0-015 closes and final export readiness is planned

### DEC-017: Final export is controlled local rendering only

- Recorded: `2026-06-27`
- Status: `active`
- Decision: V0-016 opens bounded local final MP4 export from the canonical
  timeline, explicit profile selection, retained original audio, and optional
  current BGM fit; it does not open automatic music recommendation,
  beat-aligned editing, remote rendering, network access, paid APIs, image
  generation/editing, or hidden model calls
- Rationale: final output is a real product gap after preview QC, but exporting
  a file is different from automatically making creative music and rhythm
  choices
- Consequence: `artist-portrait export` writes canonical final-export manifest,
  validation, review, run audit, status, doctor, and invalidation artifacts
  using FFmpeg/ffprobe only
- Revisit when: beat/BGM intelligence, additional delivery profiles, or release
  packaging become the next explicit capability gate

### DEC-018: BGM intelligence starts with local technical evidence

- Recorded: `2026-06-27`
- Status: `active`
- Decision: V0-017 opens local BGM technical analysis from cached candidate
  audio, including energy windows, quiet head/tail, high-energy ranges, loop
  hints, beat-engine package detection, and fit evidence binding; it does not
  open automatic music recommendation or fabricated beat grids
- Rationale: music has to coordinate with edit rhythm, but recommendation and
  beat alignment require stronger evidence than duration and loudness; technical
  local evidence is the correct next layer
- Consequence: BGM analysis becomes a canonical artifact that status, doctor,
  schemas, fit plans, preview, and final export can reason about without
  claiming unavailable BPM
- Revisit when: a mature local beat engine is installed, or a later gate opens
  explicit model/search/image/third-party recommendation workflows

### DEC-019: BGM recommendation is review, not selection

- Recorded: `2026-06-27`
- Status: `active`
- Decision: V0-018 opens BGM recommendation review through explicit handoff and
  imported recommendation JSON, but it does not automatically select, fit, or
  render a recommended candidate
- Rationale: model or third-party comparison can help judge music fit, but the
  editor still needs explicit control over the candidate that enters the
  timeline and final mix
- Consequence: recommendation output is quarantined, schema-validated, checked
  against current candidates/context, reviewed, and promoted only as a review
  artifact
- Revisit when: a later gate opens explicit recommendation-to-fit selection
  with user confirmation and validation

### DEC-020: Beat evidence requires validated local adapter output

- Recorded: `2026-06-28`
- Status: `active`
- Decision: V0-020 may execute a validated local beat-engine adapter and write
  canonical beat-grid evidence, but PCM energy windows, package presence, or
  recommendation prose must never be promoted into BPM or beat events
- Rationale: rhythm-aware editing is a real final-goal requirement, but fake
  BPM is worse than no BPM because it contaminates fitting, preview, export, and
  recommendation review
- Consequence: BGM analysis records beat-engine capabilities, writes beat-grid
  evidence only after adapter success, binds beat-grid fingerprints into
  candidates and fit plans, and keeps unavailable status when no validated
  engine runs
- Revisit when: beat-aware fit controls or recommendation-to-fit selection are
  opened with explicit user confirmation

### DEC-021: Recommendation-to-fit requires explicit user target

- Recorded: `2026-06-28`
- Status: `active`
- Decision: V0-021 may convert an imported BGM recommendation into the current
  BGM fit plan only when the user explicitly selects a recommendation ID or
  rank; the CLI must not auto-pick the top-ranked recommendation
- Rationale: recommendation review can help compare candidates, but fitting is
  an editorial act that changes the timeline music plan and invalidates preview
  and final export
- Consequence: selection is written as a separate canonical artifact with
  recommendation/context fingerprints, rationale, confidence, explicit-user
  flags, and no model/network/automatic-selection flags
- Revisit when: a later gate opens batch comparison previews or beat-aware fit
  controls with explicit user confirmation

### DEC-022: Recommendation-fit review is audit, not action

- Recorded: `2026-06-28`
- Status: `active`
- Decision: V0-022 reviews an explicit BGM recommendation selection against the
  current fit, timeline, analysis/beat evidence, preview, and final-export
  readiness; it must not select music, fit music, move edit points, render
  media, call models, or access the network
- Rationale: after music is selected, the next risk is stale or inconsistent
  evidence across fit, timeline, and rendered outputs; review must make that
  visible without silently changing editorial state
- Consequence: `bgm review` writes canonical JSON/Markdown review artifacts,
  reports missing or stale downstream media, and leaves preview/final export to
  explicit user commands
- Revisit when: a later gate opens explicit batch preview comparison or
  beat-aware fit controls

### DEC-023: BGM fit controls are explicit parameters, not automatic editing

- Recorded: `2026-06-28`
- Status: `active`
- Decision: V0-023 lets users explicitly control BGM fit mode, fades, target
  gain, ducking, and beat-alignment request state, but these controls must not
  move timeline edit points or create beat evidence
- Rationale: the user needs practical music-fit control before preview/export,
  while automatic beat-synced editing would require stronger beat, phrase, and
  editorial evidence than this gate provides
- Consequence: controls are persisted in `BgmFitControls`, bound into the fit
  ID, reused by recommendation-driven selection, and surfaced in review; media
  rendering remains an explicit preview/export command
- Revisit when: a validated beat engine is available and a later gate opens
  explicit phrase-level or beat-grid-guided edit controls

### DEC-024: Acceptance reports readiness, not automatic repair

- Recorded: `2026-06-28`
- Status: `active`
- Decision: V0-024 introduces project-level acceptance reporting that reads
  existing artifacts and state, but it must not automatically generate,
  repair, fit, render, or publish anything
- Rationale: the project now has enough pipeline pieces that the user needs one
  grounded readiness answer; automatic repair would hide which editorial or
  media step is actually missing
- Consequence: `acceptance` writes canonical JSON/Markdown reports with
  per-stage status, issues, and next actions, and records run audit/state
  without mutating creative or media outputs
- Revisit when: a later gate opens explicit guided repair with user-selected
  actions

## New Decision Template

```markdown
### DEC-NNN: Title

- Recorded: YYYY-MM-DD
- Status: `active`
- Decision:
- Rationale:
- Consequence:
- Revisit when:
```
