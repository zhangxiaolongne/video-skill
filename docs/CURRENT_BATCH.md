# Current Development Batch

## Batch Header

- Batch ID: `V2-11`
- Name: V2 Release
- Type: product capability milestone
- Status: `completed`
- Capability gate: `V2-11`
- Prerequisite: published `V2-10 Real Video Benchmark Pack`
- Publication: one commit/push only after complete validation

## Goal Delta

V2-11 freezes the V2 real-video aesthetic baseline as version `0.40.0`. The
release audits the complete evidence chain, current second-cut media hashes,
three-class benchmark truth, local-only package boundary, offline/provider
guardrails, version metadata, documentation, Git tag, and remote publication.

## Internal Acceptance Checklist

| ID | Outcome | Acceptance | Status |
|---|---|---|---|
| `capability_freeze` | Stable V2 scope | V2-01 through V2-10 boundaries are frozen for release. | `completed` |
| `evidence_chain` | End-to-end audit | Input through first review, second cut, and benchmark refs remain bound. | `completed` |
| `benchmark_release` | Three-class proof | Required classes and incomplete event loop remain visible. | `completed` |
| `media_hash_audit` | Current real outputs | Every closed-loop second-cut hash matches current media. | `completed` |
| `package_isolation` | Small distribution | Runs, outputs, sources, and caches remain outside the Skill package. | `completed` |
| `offline_provider_audit` | Free/local boundary | Local validation needs no paid API, model call, or network. | `completed` |
| `document_consistency` | One release truth | Master, dashboard, tasks, release ledger, and machine state agree. | `completed` |
| `version_boundary` | New V2 baseline | Package and runtime report `0.40.0`. | `completed` |
| `two_phase_candidate` | Correct publication gate | Pre-tag and post-tag release audits are distinct and strict. | `completed` |
| `git_publication` | Source and tag | One V2 source commit and annotated `v0.40.0` tag publish together. | `completed` |

## Guardrails

- Release only source, contracts, tests, and durable documentation.
- Preserve `degraded`, `not_publishable`, and input-only benchmark truth.
- Validate local second-cut hashes before tagging.
- Local validation remains offline and free of hidden provider calls.
- Do not begin V3 capability work inside V2 release hardening.

## Next Work

V2 closes as a truthful aesthetic baseline, not a mature editor. Stage and
interview have current real second cuts; event/promo remains input-only; the
three-class pack remains `degraded`. Version `0.40.0` is ready for one source
commit, annotated tag, post-tag audit, and remote publication.
