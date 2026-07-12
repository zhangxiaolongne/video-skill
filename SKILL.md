---
name: artist-portrait-editor
description: Artist portrait video workflow for deterministic media ledgers, evidence analysis, analysis-led material map, Codex/ChatGPT host Agent proposals quarantined, validated, reviewed, and atomically promoted, timeline planning, BGM fitting, rhythm guidance, preview/final export, acceptance reporting, editor/NLE handoff, FCPXML draft and import-review repair planning, workflow planning and evidence review, and release hardening, without paid APIs, API keys, or network calls.
---

# Artist Portrait Editor

Use this skill to operate the local `artist-portrait` CLI for deterministic
artist portrait project preparation and audit work.

## Operating Order

1. Read `project.yaml` and run validation:

   ```bash
   artist-portrait validate --project ./project.yaml
   ```

2. Initialize local state before any other workspace command:

   ```bash
   artist-portrait init --project ./project.yaml
   ```

3. Inspect current state and diagnostics:

   ```bash
   artist-portrait status --project ./project.yaml --json
   artist-portrait doctor --project ./project.yaml --json
   ```

4. Ask for the guided workflow path when the next command is unclear:

   ```bash
   artist-portrait workflow --project ./project.yaml --target delivery --json
   ```

   The workflow command writes `.artist-portrait/data/workflow_plan.json`,
   `output/workflow_plan.md`, and `output/workflow_agent_handoff.json`. It
   orders explicit commands for `core`, `preview`, or `delivery` targets. It
   does not execute commands, render media, move edit points, select music, fit
   music, call models from the CLI, or access the network.

   To review explicit external workflow execution evidence, import a record
   candidate:

   ```bash
   artist-portrait workflow --project ./project.yaml --target delivery --execution-record ./workflow_execution_record.json --json
   ```

   This quarantines the candidate byte-for-byte, then writes
   `.artist-portrait/data/workflow_execution_review.json`,
   `output/workflow_execution_review.md`, and
   `output/workflow_execution_handoff.json`. It validates plan, step, command,
   and artifact evidence bindings. It does not execute commands or treat
   execution evidence as acceptance success.

5. Before any local release, run release hardening:

   ```bash
   artist-portrait release-check --project ./project.yaml --json
   ```

   This writes `.artist-portrait/data/release_hardening_report.json` and
   `output/release_hardening_report.md`. It audits current-gate docs, git
   publication state, schema coverage, forbidden source surfaces,
   workflow/rhythm artifact coverage, and validation evidence. It does not
   commit, push, tag, render media, call models, access the network, execute
   repair commands, or mark acceptance success.

6. Scan local media only when `ffmpeg` and `ffprobe` are available:

   ```bash
   artist-portrait scan --project ./project.yaml
   ```

   This writes `.artist-portrait/data/sources.jsonl` and
   `output/scan_report.md`.

