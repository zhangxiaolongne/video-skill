# V0-010j Proposal Provider Output Quarantine Gate

V0-010j opens deterministic provider output quarantine packets. It does not
open model execution, raw provider output capture, payload parsing, promotion
to `proposals.json`, generated proposal validation, BGM fitting, timeline
generation, or preview rendering.

## Scope

Allowed in this gate:

- `ProposalProviderOutputQuarantine` Pydantic model.
- Committed `schemas/proposal_provider_output_quarantine.schema.json`.
- Canonical `.artist-portrait/data/proposal_provider_output_quarantine.json`.
- `propose` writes proposal context, text-model gate, proposal request,
  adapter preflight, provider registry, mock adapter handshake, execution
  authorization, provider output quarantine, and provider result envelope
  packets before returning the current generation boundary.
- Status and doctor diagnostics for malformed provider output quarantine
  packets.

The provider output quarantine packet records:

- provider id
- request ref
- registry ref
- handshake ref
- execution authorization ref
- adapter check ref
- quarantine fingerprint
- raw output capture fields
- parsed payload fields
- proposal promotion flag
- validation performed flag
- model/network/proposal content performed flags
- quarantine requirement
- issue list

## Closed Surfaces

Still forbidden:

- reading, creating, or sending real API keys
- selecting a real secret source
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
  `proposal_provider_output_quarantine.json`.
- Provider output quarantine status is blocked in the current gate.
- Provider output quarantine always records `raw_output_captured: false`.
- Provider output quarantine always records `raw_output_ref: null`.
- Provider output quarantine always records `raw_output_sha256: null`.
- Provider output quarantine always records `raw_output_bytes: 0`.
- Provider output quarantine always records `parsed_payload_generated: false`.
- Provider output quarantine always records `parsed_payload_ref: null`.
- Provider output quarantine always records `promoted_to_proposals: false`.
- Provider output quarantine always records `validation_performed: false`.
- Provider output quarantine always records no model call, no network access,
  and no proposal content generation.
- Provider output quarantine records quarantine required for future provider
  output.
- Malformed `proposal_provider_output_quarantine.json` is reported by `status`
  and `doctor`.
- `run_checks.py` exercises the provider output quarantine path.
