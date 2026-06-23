# V0-010h Proposal Provider Result Envelope Gate

V0-010h opens a deterministic provider result envelope. It does not open model
execution, API key use, network access, proposal payload generation, proposal
validation from provider output, BGM fitting, timeline generation, or preview
rendering.

## Scope

Allowed in this gate:

- `ProposalProviderResultEnvelope` Pydantic model.
- Committed `schemas/proposal_provider_result_envelope.schema.json`.
- Canonical `.artist-portrait/data/proposal_provider_result.json`.
- `propose` writes proposal context, text-model gate, proposal request,
  adapter preflight, provider registry, mock adapter handshake, and provider
  result envelope packets before returning the current generation boundary.
- Status and doctor diagnostics for malformed provider result envelopes.

The provider result envelope records:

- provider id
- request ref
- registry ref
- handshake ref
- adapter check ref
- expected output kind
- target schema ref
- issue list
- `payload_generated: false`
- `payload_json_ref: null`
- `validation_performed: false`
- `model_call_performed: false`
- `network_performed: false`
- `proposal_content_generated: false`

## Closed Surfaces

Still forbidden:

- reading, creating, or sending real API keys
- sending a request packet to any model
- accepting provider output as `proposals.json`
- validating generated proposal content from provider output
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

- `propose --json` output refs include `proposal_provider_result.json`.
- Blocked handshake writes a blocked provider result envelope.
- Ready mock handshake can write `ready_for_future_result_validation` but still
  does not generate proposals.
- Provider result envelope always records no payload generation.
- Provider result envelope always records no validation.
- Provider result envelope always records no model call and no network access.
- Provider result envelope always records no proposal content generation.
- Malformed `proposal_provider_result.json` is reported by `status` and
  `doctor`.
- `run_checks.py` exercises the provider result envelope path.