7. Generate deterministic local reports from `.artist-portrait/data/sources.jsonl`:

   ```bash
   artist-portrait segment --project ./project.yaml
   artist-portrait transcribe --project ./project.yaml
   artist-portrait keyframes --project ./project.yaml
   artist-portrait analyze --project ./project.yaml
   artist-portrait map --project ./project.yaml
   artist-portrait review --project ./project.yaml --scope project
   ```

   `segment` writes `.artist-portrait/data/clips.jsonl` and
   `output/clip_report.md`. Videos use `features.scene_detection`:
   `off` keeps fixed-window segmentation, `auto` uses PySceneDetect when
   available and falls back to fixed-window with a warning, and `required`
   fails with exit code 4 when PySceneDetect is missing or fails. Audio always
   uses fixed-window segmentation.

   `transcribe` writes `.artist-portrait/data/transcripts.jsonl` only when
   `features.transcription` allows it and local faster-whisper plus a local
   model are available. `off` marks the step skipped, `auto` skips with a
   warning when faster-whisper is unavailable or local model loading fails, and
   `required` fails with exit code 4 in those cases. It must not download
   models or invent transcript text.

   `keyframes` reads `.artist-portrait/data/clips.jsonl`, extracts one
   deterministic midpoint frame for each video clip via ffmpeg, writes
   `.artist-portrait/data/keyframes.jsonl`, and stores images under
   `.artist-portrait/cache/keyframes/`. Audio clips do not require keyframes.
   Cache files may be deleted and rebuilt; the JSONL manifest is the canonical
   record.

   `analyze` reads `.artist-portrait/data/clips.jsonl` and optionally uses
   existing `transcripts.jsonl` and `keyframes.jsonl` as evidence. It writes
   `.artist-portrait/data/analysis.jsonl` and `output/analysis_report.md`.
   Current analysis is evidence-only: media/material type and original audio
   usability are recorded from existing ledgers, while shot size, camera
   motion, emotion, action, and visual quality remain null or empty candidates.

   `map` requires a current `.artist-portrait/data/analysis.jsonl`. It writes
   `output/material_map.md` with material distributions, a deterministic
   priority review queue, pending confirmation fields, and risk sections. It
   does not generate creative recommendations.

   `propose` prepares a self-contained host-Agent handoff:

   ```bash
   artist-portrait propose --project ./project.yaml
   ```

   It requires `output/material_map.md`, writes deterministic
   `.artist-portrait/data/proposal_context.json` and
   `output/proposal_agent_handoff.json`. It does not create simulated provider,
   approval, authorization, dry-run, or promotion artifacts.

   Read the handoff, use the current Codex/ChatGPT reasoning capability to
   create exactly one `ProposalSet` JSON object, write it to a local candidate
   file, then run:

   ```bash
   artist-portrait propose --project ./project.yaml \
     --agent-output ./proposal_candidate.json
   ```

   The CLI quarantines exact candidate bytes before parsing, validates schema,
   evidence, policy, proposal differentiation, and BGM strategy, then atomically
   writes `.artist-portrait/data/proposals.json` only when all error-level
   checks pass. Never request an API key or call a paid/remote model for this
   workflow.

   Existing proposals can be validated deterministically:

   ```bash
   artist-portrait review --project ./project.yaml --scope proposal
   ```

   This reads `.artist-portrait/data/proposal_context.json` and
   `.artist-portrait/data/proposals.json`, writes
   `.artist-portrait/data/proposal_validation.json` and
   `output/proposal_review.md`, and checks proposal IDs, clip refs, fact refs,
   forbidden sources, and BGM strategy fields. It does not generate proposals.

6. Use `review --scope all` only as a shallow project aggregate. Use the
   dedicated proposal, timeline, and preview scopes for canonical artifact
   validation.

7. After the user explicitly chooses one canonical proposal, generate and
   review the timeline:

   ```bash
   artist-portrait timeline --project ./project.yaml \
     --proposal proposal_safe
   artist-portrait review --project ./project.yaml --scope timeline
   ```

   Replace `proposal_safe` only with the user's selected
   `proposal_advanced` or `proposal_risky`. Never choose on the user's behalf.
   The command writes `output/timeline_draft.json`,
   `.artist-portrait/data/timeline_validation.json`, and
   `output/timeline_review.md`. It preserves an unresolved or policy-disabled
   music slot but performs no BGM selection, extraction, beat analysis, fitting,
   preview, final render, model call, or network request.

## BGM Workflow

V0-013 accepts music through these input modes:

- `direct_audio`: a directly uploaded complete or partial audio track
- `video_audio_extract`: a selected stream and range from an uploaded video
- `source_embedded_audio`: original audio or music already attached to source media
- `multiple_candidates`: multiple retained candidates for separate proposal/output evaluation
- `none_yet`: an unresolved music slot while rhythm and sound structure are planned

