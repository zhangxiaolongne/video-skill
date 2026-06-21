# V0-005 Scene Segmentation Gate

V0-005 opens optional PySceneDetect scene segmentation for video sources while
keeping fixed-window segmentation as the deterministic baseline. It does not
open transcription, visual analysis, BGM selection, creative proposals,
timeline generation, preview rendering, model calls, image generation/editing,
or network search.

## Scope

- `features.scene_detection: off` uses `fixed_window`.
- `features.scene_detection: auto` uses PySceneDetect when available and falls
  back to `fixed_window` with a warning when PySceneDetect is missing or fails.
- `features.scene_detection: required` fails `segment` with exit code `4` when
  PySceneDetect is missing or fails.
- Video sources may produce `ClipMethod.pyscenedetect`.
- Audio sources always remain `fixed_window`.
- `status`, `doctor`, run metadata, `clips.jsonl`, and `clip_report.md` expose
  the selected method, fallback warnings, or required dependency issue.

## Boundaries

PySceneDetect is treated as a local boundary tool. Its output is evidence for
clip boundaries, not visual understanding, narrative structure, BGM strategy, or
timeline intent.

Still closed:

- Whisper or transcription
- OpenCV or visual analysis
- embeddings
- BGM selection, beat analysis, or music/timeline fitting
- creative proposals
- timeline generation
- preview rendering
- model calls
- network search
- image generation or image editing

## Data Contract

`ClipRecord.method` may be:

- `fixed_window`
- `pyscenedetect`

Fallback clips remain `fixed_window` and include
`scene_detection_fallback` in `risk_flags`.

## Validation Expectations

- Tests must not require PySceneDetect to be installed.
- PySceneDetect availability and failure are simulated in tests.
- `scene_detection: required` must fail before writing fake `clips.jsonl`.
- `run_checks.py` keeps deterministic local checks by setting
  `scene_detection: off` in its synthetic fixtures.
