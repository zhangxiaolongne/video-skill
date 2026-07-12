# Current Development Batch

## Batch Header

- Batch ID: `V2-02`
- Name: Frame Composition And Reframing
- Type: product capability milestone
- Status: `completed`
- Capability gate: `V2-02`
- Prerequisite: `V2-01 Real Video Aesthetic Baseline` published on `main`
- Commit/push policy: publish only when the complete V2-02 version passes real
  stage/interview playback validation and the full project check suite

## Goal Delta

Before V2-02, the skill can review real frames and propose geometry-bound
reframes, but it cannot apply a supervised per-segment selection to playable
media. Candidate contact sheets are evidence, not an edited video.

After V2-02, an explicit selection map can render one independent playback
candidate from the current final/timeline/composition evidence, preserve audio,
validate every crop and protected region, record shot-to-shot crop changes, and
prove output duration/canvas/streams without mutating the canonical timeline or
final export.

## Internal Acceptance Checklist

These are acceptance checks inside the single V2-02 version. They are not
subversions and must never be reported as V2-02-01-style progress.

| ID | Independent outcome | Acceptance | Status |
|---|---|---|---|
| `explicit_selection` | Explicit segment selection | Every applied segment binds a user/host-approved candidate id; no implicit top-candidate selection. | `completed` |
| `fresh_bindings` | Current evidence bindings | Timeline, final media, composition review, contact sheet, and selection bytes are fingerprint-bound. | `completed` |
| `segment_applicability` | Sample-to-segment applicability | Candidate sample evidence must map to the selected timeline segment; rejected candidates are blocked. | `completed` |
| `protected_regions` | Protected-region safety | Crop validation checks performer/protected boxes and records conditional/manual risks. | `completed` |
| `playback_render` | Real per-segment render | Render crop/scale per selected segment while preserving original candidate audio. | `completed` |
| `crop_change_audit` | Shot-change audit | Record candidate changes, crop-center jumps, and unsupported within-segment shot variability. | `completed` |
| `non_destructive_output` | Independent candidate output | Write separate playback media and canonical application evidence without replacing timeline/final. | `completed` |
| `media_qc` | Playback media QC | Validate hash, duration, canvas, frame rate, video/audio streams, and application truth. | `completed` |
| `cross_source_truth` | Stage/interview contrast | Stage applies visible reframes; interview preserves native full-frame composition without fake changes. | `completed` |
| `version_validation` | Complete V2-02 validation | Full tests, quality passes, package/install, release readiness, docs, and diff checks pass. | `completed` |

## Guardrails

- Reframe selection must be explicit and visible.
- Never apply a rejected crop candidate.
- A frame-sample candidate cannot prove full-motion safety; conditional risks
  remain visible until playback review.
- Preserve source/final/timeline/contact-sheet provenance and content hashes.
- Do not mutate `output/timeline_draft.json` or the canonical final export.
- Do not select or fit music, fabricate beats, call models from the CLI, access
  the network, or use paid providers.
- Local playback candidates and media cache remain outside Git/Skill packages.

## Closeout Evidence

- Interview: 60.00 seconds, `1280x720`, six explicit full-frame choices, audio
  retained, zero crop-center movement, `passed`.
- Stage: 72.10 seconds, `1080x1920`, seven visible reframes and one explicit
  promo-card preservation, audio retained, conditional subject/crop-jump risks
  remain warnings.
- Validation: `243 passed`; golden, BGM/rhythm, NLE round-trip, schemas,
  package/install simulation, release candidate, and diff checks passed.

## Next Work

Publish V2-02 as one version. Then plan the complete V2-03 evidence-fusion
version; do not start it inside this batch.
