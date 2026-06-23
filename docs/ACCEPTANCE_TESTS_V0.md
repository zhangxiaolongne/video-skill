# Acceptance Tests V0

Authoritative source: `artist_portrait_editor_revision5_optimized.md`.

Current local foundation tests cover:

- valid and invalid `project.yaml`
- fixed exit code mapping
- Pydantic schema generation
- committed schema drift
- `validate`
- `init`
- `init --dry-run`
- `status` before and after initialization
- repeated `init`
- prevention of business artifact creation during Stage A
- supported media scan and `sources.jsonl`
- `sources.csv` import
- rescan identity and supersedes tracking
- minimal `map`
- minimal `review --scope project`
- enhanced `status --json`
- `run_report.md` refresh after state-mutating commands
- invalid `sources.jsonl` handling for `scan`, `status`, `map`, and `review`
- atomic writes for rebuildable report outputs
- ledger output reference consistency in `status` and `review`
- minimal `review --scope all` that runs project review and marks timeline
  review as skipped
- read-only `doctor` diagnostics for uninitialized workspaces, missing output
  refs, invalid source ledgers, and recommended next commands
- root `SKILL.md` and `agents/openai.yaml` metadata validation
- skill package preflight with hard errors separated from known install-name
  warnings
- skill package policy declaring `artist-portrait-editor` as canonical install
  directory and `video-skill` as an allowed distribution repository
- canonical install simulation with zero package preflight warnings
- release readiness documentation for the unpushed local batch
- V0-003 gate consistency from Stage A acceptance into media scan foundation
- deterministic `scan_report.md`
- status and doctor visibility for scan reports
- downstream `map` and `review_project` invalidation after source ledger changes
- committed clip record schema
- deterministic fixed-window `segment`
- optional PySceneDetect scene segmentation routing for `off`, `auto`, and
  `required`
- fixed-window fallback when `scene_detection: auto` lacks or fails
  PySceneDetect
- dependency exit code when `scene_detection: required` lacks or fails
  PySceneDetect
- canonical `clips.jsonl`
- rebuildable `clip_report.md`
- status and doctor visibility for clip ledgers and clip reports
- downstream invalidation after source or clip ledger changes
- committed transcript record schema
- `transcribe` routing for `transcription: off`, `auto`, and `required`
- local-only faster-whisper adapter behavior without requiring faster-whisper in
  tests
- canonical `transcripts.jsonl`
- status and doctor visibility for transcript ledgers
- downstream invalidation after source ledger changes
- committed keyframe record schema
- `keyframes` command requiring existing clip ledger
- ffmpeg dependency failure for video clips
- canonical `keyframes.jsonl`
- rebuildable `.artist-portrait/cache/keyframes/`
- audio-only empty manifest handling
- status and doctor visibility for keyframe manifests and missing cache files
- downstream invalidation after source or clip ledger changes
- committed analysis record schema
- `analyze` command requiring existing clip ledger
- canonical `analysis.jsonl`
- rebuildable `analysis_report.md`
- evidence-only assertions that do not classify shot size, camera motion,
  emotion, action, or visual quality
- status and doctor visibility for analysis manifests
- downstream invalidation after source, clip, transcript, keyframe, or analysis
  ledger changes
- `map` requiring current analysis before rendering
- `material_map.md` rendered from source and analysis ledgers
- deterministic priority review queue, pending confirmation, and risk sections
- material map invalidation after analysis changes
- committed proposal set schema
- `propose` requiring `material_map.md`
- committed proposal context schema
- `propose` writing deterministic `proposal_context.json`
- committed text-model gate schema
- `propose` writing deterministic `text_model_gate.json`
- committed proposal request packet schema
- `propose` writing deterministic `proposal_request.json`
- blocked and ready proposal request statuses without model calls
- committed proposal adapter check schema
- `propose` writing deterministic `proposal_adapter_check.json`
- adapter preflight records `model_call_performed: false` and
  `network_performed: false`
- adapter preflight detects plaintext secret material in checked project files
- committed proposal provider registry schema
- `propose` writing deterministic `proposal_provider_registry.json`
- provider registry records `local_mock`, `generation_open: false`,
  `model_call_performed: false`, and `network_performed: false`
- committed proposal mock adapter handshake schema
- `propose` writing deterministic `proposal_mock_adapter_handshake.json`
- mock adapter handshake validates the future response contract without model
  calls, network access, or generated proposal content
- committed proposal execution approval request schema
- `propose` writing deterministic `proposal_execution_approval_request.json`
- execution approval request records no approval, no selected secret source, no
  credential reads, no model calls, no network access, no execution, and no
  proposal content
- committed proposal execution authorization schema
- `propose` writing deterministic `proposal_execution_authorization.json`
- execution authorization records no approved execution gate, no user approval,
  no credentials, no model calls, no network access, no execution, and no
  proposal content
- committed proposal provider output quarantine schema
- `propose` writing deterministic `proposal_provider_output_quarantine.json`
- provider output quarantine records no raw output capture, no parsed payload,
  no promotion to proposals, no validation, no model calls, no network access,
  and no proposal content
- committed proposal provider result envelope schema
- `propose` writing deterministic `proposal_provider_result.json`
- provider result envelope records no payload generation, no validation, no
  model calls, no network access, and no proposal content
- status and doctor visibility for malformed proposal request packets
- status and doctor visibility for malformed proposal adapter check packets
- status and doctor visibility for malformed proposal provider registries
- status and doctor visibility for malformed proposal mock adapter handshakes
- status and doctor visibility for malformed proposal execution approval requests
- status and doctor visibility for malformed proposal execution authorizations
- status and doctor visibility for malformed proposal provider output quarantines
- status and doctor visibility for malformed proposal provider result envelopes
- `propose` blocking without an approved text-model gate
- `propose` blocking even when the text-model gate is ready because generation
  remains closed
- `propose` writing no fake `proposals.json` or `proposals.md` when blocked
- status and doctor visibility for malformed proposal context packets
- status and doctor visibility for malformed text-model gate packets
- status and doctor visibility for malformed proposal sets
- proposal readiness invalidation after upstream source, clip, transcript,
  keyframe, analysis, or map changes
- committed proposal validation report schema
- `review --scope proposal` requiring `proposal_context.json` and
  `proposals.json`
- `review --scope proposal` writing deterministic `proposal_validation.json`
  and rebuildable `proposal_review.md`
- proposal validation for unknown clip refs, unknown fact refs, forbidden
  source usage, material-map fingerprint drift, and missing BGM strategy fields

Future visual classification, full proposal generation, timeline, preview,
remote model, BGM, image generation/editing, and network fixtures are
intentionally not implemented yet.
