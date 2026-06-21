# CLI Spec

Authoritative source: `artist_portrait_editor_revision5_optimized.md`.

Implemented V0-004 fixed-window segmentation foundation commands:

```bash
artist-portrait validate --project ./project.yaml
artist-portrait init --project ./project.yaml
artist-portrait status --project ./project.yaml
artist-portrait doctor --project ./project.yaml
artist-portrait generate-schema --output-dir schemas
artist-portrait scan --project ./project.yaml
artist-portrait segment --project ./project.yaml
artist-portrait map --project ./project.yaml
artist-portrait review --project ./project.yaml --scope project
artist-portrait review --project ./project.yaml --scope all
```

Common current-gate flags:

```text
--project PATH
--json
--verbose
--quiet
--dry-run   # init only
```

`review --scope all` runs the implemented project review, then records proposal
and timeline review as skipped warnings. `review --scope proposal` and
`review --scope timeline` still return `7 prerequisite_step_missing`.

Commands outside the current gate currently return `7 prerequisite_step_missing`.

`scan --json` writes `.artist-portrait/data/sources.jsonl`,
`output/scan_report.md`, run metadata, and a refreshed `output/run_report.md`.
It reports `output_refs` and `invalidated_steps`.

`segment --json` writes `.artist-portrait/data/clips.jsonl`,
`output/clip_report.md`, run metadata, and a refreshed `output/run_report.md`.
It uses fixed-window segmentation only and reports `output_refs` and
`invalidated_steps`.

`status --json` includes the state ledger plus local artifact, source, clip,
scan report, and clip report summaries. It also reports `artifact_issues` when
completed ledger steps refer to outputs that no longer exist. It does not run
media operations or mutate project files.

`doctor --json` is a read-only diagnostic command. It reports local workspace,
source ledger, and artifact consistency issues with `next_action` guidance and
`recommended_commands`. It reports `segment_invalidated`, `map_invalidated`,
and `review_project_invalidated` after newer upstream ledgers change. It reports
`clips_invalid` when `.artist-portrait/data/clips.jsonl` cannot be parsed. It
returns `1 success_with_warnings` when diagnostics find issues and `0 success`
when no issues are found.
