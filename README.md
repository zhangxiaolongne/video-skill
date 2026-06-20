# artist-portrait-editor

Stage A engineering foundation for the `artist-portrait-editor` skill.

## Master Document

- [artist_portrait_editor_revision5_optimized.md](artist_portrait_editor_revision5_optimized.md)

## Current Gate

Only Phase A is allowed:

```text
project.yaml
-> configuration validation
-> workspace initialization
-> capability detection
-> status ledger
-> run report
-> fixed exit codes
```

Implementation of media scanning, transcription, visual analysis, creative
proposal generation, and timeline generation is explicitly out of scope until
Phase A passes.

## Local Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

## Stage A Commands

```bash
.venv/bin/artist-portrait validate --project fixtures/stage_a/valid_project.yaml
.venv/bin/artist-portrait init --project ./project.yaml
.venv/bin/artist-portrait status --project ./project.yaml
.venv/bin/artist-portrait generate-schema --output-dir schemas
```

Non-Stage-A commands such as `scan`, `segment`, `transcribe`, `analyze`,
`propose`, and `timeline` are intentionally blocked until the Stage A gate
passes.

## Tests

```bash
.venv/bin/python -m pytest
```
