# V0-002k Invalid Ledger Handling

Status: completed.

This slice hardens commands that consume `.artist-portrait/data/sources.jsonl`.

## Accepted Behavior

- `status --json` reports an invalid source ledger without failing.
- `scan` fails with exit code `9 output_or_reference_validation_failed` when an
  existing previous `sources.jsonl` is invalid.
- `map` fails with exit code `9 output_or_reference_validation_failed` when
  `sources.jsonl` is invalid.
- `review --scope project` fails with exit code `9 output_or_reference_validation_failed`
  when `sources.jsonl` is invalid.
- The validation error includes the invalid JSONL line number from the
  `SourceRecord` parser.

## Boundaries

The command does not repair, migrate, delete, or rewrite a damaged source
ledger. It only reports the validation failure deterministically.

## Validation

Covered by:

- `test_invalid_sources_jsonl_blocks_scan_map_and_review_but_status_reports_it`
