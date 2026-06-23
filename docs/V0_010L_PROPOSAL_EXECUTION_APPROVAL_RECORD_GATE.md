# V0-010l Proposal Execution Approval Record Gate

V0-010l opens deterministic provider execution approval record packets. It does
not grant approval, select a real secret source, read credential values, open
provider execution, call a model, touch the network, capture provider output,
generate proposals, fit BGM, generate timelines, or render previews.

## Scope

Allowed in this gate:

- `ProposalExecutionApprovalRecord` Pydantic model.
- Committed `schemas/proposal_execution_approval_record.schema.json`.
- Canonical `.artist-portrait/data/proposal_execution_approval_record.json`.
- `propose` writes proposal context, text-model gate, proposal request,
  adapter preflight, provider registry, mock adapter handshake, execution
  approval request, execution approval record, execution authorization,
  provider output quarantine, and provider result envelope packets before
  returning the current generation boundary.
- Status and doctor diagnostics for malformed execution approval record
  packets.

The execution approval record packet records:

- provider id
- approval request ref
- request ref
- registry ref
- handshake ref
- adapter check ref
- approval record fingerprint
- approval granted state
- approval actor and timestamp fields
- allowed secret-source candidates
- selected secret source
- credential read state
- network/model-call permission flags
- execution allowed/performed flags
- quarantine requirement
- issue list

## Closed Surfaces

Still forbidden:

- reading, creating, or sending real API keys
- selecting a real secret source
- reading environment variable, keychain, or encrypted secret values
- recording approval as granted
- recording a real approval actor or timestamp
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
  `proposal_execution_approval_record.json`.
- Execution approval record status is blocked in the current gate.
- Execution approval record always records `approval_granted: false`.
- Execution approval record always records `approval_actor: null`.
- Execution approval record always records `approval_recorded_at: null`.
- Execution approval record always records `approval_scope:
  none_current_gate`.
- Execution approval record lists secret-source candidates from the approval
  request.
- Execution approval record always records `selected_secret_source: null`.
- Execution approval record always records `credential_value_read: false`.
- Execution approval record always records `credential_value_ref: null`.
- Execution approval record always records no model-call or network
  permission.
- Execution approval record always records no execution allowance, no
  execution, no model call, no network access, and no proposal content
  generation.
- Execution approval record records quarantine required for future provider
  output.
- Malformed `proposal_execution_approval_record.json` is reported by `status`
  and `doctor`.
- `run_checks.py` exercises the execution approval record path.
