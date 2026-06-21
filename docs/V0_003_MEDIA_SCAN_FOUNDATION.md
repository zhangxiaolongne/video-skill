# V0-003 Media Scan Foundation

Status: in progress locally.

V0-003 reconciles the project gate after the Stage A foundation and V0-002
source-ledger work. The active gate is now deterministic media scan foundation,
not Stage A-only.

## Allowed Scope

- `validate`, `init`, `status`, and `doctor`
- `scan` with local `ffmpeg` / `ffprobe` dependency checks
- content hashing and source identity
- duplicate-content location grouping
- moved-file identity stability
- same-location content replacement with `supersedes_source_id`
- canonical `.artist-portrait/data/sources.jsonl`
- deterministic `output/scan_report.md`
- minimal deterministic `map`
- minimal deterministic `review --scope project`
- `review --scope all` only as project review plus skipped future scopes
- downstream `map` and `review_project` invalidation after source ledger changes

## Closed Scope

These remain forbidden until a later gate explicitly opens them:

- PySceneDetect segmentation
- Whisper or other transcription
- OpenCV or visual analysis
- embeddings
- vision models
- creative proposals
- timeline generation
- preview rendering
- BGM selection, beat analysis, music recommendation, or music/timeline fitting
- model calls
- network search
- image generation or image editing

## Scan Report Contract

`artist-portrait scan --project <project.yaml>` writes:

- `.artist-portrait/data/sources.jsonl`
- `output/scan_report.md`
- scan step run metadata under `.artist-portrait/runs/<run_id>/`
- refreshed `output/run_report.md`

The scan report is a rebuildable local report. It must state that it was
rendered only from local filesystem data, content hashes, `sources.csv`
metadata, and ffprobe-derived media facts.

## Rescan And Invalidation Contract

When a rescan changes `.artist-portrait/data/sources.jsonl`, completed `map`
and `review_project` steps whose input fingerprints no longer match the source
ledger are marked `invalidated`.

`status`, `doctor`, run metadata, and `scan_report.md` must expose that
invalidated state so old reports are not silently trusted.

## Dependency Contract

`init`, `status`, and `doctor` may run without `ffmpeg` / `ffprobe`.

`scan` requires both dependencies. Missing dependencies return
`4 missing_required_dependency_for_command` and do not generate fake media data.

## Validation

Required checks:

```bash
.venv/bin/python -m pytest
.venv/bin/python run_checks.py
.venv/bin/python scripts/skill_package_preflight.py . --json
.venv/bin/python scripts/simulate_skill_install.py . --json
git diff --check
```
