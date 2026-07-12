# Current Development Batch

## Batch Header

- Batch ID: `V2-03`
- Name: Transcript / Vision / Audio Evidence Fusion
- Type: product capability milestone
- Status: `completed`
- Capability gate: `V2-03`
- Prerequisite: published `V2-02 Frame Composition And Reframing`
- Publication: one commit/push only after the complete version passes

## Goal Delta

Before V2-03, transcript, keyframe, scene/clip, audio, composition, and user-goal
facts live in separate artifacts. Missing evidence is easy to mistake for a
negative finding.

After V2-03, one canonical evidence map aligns those channels by source clip,
binds every input fingerprint, exposes availability/confidence/degradation, and
provides truthful downstream scoring inputs without inventing speech, visual
semantics, applause, music, emotion, lyrics, or BPM.

## Internal Acceptance Checklist

| ID | Outcome | Acceptance | Status |
|---|---|---|---|
| `canonical_map` | One canonical map | One machine JSON plus one human report. | `completed` |
| `time_alignment` | Clip time alignment | Every evidence unit binds exact source and clip ranges. | `completed` |
| `input_provenance` | Fingerprint binding | Source/clip/transcript/keyframe/analysis/brief inputs are hashed. | `completed` |
| `transcript_channel` | Transcript coverage | Text/timing coverage is measured; absence is unavailable, not silence. | `completed` |
| `vision_channel` | Visual evidence | Keyframe/analysis coverage is visible without fabricated semantics. | `completed` |
| `scene_channel` | Boundary evidence | Fixed-window versus detected-scene confidence remains explicit. | `completed` |
| `audio_channel` | Local audio features | RMS/peak/silence evidence is computed locally with method provenance. | `completed` |
| `semantic_unknowns` | Honest unknown states | Speech/music/applause/emotion/lyrics/BPM remain unknown without evidence. | `completed` |
| `goal_and_conflict` | Goal/conflict binding | User goal and BGM/source-audio conflict risks bind each unit. | `completed` |
| `real_validation` | Cross-source closeout | Stage/interview degradation contrast plus full project checks pass. | `completed` |

## Guardrails

- No paid API, network access, hidden model call, package installation, or auto
  music selection.
- Audio energy is not music, applause, speech, emotion, or beat evidence.
- A keyframe proves sampled pixels exist, not what those pixels mean.
- Missing transcript is not silence and missing vision semantics is not a blank
  frame.
- Local media/cache/evidence remain outside Git and Skill packages.

## Closeout Evidence

- Interview: 45 units, transcript `0.0`, keyframes `1.0`, audio features `1.0`,
  detected scenes `0.0`, status `degraded`.
- Stage: 50 units, transcript `0.0`, keyframes `0.5`, audio features `1.0`,
  detected scenes `0.0`, status `degraded`.
- Both preserve speech/music/applause/emotion/lyrics/BPM as unknown.
- Validation: `243 passed`; golden, BGM/rhythm, NLE, schema, package/install,
  release candidate, and diff checks passed.

## Next Work

Publish V2-03 as one version. Plan V2-04 scoring from the canonical evidence map
without starting it inside this batch.
