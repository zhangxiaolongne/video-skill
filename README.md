# artist-portrait-editor

Local V0 media research foundation for the `artist-portrait-editor` skill.

## Master Document

- [artist_portrait_editor_revision5_optimized.md](artist_portrait_editor_revision5_optimized.md)
- [SKILL.md](SKILL.md)
- [Development Progress](docs/DEVELOPMENT_PROGRESS.md)
- [Current Batch](docs/CURRENT_BATCH.md)
- [Issues And Risks](docs/ISSUES.md)
- [Decision Ledger](docs/DECISIONS.md)
- [Release Ledger](docs/RELEASES.md)

The files above are the canonical current documentation entry points.
Historical version outcomes are consolidated in `docs/RELEASES.md`.

## Spec Entrypoints

- [Engineering Spec V0](docs/ENGINEERING_SPEC_V0.md)
- [Current Machine-Readable Progress](docs/current_progress.json)

## Current Gate

Current V0-018 BGM recommendation review gate work allows deterministic project
setup, local media scanning, fixed-window clip segmentation, optional
PySceneDetect video scene segmentation, local-only faster-whisper transcription
when available, ffmpeg midpoint keyframe extraction for video clips,
source/clip/transcript/keyframe/analysis ledger operations, rebuildable
keyframe cache, analysis-led material maps, deterministic proposal context
packets, text-model gate packets, deterministic proposal request packets,
proposal adapter preflight packets, provider registry packets, local mock
adapter handshake packets, execution approval request packets, execution approval record packets, execution readiness plan packets, execution input bundle packets, provider call dry-run packets, execution authorization packets, provider response intake plan packets, provider output
quarantine packets, provider response validation plan packets, promotion authorization/validation packets, canonical write transaction plan packets, provider result envelope packets, a local host-Agent handoff, quarantined candidate import, atomic canonical proposal promotion, proposal contract validation, deterministic proposal review, explicit timeline generation, multi-source BGM fitting, local BGM technical analysis, BGM recommendation review, low-resolution preview rendering, preview render controls, preview QC, and read-only/reporting outputs and controlled local final MP4 export:

The V0-010 proposal foundation is now consolidated around one artifact registry.
`status` and `doctor` validate cross-artifact references, project identity,
missing dependencies, upstream fingerprints, and duplicate ledger output refs.
The registry and integrity checks now live in a dedicated proposal artifact
module, while `docs/current_progress.json` records capability progress separately
from implementation task counts.
Proposal JSON loading now lives in `proposal_io.py`; the workspace keeps
compatibility wrappers while status summary routing is registry-driven.
Proposal review now checks structural completeness, evidence closure,
safe/advanced/risky differentiation, and actionable BGM execution details.
It also enforces creative-brief consistency, counter-proposal challenges,
top-level evidence integrity, unique titles, explicit risks, and no absolute
local path leakage.
Policy review blocks forbidden generation methods and forbidden-material
fact-ref bypasses, aligns analysis evidence to required clips, detects
contradictory missing-material claims, and respects `allow_music: false`.

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
-> material map from sources.jsonl and analysis.jsonl
-> proposal_context.json from local ledgers
-> text_model_gate.json from project policy and detected capabilities
-> proposal_request.json for future model adapter input
-> proposal_adapter_check.json for provider/secret/model-call preflight
-> proposal_provider_registry.json for local provider registration
-> proposal_mock_adapter_handshake.json for no-call response contract handshake
-> proposal_execution_approval_request.json for no-approval execution request
-> proposal_execution_approval_record.json for no-grant approval record
-> proposal_execution_readiness_plan.json for five closed execution-readiness sub-stages
-> proposal_execution_input_bundle.json for ten closed provider execution input sub-items
-> proposal_provider_call_dry_run.json for ten closed provider call dry-run sub-items
-> proposal_execution_authorization.json for no-call execution authorization
-> proposal_provider_response_intake_plan.json for ten closed provider response intake sub-items
-> proposal_provider_output_quarantine.json for no-output quarantine
-> proposal_provider_response_validation_plan.json for ten closed response validation sub-items
-> proposal_promotion_authorization_plan.json for ten closed promotion conditions
-> proposal_promotion_validation_report.json for ten unperformed validation domains
-> proposal_canonical_write_transaction_plan.json for ten blocked transaction stages
-> proposal_provider_result.json for dry-run provider result envelope
-> proposal_agent_handoff.json for Codex/ChatGPT host-Agent generation
-> quarantined ProposalSet candidate import with no paid API or network call
-> atomic proposals.json promotion after deterministic validation
-> proposal_validation.json and proposal_review.md
-> timeline_draft.json and timeline_review.md
-> bgm_candidates.json and bgm_fit.json
-> bgm_analysis.json and bgm_analysis_report.md
-> bgm_recommendation_context.json, bgm_recommendation_request.json, and bgm_recommendation_agent_handoff.json
-> bgm_recommendations.json and bgm_recommendation_review.md
-> preview_lowres.mp4
-> preview_manifest.json and preview_validation.json
-> preview_review.md
-> final_export.mp4
-> final_export_manifest.json and final_export_validation.json
-> final_export_review.md
-> minimal project risk report from sources.jsonl
-> run report
-> fixed exit codes
```

OpenCV/vision analysis, embeddings, visual classification beyond explicit
evidence placeholders, fake/template proposals, automatic BGM selection or
recommendation, fabricated beat analysis, model calls, image
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
.venv/bin/artist-portrait propose --project ./project.yaml
.venv/bin/artist-portrait timeline --project ./project.yaml --proposal proposal_safe
.venv/bin/artist-portrait bgm import --project ./project.yaml --file media/bgm.wav --rights-status owned
.venv/bin/artist-portrait bgm fit --project ./project.yaml --candidate <candidate-id>
.venv/bin/artist-portrait preview --project ./project.yaml --width 480 --fps 12
.venv/bin/artist-portrait review --project ./project.yaml --scope project
.venv/bin/artist-portrait review --project ./project.yaml --scope proposal
.venv/bin/artist-portrait review --project ./project.yaml --scope timeline
.venv/bin/artist-portrait review --project ./project.yaml --scope preview
.venv/bin/artist-portrait review --project ./project.yaml --scope all
```

Commands such as `relate` and final `run` remain intentionally blocked.
`propose` prepares a host-Agent handoff and can import an explicit quarantined
ProposalSet candidate; it does not call paid APIs or access the network.

## Tests

```bash
.venv/bin/python -m pytest
.venv/bin/python run_checks.py
```