Every candidate must retain source identity, media kind, extraction range,
stream index, content hash, duration, rights status, user intent, analysis
status, and possible speech, vocal, environment, or sound-effect content.
Audio extracted from video is mixed audio unless explicit separation or
analysis proves otherwise. Never label extraction alone as clean BGM,
instrumental, or pure accompaniment. Extraction, transcoding, separation, and
analysis outputs belong in rebuildable cache; the original candidate remains
traceable.

Use:

```bash
artist-portrait bgm import --project ./project.yaml --file media/song.wav
artist-portrait bgm import --project ./project.yaml \
  --file media/source-video.mp4 --extract-in 0 --extract-out 30
artist-portrait bgm import --project ./project.yaml --source-id <source-id>
artist-portrait bgm list --project ./project.yaml
artist-portrait bgm recommend --project ./project.yaml
artist-portrait bgm rhythm --project ./project.yaml
artist-portrait bgm select --project ./project.yaml --recommendation-id <id>
artist-portrait bgm fit --project ./project.yaml --candidate <candidate-id> \
  --fit-mode auto --fade-in-seconds 0.5 --fade-out-seconds 1.0 \
  --ducking-gain-db -9
artist-portrait bgm review --project ./project.yaml
```

The user must select the candidate. The CLI may normalize/extract locally,
measure loudness, and create loop/trim/fade/ducking instructions. It must keep
BPM null when no validated beat engine exists and must not render final export
media.

`bgm fit` and `bgm select` may accept explicit controls for `--fit-mode`,
`--fade-in-seconds`, `--fade-out-seconds`, `--target-gain-db`,
`--ducking-gain-db`, `--no-ducking`, and `--beat-align`. These controls are
recorded in `BgmFitControls` inside `.artist-portrait/data/bgm_fit.json`; they
do not move timeline edit points or fabricate beat grids.

`bgm rhythm` requires existing `.artist-portrait/data/bgm_analysis.json` and
writes `.artist-portrait/data/bgm_rhythm_intelligence.json`,
`output/bgm_rhythm_intelligence.md`, and `output/bgm_rhythm_handoff.json`. It
turns validated beat evidence into editing-facing beat quality, bar/phrase
hints, source-risk guidance, no-engine next actions, and mixed-video-audio
warnings. It does not select music, move edit points, fit music, render media,
call models, access the network, or fabricate BPM/beat grids.

`rhythm --edit-guidance` requires the current rhythm plan and current timeline.
It writes `.artist-portrait/data/edit_guidance.json`,
`output/edit_guidance.md`, and `output/edit_guidance_handoff.json`, covering
manual subtitle, transition, pause, ducking, phrase, cut/cue, ending,
source-risk, QC-repair, and handoff guidance. It does not mutate the timeline,
move edit points, select music, fit music, render media, call models, access
the network, or use image generation/editing.

`bgm review` writes `.artist-portrait/data/bgm_fit_review.json` and
`output/bgm_fit_review.md` when a recommendation-driven fit exists. It checks
selection, recommendation context, fit, timeline, analysis/beat evidence, and
preview/final-export readiness. It reports missing or stale rendered media but
does not render, select music, call models, access the network, or move edit
points.

## Preview Workflow

V0-014 can render low-resolution local review media after timeline generation.
It reads `output/timeline_draft.json` and, when present, the current
`.artist-portrait/data/bgm_fit.json`. It writes:

```text
output/preview_lowres.mp4
.artist-portrait/data/preview_manifest.json
.artist-portrait/data/preview_validation.json
output/preview_review.md
```

Use:

```bash
artist-portrait preview --project ./project.yaml --width 480 --fps 12
artist-portrait review --project ./project.yaml --scope preview
artist-portrait composition --project ./project.yaml --samples 9
artist-portrait composition --project ./project.yaml --agent-output ./composition_review_candidate.json
artist-portrait composition --project ./project.yaml --preview-candidate <candidate-id>
artist-portrait baseline --project ./project.yaml
artist-portrait baseline --project ./project.yaml --agent-output ./aesthetic_baseline_candidate.json
artist-portrait second-cut --project ./project.yaml --concept-id <concept-id>
```

