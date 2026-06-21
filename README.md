# artist-portrait-editor

Stage A engineering foundation for the `artist-portrait-editor` skill.

## Master Document

- [artist_portrait_editor_revision5_optimized.md](artist_portrait_editor_revision5_optimized.md)

## Spec Entrypoints

- [Vision](docs/VISION.md)
- [Product Spec V0](docs/PRODUCT_SPEC_V0.md)
- [Engineering Spec V0](docs/ENGINEERING_SPEC_V0.md)
- [CLI Spec](docs/CLI_SPEC.md)
- [State And Invalidation](docs/STATE_AND_INVALIDATION.md)
- [Data Contracts](docs/DATA_CONTRACTS.md)
- [Model Boundaries](docs/MODEL_BOUNDARIES.md)
- [Acceptance Tests V0](docs/ACCEPTANCE_TESTS_V0.md)
- [Stage A Acceptance](docs/STAGE_A_ACCEPTANCE.md)
- [V0-002a Media Scan](docs/V0_002A_MEDIA_SCAN.md)
- [V0-002b Media Scan Acceptance](docs/V0_002B_MEDIA_SCAN_ACCEPTANCE.md)
- [V0-002c Sources CSV Import](docs/V0_002C_SOURCES_CSV_IMPORT.md)
- [V0-002d Rescan Identity](docs/V0_002D_RESCAN_IDENTITY.md)
- [V0-002e Supersedes Tracking](docs/V0_002E_SUPERSEDES.md)
- [V0-002f Minimal Material Map](docs/V0_002F_MINIMAL_MATERIAL_MAP.md)
- [V0-002g Minimal Project Review](docs/V0_002G_MINIMAL_PROJECT_REVIEW.md)
- [V0-002h Status Dashboard](docs/V0_002H_STATUS_DASHBOARD.md)
- [V0-002i Run Report Refresh](docs/V0_002I_RUN_REPORT_REFRESH.md)
- [Non Goals](docs/NON_GOALS.md)

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
.venv/bin/python run_checks.py
```
