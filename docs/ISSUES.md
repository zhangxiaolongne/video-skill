# Issue And Risk Ledger

This is the only canonical ledger for unresolved project issues, blockers,
accepted risks, and their resolutions. Product capability gaps are recorded
here only when they block a current or planned milestone.

## Status Vocabulary

- `open`: actionable and not yet resolved
- `blocked`: cannot proceed until the named condition changes
- `accepted`: deliberately tolerated with a documented boundary
- `resolved`: verified closed
- `superseded`: replaced by a later issue or decision

## Active Issues

### ISSUE-020: Edit brief ignores project-config target duration

- Status: `resolved`
- Severity: high
- Owner: `V2-01 duration contract repair`
- Blocking condition: none. Duration precedence is now CLI override, project
  config, then recommendation; config may omit duration explicitly.
- Impact: downstream duration options, concepts, and timelines can be generated
  from proportional source length despite an explicit project requirement.
- Resolution condition: met by optional config duration, corrected brief and
  second-cut precedence, bounded short-platform recommendations, full downstream
  invalidation, rebuilt real evidence, and complete V2-01 validation.
- Related decision: `DEC-069`

### ISSUE-019: Repository shape mixes source, rebuildable data, and history cost

- Status: `resolved`
- Severity: high
- Owner: `V2 supporting re-architecture`
- Blocking condition: none for distribution or Git. After rebuilding the
  72.15-second real final, segment cache, BGM cache, and composition frames, the
  current local workspace is about `564 MB`; `runs/` accounts for about
  `523 MB`, virtualenv about `38 MB`, executable source/docs/tests/schemas only
  a few MB, and `.git` about `1 MB`.
- Impact: routine use, installation, review, and future capability work become
  slower and make the Skill appear much larger than its actual executable source.
- Resolution condition: met by the single-root `v0.30.0` history baseline,
  package exclusions, visible local-storage diagnostics, and the rule that local
  cache/source/output evidence is preserved unless the user explicitly cleans
  it. Large local run storage is expected and must not be confused with Skill or
  Git package size.
- Related decisions: `DEC-001`, `DEC-003`, `DEC-060`

### ISSUE-018: Real-video export preserves unusable source layout

- Status: `resolved`
- Severity: high
- Owner: `V2-02 Frame Composition And Reframing`
- Blocking condition: the primary benchmark's 1080x1920 export retains large
  persistent source title/branding bands above and below the actual performance;
  the performer occupies only a small central area in sampled frames. V2-01
  proves this across 9 bound frames and supplies visually reviewed
  per-shot crop candidates, but none has been applied to the timeline or final.
- Impact: a technically valid portrait MP4 can still be visually unpublishable.
  Existing timeline, BGM, rhythm, and export checks do not evaluate final-frame
  composition or safe reframing.
- Resolution: V2-02 requires explicit per-segment selection, blocks rejected
  candidates and protected-region loss, preserves final audio, and renders an
  independent playback candidate. The real stage benchmark applies seven
  visible reframes and explicitly preserves the rejected promo-card segment;
  conditional performer and crop-jump risks remain visible warnings.
- Related decision: `DEC-062`

### ISSUE-016: Final acceptance usability is not complete

- Status: `resolved`
- Severity: high
- Owner: `final acceptance roadmap`
- Blocking condition: none after Stage 6
- Impact: the project has substantial technical substrate, but a normal
  operator now has one guided workflow path, a fixed golden real-project
  baseline, a BGM/rhythm quality pass, supervised NLE round-trip readiness, and
  a release-candidate validation/publication path
- Resolution condition: complete the six-stage final acceptance roadmap and
  pass full local validation, install simulation, release-candidate checks, and
  publication-state verification
- Related decision: `DEC-052`

### ISSUE-017: Artifact-sized gates can hide final-goal drift

- Status: `resolved`
- Severity: high
- Owner: `development governance`
- Blocking condition: none after Stage 2
- Impact: resolved; Stage 2 proved a named final-acceptance stage can close a
  real operator workflow gap instead of adding isolated artifacts
- Resolution condition: met by `ACCEPTANCE-STAGE-02` plus `run_checks.py`
  final-acceptance roadmap and anti-fragmentation checks
- Related decision: `DEC-052`

### ISSUE-015: Release check validation expected only dirty-tree warning exit

- Status: `resolved`
- Severity: medium
- Owner: `v0.25.0 release preparation`
- Blocking condition: none after `run_checks.py` accepted both release-check
  success states
- Impact: resolved; release validation now handles both dirty working-tree
  candidate checks returning warning exit `1` and clean release commits
  returning ready exit `0`
