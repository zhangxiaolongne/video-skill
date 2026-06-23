# V0-010g Proposal Provider Registry Gate

V0-010g opens deterministic proposal provider registry and local mock adapter
handshake packets. It does not open model execution, API key use, network
access, proposal content generation, BGM fitting, timeline generation, or
preview rendering.

## Scope

Allowed in this gate:

- `ProposalProviderRegistry` Pydantic model.
- Committed `schemas/proposal_provider_registry.schema.json`.
- Canonical `.artist-portrait/data/proposal_provider_registry.json`.
- `ProposalMockAdapterHandshake` Pydantic model.
- Committed `schemas/proposal_mock_adapter_handshake.schema.json`.
- Canonical `.artist-portrait/data/proposal_mock_adapter_handshake.json`.
- `propose` writes proposal context, text-model gate, proposal request,
  adapter preflight, provider registry, and mock adapter handshake packets
  before returning the current generation boundary.
- Status and doctor diagnostics for malformed provider registry and mock
  adapter handshake packets.

The provider registry records:

- selected provider id
- available provider records
- execution mode
- secret source
- target schema ref
- `generation_open: false`
- `model_call_performed: false`
- `network_performed: false`

The mock adapter handshake records:

- provider id
- request ref
- registry ref
- adapter check ref
- response contract ref
- issue list
- `model_call_performed: false`
- `network_performed: false`
- `proposal_content_generated: false`

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

- `propose --json` output refs include `proposal_provider_registry.json`.
- `propose --json` output refs include `proposal_mock_adapter_handshake.json`.
- Provider registry contains the deterministic `local_mock` provider.
- Provider registry always records generation closed, no model call, and no
  network access.
- Blocked request or blocked adapter preflight writes a blocked mock handshake.
- Ready request plus ready adapter preflight can write
  `ready_for_future_execution` but still does not generate proposals.
- Mock adapter handshake always records no model call, no network access, and
  no proposal content generation.
- Malformed `proposal_provider_registry.json` is reported by `status` and
  `doctor`.
- Malformed `proposal_mock_adapter_handshake.json` is reported by `status` and
  `doctor`.
- `run_checks.py` exercises the provider registry and mock adapter handshake
  path.
