# V0-009 Release Readiness

Status: completed locally, ready to push, not tagged.

This file records the release checkpoint for the V0-009 analysis-led material
map gate.

## Scope Completed

- `map` now requires current `.artist-portrait/data/analysis.jsonl`.
- `output/material_map.md` is rendered from source and analysis ledgers.
- Material map includes distributions, priority review queue, pending
  confirmation fields, and risk sections.
- Tests cover missing analysis prerequisite and analysis-led map rendering.
- `run_checks.py` covers the V0-009 map chain.

## Boundaries Preserved

- No OpenCV visual classification.
- No embeddings.
- No vision models.
- No BGM selection, beat analysis, or music/timeline fitting.
- No creative proposals.
- No timeline generation.
- No preview rendering.
- No model calls.
- No network search.
- No image generation or image editing.

## Validation

- pytest: 107 passed.
- run_checks.py: checks passed.
- gate consistency: covered by `run_checks.py`.
- skill package preflight: covered by `run_checks.py`.
- canonical install simulation: covered by `run_checks.py`.
- real scan/material-map chain: covered by `run_checks.py`.
