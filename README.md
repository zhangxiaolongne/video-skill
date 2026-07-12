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
Current release state lives in `docs/RELEASES.md`; detailed historical release
outcomes live in `docs/archive/RELEASES_HISTORY.md`.

## Spec Entrypoints

- [Engineering Spec V0](docs/ENGINEERING_SPEC_V0.md)
- [Current Machine-Readable Progress](docs/current_progress.json)

## Current Gate

Current V2-01 Real Video Aesthetic Baseline planning is preceded by the
Stage 07 baseline-recovery work and builds on the published
V1-08 revision promotion and release packaging work. The published system
allows deterministic project
setup, local media scanning, fixed-window clip segmentation, optional
PySceneDetect video scene segmentation, local-only faster-whisper transcription
when available, ffmpeg midpoint keyframe extraction for video clips,
source/clip/transcript/keyframe/analysis ledger operations, rebuildable
keyframe cache, analysis-led material maps, explicit or recommended
target-duration edit briefs, short/standard/extended duration options,
platform assumptions, evidence/risk notes, BGM/source-audio guidance,
state/run audit, workflow ordering before proposal, `.artist-portrait/data/edit_brief.json`,
`output/edit_brief.md`, `.artist-portrait/data/clip_scores.jsonl`,
`output/clip_score_report.md`, score-aware hook/build/payoff
`output/timeline_draft.json`, duration variants, keep/drop rationale,
source continuity checks, deterministic
sound/BGM decisions with original-audio, direct-BGM, video-extracted mixed-audio,
source-embedded-audio, silence, ducking, fade, fit-policy, and beat-fallback
coverage in `.artist-portrait/data/sound_decision.json` and
`output/sound_decision.md`, deterministic
cut review and manual second-pass planning in
`.artist-portrait/data/cut_review.json` and `output/cut_review.md`,
user revision-loop planning in `.artist-portrait/data/revision_plan.json` and
`output/revision_plan.md`, controlled revision application in
`.artist-portrait/data/revision_application.json` and
`output/revision_application.md`,
explicit revised-candidate promotion in
`.artist-portrait/data/revision_promotion.json` and
`output/revision_promotion.md`,
deterministic proposal context, a visible local host-Agent handoff,
quarantined candidate import, atomic
canonical proposal promotion, proposal contract validation, deterministic
proposal review, explicit timeline generation, multi-source BGM fitting,
explicit BGM fit controls, local BGM technical analysis, validated local
beat-engine evidence when an adapter is available, BGM recommendation review,
explicit recommendation-to-fit selection, recommendation-fit review,
low-resolution preview rendering, preview render controls, preview QC,
controlled local final MP4 export, project acceptance reporting,
profile-specific acceptance gates, generated real-media fixture acceptance
checks, direct actionable next commands in acceptance reports, BGM/edit rhythm planning,
rhythm media QC, rhythm manual repair planning, guided workflow planning,
workflow execution evidence review, workflow evidence repair planning,
release hardening audit, BGM rhythm
intelligence, phrase-level manual edit guidance, operator runbook usability,
editor package handoff, NLE interchange planning, supervised FCPXML draft
writing, explicit FCPXML import-review evidence validation, and FCPXML
import/relink repair planning,
the golden real-project baseline, the
BGM/rhythm quality pass, the supervised NLE round-trip readiness pass, and the
release-candidate validation path:

## Current Final-Acceptance Stage

Current published capability work: `V1-08 Revision promotion, revised render
readiness, and V1 release packaging` in the retained `v0.30.0` baseline.
Current local acceptance stage: `ACCEPTANCE-STAGE-07 Real Media Truthfulness And Baseline Recovery`.
Current V2-07 Text, Subtitle, And On-Screen Timing Plan is complete locally and awaiting publication. V2-06 is published.
The latest published acceptance release remains `ACCEPTANCE-STAGE-06 Release
candidate and publication` in `v0.28.0`; the latest published V1 capability
release baseline is `v0.30.0`.
The project is no longer treating isolated artifacts, schemas,
reports, packets, review rules, or individual tests as major progress toward
final usability. Remaining acceptance work was organized into six stages; Stage
6 is complete, and V1 work now moves through promoted aesthetic-editor
capability gates.

`artist-portrait timeline --project <project.yaml> --proposal <id>` now consumes
the selected canonical proposal, edit brief, clip scores, clips, and sources to
write a score-aware hook/build/payoff `output/timeline_draft.json`. Duration
variants, keep/drop rationale, source continuity checks, score bindings, and
forbidden-capability flags stay inside the canonical timeline/review artifacts
instead of creating extra sidecar JSON.

`artist-portrait sound --project <project.yaml>` now reads the canonical
timeline and available BGM/source-audio evidence to write one Tier 1 canonical
sound decision JSON plus one Markdown report. It records whether the project is
using original audio, awaiting direct BGM, carrying video-extracted mixed audio
risk, reusing embedded source audio, falling back to silence, or preserving a
beat-unavailable workflow. It does not select or fit music automatically.

