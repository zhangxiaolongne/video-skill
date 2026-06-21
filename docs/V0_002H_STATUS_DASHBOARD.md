# V0-002h Status Dashboard

Status: completed.

This slice expands `status` into a local project dashboard while preserving the
existing top-level JSON fields.

## Accepted Behavior

- `status --json` keeps `project_id`, `overall_status`, and `steps` at the top
  level when initialized.
- Before `init`, `status --json` still reports `overall_status = new` and
  `state = null`.
- `status --json` adds artifact existence and size checks.
- `status --json` adds summaries for `sources.jsonl`, `material_map.md`, and
  `risk_report.md`.
- `status --json` adds the latest run command and step result when available.
- Human `status` output is a compact multi-line panel.

## Boundaries

`status` does not scan media, run ffprobe, generate reports, validate external
rights, call models, search the network, or mutate project files.

## Validation

Covered by:

- `test_status_before_init_reports_new`
- `test_status_after_init_json`
- `test_status_after_init_human_panel`
- `test_review_project_writes_risk_report_from_sources`
