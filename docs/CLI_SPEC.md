# CLI Spec

Authoritative source: `artist_portrait_editor_revision5_optimized.md`.

Implemented V0-010d proposal validation gate commands:

```bash
artist-portrait validate --project ./project.yaml
artist-portrait init --project ./project.yaml
artist-portrait status --project ./project.yaml
artist-portrait doctor --project ./project.yaml
artist-portrait generate-schema --output-dir schemas
artist-portrait scan --project ./project.yaml
artist-portrait segment --project ./project.yaml
artist-portrait transcribe --project ./project.yaml
artist-portrait keyframes --project ./project.yaml
artist-portrait analyze --project ./project.yaml
artist-portrait map --project ./project.yaml
artist-portrait propose --project ./project.yaml
artist-portrait review --project ./project.yaml --scope project
artist-portrait review --project ./project.yaml --scope proposal
artist-portrait review --project ./project.yaml --scope all
```

Common current-gate flags:

```text
--project PATH
--json
--verbose
--quiet
--dry-run   # init only
```

`review --scope proposal` reads `.artist-portrait/data/proposal_context.json`
and `.artist-portrait/data/proposals.json`, writes
`.artist-portrait/data/proposal_validation.json` and
`output/proposal_review.md`, and validates proposal IDs, required clips,
forbidden-source usage, fact references, material-map fingerprints, and BGM
strategy fields. It does not generate proposals, call models, select music, or
build timelines.

`review --scope all` runs the implemented project review, then records timeline
review as a skipped warning. `review --scope timeline` still returns `7
prerequisite_step_missing`.

Commands outside the current gate currently return `7 prerequisite_step_missing`.

`scan --json` writes `.artist-portrait/data/sources.jsonl`,
`output/scan_report.md`, run metadata, and a refreshed `output/run_report.md`.
It reports `output_refs` and `invalidated_steps`.

`segment --json` writes `.artist-portrait/data/clips.jsonl`,
`output/clip_report.md`, run metadata, and a refreshed `output/run_report.md`.
It routes video segmentation through `features.scene_detection`:

- `off`: deterministic fixed-window segmentation.
- `auto`: PySceneDetect when available, fixed-window fallback with warning when
  missing or failing.
- `required`: PySceneDetect is mandatory; missing or failed scene detection
  returns `4 missing_required_dependency_for_command`.

Audio sources always use fixed-window segmentation. The command reports
`output_refs`, warnings, and `invalidated_steps`.

`transcribe --json` routes source transcription through
`features.transcription`:

- `off`: marks `transcribe` as `skipped` and writes no transcript ledger.
- `auto`: uses local faster-whisper when available; otherwise skips with a
  warning and writes no fake transcripts.
- `required`: local faster-whisper and local model loading are mandatory;
  missing or failed dependencies return `4
  missing_required_dependency_for_command`.

Successful transcription writes `.artist-portrait/data/transcripts.jsonl`, run
metadata, and a refreshed `output/run_report.md`. The faster-whisper adapter
uses local-only model loading and must not download models.

`keyframes --json` reads `.artist-portrait/data/clips.jsonl`, extracts one
deterministic midpoint frame per video clip via ffmpeg, writes
`.artist-portrait/data/keyframes.jsonl`, stores images under
`.artist-portrait/cache/keyframes/`, records run metadata, and refreshes
`output/run_report.md`. Audio-only clips write an empty manifest with a warning.

`analyze --json` reads `.artist-portrait/data/clips.jsonl` and optionally uses
existing `.artist-portrait/data/transcripts.jsonl` and
`.artist-portrait/data/keyframes.jsonl` as evidence. It writes
`.artist-portrait/data/analysis.jsonl`, `output/analysis_report.md`, run
metadata, and a refreshed `output/run_report.md`. Current V0-008 analysis is
evidence-only: media/material type and original audio usability are recorded
from existing ledgers, while shot size, camera motion, emotion, action, and
visual quality remain null or empty candidates. No OpenCV, vision model,
embedding, BGM, proposal, timeline, preview, image, network, or model call is
performed.

`map --json` requires a current `.artist-portrait/data/analysis.jsonl`. It
writes `output/material_map.md`, run metadata, and a refreshed
`output/run_report.md`. The report is rendered from source and analysis ledgers
and includes material distributions, a deterministic priority review queue,
pending confirmation fields, and risk sections. It does not generate creative
proposals, BGM choices, timelines, previews, visual classifications, network
results, image outputs, or model-backed judgments.

`propose --json` is currently a context/readiness gate only. It requires
`output/material_map.md`; without it the command returns `7
prerequisite_step_missing`. It writes deterministic
`.artist-portrait/data/proposal_context.json` from local source, clip,
analysis, and material-map evidence, then writes deterministic
`.artist-portrait/data/text_model_gate.json` from project policy and detected
capabilities. When the text-model gate is blocked, it records the `propose`
step as `blocked`, writes run metadata, returns `4
missing_required_dependency_for_command`, and writes no fake
`.artist-portrait/data/proposals.json` or `output/proposals.md`. If the gate is
ready, current generation still remains closed and `propose` returns the same
dependency code with `proposal_generation_not_implemented`.

`status --json` includes the state ledger plus local artifact, source, clip,
transcript, keyframe, analysis, proposal context, text-model gate, proposal,
scan report, clip report, and analysis report summaries plus material map
presence. It also reports `artifact_issues` when
completed ledger steps refer to outputs that no longer exist. It does not run
media operations or mutate project files.

`doctor --json` is a read-only diagnostic command. It reports local workspace,
source ledger, and artifact consistency issues with `next_action` guidance and
`recommended_commands`. It reports `segment_invalidated`,
`transcribe_invalidated`, `keyframes_invalidated`, `analyze_invalidated`,
`map_invalidated`, and `review_project_invalidated` after newer upstream
ledgers change. It reports
`clips_invalid` when `.artist-portrait/data/clips.jsonl` cannot be parsed,
`transcripts_invalid` when `.artist-portrait/data/transcripts.jsonl` cannot be
parsed, `keyframes_invalid` when `.artist-portrait/data/keyframes.jsonl` cannot
be parsed, and `keyframe_cache_missing` when rebuildable cached frame images are
missing. It reports `analysis_invalid` when
`.artist-portrait/data/analysis.jsonl` cannot be parsed. It reports
`scene_detection_required_missing` or
`transcription_required_missing` when the project requires an unavailable
dependency. It reports `proposal_context_invalid` when
`.artist-portrait/data/proposal_context.json` cannot be parsed as
`ProposalContext`, `text_model_gate_invalid` when
`.artist-portrait/data/text_model_gate.json` cannot be parsed as
`TextModelGate`, `proposals_invalid` when
`.artist-portrait/data/proposals.json` cannot be parsed as `ProposalSet`, and
`propose_text_model_missing` when `material_map.md` exists but no approved text
model gate is available for proposal generation. It
returns `1 success_with_warnings` when diagnostics find issues and `0 success`
when no issues are found.
