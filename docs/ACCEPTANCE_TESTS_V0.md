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
- release readiness documentation for the unpushed local batch
- V0-003 gate consistency from Stage A acceptance into media scan foundation
- deterministic `scan_report.md`
- status and doctor visibility for scan reports
- downstream `map` and `review_project` invalidation after source ledger changes
- committed clip record schema
- deterministic fixed-window `segment`
- optional PySceneDetect scene segmentation routing for `off`, `auto`, and
  `required`
- fixed-window fallback when `scene_detection: auto` lacks or fails
  PySceneDetect
- dependency exit code when `scene_detection: required` lacks or fails
  PySceneDetect
- canonical `clips.jsonl`
- rebuildable `clip_report.md`
- status and doctor visibility for clip ledgers and clip reports
- downstream invalidation after source or clip ledger changes
- committed transcript record schema
- `transcribe` routing for `transcription: off`, `auto`, and `required`
- local-only faster-whisper adapter behavior without requiring faster-whisper in
  tests
- canonical `transcripts.jsonl`
- status and doctor visibility for transcript ledgers
- downstream invalidation after source ledger changes
- committed keyframe record schema
- `keyframes` command requiring existing clip ledger
- ffmpeg dependency failure for video clips
- canonical `keyframes.jsonl`
- rebuildable `.artist-portrait/cache/keyframes/`
- audio-only empty manifest handling
- status and doctor visibility for keyframe manifests and missing cache files
- downstream invalidation after source or clip ledger changes

Future analysis, proposal, timeline, preview, remote model, BGM, image
generation/editing, and network fixtures are intentionally not implemented yet.