`artist-portrait cut-review --project <project.yaml>` now reads the current
timeline, sound decision, rhythm evidence, preview/final validation, rhythm QC,
and edit guidance when present. It writes one Tier 1 canonical cut review JSON
plus one Markdown report, diagnosing weak opening, dead space, ending,
rhythm/audio conflict, media-QC gaps, and manual second-pass actions. It does
not render media, mutate the timeline, move edit points, or treat the
second-pass plan as applied edits.

`artist-portrait revise --project <project.yaml> --intent "<user note>"` now
reads the current canonical timeline, current cut review, optional
sound/rhythm/media evidence, and an explicit user revision note. It writes one
Tier 1 canonical revision plan JSON plus one Markdown report, classifying notes
such as shorter, stronger hook, more emotional, keep/remove segment, change
ending, reduce subtitles, or reduce BGM, then compares the current version with
manual revision candidates. It does not render media, mutate the timeline, move
edit points, select or fit music, call models, access the network, or claim the
revision actions were applied.

`artist-portrait promote-revision --project <project.yaml>
--revision-application-id <id>` is the V1-08 promotion gate. It validates the
current revision application against the current canonical timeline, then
promotes the revised candidate into `output/timeline_draft.json` and marks
stale downstream preview/final/rhythm/review/handoff artifacts for rerun. The
promotion command does not render media, select or fit music, call models,
access the network, or claim revised media exists until the render commands are
run.

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
-> edit_brief.json and edit_brief.md
-> clip_scores.jsonl and clip_score_report.md
-> proposal_context.json from local ledgers
-> proposal_agent_handoff.json for Codex/ChatGPT host-Agent generation
-> quarantined ProposalSet candidate import with no paid API or network call
-> atomic proposals.json promotion after deterministic validation
-> proposal_validation.json and proposal_review.md
-> timeline_draft.json and timeline_review.md
-> bgm_candidates.json and bgm_fit.json
-> bgm_analysis.json and bgm_analysis_report.md
-> bgm_beat_grids/<music_candidate_id>.json when a validated local beat adapter succeeds
-> bgm_rhythm_intelligence.json, bgm_rhythm_intelligence.md, and bgm_rhythm_handoff.json
-> edit_guidance.json, edit_guidance.md, and edit_guidance_handoff.json
-> operator_runbook.json, operator_runbook.md, and operator_handoff.json
-> editor_package.json, editor_package.md, cue_sheet.csv, and editor_handoff.json
-> nle_interchange_plan.json, nle_interchange_plan.md, nle_interchange_map.csv, and nle_interchange_handoff.json
-> fcpxml_draft.json, fcpxml_validation.json, draft.fcpxml, fcpxml_review.md, and fcpxml_handoff.json
-> fcpxml_import_review_candidate_quarantine.json, fcpxml_import_review.json, fcpxml_import_review.md, and fcpxml_import_review_handoff.json
-> fcpxml_repair_plan.json, fcpxml_repair_plan.md, and fcpxml_repair_handoff.json
-> bgm_recommendation_context.json and bgm_recommendation_agent_handoff.json
-> bgm_recommendations.json and bgm_recommendation_review.md
-> bgm_recommendation_selection.json and bgm_recommendation_selection_review.md
-> BgmFitControls embedded in bgm_fit.json
-> bgm_fit_review.json and bgm_fit_review.md
-> preview_lowres.mp4
-> preview_manifest.json and preview_validation.json
-> preview_review.md
-> final_export.mp4
-> final_export_manifest.json and final_export_validation.json
-> final_export_review.md
-> acceptance_report.json and acceptance_report.md
-> acceptance --profile standard|core|preview|delivery
-> rhythm_plan.json, rhythm_report.md, and rhythm_agent_handoff.json
-> rhythm-aware acceptance required stages and repair commands
-> rhythm_media_qc.json, rhythm_media_qc.md, and rhythm_media_qc_handoff.json
-> rhythm_repair_plan.json, rhythm_repair_plan.md, and rhythm_repair_handoff.json
-> workflow_plan.json, workflow_plan.md, and workflow_agent_handoff.json
-> workflow_execution_record_quarantine.json
-> workflow_execution_review.json, workflow_execution_review.md, and workflow_execution_handoff.json
-> release_hardening_report.json and release_hardening_report.md
-> generated real-media acceptance fixture through run_checks.py
-> minimal project risk report from sources.jsonl
-> run report
-> fixed exit codes
```

OpenCV/vision analysis, embeddings, visual classification beyond explicit
evidence placeholders, fake/template proposals, automatic BGM selection or
recommendation, fabricated beat analysis, model calls, image
generation/editing, remote ASR/model downloads, network search, automatic
repair command execution, treating execution evidence as acceptance success,
automatic edit-point movement, automatic music selection, and rhythm-triggered
media rendering, rhythm-QC-triggered media rendering, or rhythm-repair-triggered
execution remain out of scope.

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
.venv/bin/artist-portrait bgm recommend --project ./project.yaml
.venv/bin/artist-portrait bgm select --project ./project.yaml --recommendation-id <id>
.venv/bin/artist-portrait bgm fit --project ./project.yaml --candidate <candidate-id> --fit-mode auto --fade-in-seconds 0.5 --fade-out-seconds 1.0 --ducking-gain-db -9
.venv/bin/artist-portrait bgm review --project ./project.yaml
.venv/bin/artist-portrait preview --project ./project.yaml --width 480 --fps 12
.venv/bin/artist-portrait composition --project ./project.yaml --samples 9
.venv/bin/artist-portrait composition --project ./project.yaml --agent-output ./composition_review_candidate.json
.venv/bin/artist-portrait composition --project ./project.yaml --preview-candidate <candidate-id>
.venv/bin/artist-portrait baseline --project ./project.yaml
.venv/bin/artist-portrait baseline --project ./project.yaml --agent-output ./aesthetic_baseline_candidate.json
.venv/bin/artist-portrait second-cut --project ./project.yaml --concept-id <concept-id>
.venv/bin/artist-portrait review --project ./project.yaml --scope project
.venv/bin/artist-portrait review --project ./project.yaml --scope proposal
.venv/bin/artist-portrait review --project ./project.yaml --scope timeline
.venv/bin/artist-portrait review --project ./project.yaml --scope preview
.venv/bin/artist-portrait review --project ./project.yaml --scope all
.venv/bin/artist-portrait acceptance --project ./project.yaml
.venv/bin/artist-portrait acceptance --project ./project.yaml --profile core
.venv/bin/artist-portrait acceptance --project ./project.yaml --profile preview
.venv/bin/artist-portrait acceptance --project ./project.yaml --profile delivery
```

