# Current Development Batch

## Batch Header

- Batch ID: `V2-07`
- Name: Text, Subtitle, And On-Screen Timing Plan
- Type: product capability milestone
- Status: `completed`
- Capability gate: `V2-07`
- Prerequisite: published `V2-06 BGM Mood And Rhythm Matching`
- Publication: one commit/push only after complete validation

## Goal Delta

V2-07 turns each current duration/structure option into a text-layer timing
plan. Every title, subtitle, emphasis, pause, or empty-space reservation must
bind an exact ranked range, enter/exit time, reading budget, safe-region policy,
and audio/BGM pressure. Missing transcript must produce explicit unavailable
subtitle slots, never invented dialogue, lyrics, or emphasis words.

## Internal Acceptance Checklist

| ID | Outcome | Acceptance | Status |
|---|---|---|---|
| `canonical_text_plan` | One canonical plan | One JSON and one Markdown report. | `completed` |
| `fresh_structure_binding` | Current structure | Exact recommendation fingerprint and all three options bind. | `completed` |
| `title_timing` | Title layer | Title timing is bounded and option-aware. | `completed` |
| `subtitle_truth` | Transcript boundary | Subtitle text requires overlapping transcript evidence. | `completed` |
| `emphasis_truth` | Emphasis boundary | Highlight words require supplied text evidence. | `completed` |
| `reading_budget` | Reading safety | Character count, duration, and density are validated. | `completed` |
| `safe_region` | Composition safety | Text avoids protected performer/branding regions where evidence exists. | `completed` |
| `pause_and_space` | Breathing room | Pauses and empty visual space are explicit timed elements. | `completed` |
| `audio_pressure` | BGM/source-audio coupling | Ducking and mixed-audio pressure affect text density. | `completed` |
| `real_validation` | Cross-source closeout | Stage/interview degraded plans and full checks pass. | `completed` |

## Guardrails

- No invented transcript, subtitle, lyric, speaker, or emphasis word.
- Missing transcript is `unavailable`, not empty dialogue or silence.
- Text plans do not mutate timelines, burn subtitles, or render media.
- No model/network/paid API/music selection.
- Local generated evidence remains outside Git packages.

## Next Work

Both real projects produce 5/7/10 unavailable subtitle slots, one bounded title
per option, one payoff text-free reservation, manual safe-region review, and no
invented transcript/lyrics. 243 tests and all quality checks passed.