- Resolution condition: met by updating the generated real-media release
  hardening check to accept `release-check` exit codes `(0, 1)` while still
  requiring zero failed checks and no commit, push, network, or model-call
  side effects

### ISSUE-014: V0-030 task accounting violated the batch contract

- Status: `resolved`
- Severity: high
- Owner: `V0-030`
- Blocking condition: none after V0-031 countability audit
- Impact: resolved; V0-031 listed ten user-visible rhythm-planning outcomes
  with countability rationale before implementation
- Resolution condition: met by V0-031 `CURRENT_BATCH.md` countability audit and
  machine-readable `batch_contract_audit.status=passed`
- Related decision: `DEC-030`

### ISSUE-002: Final-quality rendering is complete

- Status: `resolved`
- Severity: high
- Owner: `V0-016`
- Blocking condition: none
- Impact: resolved; the Skill can render a bounded local final MP4 from the
  canonical timeline with deterministic QC
- Resolution condition: open final-quality rendering/export with deterministic
  validation, output settings, and release-grade media checks
- Related decisions: `DEC-005`, `DEC-011`, `DEC-017`

### ISSUE-011: Controlled local final export is complete

- Status: `resolved`
- Severity: high
- Owner: `V0-016`
- Blocking condition: none
- Impact: resolved; final export artifacts, review, status, doctor, audit, and
  invalidation are now available locally
- Resolution condition: met by V0-016 targeted validation and release-ledger
  evidence
- Related decision: `DEC-017`

### ISSUE-012: Local BGM technical intelligence is complete

- Status: `resolved`
- Severity: high
- Owner: `V0-017`
- Blocking condition: none
- Impact: resolved; BGM candidates now have local energy-window analysis,
  quiet/high-energy structure, technical loop hints, status/doctor surfacing,
  and fit evidence binding
- Resolution condition: met by V0-017 full validation and release-ledger
  evidence
- Related decision: `DEC-018`

### ISSUE-013: BGM recommendation review is complete

- Status: `resolved`
- Severity: high
- Owner: `V0-018`
- Blocking condition: none
- Impact: resolved; BGM recommendations can be prepared, imported,
  quarantined, validated, reviewed, and promoted without automatic selection
- Resolution condition: met by V0-018 full validation and release-ledger
  evidence
- Related decision: `DEC-019`

### ISSUE-009: Low-resolution preview rendering is complete

- Status: `resolved`
- Severity: high
- Owner: `V0-014`
- Blocking condition: none
- Impact: resolved; timeline and BGM plans can be watched and heard as local
  low-resolution review media
- Resolution condition: met by V0-014 full validation and release-ledger
  evidence
- Related decision: `DEC-015`

### ISSUE-010: Preview quality review and render controls are complete

- Status: `resolved`
- Severity: high
- Owner: `V0-015`
- Blocking condition: none
- Impact: resolved; the Skill can report whether preview media is technically
  acceptable before final export
- Resolution condition: met by V0-015 full validation and release-ledger
  evidence
- Related decision: `DEC-016`

### ISSUE-008: Beat/BPM extraction is unavailable

- Status: `accepted`
- Severity: medium
- Owner: `V0-020`
- Boundary: V0-020 adds a validated local beat-engine adapter and canonical
  beat-grid evidence contract, but the current environment still has no mature
  engine package installed; BPM remains null and beat-grid evidence remains
  absent unless a validated adapter succeeds
- Reason accepted: package installation and network access are outside the
  current gate, and PCM energy windows must not be promoted into fake BPM
- Resolution condition: install a mature local beat engine, run the validated
  adapter on project-local cached BGM, produce canonical beat-grid evidence, and
  pass stale-evidence validation without model/network calls
- Related decisions: `DEC-012`, `DEC-018`, `DEC-020`

### ISSUE-003: V0-019 accumulated local release was not committed or pushed

- Status: `resolved`
- Severity: medium
- Owner: `V0-019`
- Blocking condition: none after V0-019 publication
- Impact: resolved; the accumulated V0-011 through V0-018 capability work has a
  planned release marker on `main` with capability tag `v0.18.0`
- Resolution condition: V0-019 creates one intentional release commit, pushes
  `main`, creates and pushes the capability release tag, verifies remote branch
  and tag freshness, and records the exact evidence in `docs/RELEASES.md`
- Related decision: `DEC-007`

Resolved capability and governance history belongs to `RELEASES.md` and
`DECISIONS.md`, not this active issue ledger.

## New Issue Template

```markdown
### ISSUE-NNN: Title

- Status: `open`
- Severity: low | medium | high | critical
- Owner:
- Blocking condition:
- Impact:
- Resolution condition:
- Related decision:
```
