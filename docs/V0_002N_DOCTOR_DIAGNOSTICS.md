# V0-002n Doctor Diagnostics

Status: completed.

This slice adds a read-only `doctor` command for local workspace diagnostics.
It turns existing status and review issue data into concrete next-action
guidance without mutating project files.

## Accepted Behavior

- `doctor --project ./project.yaml` renders a human-readable diagnostic panel.
- `doctor --json` returns a structured payload with:
  - `initialized`
  - `issue_count`
  - `issues`
  - `recommended_commands`
  - artifact and summary snapshots
- Missing workspace state is reported as `workspace_not_initialized`.
- Invalid `.artist-portrait/data/sources.jsonl` is reported as
  `source_ledger_invalid`.
- Missing completed-step outputs reuse `missing_output_ref`.
- Pending local foundation follow-ups can be reported as `map_pending` or
  `review_project_pending`.
- The command returns `1 success_with_warnings` when issues exist and
  `0 success` when no issues exist.

## Boundaries

`doctor` does not repair files, rescan media, call ffprobe, analyze media,
transcribe audio, create proposals, generate timelines, render previews, call
models, or search the network. It only reads local config, state, source ledger,
and output artifact presence.

## Validation

Covered by:

- `test_doctor_before_init_recommends_init`
- `test_doctor_after_init_reports_no_issues`
- `test_status_and_review_report_missing_output_ref`
- `test_invalid_sources_jsonl_blocks_scan_map_and_review_but_status_reports_it`
- `run_checks.py`
