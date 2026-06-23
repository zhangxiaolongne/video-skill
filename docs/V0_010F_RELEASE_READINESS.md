# V0-010f Release Readiness

Status: completed locally, ready to push, not tagged.

This checkpoint closes deterministic proposal adapter preflight. It validates
provider/secret/model-call boundaries without using keys, contacting a model,
or generating proposals.

## Included

- `ProposalAdapterCheck` Pydantic model.
- Committed `schemas/proposal_adapter_check.schema.json`.
- Canonical `.artist-portrait/data/proposal_adapter_check.json`.
- `propose` output refs now include proposal context, text-model gate,
  proposal request, and proposal adapter preflight packets.
- Adapter preflight records `model_call_performed: false` and
  `network_performed: false`.
- Plaintext secret material detection in checked project artifacts.
- Status and doctor diagnostics for malformed adapter preflight packets.
- Contract and integration tests for schema, blocked preflight, ready
  preflight, invalid preflight, and plaintext secret detection.
- `run_checks.py` coverage for the local adapter preflight path.

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

- `pytest: 125 passed`
- `run_checks.py: checks passed`
