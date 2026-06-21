# V0-005 Release Readiness

Status: completed locally, ready to push, not tagged.

This file records the release checkpoint for the V0-005 PySceneDetect scene
segmentation gate.

## Scope Completed

- `features.scene_detection` routing for `off`, `auto`, and `required`.
- Optional PySceneDetect adapter without making PySceneDetect a hard package
  dependency.
- `pyscenedetect` clip method support in `ClipRecord`.
- Fixed-window fallback warnings for `auto` when PySceneDetect is missing or
  fails.
- Required dependency failure for `required` when PySceneDetect is missing or
  fails.
- Status, doctor, run metadata, and clip report visibility for scene
  segmentation behavior.
- Updated master and development documents, CLI/data/state docs, README, skill
  metadata, schema, and gate consistency tests.

## Boundaries Preserved

- No Whisper or transcription.
- No OpenCV visual analysis.
- No embeddings.
- No creative proposals.
- No timeline generation.
- No preview rendering.
- No BGM selection, beat analysis, or music/timeline fitting.
- No model calls.
- No network search.
- No image generation or image editing.

## Validation

- pytest: 84 passed, 1 skipped.
- run_checks.py: checks passed.
- schema drift: checked by `run_checks.py`.
- skill package preflight: checked by `run_checks.py`.
- canonical install simulation: checked by `run_checks.py`.
- real scan check: skipped by `run_checks.py` because ffmpeg/ffprobe were not
  found in the current local environment.
