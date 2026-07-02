# Current Development Batch

## Batch Header

- Batch ID: `ACCEPTANCE-STAGE-06`
- Name: Release candidate and publication
- Type: final-acceptance release stage
- Status: `completed`
- Capability gate: `V0-051`
- Acceptance stage: `6 of 6`
- Started: `2026-07-02`
- Commit/push policy: publish only after local release-candidate validation passes

## Stage Outcome

Before this stage, the project had completed the operator workflow, golden
baseline, BGM/rhythm quality pass, and supervised NLE round-trip readiness. The
remaining final usability gap was whether the accumulated local work could be
validated as a coherent release candidate with package checks, install
simulation, full tests, explicit Git publication state, and release ledger
closeout.

After this stage, `scripts/run_release_candidate.py` audits the local release
candidate for target version `0.28.0`, canonical install simulation, package
preflight, Skill validation, Git remote/tag state, final-acceptance completion,
release ledger targeting, and publication guardrails. Stage 6 makes the project
ready for intentional commit/tag/push publication rather than leaving the final
release state implicit.

## Countability Audit Before Implementation

Audit status: `passed`. This is a final-acceptance release stage because it
closes the release-candidate validation and publication-readiness gap. Version
bump, docs edits, release checks, tests, and incidental release-ledger fixes are
support work inside the stage.

| ID | Countable stage outcome | Why it counts | Status |
|---|---|---|---|
| `AS6-01` | Release version target proof | Proves the local package targets `0.28.0` / `v0.28.0` instead of stale `v0.27.0`. | `completed` |
| `AS6-02` | Package preflight proof | Proves package metadata and Skill packaging policy pass before release. | `completed` |
| `AS6-03` | Canonical install simulation proof | Proves the Skill can be copied into the canonical install directory and revalidated. | `completed` |
| `AS6-04` | Full validation proof | Proves full pytest and project checks pass on the accumulated local work. | `completed` |
| `AS6-05` | Release candidate audit proof | Adds and runs the deterministic release-candidate audit script. | `completed` |
| `AS6-06` | Git publication-state proof | Records target tag, previous tag, remote, dirty/clean state, and publication boundary. | `completed` |
| `AS6-07` | Release ledger closeout proof | Keeps current validation, local release state, and publication state in the release ledger. | `completed` |
| `AS6-08` | Final-goal completion proof | Moves final acceptance to six of six stages completed. | `completed` |
| `AS6-09` | Publication boundary proof | Ensures release checks do not create commits, tags, pushes, network calls, or hidden model calls. | `completed` |
| `AS6-10` | Post-release handoff proof | Defines the post-release state and next maintenance boundary. | `completed` |

## Stage Acceptance Criteria

- `python3 scripts/run_release_candidate.py --allow-dirty --json` must pass or
  warn only because the working tree is intentionally unpublished.
- The release target must be `0.28.0` / `v0.28.0`; `v0.27.0` must remain the
  previous published baseline.
- Package preflight, canonical install simulation, Skill validation, schema
  drift checks, full pytest, project checks, and diff hygiene must pass.
- Final acceptance must show all six stages completed and no next acceptance
  stage.
- Release checks must not create commits, tags, pushes, network calls, model
  calls, media renders, or image generation/editing.
- Publication state must be explicit: either unpublished local release
  candidate or committed/tagged/pushed release with recorded hashes.

## Closeout

- Finished: `2026-07-02`
- Final status: `completed`
- Validation: release-candidate validation passed with package preflight,
  canonical install simulation, Skill validation, targeted Stage 6 governance
  tests, full pytest, project checks, schema drift, Python compile, JSON
  validation, and diff hygiene
- Final-goal delta: final usability moved from about 88 percent to 100 percent
  because the project now has a release-candidate validation and publication
  path on top of the completed operator, creative, media, delivery, and
  evidence flows
- Accepted boundary: Stage 6 release checks do not themselves commit, tag, push,
  call models, access the network, render media, mutate timelines, use image
  generation/editing, or execute NLE operations
- Release action: publication pending final Git commit/tag/push step until this
  completed batch is committed and tagged as `v0.28.0`
- Next batch: post-release maintenance only
