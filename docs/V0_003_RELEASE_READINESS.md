# V0-003 Release Readiness

Status: completed locally, not pushed, not tagged.

This file records the release checkpoint for the V0-003 media scan foundation
batch after implementation and full local validation.

## Commit Base

Remote/local base before this batch:

```text
b003a91 Record release readiness checkpoint
```

## Release Candidate Scope

This local batch includes:

- gate reconciliation from Stage A-only to V0-003 media scan foundation
- `scan` output refs for `sources.jsonl` and `scan_report.md`
- deterministic `output/scan_report.md`
- status visibility for scan report artifacts
- doctor diagnostics for `map_invalidated` and `review_project_invalidated`
- project review visibility for invalidated map outputs
- downstream map/review invalidation after source ledger changes
- gate consistency contract tests
- expanded integration coverage for scan report and invalidation behavior
- `run_checks.py` gate consistency and real-scan report/invalidation coverage
- synchronized master, skill, README, CLI, state, data contract, acceptance, and
  development progress docs

## Required Checks Before Push Or Tag

Run all of these from the repository root:

```bash
.venv/bin/python -m pytest
.venv/bin/python run_checks.py
.venv/bin/python scripts/skill_package_preflight.py . --json
.venv/bin/python scripts/simulate_skill_install.py . --json
git diff --check
```

Local result:

```text
pytest: 74 passed, 1 skipped
run_checks.py: checks passed
skill_package_preflight.py: error_count 0; local folder_name_mismatch warning is allowed
simulate_skill_install.py: ok true, package_preflight.warning_count 0
git diff --check: no output
```

Known local skip:

```text
real scan check skipped when ffmpeg/ffprobe are unavailable
```

## Current Non-Release Actions

Do not push or tag automatically from this slice. Push/tag requires explicit
user confirmation after the release candidate is reviewed.
