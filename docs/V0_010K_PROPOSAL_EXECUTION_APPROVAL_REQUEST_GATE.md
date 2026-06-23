# V0-010k Proposal Execution Approval Request Gate

V0-010k opens deterministic provider execution approval request packets. It
does not record approval, select a real secret source, read credential values,
open provider execution, call a model, touch the network, capture provider
output, generate proposals, fit BGM, generate timelines, or render previews.

## Scope

Allowed in this gate:

- `ProposalExecutionApprovalRequest` Pydantic model.
- Committed `schemas/proposal_execution_approval_request.schema.json`.
- Canonical `.artist-portrait/data/proposal_execution_approval_request.json`.
- `propose` writes proposal context, text-model gate, proposal request,
  adapter preflight, provider registry, mock adapter handshake, execution
  approval request, execution authorization, provider output quarantine, and
  provider result envelope packets before returning the current generation
  boundary.
- Status and doctor diagnostics for malformed execution approval request
  packets.

The execution approval request packet records:

- provider id
- request ref
- registry ref
- handshake ref
- adapter check ref
- approval fingerprint
- approval requirement and recorded state
- allowed secret-source candidates
- selected secret source
- credential read state
- network/model-call permission flags
- execution/model/network performed flags
- quarantine requirement
- issue list

## Closed Surfaces

Still forbidden:

- reading, creating, or sending real API keys
- selecting a real secret source
- reading environment variable, keychain, or encrypted secret values
- recording user approval as present
- opening provider execution
- sending a request packet to any model
- capturing real provider raw output
- writing raw output files
- parsing provider payloads
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

- `propose --json` output refs include
  `proposal_execution_approval_request.json`.
- Execution approval request status is blocked in the current gate.
- Execution approval request always records `approval_recorded: false`.
- Execution approval request always records `approval_record_ref: null`.
- Execution approval request lists secret-source candidates from adapter
  preflight.
- Execution approval request always records `selected_secret_source: null`.
- Execution approval request always records `credential_value_read: false`.
- Execution approval request always records `credential_value_ref: null`.
- Execution approval request always records no model-call or network
  permission.
- Execution approval request always records no execution, no model call, no
  network access, and no proposal content generation.
- Execution approval request records quarantine required for future provider
  output.
- Malformed `proposal_execution_approval_request.json` is reported by
  `status` and `doctor`.
- `run_checks.py` exercises the execution approval request path.
