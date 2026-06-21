# Stage A Acceptance

Status: accepted historical engineering foundation.

Stage A is no longer the active implementation gate. The active gate is
V0-003 media scan foundation, which opens deterministic local scan/report
behavior while keeping segmentation, transcription, visual analysis, BGM
selection, proposals, timelines, preview rendering, model calls, image
generation/editing, and network search closed.

Verified commit:

```text
597807b20c7663196aa01a4610c36f1d7f021b8e
```

GitHub Actions:

```text
workflow: Stage A
run_id: 27879271468
event: push
status: completed
conclusion: success
```

Local check entrypoint:

```bash
.venv/bin/python run_checks.py
```

## Accepted Scope

- repository skeleton
- Pydantic project config model
- Pydantic project state ledger model
- generated JSON Schema
- CLI framework
- `validate`
- `init`
- `status`
- capability detection
- fixed exit codes
- Stage A fixtures
- local tests
- GitHub Actions CI

## Required Evidence

- `validate` accepts `fixtures/stage_a/valid_project.yaml`.
- invalid config fixtures return `3 invalid_project_config`.
- committed schemas match live Pydantic schema generation.
- `init` creates only Stage A workspace files.
- `init --dry-run` does not write project files.
- repeated `init` does not create media or creative artifacts.
- `status` reports `new` before initialization.
- non-Stage-A media command `scan` returns `7 prerequisite_step_missing`.

## Explicitly Not Accepted Yet

- media scanning
- ffprobe scan workflow
- media hashing
- scene detection
- transcription
- OpenCV or visual analysis
- embeddings
- model calls
- material map generation
- creative proposals
- timeline generation
- preview rendering

## Follow-On Gate

V0-002 opened the narrow source ledger, minimal map, project review, and skill
packaging foundation. V0-003 closes the media scan foundation by reconciling
the gate, adding deterministic scan reporting, and invalidating downstream
outputs when the source ledger changes.
