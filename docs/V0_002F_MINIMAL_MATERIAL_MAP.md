# V0-002f Minimal Material Map

Status: completed.

This slice unlocks a narrow `map` command that renders a deterministic source
inventory from the existing scan ledger.

## Accepted Behavior

- `map` requires `init` and a prior `scan`.
- `map` reads `.artist-portrait/data/sources.jsonl`.
- `map` writes `output/material_map.md`.
- The map step ledger records `output/material_map.md` and a fingerprint of the
  source ledger.
- Empty source ledgers render a warning map instead of failing.

## Current Material Map Contents

- source ledger reference
- source count
- total duration
- media kind distribution
- source type distribution
- rights status distribution
- per-source location, media probe, source type, rights status, provenance,
  supersedes relation, risk flags, and notes

## Boundaries

This is not the full V0-007 material map. It does not rank clips, summarize
visual content, transcribe speech, recommend priority moments, infer emotions,
generate proposals, produce timelines, render previews, search the network, or
call text or vision models.

## Validation

Covered by:

- `test_map_requires_scan_first`
- `test_map_writes_material_map_from_sources`
