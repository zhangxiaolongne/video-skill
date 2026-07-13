# Current Development Batch

## Batch Header

- Batch ID: `V3-04`
- Name: A/B Version Review
- Type: product capability milestone
- Status: `completed`
- Capability gate: `V3-04`
- Prerequisite: published `V3-03 Interactive Revision Semantics`
- Publication: one commit/push only after complete validation

## Goal Delta

V3-04 compares two or more existing edit versions across seven editorial and
audiovisual domains. It distinguishes rendered media, timeline candidates, and
plan-only revisions; reports pairwise tradeoffs and goal-specific advantages;
and never silently selects an overall winner.

## Internal Acceptance Checklist

| ID | Outcome | Acceptance | Status |
|---|---|---|---|
| `multi_version_discovery` | Compare real alternatives | Discover canonical timeline, rendered second cut, and controlled revision candidate when present; require at least two. | `completed` |
| `evidence_level_separation` | Do not equate plans with playback | Every version is explicitly rendered media, timeline candidate, or plan-only. | `completed` |
| `freshness_binding` | Reject stale confidence | Bind artifact hashes, verify rendered media hash, and null stale revision confidence. | `completed` |
| `seven_domain_review` | Cover the master comparison | Independently assess hook, emotional arc, information density, BGM conflict, text burden, ending strength, and platform fit. | `completed` |
| `uncertainty_preservation` | Avoid fake scores | Missing or weak evidence remains unavailable/partial with confidence and limitations. | `completed` |
| `pairwise_tradeoffs` | Explain A vs B | Compare every version pair with advantages, unresolved domains, and no winner claim. | `completed` |
| `goal_specific_advantage` | Support different user goals | Report fast-hook, emotional, clarity, voice-first, text-light, ending, and delivery leaders only when two reliable candidates exist. | `completed` |
| `no_total_winner` | Preserve user choice | Overall winner is always null; explicit selection remains required. | `completed` |
| `audiovisual_truth` | Keep BGM/text/media honest | Candidate-specific BGM and text claims require matching evidence; rendered validity is not aesthetic acceptance. | `completed` |
| `real_project_comparison` | Prove actual multi-version use | Interview compares three real project versions; stale stage and input-only event boundaries remain explicit. | `completed` |

## Guardrails

- Scores are evidence summaries, not universal taste or mature publishability.
- A domain leader requires at least two sufficiently reliable comparable versions.
- No low-confidence plan proxy may outrank real playback as a supported conclusion.
- No version is selected, promoted, rendered, or written into the canonical timeline.
- CLI performs no model call, network access, or music selection.

## Real Acceptance

- `runs/interview_contrast`: three versions, three pairwise comparisons, seven domains, null overall winner, and goal-specific evidence boundaries.
- `runs/chenhaoyu_klein_blue`: stale upstream timeline/proposal state remains unsuitable for current revision/A-B claims.
- `runs/public_event_mix`: input-only baseline remains unavailable for A/B review because it has no two edit versions.

## Next Work

V3-05 NLE Round-Trip Plus may begin only after V3-04 passes full project checks
and is published as one complete capability version.
