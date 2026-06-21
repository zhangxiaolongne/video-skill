# V0-006 Release Readiness

Status: completed locally, ready to push, not tagged.

This file records the release checkpoint for the V0-006 local transcription
gate.

## Scope Completed

- `TranscriptRecord` Pydantic model and committed JSON Schema.
- `artist-portrait transcribe --project` command with `--json`, `--quiet`, and
  `--verbose`.
- `features.transcription` routing for `off`, `auto`, and `required`.
- Optional local-only faster-whisper adapter.
- Canonical `.artist-portrait/data/transcripts.jsonl` writer and validator.
- Status and doctor summaries for transcript ledgers.
- Diagnostics for invalid transcripts, required dependency missing, and
  transcribe invalidation after source ledger changes.
- Updated master and development documents, CLI/data/state docs, README, skill
  metadata, schema, and gate consistency tests.

## Boundaries Preserved

- No OpenCV visual analysis.
- No embeddings.
- No text understanding beyond raw ASR record storage.
- No BGM selection, beat analysis, or music/timeline fitting.
- No creative proposals.
- No timeline generation.
- No preview rendering.
- No remote model calls.
- No model downloads.
- No network search.
- No image generation or image editing.

## Validation

- pytest: 92 passed, 1 skipped.
- run_checks.py: checks passed.
- schema drift: checked by `run_checks.py`.
- skill package preflight: checked by `run_checks.py`.
- canonical install simulation: checked by `run_checks.py`.
- real scan check: skipped by `run_checks.py` because ffmpeg/ffprobe were not
  found in the current local environment.
