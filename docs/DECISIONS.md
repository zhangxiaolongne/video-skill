# Decision Ledger

This file keeps only decisions that affect the next development moves. Full
decision history is archived in [DECISIONS_HISTORY.md](archive/DECISIONS_HISTORY.md).

## Decision Status

- `active`: governs current or future work.
- `archived`: preserved for audit, no longer repeated in the current ledger.
- `superseded`: replaced by a newer active decision.

## Active Decisions

### DEC-001: Separate strategy from execution records

- Status: `active`
- Decision: the master document owns long-range product strategy; current
  progress, current batch, issues, decisions, releases, and machine progress
  each have one canonical owner.
- Rationale: repeated tactical facts created stale, bloated documents.
- Revisit when: the project no longer needs multiple ledgers.

### DEC-003: Count work by release outcome, not work type or edit count

- Status: `active`
- Decision: fields, schemas, tests, refactors, documentation, and incidental
  bug fixes are supporting work unless they close a named capability outcome.
- Rationale: small edits must not be disguised as version progress.
- Revisit when: the user changes the batch-size rule.

### DEC-004: Prefer mature third-party capabilities behind explicit gates

- Status: `active`
- Decision: use search, local tools, Image2/image generation, host-model
  judgment, and mature dependencies when they move the editing capability
  forward; do not rebuild commodity capabilities without reason.
- Rationale: the skill should become a mature editor, not a pile of local
  reimplementations.
- Revisit when: a dependency becomes unavailable, paid-only, or non-reproducible.

### DEC-005: Treat BGM as editing structure

- Status: `active`
- Decision: BGM must shape duration, hook/build/payoff, subtitle entrances/exits,
  transition timing, ducking under speech, and scene rhythm.
- Rationale: music added at the end cannot produce mature video editing.
- Revisit when: a future gate adds a validated beat/downbeat engine.

### DEC-007: Commit and push only meaningful large functional versions

- Status: `active`
- Decision: local edits may accumulate; commit, tag, and push only after a large
  capability version passes validation and the user approves publication.
- Rationale: frequent tiny commits were obscuring real progress.
- Revisit when: the user asks for a different publication cadence.

### DEC-008: Use the Codex/ChatGPT host Agent as the creative model

- Status: `active`
- Decision: the open-source skill may rely on the host Agent's model judgment for
  creative analysis and planning rather than requiring a paid API key.
- Rationale: this project is primarily for the user's local use and should not
  force paid services.
- Revisit when: the skill needs reproducible standalone model execution.

### DEC-009: Support multiple BGM input modes

- Status: `active`
- Decision: BGM may come from direct audio upload, video audio extraction,
  source-embedded audio, multiple candidates, or no selected file yet.
- Rationale: real editing sessions do not always start with clean music files.
- Revisit when: BGM extraction and rights/provenance handling are fully validated.

### DEC-010: Require explicit proposal selection before timeline generation

- Status: `active`
- Decision: the skill must not silently pick a proposal and generate a timeline;
  the operator must select or approve the direction.
- Rationale: automatic top-ranked selection can lock in the wrong aesthetic.
- Revisit when: a future supervised auto-selection gate exists.

### DEC-055: BGM/rhythm quality is validated as editing logic

- Status: `active`
- Decision: rhythm evidence is not enough by itself; BGM fit must be judged
  against text, video pacing, transitions, and emotional arc.
- Rationale: technical BPM evidence does not equal good editing.
- Revisit when: real-video aesthetic benchmarks prove mature automatic fitting.

### DEC-060: JSON surface must stay converged

- Status: `active`
- Decision: JSON files are allowed only when they are canonical machine truth,
  boundary evidence, or release-critical audit artifacts; ordinary status,
  handoff, review, and summaries should be merged into existing artifacts.
- Rationale: excessive JSON made the project look more capable than it was.
- Revisit when: a generated artifact needs independent schema ownership.

### DEC-062: V2 starts with real-video aesthetic baselines

- Status: `active`
- Decision: after the published V1 engineering/editor package baseline, the next
  capability gate is `V2-01 Real Video Aesthetic Baseline`.
- Rationale: the remaining gap is not file plumbing; it is mature aesthetic
  judgment on real footage.
- Revisit when: V2-01 acceptance evidence is complete.

### DEC-063: Keep the distributed Skill small and the local evidence bounded

- Status: `active`
- Decision: the installed Skill and Git commits exclude local `runs/`, `output/`,
  and workspace state; normal `status` reports must still show their storage
  usage. Run cache is rebuildable and removable through the CLI. Preserve selected
  source/final evidence locally, but do not package or commit it with the Skill.
- Rationale: executable source is only a few MB; media cache and historical
  blobs must not turn a maintainable local Skill into a multi-hundred-MB install.
- Revisit when: the repository history has been separately compacted after an
  explicit force-push approval.

### DEC-064: Remove simulated repair evidence chains

- Status: `active`
- Decision: acceptance reports list next commands directly. FCPXML retains only
  draft, import review, and manual repair planning. BGM recommendation embeds
  request instructions in its host-Agent handoff. Proposal/workflow chains
  retain only artifacts that produce or validate real work.
- Rationale: simulated approval, dry-run, bundle, and execution JSON did not
  improve edit quality and created high-coupling maintenance work.
- Revisit when: a future editor integration executes real, observable actions
  and requires an independently auditable boundary.

## Archive Policy

Archived decisions remain searchable in `docs/archive/DECISIONS_HISTORY.md`.
Do not copy old per-gate decisions back into this file unless they still govern
the next implementation choices.

## New Decision Template

### DEC-NNN: Title

- Status: `active`
- Decision:
- Rationale:
- Revisit when:
