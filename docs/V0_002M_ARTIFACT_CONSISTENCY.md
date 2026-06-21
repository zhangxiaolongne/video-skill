# V0-002m Artifact Consistency

Status: completed.

This slice hardens the local foundation by checking whether completed ledger
steps still point at real output artifacts.

## Accepted Behavior

- `status --json` includes `artifact_issues`.
- Completed or completed-with-warnings steps are checked against their
  `output_refs`.
- Missing referenced outputs are reported as `missing_output_ref` warnings.
- The human `status` panel shows the artifact issue count when issues exist.
- `review --scope project` includes ledger artifact issues in
  `output/risk_report.md`.
- `review --scope all` runs the implemented project review and records
  proposal/timeline review as skipped warnings.

## Boundaries

This does not implement proposal review, timeline review, media analysis,
transcription, embeddings, model calls, preview rendering, or network search.
It only compares local project state with local filesystem outputs.

## Validation

Covered by:

- `test_status_and_review_report_missing_output_ref`
- `test_review_all_runs_project_review_and_marks_unimplemented_scopes`
- `run_checks.py`
