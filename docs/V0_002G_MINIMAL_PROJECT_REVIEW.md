# V0-002g Minimal Project Review

Status: completed.

This slice unlocks a narrow `review --scope project` command that renders a
deterministic risk report from the existing scan ledger.

## Accepted Behavior

- `review --scope project` requires `init` and a prior `scan`.
- The command reads `.artist-portrait/data/sources.jsonl`.
- The command writes `output/risk_report.md`.
- The `review_project` ledger records `output/risk_report.md` and a fingerprint
  of the source ledger.
- Project risk issues return exit code `1 success_with_warnings`, not a fatal
  command failure.
- `review --scope proposal`, `review --scope timeline`, and `review --scope all`
  remain outside the current gate.

## Current Checks

- `provenance_confidence < 0.7` -> `low_provenance_confidence`
- `rights_status = permission_unknown` -> `rights_unknown`
- `rights_status = restricted` while project policy disallows restricted rights
  -> `rights_restricted`
- `forbidden_by_user = true` -> `forbidden_by_user`

## Boundaries

This is not the full V0-010 project review. It does not inspect clips,
transcripts, relations, proposals, timelines, rendered media, external rights
databases, network sources, text models, or vision models.

## Validation

Covered by:

- `test_review_project_requires_scan_first`
- `test_review_non_project_scope_remains_blocked`
- `test_review_project_writes_risk_report_from_sources`
