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

The current V0-010f proposal adapter preflight gate performs no remote model calls.
`scan`, `segment`, `transcribe`, `keyframes`, `analyze`, `map`, `propose`,
`review`, `status`, and `doctor` must remain local. PySceneDetect output is a local
tool-derived boundary signal, faster-whisper output is local ASR evidence,
ffmpeg keyframes are visual samples only, and `analysis.jsonl` only aggregates
existing evidence. `material_map.md` is a deterministic report, and `propose`
currently writes deterministic proposal context, writes deterministic
text-model gate state, writes deterministic proposal request packets, writes
deterministic proposal adapter preflight packets, and
records readiness or blocked state only. `review
--scope proposal` reads existing proposal artifacts and validates their
references; it does not generate or improve proposals. None of these are creative
judgments, OpenCV/vision-model visual classification, BGM strategy, or timeline
decisions. Without an explicitly opened proposal generation gate, `propose`
must not call a text model or generate fake/template proposals.
