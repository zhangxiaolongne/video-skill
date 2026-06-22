# V0-010c Text Model Gate

V0-010c opens the deterministic text-model gate contract. It does not call a
model and does not generate creative proposals.

## Scope

This gate adds:

- `TextModelGate` Pydantic contract.
- Committed `schemas/text_model_gate.schema.json`.
- `.artist-portrait/data/text_model_gate.json` written by `propose`.
- Text-model gate summaries in `status`.
- Text-model gate diagnostics in `doctor`.
- `run_checks.py` coverage that blocked `propose` writes gate reasons but no
  fake proposals.

## Command Behavior

`propose` writes `.artist-portrait/data/proposal_context.json`, then writes
`.artist-portrait/data/text_model_gate.json` from:

- `data_policy.allow_remote_text_model`
- `data_policy.include_absolute_paths_in_remote_requests`
- detected `capabilities.text_model`
- the proposal context fingerprint

Default projects remain blocked because remote text models are not allowed and
no text-model capability is detected.

If a test or future adapter makes the text-model gate ready, current `propose`
still returns `4 missing_required_dependency_for_command` with
`proposal_generation_not_implemented`. This prevents a ready gate from being
mistaken for a permission to generate proposals.

## Boundary

This gate explicitly forbids:

- text model calls
- API key creation or use
- fake proposals
- template proposals
- model-free creative proposals
- full creative proposal generation
- BGM selection, beat analysis, or music/timeline fitting
- timeline generation
- preview rendering
- OpenCV, vision models, embeddings, network search, or image generation/editing

## Acceptance

- `propose --json` default output refs include `proposal_context.json` and
  `text_model_gate.json`.
- Default gate reasons include `remote_text_model_not_allowed` and
  `text_model_capability_missing`.
- A ready text-model gate still blocks because generation is not implemented.
- Blocked `propose` writes no `proposals.json` or `proposals.md`.
- Invalid `text_model_gate.json` is visible in `status` and `doctor`.
- Schema drift checks include `text_model_gate.schema.json`.
