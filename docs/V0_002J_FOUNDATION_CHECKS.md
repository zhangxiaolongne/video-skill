# V0-002j Foundation Checks

Status: completed.

This slice expands `run_checks.py` so the repository-level verification covers
the current local foundation surface, not only Stage A initialization.

## Accepted Behavior

- `run_checks.py` still runs pytest unless `--skip-pytest` is provided.
- Schema drift remains checked.
- `scan` before `init` remains checked.
- A no-ffprobe fixture now validates `init`, handcrafted `sources.jsonl`,
  `map`, `review --scope project`, `status --json`, and run report refresh.
- The real ffmpeg/ffprobe scan check remains optional and is skipped when those
  tools are unavailable.

## Boundaries

The new fixture does not decode media, invoke ffprobe, search the network, call
models, generate creative proposals, produce timelines, or render previews.

## Validation

Covered by:

- `run_checks.py`
