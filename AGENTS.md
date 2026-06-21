# AGENTS.md

Follow `artist_portrait_editor_revision5_optimized.md` as the governing V0
engineering-freeze document.

Current gate: V0-006 local transcription gate only.

Allowed:

- `validate`
- `init`
- `status`
- `doctor`
- `scan`
- deterministic `ffmpeg` / `ffprobe` media probing
- media content hashing
- canonical `sources.jsonl`
- deterministic `scan_report.md`
- source identity, moved-file, duplicate-file, and supersedes tracking
- downstream artifact invalidation when `sources.jsonl` changes
- deterministic fixed-window `segment`
- optional PySceneDetect scene segmentation for video only when
  `features.scene_detection` is `auto` or `required`
- fixed-window fallback when `features.scene_detection: auto` and PySceneDetect
  is missing or fails
- canonical `clips.jsonl`
- deterministic `clip_report.md`
- downstream artifact invalidation when `clips.jsonl` changes
- `transcribe`
- `features.transcription` gate handling for `off`, `auto`, and `required`
- optional local-only faster-whisper transcription when available
- canonical `transcripts.jsonl`
- transcript status, doctor diagnostics, and source-ledger invalidation
- `map`
- `review --scope project`
- `review --scope all` only as project review plus skipped future scopes
- repository skeleton
- Pydantic models
- generated JSON Schema
- CLI framework
- state ledger
- capability detection
- fixed exit codes
- Stage A and media-scan fixtures

Forbidden before the next gate explicitly opens:

- remote ASR, model-downloading transcription, or ungrounded text classification
- OpenCV analysis
- embeddings
- vision models
- creative proposals
- timeline generation
- preview rendering
- BGM selection, beat analysis, music recommendation, or music/timeline fitting
- network search
- image generation or image editing
- model calls
