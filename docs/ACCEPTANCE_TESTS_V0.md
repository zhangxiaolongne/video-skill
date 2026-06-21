# Acceptance Tests V0

Authoritative source: `artist_portrait_editor_revision5_optimized.md`.

Current local foundation tests cover:

- valid and invalid `project.yaml`
- fixed exit code mapping
- Pydantic schema generation
- committed schema drift
- `validate`
- `init`
- `init --dry-run`
- `status` before and after initialization
- repeated `init`
- prevention of business artifact creation during Stage A
- supported media scan and `sources.jsonl`
- `sources.csv` import
- rescan identity and supersedes tracking
- minimal `map`
- minimal `review --scope project`
- enhanced `status --json`
- `run_report.md` refresh after state-mutating commands

Future segmentation, transcription, analysis, proposal, timeline, preview,
model, and network fixtures are intentionally not implemented yet.
