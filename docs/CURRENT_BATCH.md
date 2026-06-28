# Current Development Batch

## Batch Header

- Batch ID: `V0-024`
- Name: project acceptance gate
- Type: major functional acceptance and readiness gate
- Status: `completed`
- Capability gate: `V0-024`
- Started: `2026-06-28`
- Commit/push policy: local until the next large functional release is ready

## Version Outcome

Before this batch, the project had many focused review artifacts, but no single
canonical report answered whether the current project was core-ready,
preview-ready, final-export-ready, or blocked by missing/stale artifacts. After
this batch, `artist-portrait acceptance` writes deterministic JSON/Markdown
acceptance reports from existing artifacts and state. It gives next actions
without automatically repairing the pipeline, generating proposals, fitting
music, rendering media, calling models, or accessing the network.

## Version Tasks

| ID | Version outcome | Status | Acceptance evidence |
|---|---|---|---|
| `V024-01` | Promote project acceptance as a real capability gate. | `completed` | Primary docs and progress snapshot name V0-024 while preserving no-auto-repair and no-render boundaries. |
| `V024-02` | Define canonical acceptance report contract. | `completed` | `ProjectAcceptanceReport` records status, readiness booleans, stage counts, issues, and no-network/model/render flags. |
| `V024-03` | Evaluate core readiness. | `completed` | Acceptance checks init, source scan, segmentation, analysis, proposal validation, and timeline validation. |
| `V024-04` | Evaluate BGM readiness. | `completed` | Acceptance checks BGM fit and recommendation-fit review without fitting or selecting music. |
| `V024-05` | Evaluate preview readiness. | `completed` | Acceptance checks preview validation and reports missing preview as a delivery warning. |
| `V024-06` | Evaluate final-export readiness. | `completed` | Acceptance checks final-export validation and reports missing final export as a delivery warning. |
| `V024-07` | Audit forbidden capability flags. | `completed` | Acceptance scans canonical artifacts for forbidden model/network/automatic-selection flags. |
| `V024-08` | Add CLI/state/run-audit integration. | `completed` | `acceptance` writes JSON/Markdown reports, state ledger entry, run result, warnings, and errors. |
| `V024-09` | Add schema and regression coverage. | `completed` | Schema drift and CLI integration tests cover warning and failed acceptance states. |
| `V024-10` | Update governance docs and hard checks for V0-024. | `completed` | Master, README, Skill, engineering spec, release/progress docs, schema checks, and gate tests reflect V0-024. |

## Batch Acceptance Criteria

- `acceptance` must write `.artist-portrait/data/acceptance_report.json`.
- `acceptance` must write `output/acceptance_report.md`.
- Acceptance must report `failed` when core artifacts are missing or invalid.
- Acceptance must report `warning` when core is ready but preview/final export
  are missing.
- Acceptance must not run missing pipeline steps, render media, generate
  proposals, select music, fit music, call models, or access the network.
- Acceptance must include next-action guidance per issue.
- Acceptance must update state/run audit when state exists.

## Closeout

- Finished: `2026-06-28`
- Final status: `completed`
- Validation: `.venv/bin/python -m pytest -q` passed with `271 passed`;
  targeted V0-024/gate/schema tests passed with `41 passed`; `.venv/bin/python
  run_checks.py --skip-pytest` passed; `git diff --check` passed
- Final-goal delta: expected move from many separate review artifacts to one
  project-level readiness report suitable for deciding whether to preview,
  export, repair, or release
- Accepted boundary: automatic repair, proposal generation, music selection,
  BGM fitting, timeline mutation, media rendering, hidden model calls,
  CLI-side network calls, remote provider execution, fabricated beat grids, and
  image generation/editing remain closed
- Release action: publish as release `v0.24.0`
- Next batch: real media fixture acceptance or phrase-level beat controls when
  validated beat evidence is present
