# V0-010b Proposal Context Gate

V0-010b opens the deterministic proposal context packet. It does not generate
creative proposals.

## Scope

This gate adds:

- `ProposalContext` Pydantic contract.
- Committed `schemas/proposal_context.schema.json`.
- `.artist-portrait/data/proposal_context.json` written by `propose`.
- Proposal context summaries in `status`.
- Proposal context diagnostics in `doctor`.
- `run_checks.py` coverage that blocked `propose` writes context but no fake
  proposals.

## Command Behavior

`propose` requires `output/material_map.md` and current upstream local ledgers.
It writes `.artist-portrait/data/proposal_context.json` from:

- `project.yaml`
- `.artist-portrait/data/sources.jsonl`
- `.artist-portrait/data/clips.jsonl`
- `.artist-portrait/data/analysis.jsonl`
- `output/material_map.md`

When no approved text model is available, `propose` still returns `4
missing_required_dependency_for_command` and records the step as `blocked`.

## Boundary

`proposal_context.json` is not a proposal. It contains deterministic inputs:
creative brief, content policy, source/clip/analysis summaries, evidence refs,
required proposal IDs, BGM requirements, and blocked capabilities.

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

- `propose --json` without a text-model gate reports `blocked`.
- Blocked `propose` writes valid `proposal_context.json`.
- Blocked `propose` writes no `proposals.json` or `proposals.md`.
- `proposal_context.json` carries BGM requirements without selecting music.
- Invalid `proposal_context.json` is visible in `status` and `doctor`.
- Schema drift checks include `proposal_context.schema.json`.
