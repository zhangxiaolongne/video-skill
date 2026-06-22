# Model Boundaries

Authoritative source: `artist_portrait_editor_revision5_optimized.md`.

Default remote model policy:

```text
allow_remote_text_model = false
allow_remote_vision_model = false
```

Models may organize evidence in later phases, but they must not create facts,
material IDs, timecodes, dialogue, provenance, identity, rights status, or
timeline references.

The current V0-007 keyframe cache gate performs no remote model calls. `scan`,
`segment`, `transcribe`, `keyframes`, `map`, `review`, `status`, and `doctor`
must remain local. PySceneDetect output is a local tool-derived boundary
signal, faster-whisper output is local ASR evidence, and ffmpeg keyframes are
visual samples only. None of these are creative judgments, visual analysis, BGM
strategy, or timeline decisions.
