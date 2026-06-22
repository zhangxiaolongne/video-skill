# V0-007 Release Readiness

Status: completed locally, ready to push, not tagged.

This file records the release checkpoint for the V0-007 keyframe cache gate.

## Scope Completed

- `KeyframeRecord` Pydantic model and committed JSON Schema.
- `artist-portrait keyframes --project` command with `--json`, `--quiet`, and
  `--verbose`.
- Deterministic midpoint keyframe extraction for video clips via ffmpeg.
- Canonical `.artist-portrait/data/keyframes.jsonl`.
- rebuildable `.artist-portrait/cache/keyframes/` images.
- Audio-only handling with empty manifest and warning.
- Status and doctor summaries for keyframe manifests and cache images.
- Diagnostics for invalid keyframe manifests, missing cache images, and
  keyframes invalidated after source or clip ledger changes.
- Updated master and development documents, CLI/data/state docs, README, skill
  metadata, schema, and gate consistency tests.

## Boundaries Preserved

- No OpenCV visual analysis.
- No embeddings.
- No vision models.
- No BGM selection, beat analysis, or music/timeline fitting.
- No creative proposals.
- No timeline generation.
- No preview rendering.
- No remote model calls.
- No network search.
- No image generation or image editing.

## Validation

- pytest: 100 passed.
- run_checks.py: checks passed.
- schema drift: checked by `run_checks.py`.
- skill package preflight: checked by `run_checks.py`.
- canonical install simulation: checked by `run_checks.py`.
- real scan/keyframe chain: checked by `run_checks.py`.
