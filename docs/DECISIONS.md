# Decision Ledger

This file keeps only decisions that affect the next development moves. Full
decision history is archived in [DECISIONS_HISTORY.md](archive/DECISIONS_HISTORY.md).

## Decision Status

- `active`: governs current or future work.
- `archived`: preserved for audit, no longer repeated in the current ledger.
- `superseded`: replaced by a newer active decision.

## Active Decisions

### DEC-048: First-cut review counts only canonical-final changes

- Status: `active`
- Decision: structure, BGM, text, and reframe artifacts remain planned or
  independent evidence until a second-cut media file is actually rendered.
  Technical delivery is the only domain that may be resolved by media QC alone.
- Rationale: otherwise planning activity falsely inflates aesthetic maturity.
- Revisit when: V2-09 renders and validates a supervised second cut.

### DEC-047: Text content requires supplied language evidence

- Status: `active`
- Decision: title text may come from the edit brief, but subtitle, emphasis,
  lyric, and speaker content require overlapping transcript or explicit user
  evidence. Missing text produces an unavailable timed slot. Sampled
  composition can require safe-region review but cannot prove motion safety.
- Rationale: invented dialogue or lyrics would corrupt both editorial meaning
  and reading-time validation.
- Revisit when: validated transcript or explicit user text is imported.

### DEC-046: Editorial ranking separates neutral unknowns from quality

- Status: `active`
- Decision: every visual candidate has eight scored dimensions with evidence
  status, confidence, rationale, and risk. Unknown semantics use a 0.5 neutral
  prior with zero confidence and explicit penalties. Pure-audio units, source
  position, and loudness cannot promote visual hook/highlight/ending rank.
- Rationale: zero-scoring unknown evidence creates false negatives, while
  rewarding loudness or source position creates false aesthetic certainty.
- Revisit when: validated transcript/vision/audio semantics support replacing
  neutral priors with evidence-backed judgments.

### DEC-045: Evidence fusion preserves missing and technical-only states

- Status: `active`
- Decision: V2 evidence fusion owns one clip-aligned canonical map. Each channel
  records availability, confidence, refs, facts, limitations, and missing
  reason. Missing transcript is not silence, keyframes are not visual semantics,
  and local energy/silence features do not classify speech, music, applause,
  emotion, lyrics, or BPM.
- Rationale: downstream aesthetic scoring is invalid if absence and unknowns are
  silently converted into zero-valued content judgments.
- Revisit when: validated local/host transcript, vision, or audio-semantic
  evidence can replace an unknown channel with provenance.

### DEC-044: Reframing is an explicit non-destructive playback boundary

- Status: `active`
- Decision: every segment explicitly selects a current composition candidate or
  preserves the frame. Application binds timeline, final, composition,
  contact-sheet, and selection hashes; rejected candidates and protected-region
  loss are blocked. Output is separate playable media with preserved final audio
  and crop-jump audit, never a replacement canonical final.
- Rationale: static crop proposals do not prove that a moving edit is safe or
  that media changed. Playable provenance-bound evidence exposes motion,
  subject-containment, and shot-change failures honestly.
- Revisit when: temporal subject tracking or supervised promotion is introduced.

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

### DEC-065: Render every output against one explicit canvas contract

- Status: `active`
- Decision: preview and final export share one public rendering boundary. Every
  segment is normalized to explicit width, height, aspect ratio, frame rate,
  pixel format, and `contain` fit before concatenation. Supported timeline fades
  must be rendered and recorded; unsupported overlaps must warn instead of being
  reported as applied.
- Rationale: width-only scaling produced a technically passing `1920x3414`
  portrait export and made mixed-aspect concatenation and transition claims
  unreliable.
- Revisit when: V2 introduces supervised crop/reframe and true overlapping
  crossfades.

### DEC-066: Validate reframing per shot instead of assuming one global crop

- Status: `active`
- Decision: a reframe candidate binds exact final-media evidence, sampled frame
  ids, source canvas, pixel crop geometry, target ratio, protected-region
  policy, confidence, and risks. Candidate previews are explicit review images;
  they do not mutate the timeline or prove a final crop was applied. Different
  subject positions require different candidates.
- Rationale: the first real fixed-center candidate passed geometry validation
  but retained title branding; the corrected center crop then clipped left and
  right subject positions. Visual preview proved that one global crop is unsafe.
- Revisit when: supervised per-segment crop selection and playback validation
  can generate an executable second-cut candidate.

### DEC-067: Keep range judgment and edit concepts in one aesthetic baseline

- Status: `active`
- Decision: V2-01 uses one canonical aesthetic baseline to bind every current
  timeline/source range to visual and local audio evidence, then compares
  exactly three materially different duration concepts. Concept selection stays
  null and the baseline does not mutate or render media.
- Rationale: separate highlight, duration, and concept JSON reports would
  recreate fragmented orchestration and invite contradictory creative claims.
- Revisit when: explicit user concept selection opens a supervised second-cut
  application boundary.

### DEC-068: Technical acceptance cannot imply aesthetic publishability

- Status: `active`
- Decision: media validation, rhythm compatibility, and delivery acceptance are
  inputs to aesthetic review, never substitutes for it. A valid export may be
  explicitly classified `not_publishable`, and unsupported legacy labels must
  be superseded inside the canonical aesthetic baseline.
- Rationale: the real benchmark passed delivery at `0.929` while retaining a
  promotional card, dominant broadcast framing, weak opening, uniform pacing,
  unresolved dual-music risk, and an unverified ending.
- Revisit when: real benchmark acceptance proves repeated agreement between
  technical gates and independent aesthetic review.

### DEC-069: Project-config duration is an explicit user requirement

