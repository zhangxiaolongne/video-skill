# V0-010a Proposal Readiness Gate

V0-010a opens only the proposal readiness surface. It does not generate
creative proposals.

## Scope

This gate adds:

- `ProposalSet` Pydantic contract.
- Committed `schemas/proposal_set.schema.json`.
- `artist-portrait propose --project ./project.yaml`.
- Proposal artifact summaries in `status`.
- Proposal diagnostics in `doctor`.
- Blocked `propose` state when no approved text-model gate is available.

## Command Behavior

`propose` requires `output/material_map.md`. If the material map is missing, it
returns `7 prerequisite_step_missing`.

When no approved text model is available, `propose`:

- records `propose` as `blocked` in `.artist-portrait/state.json`
- writes run metadata under `.artist-portrait/runs/`
- refreshes `output/run_report.md`
- returns `4 missing_required_dependency_for_command`
- writes no `.artist-portrait/data/proposals.json`
- writes no `output/proposals.md`

## Boundary

This gate explicitly forbids:

- fake proposals
- template proposals
- model-free creative proposals
- full creative proposal generation
- BGM selection, beat analysis, or music/timeline fitting
- timeline generation
- preview rendering
- OpenCV, vision models, embeddings, network search, image generation/editing,
  or unapproved model calls

## Acceptance

- `propose` without `material_map.md` fails with the fixed prerequisite code.
- `propose --json` without a text-model gate reports `blocked`.
- Blocked `propose` produces no fake proposal artifacts.
- Invalid `proposals.json` is visible in `status` and `doctor`.
- Schema drift checks include `proposal_set.schema.json`.
