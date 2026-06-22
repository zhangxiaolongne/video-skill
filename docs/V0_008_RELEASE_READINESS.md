# V0-008 Release Readiness

Status: completed locally, ready to push, not tagged.

This file records the release checkpoint for the V0-008 basic evidence analysis
gate.

## Scope Completed

- `AnalysisRecord` Pydantic model.
- Committed `schemas/analysis_record.schema.json`.
- `artist-portrait analyze --project` command with `--json`, `--quiet`, and
  `--verbose`.
- Canonical `.artist-portrait/data/analysis.jsonl`.
- Rebuildable `output/analysis_report.md`.
- Evidence-only aggregation from source, clip, transcript, and keyframe
  ledgers.
- Null/empty placeholders for visual fields that are not opened yet.
- Status and doctor summaries for analysis manifests.
- Diagnostics for invalid analysis manifests and pending analysis.
- Invalidation from source, clip, transcript, keyframe, and analysis changes.

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

- pytest: 105 passed.
- run_checks.py: checks passed.
- schema drift: covered by `run_checks.py`.
- skill package preflight: covered by `run_checks.py`.
- canonical install simulation: covered by `run_checks.py`.
- real scan/analyze chain: covered by `run_checks.py`.
