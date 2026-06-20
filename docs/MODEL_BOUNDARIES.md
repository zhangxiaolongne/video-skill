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

Stage A performs no model calls.
