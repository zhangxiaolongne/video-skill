# Current Development Batch

## Batch Header

- Batch ID: `V3-02`
- Name: Style Templates
- Type: product capability milestone
- Status: `completed`
- Capability gate: `V3-02`
- Prerequisite: published `V3-01 Multi-Version Creative Strategies`
- Publication: one commit/push only after complete validation

## Goal Delta

V3-02 provides six reusable style templates and evaluates every template against
real project source evidence and creative goals. Templates constrain structure,
rhythm, audio/BGM, subtitle density, transitions, composition, evidence, and
acceptance without silently applying a style.

## Internal Acceptance Checklist

| ID | Outcome | Acceptance | Status |
|---|---|---|---|
| `six_template_library` | Domain coverage | Six canonical production templates are complete. | `completed` |
| `structure_contracts` | Structural constraints | Every template owns bounded hook/context/build/payoff ratios. | `completed` |
| `rhythm_envelopes` | Pacing constraints | Shot-duration range and evidence-safe rhythm policy are explicit. | `completed` |
| `audio_bgm_hierarchy` | Sound constraints | Source audio and BGM roles are defined per style. | `completed` |
| `text_density` | Reading constraints | Subtitle density and maximum reading speed are bounded. | `completed` |
| `transition_composition` | Visual restraint | Transition and framing policies remain style-specific. | `completed` |
| `evidence_aware_matching` | Honest compatibility | Confirmed types and lower-confidence brief signals remain distinct. | `completed` |
| `specialized_precedence` | Professional matching | Dedicated stage/interview/event templates beat generic templates. | `completed` |
| `application_boundary` | User control | Best matches are advisory; selection/application remain null. | `completed` |
| `three_class_validation` | Real coverage | Stage, interview, and event projects select the correct best match. | `completed` |

## Guardrails

- Templates must contain executable constraints, not labels alone.
- `other` source type is unknown and cannot count as confirmed matching evidence.
- Specialized templates must outrank generic styles when evidence supports them.
- Do not select/apply templates, mutate timelines, render, or choose BGM.
- Local CLI remains deterministic and offline.

## Next Work

Stage best-matches `stage_portrait`, interview best-matches
`interview_portrait`, and confirmed public-event sources best-match
`event_montage`. Stage/interview remain conditional because source type and/or
transcript evidence is incomplete. V3-03 revision semantics are next.