Preview and final export resolve an explicit canvas from the project aspect
ratio, normalize every segment with `contain` fit before concatenation, and
record whether each timeline transition was actually rendered. A valid media
export proves technical delivery only; crop/reframe composition and aesthetic
quality still require the host-Agent review gate.

`composition` requires a current valid final export. It extracts deterministic
representative frames into rebuildable local cache, writes
`output/composition_contact_sheet.jpg`, and prepares
`output/composition_review_handoff.json` with exact media/timeline fingerprints.
It does not call a model, access the network, generate imagery, or apply a crop.
An explicit review candidate is byte-quarantined and must cover every supplied
sample, match all media fingerprints/timestamps, and contain bounded crop
geometry. `--preview-candidate` renders review-only cropped frame evidence; it
does not change the timeline or final export.

`baseline` joins the current timeline, duration options, clip/audio evidence,
and reviewed composition samples into one visible host-Agent boundary. The
candidate must cover each exact timeline/source range once, preserve uncertainty,
and compare short, standard, and extended concepts. The user selects the
direction later. It also reviews source audio, BGM, vocal continuity, text,
cuts, transitions, pauses, composition, and ending together, then records an
honest first-cut publishability verdict. Import does not apply edits or render media.

`second-cut` is the explicit concept-selection boundary. It rejects unknown or
omitted concept ids and writes one canonical supervised candidate plan covering
selection, structure, trims, per-shot reframes, audio/BGM, text, transitions,
pauses, ending, and verification. Planned actions are never reported as applied.

`reframe` is the supervised application boundary. Its byte-visible selection
must cover every timeline segment, bind current timeline/final/composition
fingerprints, and explicitly choose a candidate or preserve the frame. It
blocks rejected candidates and protected-region loss, preserves final audio,
records performer-containment and crop-jump risks, and writes an independent
playback candidate without replacing canonical media.

`evidence-map` creates one canonical clip-aligned evidence map from current
source, scene/clip, transcript, keyframe/analysis, local audio, and edit-brief
goal artifacts. It preserves exact fingerprints and exposes partial/unavailable
channels and semantic unknowns. It does not infer speech, music, applause,
emotion, lyrics, BPM, or visual meaning from missing or merely technical data.

`editorial-score` consumes the current canonical evidence map and creates one
candidate set with hook, emotion, information, visual, audio, rhythm, ending,
and risk dimensions plus separate highlight/hook/ending ranks. It excludes
pure-audio units from visual ranking, gives no first/last bonus, and never
converts loudness or missing semantics into aesthetic certainty.

`structure-recommend` generates exactly three materially distinct duration and
structure options from the current editorial scores and edit brief. Each option
contains exact ranked ranges, hook/build/payoff allocation, sacrifices,
retained qualities, confidence, and coupled downstream risks. It never applies
the suggested ordering or changes timeline/media.

`bgm-match` evaluates every explicit BGM input state against current structure
options. Mood and rhythm remain unknown without evidence; mixed video audio
raises voice/ducking/text/transition pressure and is never clean BGM.

`text-plan` creates timing plans for titles, evidence-backed subtitles and
emphasis, pauses, and text-free landing space across all duration options. It
validates reading density and marks sampled safe regions for manual playback
review. Missing transcript yields unavailable slots, not invented text.

`first-cut-review` reviews the current canonical final across nine editorial
and audiovisual domains. It preserves earlier Host-Agent findings, binds newer
V2 evidence, and refuses to count plans or independent playback candidates as
applied first-cut improvements.

