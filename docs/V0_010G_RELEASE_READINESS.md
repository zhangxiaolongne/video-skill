# V0-010g Release Readiness

Status: completed locally, ready to push, not tagged.

This checkpoint closes deterministic proposal provider registry and local mock
adapter handshake packets. It validates future provider wiring without using
keys, contacting a model, touching the network, or generating proposal content.
The gate explicitly records no proposal content generation.

## Included

- `ProposalProviderRegistry` Pydantic model.
- Committed `schemas/proposal_provider_registry.schema.json`.
- Canonical `.artist-portrait/data/proposal_provider_registry.json`.
- `ProposalMockAdapterHandshake` Pydantic model.
- Committed `schemas/proposal_mock_adapter_handshake.schema.json`.
- Canonical `.artist-portrait/data/proposal_mock_adapter_handshake.json`.
- `propose` output refs now include proposal context, text-model gate,
  proposal request, adapter preflight, provider registry, and mock adapter
  handshake packets.
- Provider registry records `local_mock`, `generation_open: false`,
  `model_call_performed: false`, and `network_performed: false`.
- Mock adapter handshake records `model_call_performed: false`,
  `network_performed: false`, and `proposal_content_generated: false`.
- Status and doctor diagnostics for malformed provider registry packets.
- Status and doctor diagnostics for malformed mock adapter handshake packets.
- Contract and integration tests for schema, blocked handshake, ready
  handshake, invalid provider registry, and invalid mock handshake.
- `run_checks.py` coverage for the local provider registry and mock adapter
  handshake path.

## Still Closed

- fake, template, or model-free creative proposal generation
- full creative proposal generation
- text-model calls
- API-key setup or use
- network search
- image generation or image editing
- BGM selection, beat analysis, music recommendation, or music/timeline fitting
- timeline generation
- preview rendering
- OpenCV, embeddings, and vision models

## Validation

- `pytest: 128 passed`
- `run_checks.py: checks passed`
