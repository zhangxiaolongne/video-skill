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
- Owner: future beat-analysis gate
- Boundary: V0-017 detects mature local beat-engine packages but does not
  execute beat-grid extraction; BPM remains null when no validated engine runs
- Reason accepted: no mature free local beat engine is installed in the current
  environment
- Resolution condition: install and validate a mature local beat engine and add
  deterministic beat-grid validation
- Related decisions: `DEC-012`, `DEC-018`

### ISSUE-003: Current major local release is not committed or pushed

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
