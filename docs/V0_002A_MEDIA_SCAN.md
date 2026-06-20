# V0-002a Media Scan

Status: in progress.

This slice starts V0-002 without entering segmentation, transcription,
analysis, relations, material maps, proposals, timelines, or rendering.

## Accepted Scope

- `SourceRecord` data contract
- `MediaProbe` data contract
- generated `source_record.schema.json`
- supported media extension discovery
- SHA-256 content hashing
- duplicate file grouping by content hash
- `ffprobe` metadata parsing
- `scan` command dependency checks
- `scan` command initialization prerequisite
- atomic `sources.jsonl` write
- scan step ledger update

## Supported Extensions

```text
MP4
MOV
MKV
M4V
MP3
WAV
```

## Current Boundaries

- No scene detection.
- No fixed-window segmentation.
- No transcription.
- No OpenCV analysis.
- No material map.
- No creative model calls.
- No timeline generation.
- No preview rendering.

## Exit Code Expectations

- Missing `init`: `7 prerequisite_step_missing`
- Missing `ffmpeg` or `ffprobe`: `4 missing_required_dependency_for_command`
- All media probe failures: `5 media_operation_failed`
- Empty media directory: `1 success_with_warnings`
- Valid scan with records: `0 success`
