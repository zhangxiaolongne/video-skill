# Current Development Batch

## Batch Header

- Batch ID: `V2-05`
- Name: Duration And Structure Recommendation
- Type: product capability milestone
- Status: `completed`
- Capability gate: `V2-05`
- Prerequisite: published `V2-04 Highlight, Hook, And Ending Scoring`
- Publication: one commit/push after complete validation

## Goal Delta

V2-04 ranks ranges but does not turn the distribution into viable edit lengths
or structures. V2-05 produces short, standard, and extended recommendations
bound to current rankings and user goals, with explicit retained candidates,
sacrifices, role allocation, confidence, and downstream audio/text risks.

## Internal Acceptance Checklist

| ID | Outcome | Acceptance | Status |
|---|---|---|---|
| `canonical_plan` | One recommendation plan | One canonical JSON and one report. | `completed` |
| `fresh_score_binding` | Current ranking binding | Exact score-set and goal fingerprints are required. | `completed` |
| `three_durations` | Materially distinct lengths | Short, standard, and extended targets differ materially. | `completed` |
| `user_duration` | User target precedence | Explicit configured/user duration owns the standard option. | `completed` |
| `score_distribution` | Evidence-based capacity | Candidate duration and confidence constrain recommendations. | `completed` |
| `structure_roles` | Hook/build/payoff | Each option owns ordered structural roles. | `completed` |
| `retained_ranges` | Concrete retention | Recommendations list exact ranked candidates and ranges. | `completed` |
| `sacrifice_logic` | Explicit tradeoffs | Every option explains omissions and retained qualities. | `completed` |
| `coupled_risks` | Audio/text/transition effects | Downstream pressures remain visible. | `completed` |
| `real_validation` | Cross-source closeout | Stage/interview plans and full checks pass. | `completed` |

## Guardrails

- Do not mutate timelines, apply edits, render, select music, or call models.
- Low-confidence ranking cannot become high-confidence duration advice.
- Standard duration follows explicit user/config target when present.
- Short/extended options must be materially distinct, not cosmetic variants.
- Candidate ordering is a recommendation, not an applied edit.

## Closeout Evidence

- Both real projects produce exact 39/60/90-second short/standard/extended
  plans; standard preserves the configured 60-second target.
- Hook/build/payoff budgets sum to each target and ending is ranking-derived,
  not source-position-derived.
- Recommendation confidence remains about 0.25 due missing semantics.
- 243 tests and all quality/package/release/diff checks passed.

## Next Work

Publish V2-05 as one version. Plan V2-06 BGM mood/rhythm matching separately.
