# V0-002i Run Report Refresh

Status: completed.

This slice keeps `output/run_report.md` aligned with the local step ledger after
foundation commands mutate project state.

## Accepted Behavior

- `init` writes `output/run_report.md`.
- `scan` refreshes `output/run_report.md`.
- `map` refreshes `output/run_report.md`.
- `review --scope project` refreshes `output/run_report.md`.
- The report lists every ledger step and its current status.
- The report includes the latest command warnings.

## Boundaries

The run report is a local status artifact. It does not inspect media, run
ffprobe, generate material maps or risk reports, call models, search the
network, or mutate canonical data beyond writing `output/run_report.md`.

## Validation

Covered by:

- `test_scan_writes_sources_and_updates_state`
- `test_review_project_writes_risk_report_from_sources`
