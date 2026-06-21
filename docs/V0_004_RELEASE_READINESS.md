# V0-004 Release Readiness

Status: completed locally, ready to push, not tagged.

This file records the release checkpoint for the V0-004 fixed-window
segmentation foundation batch after implementation and full local validation.

## Commit Base

Remote/local base before this batch:

```text
6760831 Close V0-003 media scan foundation
```

## Release Candidate Scope

This local batch includes:

- `ClipRecord` schema and committed `clip_record.schema.json`
- `segment --project`
- deterministic fixed-window segmentation
- canonical `.artist-portrait/data/clips.jsonl`
- rebuildable `output/clip_report.md`
- clip artifact and summary reporting in `status`
- `clips_invalid` and `segment_invalidated` doctor diagnostics
- scan-to-segment invalidation
- clips-to-map/review invalidation
- run_checks coverage for clip report and clip summary behavior
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
pytest: 79 passed, 1 skipped
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

Push `main` only after the release candidate checks pass and the user requests
the completed version to be handled as one batch. Tagging still requires an
explicit separate user request.
