# V0-002d Rescan Identity

Status: in progress.

This slice hardens repeated `scan` behavior for moved files and changed file
contents.

## Accepted Behavior

- `source_id` is stable for the same `project.id` and content hash.
- Moving a file without changing bytes keeps the same `source_id`.
- Moving a file updates `locations` and `primary_location` to current scanned
  project-relative paths.
- Repeated writes replace `.artist-portrait/data/sources.jsonl`; stale moved
  paths are not kept as current locations.
- Changing file bytes changes the content hash and therefore creates a new
  `source_id`.

## Current Boundary

`supersedes_source_id` is not populated yet. That requires history-aware scan
state and is intentionally deferred to a later slice.

## Validation

Covered by:

- `test_stable_source_id_depends_on_project_and_content_hash_only`
- `test_file_move_keeps_source_id_and_updates_location`
- `test_file_content_change_creates_new_source_id`
- `test_repeated_write_replaces_sources_jsonl_locations`
- `test_repeated_cli_scan_updates_moved_location`
