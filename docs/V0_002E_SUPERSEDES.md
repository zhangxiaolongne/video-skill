# V0-002e Supersedes Tracking

Status: completed.

This slice adds minimal history-aware replacement tracking for repeated `scan`
runs.

## Accepted Behavior

- `scan` reads the previous `.artist-portrait/data/sources.jsonl` before
  writing the new one.
- If a newly scanned source has the same project-relative location as a
  previous source but a different content hash and `source_id`, the new record
  sets `supersedes_source_id` to the previous record's `source_id`.
- The current `sources.jsonl` remains a current-state ledger. It is overwritten
  with current records and does not retain stale paths as active locations.
- Moving a file and changing its bytes in the same rescan does not infer a
  replacement relationship, because the location continuity evidence is gone.
- Invalid prior `sources.jsonl` data fails validation instead of being silently
  ignored.

## Non Goals

- No media scanning beyond existing extension discovery and ffprobe metadata.
- No content similarity matching.
- No user confirmation workflow.
- No append-only source history table.
- No migration of older malformed source ledgers.

## Validation

Covered by:

- `test_file_content_change_at_same_location_sets_supersedes_source_id`
- `test_file_move_and_content_change_does_not_infer_supersedes_source_id`
- `test_repeated_cli_scan_records_superseded_source_for_same_location_change`
