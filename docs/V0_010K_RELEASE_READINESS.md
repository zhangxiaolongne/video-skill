# V0-010k Release Readiness

Status: completed locally, ready to push, not tagged.

This checkpoint closes deterministic provider execution approval request
packets. It defines the future approval and secret-source selection review
surface without recording approval, selecting real secrets, reading credential
values, contacting a model, touching the network, executing a provider, or
generating proposal content.

## Included

- `ProposalExecutionApprovalRequest` Pydantic model.
- Committed `schemas/proposal_execution_approval_request.schema.json`.
- Canonical `.artist-portrait/data/proposal_execution_approval_request.json`.
- `propose` output refs now include proposal context, text-model gate,
  proposal request, adapter preflight, provider registry, mock adapter
  handshake, execution approval request, execution authorization, provider
  output quarantine, and provider result envelope packets.
- Execution approval request records `approval_required: true`.
- Execution approval request records `approval_recorded: false`.
- Execution approval request records `approval_record_ref: null`.
- Execution approval request records allowed secret-source candidates.
- Execution approval request records `selected_secret_source: null`.
- Execution approval request records `credential_value_read: false`.
- Execution approval request records `credential_value_ref: null`.
- Execution approval request records `network_allowed: false`.
- Execution approval request records `model_call_allowed: false`.
- Execution approval request records `execution_performed: false`.
- Execution approval request records `model_call_performed: false`.
- Execution approval request records `network_performed: false`.
- Execution approval request records `proposal_content_generated: false`.
- Execution approval request records `quarantine_required: true`.
- Status and doctor diagnostics for malformed execution approval request
  packets.
- Contract and integration tests for schema, blocked approval request, ready
  upstream path still blocked by missing approval, and invalid approval request.
- `run_checks.py` coverage for the local execution approval request path.

## Still Closed

- fake, template, or model-free creative proposal generation
- full creative proposal generation
- text-model calls
- API-key setup or use
- real secret-source selection
- credential value reads
- raw provider output capture
- provider payload parsing
- proposal promotion from provider output
- network search
- image generation or image editing
- BGM selection, beat analysis, music recommendation, or music/timeline fitting
- timeline generation
- preview rendering
- OpenCV, embeddings, and vision models

## Validation

- `pytest: 136 passed`
- `run_checks.py: checks passed`
