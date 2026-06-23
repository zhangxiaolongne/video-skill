# V0-010m Proposal Execution Readiness Plan Gate

V0-010m closes five execution-readiness sub-stages in one deterministic packet:
secret-source selection, credential access, execution planning, provider call
preflight, and output capture planning. It does not select secrets, read
credential values, allow execution, call a model, touch the network, capture
provider output, generate proposals, fit BGM, generate timelines, or render
previews.

## Scope

Allowed in this gate:

- `ProposalExecutionReadinessPlan` Pydantic model.
- Committed `schemas/proposal_execution_readiness_plan.schema.json`.
- Canonical `.artist-portrait/data/proposal_execution_readiness_plan.json`.
- `propose` writes proposal context, text-model gate, proposal request,
  adapter preflight, provider registry, mock adapter handshake, execution
  approval request, execution approval record, execution readiness plan,
  execution authorization, provider output quarantine, and provider result
  envelope packets before returning the current generation boundary.
- Status and doctor diagnostics for malformed execution readiness plan packets.

The execution readiness plan records five closed sub-stages:

- secret-source selection
- credential access
- execution planning
- provider call preflight
- output capture planning

## Closed Surfaces

Still forbidden:

- reading, creating, or sending real API keys
- selecting a real secret source
- reading environment variable, keychain, or encrypted secret values
- recording approval as granted
- opening provider execution
- serializing or sending a request packet to any model
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
  `proposal_execution_readiness_plan.json`.
- Execution readiness plan status is blocked in the current gate.
- `secret_source_selection` is blocked and not performed.
- `credential_access` is blocked and not performed.
- `execution_plan` is blocked and not performed.
- `provider_call_preflight` is blocked and not performed.
- `output_capture_plan` is blocked and not performed.
- Execution readiness plan always records `selected_secret_source: null`.
- Execution readiness plan always records `credential_value_read: false`.
- Execution readiness plan always records `network_allowed: false`.
- Execution readiness plan always records `model_call_allowed: false`.
- Execution readiness plan always records `execution_allowed: false`.
- Execution readiness plan always records `execution_performed: false`.
- Execution readiness plan always records `raw_output_capture_allowed: false`.
- Execution readiness plan always records `raw_output_captured: false`.
- Execution readiness plan always records no model call, no network access, and
  no proposal content generation.
- Malformed `proposal_execution_readiness_plan.json` is reported by `status`
  and `doctor`.
- `run_checks.py` exercises the execution readiness plan path.
