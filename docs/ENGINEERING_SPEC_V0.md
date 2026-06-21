# Engineering Spec V0

Authoritative source: `artist_portrait_editor_revision5_optimized.md`.

Stage A historical implementation scope:

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

Required Stage A properties:

- `validate` can run before initialization and does not write project files.
- `init` validates config before creating a workspace.
- `init` does not read or analyze media.
- `init` does not create business artifacts such as `sources.jsonl`,
  `clips.jsonl`, `material_map.md`, `proposals.md`, or `timeline_draft.json`.
- missing FFmpeg/ffprobe is a warning for `init`, not a fatal error.
- state and run records are auditable.
- repeated `init` does not cross the Stage A boundary.

Current V0-004 implementation scope additionally allows:

- `scan`
- deterministic `sources.jsonl`
- deterministic `scan_report.md`
- fixed-window `segment`
- deterministic `clips.jsonl`
- deterministic `clip_report.md`
- minimal `map`
- minimal `review --scope project`
- read-only `doctor`
- source and clip invalidation diagnostics
