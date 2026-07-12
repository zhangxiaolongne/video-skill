# Current Development Batch

## Batch Header

- Batch ID: `V2-01`
- Name: Real Video Aesthetic Baseline
- Type: product capability milestone
- Status: `completed`
- Capability gate: `V2-01`
- Acceptance prerequisite: `ACCEPTANCE-STAGE-07` completed locally
- Commit/push policy: no commit, tag, or push until V2-01 closes as one
  coherent capability version and the user approves publication
- Validation policy: use syntax, artifact-binding, and real-data static checks
  while V2-01 capability work is active. Run full pytest, `run_checks.py`,
  regression repair, and release validation once at major-version close.

## Goal Delta

Before V2-01, the real pipeline can produce a current, technically valid
`1080x1920` delivery file, but it cannot yet turn final-frame composition,
performer prominence, source branding intrusion, highlight quality, weak areas,
music/text rhythm, and second-cut judgment into a reusable editing decision.

After V2-01, one canonical real-video aesthetic baseline must explain and bind
the evidence behind duration, selected moments, rejected moments, edit concepts,
frame composition, safe reframe candidates, audiovisual rhythm risks, first-cut
weaknesses, and a supervised second-cut direction. Technical delivery acceptance
must remain distinct from aesthetic acceptance.

## Internal Acceptance Checklist

These rows are acceptance checks inside the single `V2-01` version. They are
not subversions and must not be reported or advanced independently.

| ID | Independent outcome | Acceptance | Status |
|---|---|---|---|
| `real_evidence` | Reproducible real-evidence baseline | Bind the current source, timeline, rendered media, QC, and host-reviewed frames with visible provenance. | `completed` |
| `duration_contract` | Evidence-backed duration direction | Honor CLI/project duration before recommendation and keep short-platform recommendations bounded. | `completed` |
| `composition_audit` | Final-frame composition audit | Review performer prominence, branding intrusion, dead space, crop safety, and usability without unseen semantics. | `completed` |
| `supervised_reframe` | Supervised safe-reframe candidates | Produce geometry-bound candidates with protected regions and never auto-apply them. | `completed` |
| `range_map` | Highlight and weak-area map | Bind exact timeline/source ranges to visual and local audio evidence with uncertainty. | `completed` |
| `concept_comparison` | Multiple edit-concept comparison | Compare three materially different directions and require explicit selection. | `completed` |
| `audiovisual_decision` | Audiovisual rhythm decision | Judge source audio/BGM, speech, text, cuts, transitions, pauses, composition, and ending together. | `completed` |
| `first_cut_review` | Honest first-cut aesthetic review | Separate technical validity from publishability and rank weaknesses. | `completed` |
| `second_cut_plan` | Executable supervised second-cut plan | Convert the selected direction into a non-applied cross-domain action plan. | `completed` |
| `cross_source_acceptance` | Real-video aesthetic acceptance | Validate stage and interview sources; synthetic media remains regression evidence only. | `completed` |

## Current Evidence

- Primary source: `runs/chenhaoyu_klein_blue/media/source.mp4`, 240.5 seconds.
- Current timeline: 72.15 seconds, 8 segments, all proposal-required clips retained.
- Current preview: exact `360x640`, `contain` fit, current timeline/BGM binding.
- Current delivery: exact `1080x1920 @ 30fps`, valid manifest and media QC.
- Delivery acceptance: passed, score `0.929`, no failed stage, one explicit BGM
  review warning.
- Contact-sheet finding: persistent upper/lower program branding consumes much of
  the portrait canvas and the performer is too small in several wide frames.
- Composition review: all 9 supplied frames reviewed; overall status
  `needs_reframe`; sample 03 rejected as a non-performance promotional frame.
- Reframe review: center, left-close, right-profile, and conditional-wide crop
  classes were geometry-validated and rendered as review-only contact sheets.
  No crop was applied to the timeline or final media.
- Sound finding: embedded stage/video audio remains `mixed_audio=true`; it is not
  a clean separated BGM track.
- Aesthetic map: all 8 exact timeline/source ranges are covered: 3 highlights,
  3 supporting, 1 weak, and 1 reject. Legacy clip scores remain auxiliary
  because missing transcript evidence and source-risk penalties suppress them.
- Edit concepts: `43.29s` emotional close-up, `72.15s` balanced portrait, and
  `115.44s` stage-continuity directions differ in order, crop policy, sound,
  pacing, and platform objective. None is selected; the extended direction
  explicitly requires additional source selection.
- Audiovisual decision: all 9 domains are jointly reviewed. Beat sync,
  transcript timing, and clean-BGM evidence are unavailable; the current fitted
  BGM plus mixed performance audio is a conflict until explicitly auditioned,
  and uniform nine-second cuts are not treated as rhythm alignment.
- First-cut verdict: technical delivery remains valid, but aesthetic
  publishability is `not_publishable` with maturity baseline `0.34`. Six ranked
  issues start with the promotional-card selection, broadcast-frame composition,
  weak opening, mechanical pacing, unresolved audio conflict, and unverified ending.
- Second-cut capability: `second-cut --concept-id` is implemented and rejects
  unknown choices. It produces coordinated selection, structure, trim, reframe,
  source-audio, BGM, text, transition, pause, ending, and verification actions
  without applying them.
- Selected second cut: the user chose `concept_emotional_short`. The real
  candidate contains 11 ordered cross-domain actions and owns all 6 ranked
  first-cut issues with zero unowned critical/high issues. Project-config
  `60s` overrides the stale proportional concept duration `43.29s`; no action,
  crop, timeline edit, music choice, or media render is claimed as applied.
- Contrasting interview benchmark: the user-provided 448.333-second actress
  interview produced a system-recommended `45/60/90s` ladder, chronological
  60-second final, six-frame native-16:9 composition review, no-added-music
  sound decision, and a separate aesthetic baseline. Cross-source execution
  found and fixed required-clip score reordering; source ranges now remain
  `0-10` through `50-60s`. Without transcript evidence the interview first cut
  remains honestly `not_publishable` at maturity `0.38`.
- Version validation: `243 passed`; golden baseline, BGM/rhythm quality, NLE
  round-trip, package/install simulation, schema/data checks, release readiness,
  and `git diff --check` passed. Release readiness is warning-only because the
  completed version is intentionally uncommitted and unpublished.

## Non-Counting Supporting Work

Schemas, individual fields, fixtures, tests, helper extraction, documentation,
local cache rebuilds, isolated bug fixes, and formatting support these outcomes.
They are not separate V2 progress.

## Guardrails

- Host Agent, local models, search, image generation, and mature free third-party
  tools may assist through visible provenance and explicit handoff boundaries.
- The CLI must not make hidden model/network/provider calls or require paid APIs.
- No visual content understanding may be claimed without inspected frame evidence.
- Crop/reframe candidates are proposals until explicitly selected and rendered.
- Mixed video audio is never relabeled as clean BGM without separation evidence.
- Local source/output/cache evidence remains visible and is not automatically
  deleted, committed, or packaged.

## Next Work

`V2-01` is closed locally. Plan and execute the next complete version as
`V2-02 Frame Composition And Reframing`; do not report internal checklist rows
as `V2-02-01`, `V2-02-02`, or separate versions.
