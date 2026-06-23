# V0-010e Proposal Request Gate

V0-010e opens deterministic proposal request packet construction. It does not
open model execution or proposal generation.

## Scope

Allowed in this gate:

- `ProposalRequestPacket` Pydantic model.
- Committed `schemas/proposal_request_packet.schema.json`.
- Canonical `.artist-portrait/data/proposal_request.json`.
- `propose` writes proposal context, text-model gate, and proposal request
  packets before returning the current dependency/generation boundary.
- Status and doctor diagnostics for malformed proposal request packets.

The request packet defines:

- target `ProposalSet` schema reference
- required proposal IDs
- system, developer, and user prompt strings
- evidence refs
- BGM requirements
- validation requirements
- refusal requirements
- text-model gate blocking reasons

## Closed Surfaces

Still forbidden:

- sending the request packet to any model
- API key creation or use
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

- `propose --json` output refs include `proposal_context.json`,
  `text_model_gate.json`, and `proposal_request.json`.
- Blocked text-model gate writes a blocked proposal request packet.
- Ready text-model gate writes a ready proposal request packet but still does
  not generate proposals.
- The request packet targets `ProposalSet`.
- Malformed `proposal_request.json` is reported by `status` and `doctor`.
- `run_checks.py` exercises the proposal request path.
