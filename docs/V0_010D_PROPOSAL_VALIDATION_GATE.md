# V0-010d Proposal Validation Gate

V0-010d opens deterministic validation of existing proposal sets. It does not
open proposal generation.

## Scope

Allowed in this gate:

- `ProposalValidationReport` Pydantic model.
- Committed `schemas/proposal_validation_report.schema.json`.
- `review --scope proposal`.
- Canonical `.artist-portrait/data/proposal_validation.json`.
- Rebuildable `output/proposal_review.md`.
- Validation of existing `.artist-portrait/data/proposals.json` against the
  deterministic `.artist-portrait/data/proposal_context.json`.

`review --scope proposal` validates:

- proposal project ID against the proposal context project ID
- material-map fingerprint against the proposal context fingerprint
- required clip references
- forbidden-source usage through required clips
- proposal fact references against known context, source, clip, analysis,
  ledger, and material-map references
- presence of a sound structure
- presence of an explicit BGM/music strategy in the sound structure

The BGM check is intentionally only a strategy-field validation. It does not
select tracks, analyze beats, recommend music, or fit music to a timeline.

## Closed Surfaces

Still forbidden:

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

## Failure Behavior

Missing `proposal_context.json` returns `7 prerequisite_step_missing`.
Missing `proposals.json` returns `7 prerequisite_step_missing`.
Malformed proposal context or proposal set JSON returns the existing invalid
data path with a fixed error message.

Validation issues are written into `proposal_validation.json` and rendered in
`proposal_review.md`. A clean validation returns exit code `0`; validation
warnings or errors return exit code `1` because review found actionable issues.

## Acceptance

- Generated schemas include `proposal_validation_report.schema.json`.
- `review --scope proposal` writes both validation artifacts.
- Valid existing proposals produce zero issues.
- Unknown clip references produce `proposal_unknown_clip_id`.
- Missing BGM strategy produces `proposal_missing_bgm_strategy`.
- `review --scope timeline` remains closed.
- `review --scope all` remains shallow and only marks timeline review as a
  skipped future scope.
- `run_checks.py` exercises the local proposal validation path.