Preview rendering may use local FFmpeg/ffprobe to extract timeline video
ranges, retain original source audio, apply fitted BGM gain/fades/looping, and
duck BGM under retained original audio. It must not choose music, fabricate beat
alignment, render final delivery media, call models, access the network, or use
image generation/editing. Preview review validates expected duration against
actual ffprobe duration, video/audio stream presence, dimensions, frame rate,
profile drift, output hash, and upstream fingerprints.

## Acceptance Workflow

Use acceptance after the current project has at least reached timeline review,
or after preview/final export when checking delivery readiness:

```bash
artist-portrait acceptance --project ./project.yaml
artist-portrait acceptance --project ./project.yaml --profile core
artist-portrait acceptance --project ./project.yaml --profile preview
artist-portrait acceptance --project ./project.yaml --profile delivery
artist-portrait acceptance --project ./project.yaml --profile delivery --repair-plan
artist-portrait acceptance --project ./project.yaml --profile delivery --execution-record ./execution_record.json
```

It writes `.artist-portrait/data/acceptance_report.json` and
`output/acceptance_report.md`. It audits existing artifacts and state for core
readiness, BGM readiness, rhythm-plan readiness, preview readiness,
final-export readiness, rhythm media QC readiness, and forbidden capability
flags. The default `standard` profile preserves the overall readiness report;
explicit `core`, `preview`, and `delivery` profiles turn the relevant readiness
level into the hard gate and exit code. `preview` requires existing rhythm plan,
preview, and rhythm media QC evidence. `delivery` requires existing rhythm
plan, preview, final export, and rhythm media QC evidence. It does not generate
proposals, choose music, fit music, run rhythm, run rhythm QC, render media,
call models, access the network, or repair missing artifacts.

`run_checks.py` includes a generated real-media acceptance fixture when local
FFmpeg/ffprobe are available. The fixture creates temporary video and BGM audio,
runs the local pipeline through proposal import, timeline, BGM fit/review,
rhythm planning, preview, rhythm QC, final export, refreshed rhythm QC, and
`core`/`preview`/`delivery` acceptance profiles, then
deletes the temporary workspace. It uses no downloaded media, network access,
CLI-side model calls, automatic music selection, or paid APIs.

## Rhythm Planning Workflow

Use rhythm planning after timeline generation, and preferably after explicit
BGM fitting when music is part of the edit:

```bash
artist-portrait rhythm --project ./project.yaml
artist-portrait rhythm --project ./project.yaml --intent ./rhythm_intent.json
artist-portrait rhythm --project ./project.yaml --intent ./rhythm_intent.json --agent-output ./rhythm_candidate.json
artist-portrait rhythm --project ./project.yaml --qc
artist-portrait rhythm --project ./project.yaml --repair-plan --acceptance-profile delivery
```

It writes `.artist-portrait/data/rhythm_plan.json`,
`output/rhythm_report.md`, and `output/rhythm_agent_handoff.json`. The report
audits timeline rhythm, BGM rhythm, compatibility, explicit intent, cut/cue
alignment, transitions, text/subtitle readiness, ducking/silence, ending shape,
and optional external rhythm recommendations. It does not move edit points,
select music, fit music automatically, render media, call models from the CLI,
access the network, or fabricate BPM/beat grids.

With `--qc`, rhythm planning reads the current rhythm plan plus existing
preview/final-export manifests and validation reports, then writes
`.artist-portrait/data/rhythm_media_qc.json`,
`output/rhythm_media_qc.md`, and `output/rhythm_media_qc_handoff.json`. It
checks preview/final binding, timeline and BGM freshness, duration drift, audio
expectations, ducking render state, ending render state, and media-QC summary.
It does not render preview/final media or mutate timeline/music artifacts.

With `--repair-plan`, rhythm reads existing rhythm, rhythm-QC, acceptance,
preview, final-export, and BGM evidence, then writes
`.artist-portrait/data/rhythm_repair_plan.json`,
`output/rhythm_repair_plan.md`, and `output/rhythm_repair_handoff.json`. It
orders manual next commands by acceptance profile. It does not execute commands,
render media, move edit points, select music, fit music, call models from the
CLI, or access the network.

