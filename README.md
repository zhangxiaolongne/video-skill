# artist-portrait-editor

Local V0 media research foundation for the `artist-portrait-editor` skill.

## Master Document

- [artist_portrait_editor_revision5_optimized.md](artist_portrait_editor_revision5_optimized.md)
- [SKILL.md](SKILL.md)
- [Development Progress](docs/DEVELOPMENT_PROGRESS.md)

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
- [V0-002j Foundation Checks](docs/V0_002J_FOUNDATION_CHECKS.md)
- [V0-002k Invalid Ledger Handling](docs/V0_002K_INVALID_LEDGER_HANDLING.md)
- [V0-002l Atomic Report Writes](docs/V0_002L_ATOMIC_REPORT_WRITES.md)
- [V0-002m Artifact Consistency](docs/V0_002M_ARTIFACT_CONSISTENCY.md)
- [V0-002n Doctor Diagnostics](docs/V0_002N_DOCTOR_DIAGNOSTICS.md)
- [V0-002o Skill Metadata](docs/V0_002O_SKILL_METADATA.md)
- [V0-002p Skill Package Preflight](docs/V0_002P_SKILL_PACKAGE_PREFLIGHT.md)
- [V0-002q Skill Package Policy](docs/V0_002Q_SKILL_PACKAGE_POLICY.md)
- [V0-002r Canonical Install Simulation](docs/V0_002R_CANONICAL_INSTALL_SIMULATION.md)
- [V0-002s Release Readiness](docs/V0_002S_RELEASE_READINESS.md)
- [V0-003 Media Scan Foundation](docs/V0_003_MEDIA_SCAN_FOUNDATION.md)
- [V0-003 Release Readiness](docs/V0_003_RELEASE_READINESS.md)
- [V0-004 Segmentation Foundation](docs/V0_004_SEGMENTATION_FOUNDATION.md)
- [V0-004 Release Readiness](docs/V0_004_RELEASE_READINESS.md)
- [V0-005 Scene Segmentation Gate](docs/V0_005_SCENE_SEGMENTATION_GATE.md)
- [V0-005 Release Readiness](docs/V0_005_RELEASE_READINESS.md)
- [V0-006 Transcription Gate](docs/V0_006_TRANSCRIPTION_GATE.md)
- [V0-006 Release Readiness](docs/V0_006_RELEASE_READINESS.md)
- [V0-007 Keyframe Cache Gate](docs/V0_007_KEYFRAME_CACHE_GATE.md)
- [V0-007 Release Readiness](docs/V0_007_RELEASE_READINESS.md)
- [V0-008 Basic Analysis Gate](docs/V0_008_BASIC_ANALYSIS_GATE.md)
- [V0-008 Release Readiness](docs/V0_008_RELEASE_READINESS.md)
- [Non Goals](docs/NON_GOALS.md)

## Current Gate

Current V0-008 basic analysis gate work allows deterministic project
setup, local media scanning, fixed-window clip segmentation, optional
PySceneDetect video scene segmentation, local-only faster-whisper transcription
when available, ffmpeg midpoint keyframe extraction for video clips,
source/clip/transcript/keyframe/analysis ledger operations, rebuildable
keyframe cache, and read-only/reporting outputs:

```text
project.yaml
-> configuration validation
-> workspace initialization
-> capability detection
-> status ledger
-> source scan ledger
-> scan report from sources.jsonl
-> fixed-window or PySceneDetect clip ledger
-> clip report from clips.jsonl
-> transcript ledger
-> keyframe ledger
-> rebuildable keyframe cache
-> evidence-only analysis ledger
-> analysis report
-> minimal material map from sources.jsonl
-> minimal project risk report from sources.jsonl
-> run report
-> fixed exit codes
```

OpenCV/vision analysis, embeddings, visual classification beyond explicit
evidence placeholders, creative proposal generation, timeline generation,
preview rendering, BGM selection or beat analysis, model calls, image
generation/editing, remote ASR/model downloads, and network search remain out
of scope.

## Local Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

## Local Foundation Commands

```bash
.venv/bin/artist-portrait validate --project fixtures/stage_a/valid_project.yaml
.venv/bin/artist-portrait init --project ./project.yaml
.venv/bin/artist-portrait status --project ./project.yaml
.venv/bin/artist-portrait doctor --project ./project.yaml
.venv/bin/artist-portrait generate-schema --output-dir schemas
.venv/bin/artist-portrait scan --project ./project.yaml
.venv/bin/artist-portrait segment --project ./project.yaml
.venv/bin/artist-portrait transcribe --project ./project.yaml
.venv/bin/artist-portrait keyframes --project ./project.yaml
.venv/bin/artist-portrait analyze --project ./project.yaml
.venv/bin/artist-portrait map --project ./project.yaml
.venv/bin/artist-portrait review --project ./project.yaml --scope project
.venv/bin/artist-portrait review --project ./project.yaml --scope all
```

Commands such as `relate`, `propose`, `timeline`, and `run` remain
intentionally blocked.

## Tests

```bash
.venv/bin/python -m pytest
.venv/bin/python run_checks.py
```
