# Data Contracts

Authoritative source: `artist_portrait_editor_revision5_optimized.md`.

Pydantic models are the schema truth source. JSON Schema must be generated from
Pydantic, not manually maintained as an independent contract.

Current committed schemas:

- `schemas/project_config.schema.json`
- `schemas/project_state.schema.json`

Current contract tests assert that committed schemas match live Pydantic schema
generation.

Canonical media contracts such as `sources.jsonl`, `clips.jsonl`,
`transcripts.jsonl`, `relations.jsonl`, and `proposals.json` are specified in
the master document but intentionally not implemented in Stage A.
