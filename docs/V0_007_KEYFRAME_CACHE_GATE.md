# V0-007 Keyframe Cache Gate

V0-007 opens deterministic keyframe extraction for video clips. It creates a
canonical keyframe manifest and a rebuildable cache of frame images without
performing OpenCV analysis, vision-model analysis, creative selection, preview
rendering, or timeline generation.

## Scope

- `artist-portrait keyframes --project <project.yaml>` reads
  `.artist-portrait/data/clips.jsonl`.
- Each video clip gets one deterministic midpoint frame.
- Keyframe images are written under `.artist-portrait/cache/keyframes/`.
- `.artist-portrait/data/keyframes.jsonl` is the canonical manifest.
- Audio clips do not require keyframes.
- Missing cache files are rebuild warnings, not canonical data corruption.
- Changed source or clip ledgers invalidate completed keyframes.

## Boundaries

Keyframes are visual samples only. They do not classify shot size, camera
motion, emotion, quality, identity, role, action, BGM fit, or timeline value.

Still closed:

- OpenCV or visual analysis
- embeddings
- vision models
- BGM selection, beat analysis, or music/timeline fitting
- creative proposals
- timeline generation
- preview rendering
- remote model calls
- network search
- image generation or image editing

## Data Contract

`KeyframeRecord` stores:

- keyframe identity
- clip and source identity
- source content hash and clip fingerprint
- frame index and source timestamp
- cache image path
- method, method version, evidence, and risk flags

The image file is rebuildable cache. The JSONL manifest is canonical.

## Validation Expectations

- Tests must not require real ffmpeg frame extraction.
- ffmpeg availability and frame extraction are simulated in unit/integration
  paths.
- Video clips without ffmpeg fail with exit code `4`.
- Audio-only clips write an empty manifest with a warning.
- Invalid manifests and missing cache images are visible in `status`/`doctor`.
