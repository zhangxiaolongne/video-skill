# V0-009 Material Map Gate

V0-009 upgrades `map` from a source-only inventory to an analysis-led material
map. It renders `output/material_map.md` from local source and analysis ledgers
without creating creative proposals, timelines, previews, BGM decisions, visual
classification, network results, image outputs, or model-backed judgments.

## Scope

- `artist-portrait map --project <project.yaml>` requires current
  `.artist-portrait/data/analysis.jsonl`.
- The report reads `.artist-portrait/data/sources.jsonl` and
  `.artist-portrait/data/analysis.jsonl`.
- `output/material_map.md` is rebuildable and non-canonical.
- Material map output includes:
  - material and media distributions
  - original audio usability distribution
  - deterministic priority review queue
  - pending confirmation fields
  - risk items by clip
- Changed analysis invalidates completed map output.

## Boundary

Priority review order is not a creative recommendation. It is a deterministic
human-review ordering based on evidence coverage, risk flags, and duration.

Still forbidden:

- OpenCV or visual classification
- embeddings
- vision models
- BGM selection, beat analysis, or music/timeline fitting
- creative proposals
- timeline generation
- preview rendering
- model calls
- network search
- image generation or image editing

