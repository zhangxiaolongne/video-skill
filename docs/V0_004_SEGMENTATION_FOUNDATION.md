# V0-004 Segmentation Foundation

Status: completed locally.

V0-004 opens deterministic fixed-window segmentation only. It creates a clip
ledger from the current source ledger without scene detection, transcription,
visual analysis, BGM selection, timeline generation, preview rendering, network
calls, image generation/editing, or model calls.

## Allowed Scope

- `segment --project <project.yaml>`
- fixed-window segmentation for video and audio sources
- canonical `.artist-portrait/data/clips.jsonl`
- rebuildable `output/clip_report.md`
- clip summaries in `status --json`
- `clips_invalid` and `segment_invalidated` diagnostics in `doctor --json`
- downstream invalidation when `sources.jsonl` or `clips.jsonl` changes

## Closed Scope

These remain forbidden until a later gate explicitly opens them:

- PySceneDetect scene detection
- Whisper or other transcription
- OpenCV or visual analysis
- embeddings
- vision models
- creative proposals
- timeline generation
- preview rendering
- BGM selection, beat analysis, music recommendation, or music/timeline fitting
- model calls
- network search
- image generation or image editing

## Clip Ledger Contract

`artist-portrait segment --project <project.yaml>` writes:

- `.artist-portrait/data/clips.jsonl`
- `output/clip_report.md`
- segment step run metadata under `.artist-portrait/runs/<run_id>/`
- refreshed `output/run_report.md`

Each clip records its source, source fingerprint, boundary, method,
method_version, boundary confidence, inherited source risk flags, and clip risk
flags.

## Boundary Policy

The current method is `fixed_window` with method version `fixed-window-v1`.
Default window size is 10 seconds. Tail clips shorter than the window are
allowed and marked with `short_tail`.

## Validation

Required checks:

```bash
.venv/bin/python -m pytest
.venv/bin/python run_checks.py
.venv/bin/python scripts/skill_package_preflight.py . --json
.venv/bin/python scripts/simulate_skill_install.py . --json
git diff --check
```
