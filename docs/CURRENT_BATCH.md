# Current Development Batch

## Batch Header

- Batch ID: `V2-06`
- Name: BGM Mood And Rhythm Matching
- Type: product capability milestone
- Status: `completed`
- Capability gate: `V2-06`
- Prerequisite: published `V2-05 Duration And Structure Recommendation`

## Goal Delta

V2-06 evaluates direct audio, video-extracted mixed audio, source embedded
audio, multiple candidates, and no-file-yet planning against all duration
options. It exposes mood/rhythm evidence status plus ducking, text-timing, and
transition pressure without selecting music or fabricating semantics/BPM.

## Internal Acceptance Checklist

| ID | Outcome | Acceptance | Status |
|---|---|---|---|
| `canonical_match` | One canonical match | One JSON and one report. | `completed` |
| `input_modes` | Complete input states | Direct, extracted, embedded, multiple, and none are representable. | `completed` |
| `structure_binding` | Current option binding | Exact structure fingerprint and all options bind. | `completed` |
| `mood_truth` | Mood evidence | Unknown mood stays unknown. | `completed` |
| `rhythm_truth` | Rhythm evidence | Missing BPM/beat stays unknown. | `completed` |
| `mixed_audio` | Contamination policy | Video/source mix is never clean BGM. | `completed` |
| `ducking_pressure` | Voice conflict pressure | Speech uncertainty raises pressure. | `completed` |
| `text_pressure` | Text timing pressure | Audio uncertainty propagates to text timing. | `completed` |
| `transition_pressure` | Transition pressure | Missing beat/phrase evidence remains explicit. | `completed` |
| `real_validation` | Cross-source closeout | Stage/interview and full checks pass. | `completed` |

## Guardrails

- No automatic candidate selection or fit.
- No mood, speech, vocals, BPM, beat, phrase, or genre fabrication.
- Mixed extracted/embedded video audio is not clean BGM.
- No model/network/paid API/render/timeline mutation.

## Next Work

Interview is `no_file_yet/planning_only`; stage has two mixed embedded-audio
candidates with unknown mood/rhythm and high downstream pressure. No candidate
is selected. 243 tests and all quality/package/release/diff checks passed.
