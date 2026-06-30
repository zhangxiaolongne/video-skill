# Current Development Batch

## Batch Header

- Batch ID: `V0-043`
- Name: Phrase-level manual edit guidance gate
- Type: major editing-guidance capability
- Status: `completed`
- Capability gate: `V0-043`
- Started: `2026-06-30`
- Commit/push policy: local until the next large functional release is ready

## Version Outcome

Before this batch, rhythm plans and BGM rhythm intelligence could audit timing,
BGM quality, source risk, and media QC freshness. They did not produce a
single editor-facing guidance artifact that turns evidence into concrete manual
review prompts for subtitles, transitions, pauses, ducking, phrase references,
cut/cue review, endings, source risk, QC repair, and handoff.

After this batch, `rhythm --edit-guidance` writes canonical JSON, Markdown, and
handoff artifacts with ordered phrase-level manual edit guidance. Guidance is
bound to the current rhythm plan and timeline fingerprints, may reference BGM
rhythm intelligence and rhythm media QC, and records that no edit points,
timeline data, music selection, media rendering, CLI model calls, or network
access occurred.

## Countability Audit Before Implementation

Audit status: `passed`. Each task below is a user-visible manual edit guidance
outcome. Schemas, tests, docs, and incidental fixes are support work inside
these outcomes, not separately counted.

| ID | Countable version outcome | Why it counts | Status |
|---|---|---|---|
| `V043-01` | Manual edit guidance CLI | Adds runnable `rhythm --edit-guidance` behavior. | `completed` |
| `V043-02` | Subtitle entrance guidance | Turns opening timeline/rhythm evidence into manual text timing prompts. | `completed` |
| `V043-03` | Transition review guidance | Produces transition review prompts for cut or single-segment edits. | `completed` |
| `V043-04` | Pause and breathing-room guidance | Adds manual pacing prompts around the edit midpoint. | `completed` |
| `V043-05` | Ducking review guidance | Converts ducking/silence audit state into manual audio review prompts. | `completed` |
| `V043-06` | BGM phrase reference guidance | Uses validated phrase hints when present and conservative guidance otherwise. | `completed` |
| `V043-07` | Cut-to-cue manual review guidance | Turns cut/cue audit state into manual alignment review prompts. | `completed` |
| `V043-08` | Ending style guidance | Produces manual ending review prompts tied to the final timeline range. | `completed` |
| `V043-09` | Source risk and QC repair guidance | Carries BGM provenance risk and rhythm-QC state into manual review. | `completed` |
| `V043-10` | Manual handoff and no-mutation audit | Packages guidance for editor handoff and proves no automatic mutation. | `completed` |

## Batch Acceptance Criteria

- `rhythm --edit-guidance` must require a current rhythm plan and current
timeline.
- It must write `.artist-portrait/data/edit_guidance.json`,
  `output/edit_guidance.md`, and `output/edit_guidance_handoff.json`.
- Guidance must include at least ten ordered manual actions for normal projects.
- Every guidance action must be manual-only and must not claim edits were
  applied.
- Guidance may reference BGM rhythm intelligence, rhythm media QC, rhythm plan,
  and timeline evidence, but must not create or mutate upstream artifacts.
- It must not select music, move edit points, mutate timeline, fit music,
  render media, call models from the CLI, access the network, use image
  generation/editing, or fabricate BPM/beat grids.

## Closeout

- Finished: `2026-06-30`
- Final status: `completed`
- Validation: targeted V0-043 edit-guidance/schema/gate/progress/release-check
  tests passed with `17 passed`; full pytest passed with `289 passed`;
  `run_checks.py --skip-pytest` passed; `git diff --check` passed
- Final-goal delta: rhythm evidence now becomes editor-facing manual guidance
  that can directly support subtitle, transition, pause, ducking, phrase,
  cut/cue, ending, source-risk, QC, and handoff review without automatic
  mutation
- Accepted boundary: V0-043 remains manual guidance only; automatic timeline
  edits, automatic music selection, source separation, image generation, and
  beat-synced edit mutation remain unopened
- Release action: included in published `v0.27.0`
- Next batch candidate: deeper local beat-engine adapter hardening, or manual
  guidance review/import workflow
