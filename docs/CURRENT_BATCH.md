# Current Development Batch

## Batch Header

- Batch ID: `V3-03`
- Name: Interactive Revision Semantics
- Type: product capability milestone
- Status: `completed`
- Capability gate: `V3-03`
- Prerequisite: published `V3-02 Style Templates`
- Publication: one commit/push only after complete validation

## Goal Delta

V3-03 converts compound natural-language feedback into explicit, evidence-bound
editing semantics and tracks whether each semantic request was applied,
partially applied, left manual, skipped, or blocked. It extends the existing
revision plan/application chain instead of creating a parallel approval system.

## Internal Acceptance Checklist

| ID | Outcome | Acceptance | Status |
|---|---|---|---|
| `compound_intent` | Preserve compound feedback | One note produces every recognized request instead of stopping at the first keyword. | `completed` |
| `scope_intensity_priority` | Make interpretation operational | Every clause binds scope, intensity, priority, confidence, and matched text. | `completed` |
| `cross_domain_actions` | Translate language into edit work | Style, rhythm, text, voice, BGM, transition, duration, hook, emotion, and ending requests map to concrete actions. | `completed` |
| `audiovisual_coupling` | Prevent isolated edits | Actions expose coupled BGM, source-audio, text, rhythm, transition, composition, and emotion domains. | `completed` |
| `evidence_limits` | Preserve truthfulness | Every clause requires current timeline/cut-review or host/user interpretation and playback evidence; unknown language stays low-confidence custom. | `completed` |
| `conflict_detection` | Expose contradictory notes | Shorter/longer and faster/breathing conflicts remain visible with section-scoping resolution. | `completed` |
| `observable_acceptance` | Define what success looks like | Every clause and action has playback-observable acceptance, not subjective labels alone. | `completed` |
| `application_tracking` | Track real execution | Revision application reports semantic outcomes as applied, partial, manual-only, unselected, or blocked. | `completed` |
| `canonical_convergence` | Avoid workflow fragmentation | Existing revision JSON/Markdown and application JSON/Markdown own the feature; no new approval chain exists. | `completed` |
| `real_project_truth` | Validate real boundaries | Interview real media completes plan/application semantics; stage stale proposal state and event input-only state remain explicit unavailable boundaries. | `completed` |

## Guardrails

- Natural-language interpretation is deterministic CLI guidance, not proof of hidden content understanding.
- “More premium” changes hierarchy, restraint, sound, pacing, text, transition, and composition together; it is not a filter name.
- No semantic clause is called applied unless revision-application action evidence supports that status.
- The canonical timeline is not mutated, media is not rendered, and music/style is not silently selected.
- CLI performs no model call or network access. Host-Agent interpretation may be added through a future validated boundary.

## Real Acceptance

- `runs/interview_contrast`: compound Chinese feedback produced four semantic clauses, five actions, and explicit manual-only application outcomes without timeline mutation.
- `runs/chenhaoyu_klein_blue`: existing timeline/cut review are invalidated by a newer brief/proposal boundary; V3-03 correctly refuses to use stale evidence.
- `runs/public_event_mix`: no canonical timeline/cut review exists; V3-03 correctly refuses to fabricate revision semantics as an applied loop.

## Next Work

V3-04 A/B Version Review may begin only after V3-03 passes full project checks
and is published as one complete capability version.
