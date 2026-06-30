# Current Development Batch

## Batch Header

- Batch ID: `V0-041`
- Name: workflow repair evidence refresh guidance gate
- Type: major workflow repair evidence refresh guidance capability
- Status: `completed`
- Capability gate: `V0-041`
- Started: `2026-06-30`
- Commit/push policy: local until the next large functional release is ready

## Version Outcome

Before this batch, workflow repair execution reviews could validate manually
executed repair evidence, but they did not produce a dedicated next-step plan
for resubmitting repaired evidence into the workflow execution review loop.
After this batch, `workflow --repair-refresh-plan` writes canonical guidance
that maps accepted, rejected, missing, and skipped repair execution evidence
into the next explicit workflow evidence refresh action.

The command does not execute workflow commands, mutate workflow plans, render
media, call models, access the network, move edit points, select music, fit
music, or treat refreshed evidence as acceptance success.

## Countability Audit Before Implementation

Audit status: `passed`. Each task below is a user-visible workflow repair
evidence refresh capability or release-level workflow safety outcome. Schemas,
tests, docs, and incidental fixes are support work inside these outcomes, not
separately counted.

| ID | Countable version outcome | Why it counts | Status |
|---|---|---|---|
| `V041-01` | Workflow repair refresh plan CLI | Adds explicit refresh guidance after repair execution review. | `completed` |
| `V041-02` | Repair execution review binding | Requires a current repair execution review before refresh planning. | `completed` |
| `V041-03` | Accepted repair action mapping | Maps accepted repair actions to ready-to-resubmit workflow evidence. | `completed` |
| `V041-04` | Failed repair action mapping | Keeps rejected repair actions blocked for another repair pass. | `completed` |
| `V041-05` | Missing/skipped repair action mapping | Preserves missing and skipped repair evidence gaps. | `completed` |
| `V041-06` | Evidence resubmission package | Carries evidence refs and missing refs into the refresh plan. | `completed` |
| `V041-07` | Current workflow refresh command | Provides the explicit next workflow execution-record command. | `completed` |
| `V041-08` | Repair refresh handoff | Writes Agent/user handoff for the refresh plan. | `completed` |
| `V041-09` | No mutation audit | Records no command execution, no workflow mutation, and no acceptance promotion. | `completed` |
| `V041-10` | Real-media repair refresh checks | Generated real-media checks prove refresh guidance in the end-to-end workflow. | `completed` |

## Batch Acceptance Criteria

- `workflow --repair-refresh-plan` must write canonical JSON, Markdown, and
  handoff artifacts.
- The refresh plan must require the current workflow repair execution review.
- Accepted repair action evidence must become `ready_to_resubmit`.
- Rejected, missing, and skipped repair action evidence must remain explicit
  gaps rather than being silently accepted.
- The plan must include evidence refs, missing refs, and the next explicit
  workflow execution-record command.
- The command must not execute commands, mutate workflow plans, render media,
  call models, access the network, or treat refreshed evidence as acceptance
  success.

## Closeout

- Finished: `2026-06-30`
- Final status: `completed`
- Validation: targeted V0-041 workflow repair refresh/schema/gate/progress
  tests passed with `17 passed`; full pytest passed with `285 passed`;
  project checks passed with `run_checks.py --skip-pytest`
- Final-goal delta: workflow repair now has a non-executing loop from failed
  workflow evidence through repair execution review into explicit evidence
  refresh guidance
- Accepted boundary: refresh planning is guidance only; workflow evidence must
  still be explicitly submitted through `workflow --execution-record`
- Release action: no commit, push, or tag until a larger functional checkpoint
  is accepted
- Next batch candidate: release preparation if approved, or BGM/beat-engine
  local adapter integration if the user wants to move beyond workflow hardening
