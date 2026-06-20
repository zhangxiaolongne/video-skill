# V0-002b Media Scan Acceptance

Status: in progress.

This slice hardens V0-002a by adding real-media validation and source JSONL
round-trip checks.

## Accepted Scope

- real generated WAV scan when `ffmpeg` and `ffprobe` are available
- `ffprobe` payload parsing unit tests
- `sources.jsonl` read-back validation through `SourceRecord`
- invalid `sources.jsonl` failure coverage
- local `run_checks.py` real scan check when media dependencies exist
- CI installs `ffmpeg` and runs the same local check entrypoint

## Still Out Of Scope

- scene detection
- segmentation
- transcription
- OpenCV or vision analysis
- material map generation
- creative proposals
- timeline generation
- preview rendering

## Acceptance Command

```bash
.venv/bin/python run_checks.py
```

CI must pass the same check on Python 3.11 and 3.12.
