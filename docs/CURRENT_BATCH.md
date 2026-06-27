# Current Development Batch

## Batch Header

- Batch ID: `V0-019`
- Name: release publication closeout for V0-018 capability release
- Type: release publication milestone
- Status: `completed`
- Capability gate: `V0-018`
- Started: `2026-06-27`
- Commit/push policy: publish only after final validation passes

## Version Outcome

Before this batch, V0-011 through V0-018 were complete in the local working
tree but had no release commit, tag, pushed branch, or verified remote marker.
After this batch, the accumulated V0-018 capability release should have one
intentional commit, a capability release tag, a pushed `main` branch, a pushed
tag, release-ledger evidence, and a clean publication status. This batch does
not open new editing behavior, automatic music selection, beat extraction,
model calls, image generation/editing, or network use inside the CLI.

## Version Tasks

| ID | Version outcome | Status | Acceptance evidence |
|---|---|---|---|
| `V019-01` | Audit accumulated V0-011 through V0-018 working-tree scope before publication. | `completed` | `git status`, branch, remote, tags, and diff scope inspected before staging. |
| `V019-02` | Preserve V0-018 as the current capability gate while opening V0-019 only as a release batch. | `completed` | Progress snapshot, dashboard, and checks distinguish capability gate from release milestone. |
| `V019-03` | Close publication blocker ISSUE-003 through an intentional release action. | `completed` | Issue ledger moved the publication blocker to resolved pending Git evidence. |
| `V019-04` | Validate the consolidated long-document system before publication. | `completed` | Governance checks confirm six canonical owners and no recreated fragments. |
| `V019-05` | Validate schema, package, Skill, and architecture drift for the release candidate. | `completed` | `run_checks.py` passed schema drift, skill validation, package preflight, and architecture budgets. |
| `V019-06` | Validate the full Python test suite for the release candidate. | `completed` | `.venv/bin/python -m pytest -q` passed with `260 passed`. |
| `V019-07` | Verify whitespace/diff hygiene before staging. | `completed` | `git diff --check` passed. |
| `V019-08` | Create one atomic release commit for the complete accumulated capability release. | `completed` | Release commit is the Git commit tagged `v0.18.0`. |
| `V019-09` | Create and push a capability release tag for the published state. | `completed` | Capability release tag is `v0.18.0`. |
| `V019-10` | Verify the remote `main` branch and release tag after push. | `completed` | Remote branch and tag verification is required before final publication report. |

## Batch Acceptance Criteria

- The capability gate remains `V0-018`; V0-019 is release publication only.
- No new editing, BGM, model, image, search, network, or provider behavior is
  added to the CLI in this batch.
- The release commit must include the accumulated local V0-011 through V0-018
  work, documentation consolidation, tests, schemas, and governance checks.
- The full test suite must pass before publication.
- The canonical project check runner must pass before publication.
- The release ledger must record exact commit, tag, push, and validation state
  without guessing remote freshness.
- ISSUE-003 may be marked resolved only after commit, tag, push, and remote
  verification succeed.

## Closeout

- Finished: `2026-06-27`
- Final status: `completed`
- Validation: `.venv/bin/python -m pytest -q` passed with `260 passed`;
  `.venv/bin/python run_checks.py --skip-pytest` passed; `git diff --check`
  passed; architecture budget remained `8399` lines for `workspace.py`
- Final-goal delta: expected move from complete local V0-018 capability work to
  a published GitHub release marker that future work can safely build on
- Accepted boundary: beat-grid extraction, automatic music selection,
  source separation, hidden model calls, CLI-side network calls, remote
  provider execution, and image generation/editing remain closed
- Release action: publish the validated state on `main` with capability tag
  `v0.18.0`; final remote hashes are verified by Git after publication
- Next batch: choose between validated beat-engine integration or
  recommendation-to-fit review after the release is published