Commands such as `relate` and final `run` remain intentionally blocked.
`baseline` prepares one evidence-bound host-Agent handoff from the current
timeline, edit brief, clip scores, and composition review. Its explicit
candidate must cover every range and compare exactly three materially different
short, standard, and extended concepts. Import writes one canonical JSON plus
one Markdown report. The same baseline binds sound/rhythm/final evidence for a
nine-domain audiovisual decision and separates technical delivery from first-cut
publishability; it never selects a concept, moves edits, or renders media.
`second-cut` requires an exact concept id from that baseline. It converts the
chosen direction into ordered selection, structure, trim, per-shot reframe,
source-audio, BGM, text, transition, pause, ending, and verification actions,
while leaving the canonical timeline and media unchanged.
`reframe` requires one explicit selection covering every timeline segment with
either a current composition candidate or `preserve`. It binds current
timeline/final/composition fingerprints, blocks rejected candidates and
protected-region loss, preserves final audio, audits crop-center jumps, and
renders independent `output/reframe_playback.mp4` evidence without overwriting
the canonical timeline or final export.
`evidence-map` aligns clip/scene boundaries, transcript timing, keyframe and
analysis coverage, local FFmpeg audio energy/silence features, and edit-brief
goals into one canonical map. Every channel records availability, confidence,
limitations, unknown semantics, and degradation. Missing transcript is not
silence; a keyframe is not visual understanding; audio energy is not proof of
speech, music, applause, emotion, lyrics, or BPM.
`editorial-score` ranks visual evidence units independently as highlight, hook,
and ending candidates. Every candidate exposes eight editorial dimensions,
confidence, rationale, unknowns, and risk penalty. Missing semantics use a
neutral prior with zero confidence; pure-audio clips, first/last position, and
loudness receive no false aesthetic promotion.
`structure-recommend` converts current rankings and the edit brief into short,
standard, and extended options with exact candidate ranges, hook/build/payoff
roles, sacrifices, retained qualities, confidence, and coupled audio/text/BGM/
transition risks. Standard preserves the explicit target duration; no timeline
or media is changed.
`bgm-match` evaluates direct/extracted/embedded/multiple/no-file BGM states
against current structure options and exposes mood/rhythm evidence plus
ducking, text, and transition pressure. It never auto-selects music or treats
mixed video audio and technical energy as clean semantic music evidence.
`text-plan` creates option-specific title, subtitle-slot, emphasis, pause, and
empty-space timing with reading and safe-region risk. Subtitle/emphasis content
requires transcript evidence; missing text remains unavailable and is never
invented or burned into media.
`propose` prepares a host-Agent handoff and can import an explicit quarantined
ProposalSet candidate; it does not call paid APIs or access the network.

## Tests

Local `runs/`, `output/`, and `.artist-portrait/` evidence are not part of the
distributed Skill install. Use `artist-portrait cleanup --project ./project.yaml`
only when you explicitly want to remove rebuildable render cache; it never runs
as part of validation, rendering, or normal skill operation, and it does not
delete source media or final output.
They are intentionally excluded from Git commits but remain visible in
`artist-portrait status --project ./project.yaml`, including total and cache size.

```bash
.venv/bin/python -m pytest
.venv/bin/python run_checks.py
```