- Status: `active`
- Decision: duration precedence is CLI override, then
  `creative_brief.target_duration_seconds`, then system recommendation. A
  selected aesthetic concept controls editorial direction but cannot silently
  replace an explicit project duration.
- Rationale: the real project specified 60 seconds, while the old brief path
  ignored it and generated 43.29/72.15/115.44-second proportional options.
- Revisit when: configuration distinguishes hard duration, preferred duration,
  and recommendation-only modes explicitly.

### DEC-070: Advance complete V2 versions, not numbered internal subversions

- Status: `active`
- Decision: external planning, execution, and progress reporting advance one
  complete version such as `V2-02`. Internal acceptance checks may remain in the
  batch ledger but must use descriptive ids and must not be presented as
  `V2-02-01`, `V201-01`, or independent versions.
- Rationale: subversion-style progress encouraged fragmented implementation and
  made supporting fields/tests look like product releases.
- Revisit when: never for ordinary capability development; only release tags may
  add conventional patch-level version numbers.

### DEC-071: Reread canonical rules before planning every capability version

- Status: `active`
- Decision: before planning a new version, reread the project agent rules,
  governing master principles/roadmap, current batch/progress/issues/decisions/
  releases/machine snapshot, Git state, and relevant implementation contracts;
  state scope, prohibitions, user corrections, conflicts, real acceptance, and
  non-counting support work before edits.
- Rationale: planning from recent implementation memory caused V3-02 examples
  to become a closed six-template product boundary contrary to the master.
- Revisit when: the project replaces these canonical owners with one equivalent
  rule source and automatic pre-plan audit.

### DEC-072: Style is an open composable grammar, not a source-type enum

- Status: `active`
- Decision: model content/form, aesthetic style, creative strategy, technique,
  emotional arc, and `follow/bend/break` rule mode as separate extensible axes.
  Source types may inform content compatibility but cannot determine aesthetic
  style. Break-mode creative choices require form, feeling, meaning, risk,
  playback verification, and fallback.
- Rationale: stage/interview/event describe source or output form, while idol,
  hot-blooded, inspirational, restrained, cinematic, experimental, and extreme
  reversal describe different creative dimensions.
- Revisit when: a future host-Agent grammar can generate and validate these axes
  without retaining a reusable local vocabulary.

### DEC-073: Revision meaning is compound, cross-domain, and evidence-tracked

- Status: `active`
- Decision: preserve every recognized clause in a natural-language revision
  note. Bind each clause to scope, intensity, priority, confidence, evidence,
  coupled audiovisual domains, playback acceptance, and an application status
  derived from controlled action results. Contradictions remain visible.
- Rationale: first-match keyword classification loses most of feedback such as
  “more premium, faster, less text, protect voice, stronger ending” and can make
  a plan appear more complete than the edit actually is.
- Revisit when: a validated host semantic interpreter can exceed the local
  deterministic vocabulary while retaining the same provenance and tracking.

### DEC-074: Version comparison is goal-specific, never a universal winner

- Status: `active`
- Decision: compare versions domain by domain and distinguish rendered media,
  timeline candidates, and plan-only revisions. A goal leader requires at least
  two versions with sufficient confidence; otherwise the result is unavailable.
  The system must not produce or apply an overall winner.
- Rationale: a technically valid render, a high ranking proxy, and an unrendered
  revision plan have different evidentiary strength. Collapsing them into one
  score creates fake certainty and hides tradeoffs.
- Revisit when: repeated independent human playback reviews provide a validated
  preference model while preserving explicit user goals and selection.

### DEC-075: NLE files are deliverables, not round-trip success evidence

- Status: `active`
- Decision: package source identity/hash/URI, version identity, editable
  timeline files, markers, cues, and relink guidance together. Claim round-trip
  success only after external import, relink, timeline, marker, audio, playback,
  and re-export evidence is explicitly reviewed.
- Rationale: syntactically valid FCPXML or a marker CSV can still import badly,
  point at substituted media, lose audio intent, or fail playback.
- Revisit when: the host can operate a supported NLE and import/re-export
  evidence through a validated local integration.

### DEC-076: Publishability is a per-version evidence verdict, not a winner

- Status: `active`
- Decision: assign exactly one of `publishable`, `previewable`,
  `manual_refinement_required`, or `unusable` to each current reviewed version.
  Missing/stale media and plan-only candidates are unusable. Technical validity
  permits playback but cannot satisfy aesthetic publishing. Publish blockers,
  bounded refinements, evidence gaps, and next actions remain separate. The
  highest tier may be summarized, but version selection remains null.
- Rationale: collapsing technical delivery, proxy scores, aesthetic review, and
  user preference into one winner would falsely publish weak cuts and erase the
  exact work still required.
- Revisit when: repeated independent human playback decisions support a
  calibrated quality model while explicit user selection remains intact.

### DEC-077: Creative memory stores sourced instructions, not inferred taste

- Status: `active`
- Decision: project identity may come from project config, but subject identity
  requires an explicit id and display name. Every memory entry retains category,
  polarity, strength, status, fulfillment, applicability, provenance, and
  acceptance needs. A revision request remains requested even if an action was
  applied; selected style history remains observed until user-confirmed. Only
  exact matching subject identity may import reusable entries. Conflicts remain
  unresolved and memory remains advisory until explicit selection/application.
- Rationale: filenames, generic artist labels, style candidates, proxy scores,
  and one-off revision actions cannot establish personal identity or durable
  taste. Treating them as memory would silently compound wrong assumptions over
  future projects.
- Revisit when: explicit user satisfaction evidence and repeated cross-project
  outcomes support promotion rules without removing provenance or user control.

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
