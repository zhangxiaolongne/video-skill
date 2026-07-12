# Current Development Batch

## Batch Header

- Batch ID: `V2-04`
- Name: Highlight, Hook, And Ending Scoring
- Type: product capability milestone
- Status: `completed`
- Capability gate: `V2-04`
- Prerequisite: published `V2-03 Transcript / Vision / Audio Evidence Fusion`
- Publication: one commit/push only after complete version validation

## Goal Delta

Before V2-04, early technical clip scores cannot explain whether a range is a
highlight, opening, or ending candidate. Missing semantics can be mistaken for
negative evidence.

After V2-04, every evidence-map unit has eight explicit editorial dimensions,
risk penalty, evidence confidence, rationale, and independent highlight/hook/
ending ranks. Rankings use only available evidence and never promote first/last
position, loudness, or missing data into aesthetic truth.

## Internal Acceptance Checklist

| ID | Outcome | Acceptance | Status |
|---|---|---|---|
| `canonical_scores` | One scoring set | One canonical JSON and one Markdown report. | `completed` |
| `fresh_map_binding` | Evidence freshness | Exact current evidence-map fingerprint is required. | `completed` |
| `eight_dimensions` | Editorial dimensions | Hook, emotion, information, visual, audio, rhythm, ending, and risk exist per unit. | `completed` |
| `unknown_neutrality` | Missing-evidence policy | Unknown semantics use neutral priors with zero confidence, not zero quality. | `completed` |
| `risk_penalty` | Explicit penalties | Missing channels and conflict risks reduce confidence/ranking. | `completed` |
| `highlight_rank` | Highlight ranking | Cross-domain score and rationale rank all eligible units. | `completed` |
| `hook_rank` | Hook ranking | Opening candidates are not selected by source position. | `completed` |
| `ending_rank` | Ending ranking | Ending candidates are not selected by source position. | `completed` |
| `goal_alignment` | User-goal binding | Theme, audience, platform, and duration evidence remain bound. | `completed` |
| `real_validation` | Cross-source closeout | Stage/interview rankings and full project checks pass. | `completed` |

## Guardrails

- Loudness is not emotion, applause, music, climax, or hook quality.
- First and last source clips receive no positional bonus.
- Missing transcript/vision semantics use neutral score with zero confidence.
- Ranking confidence must expose evidence scarcity and conflict penalties.
- No model call, network, paid API, render, timeline mutation, or music choice.

## Closeout Evidence

- Interview: 45 visual candidates; top highlight/hook/ending ranges are
  independently ranked with evidence-limited confidence around `0.2523`.
- Stage: 25 visual candidates; 25 pure-audio/BGM units are excluded from visual
  ranking; top candidates remain evidence-limited at `0.1931-0.2523` confidence.
- Position bonuses, loudness-as-emotion, and missing-as-zero flags are false.
- Validation: 243 tests and all quality/package/release/diff checks passed.

## Next Work

Publish V2-04 as one version. Plan V2-05 duration/structure recommendation from
the ranked distribution without starting it inside this batch.
