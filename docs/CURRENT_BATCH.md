# Current Development Batch

## Batch Header

- Batch ID: `V2-09`
- Name: Second-Cut Candidate Generation
- Type: product capability milestone
- Status: `completed`
- Capability gate: `V2-09`
- Prerequisite: published `V2-08 First-Cut Aesthetic Self-Review`
- Publication: one commit/push only after complete validation

## Goal Delta

V2-09 turns one explicit structure choice into an independent, playable second
cut. It applies ranked source ranges and hook/build/payoff order, retains source
audio, performs media QC, and compares first and second cuts without overwriting
the canonical first cut or concealing unresolved semantic/aesthetic evidence.

## Internal Acceptance Checklist

| ID | Outcome | Acceptance | Status |
|---|---|---|---|
| `explicit_option` | No silent choice | Short/standard/extended must be supplied explicitly. | `completed` |
| `fresh_bindings` | Current evidence | Structure, review, scores, BGM, text, sources, and final bind by hash. | `completed` |
| `candidate_timeline` | Applied source ranges | Exact ranked ranges become a sequential independent timeline. | `completed` |
| `real_reorder` | Material second cut | Hook/build/payoff ranges are genuinely reordered and rendered. | `completed` |
| `source_audio` | Audio continuity surface | Every range retains source audio or explicit silence. | `completed` |
| `bgm_truth` | No hidden music choice | Unselected BGM is not added; mixed audio remains mixed. | `completed` |
| `text_truth` | No invented subtitles | Missing transcript leaves text unapplied. | `completed` |
| `independent_render` | Preserve first cut | New MP4 cannot overwrite canonical timeline/final. | `completed` |
| `media_qc` | Playable output | Duration, canvas, fps, video, audio, and hash are verified. | `completed` |
| `first_second_comparison` | Honest improvement | Nine domains distinguish improved, preserved, and unresolved. | `completed` |

## Guardrails

- Require an explicit option; never choose the recommended option silently.
- Render local media only; no model/network call or automatic music selection.
- Do not overwrite canonical timeline/final or apply stale reframe evidence.
- Technical validity remains separate from aesthetic publishability.

## Next Work

Both real projects now have independent 60-second standard second cuts. The
interview is `1280x720 @ 24fps`; the stage cut is `1080x1920 @ 30fps`; both
retain source audio and pass media QC. Transcript, per-range composition,
fine-grained pacing, and mature publishability remain unresolved. V2-10 is next.
