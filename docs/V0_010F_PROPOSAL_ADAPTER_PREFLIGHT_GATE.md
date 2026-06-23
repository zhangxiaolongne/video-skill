# V0-010f Proposal Adapter Preflight Gate

V0-010f opens deterministic proposal adapter preflight. It does not open model
execution, API key use, network access, or proposal generation.

## Scope

Allowed in this gate:

- `ProposalAdapterCheck` Pydantic model.
- Committed `schemas/proposal_adapter_check.schema.json`.
- Canonical `.artist-portrait/data/proposal_adapter_check.json`.
- `propose` writes proposal context, text-model gate, proposal request, and
  proposal adapter preflight packets before returning the current
  dependency/generation boundary.
- Status and doctor diagnostics for malformed adapter preflight packets.
- Plaintext secret material detection in checked project artifacts.

The adapter check records:

- provider and provider mode
- request ref and request status
- target schema ref
- secret policy and allowed future secret sources
- checked refs
- issue list
- `model_call_performed: false`
- `network_performed: false`

## Closed Surfaces

Still forbidden:

- reading, creating, or sending real API keys
- sending a request packet to any model
- remote ASR
- model-downloading transcription
- OpenCV analysis
- embeddings
- vision models
- visual classification beyond explicit evidence placeholders
- fake, template, or model-free creative proposals
- full creative proposal generation
- timeline generation
- preview rendering
- BGM selection, beat analysis, music recommendation, or music/timeline fitting
- network search
- image generation or image editing
- model calls

## Acceptance

- `propose --json` output refs include `proposal_adapter_check.json`.
- Blocked request writes a blocked adapter check.
- Ready request can write `ready_for_future_adapter` but still does not
  generate proposals.
- Adapter check always records no model call and no network access.
- Plaintext secret material is an error issue.
- Malformed `proposal_adapter_check.json` is reported by `status` and
  `doctor`.
- `run_checks.py` exercises the adapter preflight path.
