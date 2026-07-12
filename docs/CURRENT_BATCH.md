# Current Development Batch

## Batch Header

- Batch ID: `V2-10`
- Name: Real Video Benchmark Pack
- Type: product capability milestone
- Status: `completed`
- Capability gate: `V2-10`
- Prerequisite: published `V2-09 Second-Cut Candidate Generation`
- Publication: one commit/push only after complete validation

## Goal Delta

V2-10 establishes one repeatable real-video benchmark pack across stage person,
interview/talking head, and event/promo mix. Each class binds real inputs, goals,
a ten-domain checklist, failure examples, and acceptance status. Incomplete
loops remain visible and synthetic fixtures cannot count as real evidence.

## Internal Acceptance Checklist

| ID | Outcome | Acceptance | Status |
|---|---|---|---|
| `three_class_coverage` | Distinct real classes | Stage, interview, and event/promo are all required. | `completed` |
| `source_provenance` | Verifiable input truth | Sources bind hashes, rights, duration, and local project refs. | `completed` |
| `multi_source_event` | New input pressure | Four real CC0 event files exercise multi-source scanning. | `completed` |
| `goal_binding` | Comparable briefs | Every benchmark binds platform, duration, aspect, and creative goal. | `completed` |
| `ten_domain_checklist` | Shared aesthetic rubric | Every class uses the same ten review domains. | `completed` |
| `failure_examples` | Regression evidence | High-risk and unavailable behavior remains explicit. | `completed` |
| `closed_loop_binding` | Real edit evidence | Two classes bind first review and valid second-cut media. | `completed` |
| `quality_matrix` | Cross-format truth | Source count, duration, rights, outputs, and QC are comparable. | `completed` |
| `cross_case_findings` | Type-specific judgment | Interview, stage, and event risks remain distinct. | `completed` |
| `reproducible_report` | One canonical pack | One JSON/schema and one human report reproduce acceptance. | `completed` |

## Guardrails

- Require three genuinely distinct real-video classes.
- Do not count synthetic fixtures or relabeled duplicate footage as real coverage.
- Keep media local and excluded from Skill/Git publication.
- CLI remains local-only; host-fetched public sources require explicit provenance.
- Technical validity remains separate from aesthetic maturity.

## Next Work

The pack covers all three required classes. Stage and interview have valid real
first/second-cut loops; event/promo has four CC0 real sources totaling 189.74s,
an explicit 30s goal, and an honest input-only acceptance state. The pack is
`degraded`, not mature. V2-11 release hardening is next.
