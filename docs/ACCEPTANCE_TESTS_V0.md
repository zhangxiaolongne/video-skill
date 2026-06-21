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
- invalid `sources.jsonl` handling for `scan`, `status`, `map`, and `review`
- atomic writes for rebuildable report outputs
- ledger output reference consistency in `status` and `review`
- minimal `review --scope all` that runs project review and marks proposal and
  timeline review as skipped
- read-only `doctor` diagnostics for uninitialized workspaces, missing output
  refs, invalid source ledgers, and recommended next commands
- root `SKILL.md` and `agents/openai.yaml` metadata validation
- skill package preflight with hard errors separated from known install-name
  warnings
- skill package policy declaring `artist-portrait-editor` as canonical install
  directory and `video-skill` as an allowed distribution repository
- canonical install simulation with zero package preflight warnings

Future segmentation, transcription, analysis, proposal, timeline, preview,
model, and network fixtures are intentionally not implemented yet.
