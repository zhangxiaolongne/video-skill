# V0-010i Proposal Execution Authorization Gate

V0-010i opens deterministic provider execution authorization packets. It does
not open model execution, API key use, network access, provider payload
generation, proposal validation from provider output, BGM fitting, timeline
generation, or preview rendering.

## Scope

Allowed in this gate:

- `ProposalExecutionAuthorization` Pydantic model.
- Committed `schemas/proposal_execution_authorization.schema.json`.
- Canonical `.artist-portrait/data/proposal_execution_authorization.json`.
- `propose` writes proposal context, text-model gate, proposal request,
  adapter preflight, provider registry, mock adapter handshake, execution
  authorization, and provider result envelope packets before returning the
  current generation boundary.
- Status and doctor diagnostics for malformed execution authorization packets.

The execution authorization packet records:

- provider id
- request ref
- registry ref
- handshake ref
- adapter check ref
- approved execution gate
- user approval requirement and presence
- credential policy
- allowed and selected secret sources
- network and model-call permissions
- execution/model/network performed flags
- quarantine requirement for any future provider output
- issue list

## Closed Surfaces

Still forbidden:

- reading, creating, or sending real API keys
- selecting a real secret source
- recording user approval as present
- opening provider execution
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

- `propose --json` output refs include `proposal_execution_authorization.json`.
- Execution authorization status is blocked in the current gate.
- Execution authorization always records `approved_execution_gate: false`.
- Execution authorization always records `user_approval_present: false`.
- Execution authorization always records no selected secret source.
- Execution authorization always records no model-call or network permission.
- Execution authorization always records no execution, no model call, no
  network access, and no proposal content generation.
- Execution authorization records quarantine required for future provider
  output.
- Malformed `proposal_execution_authorization.json` is reported by `status` and
  `doctor`.
- `run_checks.py` exercises the execution authorization path.
