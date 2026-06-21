# Data Contracts

Authoritative source: `artist_portrait_editor_revision5_optimized.md`.

Pydantic models are the schema truth source. JSON Schema must be generated from
Pydantic, not manually maintained as an independent contract.

Current committed schemas:

- `schemas/project_config.schema.json`
- `schemas/project_state.schema.json`
- `schemas/source_record.schema.json`

Current contract tests assert that committed schemas match live Pydantic schema
generation.

`SourceRecord` is implemented for the media scan foundation and is written as
JSON Lines to `.artist-portrait/data/sources.jsonl` by `scan`.

`output/scan_report.md` is a rebuildable report rendered from the current
source ledger, local content hashes, `sources.csv` metadata, and ffprobe-derived
media facts. It is not canonical data; `sources.jsonl` remains the canonical
source ledger.

Diagnostic issues are plain JSON objects used by `status`, `review`, and
`doctor`. Current common fields:

- `scope`: issue domain, such as `source`, `artifact`, `workspace`, or
  `review_scope`
- `code`: stable machine-readable issue code
- `severity`: `info`, `warning`, or `error`
- `detail`: human-readable explanation
- `next_action`: optional command or remediation hint

Scope-specific fields are allowed when needed, including `source_id`,
`location`, `step`, `ref`, and `review_scope`.

Current stable diagnostic codes include:

- `missing_output_ref`
- `source_ledger_invalid`
- `map_pending`
- `review_project_pending`
- `map_invalidated`
- `review_project_invalidated`
- `review_scope_skipped`

Canonical contracts such as `clips.jsonl`, `transcripts.jsonl`,
`relations.jsonl`, and `proposals.json` are specified in the master document
but intentionally not implemented yet.