## Diagnostics

Remove only rebuildable workspace cache after local rendering has accumulated:

```bash
artist-portrait cleanup --project ./project.yaml --json
```

The command preserves source media, exported media, canonical data, and run
records. It never hides evidence with ignore rules.

- Use `doctor --json` before deciding the next command.
- Treat `recommended_commands` as guidance, not automatic repair.
- Treat `missing_output_ref` as a rebuild signal for the step that produced the
  missing artifact.
- Treat `source_ledger_invalid` as a stop condition until
  `.artist-portrait/data/sources.jsonl` is fixed or regenerated.
- Treat `map_invalidated` and `review_project_invalidated` as rebuild signals
  after a newer scan changes the source ledger.
- Treat `segment_invalidated` as a rebuild signal after a newer scan changes
  the source ledger.
- Treat `clips_invalid` as a stop condition until `.artist-portrait/data/clips.jsonl`
  is fixed or regenerated.
- Treat `scene_detection_required_missing` as a dependency stop condition:
  install PySceneDetect or change `features.scene_detection` to `auto`/`off`.
- Treat `transcripts_invalid` as a stop condition until
  `.artist-portrait/data/transcripts.jsonl` is fixed or regenerated.
- Treat `transcription_required_missing` as a dependency stop condition:
  install faster-whisper/local model or change `features.transcription` to
  `auto`/`off`.
- Treat `transcribe_invalidated` as a rebuild signal after a newer scan changes
  the source ledger.
- Treat `keyframes_invalid` as a stop condition until
  `.artist-portrait/data/keyframes.jsonl` is fixed or regenerated.
- Treat `keyframe_cache_missing` as a rebuild signal for
  `.artist-portrait/cache/keyframes/`.
- Treat `keyframes_invalidated` as a rebuild signal after a newer scan or
  segment changes upstream ledgers.
- Treat `analysis_invalid` as a stop condition until
  `.artist-portrait/data/analysis.jsonl` is fixed or regenerated.
- Treat `analysis_pending` as a signal to run
  `artist-portrait analyze --project ./project.yaml` after clips exist.
- Treat `analyze_invalidated` as a rebuild signal after newer source, clip,
  transcript, or keyframe ledgers change.
- Treat `map_pending` as a signal to run
  `artist-portrait map --project ./project.yaml` after analysis exists.
- Treat `map_invalidated` as a rebuild signal after newer source, clip,
  transcript, keyframe, or analysis ledgers change.
- Treat `proposals_invalid` as a stop condition until
  `.artist-portrait/data/proposals.json` is fixed or regenerated by a later
  approved proposal generation gate.
- Treat `proposal_context_invalid` as a stop condition until
  `.artist-portrait/data/proposal_context.json` is fixed or regenerated.
- Treat `proposal_agent_handoff_pending` as a signal to run `propose`.
- Treat `proposal_agent_candidate_pending` as a signal for the current
  Codex/ChatGPT host Agent to generate one ProposalSet candidate from
  `output/proposal_agent_handoff.json`, then import it with `--agent-output`.

## Hard Boundaries

Do not perform these actions through this skill in the current local foundation
gate. A later validated gate may use mature third-party tools, installed Codex
skills, plugins, search, image generation/editing tools, models, or media
libraries instead of rebuilding those capabilities from scratch:

- remote ASR, model-downloading transcription, or ungrounded text classification
- OpenCV, visual analysis, or visual classification
- embeddings
- visual classification beyond explicit evidence placeholders
- automatic BGM recommendation or candidate selection
- fabricated BPM or beat-grid analysis
- fake, template, or model-free creative proposals
- paid or remote-provider creative proposal generation
- model calls
- network search
- image generation or image editing

Keep all current foundation outputs local and deterministic.
