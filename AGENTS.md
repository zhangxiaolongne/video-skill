# AGENTS.md

Follow `artist_portrait_editor_revision5_optimized.md` as the governing V0
engineering-freeze document.

Current gate: V0-003 media scan foundation only.

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

- PySceneDetect
- Whisper
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
