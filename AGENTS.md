# AGENTS.md

Follow `artist_portrait_editor_revision5_optimized.md` as the governing V0
engineering-freeze document.

Current gate: Stage A only.

Allowed:

- repository skeleton
- Pydantic models
- generated JSON Schema
- CLI framework
- state ledger
- capability detection
- fixed exit codes
- Stage A fixtures
- `validate`
- `init`
- `status`

Forbidden before Stage A passes:

- media scanning
- ffprobe scan workflow
- media hashing
- PySceneDetect
- Whisper
- OpenCV analysis
- embeddings
- vision models
- creative proposals
- timeline generation
- preview rendering
