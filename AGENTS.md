# AGENTS.md

Follow `artist_portrait_editor_revision5_optimized.md` as the governing V0
engineering-freeze document.

Current gate: V0-009 analysis-led material map gate only.

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
- `keyframes`
- deterministic ffmpeg midpoint keyframe extraction for video clips
- canonical `keyframes.jsonl`
- rebuildable `.artist-portrait/cache/keyframes/`
- keyframe status, doctor diagnostics, and source/clip invalidation
- `analyze`
- deterministic `.artist-portrait/data/analysis.jsonl`
- deterministic `output/analysis_report.md`
- level_0/1/2 evidence-only analysis fields with null visual assertions
- analysis status, doctor diagnostics, and upstream invalidation
- `map`
- `map` requires current `analysis.jsonl`
- deterministic `output/material_map.md` rendered from source and analysis ledgers
- priority review queue, pending confirmation, and risk sections without creative recommendations
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
- visual classification beyond explicit evidence placeholders
- creative proposals
- timeline generation
- preview rendering
- BGM selection, beat analysis, music recommendation, or music/timeline fitting
- network search
- image generation or image editing
- model calls
